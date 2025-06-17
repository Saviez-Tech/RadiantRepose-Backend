from django.contrib import admin
from .models import BuyersInfo, Order,ContactMessage,NewsletterSubscriber

class OrderInline(admin.TabularInline):
    model = Order
    extra = 0

@admin.register(BuyersInfo)
class BuyersInfoAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'city', 'state', 'country']
    inlines = [OrderInline]


admin.site.register(NewsletterSubscriber)
admin.site.register(ContactMessage)