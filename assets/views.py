# assets/views.py (додати в існуючий файл)

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .tasks import find_equivalent_items, get_parser

from rest_framework import viewsets
from .models import Source, VirtualAsset
from .serializers import SourceSerializer, VirtualAssetSerializer, VirtualAssetDetailSerializer

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Source, VirtualAsset, PriceHistory
from django.utils import timezone
import json


def asset_list(request):
    """View for displaying list of virtual assets with filtering and pagination"""
    # Get all assets
    assets_query = VirtualAsset.objects.all().order_by('name')
    sources = Source.objects.all()
    
    # Apply filters
    search_query = request.GET.get('search', '')
    source_filter = request.GET.get('source', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    
    if search_query:
        assets_query = assets_query.filter(name__icontains=search_query)
    
    if source_filter:
        assets_query = assets_query.filter(source_id=source_filter)
    
    if min_price:
        assets_query = assets_query.filter(current_price__gte=min_price)
    
    if max_price:
        assets_query = assets_query.filter(current_price__lte=max_price)
    
    # Pagination
    paginator = Paginator(assets_query, 9)  # 9 assets per page
    page_number = request.GET.get('page', 1)
    assets = paginator.get_page(page_number)
    
    return render(request, 'assets/list.html', {
        'assets': assets,
        'sources': sources,
    })

def asset_detail(request, pk):
    """View for displaying details of a specific virtual asset"""
    asset = get_object_or_404(VirtualAsset, pk=pk)
    price_history = asset.price_history.all()[:30]  # Last 30 price records
    
    # Prepare chart data
    chart_labels = []
    chart_prices = []
    

    
    for record in reversed(list(price_history)):
        chart_labels.append(record.timestamp.strftime('%Y-%m-%d'))
        chart_prices.append(float(record.price))
    
    return render(request, 'assets/detail.html', {
        'asset': asset,
        'price_history': price_history,
        'chart_labels': json.dumps(chart_labels),
        'chart_prices': json.dumps(chart_prices),
    })

def asset_compare(request):
    """View for comparing multiple virtual assets"""
    assets = VirtualAsset.objects.all().order_by('name')
    items = []
    
    # Get selected items for comparison
    item_ids = request.GET.getlist('items')
    if item_ids:
        for item_id in item_ids:
            try:
                asset = VirtualAsset.objects.get(id=item_id)
                
                # Get price history for chart
                price_history = asset.price_history.all().order_by('timestamp')[:30]
                chart_data = []
                
                for record in price_history:
                    chart_data.append({
                        'x': record.timestamp.strftime('%Y-%m-%d'),
                        'y': float(record.price)
                    })
                
                asset.chart_data = json.dumps(chart_data)
                items.append(asset)
            except VirtualAsset.DoesNotExist:
                continue
    
    return render(request, 'assets/compare.html', {
        'assets': assets,
        'items': items,
    })

# Add these ViewSet classes
class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer

class VirtualAssetViewSet(viewsets.ModelViewSet):
    queryset = VirtualAsset.objects.all()
    serializer_class = VirtualAssetSerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VirtualAssetDetailSerializer
        return VirtualAssetSerializer

# Додаємо представлення для головної сторінки
def dashboard(request):
    # Отримуємо основні дані для дашборду
    recent_assets = VirtualAsset.objects.all().order_by('-last_fetched')[:10]
    sources = Source.objects.all()
    
    # Отримуємо статистику за останні 30 днів
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    
    return render(request, 'dashboard.html', {
        'recent_assets': recent_assets,
        'sources': sources
    })

# Функція для пошуку еквівалентних предметів
@require_http_methods(["GET"])
def find_equivalents(request, asset_id):
    try:
        asset = VirtualAsset.objects.get(pk=asset_id)
        equivalents = find_equivalent_items(asset)
        
        return JsonResponse({
            'success': True,
            'asset': {
                'id': asset.id,
                'name': asset.name,
                'source': asset.source.name,
                'price': float(asset.current_price) if asset.current_price else None
            },
            'equivalents': equivalents
        })
    except VirtualAsset.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Asset not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Функція для пошуку предметів за запитом
@require_http_methods(["GET"])
def search_items(request):
    query = request.GET.get('q', '')
    source_id = request.GET.get('source', None)
    
    if not query:
        return JsonResponse({
            'success': False,
            'error': 'Query parameter is required'
        }, status=400)
    
    results = []
    
    try:
        if source_id:
            # Пошук в одному джерелі
            try:
                source = Source.objects.get(pk=source_id)
                parser = get_parser(source.name)
                
                if parser:
                    source_results = parser.search_items(query)
                    results.extend(source_results)
            except Source.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Source not found'
                }, status=404)
        else:
            # Пошук у всіх джерелах
            for source in Source.objects.all():
                parser = get_parser(source.name)
                
                if parser:
                    source_results = parser.search_items(query)
                    results.extend(source_results)
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Функція для оновлення статусу джерел
@require_http_methods(["GET"])
def source_status(request):
    try:
        sources = []
        
        for source in Source.objects.all():
            # Отримуємо статистику для джерела
            asset_count = VirtualAsset.objects.filter(source=source).count()
            
            # Визначаємо статус джерела
            # Тут можна реалізувати логіку перевірки доступності API
            status = 'active'  # За замовчуванням вважаємо активним
            
            # Знаходимо час останнього оновлення
            last_updated = VirtualAsset.objects.filter(source=source).order_by('-last_fetched').first()
            last_updated_time = last_updated.last_fetched if last_updated else None
            
            sources.append({
                'id': source.id,
                'name': source.name,
                'status': status,
                'asset_count': asset_count,
                'last_updated': last_updated_time.isoformat() if last_updated_time else None
            })
        
        return JsonResponse({
            'success': True,
            'sources': sources
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)