# assets/management/commands/populate_test_data.py
class Command(BaseCommand):
    help = 'Наповнює базу тестовими даними'

    def handle(self, *args, **options):
        # Створення джерел (Steam, OpenSea, Binance NFT)
        sources = []
        source_data = [
            ('Steam', 'https://steamcommunity.com/market'),
            ('OpenSea', 'https://api.opensea.io'),
            ('Binance NFT', 'https://www.binance.com/api/nft'),
        ]
        
        # Створення активів різних типів
        for source, name, external_id, metadata in asset_data:
            asset, created = VirtualAsset.objects.get_or_create(
                name=name,
                source=source,
                defaults={
                    'external_id': external_id,
                    'metadata': metadata,
                }
            )
            
        # Генерація історії цін за останні 30 днів
        for asset in assets:
            # Логіка генерації цінової історії...