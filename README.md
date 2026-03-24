# Competitive Intelligence System — Rappi Mexico

**Caso Tecnico: AI Engineer · Rappi**

Sistema automatizado que recolecta precios, fees, ETAs y promociones de **Rappi, Uber Eats y DiDi Food** en 25 direcciones representativas de Mexico (CDMX, Guadalajara, Monterrey), comparando el mismo restaurante (McDonald's) en las 3 plataformas. Incluye analisis visual con graficos, PDF ejecutivo con insights accionables y dashboard interactivo.

---

## Quick Start

```bash
# 1. Instalar dependencias (desde la raíz del repo)
pip install -r requirements.txt
playwright install chromium

# 2. Recalcular KPIs, insights y charts usando el dataset oficial incluido
python analysis/generate_analysis.py --source data/competitive_data_with_didi.csv

# 3. Generar el PDF ejecutivo a partir de esos payloads
python analysis/generate_report_pdf.py
```

Esto deja artefactos actualizados en `output/`:
- 14 charts PNG
- `kpis.json` con metricas por plataforma
- `top_insights.json` con los 5 insights accionables
- `Competitive_Intelligence_Rappi_MX.pdf` — informe ejecutivo completo

## Arquitectura y flujo del sistema

1. `scraper/competitive_scraper.py` (Playwright) recorre las 25 direcciones estratégicas y genera los CSV/JSON en `data/` junto con screenshots de evidencia.
2. `analysis/generate_analysis.py` consume cualquier CSV/JSON (por defecto usamos `data/competitive_data_with_didi.csv`), calcula KPIs, insights y renderiza 14 visualizaciones estaticas.
3. `analysis/generate_report_pdf.py` usa los payloads anteriores para redactar el informe ejecutivo (`Competitive_Intelligence_Rappi_MX.pdf`).
4. `dashboard/ci_dashboard.html` permite explorar el dataset cargando manualmente el CSV oficial desde el navegador y genera charts interactivos con interpretaciones automáticas.

> Nota: Todo el pipeline se ejecuta desde la raíz del repo y los archivos producto quedan centralizados en `output/`.

### Ver el dashboard interactivo

```bash
# Desde la raiz del repo, abrir el HTML directamente en el navegador:
# O servir con un servidor local:
python -m http.server 9000
# Luego abrir: http://localhost:9000/dashboard/ci_dashboard.html
```

En la pantalla inicial, cargar el CSV `data/competitive_data_with_didi.csv`. El dashboard genera automaticamente todos los graficos y metricas.
---

## Estructura del repositorio

```
ci_rappi/
├── main.py                          # Punto de entrada unificado del pipeline
├── Documentacion.pdf
├── requirements.txt                 # Dependencias Python
│
├── scraper/
│   ├── competitive_scraper.py       # Scraper real (Playwright) - Rappi, Uber Eats, DiDi Food
│   └── generate_mock_data.py        # Generador de datos sinteticos (Plan B)
│
├── analysis/
│   ├── generate_analysis.py         # Genera 14 charts (matplotlib) + KPIs JSON
│   ├── generate_report_pdf.py       # Genera PDF ejecutivo con insights (reportlab)
│   └── insights_utils.py            # Utilidades: carga de datos, metricas, insights automaticos
│
├── dashboard/
│   └── ci_dashboard.html            # Dashboard interactivo (HTML + Chart.js)
│                                    # Fondo blanco, glosario, 15+ graficos con interpretaciones
│
├── data/
│   ├── competitive_data_RAW.csv     # Datos crudos del scraping automatico (Rappi + Uber Eats)
│   ├── competitive_data_RAW.json    # Mismos datos en formato JSON
│   ├── competitive_data_with_didi.csv   # Dataset oficial: Rappi + Uber + DiDi (3 plataformas)
│   └── competitive_data_with_didi.json  # Mismos datos en formato JSON
│
├── output/                          # Generado por generate_analysis.py + generate_report_pdf.py
│   ├── Competitive_Intelligence_Rappi_MX.pdf  # Informe ejecutivo
│   ├── chart_*.png                  # 14 graficos
│   ├── kpis.json                    # KPIs por plataforma
│   └── top_insights.json            # Top 5 insights accionables
│
├── screenshots/                     # Capturas automaticas del scraper (gitignored)
├── logs/                            # Logs de ejecucion (gitignored)
├── sessions/                        # Estado de sesion DiDi (gitignored)
└── .env.example                     # Template de credenciales DiDi
```

---

## Datasets incluidos en el repositorio

### `data/competitive_data_RAW.csv` — Scraping automatico real
Contiene los datos obtenidos por el scraper automatizado para **Rappi y Uber Eats**. Este es el output directo de `competitive_scraper.py` sin modificaciones.

### `data/competitive_data_with_didi.csv` — Dataset oficial completo
Contiene las **3 plataformas** (Rappi, Uber Eats, DiDi Food) en las 25 direcciones. Los datos de DiDi Food fueron recolectados manualmente (ver seccion "Decisiones tecnicas"). **Este es el CSV que se debe usar para el dashboard y el analisis.**

### Columnas del CSV

| Campo | Descripcion |
|---|---|
| `scraped_at` | Timestamp del scraping |
| `address_id` | ID unico de la direccion (ej: MX_CDMX_01) |
| `city` | Ciudad (Ciudad de Mexico, Guadalajara, Monterrey) |
| `zone` | Nombre de la zona (ej: Polanco, Iztapalapa) |
| `zone_type` | Clasificacion socioeconomica: Wealthy o Non Wealthy |
| `platform` | Plataforma: rappi, ubereats, didifood |
| `status` | Resultado: success, partial, partial_no_store |
| `restaurant_available` | Si el restaurante aparecio disponible |
| `rating` | Calificacion del restaurante en la app |
| `eta_min` | Tiempo de entrega estimado (minutos) |
| `delivery_fee_mxn` | Costo de envio (MXN) |
| `promo_general_pct` | % descuento visible en el feed (promo hook) |
| `bm_price_orig` / `bm_price_disc` / `bm_disc_pct` | Combo Big Mac: precio original, con descuento, % descuento |
| `hdq_price_orig` / `hdq_price_disc` / `hdq_disc_pct` | Hamburguesa Doble con Queso: idem |
| `cc_price_orig` / `cc_price_disc` / `cc_disc_pct` | Coca-Cola Mediana: idem |
| `subtotal_mxn` | Suma de los 3 productos |
| `service_fee_mxn` | Service fee (estimado o real para DiDi) |
| `total_estimated_mxn` | Subtotal + delivery fee + service fee |
| `error` | Mensaje de error si hubo fallo |

## Ejecucion del scraper

```bash
# Demo con datos mock (sin riesgo de bloqueos)
python main.py

# Scraper real — CDMX, 3 direcciones, browser visible
python main.py --real --city cdmx --max-addresses 3 --visible

# Scraper real — todas las ciudades (25 direcciones)
python main.py --real

# Solo regenerar analisis sobre datos existentes
python main.py --analysis-only

# Modulos individuales
cd analysis
python generate_analysis.py --source ../data/competitive_data_with_didi.csv
python generate_report_pdf.py
```

### Credenciales DiDi Food

1. Copiar `.env.example` a `.env`
2. Completar `DIDI_PHONE` y `DIDI_PHONE_COUNTRY`
3. Ejecutar con `--visible` para ingresar el codigo OTP manualmente
4. La sesion se guarda en `sessions/didi_state.json`

---

## Dependencias

```
playwright>=1.40     # Scraping con browser automation
pandas>=2.0          # Manipulacion de datos
numpy>=1.24          # Calculo numerico
matplotlib>=3.7      # Charts estaticos (PDF)
plotly>=5.0          # Charts interactivos
streamlit>=1.20      # Dashboard (Streamlit)
reportlab>=4.0       # Generacion de PDF
openpyxl>=3.1        # Export Excel
```

---

## Branch adicional

La branch `feature/verticales-wip` contiene un intento de expansion del scraper a verticales adicionales (farmacia y supermercado). Para Rappi funciona; Uber Eats requiere iteracion adicional. Se dejo pendiente por restricciones de tiempo y priorizacion del entregable principal.
