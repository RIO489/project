"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from assets import views

router = DefaultRouter()
router.register(r'api/assets', views.VirtualAssetViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('assets.urls')),
    path('', RedirectView.as_view(pattern_name='asset_list')),  # Перенаправлення з головної сторінки
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('assets/compare/', views.asset_compare, name='asset_compare'),
]