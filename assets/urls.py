# assets/urls.py (оновити існуючий файл)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sources', views.SourceViewSet)
router.register(r'assets', views.VirtualAssetViewSet)

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    path('api/equivalents/<int:asset_id>/', views.find_equivalents, name='api_find_equivalents'),
    path('api/search/', views.search_items, name='api_search_items'),
    path('api/sources/status/', views.source_status, name='api_source_status'),
    
    # Web URLs
    path('', views.dashboard, name='dashboard'),  # Нова головна сторінка
    path('web/assets/', views.asset_list, name='asset_list'),
    path('web/assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('web/compare/', views.asset_compare, name='asset_compare'),
]