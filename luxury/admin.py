from django.contrib import admin
from .models import LuxuryBranch,Worker,Product,Transaction,ScannedItem
# Register your models here.


admin.site.register(LuxuryBranch)
admin.site.register(Worker)
admin.site.register(Product)
admin.site.register(Transaction)
admin.site.register(ScannedItem)
