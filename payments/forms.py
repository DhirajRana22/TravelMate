from django import forms
from .models import Payment, Refund

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_method', 'transaction_id']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

class RefundRequestForm(forms.ModelForm):
    class Meta:
        model = Refund
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class PaymentVerificationForm(forms.Form):
    payment_id = forms.CharField(max_length=50, required=True)
    transaction_id = forms.CharField(max_length=100, required=True)
    
    def clean(self):
        cleaned_data = super().clean()
        payment_id = cleaned_data.get('payment_id')
        transaction_id = cleaned_data.get('transaction_id')
        
        # Check if payment exists
        try:
            payment = Payment.objects.get(payment_id=payment_id)
        except Payment.DoesNotExist:
            raise forms.ValidationError("Payment not found.")
        
        # Check if transaction ID matches
        if payment.transaction_id and payment.transaction_id != transaction_id:
            raise forms.ValidationError("Transaction ID does not match.")
        
        return cleaned_data