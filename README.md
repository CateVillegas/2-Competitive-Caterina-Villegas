# Competitive Intelligence System — Rappi México
**Caso Técnico: AI Engineer · Rappi**

Sistema automatizado que recolecta precios, fees, ETAs y promociones de **Rappi, Uber Eats y DiDi Food** en 25 zonas representativas de México, comparando el mismo restaurante (McDonald's) en las 3 plataformas.

---

## ⚡ Quick Start (1 comando)

```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

Genera: datos mock + 7 charts + PDF ejecutivo en `output/`.

---

## 🗂 Estructura

```
ci_rappi/
├── main.py                          ← Punto de entrada unificado
├── scraper/
│   ├── competitive_scraper.py       ← Scraper real (Playwright)
│   └── generate_mock_data.py        ← Plan B — datos calibrados
├── analysis/
│   ├── generate_analysis.py         ← 7 charts (matplotlib)
│   └── generate_report_pdf.py       ← PDF ejecutivo (reportlab)
├── data/                            ← JSON + CSV generados
├── output/                          ← Charts PNG + PDF
├── screenshots/                     ← Evidencia visual por zona
├── logs/                            ← scraper.log
└── requirements.txt
```

---

## 🎯 Scope del análisis

| Dimensión | Decisión | Justificación |
|---|---|---|
| Plataformas | Rappi + Uber Eats + DiDi Food | Los 3 jugadores con mayor share en MX |
| Ciudades | CDMX + Guadalajara + Monterrey | ~35% del GMV de Rappi MX |
| Zonas | 25 (wealthy + non-wealthy) | Captura variabilidad geográfica |
| Restaurante | McDonald's | Presente en las 3 apps → comparabilidad directa |
| Productos | Combo Big Mac mediano, Hamburguesa doble con queso, Coca-Cola mediana | Alta comparabilidad, representativos de fast food |

---

## 📊 Datos recolectados

| Campo | Descripción |
|---|---|
| `delivery_fee_mxn` | Costo de envío |
| `promo_general_pct` | % descuento general visible del restaurante (el "hook") |
| `combo_bigmac_price_original/discount` | Precios Combo Big Mac con/sin descuento |
| `hdq_price_original/discount` | Precios Hamburguesa doble con queso |
| `coke_price_original/discount` | Precios Coca-Cola mediana |
| `subtotal_mxn` | Suma de los 3 productos (precio final del carrito) |
| `service_fee_estimated_mxn` | Service fee estimado (rates: Rappi 10%, UberEats 15%, DiDi 8%) |
| `total_estimated_mxn` | Costo total al usuario (subtotal + delivery + service fee) |
| `eta_min` | Tiempo de entrega estimado (minutos) |
| `rating` | Calificación del restaurante en la plataforma |

---

## 🚀 Opciones de ejecución

```bash
# Demo completa (datos mock — sin riesgo de bloqueos)
python main.py

# Scraper real — CDMX, 3 direcciones, browser visible
python main.py --real --city cdmx --max-addresses 3 --visible

# Scraper real — todas las ciudades (25 direcciones, ~45-60 min)
python main.py --real

# Solo regenerar análisis (sobre datos existentes)
python main.py --analysis-only

# Módulos individuales
python scraper/generate_mock_data.py   # Solo datos mock
python analysis/generate_analysis.py  # Solo charts
python analysis/generate_report_pdf.py # Solo PDF
```

---

## 🔧 Estrategia técnica del scraper

### Rappi
- Navega a la página de ciudad directo: `/ciudad-de-mexico/restaurantes/delivery/706-mcdonald-s`
- Evita autocomplete (poco confiable) → URL directa por ciudad
- Screenshots del store como evidencia

### Uber Eats
- Input: `id="location-typeahead-home-input"` (confirmado en HTML real)
- **Clave**: extrae URL del resultado de búsqueda con `get_attribute("href")` y navega con `goto()` — el click falla por z-index del dropdown
- ETA extraíble desde `aria-label="Hora estimada de salida: X min"` en resultados

### DiDi Food
- URL real: `https://web.didiglobal.com/mx/food/` (didi.com.mx = dominio en venta)
- **Clave**: emula iPhone — DiDi no requiere login en móvil (documentado manualmente)
- Fallback automático a PedidosYa si DiDi no resuelve DNS desde fuera de MX

---

## 📌 Nota sobre los datos del informe

> **Los datos del PDF entregado son datos mock calibrados con market research público.**

Esto es una decisión de diseño deliberada:
- Uber Eats tiene Cloudflare activo → bloqueos consistentes sin proxy residencial
- DiDi Food requiere VPN con exit node México para resolver DNS fuera de MX

Los valores mock reflejan las dinámicas reales del mercado (precios publicados, ETAs documentados, relaciones competitivas conocidas). El scraper real está implementado y funcional para uso en red MX.

**Para datos reales en producción:**
- Uber Eats: ScraperAPI con proxy MX (~$50/mes)
- DiDi Food: VPN con exit node México

---

## 🏗 Dependencias

```
playwright>=1.40     # Scraping
pandas>=2.0          # Análisis
numpy>=1.24
matplotlib>=3.7      # Charts
reportlab>=4.0       # PDF
openpyxl>=3.1
```

---

## ⚖️ Consideraciones éticas

- Rate limiting: 2-8s aleatorios entre requests
- User-agents reales (sin fingerprints de automatización)
- Solo datos públicos visibles sin autenticación
- Para producción: validar con Legal antes de automatizar

---

## ⚠️ Limitaciones

1. **Snapshot temporal** — precios y ETAs varían por hora/día
2. **Service fee estimado** — no visible antes del checkout en todas las apps
3. **DiDi DNS** — solo resuelve desde IPs mexicanas (geofencing)
4. **Uber Eats Cloudflare** — requiere proxy residencial para uso intensivo
