-- Optimisation : index et analyse des performances

-- AVANT index : Total Time 0.458s
-- EXPLAIN ANALYZE SELECT * FROM v_customer_features LIMIT 10;

-- Création des index
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(order_status);

-- APRÈS index : Total Time 0.589s
-- Conclusion : DuckDB est un moteur colonnaire analytique.
-- Les Sequential Scans sont sa méthode optimale pour les requêtes analytiques.
-- Les index n'apportent pas de gain sur des full scans.
-- Dans PostgreSQL, ces index auraient amélioré les requêtes filtrées.