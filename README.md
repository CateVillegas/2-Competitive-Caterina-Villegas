# Competitive Intelligence System — Rappi México
**Caso Técnico: AI Engineer · Rappi**

Sistema automatizado que recolecta precios, fees, ETAs y promociones de **Rappi, Uber Eats y DiDi Food** en zonas representativas de México, comparando el mismo restaurante (McDonald's) en las 3 plataformas. Incluye análisis visual, PDF ejecutivo y dashboard interactivo.

---

## Quick Start

```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

Genera: datos mock + 7 charts + PDF ejecutivo en `output/`.

---

## Estructura

```
ci_rappi/
├── main.py                          # Punto de entrada unificado
├── dashboard.py                     # Dashboard interactivo (Streamlit)
├── scraper/
│   ├── competitive_scraper.py       # Scraper real (Playwright)
│   └── generate_mock_data.py        # Plan B — datos mock calibrados
├── analysis/
│   ├── generate_analysis.py         # 7 charts (matplotlib) + KPIs
│   └── generate_report_pdf.py       # PDF ejecutivo (reportlab)
├── data/                            # JSON + CSV generados
│   ├── competitive_data_mock.*      # Mock data (incluido en repo)
│   └── competitive_data_YYYYMMDD.*  # Datos reales (gitignored)
├── output/                          # Charts PNG + PDF + KPIs
├── screenshots/                     # Evidencia visual (gitignored)
├── logs/                            # scraper.log (gitignored)
└── requirements.txt
```

---

## Entregables

### 2.1 Sistema de Scraping Competitivo

| Requisito | Estado |
|---|---|
| Rappi scraper | Funcional |
| Uber Eats scraper | Funcional |
| DiDi Food scraper | Estructurado (requiere mobile emulation + VPN MX) |
| Precio de 3 productos comparables | Combo Big Mac, HDQ, Coca-Cola mediana |
| Delivery fee | Capturado por plataforma |
| Service fee estimado | Rappi 10%, Uber Eats 15%, DiDi 8% |
| ETA | Capturado por plataforma |
| Descuentos activos | % promo general + descuento por producto |
| Precio final total | Subtotal + delivery + service fee |
| Cobertura geografica | 25 direcciones (CDMX, GDL, MTY) en mock; expandible |
| Automatizacion | `python main.py` (un comando) |
| Output | JSON + CSV + screenshots como evidencia |

### 2.2 Informe de Insights Competitivos

| Requisito | Estado |
|---|---|
| Analisis comparativo estructurado | 7 dimensiones analizadas |
| Top 5 Insights accionables | Generados dinamicamente desde datos |
| 3+ visualizaciones | 7 charts (delivery fee, ETA, precios, fees, promos, geo, radar) |
| PDF ejecutivo | `output/Competitive_Intelligence_Rappi_MX.pdf` |
| Dashboard interactivo | `streamlit run dashboard.py` |

---

## Opciones de ejecucion

```bash
# Demo completa (datos mock — sin riesgo de bloqueos)
python main.py

# Scraper real — CDMX, 3 direcciones, browser visible
python main.py --real --city cdmx --max-addresses 3 --visible

# Scraper real — todas las ciudades (25 direcciones)
python main.py --real

# Solo regenerar analisis (sobre datos existentes)
python main.py --analysis-only

# Analisis con datos mock (forzado)
python analysis/generate_analysis.py --mock

# Dashboard interactivo
streamlit run dashboard.py

# Modulos individuales
python scraper/generate_mock_data.py
python analysis/generate_analysis.py
python analysis/generate_report_pdf.py
```

---

## Datos recolectados

| Campo | Descripcion |
|---|---|
| `delivery_fee` | Costo de envio |
| `promo_general_pct` | % descuento general visible del restaurante (el "hook") |
| `combo_bigmac_price_original/discount` | Precios Combo Big Mac con/sin descuento |
| `hdq_price_original/discount` | Precios Hamburguesa doble con queso |
| `coke_price_original/discount` | Precios Coca-Cola mediana |
| `subtotal` | Suma de los 3 productos |
| `service_fee_estimated` | Service fee estimado |
| `total_estimated` | Costo total al usuario |
| `eta_min` | Tiempo de entrega estimado (minutos) |
| `rating` | Calificacion del restaurante |

---

## Estrategia tecnica del scraper

### Rappi
- Navega a home, ingresa direccion, busca "McDonalds"
- Extrae href del resultado y navega con `page.goto()` (evita overlay bloqueante)
- Detecta y scrollea contenedores internos (el menu de Rappi no usa `window.scrollBy`)
- Extraccion basada en texto (`document.body.innerText`) — inmune a ofuscacion CSS
- Ventana forward-only de 4 lineas para evitar contaminacion de precios adyacentes

### Uber Eats
- Navega a home, ingresa direccion, va a `/mx/search?q=McDonalds`
- Encuentra link del store y navega directo
- Extrae restaurant_name desde `<h1>` del store page
- Delivery fee: soporta formato "Costo de envio a MXN0"
- Misma logica de extraccion de texto que Rappi

### DiDi Food
- Requiere emulacion mobile (iPhone viewport 390x844)
- DiDi no requiere login en mobile (documentado)
- Prueba multiples URLs (`didifood.com/mx`, `food.didiglobal.com/mx`, etc.)
- Deteccion de domain parking / login wall

---

## Dashboard (Streamlit)

```bash
streamlit run dashboard.py
```

Funcionalidades:
- Selector de dataset (real vs mock)
- Filtros interactivos: plataformas, ciudades, tipo de zona
- 5 tabs: Precios, Delivery & ETA, Fees & Total, Promos, Geografia
- Radar chart interactivo (Plotly)
- Tabla de datos crudos + descarga CSV
- Se adapta automaticamente a las plataformas con datos

---

## Dependencias

```
playwright>=1.40     # Scraping
pandas>=2.0          # Analisis
numpy>=1.24          # Calculo
matplotlib>=3.7      # Charts estaticos
plotly>=5.0          # Charts interactivos (dashboard)
streamlit>=1.20      # Dashboard
reportlab>=4.0       # PDF
openpyxl>=3.1        # Excel export
```

---

## Consideraciones eticas

- Rate limiting: 2-8s aleatorios entre requests
- User-agents reales (sin fingerprints de automatizacion)
- Anti-webdriver detection (oculta `navigator.webdriver`)
- Solo datos publicos visibles sin autenticacion
- Para produccion: validar con Legal antes de automatizar

---

## Limitaciones

1. **Snapshot temporal** — precios y ETAs varian por hora/dia
2. **Service fee estimado** — no siempre visible antes del checkout
3. **DiDi Food DNS** — solo resuelve desde IPs mexicanas (geofencing)
4. **Uber Eats Cloudflare** — requiere proxy residencial para uso intensivo
5. **Descuentos Rappi** — aparecen inconsistentemente en la pagina (depende de la sesion)
