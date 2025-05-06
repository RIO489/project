# assets/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sources', views.SourceViewSet)
router.register(r'assets', views.VirtualAssetViewSet)

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Web URLs
    path('web/assets/', views.asset_list, name='asset_list'),
    path('web/assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('web/compare/', views.asset_compare, name='asset_compare'),
]