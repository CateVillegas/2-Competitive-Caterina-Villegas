"""
Analisis Competitivo -- Rappi Mexico
=====================================
Genera 7 charts accionables + stats de consola.
Robusto: funciona con 1 o N plataformas, 1 o 50 direcciones.

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
    num_cols = ["rating","eta_min","delivery_fee","promo_general_pct",
                "combo_orig","combo_disc","combo_disc_pct",
                "hdq_orig","hdq_disc","hdq_disc_pct",
                "coke_orig","coke_disc","coke_disc_pct",
                "subtotal","service_fee_est","total_estimated"]
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


# -- Chart 1: Delivery fee por zona -------------------------------------------

def chart1_delivery_fee(df):
    plats, colors, labels = get_active_plats(df)
    zone_types = [zt for zt in ["Wealthy", "Non Wealthy"] if zt in df["zone_type"].values]
    if not zone_types:
        zone_types = [""]

    ncols = min(len(zone_types), 2) if len(zone_types) > 1 else 1
    fig, axes = plt.subplots(1, ncols, figsize=(7*ncols, 5), squeeze=False)
    fig.patch.set_facecolor("white")

    titles_map = {"Wealthy": "Zonas Ricas", "Non Wealthy": "Zonas Populares", "": "Todas las zonas"}
    for idx, zt in enumerate(zone_types):
        ax = axes[0][idx]
        sub = df[df["zone_type"] == zt] if zt else df
        means = [sub[sub["platform"] == p]["delivery_fee"].mean() for p in plats]
        bars = ax.bar(labels, means, color=colors, width=0.5, zorder=3, edgecolor="white")
        bar_labels(ax, bars)
        ax_style(ax, title=titles_map.get(zt, zt), ylabel="MXN")
        ax.set_ylim(0, safe_max(means) * 1.45)

    # Annotate Rappi vs UberEats gap if both present
    if "rappi" in plats and "ubereats" in plats and "Non Wealthy" in zone_types:
        rappi_nw = df[(df["platform"]=="rappi") & (df["zone_type"]=="Non Wealthy")]["delivery_fee"].mean()
        uber_nw  = df[(df["platform"]=="ubereats") & (df["zone_type"]=="Non Wealthy")]["delivery_fee"].mean()
        if pd.notna(rappi_nw) and pd.notna(uber_nw) and uber_nw > 0:
            gap = (rappi_nw/uber_nw - 1)*100
            nw_idx = zone_types.index("Non Wealthy")
            rappi_bar_idx = plats.index("rappi")
            axes[0][nw_idx].annotate(
                f"Rappi cobra\n{gap:.0f}% mas\nque Uber Eats",
                xy=(rappi_bar_idx, rappi_nw),
                xytext=(rappi_bar_idx + 0.15, rappi_nw * 1.2),
                fontsize=8, color=C["nonwealthy"], fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C["nonwealthy"]))

    plt.suptitle("Insight 1 -- Delivery Fee por zona",
                 fontsize=12, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart1_delivery_fee.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart1_delivery_fee.png")


# -- Chart 2: ETA y rating ----------------------------------------------------

def chart2_eta_rating(df):
    plats, colors, labels = get_active_plats(df)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")

    # ETA by city
    ax = axes[0]
    cities = df["city"].unique()
    if len(cities) == 0:
        cities = [""]
    x = np.arange(len(cities))
    w = 0.8 / max(len(plats), 1)
    for i, (p, c) in enumerate(zip(plats, colors)):
        vals = [df[(df["platform"]==p) & (df["city"]==city)]["eta_min"].mean() for city in cities]
        bars = ax.bar(x + i*w, vals, w, color=c, label=PL[p], zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            if pd.notna(val):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                        f"{val:.0f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(30, color=C["nonwealthy"], lw=1.2, ls="--", alpha=0.7)
    ax.text(len(cities)-0.3, 31, "SLA 30 min", fontsize=7.5, color=C["nonwealthy"])
    ax.set_xticks(x + w * len(plats) / 2)
    ax.set_xticklabels([c.replace("Ciudad de Mexico","CDMX") for c in cities], fontsize=9)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="ETA promedio por ciudad", ylabel="Minutos")
    ax.set_ylim(0, 55)

    # Rating
    ax = axes[1]
    means = [df[df["platform"]==p]["rating"].mean() for p in plats]
    bars = ax.bar(labels, means, color=colors, width=0.5, zorder=3, edgecolor="white")
    for bar, val in zip(bars, means):
        if pd.notna(val):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                    f"* {val:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax_style(ax, title="Rating promedio de McDonald's", ylabel="Estrellas")
    valid_ratings = [m for m in means if pd.notna(m)]
    if valid_ratings:
        ax.set_ylim(min(valid_ratings) - 0.5, 5.0)
    else:
        ax.set_ylim(3.0, 5.0)

    plt.suptitle("Insight 2 -- Operacional: ETA y Rating",
                 fontsize=12, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart2_eta_rating.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart2_eta_rating.png")


# -- Chart 3: Product prices --------------------------------------------------

def chart3_product_prices(df):
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
        orig_means = [df[df["platform"]==p][orig_col].mean() for p in plats]
        disc_means = [df[df["platform"]==p][disc_col].mean() for p in plats]

        bars_o = ax.bar(x - w/2, orig_means, w, color=[c+"55" for c in colors],
                        zorder=3, edgecolor="white", label="Precio original")
        bars_d = ax.bar(x + w/2, disc_means, w, color=colors,
                        zorder=3, edgecolor="white", label="Con descuento")

        for bar, val in zip(bars_o, orig_means):
            if pd.notna(val):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                        f"${val:.0f}", ha="center", va="bottom", fontsize=7.5, color=C["gray"])
        for bar, val in zip(bars_d, disc_means):
            if pd.notna(val):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                        f"${val:.0f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax_style(ax, title=title, ylabel="MXN")
        all_vals = orig_means + disc_means
        ax.set_ylim(0, safe_max(all_vals) * 1.35)

    axes[0].legend(fontsize=8, framealpha=0)
    plt.suptitle("Insight 3 -- Precios: Comparativa de productos entre plataformas",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart3_product_prices.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart3_product_prices.png")


# -- Chart 4: Fee structure ---------------------------------------------------

def chart4_fee_structure(df):
    plats, colors, labels = get_active_plats(df)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor("white")

    # Delivery fee
    ax = axes[0]
    means = [df[df["platform"]==p]["delivery_fee"].mean() for p in plats]
    bars = ax.bar(labels, means, color=colors, width=0.5, zorder=3, edgecolor="white")
    bar_labels(ax, bars)
    ax_style(ax, title="Delivery Fee promedio", ylabel="MXN")
    ax.set_ylim(0, safe_max(means) * 1.4)

    # Service fee %
    ax = axes[1]
    rate_vals = [SERVICE_FEE_RATES.get(p, 10) for p in plats]
    bars = ax.bar(labels, rate_vals, color=colors, width=0.5, zorder=3, edgecolor="white")
    for bar, val in zip(bars, rate_vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                f"{val}%", ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax_style(ax, title="Service Fee estimado (% del pedido)", ylabel="%")
    ax.set_ylim(0, max(rate_vals) * 1.5)

    # Total
    ax = axes[2]
    means_t = [df[df["platform"]==p]["total_estimated"].mean() for p in plats]
    bars = ax.bar(labels, means_t, color=colors, width=0.5, zorder=3, edgecolor="white")
    bar_labels(ax, bars)
    ax_style(ax, title="Costo total estimado all-in", ylabel="MXN")
    ax.set_ylim(0, safe_max(means_t) * 1.25)

    plt.suptitle("Insight 4 -- Estructura de Fees: Delivery + Service + Total",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart4_fee_structure.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart4_fee_structure.png")


# -- Chart 5: Promotions ------------------------------------------------------

def chart5_promotions(df):
    plats, colors, labels = get_active_plats(df)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")

    # General promo hook
    ax = axes[0]
    means = [df[df["platform"]==p]["promo_general_pct"].mean() for p in plats]
    bars = ax.bar(labels, means, color=colors, width=0.5, zorder=3, edgecolor="white")
    for bar, val in zip(bars, means):
        if pd.notna(val):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                    f"Hasta {val:.0f}%", ha="center", va="bottom",
                    fontsize=9, fontweight="bold")
    ax_style(ax, title='Promo general del restaurante\n("hook" visible al entrar)', ylabel="% descuento max")
    ax.set_ylim(0, 70)

    # % zones with discount per product
    ax = axes[1]
    product_labels = {"Combo Big Mac": "combo_disc_pct", "HDQ": "hdq_disc_pct", "Coca-Cola": "coke_disc_pct"}
    x = np.arange(len(product_labels))
    w = 0.8 / max(len(plats), 1)
    for i, (plat, color) in enumerate(zip(plats, colors)):
        vals = [df[df["platform"]==plat][col].notna().mean()*100 for col in product_labels.values()]
        bars = ax.bar(x + i*w, vals, w, color=color, label=PL[plat], zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(x + w * len(plats) / 2)
    ax.set_xticklabels(list(product_labels.keys()), fontsize=9)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="% zonas donde el producto tiene descuento", ylabel="% zonas")
    ax.set_ylim(0, 110)

    plt.suptitle("Insight 5 -- Estrategia Promocional por plataforma",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart5_promotions.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart5_promotions.png")


# -- Chart 6: Geographic variability -------------------------------------------

def chart6_geo_heatmap(df):
    plats, colors, labels = get_active_plats(df)
    zones = df["zone"].nunique()
    if zones < 2:
        # Not enough zones for geographic chart — make a simple comparison bar instead
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("white")
        means = [df[df["platform"]==p]["delivery_fee"].mean() for p in plats]
        bars = ax.bar(labels, means, color=[C[p] for p in plats], width=0.5, zorder=3, edgecolor="white")
        bar_labels(ax, bars)
        ax_style(ax, title="Delivery Fee por plataforma", ylabel="MXN")
        ax.set_ylim(0, safe_max(means) * 1.4)
        plt.suptitle("Insight -- Comparativa de Delivery Fee (data limitada a pocas zonas)",
                     fontsize=12, fontweight="bold", y=1.02, color=C["dark"])
        plt.tight_layout()
        plt.savefig("output/chart6_geo_heatmap.png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        print("  [ok] chart6_geo_heatmap.png (simplified — few zones)")
        return

    ncols = len(plats)
    fig, axes = plt.subplots(1, ncols, figsize=(5.5*ncols, max(7, zones*0.4)))
    if ncols == 1:
        axes = [axes]
    fig.patch.set_facecolor("white")

    wealthy_patch    = mpatches.Patch(color=C["wealthy"],    label="Wealthy")
    nonwealthy_patch = mpatches.Patch(color=C["nonwealthy"], label="Non-Wealthy")

    for ax, plat in zip(axes, plats):
        sub = df[df["platform"]==plat].groupby(["zone","zone_type"])["delivery_fee"].mean().reset_index()
        sub = sub.sort_values("delivery_fee", ascending=False)
        bar_colors = [C["nonwealthy"] if zt == "Non Wealthy" else C["wealthy"] for zt in sub["zone_type"]]
        bars = ax.barh(sub["zone"], sub["delivery_fee"], color=bar_colors, edgecolor="white")
        for bar, val in zip(bars, sub["delivery_fee"]):
            if pd.notna(val):
                ax.text(val+0.3, bar.get_y()+bar.get_height()/2,
                        f"${val:.0f}", va="center", fontsize=7.5)
        ax.set_title(PL[plat], fontsize=11, fontweight="bold", color=C["dark"])
        ax.set_xlabel("Delivery Fee (MXN)", fontsize=8)
        ax.invert_yaxis()
        ax.set_facecolor(C["bg"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.legend(handles=[wealthy_patch, nonwealthy_patch], loc="lower center",
               ncol=2, fontsize=10, framealpha=0, bbox_to_anchor=(0.5, -0.04))
    plt.suptitle("Insight -- Variabilidad geografica: brecha se amplia en zonas perifericas",
                 fontsize=12, fontweight="bold", y=1.01, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart6_geo_heatmap.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("  [ok] chart6_geo_heatmap.png")


# -- Chart 7: Radar -----------------------------------------------------------

def chart7_radar(df):
    plats, colors, labels = get_active_plats(df)
    if len(plats) < 2:
        print("  [skip] chart7_radar.png — need 2+ platforms for radar")
        return

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")

    cats = ["Delivery\nFee", "ETA", "Service\nFee %", "Precio\nCombo", "Promo\nGeneral"]
    N = len(cats)
    angles = [n/N*2*np.pi for n in range(N)] + [0]

    ax.set_theta_offset(np.pi/2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cats, fontsize=10, fontweight="bold")
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["mejor","","","peor"], fontsize=7, color="gray")
    ax.set_facecolor(C["bg"])
    ax.grid(color=C["grid"], lw=0.8)

    raw = {}
    for p in plats:
        sub = df[df["platform"]==p]
        fee = sub["delivery_fee"].mean()
        eta = sub["eta_min"].mean()
        svc = SERVICE_FEE_RATES.get(p, 10)
        combo = sub["combo_orig"].mean()
        promo = sub["promo_general_pct"].mean()
        raw[p] = [
            fee if pd.notna(fee) else 0,
            eta if pd.notna(eta) else 0,
            svc,
            combo if pd.notna(combo) else 0,
            100 - (promo if pd.notna(promo) else 0),
        ]

    arr = np.array([raw[p] for p in plats])
    mn, mx = arr.min(0), arr.max(0)
    denom = np.where(mx - mn == 0, 1, mx - mn)
    norm = {p: ((np.array(raw[p]) - mn) / denom).tolist() for p in plats}

    for plat, color in zip(plats, colors):
        vals = norm[plat] + [norm[plat][0]]
        ax.plot(angles, vals, "o-", lw=2.5, color=color, label=PL[plat])
        ax.fill(angles, vals, alpha=0.08, color=color)

    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=11, framealpha=0)
    plt.title("Posicionamiento multidimensional\n(mas cerca del centro = mas competitivo)",
              size=11, fontweight="bold", color=C["dark"], pad=20)
    plt.tight_layout()
    plt.savefig("output/chart7_radar.png", dpi=150, bbox_inches="tight", facecolor="white")
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

    print("\n  Delivery fee (MXN):")
    if has_zones:
        print(df.groupby(["platform","zone_type"])["delivery_fee"].mean().round(1).unstack().to_string())
    else:
        print(df.groupby("platform")["delivery_fee"].mean().round(1).to_string())

    if "rappi" in plats and "ubereats" in plats:
        rappi_fee = df[df["platform"]=="rappi"]["delivery_fee"].mean()
        uber_fee  = df[df["platform"]=="ubereats"]["delivery_fee"].mean()
        if pd.notna(rappi_fee) and pd.notna(uber_fee) and uber_fee > 0:
            gap = (rappi_fee/uber_fee - 1)*100
            if abs(gap) > 1:
                print(f"  -> Rappi {'cobra' if gap > 0 else 'ahorra'} {abs(gap):.0f}% vs Uber Eats en delivery fee")

    print("\n  ETA promedio (min):")
    print(df.groupby("platform")["eta_min"].mean().round(1).to_string())

    print("\n  Promo general restaurante (% hook visible):")
    print(df.groupby("platform")["promo_general_pct"].mean().round(1).to_string())

    print("\n  Combo Big Mac -- precio original promedio:")
    print(df.groupby("platform")["combo_orig"].mean().round(2).to_string())

    print("\n  Total estimado all-in (MXN):")
    if has_zones:
        print(df.groupby(["platform","zone_type"])["total_estimated"].mean().round(1).unstack().to_string())
    else:
        print(df.groupby("platform")["total_estimated"].mean().round(1).to_string())

    print("\n  Rating promedio:")
    print(df.groupby("platform")["rating"].mean().round(2).to_string())
    print("="*65)

    return compute_kpis(df, plats)


def compute_kpis(df, plats):
    """Return dict of KPIs for PDF/dashboard."""
    kpis = {}
    for p in plats:
        sub = df[df["platform"]==p]
        kpis[p] = {
            "delivery_fee_avg": sub["delivery_fee"].mean(),
            "eta_avg": sub["eta_min"].mean(),
            "rating_avg": sub["rating"].mean(),
            "promo_avg": sub["promo_general_pct"].mean(),
            "combo_orig_avg": sub["combo_orig"].mean(),
            "hdq_orig_avg": sub["hdq_orig"].mean(),
            "coke_orig_avg": sub["coke_orig"].mean(),
            "total_avg": sub["total_estimated"].mean(),
            "service_fee_pct": SERVICE_FEE_RATES.get(p, 10),
        }
        # Zone-specific
        for zt in ["Wealthy", "Non Wealthy"]:
            sub_zt = sub[sub["zone_type"]==zt]
            kpis[p][f"delivery_fee_{zt.lower().replace(' ','_')}"] = sub_zt["delivery_fee"].mean()
            kpis[p][f"total_{zt.lower().replace(' ','_')}"] = sub_zt["total_estimated"].mean()
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

    chart1_delivery_fee(df)
    chart2_eta_rating(df)
    chart3_product_prices(df)
    chart4_fee_structure(df)
    chart5_promotions(df)
    chart6_geo_heatmap(df)
    chart7_radar(df)
    print(f"\n  7 charts -> output/")


if __name__ == "__main__":
    main()
