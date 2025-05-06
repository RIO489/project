# assets/serializers.py
from rest_framework import serializers
from .models import Source, VirtualAsset, PriceHistory, ItemActivity

class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ['id', 'name', 'api_url']

class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ['id', 'price', 'currency', 'timestamp']

class VirtualAssetSerializer(serializers.ModelSerializer):
    source_name = serializers.ReadOnlyField(source='source.name')
    
    class Meta:
        model = VirtualAsset
        fields = ['id', 'name', 'external_id', 'source', 'source_name', 
                 'current_price', 'last_fetched', 'metadata']

class VirtualAssetDetailSerializer(serializers.ModelSerializer):
    price_history = PriceHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = VirtualAsset
        fields = ['id', 'name', 'external_id', 'source', 'source_name', 
                 'current_price', 'last_fetched', 'metadata', 'price_history']