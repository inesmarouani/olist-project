import os
import streamlit as st

st.set_page_config(page_title="Olist Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
.block-container { padding-top: 0.5rem !important; }
[data-testid="stSidebarCollapsedControl"] { display: flex !important; visibility: visible !important; }
section[data-testid="stSidebar"] { display: flex !important; visibility: visible !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
.kpi-card { border-radius:10px; padding:1rem 1.2rem; color:white; display:flex; align-items:center; justify-content:space-between; margin-bottom:0.8rem; }
.kpi-label { font-size:0.68rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; opacity:0.85; margin-bottom:4px; }
.kpi-value { font-size:1.6rem; font-weight:700; line-height:1F; }
.kpi-icon { font-size:1.8rem; opacity:0.7; }
.card { background:#fff; border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,0.08); margin-bottom:1rem; overflow:hidden; }
.card-header { padding:0.6rem 1rem; border-bottom:1px solid #f0f4f8; }
.card-title { font-size:0.72rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:#4a5568; }
.card-body { padding:0.4rem; }
            section[data-testid="stSidebar"] {
    display: flex !important;
    visibility: visible !important;
}
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
}
</style>
""", unsafe_allow_html=True)

try:
    import duckdb
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError as e:
    st.error(f"Module manquant : {e}")
    st.stop()

DB_PATH = os.environ.get(
    "OLIST_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "olist.db")
)

@st.cache_data
def load_features():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("SELECT * FROM v_customer_features").df()
    con.close()
    return df

@st.cache_data
def load_timeline():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT YEAR(order_purchase_timestamp) as annee,
               DATE_TRUNC('month', order_purchase_timestamp) as mois,
               COUNT(*) as nb_commandes,
               SUM(oi.price + oi.freight_value) as revenus
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1,2 ORDER BY 2
    """).df()
    con.close()
    return df

@st.cache_data
def load_geo():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT c.customer_state as etat,
               COUNT(DISTINCT c.customer_unique_id) as nb_clients,
               AVG(oi.price + oi.freight_value) as panier_moyen
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1 ORDER BY nb_clients DESC
    """).df()
    con.close()
    return df

@st.cache_data
def load_reviews():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT review_score, COUNT(*) as count
        FROM order_reviews WHERE review_score IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """).df()
    con.close()
    return df

@st.cache_data
def load_payments():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT payment_type, COUNT(*) as count, SUM(payment_value) as total
        FROM order_payments GROUP BY 1 ORDER BY count DESC
    """).df()
    con.close()
    return df

@st.cache_data
def load_top_sellers():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT oi.seller_id, s.seller_state,
               COUNT(DISTINCT o.order_id) as nb_commandes,
               SUM(oi.price) as revenus,
               AVG(r.review_score) as score_moyen
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN sellers s ON oi.seller_id = s.seller_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1,2 ORDER BY revenus DESC LIMIT 10
    """).df()
    con.close()
    return df

@st.cache_data
def load_categories():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') as categorie,
               COUNT(DISTINCT o.order_id) as nb_commandes,
               SUM(oi.price) as revenus
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
        WHERE o.order_status = 'delivered'
        GROUP BY 1 ORDER BY nb_commandes DESC LIMIT 15
    """).df()
    con.close()
    return df

try:
    df_all = load_features()
    timeline = load_timeline()
    geo = load_geo()
    reviews = load_reviews()
    payments = load_payments()
    top_sellers = load_top_sellers()
    cats = load_categories()
except Exception as e:
    st.error(f"Erreur chargement : {e}")
    st.stop()

def segment_rfm(row):
    r = row['recence_jours'] < 90
    f = row['nb_commandes'] > 1
    v = row['montant_total'] > 200
    if r and f and v:    return "Champion"
    elif r and (f or v): return "Fidele"
    elif r:              return "Nouveau"
    elif not r and f:    return "En danger"
    elif row['recence_jours'] > 300: return "Perdu"
    else:                return "A risque"

df_all['segment'] = df_all.apply(segment_rfm, axis=1)
SEG_COLORS = {"Champion":"#10b981","Fidele":"#3b82f6","Nouveau":"#6366f1",
              "En danger":"#f59e0b","A risque":"#f97316","Perdu":"#ef4444"}

PLOT = dict(plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=10,b=10,l=10,r=10),
            font=dict(family="Inter", size=11), showlegend=False)

# ══════════════════════════
# SIDEBAR
# ══════════════════════════
with st.sidebar:
    st.image("https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/1f6d2.svg", width=40)
    st.markdown("## Olist Analytics")
    st.markdown("*E-commerce · Brasil*")
    st.markdown("---")

    st.markdown("#### Filtres")
    annees = sorted(timeline['annee'].unique().tolist())
    annees_sel = st.multiselect("Années", annees, default=annees)

    seuil = st.slider("Seuil churn (jours)", 30, 365, 180, 30)

    st.markdown("---")
    st.caption(f"Dataset : {len(df_all):,} clients\nPériode : 2016–2018")

# Filtres
if not annees_sel:
    annees_sel = annees
tl = timeline[timeline['annee'].isin(annees_sel)]
df = df_all.copy()

# ══════════════════════════
# MAIN
# ══════════════════════════

# Header
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("### 🛒 Olist Dashboard")
    st.caption("E-commerce Company · Brasil · 10/1/2016 to 8/30/2018")
with col_h2:
    st.markdown(f"**Seuil churn :** {seuil}j &nbsp; | &nbsp; **Années :** {', '.join(map(str, annees_sel))}")

st.divider()

# ── KPIs ──
total_rev = tl['revenus'].sum()
total_orders = int(tl['nb_commandes'].sum())
churn_pct = len(df[df['recence_jours'] > seuil]) / len(df) * 100
avg_score = (reviews['review_score'] * reviews['count']).sum() / reviews['count'].sum()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class="kpi-card" style="background:linear-gradient(135deg,#11998e,#38ef7d)">
        <div><div class="kpi-label">Total Revenue</div><div class="kpi-value">R${total_rev/1e6:.2f}M</div></div>
        <div class="kpi-icon">📊</div></div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="kpi-card" style="background:linear-gradient(135deg,#4776e6,#8e54e9)">
        <div><div class="kpi-label">Total Customers</div><div class="kpi-value">{len(df):,}</div></div>
        <div class="kpi-icon">👥</div></div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="kpi-card" style="background:linear-gradient(135deg,#f7971e,#ffd200)">
        <div><div class="kpi-label">Total Orders</div><div class="kpi-value">{total_orders:,}</div></div>
        <div class="kpi-icon">🛒</div></div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class="kpi-card" style="background:linear-gradient(135deg,#ff416c,#ff4b2b)">
        <div><div class="kpi-label">Churn Rate</div><div class="kpi-value">{churn_pct:.1f}%</div></div>
        <div class="kpi-icon">⚠️</div></div>""", unsafe_allow_html=True)

# ── ROW 2 : Timeline + Reviews ──
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Commandes & Revenus par mois</span></div><div class="card-body">', unsafe_allow_html=True)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=tl['mois'], y=tl['nb_commandes'], name="Commandes",
                         marker_color="#38bdf8", opacity=0.8), secondary_y=False)
    fig.add_trace(go.Scatter(x=tl['mois'], y=tl['revenus'], name="Revenus",
                             line=dict(color="#f97316", width=2.5), mode='lines+markers',
                             marker=dict(size=4)), secondary_y=True)
    fig.update_layout(**{**PLOT, 'height': 260, 'showlegend': True,
        'legend': dict(orientation='h', y=-0.15, font=dict(size=10)),
        'xaxis': dict(showgrid=False),
        'yaxis': dict(showgrid=True, gridcolor="#f0f4f8"),
        'yaxis2': dict(showgrid=False)})
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Review Scores</span></div><div class="card-body">', unsafe_allow_html=True)
    REVIEW_COLORS = {1:"#ef4444",2:"#f97316",3:"#f59e0b",4:"#84cc16",5:"#10b981"}
    fig2 = px.pie(reviews, values='count', names='review_score',
                  color='review_score', color_discrete_map=REVIEW_COLORS, hole=0.6)
    fig2.update_layout(**{**PLOT, 'height': 240, 'showlegend': True,
        'legend': dict(orientation='v', font=dict(size=10), x=1, y=0.5),
        'annotations': [dict(text=f"<b>{avg_score:.2f}</b>", x=0.5, y=0.5,
                              font_size=22, showarrow=False, font_color="#1e2d40")]})
    fig2.update_traces(textinfo='percent', textfont_size=9)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ── ROW 3 : Top States + Top Sellers ──
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Top States</span></div><div class="card-body">', unsafe_allow_html=True)
    fig = px.bar(geo.head(10), x='etat', y='nb_clients',
                 color='panier_moyen', color_continuous_scale='teal',
                 text='nb_clients',
                 labels={"etat":"","nb_clients":"Clients"})
    fig.update_traces(texttemplate='%{text:,}', textposition='outside', textfont_size=9)
    fig.update_layout(**{**PLOT, 'height': 260,
        'xaxis': dict(showgrid=False),
        'yaxis': dict(showgrid=True, gridcolor="#f0f4f8"),
        'coloraxis_showscale': False})
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Top Sellers</span></div><div class="card-body" style="padding:0.8rem">', unsafe_allow_html=True)
    ts = top_sellers.head(8).copy()
    ts['seller_id'] = ts['seller_id'].str[:10] + "..."
    ts['revenus'] = ts['revenus'].apply(lambda x: f"R${x:,.0f}")
    ts['score_moyen'] = ts['score_moyen'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
    ts.columns = ["Seller ID","State","Orders","Revenue","Score"]
    ts = ts.reset_index(drop=True)
    ts.index += 1
    st.dataframe(ts, use_container_width=True, height=240)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ── ROW 4 : RFM Scatter + Payment Types ──
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Segmentation RFM & Churn</span></div><div class="card-body">', unsafe_allow_html=True)
    df_s = df.sample(min(5000, len(df)), random_state=42)
    fig = px.scatter(df_s, x="recence_jours", y="montant_total",
                     color="segment", color_discrete_map=SEG_COLORS, opacity=0.4,
                     labels={"recence_jours":"Recence (j)","montant_total":"Montant (R$)","segment":""})
    fig.add_vline(x=seuil, line_dash="dash", line_color="#ef4444",
                  annotation_text=f"Churn > {seuil}j", annotation_font_size=10)
    fig.update_layout(**{**PLOT, 'height': 240, 'showlegend': True,
        'legend': dict(orientation='h', y=-0.2, font=dict(size=10)),
        'xaxis': dict(showgrid=True, gridcolor="#f0f4f8"),
        'yaxis': dict(showgrid=True, gridcolor="#f0f4f8")})
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Payment Types</span></div><div class="card-body">', unsafe_allow_html=True)
    PAY_COLORS = {"credit_card":"#4776e6","boleto":"#11998e","voucher":"#f7971e","debit_card":"#ff416c","not_defined":"#94a3b8"}
    pct_cc = payments[payments['payment_type']=='credit_card']['count'].sum() / payments['count'].sum() * 100
    fig2 = px.pie(payments, values='count', names='payment_type',
                  color='payment_type', color_discrete_map=PAY_COLORS, hole=0.6)
    fig2.update_layout(**{**PLOT, 'height': 220, 'showlegend': True,
        'legend': dict(orientation='v', font=dict(size=9), x=1, y=0.5),
        'annotations': [dict(text=f"<b>{pct_cc:.0f}%</b>",
                              x=0.5, y=0.5, font_size=18, showarrow=False, font_color="#1e2d40")]})
    fig2.update_traces(textinfo='none')
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ── ROW 5 : Categories + Top Customers ──
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Top Categories</span></div><div class="card-body">', unsafe_allow_html=True)
    fig = px.bar(cats.head(12), x='nb_commandes', y='categorie', orientation='h',
                 color='revenus', color_continuous_scale='Greens',
                 labels={"nb_commandes":"Commandes","categorie":""})
    fig.update_layout(**{**PLOT, 'height': 300,
        'yaxis': dict(showgrid=False, autorange='reversed'),
        'xaxis': dict(showgrid=True, gridcolor="#f0f4f8"),
        'margin': dict(t=10,b=10,l=170,r=30),
        'coloraxis_showscale': False})
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card"><div class="card-header"><span class="card-title">Top Customers</span></div><div class="card-body" style="padding:0.8rem">', unsafe_allow_html=True)
    top_c = df.nlargest(8, "montant_total")[["customer_unique_id","segment","nb_commandes","montant_total","recence_jours"]].copy()
    top_c["customer_unique_id"] = top_c["customer_unique_id"].str[:12] + "..."
    top_c.columns = ["Customer","Segment","Orders","Revenue (R$)","Recence (j)"]
    top_c = top_c.reset_index(drop=True)
    top_c.index += 1
    st.dataframe(top_c, use_container_width=True, height=280)
    st.markdown('</div></div>', unsafe_allow_html=True)