#!/usr/bin/env python3
"""
Import real-world sales data from JSON files into PostgreSQL database.
This script imports 538,036+ sales transactions and associated reference data.
"""

import json
import psycopg2
import uuid
from datetime import datetime
from decimal import Decimal
import os
import sys

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': '55432',
    'database': 'retailai',
    'user': 'postgres',
    'password': 'postgres'
}

# Data file paths
DATA_DIR = '/home/vboxuser/Documents/140509_ai-oh-wip/140509_01/src/demo/demo-data'
FILES = {
    'categories': f'{DATA_DIR}/categories.json',
    'suppliers': f'{DATA_DIR}/suppliers.json',
    'stores': f'{DATA_DIR}/stores.json',
    'products': f'{DATA_DIR}/products.json',
    'sales_transactions': f'{DATA_DIR}/sales_transactions.json'
}

def connect_db():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def load_json_data(filepath):
    """Load JSON data from file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        sys.exit(1)

def clear_existing_data(conn):
    """Clear existing data from tables (in reverse dependency order)."""
    cursor = conn.cursor()
    
    print("Clearing existing data...")
    
    # Delete in reverse dependency order
    tables_to_clear = [
        'sales_transactions',
        'products', 
        'stores',
        'suppliers',
        'product_categories'
    ]
    
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
            deleted_count = cursor.rowcount
            print(f"  Cleared {deleted_count} rows from {table}")
        except Exception as e:
            print(f"  Warning: Could not clear {table}: {e}")
    
    conn.commit()
    cursor.close()

def import_categories(conn, categories_data):
    """Import product categories."""
    cursor = conn.cursor()
    category_uuid_map = {}
    
    print(f"Importing {len(categories_data)} categories...")
    
    for category in categories_data:
        category_uuid = str(uuid.uuid4())
        category_uuid_map[category['id']] = category_uuid
        
        cursor.execute("""
            INSERT INTO product_categories (id, name, seasonality_factor)
            VALUES (%s, %s, %s)
        """, (
            category_uuid,
            category['name'],
            category['seasonality_factor']
        ))
    
    conn.commit()
    cursor.close()
    print(f"  Imported {len(categories_data)} categories")
    return category_uuid_map

def import_suppliers(conn, suppliers_data):
    """Import suppliers."""
    cursor = conn.cursor()
    supplier_uuid_map = {}
    
    print(f"Importing {len(suppliers_data)} suppliers...")
    
    for supplier in suppliers_data:
        supplier_uuid = str(uuid.uuid4())
        supplier_uuid_map[supplier['id']] = supplier_uuid
        
        cursor.execute("""
            INSERT INTO suppliers (id, name, contact_email, contact_phone, lead_time_days, minimum_order_qty)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            supplier_uuid,
            supplier['name'],
            supplier['contact_email'],
            supplier['contact_phone'],
            supplier['lead_time_days'],
            supplier['minimum_order_qty']
        ))
    
    conn.commit()
    cursor.close()
    print(f"  Imported {len(suppliers_data)} suppliers")
    return supplier_uuid_map

def import_stores(conn, stores_data):
    """Import stores."""
    cursor = conn.cursor()
    store_uuid_map = {}
    
    print(f"Importing {len(stores_data)} stores...")
    
    for store in stores_data:
        store_uuid = str(uuid.uuid4())
        store_uuid_map[store['id']] = store_uuid
        
        cursor.execute("""
            INSERT INTO stores (id, name, address, city, state, zip_code, latitude, longitude, population_density, avg_income)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            store_uuid,
            store['name'],
            store['address'],
            store['city'],
            store['state'],
            store['zip_code'],
            store['latitude'],
            store['longitude'],
            store['population_density'],
            store['avg_income']
        ))
    
    conn.commit()
    cursor.close()
    print(f"  Imported {len(stores_data)} stores")
    return store_uuid_map

def import_products(conn, products_data, category_uuid_map, supplier_uuid_map):
    """Import products."""
    cursor = conn.cursor()
    product_uuid_map = {}
    
    print(f"Importing {len(products_data)} products...")
    
    batch_size = 1000
    for i in range(0, len(products_data), batch_size):
        batch = products_data[i:i+batch_size]
        
        for product in batch:
            product_uuid = str(uuid.uuid4())
            product_uuid_map[product['id']] = product_uuid
            
            # Map category and supplier IDs to UUIDs
            category_uuid = category_uuid_map.get(product['category_id'])
            supplier_uuid = supplier_uuid_map.get(product['supplier_id'])
            
            cursor.execute("""
                INSERT INTO products (id, sku, name, category_id, supplier_id, cost_price, selling_price, weight_kg, dimensions_cm, is_seasonal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                product_uuid,
                product['sku'],
                product['name'],
                category_uuid,
                supplier_uuid,
                product['cost_price'],
                product['selling_price'],
                product['weight_kg'],
                product['dimensions_cm'],
                product['is_seasonal']
            ))
        
        conn.commit()
        print(f"  Imported {i + len(batch)}/{len(products_data)} products")
    
    cursor.close()
    print(f"  Completed importing {len(products_data)} products")
    return product_uuid_map

def import_sales_transactions(conn, sales_data, product_uuid_map, store_uuid_map):
    """Import sales transactions in batches."""
    cursor = conn.cursor()
    
    print(f"Importing {len(sales_data)} sales transactions...")
    
    batch_size = 5000
    imported_count = 0
    skipped_count = 0
    
    for i in range(0, len(sales_data), batch_size):
        batch = sales_data[i:i+batch_size]
        batch_imported = 0
        
        for transaction in batch:
            # Map product and store IDs to UUIDs
            product_uuid = product_uuid_map.get(transaction['product_id'])
            store_uuid = store_uuid_map.get(transaction['store_id'])
            
            if not product_uuid or not store_uuid:
                skipped_count += 1
                continue
            
            # Parse timestamp
            transaction_time = datetime.strptime(transaction['transaction_timestamp'], '%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                INSERT INTO sales_transactions (id, product_id, store_id, quantity, unit_price, total_amount, discount_amount, transaction_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                transaction['id'],  # Use existing UUID from JSON
                product_uuid,
                store_uuid,
                transaction['quantity'],
                transaction['unit_price'],
                transaction['total_amount'],
                transaction['discount_amount'],
                transaction_time
            ))
            batch_imported += 1
        
        conn.commit()
        imported_count += batch_imported
        print(f"  Imported {imported_count}/{len(sales_data)} transactions (skipped: {skipped_count})")
    
    cursor.close()
    print(f"  Completed importing {imported_count} sales transactions (skipped: {skipped_count})")
    return imported_count

def verify_import(conn):
    """Verify the data import by checking record counts."""
    cursor = conn.cursor()
    
    print("\nVerifying import:")
    
    tables = ['product_categories', 'suppliers', 'stores', 'products', 'sales_transactions']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count:,} records")
    
    # Check date range of transactions
    cursor.execute("""
        SELECT MIN(transaction_timestamp) as earliest, MAX(transaction_timestamp) as latest 
        FROM sales_transactions
    """)
    result = cursor.fetchone()
    if result[0] and result[1]:
        print(f"  Transaction date range: {result[0]} to {result[1]}")
    
    # Check total sales amount
    cursor.execute("SELECT SUM(total_amount) FROM sales_transactions")
    total_sales = cursor.fetchone()[0]
    if total_sales:
        print(f"  Total sales amount: ${total_sales:,.2f}")
    
    cursor.close()

def main():
    """Main import function."""
    print("Starting RetailAI sales data import...")
    print(f"Data directory: {DATA_DIR}")
    
    # Verify all files exist
    for name, filepath in FILES.items():
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}")
            sys.exit(1)
        print(f"  Found {name}: {filepath}")
    
    # Connect to database
    conn = connect_db()
    print("Connected to PostgreSQL database")
    
    try:
        # Clear existing data
        clear_existing_data(conn)
        
        # Load JSON data
        print("\nLoading JSON data files...")
        categories_data = load_json_data(FILES['categories'])
        suppliers_data = load_json_data(FILES['suppliers'])
        stores_data = load_json_data(FILES['stores'])
        products_data = load_json_data(FILES['products'])
        sales_data = load_json_data(FILES['sales_transactions'])
        
        print(f"Loaded data summary:")
        print(f"  Categories: {len(categories_data)}")
        print(f"  Suppliers: {len(suppliers_data)}")
        print(f"  Stores: {len(stores_data)}")
        print(f"  Products: {len(products_data)}")
        print(f"  Sales transactions: {len(sales_data)}")
        
        # Import data in dependency order
        print("\nImporting data...")
        category_uuid_map = import_categories(conn, categories_data)
        supplier_uuid_map = import_suppliers(conn, suppliers_data)
        store_uuid_map = import_stores(conn, stores_data)
        product_uuid_map = import_products(conn, products_data, category_uuid_map, supplier_uuid_map)
        imported_transactions = import_sales_transactions(conn, sales_data, product_uuid_map, store_uuid_map)
        
        # Verify import
        verify_import(conn)
        
        print(f"\nImport completed successfully!")
        print(f"Imported {imported_transactions:,} sales transactions from {len(sales_data):,} records")
        
    except Exception as e:
        print(f"Error during import: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()