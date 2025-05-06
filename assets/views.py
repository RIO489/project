# assets/views.py (додати в існуючий файл)

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .tasks import find_equivalent_items, get_parser

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