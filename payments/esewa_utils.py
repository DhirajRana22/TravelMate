import hashlib
import hmac
import base64
from django.conf import settings
from decimal import Decimal

class EsewaConfig:
    """eSewa configuration settings"""
    # Test credentials from eSewa documentation
    MERCHANT_CODE = "EPAYTEST"
    SECRET_KEY = "8gBm/:&EnhH.1/q"
    
    # URLs
    PAYMENT_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
    SUCCESS_URL = "http://localhost:8000/payments/esewa/success/"
    FAILURE_URL = "http://localhost:8000/payments/esewa/failure/"
    STATUS_URL = "https://rc-epay.esewa.com.np/api/epay/payment/status/"
    
    @classmethod
    def get_merchant_code(cls):
        return getattr(settings, 'ESEWA_MERCHANT_CODE', cls.MERCHANT_CODE)
    
    @classmethod
    def get_secret_key(cls):
        return getattr(settings, 'ESEWA_SECRET_KEY', cls.SECRET_KEY)
    
    @classmethod
    def get_payment_url(cls):
        return getattr(settings, 'ESEWA_PAYMENT_URL', cls.PAYMENT_URL)
    
    @classmethod
    def get_success_url(cls):
        return getattr(settings, 'ESEWA_SUCCESS_URL', cls.SUCCESS_URL)
    
    @classmethod
    def get_failure_url(cls):
        return getattr(settings, 'ESEWA_FAILURE_URL', cls.FAILURE_URL)

    @classmethod
    def get_status_url(cls):
        return getattr(settings, 'ESEWA_STATUS_URL', cls.STATUS_URL)

def generate_esewa_signature(total_amount, transaction_uuid, product_code):
    """
    Generate HMAC-SHA256 signature for eSewa payment
    
    Args:
        total_amount (str): Total amount to be paid
        transaction_uuid (str): Unique transaction identifier
        product_code (str): Product code (merchant code)
    
    Returns:
        str: Base64 encoded signature
    """
    secret_key = EsewaConfig.get_secret_key()
    
    # Create the message string as per eSewa documentation
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    
    # Generate HMAC-SHA256 hash
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Encode to base64
    return base64.b64encode(signature).decode('utf-8')

def generate_esewa_signature_from_payload(payload: dict) -> str:
    """Generate signature using the fields specified by 'signed_field_names'.
    Falls back to the standard triple if 'signed_field_names' is missing.
    """
    secret_key = EsewaConfig.get_secret_key()
    signed = payload.get('signed_field_names')
    if signed:
        names = [n.strip() for n in str(signed).split(',') if n.strip()]
        message = ','.join(f"{name}={str(payload.get(name, ''))}" for name in names)
    else:
        total_amount = str(payload.get('total_amount'))
        transaction_uuid = str(payload.get('transaction_uuid'))
        product_code = str(payload.get('product_code'))
        message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def prepare_esewa_payment_data(payment, booking):
    """
    Prepare payment data for eSewa form submission
    
    Args:
        payment: Payment model instance
        booking: Booking model instance
    
    Returns:
        dict: Payment data for eSewa form
    """
    # Convert amount to string format required by eSewa
    total_amount = str(booking.total_fare)
    transaction_uuid = str(payment.payment_id)
    product_code = EsewaConfig.get_merchant_code()
    
    # Generate signature
    signature = generate_esewa_signature(total_amount, transaction_uuid, product_code)
    
    return {
        'amount': total_amount,  # Amount without tax and service charges
        'tax_amount': '0',  # Required field - set to 0 if no tax
        'total_amount': total_amount,
        'transaction_uuid': transaction_uuid,
        'product_code': product_code,
        'product_service_charge': '0',
        'product_delivery_charge': '0',
        'success_url': EsewaConfig.get_success_url(),
        'failure_url': EsewaConfig.get_failure_url(),
        'signed_field_names': 'total_amount,transaction_uuid,product_code',
        'signature': signature,
    }

def verify_esewa_payment(payment_data):
    """
    Verify eSewa payment response
    
    Args:
        payment_data (dict): Payment response data from eSewa
    
    Returns:
        bool: True if payment is verified, False otherwise
    """
    try:
        payload = dict(payment_data or {})
        # Support eSewa responses that wrap fields in a base64 'data' envelope
        raw = payload.get('data')
        if raw:
            import base64, json
            try:
                decoded = base64.b64decode(raw).decode('utf-8')
                payload = json.loads(decoded)
            except Exception:
                # If decoding fails, keep original payload
                pass

        received_signature = payload.get('signature')
        if not received_signature:
            return False

        expected_signature = generate_esewa_signature_from_payload(payload)
        return hmac.compare_digest(expected_signature, received_signature)

    except Exception as e:
        print(f"Error verifying eSewa payment: {e}")
        return False

def query_esewa_status(transaction_uuid, total_amount):
    try:
        import json
        from urllib import request
        from urllib.error import URLError, HTTPError
        url = EsewaConfig.get_status_url()
        product_code = EsewaConfig.get_merchant_code()

        # Build payload using canonical fields expected by eSewa
        signature = generate_esewa_signature(str(total_amount), str(transaction_uuid), product_code)
        payload = {
            'total_amount': str(total_amount),
            'transaction_uuid': str(transaction_uuid),
            'product_code': product_code,
            'signature': signature,
        }
        data = json.dumps(payload).encode('utf-8')

        req = request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {'raw': body}

            # Normalize status across possible response shapes
            status = str(
                parsed.get('status')
                or parsed.get('result')
                or parsed.get('message')
                or parsed.get('raw', '')
            ).upper()
            verified = any(s in status for s in ['COMPLETE', 'COMPLETED', 'SUCCESS', 'SUCCESSFUL', 'APPROVED'])
            return {'verified': verified, 'response': parsed}
    except (URLError, HTTPError) as e:
        return {'verified': False, 'error': str(e)}
    except Exception as e:
        return {'verified': False, 'error': str(e)}