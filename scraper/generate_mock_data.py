"""
Plan B -- Mock data generator
==============================
Genera datos simulados que replican la salida del scraper real.
Calibrado con precios REALES observados via scraping (marzo 2026).

Fuente de calibracion:
  - Rappi + Uber Eats scrapeados en Polanco (Masaryk 111) el 22/03/2026
  - Combo Big Mac = Home Office con Big Mac: $174 orig, $99 disc (-43%)
  - HDQ = Hamburguesa doble con queso: $69
  - Coca-Cola mediana: $55
  - Rappi: delivery $0 (gratis nuevos usuarios), ETA ~20min, rating 3.9
  - Uber Eats: delivery $0 (gratis nuevos usuarios), ETA ~20min, rating 4.5
  - DiDi Food: estimado de market research publico

Uso: python scraper/generate_mock_data.py
"""

import csv, json, os, random
from datetime import datetime
from pathlib import Path
import numpy as np

random.seed(42)
np.random.seed(42)

os.chdir(Path(__file__).parent.parent)
Path("data").mkdir(exist_ok=True)

ADDRESSES = [
    # CDMX — 9 zonas
    {"id": "MX_CDMX_01", "city": "Ciudad de Mexico", "zone": "Polanco",        "zone_type": "Wealthy",     "address": "Presidente Masaryk 111, Polanco, Miguel Hidalgo"},
    {"id": "MX_CDMX_02", "city": "Ciudad de Mexico", "zone": "Condesa",        "zone_type": "Wealthy",     "address": "Av. Tamaulipas 150, Condesa, Cuauhtemoc"},
    {"id": "MX_CDMX_03", "city": "Ciudad de Mexico", "zone": "Roma Norte",     "zone_type": "Wealthy",     "address": "Av. Alvaro Obregon 200, Roma Norte, Cuauhtemoc"},
    {"id": "MX_CDMX_04", "city": "Ciudad de Mexico", "zone": "Santa Fe",       "zone_type": "Wealthy",     "address": "Av. Santa Fe 440, Santa Fe, Alvaro Obregon"},
    {"id": "MX_CDMX_05", "city": "Ciudad de Mexico", "zone": "Del Valle",      "zone_type": "Wealthy",     "address": "Av. Insurgentes Sur 1602, Del Valle, Benito Juarez"},
    {"id": "MX_CDMX_06", "city": "Ciudad de Mexico", "zone": "Iztapalapa",     "zone_type": "Non Wealthy", "address": "Ermita Iztapalapa 3200, Iztapalapa"},
    {"id": "MX_CDMX_07", "city": "Ciudad de Mexico", "zone": "Ecatepec",       "zone_type": "Non Wealthy", "address": "Via Morelos 155, Ecatepec de Morelos"},
    {"id": "MX_CDMX_08", "city": "Ciudad de Mexico", "zone": "Tepito",         "zone_type": "Non Wealthy", "address": "Eje 1 Norte 100, Centro, Cuauhtemoc"},
    {"id": "MX_CDMX_09", "city": "Ciudad de Mexico", "zone": "Tlalpan",        "zone_type": "Non Wealthy", "address": "Calzada de Tlalpan 4800, Tlalpan"},
    # Guadalajara — 7 zonas
    {"id": "MX_GDL_01",  "city": "Guadalajara",      "zone": "Providencia",    "zone_type": "Wealthy",     "address": "Av. Providencia 2500, Providencia, Guadalajara"},
    {"id": "MX_GDL_02",  "city": "Guadalajara",      "zone": "Chapalita",      "zone_type": "Wealthy",     "address": "Av. Guadalupe 1300, Chapalita, Guadalajara"},
    {"id": "MX_GDL_03",  "city": "Guadalajara",      "zone": "Zapopan Centro", "zone_type": "Wealthy",     "address": "Av. Vallarta 6503, Zapopan"},
    {"id": "MX_GDL_04",  "city": "Guadalajara",      "zone": "Andares",        "zone_type": "Wealthy",     "address": "Blvd. Puerta de Hierro 4965, Zapopan"},
    {"id": "MX_GDL_05",  "city": "Guadalajara",      "zone": "Oblatos",        "zone_type": "Non Wealthy", "address": "Calzada Independencia Norte 3200, Oblatos"},
    {"id": "MX_GDL_06",  "city": "Guadalajara",      "zone": "Las Juntas",     "zone_type": "Non Wealthy", "address": "Av. Aviacion 1200, Las Juntas, Tlaquepaque"},
    {"id": "MX_GDL_07",  "city": "Guadalajara",      "zone": "Tonala",         "zone_type": "Non Wealthy", "address": "Av. Tonaltecas 150, Tonala"},
    # Monterrey — 9 zonas
    {"id": "MX_MTY_01",  "city": "Monterrey",        "zone": "San Pedro",      "zone_type": "Wealthy",     "address": "Calzada del Valle 400, San Pedro Garza Garcia"},
    {"id": "MX_MTY_02",  "city": "Monterrey",        "zone": "Valle",          "zone_type": "Wealthy",     "address": "Av. Lazaro Cardenas 2424, Valle, Monterrey"},
    {"id": "MX_MTY_03",  "city": "Monterrey",        "zone": "Cumbres",        "zone_type": "Wealthy",     "address": "Av. Paseo de los Leones 2600, Cumbres, Monterrey"},
    {"id": "MX_MTY_04",  "city": "Monterrey",        "zone": "Tecnologico",    "zone_type": "Wealthy",     "address": "Av. Eugenio Garza Sada 2501, Tecnologico"},
    {"id": "MX_MTY_05",  "city": "Monterrey",        "zone": "Centrito Valle", "zone_type": "Wealthy",     "address": "Av. Diego Rivera 500, Valle Oriente, San Pedro"},
    {"id": "MX_MTY_06",  "city": "Monterrey",        "zone": "Independencia",  "zone_type": "Non Wealthy", "address": "Av. Aztlan 100, Col. Independencia, Monterrey"},
    {"id": "MX_MTY_07",  "city": "Monterrey",        "zone": "Apodaca",        "zone_type": "Non Wealthy", "address": "Blvd. Zenon Fernandez 800, Apodaca"},
    {"id": "MX_MTY_08",  "city": "Monterrey",        "zone": "Escobedo",       "zone_type": "Non Wealthy", "address": "Av. Raul Salinas 1500, Escobedo"},
    {"id": "MX_MTY_09",  "city": "Monterrey",        "zone": "Guadalupe",      "zone_type": "Non Wealthy", "address": "Av. Pablo Livas 3200, Guadalupe"},
]

# -- Modelos calibrados con datos REALES observados (marzo 2026) --
# Precios base: identicos entre plataformas (son del restaurante, no de la app)
# Las diferencias estan en: delivery fee, ETA, service fee, promos
COMBO_BASE = 174    # Home Office con Big Mac (observado en Rappi y UberEats)
HDQ_BASE   = 69     # Hamburguesa doble con queso (observado)
COKE_BASE  = 55     # Coca-Cola mediana (observado)

MODELS = {
    "rappi": {
        # Delivery fee: gratis en zonas cercanas, sube en perifericas
        "fee_wealthy":     {"mean": 22, "std": 10},
        "fee_nonwealthy":  {"mean": 45, "std": 12},
        "fee_free_prob":   0.30,
        # ETA: observado 19-29 min en Polanco
        "eta_wealthy":     {"mean": 22, "std": 5},
        "eta_nonwealthy":  {"mean": 35, "std": 8},
        # Rating: observado 3.9 en Polanco
        "rating":          {"mean": 3.9, "std": 0.25},
        # Review count: Rappi tiene menos resenas visibles que Uber
        "review_count":    {"mean": 800, "std": 400},
        # Precios: variacion minima entre zonas
        "combo_var": 3, "hdq_var": 2, "coke_var": 1,
        # Descuentos: observado -43% en Combo (Home Office)
        "combo_disc_prob": 0.55, "combo_disc_pct": {"mean": 35, "std": 10},
        "hdq_disc_prob":   0.20, "hdq_disc_pct":   {"mean": 15, "std": 5},
        "coke_disc_prob":  0.10, "coke_disc_pct":   {"mean": 10, "std": 3},
        # Promo general: observado "Hasta 51%" en Polanco
        "promo_general_prob": 0.75,
        "promo_general_pct":  {"mean": 42, "std": 12},
        "service_fee_rate": 0.10,
    },
    "ubereats": {
        "fee_wealthy":     {"mean": 15, "std": 7},
        "fee_nonwealthy":  {"mean": 25, "std": 9},
        "fee_free_prob":   0.35,
        # ETA: observado 17-23 min en Polanco (mas rapido)
        "eta_wealthy":     {"mean": 19, "std": 4},
        "eta_nonwealthy":  {"mean": 28, "std": 6},
        # Rating: observado 4.5 en Polanco
        "rating":          {"mean": 4.5, "std": 0.15},
        # Review count: Uber tiene muchas mas resenas (observado 15000+ en Polanco)
        "review_count":    {"mean": 12000, "std": 5000},
        "combo_var": 3, "hdq_var": 2, "coke_var": 1,
        "combo_disc_prob": 0.65, "combo_disc_pct": {"mean": 38, "std": 10},
        "hdq_disc_prob":   0.35, "hdq_disc_pct":   {"mean": 18, "std": 6},
        "coke_disc_prob":  0.15, "coke_disc_pct":   {"mean": 12, "std": 4},
        "promo_general_prob": 0.80,
        "promo_general_pct":  {"mean": 40, "std": 10},
        "service_fee_rate": 0.15,
    },
    "didifood": {
        "fee_wealthy":     {"mean": 18, "std": 8},
        "fee_nonwealthy":  {"mean": 32, "std": 10},
        "fee_free_prob":   0.25,
        # ETAs: DiDi mas lento (menor densidad de repartidores)
        "eta_wealthy":     {"mean": 28, "std": 6},
        "eta_nonwealthy":  {"mean": 40, "std": 9},
        "rating":          {"mean": 4.1, "std": 0.25},
        # Review count: DiDi mucho menor (menos uso)
        "review_count":    {"mean": 300, "std": 200},
        "combo_var": 4, "hdq_var": 3, "coke_var": 2,
        # DiDi mas agresivo en promos para ganar share
        "combo_disc_prob": 0.70, "combo_disc_pct": {"mean": 40, "std": 12},
        "hdq_disc_prob":   0.50, "hdq_disc_pct":   {"mean": 25, "std": 8},
        "coke_disc_prob":  0.30, "coke_disc_pct":   {"mean": 18, "std": 5},
        "promo_general_prob": 0.85,
        "promo_general_pct":  {"mean": 48, "std": 10},
        "service_fee_rate": 0.08,
    },
}

PLATFORMS = ["rappi", "ubereats", "didifood"]
RESTAURANT_NAMES = {
    "rappi":    ["Mc Donald's", "McDonald's", "McDonald's Delivery"],
    "ubereats": ["McDonald's (Plaza Galerias)", "McDonald's (Insurgentes)", "McDonald's (Sears)", "McDonald's (Santa Fe)"],
    "didifood": ["McDonald's", "McDonald's Delivery", "McDonald's Express"],
}


def gen_product(m, name, base_price, var_key, disc_prob_key, disc_pct_key):
    var = m[var_key]
    price_orig = round(max(base_price - 5, base_price + np.random.normal(0, var)), 2)
    has_disc = random.random() < m[disc_prob_key]
    price_disc = None
    disc_pct = None
    if has_disc:
        disc_pct = round(max(5, min(60, np.random.normal(m[disc_pct_key]["mean"], m[disc_pct_key]["std"]))), 1)
        price_disc = round(price_orig * (1 - disc_pct / 100), 2)
    return {
        "name": name,
        "price_original":   price_orig,
        "price_discounted": price_disc,
        "discount_pct":     disc_pct,
    }


def gen_platform(platform, zone_type):
    m = MODELS[platform]
    is_wealthy = zone_type == "Wealthy"
    sfx = "wealthy" if is_wealthy else "nonwealthy"

    # Delivery fee con probabilidad de gratis
    if random.random() < m["fee_free_prob"]:
        fee = 0.0
    else:
        fee = round(max(0, np.random.normal(m[f"fee_{sfx}"]["mean"], m[f"fee_{sfx}"]["std"])), 2)

    eta = max(12, int(np.random.normal(m[f"eta_{sfx}"]["mean"], m[f"eta_{sfx}"]["std"])))
    rating = round(max(3.0, min(5.0, np.random.normal(m["rating"]["mean"], m["rating"]["std"]))), 1)

    promo_pct = None
    if random.random() < m["promo_general_prob"]:
        promo_pct = round(max(10, min(65, np.random.normal(m["promo_general_pct"]["mean"], m["promo_general_pct"]["std"]))), 0)

    products = [
        gen_product(m, "Combo Big Mac mediano",        COMBO_BASE, "combo_var", "combo_disc_prob", "combo_disc_pct"),
        gen_product(m, "Hamburguesa doble con queso",  HDQ_BASE,   "hdq_var",   "hdq_disc_prob",   "hdq_disc_pct"),
        gen_product(m, "Coca-Cola mediana",            COKE_BASE,  "coke_var",  "coke_disc_prob",  "coke_disc_pct"),
    ]

    subtotal = sum(
        (p["price_discounted"] if p["price_discounted"] else p["price_original"])
        for p in products
    )
    subtotal = round(subtotal, 2)
    service_fee = round(subtotal * m["service_fee_rate"], 2)
    total = round(subtotal + fee + service_fee, 2)

    # Review count — clamp to positive
    rc = m["review_count"]
    review_count = max(10, int(np.random.normal(rc["mean"], rc["std"])))

    return {
        "platform":               platform,
        "status":                 "success",
        "restaurant_name":        random.choice(RESTAURANT_NAMES[platform]),
        "restaurant_available":   True,
        "rating":                 rating,
        "review_count":           review_count,
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
            "address":             addr["address"],
            "restaurant_compared": "McDonald's",
        }
        for platform in PLATFORMS:
            row[platform] = gen_platform(platform, addr["zone_type"])
        records.append(row)

    with open("data/competitive_data_mock.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

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
                "address":                      r["address"],
                "restaurant_compared":          r["restaurant_compared"],
                "platform":                     platform,
                "status":                       p["status"],
                "restaurant_name":              p["restaurant_name"],
                "restaurant_available":         p["restaurant_available"],
                "rating":                       p["rating"],
                "eta_min":                      p["eta_min"],
                "review_count":                 p["review_count"],
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

    print(f"  {len(records)} direcciones x 3 plataformas = {len(records)*3} registros")
    print(f"  -> data/competitive_data_mock.json")
    print(f"  -> data/competitive_data_mock.csv")


if __name__ == "__main__":
    generate()
