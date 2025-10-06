from django.contrib import admin
from .models import Transaction, SubscriptionPlan, Subscription, SubscriptionTransaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'status', 'trans_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__phone_number', 'trans_id', 'card_num', 'factor_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_days', 'price', 'currency', 'is_active', 'created_at']
    list_filter = ['is_active', 'currency']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'start_date', 'end_date', 'is_active']
    list_filter = ['plan', 'start_date', 'end_date']
    search_fields = ['user__phone_number', 'plan__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'


@admin.register(SubscriptionTransaction)
class SubscriptionTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'plan', 'amount', 'status', 'created_at']
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['user__phone_number', 'plan__name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
