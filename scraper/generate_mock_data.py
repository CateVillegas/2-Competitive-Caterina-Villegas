"""
Plan B — Mock data generator
==============================
Genera datos simulados que replican la salida del scraper real.
Calibrado con precios y dinámicas reales del mercado MX (marzo 2026).

Uso: python scraper/generate_mock_data.py
"""

import csv
import json
import os
import random
from datetime import datetime
from pathlib import Path

import numpy as np

random.seed(42)
np.random.seed(42)

os.chdir(Path(__file__).parent.parent)
Path("data").mkdir(exist_ok=True)

ADDRESSES = [
    {"id": "MX_CDMX_01", "city": "Ciudad de Mexico", "zone": "Polanco",        "zone_type": "Wealthy"},
    {"id": "MX_CDMX_02", "city": "Ciudad de Mexico", "zone": "Condesa",        "zone_type": "Wealthy"},
    {"id": "MX_CDMX_03", "city": "Ciudad de Mexico", "zone": "Roma Norte",     "zone_type": "Wealthy"},
    {"id": "MX_CDMX_04", "city": "Ciudad de Mexico", "zone": "Santa Fe",       "zone_type": "Wealthy"},
    {"id": "MX_CDMX_05", "city": "Ciudad de Mexico", "zone": "Del Valle",      "zone_type": "Wealthy"},
    {"id": "MX_CDMX_06", "city": "Ciudad de Mexico", "zone": "Iztapalapa",     "zone_type": "Non Wealthy"},
    {"id": "MX_CDMX_07", "city": "Ciudad de Mexico", "zone": "Ecatepec",       "zone_type": "Non Wealthy"},
    {"id": "MX_CDMX_08", "city": "Ciudad de Mexico", "zone": "Tepito",         "zone_type": "Non Wealthy"},
    {"id": "MX_CDMX_09", "city": "Ciudad de Mexico", "zone": "Tlalpan",        "zone_type": "Non Wealthy"},
    {"id": "MX_GDL_01",  "city": "Guadalajara",      "zone": "Providencia",    "zone_type": "Wealthy"},
    {"id": "MX_GDL_02",  "city": "Guadalajara",      "zone": "Chapalita",      "zone_type": "Wealthy"},
    {"id": "MX_GDL_03",  "city": "Guadalajara",      "zone": "Zapopan Centro", "zone_type": "Wealthy"},
    {"id": "MX_GDL_04",  "city": "Guadalajara",      "zone": "Andares",        "zone_type": "Wealthy"},
    {"id": "MX_GDL_05",  "city": "Guadalajara",      "zone": "Oblatos",        "zone_type": "Non Wealthy"},
    {"id": "MX_GDL_06",  "city": "Guadalajara",      "zone": "Las Juntas",     "zone_type": "Non Wealthy"},
    {"id": "MX_GDL_07",  "city": "Guadalajara",      "zone": "Tonala",         "zone_type": "Non Wealthy"},
    {"id": "MX_MTY_01",  "city": "Monterrey",        "zone": "San Pedro",      "zone_type": "Wealthy"},
    {"id": "MX_MTY_02",  "city": "Monterrey",        "zone": "Valle",          "zone_type": "Wealthy"},
    {"id": "MX_MTY_03",  "city": "Monterrey",        "zone": "Cumbres",        "zone_type": "Wealthy"},
    {"id": "MX_MTY_04",  "city": "Monterrey",        "zone": "Tecnológico",    "zone_type": "Wealthy"},
    {"id": "MX_MTY_05",  "city": "Monterrey",        "zone": "Centrito Valle", "zone_type": "Wealthy"},
    {"id": "MX_MTY_06",  "city": "Monterrey",        "zone": "Independencia",  "zone_type": "Non Wealthy"},
    {"id": "MX_MTY_07",  "city": "Monterrey",        "zone": "Apodaca",        "zone_type": "Non Wealthy"},
    {"id": "MX_MTY_08",  "city": "Monterrey",        "zone": "Escobedo",       "zone_type": "Non Wealthy"},
    {"id": "MX_MTY_09",  "city": "Monterrey",        "zone": "Guadalupe",      "zone_type": "Non Wealthy"},
]

# ── Modelos de mercado calibrados con precios reales MX (mar 2026) ────────────
# Fuentes: precios publicados en apps, reseñas de usuarios, market research público
MODELS = {
    "rappi": {
        # Delivery fee: más alto en periféricas (insight clave)
        "fee_wealthy":     {"mean": 29, "std": 8},
        "fee_nonwealthy":  {"mean": 52, "std": 13},
        # ETA: moderado
        "eta_wealthy":     {"mean": 28, "std": 6},
        "eta_nonwealthy":  {"mean": 38, "std": 9},
        # Rating: consistente
        "rating":          {"mean": 4.3, "std": 0.2},
        # Precios de productos (MXN) — McDonald's en Rappi
        "combo_bigmac":    {"mean": 159, "std": 6},    # Home Office con Big Mac
        "hdq":             {"mean": 62,  "std": 4},    # Hamburguesa doble con queso
        "coke":            {"mean": 38,  "std": 3},    # Coca-Cola mediana
        # Descuentos por producto (probabilidad y magnitud)
        "combo_disc_prob": 0.45,
        "combo_disc_pct":  {"mean": 20, "std": 8},
        "hdq_disc_prob":   0.25,
        "hdq_disc_pct":    {"mean": 15, "std": 5},
        "coke_disc_prob":  0.15,
        "coke_disc_pct":   {"mean": 10, "std": 3},
        # Promo general del restaurante (el "hook")
        "promo_general_prob": 0.70,
        "promo_general_pct":  {"mean": 35, "std": 15},
        # Service fee rate (estimado)
        "service_fee_rate": 0.10,
    },
    "ubereats": {
        "fee_wealthy":     {"mean": 17, "std": 6},    # KEY: ~45% más barato que Rappi
        "fee_nonwealthy":  {"mean": 22, "std": 8},    # KEY: ~58% más barato que Rappi
        "eta_wealthy":     {"mean": 22, "std": 5},
        "eta_nonwealthy":  {"mean": 30, "std": 7},
        "rating":          {"mean": 4.4, "std": 0.15},
        "combo_bigmac":    {"mean": 162, "std": 5},
        "hdq":             {"mean": 64,  "std": 4},
        "coke":            {"mean": 39,  "std": 2},
        "combo_disc_prob": 0.60,
        "combo_disc_pct":  {"mean": 25, "std": 10},
        "hdq_disc_prob":   0.40,
        "hdq_disc_pct":    {"mean": 20, "std": 8},
        "coke_disc_prob":  0.20,
        "coke_disc_pct":   {"mean": 12, "std": 4},
        "promo_general_prob": 0.75,
        "promo_general_pct":  {"mean": 40, "std": 12},
        "service_fee_rate": 0.15,   # KEY: mayor service fee
    },
    "didifood": {
        "fee_wealthy":     {"mean": 24, "std": 7},
        "fee_nonwealthy":  {"mean": 38, "std": 11},
        "eta_wealthy":     {"mean": 30, "std": 7},
        "eta_nonwealthy":  {"mean": 40, "std": 10},
        "rating":          {"mean": 4.2, "std": 0.2},
        "combo_bigmac":    {"mean": 158, "std": 6},
        "hdq":             {"mean": 61,  "std": 4},
        "coke":            {"mean": 37,  "std": 3},
        "combo_disc_prob": 0.65,
        "combo_disc_pct":  {"mean": 30, "std": 10},
        "hdq_disc_prob":   0.45,
        "hdq_disc_pct":    {"mean": 22, "std": 7},
        "coke_disc_prob":  0.30,
        "coke_disc_pct":   {"mean": 15, "std": 5},
        "promo_general_prob": 0.80,   # KEY: más agresivo en promos
        "promo_general_pct":  {"mean": 45, "std": 12},
        "service_fee_rate": 0.08,     # KEY: menor service fee
    },
}

PLATFORMS = ["rappi", "ubereats", "didifood"]
RESTAURANT_NAMES = {
    "rappi":    ["McDonald's (Polanco)", "McDonald's Roma Norte", "McDonald's Insurgentes Sur", "McDonald's Santa Fe"],
    "ubereats": ["McDonald's Sears Insurgentes", "McDonald's Zona Rosa", "McDonald's Polanco", "McDonald's Marina Nacional"],
    "didifood": ["McDonald's (Sears Insurgente)", "McDonald's Insurgentes", "McDonald's Polanco", "McDonald's Reforma"],
}


def gen_product(m: dict, name: str, base_key: str, disc_prob_key: str, disc_pct_key: str) -> dict:
    price_orig = round(max(30, np.random.normal(m[base_key]["mean"], m[base_key]["std"])), 2)
    has_disc = random.random() < m[disc_prob_key]
    price_disc = None
    disc_pct = None
    if has_disc:
        disc_pct = round(max(5, np.random.normal(m[disc_pct_key]["mean"], m[disc_pct_key]["std"])), 1)
        price_disc = round(price_orig * (1 - disc_pct / 100), 2)
    return {
        "name": name,
        "price_original":   price_orig,
        "price_discounted": price_disc,
        "discount_pct":     disc_pct,
    }


def gen_platform(platform: str, zone_type: str) -> dict:
    m = MODELS[platform]
    is_wealthy = zone_type == "Wealthy"
    sfx = "wealthy" if is_wealthy else "nonwealthy"

    fee = round(max(0, np.random.normal(m[f"fee_{sfx}"]["mean"], m[f"fee_{sfx}"]["std"])), 2)
    eta = max(15, int(np.random.normal(m[f"eta_{sfx}"]["mean"], m[f"eta_{sfx}"]["std"])))
    rating = round(max(3.5, min(5.0, np.random.normal(m["rating"]["mean"], m["rating"]["std"]))), 1)

    promo_pct = None
    if random.random() < m["promo_general_prob"]:
        promo_pct = round(max(10, np.random.normal(m["promo_general_pct"]["mean"], m["promo_general_pct"]["std"])), 0)

    products = [
        gen_product(m, "Combo Big Mac mediano",    "combo_bigmac", "combo_disc_prob", "combo_disc_pct"),
        gen_product(m, "Hamburguesa doble con queso", "hdq",       "hdq_disc_prob",   "hdq_disc_pct"),
        gen_product(m, "Coca-Cola mediana",         "coke",         "coke_disc_prob",  "coke_disc_pct"),
    ]

    subtotal = sum(
        (p["price_discounted"] if p["price_discounted"] else p["price_original"])
        for p in products
    )
    subtotal = round(subtotal, 2)
    service_fee = round(subtotal * m["service_fee_rate"], 2)
    total = round(subtotal + fee + service_fee, 2)

    return {
        "platform":               platform,
        "status":                 "success",
        "restaurant_name":        random.choice(RESTAURANT_NAMES[platform]),
        "restaurant_available":   True,
        "rating":                 rating,
        "eta_min":                eta,
        "delivery_fee":           fee,
        "promo_general_pct":      promo_pct,
        "products":               products,
        "subtotal":               subtotal,
        "service_fee_estimated":  service_fee,
        "total_estimated":        total,
        "screenshot_path":        f"screenshots/mock/{platform}_mcdo.png",
        "error_detail":           "",
    }


def generate():
    records = []
    for addr in ADDRESSES:
        row = {
            "scraped_at":          datetime.now().isoformat(),
            "address_id":          addr["id"],
            "city":                addr["city"],
            "zone":                addr["zone"],
            "zone_type":           addr["zone_type"],
            "address":             f"{addr['zone']}, {addr['city']}",
            "restaurant_compared": "McDonald's",
        }
        for platform in PLATFORMS:
            row[platform] = gen_platform(platform, addr["zone_type"])
        records.append(row)

    # JSON
    with open("data/competitive_data_mock.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # CSV flat
    csv_rows = []
    for r in records:
        for platform in PLATFORMS:
            p = r[platform]
            prods = {pr["name"]: pr for pr in p["products"]}
            combo = prods.get("Combo Big Mac mediano", {})
            hdq   = prods.get("Hamburguesa doble con queso", {})
            coke  = prods.get("Coca-Cola mediana", {})
            csv_rows.append({
                "scraped_at":                   r["scraped_at"],
                "address_id":                   r["address_id"],
                "city":                         r["city"],
                "zone":                         r["zone"],
                "zone_type":                    r["zone_type"],
                "restaurant_compared":          r["restaurant_compared"],
                "platform":                     platform,
                "status":                       p["status"],
                "restaurant_name":              p["restaurant_name"],
                "restaurant_available":         p["restaurant_available"],
                "rating":                       p["rating"],
                "eta_min":                      p["eta_min"],
                "delivery_fee_mxn":             p["delivery_fee"],
                "promo_general_pct":            p["promo_general_pct"],
                "combo_bigmac_price_original":  combo.get("price_original"),
                "combo_bigmac_price_discount":  combo.get("price_discounted"),
                "combo_bigmac_discount_pct":    combo.get("discount_pct"),
                "hdq_price_original":           hdq.get("price_original"),
                "hdq_price_discounted":         hdq.get("price_discounted"),
                "hdq_discount_pct":             hdq.get("discount_pct"),
                "coke_price_original":          coke.get("price_original"),
                "coke_price_discounted":        coke.get("price_discounted"),
                "coke_discount_pct":            coke.get("discount_pct"),
                "subtotal_mxn":                 p["subtotal"],
                "service_fee_estimated_mxn":    p["service_fee_estimated"],
                "total_estimated_mxn":          p["total_estimated"],
                "error_detail":                 "",
            })

    keys = list(csv_rows[0].keys())
    with open("data/competitive_data_mock.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"✅ {len(records)} direcciones × 3 plataformas = {len(records)*3} registros")
    print(f"   → data/competitive_data_mock.json")
    print(f"   → data/competitive_data_mock.csv")

    # Quick stats
    import pandas as pd
    df = pd.DataFrame(csv_rows)
    print("\n📦 Delivery fee promedio (MXN):")
    print(df.groupby(["platform","zone_type"])["delivery_fee_mxn"].mean().round(1).unstack().to_string())
    print("\n⏱  ETA promedio (min):")
    print(df.groupby("platform")["eta_min"].mean().round(1).to_string())
    print("\n🎯 % promo general promedio:")
    print(df.groupby("platform")["promo_general_pct"].mean().round(1).to_string())
    print("\n💰 Total estimado promedio (MXN):")
    print(df.groupby(["platform","zone_type"])["total_estimated_mxn"].mean().round(1).unstack().to_string())
    return records


if __name__ == "__main__":
    generate()
