# Оновлення assets/views.py:
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Max, Min

from .models import Source, VirtualAsset, PriceHistory, ItemActivity
from .serializers import (
    SourceSerializer, 
    VirtualAssetSerializer, 
    VirtualAssetDetailSerializer,
    PriceHistorySerializer
)

# API Views
class SourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer

class VirtualAssetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VirtualAsset.objects.all()
    serializer_class = VirtualAssetSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VirtualAssetDetailSerializer
        return VirtualAssetSerializer
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        asset = self.get_object()
        # Отримання статистики з цінової історії
        price_stats = PriceHistory.objects.filter(asset=asset).aggregate(
            avg_price=Avg('price'),
            max_price=Max('price'),
            min_price=Min('price')
        )
        return Response(price_stats)
    
    @action(detail=False, methods=['get'])
    def compare(self, request):
        # Параметр запиту: ?items=1,2,3
        items_param = request.query_params.get('items', '')
        if not items_param:
            return Response({"error": "No items specified for comparison"}, status=400)
        
        item_ids = [int(id) for id in items_param.split(',') if id.isdigit()]
        items_to_compare = VirtualAsset.objects.filter(id__in=item_ids)
        
        if not items_to_compare:
            return Response({"error": "No valid items found for comparison"}, status=404)
        
        # Підготовка даних для порівняння
        comparison_data = []
        for item in items_to_compare:
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

# Web Views
def asset_list(request):
    assets_list = VirtualAsset.objects.all()
    # Фільтрація та пошук
    source_id = request.GET.get('source')
    if source_id:
        assets_list = assets_list.filter(source_id=source_id)
    
    # Пагінація
    paginator = Paginator(assets_list, 9)
    page_number = request.GET.get('page')
    assets = paginator.get_page(page_number)
    
    sources = Source.objects.all()
    
    return render(request, 'assets/list.html', {'assets': assets, 'sources': sources})

def asset_detail(request, pk):
    asset = get_object_or_404(VirtualAsset, pk=pk)
    price_history = PriceHistory.objects.filter(asset=asset).order_by('-timestamp')[:30]
    
    # Підготовка даних для графіка
    labels = []
    prices = []
    
    for price_record in reversed(price_history):
        labels.append(price_record.timestamp.strftime('%d.%m.%Y'))
        prices.append(float(price_record.price))
    
    return render(request, 'assets/detail.html', {
        'asset': asset,
        'price_history': price_history,
        'chart_labels': labels,
        'chart_prices': prices,
    })

def asset_compare(request):
    item_ids = request.GET.getlist('items')
    if not item_ids:
        assets = VirtualAsset.objects.all()
        return render(request, 'assets/compare.html', {'assets': assets, 'items': None})
    
    items = VirtualAsset.objects.filter(id__in=item_ids)
    
    # Підготовка даних для графіка
    for item in items:
        price_history = PriceHistory.objects.filter(asset=item).order_by('-timestamp')[:30]
        chart_data = [{'x': record.timestamp.strftime('%Y-%m-%d'), 'y': float(record.price)} 
                      for record in reversed(price_history)]
        item.chart_data = chart_data
    
    return render(request, 'assets/compare.html', {'items': items})