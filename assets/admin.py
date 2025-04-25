from django.contrib import admin
from .models import Source, VirtualAsset, PriceHistory, ItemActivity

admin.site.register(Source)
admin.site.register(VirtualAsset)
admin.site.register(PriceHistory)
admin.site.register(ItemActivity)