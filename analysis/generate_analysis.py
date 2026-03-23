"""
Análisis Competitivo — Rappi México
=====================================
Genera 7 charts accionables + stats de consola.

Uso: python analysis/generate_analysis.py
"""

import json, os, re, warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Setup ──────────────────────────────────────────────────────────────────────
os.chdir(Path(__file__).parent.parent)
Path("output").mkdir(exist_ok=True)

C = {
    "rappi":       "#FF441F",
    "ubereats":    "#06C167",
    "didifood":    "#FF6B00",
    "wealthy":     "#2E4057",
    "nonwealthy":  "#E84855",
    "bg":          "#FAFAFA",
    "grid":        "#E8E8E8",
    "dark":        "#1A1A2E",
    "gray":        "#666666",
}
PL = {"rappi": "Rappi", "ubereats": "Uber Eats", "didifood": "DiDi Food"}
PLATS = ["rappi", "ubereats", "didifood"]
PLT_COLORS = [C[p] for p in PLATS]

plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "white"})


# ── Load data ──────────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    candidates = sorted(Path("data").glob("competitive_data_*.json"), reverse=True)
    if not candidates:
        raise FileNotFoundError("No data in data/. Run: python scraper/generate_mock_data.py")
    path = candidates[0]
    print(f"📂 {path.name}")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    rows = []
    for r in raw:
        for plat in PLATS:
            if plat not in r:
                continue
            p = r[plat]
            prods = {pr["name"]: pr for pr in p.get("products", [])}
            combo = prods.get("Combo Big Mac mediano", {})
            hdq   = prods.get("Hamburguesa doble con queso", {})
            coke  = prods.get("Coca-Cola mediana", {})
            rows.append({
                "address_id":        r["address_id"],
                "city":              r["city"],
                "zone":              r["zone"],
                "zone_type":         r["zone_type"],
                "platform":          plat,
                "status":            p.get("status"),
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
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ── Style helpers ──────────────────────────────────────────────────────────────

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


# ── Chart 1: Delivery fee por zona ─────────────────────────────────────────────

def chart1_delivery_fee(df):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")

    for ax, zt, title in zip(
        axes, ["Wealthy", "Non Wealthy"],
        ["Zonas Ricas", "Zonas Populares ← brecha más grande"],
    ):
        sub = df[df["zone_type"] == zt]
        means = [sub[sub["platform"] == p]["delivery_fee"].mean() for p in PLATS]
        bars = ax.bar([PL[p] for p in PLATS], means, color=PLT_COLORS,
                      width=0.5, zorder=3, edgecolor="white")
        bar_labels(ax, bars)
        ax_style(ax, title=title, ylabel="MXN")
        ax.set_ylim(0, max(m for m in means if pd.notna(m)) * 1.45)

    # Anotar gap rappi vs ubereats en non-wealthy
    rappi_nw = df[(df["platform"]=="rappi") & (df["zone_type"]=="Non Wealthy")]["delivery_fee"].mean()
    uber_nw  = df[(df["platform"]=="ubereats") & (df["zone_type"]=="Non Wealthy")]["delivery_fee"].mean()
    if rappi_nw and uber_nw:
        gap = (rappi_nw/uber_nw - 1)*100
        axes[1].annotate(f"Rappi cobra\n{gap:.0f}% más\nque Uber Eats",
                         xy=(0, rappi_nw), xytext=(0.15, rappi_nw*1.2),
                         fontsize=8, color=C["nonwealthy"], fontweight="bold",
                         arrowprops=dict(arrowstyle="->", color=C["nonwealthy"]))

    plt.suptitle("Insight 1 — Delivery Fee: Rappi es el más caro en zonas populares",
                 fontsize=12, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart1_delivery_fee.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ chart1_delivery_fee.png")


# ── Chart 2: ETA y rating ──────────────────────────────────────────────────────

def chart2_eta_rating(df):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")

    # ETA por ciudad
    ax = axes[0]
    cities = df["city"].unique()
    x = np.arange(len(cities))
    w = 0.25
    for i, (p, c) in enumerate(zip(PLATS, PLT_COLORS)):
        vals = [df[(df["platform"]==p) & (df["city"]==city)]["eta_min"].mean() for city in cities]
        bars = ax.bar(x + i*w, vals, w, color=c, label=PL[p], zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            if pd.notna(val):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                        f"{val:.0f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(30, color=C["nonwealthy"], lw=1.2, ls="--", alpha=0.7)
    ax.text(len(cities)-0.3, 31, "SLA 30 min", fontsize=7.5, color=C["nonwealthy"])
    ax.set_xticks(x + w)
    ax.set_xticklabels([c.replace("Ciudad de Mexico","CDMX") for c in cities], fontsize=9)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="ETA promedio por ciudad", ylabel="Minutos")
    ax.set_ylim(0, 55)

    # Rating
    ax = axes[1]
    means = [df[df["platform"]==p]["rating"].mean() for p in PLATS]
    bars = ax.bar([PL[p] for p in PLATS], means, color=PLT_COLORS,
                  width=0.5, zorder=3, edgecolor="white")
    for bar, val in zip(bars, means):
        if pd.notna(val):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                    f"★ {val:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax_style(ax, title="Rating promedio de McDonald's", ylabel="Estrellas")
    ax.set_ylim(3.8, 5.0)

    plt.suptitle("Insight 2 — Operacional: Uber Eats es más rápido; DiDi tiene menor rating",
                 fontsize=12, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart2_eta_rating.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ chart2_eta_rating.png")


# ── Chart 3: Precios de productos ─────────────────────────────────────────────

def chart3_product_prices(df):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor("white")

    products = [
        ("combo_orig",  "combo_disc",  "Combo Big Mac mediano"),
        ("hdq_orig",    "hdq_disc",    "Hamburguesa doble con queso"),
        ("coke_orig",   "coke_disc",   "Coca-Cola mediana"),
    ]

    for ax, (orig_col, disc_col, title) in zip(axes, products):
        x = np.arange(len(PLATS))
        w = 0.35
        orig_means = [df[df["platform"]==p][orig_col].mean() for p in PLATS]
        disc_means = [df[df["platform"]==p][disc_col].mean() for p in PLATS]

        bars_o = ax.bar(x - w/2, orig_means, w, color=[c+"55" for c in PLT_COLORS],
                        zorder=3, edgecolor="white", label="Precio original")
        bars_d = ax.bar(x + w/2, disc_means, w, color=PLT_COLORS,
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
        ax.set_xticklabels([PL[p] for p in PLATS], fontsize=9)
        ax_style(ax, title=title, ylabel="MXN")
        all_vals = [v for v in orig_means + disc_means if pd.notna(v) and v > 0]
        ax.set_ylim(0, max(all_vals)*1.35 if all_vals else 200)

    axes[0].legend(fontsize=8, framealpha=0)
    plt.suptitle("Insight 3 — Precios: Comparables entre plataformas; los descuentos son el diferenciador",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart3_product_prices.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ chart3_product_prices.png")


# ── Chart 4: Fee structure (delivery + service + total) ───────────────────────

def chart4_fee_structure(df):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor("white")

    # Delivery fee promedio
    ax = axes[0]
    means = [df[df["platform"]==p]["delivery_fee"].mean() for p in PLATS]
    bars = ax.bar([PL[p] for p in PLATS], means, color=PLT_COLORS,
                  width=0.5, zorder=3, edgecolor="white")
    bar_labels(ax, bars)
    ax_style(ax, title="Delivery Fee promedio", ylabel="MXN")
    ax.set_ylim(0, max(m for m in means if pd.notna(m))*1.4)

    # Service fee estimado
    ax = axes[1]
    rates = {"rappi": 10, "ubereats": 15, "didifood": 8}
    rate_vals = [rates[p] for p in PLATS]
    bars = ax.bar([PL[p] for p in PLATS], rate_vals, color=PLT_COLORS,
                  width=0.5, zorder=3, edgecolor="white")
    for bar, val in zip(bars, rate_vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                f"{val}%", ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax_style(ax, title="Service Fee estimado (% del pedido)", ylabel="%")
    ax.set_ylim(0, 22)

    # Total estimado
    ax = axes[2]
    means_t = [df[df["platform"]==p]["total_estimated"].mean() for p in PLATS]
    bars = ax.bar([PL[p] for p in PLATS], means_t, color=PLT_COLORS,
                  width=0.5, zorder=3, edgecolor="white")
    bar_labels(ax, bars)
    ax_style(ax, title="Costo total estimado all-in", ylabel="MXN")
    ax.set_ylim(0, max(m for m in means_t if pd.notna(m))*1.25)

    # Nota sobre service fee
    axes[1].text(0.5, 0.1, "Rappi y DiDi\nconvergen en\ncosto total\na pesar del\ngap en fees",
                 transform=axes[1].transAxes, ha="center", fontsize=7.5,
                 color=C["gray"], style="italic")

    plt.suptitle("Insight 4 — Estructura de Fees: DiDi tiene menor service fee; Rappi mayor delivery fee",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart4_fee_structure.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ chart4_fee_structure.png")


# ── Chart 5: Estrategia promocional ───────────────────────────────────────────

def chart5_promotions(df):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")

    # Promo general del restaurante (el "hook")
    ax = axes[0]
    means = [df[df["platform"]==p]["promo_general_pct"].mean() for p in PLATS]
    bars = ax.bar([PL[p] for p in PLATS], means, color=PLT_COLORS,
                  width=0.5, zorder=3, edgecolor="white")
    for bar, val in zip(bars, means):
        if pd.notna(val):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                    f"Hasta {val:.0f}%", ha="center", va="bottom",
                    fontsize=9, fontweight="bold")
    ax_style(ax, title='Promo general del restaurante\n("hook" visible al entrar)', ylabel="% descuento máximo")
    ax.set_ylim(0, 70)

    # % zonas con algún descuento por producto
    ax = axes[1]
    products_rate = {
        "Combo Big Mac": {p: df[df["platform"]==p]["combo_disc_pct"].notna().mean()*100 for p in PLATS},
        "Hamburgesa DQ": {p: df[df["platform"]==p]["hdq_disc_pct"].notna().mean()*100 for p in PLATS},
        "Coca-Cola":     {p: df[df["platform"]==p]["coke_disc_pct"].notna().mean()*100 for p in PLATS},
    }
    x = np.arange(len(products_rate))
    w = 0.25
    for i, (plat, color) in enumerate(zip(PLATS, PLT_COLORS)):
        vals = [products_rate[prod][plat] for prod in products_rate]
        bars = ax.bar(x + i*w, vals, w, color=color, label=PL[plat], zorder=3, edgecolor="white")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(x + w)
    ax.set_xticklabels(list(products_rate.keys()), fontsize=9)
    ax.legend(fontsize=9, framealpha=0)
    ax_style(ax, title="% zonas donde el producto tiene descuento", ylabel="% zonas")
    ax.set_ylim(0, 110)

    plt.suptitle("Insight 5 — Promos: DiDi es el más agresivo en descuentos; Rappi el más conservador",
                 fontsize=11, fontweight="bold", y=1.02, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart5_promotions.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ chart5_promotions.png")


# ── Chart 6: Variabilidad geográfica ─────────────────────────────────────────

def chart6_geo_heatmap(df):
    fig, axes = plt.subplots(1, 3, figsize=(16, 7))
    fig.patch.set_facecolor("white")

    wealthy_patch   = mpatches.Patch(color=C["wealthy"],    label="Wealthy")
    nonwealthy_patch = mpatches.Patch(color=C["nonwealthy"], label="Non-Wealthy")

    for ax, plat in zip(axes, PLATS):
        sub = df[df["platform"]==plat].groupby(["zone","zone_type"])["delivery_fee"].mean().reset_index()
        sub = sub.sort_values("delivery_fee", ascending=False)
        colors = [C["nonwealthy"] if zt == "Non Wealthy" else C["wealthy"] for zt in sub["zone_type"]]
        bars = ax.barh(sub["zone"], sub["delivery_fee"], color=colors, edgecolor="white")
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
    plt.suptitle("Insight — Variabilidad geográfica: brecha se amplía en zonas periféricas",
                 fontsize=12, fontweight="bold", y=1.01, color=C["dark"])
    plt.tight_layout()
    plt.savefig("output/chart6_geo_heatmap.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ chart6_geo_heatmap.png")


# ── Chart 7: Radar multidimensional ──────────────────────────────────────────

def chart7_radar(df):
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
    for p in PLATS:
        sub = df[df["platform"]==p]
        raw[p] = [
            sub["delivery_fee"].mean(),
            sub["eta_min"].mean(),
            {"rappi":10,"ubereats":15,"didifood":8}[p],
            sub["combo_orig"].mean(),
            # Para promo: invertir (mayor promo = mejor)
            100 - (sub["promo_general_pct"].mean() or 0),
        ]

    arr = np.array([raw[p] for p in PLATS])
    mn, mx = arr.min(0), arr.max(0)
    norm = {p: ((np.array(raw[p])-mn)/np.where(mx-mn==0,1,mx-mn)).tolist() for p in PLATS}

    for plat, color in zip(PLATS, PLT_COLORS):
        vals = norm[plat] + [norm[plat][0]]
        ax.plot(angles, vals, "o-", lw=2.5, color=color, label=PL[plat])
        ax.fill(angles, vals, alpha=0.08, color=color)

    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=11, framealpha=0)
    plt.title("Posicionamiento multidimensional\n(más cerca del centro = más competitivo)",
              size=11, fontweight="bold", color=C["dark"], pad=20)
    plt.tight_layout()
    plt.savefig("output/chart7_radar.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ chart7_radar.png")


# ── Summary stats ─────────────────────────────────────────────────────────────

def print_summary(df):
    print("\n" + "="*65)
    print("  COMPETITIVE INTELLIGENCE SUMMARY — RAPPI MÉXICO")
    print("="*65)

    print("\n📦 Delivery fee (MXN):")
    print(df.groupby(["platform","zone_type"])["delivery_fee"].mean().round(1).unstack().to_string())

    rappi_nw = df[(df["platform"]=="rappi")&(df["zone_type"]=="Non Wealthy")]["delivery_fee"].mean()
    uber_nw  = df[(df["platform"]=="ubereats")&(df["zone_type"]=="Non Wealthy")]["delivery_fee"].mean()
    if rappi_nw and uber_nw:
        print(f"  → Rappi cobra {(rappi_nw/uber_nw-1)*100:.0f}% más que Uber Eats en Non-Wealthy")

    print("\n⏱  ETA promedio (min):")
    print(df.groupby("platform")["eta_min"].mean().round(1).to_string())

    print("\n🎯 Promo general restaurante (% hook visible):")
    print(df.groupby("platform")["promo_general_pct"].mean().round(1).to_string())

    print("\n🍔 Combo Big Mac — precio original promedio:")
    print(df.groupby("platform")["combo_orig"].mean().round(2).to_string())

    print("\n💰 Total estimado all-in (MXN):")
    totals = df.groupby(["platform","zone_type"])["total_estimated"].mean().round(1).unstack()
    print(totals.to_string())

    print("\n⭐ Rating promedio:")
    print(df.groupby("platform")["rating"].mean().round(2).to_string())
    print("="*65)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    df = load_data()
    print_summary(df)
    chart1_delivery_fee(df)
    chart2_eta_rating(df)
    chart3_product_prices(df)
    chart4_fee_structure(df)
    chart5_promotions(df)
    chart6_geo_heatmap(df)
    chart7_radar(df)
    print("\n✅ 7 charts guardados en output/")


if __name__ == "__main__":
    main()
