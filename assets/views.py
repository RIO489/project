from django.shortcuts import render

# Create your views here.
# Додаємо до assets/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Max, Min
from .serializers import SourceSerializer, VirtualAssetSerializer, VirtualAssetDetailSerializer

class VirtualAssetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VirtualAsset.objects.all()
    serializer_class = VirtualAssetSerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VirtualAssetDetailSerializer
        return VirtualAssetSerializer
    
    @action(detail=False, methods=['get'])
    def compare(self, request):
        # Endpoint для порівняння активів
        items_param = request.query_params.get('items', '')
        if not items_param:
            return Response({"error": "No items specified"}, status=400)
        
        item_ids = [int(id) for id in items_param.split(',') if id.isdigit()]
        items = VirtualAsset.objects.filter(id__in=item_ids)
        
        # Збір даних для порівняння
        comparison_data = []
        for item in items:
            price_history = PriceHistory.objects.filter(asset=item).order_by('-timestamp')[:30]
            
            item_data = {
                'id': item.id,
                'name': item.name,
                'source': item.source.name,
                'current_price': item.current_price,
                'price_history': PriceHistorySerializer(price_history, many=True).data
            }
            comparison_data.append(item_data)
        
        return Response(comparison_data)