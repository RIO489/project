# myproject/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
# Підтягуємо налаштування CELERY_* із settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')
# Автоматично знаходимо tasks.py у всіх INSTALLED_APPS
app.autodiscover_tasks()
