# assets/tasks.py (додати в існуючий файл)

from abc import ABC, abstractmethod
import logging
import requests
import redis
from bs4 import BeautifulSoup
from decimal import Decimal
from django.utils import timezone
from celery import shared_task  # Додайте цей рядок
from .models import Source, VirtualAsset, PriceHistory

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Абстрактний базовий клас для всіх парсерів"""
    
    def __init__(self, source):
        self.source = source
    
    @abstractmethod
    def fetch_price(self, asset):
        """Отримати поточну ціну для активу"""
        pass
    
    @abstractmethod
    def fetch_popular_items(self, limit=20):
        """Отримати список популярних предметів"""
        pass
    
    @abstractmethod
    def search_items(self, query):
        """Пошук предметів за запитом"""
        pass

class SteamParser(BaseParser):
    """Парсер для Steam Community Market"""
    
    def fetch_price(self, asset):
        """Отримати ціну для активу Steam"""
        try:
            # Перевіряємо обмеження запитів
            check_request_limit(f"steam_{asset.external_id}")
            
            # Формуємо URL запиту
            url = f"{self.source.api_url}/priceoverview/?currency=1&appid=730&market_hash_name={asset.name}"
            
            # Виконуємо запит
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    # Парсимо ціну з формату "$123.45"
                    price_str = data.get('lowest_price', '0').replace('$', '')
                    price = Decimal(price_str)
                    
                    # Оновлюємо запис активу
                    asset.current_price = price
                    asset.last_fetched = timezone.now()
                    asset.save(update_fields=['current_price', 'last_fetched'])
                    
                    # Додаємо запис в історію цін
                    PriceHistory.objects.create(
                        asset=asset,
                        price=price,
                        currency='USD',
                        timestamp=timezone.now()
                    )
                    
                    logger.info(f"Успішно оновлено ціну для {asset.name}: {price} USD")
                    return price
                else:
                    logger.error(f"Не вдалося отримати ціну для {asset.name}: API повернув помилку")
            else:
                logger.error(f"Не вдалося отримати ціну для {asset.name}: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Помилка при отриманні ціни для {asset.name}: {str(e)}")
        
        return None
    
    def fetch_popular_items(self, limit=20):
        """Отримати список популярних предметів Steam"""
        try:
            # URL для отримання популярних предметів
            url = f"{self.source.api_url}/search/render/?query=&start=0&count={limit}&search_descriptions=0&sort_column=popular&sort_dir=desc&appid=730"
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and data.get('results_html'):
                    # Парсимо HTML результатів
                    soup = BeautifulSoup(data['results_html'], 'html.parser')
                    
                    # Знаходимо всі елементи товарів
                    items = soup.select('.market_listing_row')
                    
                    results = []
                    for item in items:
                        try:
                            name_element = item.select_one('.market_listing_item_name')
                            price_element = item.select_one('.market_listing_price')
                            
                            if name_element and price_element:
                                name = name_element.text.strip()
                                price_text = price_element.text.strip().replace('$', '').replace(',', '')
                                
                                if price_text and price_text != '-':
                                    price = Decimal(price_text)
                                    
                                    # Перевіряємо, чи існує такий актив
                                    asset, created = VirtualAsset.objects.get_or_create(
                                        source=self.source,
                                        name=name,
                                        defaults={
                                            'external_id': name.replace(' ', '_').replace('|', '_'),
                                            'current_price': price,
                                            'last_fetched': timezone.now()
                                        }
                                    )
                                    
                                    # Якщо актив вже існує, оновлюємо ціну
                                    if not created:
                                        asset.current_price = price
                                        asset.last_fetched = timezone.now()
                                        asset.save(update_fields=['current_price', 'last_fetched'])
                                    
                                    # Додаємо запис в історію цін
                                    PriceHistory.objects.create(
                                        asset=asset,
                                        price=price,
                                        currency='USD',
                                        timestamp=timezone.now()
                                    )
                                    
                                    results.append(asset)
                        except Exception as e:
                            logger.error(f"Помилка при обробці предмету: {str(e)}")
                    
                    logger.info(f"Успішно отримано {len(results)} популярних предметів Steam")
                    return results
                else:
                    logger.error("Не вдалося отримати HTML результатів популярних предметів")
            else:
                logger.error(f"Не вдалося отримати популярні предмети: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Помилка при отриманні популярних предметів: {str(e)}")
        
        return []
    
    def search_items(self, query):
        """Пошук предметів Steam за запитом"""
        try:
            # URL для пошуку предметів
            url = f"{self.source.api_url}/search/render/?query={query}&start=0&count=20&search_descriptions=0&sort_column=price&sort_dir=asc&appid=730"
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and data.get('results_html'):
                    # Парсимо HTML результатів
                    soup = BeautifulSoup(data['results_html'], 'html.parser')
                    
                    # Знаходимо всі елементи товарів
                    items = soup.select('.market_listing_row')
                    
                    results = []
                    for item in items:
                        try:
                            name_element = item.select_one('.market_listing_item_name')
                            price_element = item.select_one('.market_listing_price')
                            
                            if name_element and price_element:
                                name = name_element.text.strip()
                                price_text = price_element.text.strip().replace('$', '').replace(',', '')
                                
                                if price_text and price_text != '-':
                                    price = Decimal(price_text)
                                    
                                    results.append({
                                        'name': name,
                                        'price': price,
                                        'source': self.source.name,
                                        'external_id': name.replace(' ', '_').replace('|', '_'),
                                    })
                        except Exception as e:
                            logger.error(f"Помилка при обробці результату пошуку: {str(e)}")
                    
                    logger.info(f"Успішно знайдено {len(results)} предметів Steam за запитом '{query}'")
                    return results
                else:
                    logger.error("Не вдалося отримати HTML результатів пошуку")
            else:
                logger.error(f"Не вдалося виконати пошук: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Помилка при пошуку предметів: {str(e)}")
        
        return []

# Фабрика парсерів
def get_parser(source_name):
    """Повертає відповідний парсер для вказаного джерела"""
    try:
        source = Source.objects.get(name=source_name)
        
        if source_name == 'Steam':
            return SteamParser(source)
        # Тут можна додати інші парсери для різних платформ
        
        logger.error(f"Парсер для джерела '{source_name}' не реалізовано")
        
    except Source.DoesNotExist:
        logger.error(f"Джерело '{source_name}' не знайдено в базі даних")
    
    return None

# Оновлена функція для пошуку еквівалентних предметів
def find_equivalent_items(asset, threshold=0.7):
    """
    Знаходить еквівалентні предмети на інших платформах
    
    :param asset: VirtualAsset для пошуку еквівалентів
    :param threshold: Поріг схожості для нечіткого пошуку (0-1)
    :return: Список знайдених еквівалентних предметів
    """
    # Отримуємо всі джерела, крім поточного
    other_sources = Source.objects.exclude(id=asset.source.id)
    
    # Готуємо варіанти пошукових запитів
    search_queries = [
        asset.name,
        # Спрощені версії назви
        asset.name.split('|')[0].strip() if '|' in asset.name else asset.name,
        asset.name.split('(')[0].strip() if '(' in asset.name else asset.name
    ]
    
    # Видаляємо дублікати
    search_queries = list(set(search_queries))
    
    results = []
    
    for source in other_sources:
        parser = get_parser(source.name)
        
        if not parser:
            continue
        
        for query in search_queries:
            # Пошук предметів на поточній платформі
            found_items = parser.search_items(query)
            
            for item in found_items:
                # Тут можна додати алгоритм нечіткого порівняння назв
                # для визначення подібності предметів
                # Наприклад, використати fuzzywuzzy або інші бібліотеки
                
                # Для простоти зараз просто додаємо всі знайдені предмети
                results.append(item)
    
    return results

# Оновлена функція оновлення цін для всіх активів
@shared_task
def fetch_all_prices():
    """Оновлює ціни для всіх активів"""
    for asset in VirtualAsset.objects.all():
        parser = get_parser(asset.source.name)
        
        if parser:
            parser.fetch_price(asset)
        else:
            # Для джерел без парсера використовуємо стару функцію
            fetch_price_for.delay(asset.id)