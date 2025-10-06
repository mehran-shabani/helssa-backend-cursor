from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


def normalize_phone_number(phone):
    """Normalize phone number by removing spaces, converting Persian digits, and handling country codes."""
    if not phone:
        return phone
    
    # Persian to English digit mapping
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    
    # Remove spaces and convert Persian digits
    phone = phone.replace(' ', '').replace('-', '').translate(translation_table)
    
    # Handle country codes (+98, 0098, 98)
    if phone.startswith('+98'):
        phone = '0' + phone[3:]
    elif phone.startswith('0098'):
        phone = '0' + phone[4:]
    elif phone.startswith('98') and len(phone) == 12:
        phone = '0' + phone[2:]
    
    return phone


class RequestOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)
    
    def validate_phone_number(self, value):
        # Normalize first
        normalized = normalize_phone_number(value)
        
        # Then validate
        if not normalized or not normalized.isdigit() or len(normalized) != 11:
            raise serializers.ValidationError('شماره تلفن باید ۱۱ رقم باشد')
        if not normalized.startswith('09'):
            raise serializers.ValidationError('شماره تلفن معتبر نیست')
        
        return normalized


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)
    code = serializers.IntegerField(required=True)
    
    def validate_phone_number(self, value):
        # Normalize phone number
        normalized = normalize_phone_number(value)
        
        if not normalized or not normalized.isdigit() or len(normalized) != 11:
            raise serializers.ValidationError('شماره تلفن باید ۱۱ رقم باشد')
        if not normalized.startswith('09'):
            raise serializers.ValidationError('شماره تلفن معتبر نیست')
        
        return normalized
    
    def validate_code(self, value):
        if not (100000 <= value <= 999999):
            raise serializers.ValidationError('کد باید ۶ رقم باشد')
        return value


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'phone_number', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'phone_number', 'date_joined')
