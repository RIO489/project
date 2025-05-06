from django.db import models

class Source(models.Model):
    name    = models.CharField(max_length=100)
    api_url = models.URLField()

    def __str__(self):
        return self.name

class VirtualAsset(models.Model):
    source       = models.ForeignKey(Source, on_delete=models.CASCADE)
    external_id  = models.CharField(max_length=100)
    name         = models.CharField(max_length=200)
    metadata     = models.JSONField(default=dict, blank=True)

    # Додаткові поля для ціни та часу
    current_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    last_fetched = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.source.name})"

class PriceHistory(models.Model):
    asset = models.ForeignKey(VirtualAsset, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    timestamp = models.DateTimeField()  # Час запису ціни

    class Meta:
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        # Спочатку зберігаємо запис історії ціни
        super().save(*args, **kwargs)
        
        # Оновлюємо поточну ціну активу
        self.asset.current_price = self.price
        self.asset.last_fetched = self.timestamp
        self.asset.save(update_fields=['current_price', 'last_fetched'])
        
class ItemActivity(models.Model):
    asset = models.ForeignKey(VirtualAsset, on_delete=models.CASCADE, related_name='activity')
    sales_volume = models.IntegerField()  # Кількість проданих одиниць
    price = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField()  # Час запису активності

    class Meta:
        ordering = ['-timestamp']
