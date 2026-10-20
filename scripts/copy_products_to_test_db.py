import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RadiantRepose.test_settings')

import django

django.setup()

import dj_database_url
from decouple import config
from django.core.management import call_command
from django.db import connections, transaction

from luxury.models import LuxuryBranch, Product


def main():
    parser = argparse.ArgumentParser(
        description='Copy a small product snapshot from DATABASE_URL into isolated db.sqlite.'
    )
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be at least 1')

    target_database = Path(connections.databases['default']['NAME'])
    if target_database.exists():
        raise SystemExit(
            f'{target_database} already exists; refusing to overwrite the test database.'
        )

    source_database = {
        **connections.databases['default'],
        **dj_database_url.parse(config('DATABASE_URL')),
    }
    source_database['OPTIONS'] = dict(source_database.get('OPTIONS', {}))
    if source_database['ENGINE'].endswith('postgresql'):
        options = source_database.setdefault('OPTIONS', {})
        options['options'] = (
            f"{options.get('options', '')} -c default_transaction_read_only=on"
        ).strip()
    connections.databases['source'] = source_database

    try:
        products = list(
            Product.objects.using('source')
            .select_related('branch')
            .order_by('pk')[:args.limit]
        )
        if not products:
            raise SystemExit('The source database returned no products to copy.')

        branches = {}
        for product in products:
            source_branch = product.branch
            branches[source_branch.pk] = {
                'name': f'Test branch {len(branches) + 1}',
                'location': 'Local test fixture',
                'contact_number': '0000000000',
            }

        call_command('migrate', database='default', interactive=False, verbosity=0)

        with transaction.atomic(using='default'):
            destination_branches = {
                source_id: LuxuryBranch.objects.create(**branch_data)
                for source_id, branch_data in branches.items()
            }
            for product in products:
                Product.objects.create(
                    name=product.name,
                    image_url=product.image_url,
                    category=product.category,
                    description=product.description,
                    price=product.price,
                    stock_quantity=product.stock_quantity,
                    barcode=product.barcode,
                    branch=destination_branches[product.branch_id],
                )
    finally:
        connections['source'].close()

    print(f'Copied {len(products)} products into {target_database}.')


if __name__ == '__main__':
    main()
