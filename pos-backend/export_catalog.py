import sqlite3
import csv
import sys

def main():
    conn = sqlite3.connect('pos_dev.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            c.name,
            p.brand_name,
            p.manufacturer,
            s.name,
            s.selling_price,
            s.buying_price,
            s.stock_qty
        FROM skus s
        LEFT JOIN products p ON s.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
    """)
    writer = csv.writer(sys.stdout)
    writer.writerow(['Category', 'Brand', 'Manufacturer', 'SKU Name', 'Selling Price', 'Buying Price', 'Stock Qty'])
    for row in cursor.fetchall():
        writer.writerow(['' if v is None else v for v in row])

if __name__ == '__main__':
    main()
