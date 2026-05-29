-- Phase 2 : Features basiques par client
-- Agrégations simples (GROUP BY, COUNT, SUM, AVG)
-- On utilise customer_unique_id et non customer_id
-- pour éviter les doublons de clients multi-commandes

SELECT 
    c.customer_unique_id,
    COUNT(DISTINCT o.order_id) as nb_commandes,
    SUM(oi.price + oi.freight_value) as montant_total,
    AVG(oi.price + oi.freight_value) as panier_moyen,
    MIN(o.order_purchase_timestamp) as premiere_commande,
    MAX(o.order_purchase_timestamp) as derniere_commande
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_unique_id
LIMIT 10;

-- Phase 3 : Window Functions

-- Feature Tendance : évolution du panier entre commandes successives (LAG)
WITH commandes_client AS (
    SELECT 
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        SUM(oi.price + oi.freight_value) as montant_commande
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id, o.order_id, o.order_purchase_timestamp
)
SELECT 
    customer_unique_id,
    order_id,
    order_purchase_timestamp,
    montant_commande,
    LAG(montant_commande) OVER (
        PARTITION BY customer_unique_id 
        ORDER BY order_purchase_timestamp
    ) as montant_commande_precedente,
    montant_commande - LAG(montant_commande) OVER (
        PARTITION BY customer_unique_id 
        ORDER BY order_purchase_timestamp
    ) as evolution_panier
FROM commandes_client;

-- Feature Rang : classement des clients par montant total (RANK)
SELECT 
    customer_unique_id,
    montant_total,
    RANK() OVER (ORDER BY montant_total DESC) as rang_client
FROM (
    SELECT 
        c.customer_unique_id,
        SUM(oi.price + oi.freight_value) as montant_total
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
) sub;

-- Grande CTE finale : 6 features consolidées par client
-- Récence, Fréquence, Montant, Tendance, Satisfaction, Diversité

WITH date_ref AS (
    SELECT MAX(order_purchase_timestamp) as ref_date 
    FROM orders
),

features_base AS (
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) as nb_commandes,
        DATEDIFF('day', MAX(o.order_purchase_timestamp), (SELECT ref_date FROM date_ref)) as recence_jours,
        SUM(oi.price + oi.freight_value) as montant_total,
        AVG(oi.price + oi.freight_value) as panier_moyen
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),

features_tendance AS (
    SELECT 
        customer_unique_id,
        AVG(evolution_panier) as tendance_panier_moyen
    FROM (
        SELECT 
            c.customer_unique_id,
            montant_commande - LAG(montant_commande) OVER (
                PARTITION BY c.customer_unique_id 
                ORDER BY o.order_purchase_timestamp
            ) as evolution_panier
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN (
            SELECT order_id, SUM(price + freight_value) as montant_commande
            FROM order_items
            GROUP BY order_id
        ) oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
    ) t
    GROUP BY customer_unique_id
),

features_satisfaction AS (
    SELECT 
        c.customer_unique_id,
        AVG(r.review_score) as score_moyen,
        COUNT(CASE WHEN r.review_score <= 2 THEN 1 END) * 100.0 / COUNT(*) as pct_reviews_negatives
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_reviews r ON o.order_id = r.order_id
    GROUP BY c.customer_unique_id
),

features_diversite AS (
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT p.product_category_name) as nb_categories
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)

SELECT 
    b.customer_unique_id,
    b.nb_commandes,
    b.recence_jours,
    b.montant_total,
    b.panier_moyen,
    COALESCE(t.tendance_panier_moyen, 0) as tendance_panier_moyen,
    COALESCE(s.score_moyen, 0) as score_moyen,
    COALESCE(s.pct_reviews_negatives, 0) as pct_reviews_negatives,
    COALESCE(d.nb_categories, 0) as nb_categories
FROM features_base b
LEFT JOIN features_tendance t ON b.customer_unique_id = t.customer_unique_id
LEFT JOIN features_satisfaction s ON b.customer_unique_id = s.customer_unique_id
LEFT JOIN features_diversite d ON b.customer_unique_id = d.customer_unique_id;