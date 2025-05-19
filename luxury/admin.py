from django.contrib import admin
from .models import LuxuryBranch,Worker,Product,Transaction,ScannedItem,Service,BookedService,Booking


class ProductAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.upload_image_to_supabase()


admin.site.register(Product, ProductAdmin)
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
