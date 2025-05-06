import logging
import requests
from decimal import Decimal
from datetime import datetime
from datetime import timedelta
import redis
from celery import shared_task
from bs4 import BeautifulSoup
from .models import VirtualAsset, PriceHistory, ItemActivity,Source

logger = logging.getLogger(__name__)

# Підключення до Redis
r = redis.StrictRedis(host='localhost', port=6379, db=0)

def check_request_limit(item_name):
    # Використовуємо ім'я елемента як унікальний ключ для обмеження запитів
    key = f"request_count:{item_name}"
    current_time = datetime.now()

    # Встановлюємо час закінчення ліміту (наприклад, 1 година)
    time_limit = current_time - timedelta(hours=1)

    # Отримуємо кількість запитів за останню годину
    request_count = r.get(key)

    if request_count and int(request_count.decode()) >= 60:  # 60 запитів на годину, наприклад
        # Якщо ліміт перевищено, викидаємо помилку
        raise Exception(f"Request limit exceeded for {item_name}")

    # Якщо ліміт не перевищено, збільшуємо лічильник
    r.incr(key)
    r.expire(key, timedelta(hours=1))  # Встановлюємо час закінчення ліміту на 1 годину


@shared_task
def fetch_price_for(asset_id):
    """
    Цей таск бере один VirtualAsset по його ID,
    звертається до його source.api_url + external_id,
    і створює новий PriceRecord у уніфікованому форматі.
    """
    try:
        asset = VirtualAsset.objects.get(pk=asset_id)
    except VirtualAsset.DoesNotExist:
        logger.error(f"Asset #{asset_id} not found, skipping")
        return

    url_price = f"{asset.source.api_url}/market/pricehistory/?appid=730&market_hash_name={asset.name}"
    url_activity = f"{asset.source.api_url}/market/itemordersactivity?item_name={asset.name}"

    logger.info(f"Fetching price and activity data for {asset.name}")

    try:
        resp_price = requests.get(url_price, timeout=10)
        resp_activity = requests.get(url_activity, timeout=10)
    except Exception as e:
        logger.error(f"Request to API failed: {e}")
        return

    if resp_price.status_code == 200:
        price_data = resp_price.json()
        if 'success' in price_data and price_data['success']:
            price = Decimal(price_data['prices'][0][1])  # Отримуємо першу ціну з історії
            PriceHistory.objects.create(
                asset=asset,
                price=price,
                currency=price_data['price_suffix'],
                timestamp=datetime.utcfromtimestamp(price_data['prices'][0][0])
            )
            logger.info(f"Price recorded for {asset.name}: {price}")
        else:
            logger.error(f"Failed to fetch price data for {asset.name}")
    else:
        logger.error(f"Failed to fetch price history for {asset.name}")

    if resp_activity.status_code == 200:
        activity_data = resp_activity.json()
        if 'success' in activity_data and activity_data['success']:
            sales_volume = activity_data['activity'][0][2]  # Кількість проданих одиниць
            price = Decimal(activity_data['activity'][0][1])  # Поточна ціна
            ItemActivity.objects.create(
                asset=asset,
                sales_volume=sales_volume,
                price=price,
                timestamp=datetime.utcfromtimestamp(activity_data['activity'][0][0])
            )
            logger.info(f"Activity recorded for {asset.name}: {sales_volume} units sold")
        else:
            logger.error(f"Failed to fetch activity data for {asset.name}")
    else:
        logger.error(f"Failed to fetch activity for {asset.name}")

    # Оновлюємо останню отриману ціну в VirtualAsset
    asset.current_price = price
    asset.last_fetched = datetime.now()
    asset.save(update_fields=['current_price', 'last_fetched'])

def fetch_price_from_api(item_name):
    try:
        check_request_limit(item_name)
        # Виконуємо запит до API
        # Наприклад, Steam API
        url = f"https://steamcommunity.com/market/itemordersactivity?item_name={item_name}"
        response = requests.get(url)
        # Обробляємо відповідь від API
        return response.json()
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

import requests
from bs4 import BeautifulSoup

def get_item_nameid_from_listing_page(url, appid):
    """
    Отримуємо item_nameid зі сторінки Steam, фільтруючи за appid (730 для CS2, 430 для TF2).
    """
    try:
        # Відправляємо GET-запит до сторінки
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to load page, status code: {response.status_code}")

        # Парсимо HTML сторінки
        soup = BeautifulSoup(response.text, 'html.parser')

        # Шукаємо всі елементи з атрибутом data-appid, який відповідає одному з двох значень
        item_nameid = None
        items = soup.find_all(attrs={"data-appid": appid})
        
        if not items:
            print(f"No items found for appid={appid}")
            return None

        for item in items:
            # Шукаємо item_nameid всередині елемента
            try:
                item_nameid = item.get("data-item_nameid")
                if item_nameid:
                    return item_nameid
            except AttributeError:
                continue

        return None

    except Exception as e:
        print(f"Error parsing item_nameid: {str(e)}")
        return None


@shared_task
def fetch_popular_items(appid, max_pages=10):
    """
    Цей task отримує популярні товари з Steam для заданого appid (наприклад, для TF2 або CS:GO),
    парсить їх і зберігає в базі даних.
    """
    for page_number in range(1, max_pages + 1):
        url = f"https://steamcommunity.com/market/search?appid={appid}#p{page_number}_popular_asc"
        logger.info(f"Fetching page {page_number} from {url}")

        try:
            response = requests.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch page {page_number}, status code {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Парсимо всі елементи на сторінці
            page_items = soup.find_all('div', class_='market_listing_row')
            for item in page_items:
                item_name = item.get('data-hash-name')
                item_appid = item.get('data-appid')

                # Перевіряємо, чи цей елемент відповідає потрібному appid
                if item_appid in ['730', '440']:  # CS:GO або TF2
                    source, created = Source.objects.get_or_create(
                        api_url=f"https://steamcommunity.com/market/search?appid={appid}",
                        defaults={'name': 'Steam'}
                    )

                    # Перевірка на наявність предмета в базі
                    existing_item = VirtualAsset.objects.filter(
                        name=item_name, source=source
                    ).first()

                    if not existing_item:
                        # Якщо предмет не існує в базі, додаємо його
                        VirtualAsset.objects.create(
                            name=item_name,
                            source=source
                        )
                        logger.info(f"Added new item: {item_name}")
            
        except Exception as e:
            logger.error(f"Error while fetching page {page_number}: {e}")

    logger.info("Finished fetching and saving popular items.")



@shared_task
def fetch_all_prices():
    for asset in VirtualAsset.objects.all():
        fetch_price_for.delay(asset.id)