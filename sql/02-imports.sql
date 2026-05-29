-- Import des CSV Olist
-- Adapter le chemin selon votre machine

COPY customers FROM 'data/olist_customers_dataset.csv' (HEADER TRUE, DELIMITER ',');
COPY orders FROM 'data/olist_orders_dataset.csv' (HEADER TRUE, DELIMITER ',');
COPY order_items FROM 'data/olist_order_items_dataset.csv' (HEADER TRUE, DELIMITER ',');
COPY order_payments FROM 'data/olist_order_payments_dataset.csv' (HEADER TRUE, DELIMITER ',');
COPY order_reviews FROM 'data/olist_order_reviews_dataset.csv' (HEADER TRUE, DELIMITER ',');
COPY products FROM 'data/olist_products_dataset.csv' (HEADER TRUE, DELIMITER ',');
COPY sellers FROM 'data/olist_sellers_dataset.csv' (HEADER TRUE, DELIMITER ',');
COPY product_category_translation FROM 'data/product_category_name_translation.csv' (HEADER TRUE, DELIMITER ',');

-- Vérification des comptages
SELECT 'customers' as table_name, COUNT(*) as nb_lignes FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL
SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL
SELECT 'product_category_translation', COUNT(*) FROM product_category_translation;