# Olist — Base Analytique Churn Prediction

## Contexte

Olist est une marketplace brésilienne qui connecte des petits commerçants à des clients finaux. Ce projet construit une base analytique complète pour répondre à la question :

> **Quels clients vont churner dans les 90 prochains jours, et quels signaux comportementaux les distinguent des clients fidèles ?**

Le dataset couvre ~100 000 commandes passées entre 2016 et 2018.

## Technologies

- **DuckDB v1.5.3** — base de données analytique
- **Python 3.10+** — dashboard
- **Streamlit** — visualisation
- **Plotly** — graphiques interactifs
- **Dataset** : [Olist Brazilian E-Commerce (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/TON_USERNAME/olist-project.git
cd olist-project
```

### 2. Télécharger les données

Télécharger le dataset depuis [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) et placer les CSV dans un dossier `data/`.

### 3. Créer la base DuckDB

```bash
duckdb olist.db
```

Puis exécuter les scripts dans l'ordre :

```sql
.read '01-schema.sql'
.read '02-imports.sql'
.read '03-nettoyage.sql'
.read '05-vue-finale.sql'
.read '06-optimisation.sql'
```

### 4. Lancer le dashboard

```bash
pip install streamlit duckdb pandas plotly
streamlit run dashboard.py
```

## Schéma de la base

![Schéma ERD](schema.png)

## Scripts SQL

| Fichier | Description |
|---------|-------------|
| `01-schema.sql` | Création des 8 tables avec types et contraintes |
| `02-imports.sql` | Import des CSV + vérification des comptages |
| `03-nettoyage.sql` | Correction des anomalies identifiées |
| `04-features.sql` | Feature engineering (agrégations, CTEs, Window Functions) |
| `05-vue-finale.sql` | Création de la vue `v_customer_features` |
| `06-optimisation.sql` | Index + résultats EXPLAIN ANALYZE |

## Features construites — `v_customer_features`

| Feature | Description | Pertinence churn |
|---------|-------------|-----------------|
| `nb_commandes` | Nombre total de commandes | Fréquence RFM — un client qui n'achète qu'une fois est à risque |
| `recence_jours` | Jours depuis la dernière commande | Récence RFM — signal principal du churn |
| `montant_total` | Valeur totale dépensée | Montant RFM — les clients à forte valeur méritent plus d'attention |
| `panier_moyen` | Panier moyen par commande | Valeur unitaire — baisse du panier = signal de désengagement |
| `tendance_panier_moyen` | Evolution du panier entre commandes successives (LAG) | Signal de désengagement progressif |
| `score_moyen` | Score moyen des reviews | Satisfaction — un client insatisfait churne plus vite |
| `pct_reviews_negatives` | % de reviews avec score ≤ 2 | Insatisfaction chronique |
| `nb_categories` | Nombre de catégories distinctes achetées | Diversité — plus un client explore, plus il est engagé |

## Anomalies identifiées et traitées

| # | Anomalie | Nb lignes | Décision |
|---|----------|-----------|----------|
| 1 | Commandes `delivered` sans date de livraison | 8 | Laissées NULL — non corrigeables sans données externes |
| 2 | Commandes `canceled` avec date de livraison | 6 | Date mise à NULL — incohérence corrigée |
| 3 | Produits sans catégorie | 610 | Remplacés par `'unknown'` |
| 4 | Commandes sans items associés | 775 | Exclues via filtre `WHERE` dans les features |
| 5 | Commandes sans paiement | 1 | Exclue naturellement via JOIN |

## Segmentation RFM

Les clients sont segmentés en 6 groupes basés sur Récence, Fréquence et Montant :

| Segment | Critères | Action recommandée |
|---------|----------|-------------------|
| **Champion** | Récent + fréquent + valeur élevée | Fidéliser, programme VIP |
| **Fidele** | Récent + fréquent ou valeur élevée | Upsell, cross-sell |
| **Nouveau** | Récent, 1 commande | Onboarding, 2ème achat |
| **En danger** | Pas récent mais fréquent | Campagne de rétention urgente |
| **A risque** | Inactif, historique moyen | Email de réactivation |
| **Perdu** | Inactif > 300 jours | Campagne win-back ou abandon |

## Optimisation

- **Index créés** : `idx_orders_customer_id`, `idx_orders_status`
- **Résultat** : DuckDB est un moteur colonnaire — les Sequential Scans sont sa méthode optimale. Les index n'améliorent pas les full scans analytiques (temps : 0.458s → 0.589s après index). Dans PostgreSQL, ces index auraient bénéficié aux requêtes filtrées.

## Dashboard

Le dashboard Streamlit expose la vue `v_customer_features` avec :
- KPIs : revenus, clients, commandes, taux de churn
- Evolution mensuelle des commandes et revenus
- Segmentation RFM interactive
- Distribution de la récence avec seuil de churn ajustable
- Top states, top sellers, top customers
- Review scores et payment types

**Filtres sidebar** : années, seuil de churn, nombre de top clients.