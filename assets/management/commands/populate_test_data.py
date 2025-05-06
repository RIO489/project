import random
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from assets.models import Source, VirtualAsset, PriceHistory, ItemActivity

class Command(BaseCommand):
    help = 'Наповнює базу даними тестовими даними'

    def handle(self, *args, **options):
        self.stdout.write('Створення тестових даних...')
        
        # Створення джерел
        sources = []
        source_data = [
            ('Steam', 'https://steamcommunity.com/market'),
            ('OpenSea', 'https://api.opensea.io'),
            ('Binance NFT', 'https://www.binance.com/api/nft'),
        ]
        
        for name, api_url in source_data:
            source, created = Source.objects.get_or_create(
                name=name,
                defaults={'api_url': api_url}
            )
            if created:
                self.stdout.write(f'Створено джерело: {name}')
            sources.append(source)
        
        # Створення віртуальних активів
        assets = []
        asset_data = [
            # Steam items
            (sources[0], 'AK-47 | Redline (Field-Tested)', 'AK-47_Redline_FT', {'wear': 0.15, 'category': 'Rifle', 'rarity': 'Classified'}),
            (sources[0], 'AWP | Asiimov (Field-Tested)', 'AWP_Asiimov_FT', {'wear': 0.23, 'category': 'Sniper Rifle', 'rarity': 'Covert'}),
            (sources[0], 'M4A4 | Howl (Factory New)', 'M4A4_Howl_FN', {'wear': 0.04, 'category': 'Rifle', 'rarity': 'Contraband'}),
            (sources[0], 'Butterfly Knife | Fade (Factory New)', 'Butterfly_Fade_FN', {'wear': 0.01, 'category': 'Knife', 'rarity': 'Covert'}),
            (sources[0], 'Gloves | Crimson Kimono (Field-Tested)', 'Gloves_Crimson_FT', {'wear': 0.20, 'category': 'Gloves', 'rarity': 'Extraordinary'}),
            
            # OpenSea NFTs
            (sources[1], 'Bored Ape Yacht Club #7890', 'BAYC_7890', {'collection': 'Bored Ape Yacht Club', 'traits': ['Blue Background', 'Sailor Hat']}),
            (sources[1], 'CryptoPunk #3100', 'CryptoPunk_3100', {'collection': 'CryptoPunks', 'traits': ['Alien', 'Headband']}),
            (sources[1], 'Art Blocks #532', 'ArtBlocks_532', {'collection': 'Art Blocks', 'artist': 'Tyler Hobbs'}),
            (sources[1], 'Azuki #1234', 'Azuki_1234', {'collection': 'Azuki', 'traits': ['Red Background', 'Leather Jacket']}),
            (sources[1], 'Doodles #9876', 'Doodles_9876', {'collection': 'Doodles', 'traits': ['Rainbow Background', 'Crown']}),
            
            # Binance NFT
            (sources[2], 'Binance Launchpad Token #42', 'BLT_42', {'collection': 'Binance Launchpad', 'edition': '42/100'}),
            (sources[2], 'Binance VIP Card', 'BVIP_Card', {'collection': 'Binance VIP', 'tier': 'Diamond'}),
            (sources[2], 'Binance Anniversary NFT', 'B_Anniv', {'collection': 'Binance Anniversary', 'year': '2022'}),
            (sources[2], 'Cristiano Ronaldo NFT #7', 'CR7_NFT', {'collection': 'CR7', 'rarity': 'Legendary'}),
            (sources[2], 'NBA Top Shot #LeBron Dunk', 'NBA_LeBron', {'collection': 'NBA Top Shot', 'moment': 'Dunk'}),
        ]
        
        for source, name, external_id, metadata in asset_data:
            asset, created = VirtualAsset.objects.get_or_create(
                name=name,
                source=source,
                defaults={
                    'external_id': external_id,
                    'metadata': metadata,
                }
            )
            if created:
                self.stdout.write(f'Створено актив: {name}')
            assets.append(asset)
        
        # Генерація історії цін для кожного активу
        for asset in assets:
            # Визначаємо базову ціну залежно від типу активу
            if asset.source.name == 'Steam':
                if 'Knife' in asset.name or 'Howl' in asset.name:
                    base_price = Decimal(random.uniform(500, 2000))
                elif 'Gloves' in asset.name:
                    base_price = Decimal(random.uniform(200, 800))
                else:
                    base_price = Decimal(random.uniform(10, 200))
            elif asset.source.name == 'OpenSea':
                if 'Bored Ape' in asset.name or 'CryptoPunk' in asset.name:
                    base_price = Decimal(random.uniform(50000, 150000))
                else:
                    base_price = Decimal(random.uniform(1000, 20000))
            else:  # Binance NFT
                base_price = Decimal(random.uniform(100, 5000))
            
            # Оновлюємо поточну ціну для активу
            asset.current_price = base_price
            asset.last_fetched = datetime.datetime.now()
            asset.save()
            
            # Генеруємо історію цін за останні 30 днів
            for day in range(30, 0, -1):
                date = datetime.datetime.now() - datetime.timedelta(days=day)
                
                # Додаємо випадкову зміну до базової ціни
                change_percent = random.uniform(-0.05, 0.05)  # від -5% до +5%
                price = base_price * (1 + change_percent)
                
                # Додаємо тренд - поступове зростання або падіння
                trend_factor = random.uniform(-0.001, 0.003) * day
                price = price * (1 + trend_factor)
                
                # Зберігаємо заокруглену ціну
                price = round(price, 2)
                
                # Оновлюємо базову ціну для наступної ітерації
                base_price = price
                
                # Створюємо запис історії ціни
                PriceHistory.objects.create(
                    asset=asset,
                    price=price,
                    currency='USD',
                    timestamp=date
                )
                
                # Створюємо запис активності (для деяких днів)
                if random.random() > 0.5:  # 50% ймовірність
                    ItemActivity.objects.create(
                        asset=asset,
                        sales_volume=random.randint(1, 10),
                        price=price,
                        timestamp=date
                    )
        
        self.stdout.write(self.style.SUCCESS('Тестові дані успішно створені!'))