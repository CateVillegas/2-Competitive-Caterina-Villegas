# Competitive Intelligence System — Rappi Mexico

**Caso Tecnico: AI Engineer · Rappi**

Sistema automatizado que recolecta precios, fees, ETAs y promociones de **Rappi, Uber Eats y DiDi Food** en 25 direcciones representativas de Mexico (CDMX, Guadalajara, Monterrey), comparando el mismo restaurante (McDonald's) en las 3 plataformas. Incluye analisis visual con 14 graficos, PDF ejecutivo con insights accionables y dashboard interactivo.

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
4. `dashboard/ci_dashboard.html` permite explorar el dataset cargando manualmente el CSV oficial desde el navegador y genera 15+ charts interactivos con interpretaciones automáticas.

> Nota: Todo el pipeline se ejecuta desde la raíz del repo y los archivos producto quedan centralizados en `output/`.

### Ver el dashboard interactivo

```bash
# Desde la raiz del repo, abrir el HTML directamente en el navegador:
# O servir con un servidor local:
python -m http.server 9000
# Luego abrir: http://localhost:9000/dashboard/ci_dashboard.html
```

En la pantalla inicial, cargar el CSV `data/competitive_data_with_didi.csv`. El dashboard genera automaticamente todos los graficos y metricas.

### Estado del scraping y decisiones tomadas

- ✅ **Rappi / Uber Eats**: scraping 100 % automatizado desde desktop usando Playwright, con manejo de overlays, scrolling custom y extracción basada en texto para evitar ofuscación CSS.
- ⚠️ **DiDi Food**: la versión desktop no muestra precios sin login y la versión mobile exige OTP en cada sesión. Logré automatizar el flujo mobile hasta el buscador, pero debido al OTP y a cambios UI por dirección, opté por capturar manualmente las 25 direcciones para no frenar el análisis. Los datos manuales están integrados en `data/competitive_data_with_didi.csv` y marcados en los campos `platform=didifood`.
- 📸 **Evidencia**: cada corrida guarda screenshots por dirección/plataforma y logs en `screenshots/` y `logs/`.
- 🔁 **Próximos pasos DiDi**: con más tiempo, planeo persistir la sesión mobile, automatizar el input del OTP mediante un servicio externo y robustecer los selectores adaptativos por ciudad.

---

## Estructura del repositorio

```
ci_rappi/
├── main.py                          # Punto de entrada unificado del pipeline
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

### Supuestos financieros y calculo del total estimado

- **Service fee**: sin login las apps no muestran el cargo final. `PlatformResult.compute_financials()` estima el service fee multiplicando el subtotal por una tasa fija por plataforma (`Rappi 10 %`, `Uber Eats 15 %`, `DiDi 8 %`). Para DiDi, cuando existe el valor real capturado manualmente, se usa ese número.
- **Delivery fee**: el primer envío suele aparecer gratis, por lo que homogenizamos el cálculo usando `delivery_fee_mxn` cuando existe o un valor estándar de `15 MXN` para estimar el costo final.
- **Total estimado**: `total_estimated_mxn = subtotal_mxn + (delivery_fee_mxn or 0) + service_fee_mxn`, redondeado a 2 decimales. Esto mantiene comparabilidad aun sin estar logueados.

---

## Entregables

### 2.1 Sistema de Scraping Competitivo (70%)

| Requisito | Estado | Detalle |
|---|---|---|
| Rappi scraper | Funcional | Automatizado con Playwright |
| Uber Eats scraper | Funcional | Automatizado con Playwright |
| DiDi Food scraper | Parcial | Requiere login manual (OTP por SMS). Datos recolectados manualmente |
| 3 productos comparables | Completo | Combo Big Mac Mediano, Hamburguesa Doble con Queso, Coca-Cola Mediana |
| Delivery fee | Capturado | Por plataforma y zona |
| Service fee | Estimado | Rappi 10%, Uber Eats 15%, DiDi 8% (no visible sin login) |
| ETA | Capturado | Tiempo estimado de entrega en minutos |
| Descuentos activos | Capturado | % promo general + descuento por producto |
| Precio final total | Calculado | Subtotal + delivery + service fee |
| Cobertura geografica | 25 direcciones | 9 CDMX + 7 GDL + 9 MTY (Wealthy + Non Wealthy) |
| Automatizacion | Un comando | `python main.py --real` |
| Output | CSV + JSON + screenshots | Evidencia automatica en screenshots/ |

### 2.2 Informe de Insights Competitivos (30%)

| Requisito | Estado | Detalle |
|---|---|---|
| Analisis comparativo | 5 dimensiones | Precios, operacional, fees, promos, geografia |
| Top 5 Insights accionables | Generados automaticamente | Finding + Impacto + Recomendacion |
| Visualizaciones | 14 graficos | Barras, heatmaps, scatter, stacked, lineas |
| PDF ejecutivo | Completo | Con glosario, tablas, insights, 14 graficos con interpretaciones |
| Dashboard interactivo | Completo | HTML + Chart.js con filtros, glosario, interpretaciones automaticas |

---

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
- Delivery fee: soporta formato "Costo de envio a MXN0"
- Misma logica de extraccion de texto que Rappi

### DiDi Food
- Emulacion mobile iPhone (390x844) — DiDi requiere user-agent mobile
- Login obligatorio con verificacion SMS (codigo OTP manual)
- Entry URL con direccion pre-cargada via parametro `pl=` (Base64)
- Busca McDonald's en la barra de busqueda
- Captura promo hook ("Hasta X% dto.") desde los resultados de busqueda

---

## Dashboard interactivo

El dashboard es un archivo HTML autocontenido (`dashboard/ci_dashboard.html`) que usa Chart.js para visualizacion. No requiere servidor backend.

**Para usarlo:**
1. Abrir el archivo HTML directamente en el navegador (o servir con `python -m http.server 9000`)
2. Cargar el CSV `data/competitive_data_with_didi.csv`
3. El dashboard genera automaticamente:
   - KPIs por plataforma (ETA, rating, precios de 3 productos, delivery fee, total)
   - 15+ graficos interactivos con filtros por ciudad, zona y plataforma
   - Interpretaciones automaticas debajo de cada grafico
   - Glosario de terminos y abreviaciones (ETA, SLA, BM, HDQ, CC, etc.)
   - Heatmaps de ETA y precios
   - Comparacion Wealthy vs Non Wealthy
   - Tabla detallada con todos los datos crudos

---

## Analisis generado (PDF y dashboard)

Ambos productos (PDF y dashboard) incluyen las mismas dimensiones de analisis:

1. **Posicionamiento de precios** — Comparativa de los 3 productos por plataforma (precio base vs con promo)
2. **Ventaja operacional** — ETA por zona, rating por ciudad, cumplimiento de SLA 30 min
3. **Estructura de fees** — Delivery fee y service fee por zona, desglose del costo total (stacked)
4. **Estrategia promocional** — Promo hook por zona, distribucion (boxplot), descuentos reales en productos
5. **Variabilidad geografica** — Comparacion Wealthy vs Non Wealthy (total, ETA, delivery fee, promos)
6. **Heatmaps** — ETA y precio Big Mac por zona/plataforma
7. **Analisis cruzado** — Scatter ETA vs promo hook, disponibilidad por tipo de zona

Cada grafico incluye:
- Titulo descriptivo
- Explicacion de que muestra y que variables usa
- Interpretacion automatica con relevancia para los equipos de Strategy y Pricing

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

## Consideraciones eticas

- Rate limiting: 2-8 segundos aleatorios entre requests
- User-agents reales (sin fingerprints de automatizacion)
- Anti-webdriver detection (oculta `navigator.webdriver`)
- Solo datos publicos visibles sin autenticacion (excepto DiDi que requiere login)
- Para produccion: validar con Legal antes de automatizar scraping sistematico

---

## Limitaciones conocidas

1. **Snapshot temporal** — precios y ETAs varian por hora/dia; los datos representan un momento especifico
2. **Service fee estimado** — no es visible sin estar logueado en la app, se estima con tasas fijas (Rappi 10%, Uber Eats 15%, DiDi 8%)
3. **Delivery fee no representativo** — el primer envio suele ser gratis; se usa $15 MXN estandar para estimaciones mas realistas
4. **DiDi Food requiere sesion activa** — verificacion por SMS (OTP) cada vez que se ejecuta; no automatizable
5. **DiDi Food version desktop** — no muestra restaurantes ni precios sin login; el scraper usa emulacion mobile
6. **Uber Eats Cloudflare** — puede requerir proxy residencial para uso intensivo
7. **Descuentos Rappi** — aparecen inconsistentemente dependiendo de la sesion

---

## Branch adicional

La branch `feature/verticales-wip` contiene un intento de expansion del scraper a verticales adicionales (farmacia y supermercado). Para Rappi funciona; Uber Eats requiere iteracion adicional. Se dejo pendiente por restricciones de tiempo y priorizacion del entregable principal.

## Futuras mejoras

- Persistir sesiones mobile de DiDi Food y automatizar la resolución del OTP para habilitar scraping 100 % automatizado de esa plataforma.
- Capturar y almacenar el conteo de reviews junto al rating para ponderar engagement y detectar apps donde un restaurante tiene más interacción.
- Extender el pipeline a nuevas verticales (farmacia/super) retomando lo avanzado en `feature/verticales-wip`.
- Añadir análisis de texto de reviews para identificar patrones de servicio diferenciados por plataforma.
