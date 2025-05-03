from django.contrib import admin
from .models import LuxuryBranch,Worker,Product,Transaction,ScannedItem


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
