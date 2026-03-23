"""Competitive insights generator.

Reads the latest CSV/JSON dataset, builds business charts aligned to the
2.2 requirements, and materializes KPI/insights payloads for the PDF and
interactive dashboard.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from insights_utils import (
    PLATFORM_COLORS,
    SLA_MINUTES,
    DatasetViews,
    availability_matrix,
    compute_insights,
    eta_vs_promo_points,
    export_payload,
    heatmap_matrix,
    load_dataset,
    promo_distributions,
    summarize_platforms,
    zone_metrics,
)

OUTPUT_DIR = Path("output")
plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "white"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Competitive insights analysis")
    parser.add_argument("--source", help="Ruta al CSV/JSON a analizar", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Directorio donde guardar charts y payloads")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    views = load_dataset(args.source)
    summary = summarize_platforms(views)
    availability = availability_matrix(views)
    zones_df = zone_metrics(views)
    promo_dist = promo_distributions(views)
    scatter_df = eta_vs_promo_points(views)

    print("\n[INFO] Dataset cargado desde:", views.source_path)
    print(f"   - direcciones únicas: {views.raw['address_id'].nunique()} | zonas: {views.raw['zone'].nunique()} | plataformas: {len(summary)}")

    charts = []
    charts.append(plot_eta_by_zone(zones_df, summary, output_dir))
    charts.append(plot_rating_by_city(views, summary, output_dir))
    charts.append(plot_promo_hook_by_zone(zones_df, summary, output_dir))
    charts.append(plot_promo_distribution(promo_dist, summary, output_dir))
    charts.append(plot_bigmac_price_positioning(views, summary, output_dir))
    charts.append(plot_service_fee_by_zone(zones_df, summary, output_dir))
    charts.append(plot_total_price_by_zone(zones_df, summary, output_dir))
    charts.append(plot_eta_vs_promo_scatter(scatter_df, output_dir))
    charts.append(plot_eta_heatmap(views, output_dir))
    charts.append(plot_price_heatmap(views, output_dir))
    charts.append(plot_delivery_fee_comparison(zones_df, summary, output_dir))
    charts.append(plot_wealthy_vs_nonwealthy(views, summary, output_dir))
    charts.append(plot_three_products_comparison(views, summary, output_dir))
    charts.append(plot_total_cost_breakdown(views, summary, output_dir))

    meta = {
        "source": str(views.source_path),
        "generated_at": datetime.now(UTC).isoformat(),
        "addresses": int(views.raw["address_id"].nunique()),
        "zones": int(views.raw["zone"].nunique()),
        "cities": sorted(set(views.raw["city"].dropna().tolist())),
    }
    kpis_payload = {
        "meta": meta,
        "platforms": summary,
        "availability": availability,
        "charts": [c for c in charts if c],
    }
    export_payload(output_dir / "kpis.json", kpis_payload)

    insights = compute_insights(summary, availability, views)
    export_payload(output_dir / "top_insights.json", {"insights": insights})

    print(f"\n[OK] Análisis listo -> {output_dir}")
    print("   - KPIs: output/kpis.json")
    print("   - Insights: output/top_insights.json")
    print("   - Charts:")
    for chart in charts:
        if chart:
            print(f"     - {chart}")


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def plot_eta_by_zone(zones: pd.DataFrame, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    data = zones.dropna(subset=["eta_min"])
    if data.empty:
        return None

    platforms = list(summary.keys())
    zones_order = (
        data.groupby("zone")["eta_min"].mean().sort_values().index.tolist()
    )
    fig_height = max(6, len(zones_order) * 0.35)
    fig, ax = plt.subplots(figsize=(11, fig_height))

    base_height = 0.8
    bar_height = base_height / max(len(platforms), 1)
    positions = np.arange(len(zones_order))

    for idx, plat in enumerate(platforms):
        color = PLATFORM_COLORS.get(plat, "#5B8EF0")
        subset = (
            data[data["platform"] == plat]
            .set_index("zone")["eta_min"]
            .reindex(zones_order)
        )
        offset = (idx - (len(platforms) - 1) / 2) * bar_height
        ax.barh(
            positions + offset,
            subset.values,
            height=bar_height * 0.9,
            label=summary[plat]["label"],
            color=color,
            edgecolor="white",
        )

    ax.axvline(SLA_MINUTES, color="#f05b5b", linestyle="--", linewidth=1.2)
    ax.text(SLA_MINUTES + 0.5, max(ax.get_ylim()) - 0.5, "SLA 30 min", color="#f05b5b", fontsize=9)
    ax.set_yticks(positions)
    ax.set_yticklabels(zones_order, fontsize=9)
    ax.set_xlabel("Minutos")
    ax.set_title("ETA promedio por zona (se excluye restaurant_available=False)")
    ax.grid(axis="x", color="#e2e6ef", linestyle="--", linewidth=0.6)
    ax.legend(loc="best", frameon=False)
    fig.tight_layout()

    path = output_dir / "chart_eta_by_zone.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_rating_by_city(views: DatasetViews, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    data = (
        views.success
        .groupby(["city", "platform"], dropna=False)["rating"].mean()
        .reset_index()
        .dropna(subset=["rating"])
    )
    if data.empty:
        return None

    platforms = list(summary.keys())
    cities = data["city"].fillna("Sin ciudad").unique().tolist()
    fig, ax = plt.subplots(figsize=(10, 5))

    width = 0.8 / max(len(platforms), 1)
    positions = np.arange(len(cities))
    for idx, plat in enumerate(platforms):
        color = PLATFORM_COLORS.get(plat, "#5B8EF0")
        vals = (
            data[data["platform"] == plat]
            .set_index("city")["rating"]
            .reindex(cities)
            .values
        )
        ax.bar(
            positions + idx * width,
            vals,
            width=width,
            label=summary[plat]["label"],
            color=color,
            edgecolor="white",
        )

    ax.set_xticks(positions + width * (len(platforms) - 1) / 2)
    ax.set_xticklabels([c.replace("Ciudad de Mexico", "CDMX") for c in cities], rotation=15)
    ax.set_ylim(3, 5)
    ax.set_ylabel("Rating promedio (escala 3-5)")
    ax.set_title("Rating por ciudad y plataforma")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="#d9deea")
    ax.legend(frameon=False)
    fig.tight_layout()

    path = output_dir / "chart_rating_by_city.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_promo_hook_by_zone(zones: pd.DataFrame, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    data = zones.dropna(subset=["promo_general_pct"])
    if data.empty:
        return None

    platforms = list(summary.keys())
    zones_order = (
        data.groupby("zone")["promo_general_pct"].mean().sort_values(ascending=False).index.tolist()
    )
    fig_height = max(6, len(zones_order) * 0.35)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    bar_height = 0.8 / max(len(platforms), 1)
    pos = np.arange(len(zones_order))

    for idx, plat in enumerate(platforms):
        color = PLATFORM_COLORS.get(plat, "#5B8EF0")
        subset = (
            data[data["platform"] == plat]
            .set_index("zone")["promo_general_pct"]
            .reindex(zones_order)
        )
        offset = (idx - (len(platforms) - 1) / 2) * bar_height
        ax.barh(
            pos + offset,
            subset.values,
            height=bar_height * 0.9,
            label=summary[plat]["label"],
            color=color,
            edgecolor="white",
        )

    ax.set_xlabel("% descuento visible (promo hook)")
    ax.set_yticks(pos)
    ax.set_yticklabels(zones_order, fontsize=9)
    ax.set_title("Promo hook por zona")
    ax.grid(axis="x", linestyle="--", linewidth=0.5, color="#dfe3ef")
    ax.legend(frameon=False)
    fig.tight_layout()

    path = output_dir / "chart_promo_hook_by_zone.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_promo_distribution(promo_dist: Dict[str, List[float]], summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    data = {plat: vals for plat, vals in promo_dist.items() if vals}
    if len(data) < 1:
        return None

    fig, ax = plt.subplots(figsize=(9, 5))
    labels = [summary[p]["label"] for p in data.keys()]
    box = ax.boxplot(data.values(), patch_artist=True, labels=labels)
    for patch, plat in zip(box["boxes"], data.keys()):
        patch.set_facecolor(PLATFORM_COLORS.get(plat, "#5B8EF0"))
        patch.set_alpha(0.5)
        patch.set_edgecolor("white")
    ax.set_ylabel("% descuento hook")
    ax.set_title("Distribución de promo % (mínimo-mediana-máximo)")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="#dfe3ef")
    fig.tight_layout()

    path = output_dir / "chart_promo_distribution.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_bigmac_price_positioning(views: DatasetViews, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    data = views.success.copy()
    if data.empty:
        return None

    stats = []
    for plat, grp in data.groupby("platform"):
        stats.append(
            {
                "platform": plat,
                "label": summary[plat]["label"],
                "original": grp.get("bm_price_orig", pd.Series(dtype=float)).mean(),
                "discounted": grp.get("bm_effective_price", pd.Series(dtype=float)).mean(),
            }
        )
    df = pd.DataFrame(stats).dropna(subset=["original", "discounted"], how="all")
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(df))
    width = 0.35
    ax.bar(x - width / 2, df["original"], width=width, label="Precio base", color="#ccd3e6")
    ax.bar(x + width / 2, df["discounted"], width=width, label="Con promo", color="#5b8ef0")
    ax.set_xticks(x)
    ax.set_xticklabels(df["label"], rotation=15)
    ax.set_ylabel("MXN")
    ax.set_title("Combo Big Mac · precio original vs con descuento")
    for idx, row in df.iterrows():
        if pd.notna(row["original"]):
            ax.text(idx - width / 2, row["original"] + 1, f"${row['original']:.0f}", ha="center", fontsize=8)
        if pd.notna(row["discounted"]):
            ax.text(idx + width / 2, row["discounted"] + 1, f"${row['discounted']:.0f}", ha="center", fontsize=8, fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#e4e7f1")
    fig.tight_layout()

    path = output_dir / "chart_bigmac_price_positioning.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_service_fee_by_zone(zones: pd.DataFrame, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    data = zones.dropna(subset=["service_fee_model"])
    if data.empty:
        return None

    platforms = list(summary.keys())
    zones_order = (
        data.groupby("zone")["service_fee_model"].mean().sort_values().index.tolist()
    )
    fig_height = max(6, len(zones_order) * 0.35)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    bar_height = 0.8 / max(len(platforms), 1)
    pos = np.arange(len(zones_order))

    for idx, plat in enumerate(platforms):
        color = PLATFORM_COLORS.get(plat, "#5B8EF0")
        subset = (
            data[data["platform"] == plat]
            .set_index("zone")["service_fee_model"]
            .reindex(zones_order)
        )
        offset = (idx - (len(platforms) - 1) / 2) * bar_height
        ax.barh(
            pos + offset,
            subset.values,
            height=bar_height * 0.9,
            label=summary[plat]["label"],
            color=color,
            edgecolor="white",
        )

    ax.set_xlabel("MXN (service fee estimado = subtotal * tasa fija)")
    ax.set_yticks(pos)
    ax.set_yticklabels(zones_order, fontsize=9)
    ax.set_title("Service fee por zona · Rappi 10% · Uber Eats 15% · DiDi 8%")
    ax.grid(axis="x", linestyle="--", linewidth=0.5, color="#e0e4f0")
    ax.legend(frameon=False)
    fig.tight_layout()

    path = output_dir / "chart_service_fee_by_zone.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_total_price_by_zone(zones: pd.DataFrame, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    data = zones.dropna(subset=["total_estimated"])
    if data.empty:
        return None

    platforms = list(summary.keys())
    zones_order = (
        data.groupby("zone")["total_estimated"].mean().sort_values().index.tolist()
    )
    fig_height = max(6, len(zones_order) * 0.35)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    bar_height = 0.8 / max(len(platforms), 1)
    pos = np.arange(len(zones_order))

    for idx, plat in enumerate(platforms):
        color = PLATFORM_COLORS.get(plat, "#5B8EF0")
        subset = (
            data[data["platform"] == plat]
            .set_index("zone")["total_estimated"]
            .reindex(zones_order)
        )
        offset = (idx - (len(platforms) - 1) / 2) * bar_height
        ax.barh(
            pos + offset,
            subset.values,
            height=bar_height * 0.9,
            label=summary[plat]["label"],
            color=color,
            edgecolor="white",
        )

    ax.set_xlabel("MXN (subtotal + delivery + service fee estimado)")
    ax.set_yticks(pos)
    ax.set_yticklabels(zones_order, fontsize=9)
    ax.set_title("Total estimado al usuario por zona")
    ax.grid(axis="x", linestyle="--", linewidth=0.5, color="#e0e4f0")
    ax.legend(frameon=False)
    fig.tight_layout()

    path = output_dir / "chart_total_price_by_zone.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_eta_vs_promo_scatter(scatter_df: pd.DataFrame, output_dir: Path) -> Optional[str]:
    if scatter_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(7, 5))
    for plat, grp in scatter_df.groupby("platform"):
        color = PLATFORM_COLORS.get(plat, "#5B8EF0")
        ax.scatter(grp["eta_min"], grp["promo_general_pct"], label=grp["platform_label"].iloc[0], color=color, alpha=0.7)
    ax.set_xlabel("ETA (min)")
    ax.set_ylabel("Promo hook (%)")
    ax.set_title("Scatter: ¿compensan tardanza con descuento?")
    ax.grid(True, linestyle="--", linewidth=0.4, color="#dfe4f0")
    ax.legend(frameon=False)
    fig.tight_layout()

    path = output_dir / "chart_eta_vs_promo_scatter.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_eta_heatmap(views: DatasetViews, output_dir: Path) -> Optional[str]:
    pivot = heatmap_matrix(views, "eta_min")
    if pivot.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, max(4, len(pivot) * 0.35)))
    im = ax.imshow(pivot.values, cmap="RdYlGn_r", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([views.raw.loc[views.raw["platform"] == c, "platform_label"].iloc[0] if not views.raw.loc[views.raw["platform"] == c, "platform_label"].empty else c.title() for c in pivot.columns], rotation=15)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Heatmap ETA por zona (verde = más rápido)")
    fig.colorbar(im, ax=ax, label="Minutos")
    fig.tight_layout()

    path = output_dir / "chart_eta_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_price_heatmap(views: DatasetViews, output_dir: Path) -> Optional[str]:
    pivot = heatmap_matrix(views, "bm_effective_price")
    if pivot.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, max(4, len(pivot) * 0.35)))
    im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([views.raw.loc[views.raw["platform"] == c, "platform_label"].iloc[0] if not views.raw.loc[views.raw["platform"] == c, "platform_label"].empty else c.title() for c in pivot.columns], rotation=15)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Heatmap precio Big Mac con descuento (oscuro = más caro)")
    fig.colorbar(im, ax=ax, label="MXN")
    fig.tight_layout()

    path = output_dir / "chart_price_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_delivery_fee_comparison(zones: pd.DataFrame, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    """Delivery fee por zona y plataforma – permite ver qué app cobra más envío."""
    data = zones.dropna(subset=["delivery_fee"])
    if data.empty:
        return None

    platforms = list(summary.keys())
    zones_order = data.groupby("zone")["delivery_fee"].mean().sort_values().index.tolist()
    fig_height = max(6, len(zones_order) * 0.35)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    bar_height = 0.8 / max(len(platforms), 1)
    pos = np.arange(len(zones_order))

    for idx, plat in enumerate(platforms):
        color = PLATFORM_COLORS.get(plat, "#5B8EF0")
        subset = (
            data[data["platform"] == plat]
            .set_index("zone")["delivery_fee"]
            .reindex(zones_order)
        )
        offset = (idx - (len(platforms) - 1) / 2) * bar_height
        ax.barh(
            pos + offset,
            subset.values,
            height=bar_height * 0.9,
            label=summary[plat]["label"],
            color=color,
            edgecolor="white",
        )

    ax.set_xlabel("Delivery Fee (MXN)")
    ax.set_yticks(pos)
    ax.set_yticklabels(zones_order, fontsize=9)
    ax.set_title("Delivery Fee por zona y plataforma\nCuánto cobra cada app por envío en cada zona")
    ax.grid(axis="x", linestyle="--", linewidth=0.5, color="#e0e4f0")
    ax.legend(frameon=False)
    fig.tight_layout()

    path = output_dir / "chart_delivery_fee_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_wealthy_vs_nonwealthy(views: DatasetViews, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    """Compara métricas clave entre zonas Wealthy y Non Wealthy por plataforma."""
    data = views.success.copy()
    if data.empty or "zone_type" not in data.columns:
        return None

    metrics = [
        ("total_estimated", "Total Estimado (MXN)"),
        ("eta_min", "ETA (min)"),
        ("delivery_fee", "Delivery Fee (MXN)"),
        ("promo_general_pct", "Promo Hook (%)"),
    ]
    platforms = list(summary.keys())
    n_metrics = len(metrics)

    fig, axes = plt.subplots(1, n_metrics, figsize=(4 * n_metrics, 5), sharey=False)
    if n_metrics == 1:
        axes = [axes]

    width = 0.35
    for ax_idx, (col, label) in enumerate(metrics):
        ax = axes[ax_idx]
        x = np.arange(len(platforms))
        wealthy_vals = []
        nonwealthy_vals = []
        for plat in platforms:
            plat_data = data[data["platform"] == plat]
            w = plat_data.loc[plat_data["zone_type"] == "Wealthy", col].dropna()
            nw = plat_data.loc[plat_data["zone_type"] == "Non Wealthy", col].dropna()
            wealthy_vals.append(float(w.mean()) if not w.empty else 0)
            nonwealthy_vals.append(float(nw.mean()) if not nw.empty else 0)

        bars1 = ax.bar(x - width / 2, wealthy_vals, width, label="Wealthy", color="#5B8EF0", edgecolor="white")
        bars2 = ax.bar(x + width / 2, nonwealthy_vals, width, label="Non Wealthy", color="#F5A623", edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels([summary[p]["label"] for p in platforms], rotation=20, fontsize=8)
        ax.set_title(label, fontsize=10)
        ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#e4e7f1")
        if ax_idx == 0:
            ax.legend(fontsize=8, frameon=False)

        for bars in [bars1, bars2]:
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                            f"{h:.0f}", ha="center", fontsize=7)

    fig.suptitle("Variabilidad Geográfica: Wealthy vs Non Wealthy\n¿Cambia la competitividad según el nivel socioeconómico de la zona?",
                 fontsize=11, fontweight="bold", y=1.02)
    fig.tight_layout()

    path = output_dir / "chart_wealthy_vs_nonwealthy.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_three_products_comparison(views: DatasetViews, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    """Compara precios de los 3 productos (Big Mac, HDQ, Coca-Cola) por plataforma."""
    data = views.success.copy()
    if data.empty:
        return None

    products = [
        ("bm_effective_price", "bm_price_orig", "Combo Big Mac\nMediano"),
        ("hdq_effective_price", "hdq_price_orig", "Hamburguesa Doble\ncon Queso"),
        ("cc_effective_price", "cc_price_orig", "Coca-Cola\nMediana"),
    ]
    platforms = list(summary.keys())

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)

    for ax_idx, (eff_col, orig_col, title) in enumerate(products):
        ax = axes[ax_idx]
        x = np.arange(len(platforms))
        width = 0.35
        orig_vals = []
        eff_vals = []
        for plat in platforms:
            plat_data = data[data["platform"] == plat]
            orig = plat_data[orig_col].dropna().mean() if orig_col in plat_data.columns else np.nan
            eff = plat_data[eff_col].dropna().mean() if eff_col in plat_data.columns else np.nan
            orig_vals.append(orig)
            eff_vals.append(eff)

        ax.bar(x - width / 2, orig_vals, width, label="Precio base", color="#ccd3e6", edgecolor="white")
        ax.bar(x + width / 2, eff_vals, width, label="Con promo", color="#5b8ef0", edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels([summary[p]["label"] for p in platforms], rotation=15, fontsize=9)
        ax.set_ylabel("MXN")
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#e4e7f1")

        for i, (o, e) in enumerate(zip(orig_vals, eff_vals)):
            if not np.isnan(o):
                ax.text(i - width / 2, o + 1, f"${o:.0f}", ha="center", fontsize=7)
            if not np.isnan(e):
                ax.text(i + width / 2, e + 1, f"${e:.0f}", ha="center", fontsize=7, fontweight="bold")

        if ax_idx == 0:
            ax.legend(fontsize=8, frameon=False)

    fig.suptitle("Comparativa de precios: 3 productos clave por plataforma\nPrecio base vs precio con promoción aplicada",
                 fontsize=11, fontweight="bold", y=1.02)
    fig.tight_layout()

    path = output_dir / "chart_three_products_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


def plot_total_cost_breakdown(views: DatasetViews, summary: Dict[str, Dict], output_dir: Path) -> Optional[str]:
    """Desglose del costo total: subtotal + delivery fee + service fee por plataforma."""
    data = views.success.copy()
    if data.empty:
        return None

    platforms = list(summary.keys())
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(platforms))
    width = 0.5

    subtotals = []
    del_fees = []
    svc_fees = []
    for plat in platforms:
        plat_data = data[data["platform"] == plat]
        subtotals.append(plat_data["subtotal"].dropna().mean() if "subtotal" in plat_data.columns else 0)
        del_fees.append(plat_data["delivery_fee"].dropna().mean() if "delivery_fee" in plat_data.columns else 0)
        svc_col = "service_fee_effective" if "service_fee_effective" in plat_data.columns else "service_fee_model"
        svc_fees.append(plat_data[svc_col].dropna().mean() if svc_col in plat_data.columns else 0)

    subtotals = [0 if np.isnan(v) else v for v in subtotals]
    del_fees = [0 if np.isnan(v) else v for v in del_fees]
    svc_fees = [0 if np.isnan(v) else v for v in svc_fees]

    ax.bar(x, subtotals, width, label="Subtotal (productos)", color="#5b8ef0", edgecolor="white")
    ax.bar(x, del_fees, width, bottom=subtotals, label="Delivery Fee", color="#F5A623", edgecolor="white")
    bottoms2 = [s + d for s, d in zip(subtotals, del_fees)]
    ax.bar(x, svc_fees, width, bottom=bottoms2, label="Service Fee", color="#FF441F", edgecolor="white")

    totals = [s + d + f for s, d, f in zip(subtotals, del_fees, svc_fees)]
    for i, total in enumerate(totals):
        ax.text(i, total + 2, f"${total:.0f}", ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([summary[p]["label"] for p in platforms])
    ax.set_ylabel("MXN")
    ax.set_title("Desglose del costo total por plataforma\nSubtotal + Delivery Fee + Service Fee = lo que paga el usuario")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, color="#e4e7f1")
    fig.tight_layout()

    path = output_dir / "chart_total_cost_breakdown.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path.name


if __name__ == "__main__":
    main()
