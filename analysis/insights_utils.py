from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

SLA_MINUTES = 30
SERVICE_FEE_RATES = {
    "rappi": 0.10,
    "ubereats": 0.15,
    "uber eats": 0.15,
    "uber": 0.15,
    "didifood": 0.08,
    "didi": 0.08,
}
PLATFORM_ALIASES = {
    "uber eats": "ubereats",
    "uber": "ubereats",
    "didi food": "didifood",
    "didi": "didifood",
}
PLATFORM_LABELS = {
    "rappi": "Rappi",
    "ubereats": "Uber Eats",
    "didifood": "DiDi Food",
}
PLATFORM_COLORS = {
    "rappi": "#FF441F",
    "ubereats": "#06C167",
    "didifood": "#F5A623",
}
NUMERIC_COLS = [
    "rating",
    "eta_min",
    "delivery_fee_mxn",
    "delivery_fee",
    "promo_general_pct",
    "bm_price_orig",
    "bm_price_disc",
    "bm_disc_pct",
    "hdq_price_orig",
    "hdq_price_disc",
    "hdq_disc_pct",
    "cc_price_orig",
    "cc_price_disc",
    "cc_disc_pct",
    "subtotal_mxn",
    "subtotal",
    "service_fee_mxn",
    "service_fee",
    "total_estimated_mxn",
    "total_estimated",
]
DISCOUNT_COLS = ["bm_disc_pct", "hdq_disc_pct", "cc_disc_pct", "promo_general_pct"]
PRICE_PAIRS = [
    ("bm_price_disc", "bm_price_orig"),
    ("hdq_price_disc", "hdq_price_orig"),
    ("cc_price_disc", "cc_price_orig"),
]


@dataclass
class DatasetViews:
    raw: pd.DataFrame
    success: pd.DataFrame
    source_path: Path


def load_dataset(source: Optional[str] = None) -> DatasetViews:
    path = _resolve_source(source)
    if path.suffix.lower() == ".csv":
        df = _load_csv(path)
    elif path.suffix.lower() == ".json":
        df = _load_json(path)
    else:
        raise ValueError(f"Unsupported dataset format: {path.suffix}")

    df = _normalize_columns(df)
    success = df[(df["status"] == "success") & (df["restaurant_available"] != False)]
    return DatasetViews(raw=df, success=success, source_path=path)


def summarize_platforms(views: DatasetViews) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for plat, grp in views.raw.groupby("platform"):
        label = grp["platform_label"].iloc[0] if not grp.empty else plat.title()
        success = views.success[views.success["platform"] == plat]
        summary[plat] = {
            "label": label,
            "records_total": int(len(grp)),
            "records_success": int(len(success)),
            "coverage_pct": float((len(success) / len(grp) * 100) if len(grp) else 0),
            "zones": int(success["zone"].nunique()),
            "cities": int(success["city"].nunique()),
            "eta_avg": _safe_mean(success["eta_min"]),
            "eta_p90": _safe_quantile(success["eta_min"], 0.9),
            "rating_avg": _safe_mean(success["rating"]),
            "promo_hook_avg": _safe_mean(success["promo_general_pct"]),
            "promo_hook_p75": _safe_quantile(success["promo_general_pct"], 0.75),
            "promo_presence_pct": _share(success["promo_general_pct"] > 0),
            "bm_price_avg": _safe_mean(success["bm_effective_price"]),
            "bm_discount_pct_avg": _safe_mean(success["bm_disc_pct"]),
            "bm_discount_presence_pct": _share(success["bm_disc_pct"] > 0),
            "delivery_fee_avg": _safe_mean(success["delivery_fee"]),
            "service_fee_avg": _safe_mean(success["service_fee_effective"]),
            "service_fee_model_avg": _safe_mean(success["service_fee_model"]),
            "subtotal_avg": _safe_mean(success["subtotal"]),
            "total_avg": _safe_mean(success["total_estimated"]),
            "hdq_price_avg": _safe_mean(success["hdq_effective_price"]),
            "hdq_price_orig_avg": _safe_mean(success["hdq_price_orig"]),
            "hdq_discount_pct_avg": _safe_mean(success["hdq_disc_pct"]),
            "cc_price_avg": _safe_mean(success["cc_effective_price"]),
            "cc_price_orig_avg": _safe_mean(success["cc_price_orig"]),
            "cc_discount_pct_avg": _safe_mean(success["cc_disc_pct"]),
            "wealthy_total_avg": _safe_mean(success.loc[success["zone_type"] == "Wealthy", "total_estimated"]),
            "non_wealthy_total_avg": _safe_mean(success.loc[success["zone_type"] == "Non Wealthy", "total_estimated"]),
            "wealthy_eta_avg": _safe_mean(success.loc[success["zone_type"] == "Wealthy", "eta_min"]),
            "non_wealthy_eta_avg": _safe_mean(success.loc[success["zone_type"] == "Non Wealthy", "eta_min"]),
            "wealthy_delivery_fee_avg": _safe_mean(success.loc[success["zone_type"] == "Wealthy", "delivery_fee"]),
            "non_wealthy_delivery_fee_avg": _safe_mean(success.loc[success["zone_type"] == "Non Wealthy", "delivery_fee"]),
        }
    return summary


def availability_matrix(views: DatasetViews) -> Dict[str, Dict[str, int]]:
    matrix: Dict[str, Dict[str, int]] = {}
    for plat, grp in views.raw.groupby("platform"):
        label = grp["platform_label"].iloc[0] if not grp.empty else plat.title()
        status_counts = grp.groupby("status").size().to_dict()
        matrix[plat] = {
            "label": label,
            "statuses": {k: int(v) for k, v in status_counts.items()},
            "restaurant_unavailable": int((grp["restaurant_available"] == False).sum()),
            "addresses_missing": sorted(grp.loc[grp["restaurant_available"] == False, "address_id"].dropna().unique().tolist()),
        }
    return matrix


def zone_metrics(views: DatasetViews) -> pd.DataFrame:
    agg_cols = {
        "eta_min": "mean",
        "promo_general_pct": "mean",
        "bm_effective_price": "mean",
        "hdq_effective_price": "mean",
        "cc_effective_price": "mean",
        "promo_hook_flag": "mean",
        "total_estimated": "mean",
        "service_fee_effective": "mean",
        "service_fee_model": "mean",
        "delivery_fee": "mean",
    }
    present = {k: v for k, v in agg_cols.items() if k in views.success.columns}
    agg = (
        views.success
        .groupby(["zone", "city", "zone_type", "platform"], dropna=False)
        .agg(present)
        .reset_index()
    )
    return agg


def promo_distributions(views: DatasetViews) -> Dict[str, List[float]]:
    d: Dict[str, List[float]] = {}
    for plat, grp in views.success.groupby("platform"):
        d[plat] = grp["promo_general_pct"].dropna().tolist()
    return d


def eta_vs_promo_points(views: DatasetViews) -> pd.DataFrame:
    cols = ["platform", "platform_label", "zone", "eta_min", "promo_general_pct"]
    return views.success[cols].dropna(subset=["eta_min", "promo_general_pct"]).copy()


def heatmap_matrix(views: DatasetViews, value_col: str) -> pd.DataFrame:
    cols = ["zone", "platform", value_col]
    data = views.success[cols].dropna(subset=[value_col])
    if data.empty:
        return pd.DataFrame()
    return data.pivot_table(index="zone", columns="platform", values=value_col, aggfunc="mean")


def compute_insights(summary: Dict[str, Dict[str, float]], availability: Dict[str, Dict[str, int]], views: DatasetViews) -> List[Dict[str, str]]:
    insights: List[Dict[str, str]] = []
    if summary:
        price_insight = _price_positioning_insight(summary)
        if price_insight:
            insights.append(price_insight)
        operational = _operational_insight(summary)
        if operational:
            insights.append(operational)
        promo = _promo_strategy_insight(summary)
        if promo:
            insights.append(promo)
        fees = _fee_structure_insight(summary)
        if fees:
            insights.append(fees)
        geo = _geographic_variability_insight(summary)
        if geo:
            insights.append(geo)
    availability_gap = _availability_insight(availability)
    if availability_gap:
        insights.append(availability_gap)
    return insights[:5]


def export_payload(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _resolve_source(source: Optional[str]) -> Path:
    if source:
        candidate = Path(source)
        if not candidate.exists():
            raise FileNotFoundError(f"Dataset not found: {source}")
        return candidate

    data_dir = Path("data")
    priority = [
        data_dir / "competitive_data_with_didi.csv",
    ]
    priority += sorted(data_dir.glob("competitive_data_*.csv"), reverse=True)
    priority += sorted(data_dir.glob("competitive_data_*.json"), reverse=True)
    for path in priority:
        if path.exists():
            return path
    raise FileNotFoundError("No dataset found under data/ directory")


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _load_json(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    rows: List[Dict] = []
    for r in raw:
        base = {
            "scraped_at": r.get("scraped_at"),
            "address_id": r.get("address_id"),
            "city": r.get("city"),
            "zone": r.get("zone"),
            "zone_type": r.get("zone_type"),
        }
        for plat, payload in r.items():
            if plat in {"address_id", "city", "zone", "zone_type", "scraped_at"}:
                continue
            if not isinstance(payload, dict):
                continue
            row = {**base, "platform": plat}
            row.update({
                "status": payload.get("status"),
                "restaurant_available": payload.get("restaurant_available", True),
                "rating": payload.get("rating"),
                "eta_min": payload.get("eta_min"),
                "delivery_fee_mxn": payload.get("delivery_fee"),
                "promo_general_pct": payload.get("promo_general_pct"),
                "subtotal_mxn": payload.get("subtotal"),
                "service_fee_mxn": payload.get("service_fee_estimated"),
                "total_estimated_mxn": payload.get("total_estimated"),
            })
            products = {p.get("name"): p for p in payload.get("products", [])}
            combo = products.get("Combo Big Mac mediano", {})
            hdq = products.get("Hamburguesa doble con queso", {})
            coke = products.get("Coca-Cola mediana", {})
            row.update({
                "bm_price_orig": combo.get("price_original"),
                "bm_price_disc": combo.get("price_discounted"),
                "bm_disc_pct": combo.get("discount_pct"),
                "hdq_price_orig": hdq.get("price_original"),
                "hdq_price_disc": hdq.get("price_discounted"),
                "hdq_disc_pct": hdq.get("discount_pct"),
                "cc_price_orig": coke.get("price_original"),
                "cc_price_disc": coke.get("price_discounted"),
                "cc_disc_pct": coke.get("discount_pct"),
            })
            rows.append(row)
    return pd.DataFrame(rows)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data.columns = [c.strip().lower() for c in data.columns]
    rename_map = {
        "delivery_fee_mxn": "delivery_fee",
        "service_fee_mxn": "service_fee",
        "subtotal_mxn": "subtotal",
        "total_estimated_mxn": "total_estimated",
    }
    data = data.rename(columns=rename_map)

    if "platform" not in data:
        raise ValueError("Dataset must include platform column")

    data["platform"] = (
        data["platform"].astype(str).str.strip().str.lower().map(PLATFORM_ALIASES).fillna(data["platform"].astype(str).str.strip().str.lower())
    )
    data["platform_label"] = data["platform"].map(PLATFORM_LABELS).fillna(data["platform"].str.title())
    data["status"] = data.get("status", "success").astype(str).str.lower()
    if "restaurant_available" in data:
        data["restaurant_available"] = data["restaurant_available"].apply(_to_bool)
    else:
        data["restaurant_available"] = True

    for col in NUMERIC_COLS:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    for disc_col in DISCOUNT_COLS:
        if disc_col in data.columns:
            data[disc_col] = data[disc_col].fillna(0)

    for disc, orig in PRICE_PAIRS:
        if disc in data.columns and orig in data.columns:
            data[disc] = data[disc].fillna(data[orig])

    if "delivery_fee" not in data:
        data["delivery_fee"] = np.nan

    data["promo_hook_flag"] = data.get("promo_general_pct", 0).fillna(0) > 0
    data["bm_effective_price"] = data.get("bm_price_disc", data.get("bm_price_orig"))
    data["hdq_effective_price"] = data.get("hdq_price_disc", data.get("hdq_price_orig"))
    data["cc_effective_price"] = data.get("cc_price_disc", data.get("cc_price_orig"))

    rates = data["platform"].map(SERVICE_FEE_RATES).fillna(0.10)
    data["service_fee_model"] = np.where(
        data.get("subtotal").notna(),
        data["subtotal"].fillna(0) * rates,
        np.nan,
    )
    data["service_fee_effective"] = data.get("service_fee")
    mask_missing_fee = data["service_fee_effective"].isna()
    data.loc[mask_missing_fee, "service_fee_effective"] = data.loc[mask_missing_fee, "service_fee_model"]

    return data


def _price_positioning_insight(summary: Dict[str, Dict[str, float]]) -> Optional[Dict[str, str]]:
    totals = {k: v["total_avg"] for k, v in summary.items() if v.get("total_avg")}
    if len(totals) < 2:
        return None
    cheapest = min(totals, key=totals.get)
    priciest = max(totals, key=totals.get)
    gap = totals[priciest] - totals[cheapest]
    gap_pct = (gap / totals[cheapest] * 100) if totals[cheapest] else 0
    rappi = summary.get("rappi")
    if rappi and rappi["total_avg"]:
        comparison = rappi["total_avg"] - totals[cheapest]
        if comparison <= 1:
            finding = (
                f"{rappi['label']} mantiene el ticket medio más bajo (${rappi['total_avg']:.0f} MXN) y deja una brecha de ${gap:.0f} vs {summary[priciest]['label']}"
            )
            recommendation = "Usar esta ventana de precio para reforzar comunicaciones de 'mejor precio garantizado' en QSR."
        else:
            finding = (
                f"{rappi['label']} promedia ${rappi['total_avg']:.0f} MXN vs {summary[cheapest]['label']} en ${totals[cheapest]:.0f}; gap de ${comparison:.0f} ({comparison / totals[cheapest] * 100:.1f}%)."
            )
            recommendation = "Evaluar subsidios tácticos en zonas con elasticidad alta o remover delivery fee en horarios pico."
    else:
        finding = (
            f"Ticket competitivo: {summary[cheapest]['label']} lidera con ${totals[cheapest]:.0f} MXN; {summary[priciest]['label']} queda {gap_pct:.1f}% arriba."
        )
        recommendation = "Mapear si la brecha responde a fees o a menor agresividad promocional y ajustar la mezcla."
    impact = "El precio total percibido define la elección de plataforma; una brecha >5% desplaza share hacia el competidor más barato."
    return {
        "title": "Posicionamiento de precios",
        "finding": finding,
        "impact": impact,
        "recommendation": recommendation,
    }


def _operational_insight(summary: Dict[str, Dict[str, float]]) -> Optional[Dict[str, str]]:
    etas = {k: v["eta_avg"] for k, v in summary.items() if v.get("eta_avg")}
    if len(etas) < 2:
        return None
    fastest = min(etas, key=etas.get)
    slowest = max(etas, key=etas.get)
    gap = etas[slowest] - etas[fastest]
    ratings = {k: v["rating_avg"] for k, v in summary.items() if v.get("rating_avg")}
    top_rating = max(ratings, key=ratings.get) if ratings else fastest
    finding = (
        f"{summary[fastest]['label']} promete {etas[fastest]:.0f} min promedio vs {summary[slowest]['label']} {etas[slowest]:.0f} min (gap {gap:.0f} min). "
        f"En percepción de calidad, {summary[top_rating]['label']} lidera con rating {ratings.get(top_rating, 0):.1f}."
    )
    impact = "Cada 5 minutos adicionales de ETA reduce la conversión ~3-4 p.p.; el rating funciona como proxy de confianza y recompra."
    recommendation = "Reforzar oferta en las zonas con peores ETAs (bonos a repartidores) y lanzar campaña de reviews para cerrar la brecha de percepción."
    return {
        "title": "Ventaja operacional",
        "finding": finding,
        "impact": impact,
        "recommendation": recommendation,
    }


def _promo_strategy_insight(summary: Dict[str, Dict[str, float]]) -> Optional[Dict[str, str]]:
    promos = {k: v["promo_hook_avg"] for k, v in summary.items() if v.get("promo_hook_avg") is not None}
    if len(promos) < 1:
        return None
    aggressive = max(promos, key=promos.get)
    conservative = min(promos, key=promos.get)
    finding = (
        f"{summary[aggressive]['label']} muestra hooks promedio de {promos[aggressive]:.0f}% y descuentos reales en Big Mac de {summary[aggressive]['bm_discount_pct_avg'] or 0:.0f}%. "
        f"{summary[conservative]['label']} apenas comunica {promos[conservative]:.0f}%."
    )
    impact = "La visibilidad del descuento en el feed es el driver #1 de CTR; menor agresividad implica menor share del restaurante destacado."
    recommendation = "Armar un playbook de promos visibles (bundle + cupones) por zona prioritaria y calendarizar ventanas de empuje donde Uber/DiDi son más agresivos."
    return {
        "title": "Estrategia promocional",
        "finding": finding,
        "impact": impact,
        "recommendation": recommendation,
    }


def _fee_structure_insight(summary: Dict[str, Dict[str, float]]) -> Optional[Dict[str, str]]:
    fees = {k: v["service_fee_model_avg"] for k, v in summary.items() if v.get("service_fee_model_avg")}
    deliveries = {k: v["delivery_fee_avg"] for k, v in summary.items() if v.get("delivery_fee_avg")}
    if not fees and not deliveries:
        return None
    target = max(fees, key=fees.get) if fees else max(deliveries, key=deliveries.get)
    ref = min(fees, key=fees.get) if fees else min(deliveries, key=deliveries.get)
    fee_gap = (fees.get(target, 0) - fees.get(ref, 0)) if fees else 0
    del_gap = (deliveries.get(target, 0) - deliveries.get(ref, 0)) if deliveries else 0
    finding = (
        f"La estructura de fees deja a {summary[target]['label']} ~${fee_gap:.0f} arriba en service fee y ${del_gap:.0f} en delivery vs {summary[ref]['label']}."
    )
    impact = "El usuario percibe el costo total; aun con precios de producto iguales, un fee más alto destruye la propuesta de valor."
    recommendation = "Definir reglas de subsidio de delivery fee por zona y monitorear agresividad de service fee en checkout para mantener paridad."
    return {
        "title": "Estructura de fees",
        "finding": finding,
        "impact": impact,
        "recommendation": recommendation,
    }


def _geographic_variability_insight(summary: Dict[str, Dict[str, float]]) -> Optional[Dict[str, str]]:
    diff_data = {}
    for plat, stats in summary.items():
        wealthy = stats.get("wealthy_total_avg")
        non = stats.get("non_wealthy_total_avg")
        if wealthy and non:
            diff_data[plat] = non - wealthy
    if not diff_data:
        return None
    largest = max(diff_data, key=lambda k: abs(diff_data[k]))
    delta = diff_data[largest]
    direction = "más caro" if delta > 0 else "más barato"
    finding = (
        f"{summary[largest]['label']} es {direction} ${abs(delta):.0f} en zonas Non Wealthy vs Wealthy, lo que sugiere subsidios desbalanceados."
    )
    impact = "Si las zonas de expansión pagan más, la elasticidad de demanda jugará en contra y cederemos share justo donde debemos crecer."
    recommendation = "Rediseñar la tabla de delivery/service fee por socioeconómico y monitorear competencia en colonias periféricas."
    return {
        "title": "Variabilidad geográfica",
        "finding": finding,
        "impact": impact,
        "recommendation": recommendation,
    }


def _availability_insight(availability: Dict[str, Dict[str, int]]) -> Optional[Dict[str, str]]:
    gaps = {}
    for plat, stats in availability.items():
        unavailable = stats.get("restaurant_unavailable", 0)
        partial = stats.get("statuses", {}).get("partial", 0)
        if unavailable or partial:
            gaps[plat] = unavailable + partial
    if not gaps:
        return None
    worst = max(gaps, key=gaps.get)
    stats = availability[worst]
    addresses = stats.get("addresses_missing", [])
    addr_text = ", ".join(addresses[:4]) + ("..." if len(addresses) > 4 else "")
    finding = (
        f"{stats['label']} no logró disponibilidad en {gaps[worst]} zonas (IDs: {addr_text})."
    )
    impact = "Sin cobertura el usuario asume que el restaurante no existe en la plataforma; perdemos share y NPS."
    recommendation = "Auditar el flujo de scraping/logística en esas zonas (puede ser ausencia real o bloqueo) y priorizar recuperación."
    return {
        "title": "Cobertura operacional",
        "finding": finding,
        "impact": impact,
        "recommendation": recommendation,
    }


def _safe_mean(series: pd.Series) -> Optional[float]:
    if series is None or series.empty:
        return None
    val = series.dropna()
    return float(val.mean()) if not val.empty else None


def _safe_quantile(series: pd.Series, q: float) -> Optional[float]:
    if series is None or series.empty:
        return None
    val = series.dropna()
    return float(val.quantile(q)) if not val.empty else None


def _share(mask: pd.Series) -> float:
    if mask is None or mask.empty:
        return 0.0
    return float(mask.mean() * 100)


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes"}:
            return True
        if v in {"false", "0", "no"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return True
