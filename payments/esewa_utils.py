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
        # Extract required fields
        total_amount = payment_data.get('total_amount')
        transaction_uuid = payment_data.get('transaction_uuid')
        product_code = payment_data.get('product_code')
        received_signature = payment_data.get('signature')
        
        if not all([total_amount, transaction_uuid, product_code, received_signature]):
            return False
        
        # Generate expected signature
        expected_signature = generate_esewa_signature(total_amount, transaction_uuid, product_code)
        
        # Compare signatures
        return hmac.compare_digest(expected_signature, received_signature)
        
    except Exception as e:
        print(f"Error verifying eSewa payment: {e}")
        return False