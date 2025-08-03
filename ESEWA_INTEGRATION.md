# eSewa Payment Integration for TravelMate

This document describes the eSewa payment gateway integration implemented in the TravelMate Django project.

## Overview

The eSewa integration allows users to pay for their bus bookings using eSewa digital wallet. The implementation follows eSewa's official API documentation and uses HMAC-SHA256 signature verification for secure transactions.

## Features

- **Secure Payment Processing**: Uses HMAC-SHA256 signature generation and verification
- **Seamless Integration**: Works with existing payment flow
- **Test Environment**: Configured with eSewa test credentials
- **Error Handling**: Proper success and failure callback handling
- **User Experience**: Clear payment instructions and status updates

## Technical Implementation

### 1. Core Components

#### `payments/esewa_utils.py`
- **EsewaConfig**: Configuration class with test credentials and URLs
- **generate_esewa_signature()**: HMAC-SHA256 signature generation
- **prepare_esewa_payment_data()**: Prepares payment form data
- **verify_esewa_payment()**: Verifies payment response signatures

#### Updated Views (`payments/views.py`)
- **process_payment()**: Enhanced to handle eSewa payment method
- **esewa_success()**: Handles successful payment callbacks
- **esewa_failure()**: Handles failed payment callbacks

#### Updated Templates
- **process_payment.html**: Enhanced with eSewa form submission
- **esewa_success.html**: Success page for completed payments
- **esewa_failure.html**: Failure page for failed payments

### 2. Payment Flow

#### Improved Payment Flow (Current)
1. **User selects payment method** (eSewa, Khalti, or Bus Conductor)
2. **Booking created with 'pending' status** - seats are temporarily reserved but not marked unavailable
3. **Payment processing**:
   - **eSewa**: User redirected to eSewa gateway → payment verification → booking confirmation
   - **Other methods**: Immediate confirmation for Khalti/Bus Conductor payments
4. **On successful payment verification**:
   - Payment status set to 'completed'
   - Booking status changed to 'confirmed'
   - Seats marked as unavailable
5. **On payment failure**:
   - Payment status set to 'failed'
   - Booking status changed to 'cancelled'
   - Seats remain available for other users

#### Benefits of New Flow
- **No ghost bookings**: Failed payments don't result in confirmed bookings
- **Seat availability accuracy**: Seats are only blocked after successful payment
- **Better user experience**: Clear feedback on payment status
- **Data consistency**: Booking and payment statuses are always synchronized

#### Legacy Flow (Reference)
1. **User Selection**: User selects eSewa as payment method
2. **Data Preparation**: System generates payment data with signature
3. **Redirect**: User is redirected to eSewa payment gateway
4. **Payment**: User completes payment on eSewa platform
5. **Callback**: eSewa redirects back with payment result
6. **Verification**: System verifies payment signature
7. **Completion**: Booking status is updated accordingly

### 3. Configuration

#### Test Credentials (Current)
```python
MERCHANT_CODE = "EPAYTEST"
SECRET_KEY = "8gBm/:&EnhH.1/q"
PAYMENT_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
```

#### Production Setup
For production, update the following in `settings.py`:
```python
# eSewa Production Settings
ESEWA_MERCHANT_CODE = "your_merchant_code"
ESEWA_SECRET_KEY = "your_secret_key"
ESEWA_PAYMENT_URL = "https://epay.esewa.com.np/api/epay/main/v2/form"
ESEWA_SUCCESS_URL = "https://yourdomain.com/payments/esewa/success/"
ESEWA_FAILURE_URL = "https://yourdomain.com/payments/esewa/failure/"
```

### 4. URL Configuration

New URLs added to `payments/urls.py`:
```python
path('esewa/success/', views.esewa_success, name='esewa_success'),
path('esewa/failure/', views.esewa_failure, name='esewa_failure'),
```

### 5. Security Features

- **CSRF Protection**: Callback views use `@csrf_exempt` for eSewa responses
- **Signature Verification**: All payments verified using HMAC-SHA256
- **Input Validation**: Proper validation of payment data
- **Error Handling**: Comprehensive error handling and logging

## Testing

### Running Tests
```bash
python test_esewa.py
```

### Test Coverage
- Signature generation
- Configuration validation
- Payment data preparation
- Mock payment processing

### Manual Testing
1. Create a booking
2. Navigate to payment page
3. Select eSewa payment method
4. Complete payment flow
5. Verify booking confirmation

## Integration Points

### Frontend (JavaScript)
- Dynamic form creation for eSewa submission
- AJAX handling for payment method selection
- Automatic redirection to eSewa gateway

### Backend (Django)
- Payment model updates
- Booking status management
- Transaction logging
- Error handling and user feedback

## Error Handling

### Common Scenarios
1. **Invalid Signature**: Payment verification fails
2. **Network Issues**: Timeout or connection errors
3. **Insufficient Balance**: User has insufficient eSewa balance
4. **Cancelled Payment**: User cancels payment on eSewa

### Error Recovery
- Failed payments allow retry
- Clear error messages to users
- Booking remains in pending state for retry

## Monitoring and Logging

### Payment Tracking
- All payment attempts logged
- Transaction IDs stored for reference
- Payment status updates tracked

### Debug Information
- Signature generation details
- Payment data validation
- Callback response handling

## Future Enhancements

1. **Payment Status API**: Implement eSewa payment status checking
2. **Refund Support**: Add eSewa refund functionality
3. **Analytics**: Enhanced payment analytics and reporting
4. **Mobile Optimization**: Improved mobile payment experience

## Known Issues and Troubleshooting

### Common Issues
1. **Signature Mismatch**: Ensure the secret key and message format are correct
2. **Invalid Response**: Check that all required fields are present in the callback
3. **CSRF Errors**: The callback views use `@csrf_exempt` decorator
4. **URL Configuration**: Ensure callback URLs are accessible and correctly configured
5. **Missing tax_amount Field**: eSewa requires the `tax_amount` field in the form submission (fixed in current implementation)

### Recent Fixes
- **Payment Flow and Booking Status Fix (Latest)**: 
  - **Issue**: Bookings were immediately confirmed and seats marked unavailable before payment verification, causing "Invalid payment response" errors while tickets remained booked
  - **Solution**: 
    - Changed initial booking status from 'confirmed' to 'pending'
    - Seats are now only marked unavailable after successful payment verification
    - Failed payments now properly cancel the booking and free up seats
    - Added proper transaction handling for all payment methods
  - **Impact**: Eliminates the issue where failed payments still result in confirmed bookings
- **Fixed tax_amount Field Issue**: Added the required `tax_amount` field to the eSewa form data. This field is mandatory according to eSewa API v2 documentation and should be set to "0" if no tax is applied.
- **Updated amount Field**: Changed the `amount` field to contain the base amount (without tax and service charges) as per eSewa requirements.

### Debug Tips
- Check Django logs for detailed error messages
- Verify eSewa test credentials are correctly set
- Test with small amounts first (minimum रू 10)
- Ensure callback URLs are accessible from eSewa servers
- Verify all required fields are present in the form submission: amount, tax_amount, total_amount, transaction_uuid, product_code, product_service_charge, product_delivery_charge, success_url, failure_url, signed_field_names, signature

## Support and Maintenance

### Regular Tasks
- Monitor payment success rates
- Update credentials when needed
- Review error logs
- Test payment flow regularly

### Troubleshooting
- Check signature generation
- Verify callback URLs
- Validate merchant credentials
- Review eSewa documentation updates

## Contact Information

For eSewa integration support:
- eSewa Developer Portal: https://developer.esewa.com.np/
- Technical Support: developer@esewa.com.np

---

**Note**: This integration uses eSewa test environment. For production deployment, ensure proper merchant account setup and credential updates.