"""
Dashboard Interactivo -- Competitive Intelligence Rappi Mexico
==============================================================
Uso: streamlit run dashboard.py

Carga el JSON mas reciente de data/ y presenta metricas comparativas.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -- Config ---
st.set_page_config(
    page_title="CI Rappi Mexico",
    page_icon=":truck:",
    layout="wide",
    initial_sidebar_state="expanded",
)

PLATFORM_COLORS = {"rappi": "#FF441F", "ubereats": "#06C167", "didifood": "#FF6B00"}
PLATFORM_NAMES = {"rappi": "Rappi", "ubereats": "Uber Eats", "didifood": "DiDi Food"}
SERVICE_FEES = {"rappi": 10, "ubereats": 15, "didifood": 8}
ALL_PLATS = ["rappi", "ubereats", "didifood"]


# -- Load data ---
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    rows = []
    for r in raw:
        for plat in ALL_PLATS:
            if plat not in r:
                continue
            p = r[plat]
            if p.get("status") not in ("success", "partial"):
                continue
            prods = {pr["name"]: pr for pr in p.get("products", [])}
            combo = prods.get("Combo Big Mac mediano", {})
            hdq   = prods.get("Hamburguesa doble con queso", {})
            coke  = prods.get("Coca-Cola mediana", {})
            rows.append({
                "address_id":        r["address_id"],
                "city":              r.get("city", ""),
                "zone":              r.get("zone", ""),
                "zone_type":         r.get("zone_type", ""),
                "platform":          plat,
                "platform_name":     PLATFORM_NAMES.get(plat, plat),
                "restaurant_name":   p.get("restaurant_name", ""),
                "rating":            p.get("rating"),
                "eta_min":           p.get("eta_min"),
                "delivery_fee":      p.get("delivery_fee"),
                "review_count":      p.get("review_count"),
                "promo_general_pct": p.get("promo_general_pct"),
                "combo_orig":        combo.get("price_original"),
                "combo_disc":        combo.get("price_discounted"),
                "combo_disc_pct":    combo.get("discount_pct"),
                "hdq_orig":          hdq.get("price_original"),
                "hdq_disc":          hdq.get("price_discounted"),
                "hdq_disc_pct":      hdq.get("discount_pct"),
                "coke_orig":         coke.get("price_original"),
                "coke_disc":         coke.get("price_discounted"),
                "coke_disc_pct":     coke.get("discount_pct"),
                "subtotal":          p.get("subtotal"),
                "service_fee_est":   p.get("service_fee_estimated"),
                "total_estimated":   p.get("total_estimated"),
            })

    df = pd.DataFrame(rows)
    num_cols = ["rating", "eta_min", "delivery_fee", "review_count",
                "promo_general_pct",
                "combo_orig", "combo_disc", "combo_disc_pct",
                "hdq_orig", "hdq_disc", "hdq_disc_pct",
                "coke_orig", "coke_disc", "coke_disc_pct",
                "subtotal", "service_fee_est", "total_estimated"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def find_data_files():
    data_dir = Path("data")
    files = sorted(data_dir.glob("competitive_data_*.json"), reverse=True)
    real = [f for f in files if "mock" not in f.name]
    mock = [f for f in files if "mock" in f.name]
    return real + mock


# -- Sidebar ---
st.sidebar.title("CI Rappi Mexico")
st.sidebar.markdown("**Competitive Intelligence Dashboard**")

data_files = find_data_files()
if not data_files:
    st.error("No hay datos en data/. Ejecuta primero el scraper o genera datos mock.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Dataset",
    data_files,
    format_func=lambda x: f"{'[MOCK] ' if 'mock' in x.name else ''}{x.name}"
)

df = load_data(str(selected_file))
available_plats = [p for p in ALL_PLATS if p in df["platform"].values]

selected_plats = st.sidebar.multiselect(
    "Plataformas",
    available_plats,
    default=available_plats,
    format_func=lambda x: PLATFORM_NAMES.get(x, x)
)

if not selected_plats:
    st.warning("Selecciona al menos una plataforma")
    st.stop()

df = df[df["platform"].isin(selected_plats)]

cities = sorted(df["city"].unique())
if len(cities) > 1:
    selected_cities = st.sidebar.multiselect("Ciudades", cities, default=cities)
    df = df[df["city"].isin(selected_cities)]

zone_types = sorted(df["zone_type"].dropna().unique())
if len(zone_types) > 1:
    selected_zones = st.sidebar.multiselect("Tipo de zona", zone_types, default=zone_types)
    df = df[df["zone_type"].isin(selected_zones)]

st.sidebar.markdown("---")
st.sidebar.metric("Direcciones", df["address_id"].nunique())
st.sidebar.metric("Registros", len(df))

color_map = {PLATFORM_NAMES[p]: PLATFORM_COLORS[p] for p in selected_plats}

# -- Header ---
st.title("Competitive Intelligence -- Rappi Mexico")
st.caption(f"Dataset: {selected_file.name} | {df['address_id'].nunique()} direcciones | "
           f"{len(selected_plats)} plataformas")

# -- KPI row ---
st.markdown("### KPIs principales")
kpi_cols = st.columns(len(selected_plats))
for col, plat in zip(kpi_cols, selected_plats):
    sub = df[df["platform"] == plat]
    with col:
        st.markdown(f"**{PLATFORM_NAMES[plat]}**")
        c1, c2 = st.columns(2)
        reviews = sub["review_count"].mean()
        eta = sub["eta_min"].mean()
        rating = sub["rating"].mean()
        total = sub["total_estimated"].mean()
        promo = sub["promo_general_pct"].mean()

        c1.metric("Reviews", f"{reviews:,.0f}" if pd.notna(reviews) else "N/D")
        c2.metric("ETA", f"{eta:.0f} min" if pd.notna(eta) else "N/D")
        c1.metric("Rating", f"{rating:.1f}" if pd.notna(rating) else "N/D")
        c2.metric("Promo max", f"{promo:.0f}%" if pd.notna(promo) else "N/D")
        st.metric("Total estimado", f"${total:.0f}" if pd.notna(total) else "N/D")

st.markdown("---")

# -- Charts ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Precios", "Promos", "Engagement", "Operacional", "Costos", "Geografia"
])


# -- Tab 1: Precios ---
with tab1:
    st.subheader("Comparativa de precios de producto")

    # Build long-form price data
    price_rows = []
    for _, row in df.iterrows():
        pname = PLATFORM_NAMES[row["platform"]]
        for prod, orig, disc in [
            ("Combo Big Mac", "combo_orig", "combo_disc"),
            ("Hamburguesa DQ", "hdq_orig", "hdq_disc"),
            ("Coca-Cola med.", "coke_orig", "coke_disc"),
        ]:
            if pd.notna(row[orig]):
                price_rows.append({"Plataforma": pname, "Producto": prod,
                                   "Tipo": "Original", "Precio": row[orig]})
            if pd.notna(row[disc]):
                price_rows.append({"Plataforma": pname, "Producto": prod,
                                   "Tipo": "Con descuento", "Precio": row[disc]})

    if price_rows:
        pdf = pd.DataFrame(price_rows)
        fig = px.bar(pdf, x="Producto", y="Precio", color="Plataforma",
                     barmode="group", facet_col="Tipo",
                     color_discrete_map=color_map,
                     title="Precios originales vs con descuento",
                     labels={"Precio": "MXN"})
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    # Price table
    st.subheader("Tabla de precios promedio")
    price_table = []
    for plat in selected_plats:
        sub = df[df["platform"] == plat]
        price_table.append({
            "Plataforma": PLATFORM_NAMES[plat],
            "Combo Big Mac (orig)": f"${sub['combo_orig'].mean():.0f}" if sub["combo_orig"].notna().any() else "N/D",
            "Combo Big Mac (disc)": f"${sub['combo_disc'].mean():.0f}" if sub["combo_disc"].notna().any() else "N/D",
            "HDQ (orig)": f"${sub['hdq_orig'].mean():.0f}" if sub["hdq_orig"].notna().any() else "N/D",
            "HDQ (disc)": f"${sub['hdq_disc'].mean():.0f}" if sub["hdq_disc"].notna().any() else "N/D",
            "Coca-Cola (orig)": f"${sub['coke_orig'].mean():.0f}" if sub["coke_orig"].notna().any() else "N/D",
            "Coca-Cola (disc)": f"${sub['coke_disc'].mean():.0f}" if sub["coke_disc"].notna().any() else "N/D",
        })
    st.dataframe(pd.DataFrame(price_table), use_container_width=True, hide_index=True)


# -- Tab 2: Promos ---
with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Promo general del restaurante")
        promo_data = df.groupby("platform_name")["promo_general_pct"].mean().reset_index()
        promo_data.columns = ["Plataforma", "Descuento max %"]
        fig = px.bar(promo_data, x="Plataforma", y="Descuento max %",
                     color="Plataforma", color_discrete_map=color_map,
                     title="Hook visible al entrar al restaurante")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Descuentos por producto")
        disc_rows = []
        for plat in selected_plats:
            sub = df[df["platform"] == plat]
            for prod, col_name in [
                ("Combo Big Mac", "combo_disc_pct"),
                ("HDQ", "hdq_disc_pct"),
                ("Coca-Cola", "coke_disc_pct"),
            ]:
                pct_with = sub[col_name].notna().mean() * 100
                disc_rows.append({
                    "Plataforma": PLATFORM_NAMES[plat],
                    "Producto": prod,
                    "% zonas con descuento": pct_with,
                })
        disc_df = pd.DataFrame(disc_rows)
        fig = px.bar(disc_df, x="Producto", y="% zonas con descuento", color="Plataforma",
                     barmode="group", color_discrete_map=color_map,
                     title="% zonas donde el producto tiene descuento")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


# -- Tab 3: Engagement ---
with tab3:
    st.subheader("Review Count por plataforma")
    rev_plat = df.groupby("platform_name")["review_count"].mean().reset_index()
    rev_plat.columns = ["Plataforma", "Reviews (promedio)"]
    fig = px.bar(rev_plat, x="Plataforma", y="Reviews (promedio)",
                 color="Plataforma", color_discrete_map=color_map,
                 title="Promedio de reviews por plataforma")
    fig.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Reviews by city
    if df["city"].nunique() > 1:
        st.subheader("Reviews por ciudad")
        rev_city = df.groupby(["city", "platform_name"])["review_count"].mean().reset_index()
        rev_city.columns = ["Ciudad", "Plataforma", "Reviews (promedio)"]
        fig = px.bar(rev_city, x="Ciudad", y="Reviews (promedio)", color="Plataforma",
                     barmode="group", color_discrete_map=color_map,
                     title="Reviews promedio por ciudad y plataforma")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Reviews by zone type
    if df["zone_type"].nunique() > 1:
        st.subheader("Reviews por tipo de zona")
        rev_zone = df.groupby(["zone_type", "platform_name"])["review_count"].mean().reset_index()
        rev_zone.columns = ["Tipo de zona", "Plataforma", "Reviews (promedio)"]
        fig = px.bar(rev_zone, x="Tipo de zona", y="Reviews (promedio)", color="Plataforma",
                     barmode="group", color_discrete_map=color_map,
                     title="Reviews promedio por tipo de zona y plataforma")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


# -- Tab 4: Operacional (ETA + Rating) ---
with tab4:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("ETA promedio por plataforma")
        eta_data = df.groupby("platform_name")["eta_min"].mean().reset_index()
        eta_data.columns = ["Plataforma", "ETA (min)"]
        fig = px.bar(eta_data, x="Plataforma", y="ETA (min)",
                     color="Plataforma", color_discrete_map=color_map,
                     title="Tiempo estimado de entrega")
        fig.add_hline(y=30, line_dash="dash", line_color="red",
                      annotation_text="SLA 30 min")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Rating promedio")
        rat_data = df.groupby("platform_name")["rating"].mean().reset_index()
        rat_data.columns = ["Plataforma", "Rating"]
        fig = px.bar(rat_data, x="Plataforma", y="Rating",
                     color="Plataforma", color_discrete_map=color_map,
                     title="Rating de McDonald's")
        fig.update_layout(showlegend=False, height=400)
        fig.update_yaxes(range=[3.0, 5.0])
        st.plotly_chart(fig, use_container_width=True)

    # ETA by city if multiple cities
    if df["city"].nunique() > 1:
        st.subheader("ETA por ciudad")
        eta_city = df.groupby(["city", "platform_name"])["eta_min"].mean().reset_index()
        eta_city.columns = ["Ciudad", "Plataforma", "ETA (min)"]
        fig = px.bar(eta_city, x="Ciudad", y="ETA (min)", color="Plataforma",
                     barmode="group", color_discrete_map=color_map)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


# -- Tab 5: Costos (Service Fee + Total) ---
with tab5:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Service Fee %")
        svc_data = pd.DataFrame([
            {"Plataforma": PLATFORM_NAMES[p], "Service Fee %": SERVICE_FEES.get(p, 10)}
            for p in selected_plats
        ])
        fig = px.bar(svc_data, x="Plataforma", y="Service Fee %",
                     color="Plataforma", color_discrete_map=color_map,
                     title="Service Fee estimado")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Total All-in")
        total_data = df.groupby("platform_name")["total_estimated"].mean().reset_index()
        total_data.columns = ["Plataforma", "Total (MXN)"]
        fig = px.bar(total_data, x="Plataforma", y="Total (MXN)",
                     color="Plataforma", color_discrete_map=color_map,
                     title="Costo total estimado")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)


# -- Tab 6: Geografia ---
with tab6:
    if df["zone"].nunique() > 1:
        # Total price by zone (replaces delivery fee by zone)
        st.subheader("Precio total por zona")
        total_zone = df.groupby(["zone", "zone_type", "platform_name"])["total_estimated"].mean().reset_index()
        total_zone.columns = ["Zona", "Tipo", "Plataforma", "Total (MXN)"]
        fig = px.bar(total_zone, x="Total (MXN)", y="Zona", color="Plataforma",
                     barmode="group", color_discrete_map=color_map,
                     orientation="h", title="Precio total por zona y plataforma")
        fig.update_layout(height=max(400, len(df["zone"].unique()) * 35))
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)

        # Promo % by zone
        st.subheader("Promo % por zona")
        promo_zone = df.groupby(["zone", "zone_type", "platform_name"])["promo_general_pct"].mean().reset_index()
        promo_zone.columns = ["Zona", "Tipo", "Plataforma", "Promo %"]
        fig = px.bar(promo_zone, x="Promo %", y="Zona", color="Plataforma",
                     barmode="group", color_discrete_map=color_map,
                     orientation="h", title="Promo % por zona y plataforma")
        fig.update_layout(height=max(400, len(df["zone"].unique()) * 35))
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Se necesitan mas zonas para el analisis geografico. Ejecuta el scraper con mas direcciones.")

    # Radar chart
    if len(selected_plats) >= 2:
        st.subheader("Posicionamiento multidimensional")
        cats = ["ETA", "Service Fee", "Precio Combo", "Promo %", "Reviews"]

        fig = go.Figure()
        raw_vals = {}
        for p in selected_plats:
            sub = df[df["platform"] == p]
            eta = sub["eta_min"].mean()
            svc = SERVICE_FEES.get(p, 10)
            combo = sub["combo_orig"].mean()
            promo = 100 - (sub["promo_general_pct"].mean() if sub["promo_general_pct"].notna().any() else 0)
            # Reviews: inverted so high review count = low value (closer to center = better)
            rev = sub["review_count"].mean()
            rev_inv = (1.0 / rev) * 1000 if pd.notna(rev) and rev > 0 else 0
            raw_vals[p] = [
                eta if pd.notna(eta) else 0,
                svc,
                combo if pd.notna(combo) else 0,
                promo,
                rev_inv,
            ]

        # Normalize 0-1
        arr = np.array([raw_vals[p] for p in selected_plats])
        mn, mx = arr.min(0), arr.max(0)
        denom = np.where(mx - mn == 0, 1, mx - mn)

        for p in selected_plats:
            norm = ((np.array(raw_vals[p]) - mn) / denom).tolist()
            fig.add_trace(go.Scatterpolar(
                r=norm + [norm[0]],
                theta=cats + [cats[0]],
                fill="toself",
                name=PLATFORM_NAMES[p],
                line_color=PLATFORM_COLORS[p],
                opacity=0.7,
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1.1])),
            showlegend=True,
            title="Mapa competitivo (mas cerca del centro = mas competitivo)",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)


# -- Raw data ---
st.markdown("---")
with st.expander("Ver datos crudos"):
    st.dataframe(df, use_container_width=True, height=400)
    csv = df.to_csv(index=False)
    st.download_button("Descargar CSV", csv, "competitive_data.csv", "text/csv")
