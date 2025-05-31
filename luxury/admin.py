from django.contrib import admin
from .models import LuxuryBranch,Worker,Product,Transaction,ScannedItem,Service,BookedService,Booking,SpaProduct,SPATransaction,SPAScannedItem


class ProductAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.upload_image_to_supabase()


admin.site.register(Product, ProductAdmin)
admin.site.register(SpaProduct)
admin.site.register(LuxuryBranch)
admin.site.register(Worker)
# admin.site.register(Product)
admin.site.register(Transaction)
admin.site.register(ScannedItem)
admin.site.register(Service)
class BookedServiceInline(admin.TabularInline):
    model = BookedService
    extra = 1  # how many blank BookedService forms to show

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    inlines = [BookedServiceInline]


class SPAScannedItemInline(admin.TabularInline):
    model = SPAScannedItem
    extra = 1
   
@admin.register(SPATransaction)
class SPATransactionAdmin(admin.ModelAdmin):
    list_display = ('staff', 'timestamp', 'subtotal', 'discount', 'customer_name', 'customer_contact', 'code')
    inlines = [SPAScannedItemInline]
    search_fields = ['code', 'staff__user__username', 'customer_name']
    list_filter = ['timestamp', 'staff']