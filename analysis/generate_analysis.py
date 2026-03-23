"""
Analisis Competitivo -- Rappi Mexico
=====================================
Genera 7 charts accionables + stats de consola.
Robusto: funciona con 1 o N plataformas, 1 o 50 direcciones.

Ejes de analisis:
  1. Price Positioning (precios orig vs disc por producto y plataforma)
  2. Operacional: ETA + Rating + Review Count
  3. Discount Depth (% descuento promedio por producto por plataforma)
  4. Promotional Strategy (hook % + % zonas con descuento + profundidad)
  5. Geographic Competitiveness (total price por ciudad, zone_type)
  6. Market Engagement (review count por plataforma y ciudad)
  7. Radar multidimensional (sin delivery fee, con review count)

Uso: python analysis/generate_analysis.py
     python analysis/generate_analysis.py --mock   (forzar datos mock)
"""

import argparse, json, os, sys, warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# -- Setup --
os.chdir(Path(__file__).parent.parent)
Path("output").mkdir(exist_ok=True)

C = {
    "rappi":      "#FF441F",
    "ubereats":   "#06C167",
    "didifood":   "#FF6B00",
    "wealthy":    "#2E4057",
    "nonwealthy": "#E84855",
    "bg":         "#FAFAFA",
    "grid":       "#E8E8E8",
    "dark":       "#1A1A2E",
    "gray":       "#666666",
}
PL = {"rappi": "Rappi", "ubereats": "Uber Eats", "didifood": "DiDi Food"}
ALL_PLATS = ["rappi", "ubereats", "didifood"]
SERVICE_FEE_RATES = {"rappi": 10, "ubereats": 15, "didifood": 8}

plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "white"})


# -- Load data ----------------------------------------------------------------

def load_data(force_mock=False) -> pd.DataFrame:
    candidates = sorted(Path("data").glob("competitive_data_*.json"), reverse=True)
    if not candidates:
        raise FileNotFoundError("No data in data/. Run: python scraper/generate_mock_data.py")

    if force_mock:
        mocks = [c for c in candidates if "mock" in c.name]
        path = mocks[0] if mocks else candidates[0]
    else:
        real = [c for c in candidates if "mock" not in c.name]
        path = real[0] if real else candidates[0]

    print(f"[data] {path.name}")
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


def get_active_plats(df):
    """Return only platforms that have data in the DataFrame."""
    present = [p for p in ALL_PLATS if p in df["platform"].values]
    return present, [C[p] for p in present], [PL[p] for p in present]


def safe_max(values, default=100):
    valid = [v for v in values if pd.notna(v) and v > 0]
    return max(valid) if valid else default


# -- Style helpers -------------------------------------------------------------

def ax_style(ax, title="", ylabel=""):
    ax.set_facecolor(C["bg"])
    ax.grid(axis="y", color=C["grid"], lw=0.8, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(C["grid"])
    ax.spines["bottom"].set_color(C["grid"])
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8, color=C["dark"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9, color=C["gray"])


def bar_labels(ax, bars, fmt="${}"):
    for bar in bars:
        h = bar.get_height()
        if pd.notna(h) and h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                    fmt.format(f"{h:.0f}"), ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color=C["dark"])


# -- Chart 1: Price Positioning ------------------------------------------------

def chart1_price_positioning(df):
    """3 products: original vs discounted price, grouped by platform."""
    plats, colors, labels = get_active_plats(df)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor("white")

    products = [
        ("combo_orig", "combo_disc", "Combo Big Mac mediano"),
        ("hdq_orig",   "hdq_disc",   "Hamburguesa doble con queso"),
        ("coke_orig",  "coke_disc",  "Coca-Cola mediana"),
    ]

    for ax, (orig_col, disc_col, title) in zip(axes, products):
        x = np.arange(len(plats))
        w = 0.35
        orig_means = [df[df["platform"] == p][orig_col].mean() for p in plats]
        disc_means = [df[df["platform"] == p][disc_col].mean() for p in plats]

        bars_o = ax.bar(x - w/2, orig_means, w,
                        color=[c + "55" for c in colors],
                        zorder=3, edgecolor="white", label="Precio original")
        bars_d = ax.bar(x + w/2, disc_means, w,
                        color=colors,
                        zorder=3, edgecolor="white", label="Con descuento")

        for bar, val in zip(bars_o, orig_means):
            if pd.notna(val):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        f"${val:.0f}", ha="center", va="bottom",
                        fontsize=7.5, color=C["gray"])
        for bar, val in zip(bars_d, disc_means):
            if pd.notna(val):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        f"${val:.0f}", ha="center", va="bottom",
                        fontsize=7.5, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax_style(ax, title=title, ylabel="MXN")
        all_vals = orig_means + disc_means
        ax.set_ylim(0, safe_max(all_vals) * 1.35)

    axes[0].legend(fontsize=8, framealpha=0)
    plt.suptitle("Insight 1 -- Price Positioning: precio original vs con descuento",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart1_price_positioning.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart1_price_positioning.png")


# -- Chart 2: Operational (ETA + Rating + Review Count) ------------------------

def chart2_operational(df):
    """ETA by city, rating, and review count -- three subplots."""
    plats, colors, labels = get_active_plats(df)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.patch.set_facecolor("white")

    # --- ETA by city ---
    ax = axes[0]
    cities = df["city"].unique()
    if len(cities) == 0:
        cities = [""]
    x = np.arange(len(cities))
    w = 0.8 / max(len(plats), 1)
    for i, (p, c) in enumerate(zip(plats, colors)):
        vals = [df[(df["platform"] == p) & (df["city"] == city)]["eta_min"].mean()
                for city in cities]
        bars = ax.bar(x + i*w, vals, w, color=c, label=PL[p],
                      zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            if pd.notna(val):
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.3,
                        f"{val:.0f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(30, color=C["nonwealthy"], lw=1.2, ls="--", alpha=0.7)
    ax.text(len(cities) - 0.3, 31, "SLA 30 min",
            fontsize=7.5, color=C["nonwealthy"])
    ax.set_xticks(x + w * len(plats) / 2)
    ax.set_xticklabels(
        [c.replace("Ciudad de Mexico", "CDMX") for c in cities], fontsize=9)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="ETA promedio por ciudad", ylabel="Minutos")
    ax.set_ylim(0, 55)

    # --- Rating ---
    ax = axes[1]
    means = [df[df["platform"] == p]["rating"].mean() for p in plats]
    bars = ax.bar(labels, means, color=colors, width=0.5,
                  zorder=3, edgecolor="white")
    for bar, val in zip(bars, means):
        if pd.notna(val):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.01,
                    f"* {val:.1f}", ha="center", va="bottom",
                    fontsize=10, fontweight="bold")
    ax_style(ax, title="Rating promedio de McDonald's", ylabel="Estrellas")
    valid_ratings = [m for m in means if pd.notna(m)]
    if valid_ratings:
        ax.set_ylim(min(valid_ratings) - 0.5, 5.0)
    else:
        ax.set_ylim(3.0, 5.0)

    # --- Review Count ---
    ax = axes[2]
    rev_means = [df[df["platform"] == p]["review_count"].mean() for p in plats]
    bars = ax.bar(labels, rev_means, color=colors, width=0.5,
                  zorder=3, edgecolor="white")
    for bar, val in zip(bars, rev_means):
        if pd.notna(val) and val > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.5,
                    f"{val:,.0f}", ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color=C["dark"])
    ax_style(ax, title="Review count promedio", ylabel="Reviews")
    ax.set_ylim(0, safe_max(rev_means) * 1.4)

    plt.suptitle("Insight 2 -- Operacional: ETA, Rating y Reviews",
                 fontsize=12, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart2_operational.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart2_operational.png")


# -- Chart 3: Discount Depth --------------------------------------------------

def chart3_discount_depth(df):
    """Average discount % per product per platform."""
    plats, colors, labels = get_active_plats(df)

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("white")

    product_info = {
        "Combo Big Mac":  "combo_disc_pct",
        "HDQ":            "hdq_disc_pct",
        "Coca-Cola":      "coke_disc_pct",
    }
    prod_names = list(product_info.keys())
    disc_cols = list(product_info.values())

    x = np.arange(len(prod_names))
    w = 0.8 / max(len(plats), 1)

    for i, (plat, color) in enumerate(zip(plats, colors)):
        vals = []
        for col in disc_cols:
            s = df[df["platform"] == plat][col].dropna()
            vals.append(s.mean() if len(s) > 0 else 0)
        bars = ax.bar(x + i*w, vals, w, color=color, label=PL[plat],
                      zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            if pd.notna(val) and val > 0:
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.3,
                        f"{val:.1f}%", ha="center", va="bottom",
                        fontsize=8, fontweight="bold")

    ax.set_xticks(x + w * len(plats) / 2)
    ax.set_xticklabels(prod_names, fontsize=10)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="Descuento promedio por producto (solo donde hay descuento)",
             ylabel="% descuento")
    ax.set_ylim(0, 60)

    plt.suptitle("Insight 3 -- Discount Depth: profundidad de descuento por producto",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart3_discount_depth.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart3_discount_depth.png")


# -- Chart 4: Promotional Strategy ---------------------------------------------

def chart4_promo_strategy(df):
    """Three subplots: hook %, % zones with product discount, avg discount depth."""
    plats, colors, labels = get_active_plats(df)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.patch.set_facecolor("white")

    # --- Hook % (promo_general_pct) ---
    ax = axes[0]
    means = [df[df["platform"] == p]["promo_general_pct"].mean() for p in plats]
    bars = ax.bar(labels, means, color=colors, width=0.5,
                  zorder=3, edgecolor="white")
    for bar, val in zip(bars, means):
        if pd.notna(val):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.3,
                    f"Hasta {val:.0f}%", ha="center", va="bottom",
                    fontsize=9, fontweight="bold")
    ax_style(ax, title='Promo general del restaurante\n("hook" visible al entrar)',
             ylabel="% descuento max")
    ax.set_ylim(0, 70)

    # --- % zones with any product discount ---
    ax = axes[1]
    product_cols = {"Combo Big Mac": "combo_disc_pct",
                    "HDQ": "hdq_disc_pct",
                    "Coca-Cola": "coke_disc_pct"}
    x = np.arange(len(product_cols))
    w = 0.8 / max(len(plats), 1)
    for i, (plat, color) in enumerate(zip(plats, colors)):
        vals = [df[df["platform"] == plat][col].notna().mean() * 100
                for col in product_cols.values()]
        bars = ax.bar(x + i*w, vals, w, color=color, label=PL[plat],
                      zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.5,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(x + w * len(plats) / 2)
    ax.set_xticklabels(list(product_cols.keys()), fontsize=9)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="% zonas donde el producto tiene descuento",
             ylabel="% zonas")
    ax.set_ylim(0, 110)

    # --- Avg discount depth across all 3 products ---
    ax = axes[2]
    disc_pct_cols = ["combo_disc_pct", "hdq_disc_pct", "coke_disc_pct"]
    avg_depths = []
    for p in plats:
        sub = df[df["platform"] == p]
        all_disc = pd.concat([sub[col].dropna() for col in disc_pct_cols])
        avg_depths.append(all_disc.mean() if len(all_disc) > 0 else 0)
    bars = ax.bar(labels, avg_depths, color=colors, width=0.5,
                  zorder=3, edgecolor="white")
    for bar, val in zip(bars, avg_depths):
        if pd.notna(val) and val > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.3,
                    f"{val:.1f}%", ha="center", va="bottom",
                    fontsize=9, fontweight="bold")
    ax_style(ax, title="Profundidad promedio de descuento\n(todos los productos)",
             ylabel="% descuento")
    ax.set_ylim(0, safe_max(avg_depths) * 1.5 if safe_max(avg_depths, 0) > 0 else 50)

    plt.suptitle("Insight 4 -- Estrategia Promocional: hook + cobertura + profundidad",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart4_promo_strategy.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart4_promo_strategy.png")


# -- Chart 5: Geographic Competitiveness ---------------------------------------

def chart5_geo_competitiveness(df):
    """Total estimated price by city and zone_type heatmap-style bars."""
    plats, colors, labels = get_active_plats(df)
    cities = sorted(df["city"].dropna().unique())
    zone_types = [zt for zt in ["Wealthy", "Non Wealthy"]
                  if zt in df["zone_type"].values]

    if not cities:
        cities = [""]
    if not zone_types:
        zone_types = [""]

    ncols = max(len(zone_types), 1)
    fig, axes = plt.subplots(1, ncols, figsize=(7 * ncols, 5), squeeze=False)
    fig.patch.set_facecolor("white")

    zt_labels = {"Wealthy": "Zonas Ricas", "Non Wealthy": "Zonas Populares",
                 "": "Todas las zonas"}

    for idx, zt in enumerate(zone_types):
        ax = axes[0][idx]
        sub = df[df["zone_type"] == zt] if zt else df
        x = np.arange(len(cities))
        w = 0.8 / max(len(plats), 1)

        for i, (p, color) in enumerate(zip(plats, colors)):
            vals = [sub[(sub["platform"] == p) & (sub["city"] == city)
                        ]["total_estimated"].mean() for city in cities]
            bars = ax.bar(x + i*w, vals, w, color=color, label=PL[p],
                          zorder=3, edgecolor="white")
            for bar, val in zip(bars, vals):
                if pd.notna(val):
                    ax.text(bar.get_x() + bar.get_width()/2,
                            bar.get_height() + 0.5,
                            f"${val:.0f}", ha="center", va="bottom",
                            fontsize=7, fontweight="bold")

        ax.set_xticks(x + w * len(plats) / 2)
        ax.set_xticklabels(
            [c.replace("Ciudad de Mexico", "CDMX") for c in cities],
            fontsize=9)
        ax.legend(fontsize=8, framealpha=0)
        ax_style(ax, title=zt_labels.get(zt, zt), ylabel="MXN (total estimado)")
        # Set ylim based on data
        all_vals_flat = []
        for p in plats:
            for city in cities:
                v = sub[(sub["platform"] == p) & (sub["city"] == city)
                        ]["total_estimated"].mean()
                if pd.notna(v):
                    all_vals_flat.append(v)
        ax.set_ylim(0, safe_max(all_vals_flat) * 1.3)

    plt.suptitle("Insight 5 -- Competitividad Geografica: precio total por ciudad y zona",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart5_geo_competitiveness.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart5_geo_competitiveness.png")


# -- Chart 6: Market Engagement (review count) ---------------------------------

def chart6_market_engagement(df):
    """Review count by platform (overall) and by city."""
    plats, colors, labels = get_active_plats(df)
    cities = sorted(df["city"].dropna().unique())

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("white")

    # --- Overall review count ---
    ax = axes[0]
    rev_means = [df[df["platform"] == p]["review_count"].mean() for p in plats]
    bars = ax.bar(labels, rev_means, color=colors, width=0.5,
                  zorder=3, edgecolor="white")
    for bar, val in zip(bars, rev_means):
        if pd.notna(val) and val > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.5,
                    f"{val:,.0f}", ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color=C["dark"])
    ax_style(ax, title="Review count promedio por plataforma",
             ylabel="Reviews")
    ax.set_ylim(0, safe_max(rev_means) * 1.4)

    # --- Review count by city ---
    ax = axes[1]
    if len(cities) == 0:
        cities = [""]
    x = np.arange(len(cities))
    w = 0.8 / max(len(plats), 1)
    for i, (p, color) in enumerate(zip(plats, colors)):
        vals = [df[(df["platform"] == p) & (df["city"] == city)
                   ]["review_count"].mean() for city in cities]
        bars = ax.bar(x + i*w, vals, w, color=color, label=PL[p],
                      zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            if pd.notna(val) and val > 0:
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.5,
                        f"{val:,.0f}", ha="center", va="bottom",
                        fontsize=7.5)
    ax.set_xticks(x + w * len(plats) / 2)
    ax.set_xticklabels(
        [c.replace("Ciudad de Mexico", "CDMX") for c in cities], fontsize=9)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="Review count promedio por ciudad",
             ylabel="Reviews")
    all_city_vals = []
    for p in plats:
        for city in cities:
            v = df[(df["platform"] == p) & (df["city"] == city)
                   ]["review_count"].mean()
            if pd.notna(v):
                all_city_vals.append(v)
    ax.set_ylim(0, safe_max(all_city_vals) * 1.4)

    plt.suptitle("Insight 6 -- Market Engagement: review count como proxy de market share",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart6_market_engagement.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart6_market_engagement.png")


# -- Chart 7: Radar -----------------------------------------------------------

def chart7_radar(df):
    """Multidimensional positioning -- no delivery fee axis, includes review count."""
    plats, colors, labels = get_active_plats(df)
    if len(plats) < 2:
        print("  [skip] chart7_radar.png -- need 2+ platforms for radar")
        return

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")

    cats = ["ETA", "Precio\nCombo", "Promo\nGeneral",
            "Discount\nDepth", "Review\nCount"]
    N = len(cats)
    angles = [n / N * 2 * np.pi for n in range(N)] + [0]

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cats, fontsize=10, fontweight="bold")
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["mejor", "", "", "peor"], fontsize=7, color="gray")
    ax.set_facecolor(C["bg"])
    ax.grid(color=C["grid"], lw=0.8)

    disc_pct_cols = ["combo_disc_pct", "hdq_disc_pct", "coke_disc_pct"]

    raw = {}
    for p in plats:
        sub = df[df["platform"] == p]
        eta = sub["eta_min"].mean()
        combo = sub["combo_orig"].mean()
        promo = sub["promo_general_pct"].mean()
        # Avg discount depth (higher = more aggressive discounting)
        all_disc = pd.concat([sub[col].dropna() for col in disc_pct_cols])
        disc_depth = all_disc.mean() if len(all_disc) > 0 else 0
        rev = sub["review_count"].mean()
        raw[p] = [
            eta if pd.notna(eta) else 0,
            combo if pd.notna(combo) else 0,
            100 - (promo if pd.notna(promo) else 0),   # invert: higher promo = better
            100 - (disc_depth if pd.notna(disc_depth) else 0),  # invert: deeper discount = better
            -(rev if pd.notna(rev) else 0),  # invert: more reviews = better (closer to center)
        ]

    arr = np.array([raw[p] for p in plats])
    mn, mx = arr.min(0), arr.max(0)
    denom = np.where(mx - mn == 0, 1, mx - mn)
    norm = {p: ((np.array(raw[p]) - mn) / denom).tolist() for p in plats}

    for plat, color in zip(plats, colors):
        vals = norm[plat] + [norm[plat][0]]
        ax.plot(angles, vals, "o-", lw=2.5, color=color, label=PL[plat])
        ax.fill(angles, vals, alpha=0.08, color=color)

    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15),
              fontsize=11, framealpha=0)
    plt.title("Posicionamiento multidimensional\n"
              "(mas cerca del centro = mas competitivo)",
              size=11, fontweight="bold", color=C["dark"], pad=20)
    plt.tight_layout()
    plt.savefig("output/chart7_radar.png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart7_radar.png")


# -- Summary stats -------------------------------------------------------------

def print_summary(df):
    plats, _, _ = get_active_plats(df)
    n_addr = df["address_id"].nunique()
    n_plats = len(plats)

    print(f"\n{'='*65}")
    print(f"  COMPETITIVE INTELLIGENCE SUMMARY")
    print(f"  {n_addr} direcciones | {n_plats} plataformas: {', '.join(PL[p] for p in plats)}")
    print(f"{'='*65}")

    zone_types = df["zone_type"].dropna().unique()
    has_zones = len(zone_types) > 1

    print("\n  ETA promedio (min):")
    print(df.groupby("platform")["eta_min"].mean().round(1).to_string())

    print("\n  Rating promedio:")
    print(df.groupby("platform")["rating"].mean().round(2).to_string())

    print("\n  Review count promedio:")
    if "review_count" in df.columns:
        print(df.groupby("platform")["review_count"].mean().round(0).to_string())
    else:
        print("  (no disponible)")

    print("\n  Promo general restaurante (% hook visible):")
    print(df.groupby("platform")["promo_general_pct"].mean().round(1).to_string())

    print("\n  Combo Big Mac -- precio original promedio:")
    print(df.groupby("platform")["combo_orig"].mean().round(2).to_string())

    print("\n  Descuento promedio por producto (%):")
    for col_label, col in [("Combo Big Mac", "combo_disc_pct"),
                            ("HDQ", "hdq_disc_pct"),
                            ("Coca-Cola", "coke_disc_pct")]:
        print(f"    {col_label}:")
        print("    " + df.groupby("platform")[col].mean().round(1).to_string().replace("\n", "\n    "))

    print("\n  Total estimado all-in (MXN):")
    if has_zones:
        print(df.groupby(["platform", "zone_type"])["total_estimated"].mean()
              .round(1).unstack().to_string())
    else:
        print(df.groupby("platform")["total_estimated"].mean().round(1).to_string())

    print("=" * 65)

    return compute_kpis(df, plats)


def compute_kpis(df, plats):
    """Return dict of KPIs for PDF/dashboard."""
    disc_pct_cols = ["combo_disc_pct", "hdq_disc_pct", "coke_disc_pct"]
    kpis = {}
    for p in plats:
        sub = df[df["platform"] == p]
        # Avg discount depth across all products
        all_disc = pd.concat([sub[col].dropna() for col in disc_pct_cols])
        avg_disc_depth = all_disc.mean() if len(all_disc) > 0 else 0

        kpis[p] = {
            "eta_avg": sub["eta_min"].mean(),
            "rating_avg": sub["rating"].mean(),
            "review_count_avg": sub["review_count"].mean(),
            "promo_avg": sub["promo_general_pct"].mean(),
            "combo_orig_avg": sub["combo_orig"].mean(),
            "combo_disc_avg": sub["combo_disc"].mean(),
            "combo_disc_pct_avg": sub["combo_disc_pct"].mean(),
            "hdq_orig_avg": sub["hdq_orig"].mean(),
            "hdq_disc_avg": sub["hdq_disc"].mean(),
            "hdq_disc_pct_avg": sub["hdq_disc_pct"].mean(),
            "coke_orig_avg": sub["coke_orig"].mean(),
            "coke_disc_avg": sub["coke_disc"].mean(),
            "coke_disc_pct_avg": sub["coke_disc_pct"].mean(),
            "avg_discount_depth": avg_disc_depth,
            "combo_disc_zone_pct": sub["combo_disc_pct"].notna().mean() * 100,
            "total_avg": sub["total_estimated"].mean(),
            "service_fee_pct": SERVICE_FEE_RATES.get(p, 10),
        }
        # Zone-specific
        for zt in ["Wealthy", "Non Wealthy"]:
            zt_key = zt.lower().replace(" ", "_")
            sub_zt = sub[sub["zone_type"] == zt]
            kpis[p][f"total_{zt_key}"] = sub_zt["total_estimated"].mean()
            kpis[p][f"review_count_{zt_key}"] = sub_zt["review_count"].mean()
    return kpis


# -- Main ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Forzar datos mock")
    args = parser.parse_args()

    df = load_data(force_mock=args.mock)
    kpis = print_summary(df)

    # Save KPIs for PDF report
    kpis_path = Path("output/kpis.json")
    # Convert NaN to None for JSON serialization
    clean_kpis = {}
    for p, vals in kpis.items():
        clean_kpis[p] = {k: (None if pd.isna(v) else v) for k, v in vals.items()}
    with open(kpis_path, "w", encoding="utf-8") as f:
        json.dump(clean_kpis, f, indent=2, ensure_ascii=False)

    chart1_price_positioning(df)
    chart2_operational(df)
    chart3_discount_depth(df)
    chart4_promo_strategy(df)
    chart5_geo_competitiveness(df)
    chart6_market_engagement(df)
    chart7_radar(df)
    print(f"\n  7 charts -> output/")


if __name__ == "__main__":
    main()
