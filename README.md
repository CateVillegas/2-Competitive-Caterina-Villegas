# Competitive Intelligence System — Rappi México
**Caso Técnico: AI Engineer · Rappi**

Sistema automatizado que recolecta precios, fees, ETAs y promociones de **Rappi, Uber Eats y DiDi Food** en zonas representativas de México, comparando el mismo restaurante (McDonald's) en las 3 plataformas. Incluye análisis visual, PDF ejecutivo y dashboard interactivo.

---

## Quick Start

```bash
pip install -r requirements.txt
playwright install chromium

# Recalcula KPIs/insights con el dataset oficial
python analysis/generate_analysis.py --source data/competitive_data_with_didi.csv

# Renderiza el PDF ejecutivo con esos datos
python analysis/generate_report_pdf.py
```

Genera: charts PNG, `output/kpis.json`, `output/top_insights.json` y `output/Competitive_Intelligence_Rappi_MX.pdf` basados **exclusivamente** en `data/competitive_data_with_didi.csv`.

### Credenciales privadas (DiDi Food)

1. Copia el archivo `.env.example` a `.env` (ya esta en `.gitignore`).
2. Completa `DIDI_EMAIL`/`DIDI_PASSWORD` **o** `DIDI_PHONE` + `DIDI_PHONE_COUNTRY` (prefijo por defecto `+54`). Opcional: `DIDI_BASE_URL` para forzar otro feed.
3. La primera vez deberas ingresar el codigo OTP (SMS) manualmente en el navegador. Luego de un login exitoso, el scraper guarda la sesion en `sessions/didi_state.json` y la reutiliza en corridas futuras. Borra ese archivo si queres forzar un login nuevo.
4. El scraper carga las variables de `.env` y la sesion persistida automaticamente antes de iniciar Playwright.

---

## Estructura

```
ci_rappi/
├── main.py                          # Punto de entrada unificado
├── dashboard.py                     # Dashboard histórico (Streamlit)
├── dashboard/
│   └── ci_dashboard.html            # Dashboard narrativo (HTML + Chart.js)
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
| DiDi Food scraper | Funcional (requiere login manual con OTP por SMS) |
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
| 3+ visualizaciones | 7 charts (precios, operacional, descuentos, promos, geografia, engagement, radar) |
| PDF ejecutivo | `output/Competitive_Intelligence_Rappi_MX.pdf` |
| Dashboard interactivo | `dashboard/ci_dashboard.html` (ver sección “Dashboard narrativo”) |

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

# Analisis replicable del entregable (CSV oficial)
python analysis/generate_analysis.py --source data/competitive_data_with_didi.csv

# PDF con los payloads anteriores
python analysis/generate_report_pdf.py

# Dashboard narrativo (HTML)
python -m http.server 9000  # luego abrir /dashboard/ci_dashboard.html

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
| `review_count` | Cantidad de resenas/calificaciones del restaurante |

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
- Emulacion mobile iPhone (390x844) — DiDi requiere user-agent mobile
- **Login obligatorio con verificacion SMS**: el scraper ingresa el telefono, acepta terminos y condiciones, y hace click en "Siguiente". Luego **espera hasta 2 minutos** a que el usuario ingrese manualmente el codigo OTP que llega por SMS. Este paso no se puede automatizar.
- Configurable via `.env`: `DIDI_PHONE`, `DIDI_PHONE_COUNTRY` (+54 por defecto)
- Entry URL con direccion pre-cargada via parametro `pl=` (Base64)
- Busca McDonald's en la barra de busqueda (icono de lupa en la parte superior del feed)
- Captura promo hook ("Hasta X% dto.") desde los resultados de busqueda antes de entrar al restaurante
- Dentro del restaurante, navega las pestanas de categorias (Mc para Todos, A la Carta, Bebidas) para encontrar todos los productos
- Extrae rating y review count del formato "4.2(10000+)"
- Debe ejecutarse con `--visible` para poder ingresar el codigo OTP

---

## Dashboard narrativo (HTML + Chart.js)

1. Inicia un servidor local desde la raiz del repo:
	```bash
	python -m http.server 9000
	```
2. Abre `http://localhost:9000/dashboard/ci_dashboard.html` en tu navegador.
3. En la pantalla inicial, haz clic en **“Seleccionar CSV”** y carga `data/competitive_data_with_didi.csv` (es el dataset oficial del entregable).
4. El dashboard detecta dinámicamente ciudades, zonas, plataformas y genera las 10 visualizaciones con interpretaciones escritas para cada métrica.

Tips:
- Si regeneras el CSV, vuelve a cargarlo (el dashboard no hace polling).
- El botón **Reload dataset** limpia filtros y te permite cargar otro archivo sin refrescar el navegador.
- El header muestra la ruta del archivo para validar que estás analizando `data/competitive_data_with_didi.csv`.

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
- Solo datos publicos visibles (DiDi requiere autenticacion pero los datos son publicos)
- Para produccion: validar con Legal antes de automatizar

---

## Limitaciones

1. **Snapshot temporal** — precios y ETAs varian por hora/dia
2. **Service fee estimado** — no siempre visible antes del checkout
3. **DiDi Food requiere sesion activa** — necesitas tener una cuenta de DiDi Food con numero de telefono verificado. Cada vez que se ejecuta el scraper, DiDi pide verificacion por SMS (codigo OTP) que debe ingresarse manualmente en el navegador. No hay forma de automatizar este paso. El scraper debe ejecutarse con `--visible` para DiDi.
4. **DiDi Food DNS** — solo resuelve desde IPs mexicanas (geofencing)
5. **Uber Eats Cloudflare** — requiere proxy residencial para uso intensivo
6. **Descuentos Rappi** — aparecen inconsistentemente en la pagina (depende de la sesion)
