from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, username=None, email=None, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('شماره تلفن الزامی است')
        
        # Normalize phone number
        phone_number = phone_number.strip()
        
        if email:
            email = self.normalize_email(email)
        
        # Ensure is_active defaults to False unless explicitly set
        extra_fields.setdefault('is_active', False)
        
        user = self.model(
            phone_number=phone_number,
            username=username,
            email=email,
            **extra_fields
        )
        
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('سوپریوزر باید is_staff=True داشته باشد')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('سوپریوزر باید is_superuser=True داشته باشد')
        
        return self.create_user(phone_number, username, email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=11, unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    # OTP fields
    auth_code = models.IntegerField(null=True, blank=True)
    auth_code_created_at = models.DateTimeField(null=True, blank=True)
    auth_attempts = models.IntegerField(default=0)
    auth_locked_until = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
    
    def __str__(self):
        return self.phone_number or self.username or str(self.id)
