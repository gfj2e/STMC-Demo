from django.contrib import admin
from .models import FloorPlanModel, ExteriorRateCard, Branch, UpgradeItem

# Register your models here.
@admin.register(ExteriorRateCard)
class ExteriorRateCardAdmin(admin.ModelAdmin):
    list_display = ("label", "category", "rate", "unit")
    list_filter = ("category",)
    search_fields = ("label", "key")
    
