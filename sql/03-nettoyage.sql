-- Anomalie 1 : 8 commandes 'delivered' sans date de livraison
-- Décision : laisser NULL, cas non corrigeable sans données externes
SELECT COUNT(*) FROM orders 
WHERE order_status = 'delivered' 
AND order_delivered_customer_date IS NULL;

-- Anomalie 2 : 6 commandes 'canceled' avec date de livraison incorrecte
-- Décision : mettre la date à NULL, la commande est annulée
UPDATE orders 
SET order_delivered_customer_date = NULL 
WHERE order_status = 'canceled' 
AND order_delivered_customer_date IS NOT NULL;

-- Anomalie 3 : 610 produits sans catégorie
-- Décision : remplacer NULL par 'unknown'
UPDATE products 
SET product_category_name = 'unknown' 
WHERE product_category_name IS NULL;

-- Anomalie 4 : 775 commandes sans items associés
-- Décision : exclusion via filtre WHERE dans les requêtes features, pas de suppression
-- car ces commandes peuvent avoir d'autres statuts légitimes

-- Anomalie 5 : 1 commande sans paiement associé
-- Décision : exclusion naturelle via JOIN sur order_payments dans les features

-- Anomalie 6 : fautes de frappe dans les noms de villes
-- Décision : non corrigées, nécessiterait un référentiel officiel des villes brésiliennes
-- Impact faible sur les features ML (ville non utilisée comme feature)