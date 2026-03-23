"""
competitive_scraper.py  v4 — Rappi Competitive Intelligence
==============================================================
FIXES v4:
  - Rappi: navigate to store via page.goto(href) instead of clicking
    (fixes overlay div blocking pointer events)
  - Rappi: improved search bar interaction — click container first,
    then type with keyboard, multiple fallback strategies
  - Uber Eats: direct search URL navigation (bypasses unreliable UI search)
  - Uber Eats: more scrolling to capture Coca-Cola in Bebidas section
  - DiDi Food: improved mobile emulation flow
  - Coca-Cola keywords expanded (coca, coca-cola, 21 oz variants)
  - Rating extraction improved (star icon patterns)
  - Longer scrolling (20 scrolls) to trigger all lazy content

ESTRATEGIA DE PRODUCTOS:
  En lugar de buscar por selectores CSS (que son clases ofuscadas
  y cambian constantemente en Rappi/Uber), extraemos TODO el texto
  de la página y parseamos con regex. Esto es mucho más robusto.

FLUJO POR PLATAFORMA:
  Rappi    → home → dirección → buscar → store URL goto → extraer texto
  UberEats → home → dirección → /search?q=McDonalds → store URL goto → extraer texto
  DiDi     → iPhone UA → dirección → buscar → store → extraer texto
"""

from __future__ import annotations
import asyncio, csv, json, logging, random, re, sys, io, os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus, urlparse, parse_qsl, urlencode, urlunparse
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


def _load_local_env(path: Path = Path(".env")):
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception as exc:
        logging.getLogger("ci").warning(f"No se pudo cargar .env: {exc}")


_load_local_env()

# ── Logging UTF-8 (fix Windows cp1252) ───────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("screenshots").mkdir(exist_ok=True)
Path("storage").mkdir(exist_ok=True)
Path("sessions").mkdir(exist_ok=True)

LEGACY_DIDI_STORAGE_PATH = Path("storage/didi_state.json")
_custom_storage = os.environ.get("DIDI_STORAGE_STATE")
if _custom_storage:
    DIDI_STORAGE_PATH = Path(_custom_storage)
    DIDI_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
else:
    DIDI_STORAGE_PATH = Path("sessions/didi_state.json")
    DIDI_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LEGACY_DIDI_STORAGE_PATH.exists() and not DIDI_STORAGE_PATH.exists():
        try:
            LEGACY_DIDI_STORAGE_PATH.rename(DIDI_STORAGE_PATH)
        except Exception:
            pass

_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/scraper.log", encoding="utf-8"),
              logging.StreamHandler(_utf8)],
)
log = logging.getLogger("ci")

# ── Addresses ─────────────────────────────────────────────────────────────────
ADDRESSES = [
    {"id":"MX_CDMX_01","city":"Ciudad de Mexico","zone":"Polanco",       "zone_type":"Wealthy",    "address":"Presidente Masaryk 111, Polanco, Miguel Hidalgo, Ciudad de Mexico"},
    {"id":"MX_CDMX_02","city":"Ciudad de Mexico","zone":"Condesa",       "zone_type":"Wealthy",    "address":"Tamaulipas 66, Hipodromo Condesa, Cuauhtemoc, Ciudad de Mexico"},
    {"id":"MX_CDMX_03","city":"Ciudad de Mexico","zone":"Roma Norte",    "zone_type":"Wealthy",    "address":"Orizaba 101, Roma Norte, Cuauhtemoc, Ciudad de Mexico"},
    {"id":"MX_CDMX_04","city":"Ciudad de Mexico","zone":"Santa Fe",      "zone_type":"Wealthy",    "address":"Av. Santa Fe 170, Santa Fe, Alvaro Obregon, Ciudad de Mexico"},
    {"id":"MX_CDMX_05","city":"Ciudad de Mexico","zone":"Del Valle",     "zone_type":"Wealthy",    "address":"Insurgentes Sur 649, Del Valle Norte, Benito Juarez, Ciudad de Mexico"},
    {"id":"MX_CDMX_06","city":"Ciudad de Mexico","zone":"Iztapalapa",    "zone_type":"Non Wealthy","address":"Av. Ermita Iztapalapa 4001, Iztapalapa, Ciudad de Mexico"},
    {"id":"MX_CDMX_07","city":"Ciudad de Mexico","zone":"Ecatepec",      "zone_type":"Non Wealthy","address":"Av. Central 205, Ciudad Azteca, Ecatepec, Estado de Mexico"},
    {"id":"MX_CDMX_08","city":"Ciudad de Mexico","zone":"Tepito",        "zone_type":"Non Wealthy","address":"Peralvillo 45, Morelos, Cuauhtemoc, Ciudad de Mexico"},
    {"id":"MX_CDMX_09","city":"Ciudad de Mexico","zone":"Tlalpan",       "zone_type":"Non Wealthy","address":"Insurgentes Sur 4111, La Joya, Tlalpan, Ciudad de Mexico"},
    {"id":"MX_GDL_01", "city":"Guadalajara",     "zone":"Providencia",   "zone_type":"Wealthy",    "address":"Av. Providencia 2400, Providencia, Guadalajara, Jalisco"},
    {"id":"MX_GDL_02", "city":"Guadalajara",     "zone":"Chapalita",     "zone_type":"Wealthy",    "address":"Av. Guadalupe 1023, Chapalita, Guadalajara, Jalisco"},
    {"id":"MX_GDL_03", "city":"Guadalajara",     "zone":"Zapopan",       "zone_type":"Wealthy",    "address":"Av. Hidalgo 151, Centro, Zapopan, Jalisco"},
    {"id":"MX_GDL_04", "city":"Guadalajara",     "zone":"Andares",       "zone_type":"Wealthy",    "address":"Blvd. Puerta de Hierro 4965, Puerta de Hierro, Zapopan, Jalisco"},
    {"id":"MX_GDL_05", "city":"Guadalajara",     "zone":"Oblatos",       "zone_type":"Non Wealthy","address":"Av. Oblatos 3456, Oblatos, Guadalajara, Jalisco"},
    {"id":"MX_GDL_06", "city":"Guadalajara",     "zone":"Las Juntas",    "zone_type":"Non Wealthy","address":"Av. Las Torres 2000, Las Juntas, San Pedro Tlaquepaque, Jalisco"},
    {"id":"MX_GDL_07", "city":"Guadalajara",     "zone":"Tonala",        "zone_type":"Non Wealthy","address":"Av. Tonala 456, Centro, Tonala, Jalisco"},
    {"id":"MX_MTY_01", "city":"Monterrey",       "zone":"San Pedro",     "zone_type":"Wealthy",    "address":"Av. Vasconcelos 500, San Pedro Garza Garcia, Nuevo Leon"},
    {"id":"MX_MTY_02", "city":"Monterrey",       "zone":"Valle",         "zone_type":"Wealthy",    "address":"Av. del Valle 100, Del Valle, San Pedro Garza Garcia, Nuevo Leon"},
    {"id":"MX_MTY_03", "city":"Monterrey",       "zone":"Cumbres",       "zone_type":"Wealthy",    "address":"Av. Via Cumbres 1000, Cumbres, Monterrey, Nuevo Leon"},
    {"id":"MX_MTY_04", "city":"Monterrey",       "zone":"Tecnologico",   "zone_type":"Wealthy",    "address":"Av. Eugenio Garza Sada 2501, Tecnologico, Monterrey, Nuevo Leon"},
    {"id":"MX_MTY_05", "city":"Monterrey",       "zone":"Centrito",      "zone_type":"Wealthy",    "address":"Alfonso Reyes 2020, Contry, Monterrey, Nuevo Leon"},
    {"id":"MX_MTY_06", "city":"Monterrey",       "zone":"Independencia", "zone_type":"Non Wealthy","address":"Av. Independencia 1500, Independencia, Monterrey, Nuevo Leon"},
    {"id":"MX_MTY_07", "city":"Monterrey",       "zone":"Apodaca",       "zone_type":"Non Wealthy","address":"Av. Apodaca 300, Centro, Apodaca, Nuevo Leon"},
    {"id":"MX_MTY_08", "city":"Monterrey",       "zone":"Escobedo",      "zone_type":"Non Wealthy","address":"Av. Aztlan 200, Buenavista, General Escobedo, Nuevo Leon"},
    {"id":"MX_MTY_09", "city":"Monterrey",       "zone":"Guadalupe",     "zone_type":"Non Wealthy","address":"Av. Benito Juarez 450, Centro, Guadalupe, Nuevo Leon"},
]

PLATFORMS = ["rappi","ubereats","didifood"]

SERVICE_FEE = {"rappi":0.10, "ubereats":0.15, "didifood":0.08}
# Some stores mask the shipping fee with MXN0; use a sane fallback so totals are realistic.
FALLBACK_DELIVERY_FEE = 15.0

DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
IPHONE_UA  = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"

# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class ProductData:
    name: str
    price_original: Optional[float]   = None
    price_discounted: Optional[float] = None
    discount_pct: Optional[float]     = None

@dataclass
class PlatformResult:
    platform: str
    status: str = "pending"
    restaurant_name: str = ""
    restaurant_available: bool = False
    rating: Optional[float] = None
    review_count: Optional[int] = None
    eta_min: Optional[int] = None
    delivery_fee: Optional[float] = None
    promo_general_pct: Optional[float] = None
    products: list = field(default_factory=list)
    subtotal: Optional[float] = None
    service_fee_estimated: Optional[float] = None
    total_estimated: Optional[float] = None
    screenshot_path: str = ""
    error_detail: str = ""

    def compute_financials(self, platform):
        prices = [
            (p.price_discounted if p.price_discounted is not None else p.price_original)
            for p in self.products
            if (p.price_discounted or p.price_original) is not None
        ]
        # Use cart subtotal if already set (e.g. from DiDi's cart view),
        # otherwise compute from individual product prices
        if not self.subtotal and prices:
            self.subtotal = round(sum(prices), 2)
        if self.subtotal:
            rate = SERVICE_FEE.get(platform, 0.10)
            self.service_fee_estimated = round(self.subtotal * rate, 2)
            delivery_fee = self.delivery_fee
            if delivery_fee is None or delivery_fee == 0:
                delivery_fee = FALLBACK_DELIVERY_FEE
                self.delivery_fee = delivery_fee
            self.total_estimated = round(self.subtotal + delivery_fee + self.service_fee_estimated, 2)

# ── Helpers ───────────────────────────────────────────────────────────────────

async def delay(lo=2.0, hi=4.5):
    await asyncio.sleep(random.uniform(lo, hi))

def px(text) -> Optional[float]:
    """Parse price from any string. Returns None if not found."""
    if not text: return None
    text = str(text).replace(",","").replace("\xa0"," ")
    if any(w in text.lower() for w in ["gratis","free","sin costo"]): return 0.0
    m = re.search(r"\b(\d+\.?\d*)\b", text)
    if not m: return None
    v = float(m.group(1))
    return v if 5 <= v <= 2000 else None

def peta(text) -> Optional[int]:
    if not text: return None
    nums = [int(n) for n in re.findall(r"\d+", str(text)) if 5 <= int(n) <= 120]
    if not nums: return None
    return nums[0] if len(nums)==1 else (nums[0]+nums[1])//2

def ppct(text) -> Optional[float]:
    if not text: return None
    m = re.search(r"(\d+)\s*%", str(text))
    return float(m.group(1)) if m else None

MC_EXCLUDE_KEYWORDS = [
    "postre",
    "postres",
    "desayuno",
    "breakfast",
    "mcflurry",
    "helado",
    "helados",
    "pollo",
    "pollos",
    "chicken",
]


def valid_mcdo(name):
    lname = (name or "").lower()
    return "mcdonald" in lname and all(x not in lname for x in MC_EXCLUDE_KEYWORDS)

async def shot(page, addr_id, platform, stage, sdir) -> str:
    try:
        p = sdir / f"{addr_id}_{platform}_{stage}_{datetime.now().strftime('%H%M%S')}.png"
        await page.screenshot(path=str(p), full_page=False)
        log.info(f"  screenshot: {p.name}")
        return str(p)
    except: return ""

async def try_text(page, sels) -> Optional[str]:
    for s in sels:
        try:
            el = page.locator(s).first
            if await el.count() > 0:
                t = (await el.inner_text()).strip()
                if t: return t
        except: continue
    return None


async def ensure_full_scroll(page: Page, pause=0.7, max_scrolls=20):
    """Scroll down the page progressively to trigger lazy loading.
    Used for Uber Eats / DiDi where window scrolling works."""
    try:
        for i in range(max_scrolls):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await asyncio.sleep(pause)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    except Exception:
        return


async def scroll_and_collect_text(page: Page, pause=0.6, max_scrolls=35) -> str:
    """Scroll both window AND internal scroll containers to trigger lazy loading,
    then grab the full page text ONCE.

    IMPORTANT: Do NOT deduplicate lines — the same price (e.g. "$55.00") can
    appear for multiple products. Dedup kills the second occurrence and breaks
    price extraction."""

    # ── Tag the largest internal scrollable container via JS ──
    has_container = await page.evaluate("""
        () => {
            let best = null;
            let bestArea = 0;
            document.querySelectorAll('div, main, section, article').forEach(el => {
                const s = getComputedStyle(el);
                const scrollable = (s.overflowY === 'auto' || s.overflowY === 'scroll');
                const hasOverflow = el.scrollHeight > el.clientHeight + 100;
                const bigEnough = el.clientHeight > 200;
                if (scrollable && hasOverflow && bigEnough) {
                    const area = el.scrollHeight;
                    if (area > bestArea) {
                        bestArea = area;
                        best = el;
                    }
                }
            });
            if (best) {
                best.setAttribute('data-ci-scroll', 'true');
                return true;
            }
            return false;
        }
    """)
    log.info(f"  scroll: internal container found = {has_container}")

    # ── Scroll to bottom progressively ──
    prev_scroll_y = -1
    prev_container_y = -1
    stale_count = 0

    for i in range(max_scrolls):
        positions = await page.evaluate("""
            () => {
                window.scrollBy(0, window.innerHeight * 0.8);
                const c = document.querySelector('[data-ci-scroll]');
                if (c) c.scrollBy(0, c.clientHeight * 0.7);
                return {
                    windowY: Math.round(window.scrollY),
                    containerY: c ? Math.round(c.scrollTop) : -1
                };
            }
        """)
        await asyncio.sleep(pause)

        wy = positions.get("windowY", 0)
        cy = positions.get("containerY", 0)
        if wy == prev_scroll_y and cy == prev_container_y:
            stale_count += 1
            if stale_count >= 3:
                break
        else:
            stale_count = 0
        prev_scroll_y = wy
        prev_container_y = cy

    # ── Grab full text ONCE (no dedup!) ──
    # All lazy content is now loaded and stays in the DOM.
    full_text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    log.info(f"  scroll: done after scrolling, {len(lines)} lines captured")
    return full_text

# ── CORE: Text-based product extraction ───────────────────────────────────────
TARGET_PRODUCTS = [
    {
        "name":        "Combo Big Mac mediano",
        # "home office" is the preferred keyword — it uniquely identifies the
        # combo mediano. "big mac" alone matches Tocino variants and section headers.
        "keywords":    [
            "combo big mac mediano",
            "big mac mediano",
            "home office con big mac",
            "home office big mac",
            "home office",
            "mctrio mediano big mac",
            "mc trio mediano big mac",
            "mctrio big mac",
            "mc trio big mac",
        ],
        "anti":        ["postre","mcflurry","nuggets","cuarto","quarter","triple",
                        "desayuno","tocino","favoritos","mctrío","mctrio"],
        "price_range": (80, 400),
    },
    {
        "name":        "Hamburguesa doble con queso",
        # Must match the standalone item, NOT combo descriptions like
        # "McPollo o Doble con Queso" or "Elige entre McPollo o Hamburguesa..."
        "keywords":    [
            "hamburguesa doble con queso",
            "hamburguesa doble queso",
            "doble con queso",
            "doble queso",
        ],
        "anti":        ["combo","papas","triple","mcnifica","mcpollo","elige","paquete","cajita"],
        "price_range": (40, 200),
    },
    {
        "name":        "Coca-Cola mediana",
        "keywords":    [
            "coca-cola mediana",
            "coca cola mediana",
            "coca mediana",
            "refresco mediano coca",
        ],
        "anti":        ["grande","1l","litro","2l","1.5","familiar","zero","light","sin azúcar","sin azucar"],
        "price_range": (25, 100),
    },
]

def extract_products_from_text(full_text: str) -> list:
    """
    Extrae los 3 productos del texto completo de la pagina.
    Ventana forward-only desde la linea del producto (evita precios del item anterior).
    Precio validado por rango conocido de cada producto.
    """
    results = []
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    for pdef in TARGET_PRODUCTS:
        lo, hi = pdef["price_range"]
        found = None

        for i, line in enumerate(lines):
            ll = line.lower()
            if not any(kw in ll for kw in pdef["keywords"]):
                continue
            if any(a in ll for a in pdef["anti"]):
                continue

            # Forward-only window: current line + 3 lines after (4 total).
            # DO NOT look backward — prices before the product name belong to
            # the PREVIOUS product in the grid layout.
            # 4 lines covers: name → description → $price → maybe discount
            # Keep it tight to avoid capturing prices from the NEXT product.
            window = " ".join(lines[i:i+4])
            prices = []
            # First pass: look for explicit $ prices
            for m in re.finditer(r'\$\s*([\d,]+\.?\d*)', window):
                v = float(m.group(1).replace(",",""))
                if lo <= v <= hi:
                    prices.append(v)
            if not prices:
                # Second pass: bare numbers — but EXCLUDE measurements (oz, ml, g, pzas, etc.)
                for m in re.finditer(r'(?<![\d$])(\d{2,3}(?:\.\d{2})?)(?!\d)', window):
                    # Check that this number isn't followed by a unit
                    end = m.end()
                    rest = window[end:end+6].strip().lower()
                    if any(rest.startswith(u) for u in ["oz","ml","g ","gr","pz","kg","cm","lt"]):
                        continue
                    v = float(m.group(1))
                    if lo <= v <= hi:
                        prices.append(v)

            if not prices:
                # Product name found but no visible price — still report it
                found = ProductData(name=pdef["name"])
                log.info(f"  product FOUND (no visible price): {pdef['name']}")
                break

            prices = sorted(set(prices), reverse=True)
            prod = ProductData(name=pdef["name"])

            # Extract discount % from the window text (e.g., "-43%", "43% OFF")
            disc_in_window = None
            dm = re.search(r'-?\s*(\d{1,2})\s*%', window)
            if dm:
                dv = float(dm.group(1))
                if 5 <= dv <= 70:
                    disc_in_window = dv

            if len(prices) >= 2:
                # Two prices: higher = original, lower = discounted
                prod.price_original = prices[0]
                prod.price_discounted = prices[-1]
                if prod.price_original > 0:
                    prod.discount_pct = round((1 - prod.price_discounted / prod.price_original) * 100, 1)
            elif len(prices) == 1 and disc_in_window:
                # One price + discount %:
                # In food delivery apps, when only ONE price is visible alongside
                # a -XX% badge, it's always the DISCOUNTED price (what the user pays).
                # The original (struck-through) price often doesn't appear in innerText.
                # So: shown price = discounted, original = price / (1 - disc/100).
                p = prices[0]
                prod.price_discounted = p
                prod.price_original = round(p / (1 - disc_in_window / 100), 2)
                prod.discount_pct = disc_in_window
            else:
                # Just one price, no discount info
                prod.price_original = prices[0]

            found = prod
            log.info(f"  product FOUND: {prod.name} orig={prod.price_original} disc={prod.price_discounted} %={prod.discount_pct}")
            break

        if found:
            results.append(found)
        else:
            log.info(f"  product not found in text: {pdef['name']}")

    return results

def extract_delivery_fee(text: str) -> Optional[float]:
    """Busca el delivery fee en el texto de la pagina."""
    # Check for free delivery first
    if re.search(r"env[iío]o?\s+gratis|gratis\s+env[iío]o?|delivery\s+gratis|env[iío]o?\s*(?:\$|MXN)\s*0(?:\b|\.00)", text, re.IGNORECASE):
        return 0.0
    # "Costo de envío a MXN0" (Uber Eats format)
    if re.search(r"(?:costo de env[iío]o?|env[iío]o?)\s+a?\s*MXN\s*0(?:\b|\.)", text, re.IGNORECASE):
        return 0.0
    patterns = [
        r"(?:env[iío]o?|delivery fee?|costo de env[iío]o?)[:\s]*(?:\$|MXN)\s*([\d,]+\.?\d*)",
        r"\$\s*([\d]+)\s*(?:de env[iío]o?|delivery)",
        r"env[iío]o?\s+(?:\$|MXN)\s*([\d,]+\.?\d*)",
        r"(?:costo de env[iío]o?|delivery)[:\s]+(?:\$|MXN)\s*([\d,]+\.?\d*)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            v = px(m.group(1))
            if v is not None and 0 <= v <= 200:
                return v
    return None

def extract_eta(text: str) -> Optional[int]:
    """Extrae tiempo estimado de entrega."""
    patterns = [
        r"(\d+)\s*[-–a]\s*(\d+)\s*min",
        r"(\d+)\s*min(?:utos?)?",
        r"llega(?:da)?\s+(?:m[aá]s\s+temprana\s+)?(?:en\s+)?(\d+)",
        r"estimad[ao]\s+(\d+)",
        r"entrega\s+(?:en\s+)?(\d+)",
        r"delivery\s+(\d+)\s*min",
        r"(\d+)\s*-\s*(\d+)\s*min",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            groups = [int(g) for g in m.groups() if g and 5 <= int(g) <= 120]
            if groups:
                return groups[0] if len(groups)==1 else (groups[0]+groups[1])//2
    return None

def extract_promo(text: str) -> Optional[float]:
    """Extrae el maximo descuento visible como hook del restaurante."""
    pcts = []
    for m in re.finditer(r"(\d+)\s*%", text):
        v = float(m.group(1))
        if 5 <= v <= 80:
            pcts.append(v)
    return max(pcts) if pcts else None

def extract_review_count(text: str) -> Optional[int]:
    """Extract the number of reviews/ratings from page text.
    Formats:
      - Rappi/Uber: "15,000+ calificaciones", "1500 calificaciones"
      - DiDi: "4.2(10000+)" — rating followed by review count in parens
      - Generic: "(3000+)" near rating context
    """
    patterns = [
        r"([\d.,]+)\+?\s*(?:calificaciones|calificaci[oó]n|rese[nñ]as|ratings|opiniones)",
        # DiDi: rating(count+) e.g. "4.2(10000+)"
        r"\d\.\d\s*\(\s*([\d.,]+)\+?\s*\)",
        # Generic: parenthesized large number with + (likely review count)
        r"\(\s*([\d.,]{3,})\+?\s*\)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "").replace(".", "")
            try:
                val = int(raw)
                if val >= 5:  # filter out tiny numbers that are likely not review counts
                    return val
            except ValueError:
                continue
    return None

def extract_rating(text: str) -> Optional[float]:
    patterns = [
        r"(\d+[.,]\d+)\s*(?:estrellas?|stars?|\(|\s*calificaci)",
        r"calificaci[oó]n[:\s]+(\d+[.,]\d+)",
        r"rating[:\s]+(\d+[.,]\d+)",
        r"★\s*(\d+[.,]\d+)",
        r"(\d+[.,]\d+)\s*★",
        r"(\d\.\d)\s*/\s*5",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            v = float(m.group(1).replace(",","."))
            if 1 <= v <= 5:
                return v
    return None

# ── Browser contexts ───────────────────────────────────────────────────────────

async def desktop_ctx(browser):
    ctx = await browser.new_context(
        user_agent=DESKTOP_UA,
        locale="es-MX",
        timezone_id="America/Mexico_City",
        viewport={"width":1366,"height":768},
        extra_http_headers={"Accept-Language":"es-MX,es;q=0.9"},
    )
    await ctx.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        "window.chrome={runtime:{}};"
    )
    return ctx

async def iphone_ctx(browser, storage_state: Optional[str] = None):
    ctx_kwargs = dict(
        user_agent=IPHONE_UA,
        locale="es-MX",
        timezone_id="America/Mexico_City",
        viewport={"width":390,"height":844},
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True,
        ignore_https_errors=True,
    )
    if storage_state:
        ctx_kwargs["storage_state"] = storage_state
    return await browser.new_context(**ctx_kwargs)

# ── Helper: find and interact with an input ──────────────────────────────────

async def find_and_fill_input(page: Page, selectors: list, text: str,
                               use_keyboard=False, clear_first=True) -> bool:
    """Try multiple selectors to find an input, click it, and fill/type text.
    Returns True if successfully typed into an input."""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if await el.count() == 0:
                continue
            # Click to focus (force=True bypasses overlays)
            try:
                await el.click(force=True)
            except Exception:
                # JS click fallback
                try:
                    await page.evaluate(
                        """(sel) => {
                            const el = document.querySelector(sel);
                            if (el) { el.focus(); el.click(); }
                        }""", sel)
                except Exception:
                    continue
            await asyncio.sleep(0.4)

            if clear_first:
                try:
                    await el.fill("")
                except Exception:
                    await page.keyboard.press("Control+a")
                    await page.keyboard.press("Backspace")
                await asyncio.sleep(0.2)

            if use_keyboard:
                await page.keyboard.type(text, delay=random.randint(30, 60))
            else:
                try:
                    await el.fill(text)
                except Exception:
                    await page.keyboard.type(text, delay=random.randint(30, 60))

            log.info(f"  typed into {sel}")
            return True
        except Exception:
            continue
    return False


async def click_first_suggestion(page: Page) -> bool:
    """Click the first autocomplete suggestion, or fallback to keyboard."""
    suggestion_sels = [
        '[class*="suggestion"] >> nth=0',
        'ul[role="listbox"] li:first-child',
        '.pac-item:first-child',
        '[class*="Suggestion"]:first-child',
        '[data-testid*="suggestion"]:first-child',
        'li[role="option"]:first-child',
    ]
    for sel in suggestion_sels:
        try:
            s = page.locator(sel).first
            if await s.count() > 0:
                await s.click()
                log.info(f"  suggestion clicked: {sel}")
                return True
        except Exception:
            continue

    # Keyboard fallback: ArrowDown + Enter
    try:
        await page.keyboard.press('ArrowDown')
        await asyncio.sleep(0.3)
        await page.keyboard.press('Enter')
        log.info("  suggestion selected via keyboard")
        return True
    except Exception:
        return False


# ── RAPPI ─────────────────────────────────────────────────────────────────────

class RappiScraper:
    PLATFORM = "rappi"

    ADDRESS_SELS = [
        'input[placeholder*="donde quieres" i]',
        'input[placeholder*="recibir" i]',
        '[data-testid="address_autocomplete"] input',
        'input[id*="address" i]',
        'input[placeholder*="direcci" i]',
    ]

    # Selectors for the search bar on Rappi main page.
    # Rappi uses a React component — sometimes it's a real input, sometimes
    # a styled div/button that opens a search overlay. We try both.
    SEARCH_CONTAINER_SELS = [
        '[data-qa="search-bar"]',
        '[class*="SearchBar" i]',
        '[class*="search-bar" i]',
        'div[class*="search" i] >> visible=true',
    ]

    SEARCH_INPUT_SELS = [
        'input[placeholder*="Comida" i]',
        'input[placeholder*="restaurantes" i]',
        'input[placeholder*="¿" i]',
        'input[placeholder*="busca" i]',
        'input[placeholder*="comer" i]',
        'input[data-qa="input"]',
        'input[type="search"]',
        'input[role="searchbox"]',
        'input[aria-label*="Buscar" i]',
        'input[aria-label*="search" i]',
    ]

    STORE_LINK_SEL = 'a[href*="mcdonalds"], a[href*="McDonald"], a[href*="mc-donalds"]'

    async def scrape(self, page: Page, addr: dict, sdir: Path, take_shots: bool) -> PlatformResult:
        r = PlatformResult(platform=self.PLATFORM)
        try:
            # ── 1. Load home page ─────────────────────────────────────────
            await page.goto("https://www.rappi.com.mx", wait_until="domcontentloaded", timeout=30000)
            await delay(2, 4)

            # ── 2. Set delivery address ───────────────────────────────────
            addr_ok = await find_and_fill_input(page, self.ADDRESS_SELS, addr["address"], use_keyboard=True)
            if addr_ok:
                await delay(2, 3)
                await click_first_suggestion(page)
                await delay(3, 5)
            else:
                # Last resort: press Enter and hope the page moves forward
                await page.keyboard.press("Enter")
                await delay(3, 4)
                log.warning("  [Rappi] address input not found, pressed Enter")

            # ── 3. Search for McDonald's ──────────────────────────────────
            search_done = False

            # Strategy A: Click on search container/area first to activate the input
            for sel in self.SEARCH_CONTAINER_SELS:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.click(force=True)
                        await asyncio.sleep(0.8)
                        log.info(f"  [Rappi] clicked search container: {sel}")
                        break
                except Exception:
                    continue

            # Strategy B: Find and type into the search input
            for _ in range(3):
                typed = await find_and_fill_input(
                    page, self.SEARCH_INPUT_SELS, "mc donalds", use_keyboard=True
                )
                if not typed:
                    # If no input found, try clicking containers again
                    for sel in self.SEARCH_CONTAINER_SELS:
                        try:
                            el = page.locator(sel).first
                            if await el.count() > 0:
                                await el.click(force=True)
                                await asyncio.sleep(1)
                                break
                        except Exception:
                            continue
                    continue

                # Press Enter to trigger search
                await page.keyboard.press('Enter')
                await delay(2, 4)

                # Check if search results with McDonalds links appeared
                try:
                    await page.wait_for_selector(self.STORE_LINK_SEL, timeout=5000)
                    search_done = True
                    log.info("  [Rappi] search results found")
                    break
                except Exception:
                    pass

                # Try picking a suggestion via keyboard
                try:
                    await page.keyboard.press('ArrowDown')
                    await asyncio.sleep(0.3)
                    await page.keyboard.press('Enter')
                    await delay(2, 4)
                    try:
                        await page.wait_for_selector(self.STORE_LINK_SEL, timeout=5000)
                        search_done = True
                        log.info("  [Rappi] search via keyboard suggestion")
                        break
                    except Exception:
                        pass
                except Exception:
                    pass

                await delay(1, 2)

            if not search_done:
                # Strategy C: JS injection as last resort
                for sel_raw in ['input[data-qa="input"]', 'input[type="search"]',
                                'input[placeholder*="Comida"]']:
                    try:
                        injected = await page.evaluate(
                            """(sel, val) => {
                                const el = document.querySelector(sel);
                                if (!el) return false;
                                el.focus();
                                el.value = val;
                                el.dispatchEvent(new Event('input', {bubbles:true}));
                                el.dispatchEvent(new Event('change', {bubbles:true}));
                                const ke = new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, bubbles:true});
                                el.dispatchEvent(ke);
                                return true;
                            }""", [sel_raw, "mc donalds"])
                        if injected:
                            log.info(f"  [Rappi] search injected via JS: {sel_raw}")
                            await delay(3, 5)
                            try:
                                await page.wait_for_selector(self.STORE_LINK_SEL, timeout=6000)
                                search_done = True
                            except Exception:
                                pass
                        if search_done:
                            break
                    except Exception:
                        continue

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "search", sdir)

            # ── 4. Find store link and NAVIGATE via goto (avoids overlay) ─
            store_url = None
            for _ in range(5):
                try:
                    links = await page.locator(self.STORE_LINK_SEL).all()
                except Exception:
                    break
                for link in links:
                    try:
                        href = await link.get_attribute("href") or ""
                        name = (await link.inner_text()).strip()
                        if not (valid_mcdo(name) or valid_mcdo(href)):
                            continue
                        # Build absolute URL
                        if href.startswith("/"):
                            store_url = "https://www.rappi.com.mx" + href.split("?")[0]
                        elif href.startswith("http"):
                            store_url = href.split("?")[0]
                        else:
                            store_url = "https://www.rappi.com.mx/" + href.split("?")[0]
                        r.restaurant_name = name[:60]
                        break
                    except Exception:
                        continue
                if store_url:
                    break
                await delay(1, 2)

            if not store_url:
                r.status = "partial_no_store"
                log.warning("  [Rappi] no valid McDonalds store link found")
                return r

            # Navigate directly — this AVOIDS the overlay click-interception bug
            log.info(f"  [Rappi] navigating to store: {store_url}")
            await page.goto(store_url, wait_until="domcontentloaded", timeout=30000)
            r.restaurant_available = True
            await delay(3, 5)

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "store", sdir)

            # ── 5. Progressive scroll + text collection ─────────────────
            # Rappi uses an internal scrollable container for the menu.
            # window.scrollBy does nothing. We scroll the container AND
            # collect text at each position to handle virtual scrolling.
            full_text = await scroll_and_collect_text(page, pause=0.6, max_scrolls=35)

            # Debug: save text dump so we can inspect what was captured
            try:
                dump_path = sdir / f"{addr['id']}_rappi_text_dump.txt"
                dump_path.write_text(full_text, encoding="utf-8")
                log.info(f"  [Rappi] text dump: {dump_path.name} ({len(full_text)} chars)")
            except Exception:
                pass

            # Log key product searches for debugging
            ft_lower = full_text.lower()
            for kw in ["home office", "big mac", "hamburguesa doble", "coca-cola", "coca cola"]:
                log.info(f"  [Rappi] keyword '{kw}' found: {kw in ft_lower}")

            # ── 6. Extract data from collected text ───────────────────────
            r.products = extract_products_from_text(full_text)
            r.delivery_fee = extract_delivery_fee(full_text)
            r.eta_min = extract_eta(full_text)
            r.promo_general_pct = extract_promo(full_text)
            r.rating = extract_rating(full_text)
            r.review_count = extract_review_count(full_text)

            log.info(f"  [Rappi] products={len(r.products)} fee={r.delivery_fee} eta={r.eta_min} promo={r.promo_general_pct}%")

            r.compute_financials(self.PLATFORM)
            r.status = "success" if len(r.products) > 0 else "partial"

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "final", sdir)

        except Exception as e:
            r.status = "error"
            r.error_detail = str(e)[:300]
            log.warning(f"[Rappi] {addr['id']} {type(e).__name__}: {str(e)[:100]}")

        return r


# ── UBER EATS ─────────────────────────────────────────────────────────────────

class UberEatsScraper:
    PLATFORM = "ubereats"

    ADDRESS_SELS = [
        '#location-typeahead-home-input',
        'input[id*="location-typeahead"]',
        'input[placeholder*="direcci" i]',
        'input[placeholder*="Ingresa tu direcci" i]',
    ]

    STORE_LINK_SEL = 'a[href*="/store/mcdonalds"], a[href*="/store/mc-donalds"]'

    async def scrape(self, page: Page, addr: dict, sdir: Path, take_shots: bool) -> PlatformResult:
        r = PlatformResult(platform=self.PLATFORM)
        try:
            # ── 1. Load home and set address ──────────────────────────────
            await page.goto("https://www.ubereats.com/mx", wait_until="domcontentloaded", timeout=35000)
            await delay(2, 4)

            addr_ok = await find_and_fill_input(page, self.ADDRESS_SELS, addr["address"], use_keyboard=True)
            if addr_ok:
                await delay(2, 3.5)
                # Wait for autocomplete suggestions
                try:
                    await page.wait_for_selector(
                        '#location-typeahead-home-menu li, ul[role="listbox"] li',
                        timeout=7000
                    )
                except Exception:
                    pass
                await click_first_suggestion(page)
                log.info("  [Uber] address set")
                await delay(3, 5)
            else:
                await page.keyboard.press("Enter")
                await delay(3, 4)
                log.warning("  [Uber] address input not found")

            # ── 2. Search — navigate directly to search URL ───────────────
            # This is MUCH more reliable than trying to find/interact with
            # the search bar UI which has inconsistent selectors.
            search_url = "https://www.ubereats.com/mx/search?q=McDonalds"
            log.info(f"  [Uber] navigating to search URL")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await delay(3, 5)

            # Wait for search results to load
            try:
                await page.wait_for_selector(self.STORE_LINK_SEL, timeout=10000)
            except Exception:
                # Fallback: try broader selector
                try:
                    await page.wait_for_selector('a[href*="/store/"]', timeout=5000)
                except Exception:
                    log.warning("  [Uber] no store links in search results")

            if take_shots:
                await shot(page, addr["id"], self.PLATFORM, "search", sdir)

            # ── 3. Find store link and navigate ───────────────────────────
            store_url = None

            # Try specific McDonalds links first
            try:
                links = await page.locator(self.STORE_LINK_SEL).all()
                for link in links[:15]:
                    try:
                        name = (await link.inner_text()).strip()
                        href = await link.get_attribute("href") or ""
                        if valid_mcdo(name) or valid_mcdo(href):
                            if href.startswith("/"):
                                store_url = "https://www.ubereats.com" + href.split("?")[0]
                            elif href.startswith("http"):
                                store_url = href.split("?")[0]
                            r.restaurant_name = name[:60]
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # Fallback: any store link mentioning mcdonald
            if not store_url:
                try:
                    links = await page.locator('a[href*="/store/"]').all()
                    for link in links[:20]:
                        try:
                            name = (await link.inner_text()).strip()
                            href = await link.get_attribute("href") or ""
                            if "mcdonald" in name.lower() and valid_mcdo(name):
                                if href.startswith("/"):
                                    store_url = "https://www.ubereats.com" + href.split("?")[0]
                                elif href.startswith("http"):
                                    store_url = href.split("?")[0]
                                r.restaurant_name = name[:60]
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            if not store_url:
                r.status = "partial_no_store"
                log.warning("  [Uber] no valid McDonalds store URL found")
                return r

            log.info(f"  [Uber] store URL: {store_url}")
            await page.goto(store_url, wait_until="domcontentloaded", timeout=35000)
            await delay(2, 3)
            r.restaurant_available = True

            # Fix empty restaurant_name: extract from store page heading
            if not r.restaurant_name.strip():
                try:
                    heading = await page.locator("h1").first.inner_text(timeout=3000)
                    if heading and heading.strip():
                        r.restaurant_name = heading.strip()[:60]
                        log.info(f"  [Uber] restaurant name from h1: {r.restaurant_name}")
                except Exception:
                    # Fallback: extract from page text
                    try:
                        title_text = await page.title()
                        if title_text:
                            # Uber Eats titles are like "McDonald's (Plaza Galerías) | Uber Eats"
                            name_part = title_text.split("|")[0].strip()
                            if name_part:
                                r.restaurant_name = name_part[:60]
                    except Exception:
                        pass

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "store", sdir)

            # ── 4. Scroll to load ALL sections (Bebidas is at the bottom) ──
            # Use scroll_and_collect_text — handles internal scroll containers
            # and does NOT deduplicate (same price can appear for multiple products)
            full_text = await scroll_and_collect_text(page, pause=0.6, max_scrolls=35)

            # Debug: save text dump
            try:
                dump_path = sdir / f"{addr['id']}_ubereats_text_dump.txt"
                dump_path.write_text(full_text, encoding="utf-8")
                log.info(f"  [Uber] text dump: {dump_path.name} ({len(full_text)} chars)")
            except Exception:
                pass

            # Log key product searches
            ft_lower = full_text.lower()
            for kw in ["home office", "big mac", "hamburguesa doble", "coca-cola", "coca cola"]:
                log.info(f"  [Uber] keyword '{kw}' found: {kw in ft_lower}")

            # ── 5. Extract data from page text ────────────────────────────
            r.products = extract_products_from_text(full_text)
            r.delivery_fee = extract_delivery_fee(full_text)
            r.eta_min = extract_eta(full_text)
            r.promo_general_pct = extract_promo(full_text)
            r.rating = extract_rating(full_text)
            r.review_count = extract_review_count(full_text)

            log.info(f"  [Uber] products={len(r.products)} fee={r.delivery_fee} eta={r.eta_min} promo={r.promo_general_pct}%")

            r.compute_financials(self.PLATFORM)
            r.status = "success" if len(r.products) > 0 else "partial"

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "final", sdir)

        except Exception as e:
            r.status = "error"
            r.error_detail = str(e)[:300]
            log.warning(f"[Uber] {addr['id']} {type(e).__name__}: {str(e)[:100]}")

        return r


# ── DIDI FOOD ─────────────────────────────────────────────────────────────────

class DiDiFoodScraper:
    """
    DiDi solo deja navegar si se emula un móvil, se elige ciudad, se pulsa
    "Entra al sitio" y (cuando aparece) se completa el login. Esta clase se
    encarga de automatizar todo ese flujo antes de extraer texto como en las
    otras plataformas.
    """

    PLATFORM = "didifood"
    _DEFAULT_DIDI_HOME = os.environ.get("DIDI_BASE_URL", "https://www.didi-food.com/es-MX/")
    _LEGACY_FEED_URL = os.environ.get(
        "DIDI_FEED_URL",
        "https://www.didi-food.com/es-MX/food/feed/?pl=eyJwb2lJZCI6IjExMTc3NjY4NDczMTIxNjY5MTIiLCJkaXNwbGF5TmFtZSI6IlRlcnJhemEgUm9tYSIsImFkZHJlc3MiOiJBdmVuaWRhIE9heGFjYSA5MCwgUm9tYSBOdGUuLCBDdWF1aHTDqW1vYywgMDY3MDAgQ2l1ZGFkIGRlIE3DqXhpY28sIENETVgsIE3DqXhpY28iLCJsYXQiOjE5LjQxODY5OTY4LCJsbmciOi05OS4xNjcyNTU5LCJzcmNUYWciOiJuZXdlcyIsInBvaVNyY1RhZyI6Im1hbnVhbF9zdWciLCJjb29yZGluYXRlVHlwZSI6Indnczg0IiwiY2l0eUlkIjo1MjA5MDEwMCwiY2l0eSI6IkNpdWRhZCBkZSBNw6l4aWNvIiwic2VhcmNoSWQiOiIwYTkzMzE3ZDY5YzA0NmJlMjc3ZjFkOTMzZjY5ZTQwMiIsImFkZHJlc3NBbGwiOiJUZXJyYXphIFJvbWEsIEF2ZW5pZGEgT2F4YWNhIDkwLCBSb21hIE50ZS4sIEN1YXVodMOpbW9jLCAwNjcwMCBDaXVkYWQgZGUgTcOpeGljbywgQ0RNWCwgTcOpeGljbyIsImFkZHJlc3NBbGxEaXNwbGF5IjoiQXZlbmlkYSBPYXhhY2EgOTAsIFJvbWEgTnRlLiwgQ3VhdWh0w6ltb2MsIDA2NzAwIENpdWRhZCBkZSBNw6l4aWNvLCBDRE1YLCBNw6l4aWNvIiwiY291bnRyeUNvZGUiOiJNWCIsImNvdW50cnlJZCI6NTIsImRpc3RTdHIiOiIyLjBrbSIsImRpc3QiOjE5NjAsInBvaVR5cGUiOiJOaWdodGxpZmUtRW50ZXJ0YWlubWVudDtDb2NrdGFpbCBMb3VuZ2U7TmlnaHQgQ2x1YjtEYW5jaW5nO1Jlc3RhdXJhbnQ7QmFyIG9yIFB1YiIsImNvdW50eUlkIjo1MjA5MDExNCwiY291bnR5R3JvdXBJZCI6NTIwOTAxMDAwMDAxLCJhaWQiOiIifQ%3D%3D",
    )
    ENTRY_URLS = [
        _LEGACY_FEED_URL,
        _DEFAULT_DIDI_HOME,
        "https://www.didi-food.com/es-MX/food/feed/",
        "https://web.didiglobal.com/mx/food/",
        "https://www.didifood.com/mx",
        "https://m.didiglobal.com/mx/food/",
    ]
    CITY_MAP = {
        "Ciudad de Mexico": "Ciudad de México",
        "Guadalajara": "Guadalajara",
        "Monterrey": "Monterrey",
    }
    ENTER_KEYWORDS = [
        "entra al sitio",
        "entra",
        "ver restaurantes",
        "entrar",
    ]
    LOGIN_TRIGGER_KEYWORDS = [
        "iniciar sesión",
        "iniciar sesion",
        "mi perfil",
        "mi cuenta",
        "entrar",
        "acceso",
    ]
    TERMS_KEYWORDS = [
        "acepto",
        "aceptar",
        "términos",
        "terminos",
        "privacidad",
    ]
    ADDRESS_INPUTS = [
        'input[placeholder*="direcci" i]',
        'input[placeholder*="ingresa" i]',
        'input[placeholder*="domicilio" i]',
        'input[id*="address" i]',
        'input[data-testid*="address" i]',
        'input[name*="address" i]',
        'textarea[placeholder*="direcci" i]',
        'input[type="text"]:not([hidden])',
    ]
    ADDRESS_TRIGGER_KEYWORDS = [
        "ingresa tu direccion",
        "ingresa tu dirección",
        "agrega tu direccion",
        "cambiar direccion",
        "agregar direccion",
        "poner direccion",
    ]
    ADDRESS_HEADER_SELS = [
        '[data-testid*="address-chip" i]',
        '[data-testid*="address-header" i]',
        '[data-testid*="address-selector" i]',
        '[data-testid*="location" i]',
        '[data-testid*="header-location" i]',
        '[data-testid*="delivery-address" i]',
        '[aria-label*="dirección" i]',
        '[aria-label*="direccion" i]',
        'button:has-text("Ingresa tu dirección")',
        'button:has-text("Ingresa tu direccion")',
        'button:has-text("Agregar dirección")',
        'button:has-text("Agregar direccion")',
        'button:has-text("Selecciona una dirección")',
        'button:has-text("Selecciona una direccion")',
        'div:has-text("Ingresa tu dirección")',
        'header button[role="button"]:has-text("Dirección")',
    ]
    SEARCH_INPUTS = [
        'input[placeholder*="tacos" i]',
        'input[placeholder*="hamburguesa" i]',
        'input[placeholder*="restaurante" i]',
        'input[placeholder*="restaurantes o comida" i]',
        'input[placeholder*="buscar" i]',
        'input[placeholder*="busca" i]',
        'input[placeholder*="comida" i]',
        'input[placeholder*="¿" i]',
        'input[placeholder*="qu" i]',
        'input[type="search"]',
        'input[role="searchbox"]',
        'input[id*="search" i]',
        'input[name*="search" i]',
        'input[data-testid*="search" i]',
        'input[data-qa*="search" i]',
        'input[aria-label*="buscar" i]',
        'input[aria-label*="search" i]',
    ]
    STORE_CARD_SELS = [
        'a:has-text("McDonald")',
        'a:has-text("Mc Donald")',
        '[class*="restaurant" i]:has-text("Mc")',
        '[role="link"]:has-text("Mc")',
        'div:has-text("McDonald")',
        '[role="button"]:has-text("McDonald")',
    ]
    SEARCH_CHIP_KEYWORDS = ["mcdonald's", "mcdonalds", "mc donalds"]

    CATEGORY_FALLBACKS = [
        "Mc para Todos",
        "Paquetes",
        "Paquete",
        "McTrio",
        "McTrío",
        "A la Carta",
        "Bebidas",
        "Postres",
        "Complementos",
    ]
    LOGIN_EMAIL_SELS = [
        'input[type="email"]',
        'input[name*="correo" i]',
        'input[placeholder*="correo" i]',
    ]
    LOGIN_PASS_SELS = [
        'input[type="password"]',
        'input[name*="contra" i]',
        'input[placeholder*="contraseña" i]',
    ]
    LOGIN_PHONE_SELS = [
        'input[type="tel"]',
        'input[name*="tel" i]',
        'input[name*="phone" i]',
        'input[placeholder*="tel" i]',
        'input[placeholder*="cel" i]',
    ]
    LOGIN_BUTTON_SELS = [
        'button:has-text("Iniciar sesión")',
        'button:has-text("entrar")',
        'button:has-text("continuar")',
        '[data-testid*="login-submit"]',
    ]
    LOGIN_TRIGGER_SELS = [
        '[data-testid*="header-login"]',
        '[aria-label*="Iniciar sesión" i]',
        'button:has-text("Iniciar sesión")',
        'a:has-text("Iniciar sesión")',
        'span:has-text("Iniciar sesión")',
    ]
    OTP_INPUT_SELS = [
        'input[placeholder*="código" i]',
        'input[placeholder*="codigo" i]',
        'input[maxlength="6"]',
        'input[type="tel"]',
    ]
    OTP_TEXT_MARKERS = [
        "código de verificación",
        "codigo de verificacion",
        "ingresa el código",
        "ingresa el codigo",
    ]

    def __init__(self):
        self.email = os.environ.get("DIDI_EMAIL")
        self.password = os.environ.get("DIDI_PASSWORD")
        self.phone = os.environ.get("DIDI_PHONE")
        code = os.environ.get("DIDI_PHONE_COUNTRY", "+54")
        if code and not code.strip().startswith("+"):
            code = f"+{code.strip()}"
        self.phone_country = code
        self.storage_path = DIDI_STORAGE_PATH
        self.session_dirty = False
        if self.storage_path.exists():
            log.info(f"  [DiDi] cargando sesión persistida desde {self.storage_path}")

    async def _switch_to_latest_page(self, page: Page) -> Page:
        try:
            pages = page.context.pages
            if pages and pages[-1] is not page:
                new_page = pages[-1]
                await new_page.wait_for_load_state("domcontentloaded")
                log.info("  [DiDi] switched to latest popup page")
                return new_page
        except Exception:
            pass
        return page

    async def _detect_otp_prompt(self, page: Page) -> bool:
        for sel in self.OTP_INPUT_SELS:
            try:
                if await page.locator(sel).count() > 0:
                    log.warning("  [DiDi] OTP input detected")
                    return True
            except Exception:
                continue
        try:
            body = (await page.inner_text("body")).lower()
            if any(marker in body for marker in self.OTP_TEXT_MARKERS):
                log.warning("  [DiDi] OTP text detected")
                return True
        except Exception:
            pass
        return False

    async def _focus_search_input(self, page: Page) -> bool:
        """Focus the search input on DiDi mobile.
        On the feed page, there's usually a search icon (magnifying glass) or a
        placeholder bar at the top. Tapping it opens the actual search input."""
        page = await self._switch_to_latest_page(page)
        # First, try tapping the search icon/bar at the top of the feed
        search_trigger_sels = [
            '[data-testid*="search" i]',
            '[class*="search" i]:not(input)',
            '[aria-label*="buscar" i]',
            '[aria-label*="search" i]',
            'svg[class*="search" i]',
        ]
        for sel in search_trigger_sels:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    try:
                        await el.tap()
                    except Exception:
                        await el.click(force=True)
                    await asyncio.sleep(0.8)
                    log.info(f"  [DiDi] tapped search trigger: {sel}")
                    page = await self._switch_to_latest_page(page)
                    break
            except Exception:
                continue

        # Try tapping the search bar/placeholder via JS (looks for elements with search-related text)
        try:
            tapped = await page.evaluate("""
                () => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                    // Look for a div/span that acts as search placeholder
                    const candidates = Array.from(document.querySelectorAll('div, span, button, a'));
                    for (const el of candidates) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const text = norm(el.innerText || el.textContent || el.getAttribute('placeholder') || '');
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 100 || rect.height < 20 || rect.height > 60) continue;
                        // Must be near top of page
                        if (rect.top > 200) continue;
                        if (text.includes('buscar') || text.includes('busca') || text.includes('restaurante')
                            || text.includes('comida') || text.includes('tacos') || text.includes('hamburguesa')
                            || text.includes('que se te antoja')) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            if tapped:
                log.info("  [DiDi] tapped search placeholder bar")
                await asyncio.sleep(0.8)
                page = await self._switch_to_latest_page(page)
        except Exception:
            pass

        # Now try to find and focus the actual search input
        selectors = [
            'input[placeholder*="buscar" i]',
            'input[placeholder*="restaurante" i]',
            'input[placeholder*="restaurantes o comida" i]',
            'input[placeholder*="tacos" i]',
            'input[placeholder*="comida" i]',
            '[data-testid*="search"] input',
            'form[role="search"] input',
            'div[class*="search" i] input',
            'input[type="search"]',
            'input[role="searchbox"]',
            'input[id*="search" i]',
            'input[name*="search" i]',
            'input[data-testid*="search" i]',
            'input[data-qa*="search" i]',
            '[role="search"] input',
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    try:
                        await el.wait_for(state="visible", timeout=1500)
                    except Exception:
                        pass
                    try:
                        await el.tap()
                    except Exception:
                        await el.click(force=True)
                    await asyncio.sleep(0.2)
                    log.info(f"  [DiDi] focused search input: {sel}")
                    return True
            except Exception:
                continue

        try:
            return await page.evaluate(
                """
                () => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
                    const inputs = Array.from(document.querySelectorAll('input, textarea, [contenteditable="true"]'));
                    for (const el of inputs) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const ph = norm(el.placeholder || '');
                        const aria = norm(el.getAttribute('aria-label') || '');
                        const role = norm(el.getAttribute('role') || '');
                        const cls = norm(el.className || '');
                        if (ph.includes('buscar') || ph.includes('comida') || ph.includes('restaurante')
                            || ph.includes('tacos') || ph.includes('hamburguesa')
                            || aria.includes('buscar') || role.includes('search') || cls.includes('search')) {
                            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                                el.focus();
                                el.click();
                            } else if (el.isContentEditable) {
                                el.focus();
                            }
                            return true;
                        }
                    }
                    return false;
                }
                """
            )
        except Exception:
            return False

    async def _wait_for_address_confirmation(self, page: Page, addr: dict) -> bool:
        """Check if the address is already shown in the page UI.
        Uses multiple strategies: exact text match, partial body text search,
        and checking if the feed has restaurant content (meaning address is set)."""
        # Strategy 1: look for zone/city text in page elements
        tokens = [addr.get("zone"), addr.get("city")]
        for token in tokens:
            if not token:
                continue
            try:
                await page.locator(f"text={token}").first.wait_for(timeout=3000)
                log.info(f"  [DiDi] direccion visible en UI: {token}")
                return True
            except Exception:
                continue

        # Strategy 2: check body text for address fragments
        try:
            body = await page.evaluate("() => document.body.innerText")
            body_lower = body.lower()
            for token in tokens:
                if token and token.lower() in body_lower:
                    log.info(f"  [DiDi] direccion encontrada en body text: {token}")
                    return True
            # Also check for address street fragments
            address_str = addr.get("address", "")
            if address_str:
                # Check first meaningful part of address (street name)
                parts = address_str.split(",")
                for part in parts[:2]:
                    clean = part.strip().lower()
                    if len(clean) > 5 and clean in body_lower:
                        log.info(f"  [DiDi] fragmento de direccion encontrado: {part.strip()}")
                        return True
        except Exception:
            pass

        # Strategy 3: if we see restaurant cards/content, address is likely set
        try:
            has_restaurants = await page.evaluate("""
                () => {
                    const text = document.body.innerText.toLowerCase();
                    return text.includes('restaurante') || text.includes('hamburguesa')
                        || text.includes('comida') || text.includes('envio gratis')
                        || text.includes('min');
                }
            """)
            if has_restaurants:
                log.info("  [DiDi] feed con restaurantes visible — direccion ya esta seteada")
                return True
        except Exception:
            pass

        log.warning("  [DiDi] no pude confirmar la direccion en pantalla")
        return False

    async def _persist_session(self, context: BrowserContext):
        if not self.storage_path:
            return
        # Si la sesión ya está guardada y no hubo cambios, evitamos escribir innecesariamente,
        # pero aseguramos que el JSON exista en disco al menos una vez.
        if not self.session_dirty and self.storage_path.exists():
            return
        try:
            await context.storage_state(path=str(self.storage_path))
            self.session_dirty = False
            log.info(f"  [DiDi] sesión guardada en {self.storage_path}")
        except Exception as exc:
            log.warning(f"  [DiDi] no se pudo guardar la sesión: {exc}")

    async def _session_already_active(self, page: Page) -> bool:
        """Detecta si el usuario ya está logueado usando la storage_state actual."""
        avatar_selectors = [
            '[data-testid*="avatar" i]',
            '[data-testid*="profile" i]',
            '[aria-label*="perfil" i]',
            '[aria-label*="cuenta" i]',
            '[class*="avatar" i]'
        ]
        for sel in avatar_selectors:
            try:
                if await page.locator(sel).first.count() > 0:
                    log.info("  [DiDi] avatar/perfil detectado — sesión ya activa")
                    return True
            except Exception:
                continue

        try:
            login_present = await page.evaluate(
                """
                (keywords) => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
                    const nodes = Array.from(document.querySelectorAll('button, a, div, span'));
                    const targets = keywords.map(norm);
                    for (const node of nodes) {
                        if (!node || !node.isConnected || node.offsetParent === null) continue;
                        const text = norm(node.innerText || node.textContent || '');
                        if (!text) continue;
                        if (targets.some(t => text.includes(t))) {
                            return true;
                        }
                    }
                    return false;
                }
                """,
                self.LOGIN_TRIGGER_KEYWORDS + ["iniciar sesion", "inicia sesion", "entrar"],
            )
            if login_present:
                return False
        except Exception:
            pass

        try:
            body = (await page.evaluate("() => document.body.innerText") or "").lower()
            if any(token in body for token in ["cerrar sesión", "cerrar sesion", "mis pedidos", "mi cuenta"]):
                log.info("  [DiDi] elementos de cuenta detectados en el body — reusamos sesión")
                return True
        except Exception:
            pass

        return False

    async def _handle_login_and_persist(self, page: Page) -> bool:
        handled = await self._handle_login_if_present(page)
        if handled:
            await self._persist_session(page.context)
        return handled

    async def _select_city(self, page: Page, city_name: str) -> bool:
        if not city_name:
            return False
        try:
            await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            await delay(1, 2)
        except Exception:
            pass
        clicked = await self._click_by_keywords(page, [city_name])
        if clicked:
            log.info(f"  [DiDi] selected city: {city_name}")
            await delay(2, 3)
        return clicked

    async def _wait_for_otp(self, page: Page, timeout_seconds=120) -> bool:
        """Wait for the user to manually enter the OTP verification code.
        DiDi sends an SMS code on every login — this step cannot be automated.
        The scraper pauses here and polls until the OTP screen disappears."""
        log.info("  [DiDi] *** PASO MANUAL: Ingresa el codigo de verificacion en el navegador ***")
        log.info(f"  [DiDi] Esperando hasta {timeout_seconds}s para que ingreses el codigo...")

        for i in range(timeout_seconds // 3):
            await asyncio.sleep(3)
            # Check if we moved past the OTP screen
            if not await self._detect_otp_prompt(page):
                log.info("  [DiDi] OTP completado, continuando...")
                return True
            # Check if a new page opened (redirect after OTP)
            page = await self._switch_to_latest_page(page)
            if not await self._detect_otp_prompt(page):
                log.info("  [DiDi] OTP completado (nueva pagina), continuando...")
                return True
            if i % 10 == 0 and i > 0:
                log.info(f"  [DiDi] Aun esperando OTP... ({i*3}s)")

        log.warning("  [DiDi] Timeout esperando OTP")
        return False

    async def _ensure_logged_in(self, page: Page) -> Page:
        """Login flow for DiDi Food:
        1. Click login trigger
        2. Set country code (+54)
        3. Enter phone number
        4. Check terms & conditions checkbox
        5. Click 'Siguiente' button
        6. WAIT for user to manually enter OTP code (SMS verification)
        """
        if self.storage_path.exists():
            try:
                await page.wait_for_load_state("domcontentloaded")
            except Exception:
                pass
            if await self._session_already_active(page):
                await self._persist_session(page.context)
                return await self._switch_to_latest_page(page)
        for attempt in range(3):
            trigger_clicked = await self._click_by_keywords(page, self.LOGIN_TRIGGER_KEYWORDS)
            if not trigger_clicked:
                trigger_clicked = await self._trigger_login_flow(page)
            if trigger_clicked:
                await delay(2, 3)
                page = await self._switch_to_latest_page(page)
            form_filled = await self._handle_login_and_persist(page)
            if form_filled:
                # Check if OTP screen appeared — wait for user to enter code
                if await self._detect_otp_prompt(page):
                    otp_ok = await self._wait_for_otp(page, timeout_seconds=120)
                    if not otp_ok:
                        raise RuntimeError("Timeout esperando codigo OTP manual")
                    page = await self._switch_to_latest_page(page)
                    await self._persist_session(page.context)
                await delay(2, 3)
                page = await self._switch_to_latest_page(page)
                await self._persist_session(page.context)
                return page
            if not trigger_clicked:
                await delay(1, 2)
        return page

    async def _click_by_keywords(self, page: Page, keywords) -> bool:
        try:
            return await page.evaluate(
                """
                (texts) => {
                    const norm = (s) => (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                    const nodes = Array.from(document.querySelectorAll('button,a,div,span'));
                    for (const keyword of texts) {
                        const target = norm(keyword);
                        if (!target) continue;
                        for (const node of nodes) {
                            if (!node || !node.isConnected || node.offsetParent === null) continue;
                            const content = norm(node.innerText || node.textContent || '');
                            if (!content) continue;
                            if (content.includes(target)) {
                                node.scrollIntoView({behavior:'auto', block:'center'});
                                node.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }
                """,
                keywords,
            )
        except Exception:
            return False

    async def _handle_login_if_present(self, page: Page) -> bool:
        """Handles DiDi login form:
        1. Detect phone input (primary flow)
        2. Set country code to +54
        3. Enter phone number
        4. Check the terms & conditions checkbox/circle
        5. Click 'Siguiente' (next) button
        """
        email_present = False
        for sel in self.LOGIN_EMAIL_SELS:
            try:
                if await page.locator(sel).count() > 0:
                    email_present = True
                    break
            except Exception:
                continue

        phone_present = False
        for sel in self.LOGIN_PHONE_SELS:
            try:
                if await page.locator(sel).count() > 0:
                    phone_present = True
                    break
            except Exception:
                continue

        filled = False
        needs_terms = False
        if email_present:
            if not (self.email and self.password):
                log.warning("  [DiDi] login requiere DIDI_EMAIL y DIDI_PASSWORD (define variables de entorno)")
                return False
            email_ok = await find_and_fill_input(page, self.LOGIN_EMAIL_SELS, self.email, use_keyboard=False)
            pass_ok = await find_and_fill_input(page, self.LOGIN_PASS_SELS, self.password, use_keyboard=False)
            filled = email_ok and pass_ok
        elif phone_present:
            if not self.phone:
                log.warning("  [DiDi] login requiere DIDI_PHONE (define variables de entorno)")
                return False
            await self._set_phone_country(page)
            await delay(0.5, 1)
            filled = await find_and_fill_input(page, self.LOGIN_PHONE_SELS, self.phone, use_keyboard=True)
            needs_terms = True
        else:
            return False

        if not filled:
            log.warning("  [DiDi] no se pudo completar el formulario de login")
            return False

        # Accept terms & conditions checkbox (required before clicking Siguiente)
        if needs_terms:
            await delay(0.5, 1)
            terms_ok = await self._accept_terms(page)
            if not terms_ok:
                log.warning("  [DiDi] no se pudo aceptar Terminos y Condiciones, intentando de todas formas...")
            else:
                log.info("  [DiDi] terminos y condiciones aceptados")
            await delay(0.3, 0.5)

        # Click 'Siguiente' / submit button — use tap for mobile emulation
        siguiente_sels = [
            'button:has-text("Siguiente")',
            'button:has-text("siguiente")',
            'button:has-text("SIGUIENTE")',
            'button:has-text("Enviar")',
            'button:has-text("Enviar código")',
            '[type="submit"]',
        ] + self.LOGIN_BUTTON_SELS
        for sel in siguiente_sels:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    clicked = False
                    # Try tap first (mobile), then progressively stronger fallbacks
                    try:
                        await btn.tap()
                        clicked = True
                    except Exception:
                        clicked = False
                    if not clicked:
                        try:
                            await btn.click(force=True)
                            clicked = True
                        except Exception:
                            clicked = False
                    if not clicked:
                        try:
                            await btn.evaluate("(node) => node.click()")
                            clicked = True
                        except Exception:
                            clicked = False
                    if not clicked:
                        continue
                    self.session_dirty = True
                    log.info(f"  [DiDi] tapped submit/siguiente button: {sel}")
                    await delay(3, 5)
                    return True
            except Exception:
                continue

        # Fallback: find Siguiente button via JS and tap by coordinates
        try:
            btn_coords = await page.evaluate(
                """
                () => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                    const targets = ['siguiente', 'enviar', 'continuar', 'enviar codigo'];
                    const nodes = Array.from(document.querySelectorAll('button, [role="button"], a, div, span'));
                    for (const node of nodes) {
                        if (!node.isConnected || node.offsetParent === null) continue;
                        const text = norm(node.innerText || node.textContent || '');
                        if (!text) continue;
                        for (const t of targets) {
                            if (text.includes(t)) {
                                const rect = node.getBoundingClientRect();
                                if (rect.width > 40 && rect.height > 20) {
                                    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
                                }
                            }
                        }
                    }
                    return null;
                }
                """
            )
            if btn_coords:
                try:
                    await page.touchscreen.tap(btn_coords["x"], btn_coords["y"])
                except Exception:
                    await page.mouse.click(btn_coords["x"], btn_coords["y"])
                self.session_dirty = True
                log.info(f"  [DiDi] tapped siguiente via coordinates ({btn_coords['x']:.0f}, {btn_coords['y']:.0f})")
                await delay(2, 4)
                return True
        except Exception:
            pass

        # Last resort: keyword click
        if await self._click_by_keywords(page, ["Siguiente", "siguiente", "Continuar", "continuar"]):
            self.session_dirty = True
            log.info("  [DiDi] clicked siguiente via keyword")
            await delay(2, 4)
            return True

        log.warning("  [DiDi] no se encontro boton Siguiente")
        return False

    async def _set_phone_country(self, page: Page) -> bool:
        if not self.phone_country:
            return False
        target = self.phone_country.strip()
        opened = False
        try:
            opened = await page.evaluate(
                """
                () => {
                    const nodes = Array.from(document.querySelectorAll('button, div, span'));
                    for (const node of nodes) {
                        const text = (node.innerText || node.textContent || '').trim();
                        if (/^\\+\\d+$/.test(text)) {
                            node.click();
                            return true;
                        }
                    }
                    return false;
                }
                """
            )
        except Exception:
            opened = False
        if not opened:
            log.warning("  [DiDi] no se pudo abrir el selector de código telefónico")
            return False
        await delay(0.8, 1.2)
        picked = False
        try:
            picked = await page.evaluate(
                """
                (target) => {
                    const nodes = Array.from(document.querySelectorAll('li, button, div, span'));
                    for (const node of nodes) {
                        const text = (node.innerText || node.textContent || '').trim();
                        if (!text) continue;
                        if (text.startsWith(target)) {
                            node.click();
                            return true;
                        }
                    }
                    return false;
                }
                """,
                target,
            )
        except Exception:
            picked = False
        if picked:
            log.info(f"  [DiDi] código telefónico seleccionado: {target}")
        else:
            log.warning(f"  [DiDi] no se encontró el código {target}")
        return picked

    async def _is_terms_checked(self, page: Page) -> bool:
        try:
            return await page.evaluate(
                """
                (keywords) => {
                    const norm = (s = '') => s.normalize('NFD').replace(/\u0300-\u036f/g, '').toLowerCase();
                    const matches = (text = '') => {
                        const normalized = norm(text);
                        return keywords.some(k => normalized.includes(norm(k)));
                    };

                    const nodes = Array.from(document.querySelectorAll('input[type="checkbox"], [role="checkbox"]'));
                    for (const node of nodes) {
                        const label = node.closest('label');
                        const context = [node.getAttribute('aria-label') || '', label?.innerText || '', node.parentElement?.innerText || ''].join(' ');
                        if (!matches(context)) continue;
                        const isChecked = node.matches('[role="checkbox"]')
                            ? (node.getAttribute('aria-checked') === 'true')
                            : !!node.checked;
                        if (isChecked) return true;
                    }

                    const toggles = Array.from(document.querySelectorAll('[aria-checked]'));
                    for (const toggle of toggles) {
                        const context = [toggle.innerText || '', toggle.parentElement?.innerText || ''].join(' ');
                        if (!matches(context)) continue;
                        if (toggle.getAttribute('aria-checked') === 'true') return true;
                    }
                    return false;
                }
                """,
                self.TERMS_KEYWORDS + ["Acepto"],
            )
        except Exception:
            return False

    async def _click_terms_circle(self, page: Page) -> bool:
        """Find and tap the circular terms checkbox on DiDi mobile login.
        Looks for a small clickable element (the circle) near the terms text,
        or taps just to the left of the terms text as fallback."""
        try:
            coords = await page.evaluate(
                """
                (keywords) => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                    const matches = (text = '') => keywords.some(k => norm(text).includes(norm(k)));

                    // Find the terms text container
                    const allEls = Array.from(document.querySelectorAll('label, div, span, p, a'));
                    let termsEl = null;
                    let termsRect = null;
                    for (const el of allEls) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (!matches(text)) continue;
                        const rect = el.getBoundingClientRect();
                        if (!rect || rect.width === 0 || rect.height === 0) continue;
                        // Prefer smaller/more specific elements
                        if (!termsEl || rect.width < termsRect.width) {
                            termsEl = el;
                            termsRect = rect;
                        }
                    }
                    if (!termsEl) return null;

                    // Strategy 1: Look for a small square/circular element (10-40px)
                    // in the same row as the terms text (the checkbox circle)
                    const searchIn = [
                        ...Array.from(termsEl.parentElement?.children || []),
                        ...Array.from(termsEl.parentElement?.parentElement?.children || []),
                        ...Array.from(termsEl.querySelectorAll('*')),
                        ...Array.from(termsEl.parentElement?.querySelectorAll('*') || []),
                    ];
                    const seen = new Set();
                    for (const el of searchIn) {
                        if (seen.has(el) || el === termsEl) continue;
                        seen.add(el);
                        const rect = el.getBoundingClientRect();
                        if (!rect || rect.width === 0 || rect.height === 0) continue;
                        const isSmallSquare = rect.width >= 10 && rect.width <= 40
                                           && rect.height >= 10 && rect.height <= 40;
                        if (!isSmallSquare) continue;
                        // Must be vertically aligned with terms text
                        const vCenter = rect.top + rect.height / 2;
                        const tVCenter = termsRect.top + termsRect.height / 2;
                        if (Math.abs(vCenter - tVCenter) < 25) {
                            return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
                        }
                    }

                    // Strategy 2: Click just to the left of the terms text (where circle usually is)
                    if (termsRect.left > 20) {
                        return { x: termsRect.left - 15, y: termsRect.top + termsRect.height / 2 };
                    }

                    // Strategy 3: Click the terms text element itself (some UIs toggle on text tap)
                    return { x: termsRect.left + 10, y: termsRect.top + termsRect.height / 2 };
                }
                """,
                self.TERMS_KEYWORDS + ["Acepto"],
            )
        except Exception:
            coords = None

        if coords:
            # Use touchscreen tap for mobile emulation (DiDi requires mobile)
            try:
                await page.touchscreen.tap(coords["x"], coords["y"])
                log.info(f"  [DiDi] tapped terms circle at ({coords['x']:.0f}, {coords['y']:.0f})")
                return True
            except Exception:
                pass
            # Fallback to mouse click
            try:
                await page.mouse.click(coords["x"], coords["y"])
                return True
            except Exception:
                return False
        return False

    async def _accept_terms(self, page: Page) -> bool:
        if await self._is_terms_checked(page):
            return True

        # Strategy 1: Standard checkbox selectors with tap (mobile)
        checkbox_sels = ['input[type="checkbox"]', '[role="checkbox"]']
        for sel in checkbox_sels:
            try:
                box = page.locator(sel).first
                if await box.count() == 0:
                    continue
                try:
                    await box.tap()
                    await delay(0.3, 0.5)
                    if await self._is_terms_checked(page):
                        log.info("  [DiDi] checkbox de términos marcado (tap)")
                        return True
                except Exception:
                    pass
                try:
                    await box.check(force=True)
                    await delay(0.2, 0.4)
                    if await self._is_terms_checked(page):
                        log.info("  [DiDi] checkbox de términos marcado (Playwright check)")
                        return True
                except Exception:
                    pass
                try:
                    await box.click(force=True)
                    await delay(0.2, 0.4)
                    if await self._is_terms_checked(page):
                        log.info("  [DiDi] checkbox de términos marcado (click force)")
                        return True
                except Exception:
                    continue
            except Exception:
                continue

        # Strategy 2: Find and tap the circular element near terms text
        for attempt in range(3):
            if await self._click_terms_circle(page):
                await delay(0.4, 0.6)
                if await self._is_terms_checked(page):
                    log.info("  [DiDi] términos aceptados con tap al círculo")
                    return True
            await asyncio.sleep(0.3)

        # Strategy 3: Tap any element with terms text (some UIs toggle on text tap)
        terms_locators = [
            page.locator('text=/[Aa]cepto/'),
            page.locator('text=/[Tt][eé]rminos/'),
            page.locator('label:has-text("Acepto")'),
            page.locator('span:has-text("Acepto")'),
        ]
        for loc in terms_locators:
            try:
                if await loc.count() > 0:
                    await loc.first.tap()
                    await delay(0.3, 0.5)
                    if await self._is_terms_checked(page):
                        log.info("  [DiDi] términos aceptados via tap en texto")
                        return True
            except Exception:
                continue

        # Strategy 4: JS keyword click (last resort)
        if await self._click_by_keywords(page, self.TERMS_KEYWORDS + ["Acepto"]):
            await delay(0.2, 0.4)
            if await self._is_terms_checked(page):
                log.info("  [DiDi] términos aceptados via keyword click")
                return True

        # Even if we can't confirm it's checked, try proceeding —
        # the Siguiente button might work anyway
        log.warning("  [DiDi] no se pudo confirmar checkbox de términos")
        return False

    async def _trigger_login_flow(self, page: Page):
        for attempt in range(3):
            for sel in self.LOGIN_TRIGGER_SELS:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.click()
                        log.info(f"  [DiDi] clicked login trigger: {sel}")
                        await delay(1, 2)
                        return True
                except Exception:
                    continue
            await asyncio.sleep(0.5)
        return False

    async def _address_form_visible(self, page: Page) -> bool:
        """Detect if the central address form is already open/visible."""
        for sel in self.ADDRESS_INPUTS:
            try:
                loc = page.locator(sel).first
                if await loc.count() == 0:
                    continue
                try:
                    await loc.wait_for(state="visible", timeout=1000)
                except Exception:
                    pass
                try:
                    if await loc.is_disabled():
                        continue
                except Exception:
                    pass
                log.info(f"  [DiDi] address input already visible via {sel}")
                return True
            except Exception:
                continue

        try:
            central = page.locator('text=/Ingresa tu direcci[oó]n/i').first
            if await central.count() > 0 and await central.is_visible():
                log.info("  [DiDi] central address prompt detected")
                return True
        except Exception:
            pass

        try:
            popup_pattern = re.compile(r"selecciona una direcci[oó]n", re.IGNORECASE)
            popup_selectors = [
                page.locator('[role="dialog"]').filter(has_text=popup_pattern),
                page.locator('h5-dialog').filter(has_text=popup_pattern),
                page.locator('.h5-dialog_content').filter(has_text=popup_pattern),
            ]
            for popup in popup_selectors:
                popup = popup.first
                if await popup.count() > 0:
                    log.info("  [DiDi] 'Selecciona una dirección' popup visible")
                    return True
        except Exception:
            pass
        return False

    async def _open_address_modal(self, page: Page, addr: Optional[dict] = None) -> bool:
        try:
            await page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass
        if await self._address_form_visible(page):
            return True
        for sel in self.ADDRESS_HEADER_SELS:
            try:
                el = page.locator(sel).first
                if await el.count() == 0:
                    continue
                await el.click(force=True)
                await delay(0.5, 0.8)
                if await self._address_form_visible(page):
                    return True
            except Exception:
                continue
        dynamic_keywords = list(self.ADDRESS_TRIGGER_KEYWORDS)
        if addr:
            for token in (addr.get("zone"), addr.get("city")):
                if token:
                    dynamic_keywords.append(token)
        if await self._click_by_keywords(page, dynamic_keywords):
            await delay(0.5, 0.8)
            if await self._address_form_visible(page):
                return True
        # JS fallback: find any header element near the top that contains a location chip text
        try:
            tokens = [t.lower() for t in dynamic_keywords if isinstance(t, str)]
            opened = await page.evaluate(
                """
                (keywords) => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
                    const toks = keywords.filter(Boolean).map(norm);
                    const candidates = Array.from(document.querySelectorAll('header *, [role="banner"] *, button, div, span'));
                    for (const el of candidates) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const rect = el.getBoundingClientRect();
                        if (!rect || rect.top > 220) continue; // only near top bar
                        const text = norm(el.innerText || el.textContent || '');
                        if (!text) continue;
                        if (toks.some(t => text.includes(t))) {
                            el.click();
                            return true;
                        }
                        if (text.includes('direccion') || text.includes('dirección') || text.includes('ubicacion') || text.includes('ubicación')) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }
                """,
                tokens,
            )
            if opened:
                await delay(0.5, 0.8)
                if await self._address_form_visible(page):
                    return True
        except Exception:
            pass
        return False

    async def _click_keyword_store(self, page: Page) -> bool:
        """Fallback: find any McDonald's element and click it via JS to bypass sticky headers."""
        try:
            clicked = await page.evaluate("""
                () => {
                    const norm = (s = '') => s
                        .normalize('NFD')
                        .replace(/[\\u0300-\\u036f]/g, '')
                        .toLowerCase()
                        .replace(/[^a-z0-9]+/g, '');
                    const blacklist = ['uber', 'rappi', 'menu', 'inicio', 'sesion', 'login'];
                    const candidates = Array.from(document.querySelectorAll('a, div, span, [role="link"], [role="button"]'));
                    for (const el of candidates) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const text = norm(el.innerText || el.textContent || '');
                        if (!text.includes('mcdonald')) continue;
                        if (blacklist.some(b => text.includes(b))) continue;
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 40 || rect.height < 20) continue;
                        el.scrollIntoView({behavior: 'auto', block: 'center'});
                        el.click();
                        return true;
                    }
                    return false;
                }
            """)
            if clicked:
                await delay(3, 4)
                return True
        except Exception:
            pass
        return False

    async def _focus_address_input(self, page: Page) -> bool:
        popup_text = re.compile(r"(selecciona una direcci[oó]n|ingresa tu direcci[oó]n|direccion de entrega)", re.IGNORECASE)
        popup_candidates = [
            page.locator('[role="dialog"]').filter(has_text=popup_text),
            page.locator('h5-dialog').filter(has_text=popup_text),
            page.locator('.h5-dialog_content').filter(has_text=popup_text),
        ]
        modal_input_selectors = [
            'input[placeholder*="direcci" i]',
            'input[placeholder*="entrega" i]',
            'input[placeholder*="domicilio" i]',
            'input[type="search"]',
            'textarea[placeholder*="direcci" i]',
            '[contenteditable="true"]',
        ]
        for modal in popup_candidates:
            modal = modal.first
            try:
                if await modal.count() == 0:
                    continue
                try:
                    await modal.wait_for(state="visible", timeout=1500)
                except Exception:
                    pass
                try:
                    trigger = modal.locator('button, [role="button"]').filter(
                        has_text=re.compile(r"buscar direcci[oó]n", re.IGNORECASE)
                    ).first
                    if await trigger.count() > 0:
                        await trigger.click()
                        await asyncio.sleep(0.3)
                        log.info("  [DiDi] clicked 'Buscar dirección' inside popup")
                except Exception:
                    pass
                for inner_sel in modal_input_selectors:
                    try:
                        inner = modal.locator(inner_sel).first
                        if await inner.count() == 0:
                            continue
                        try:
                            await inner.wait_for(state="visible", timeout=1200)
                        except Exception:
                            pass
                        try:
                            await inner.tap()
                        except Exception:
                            try:
                                await inner.click(force=True)
                            except Exception:
                                continue
                        await asyncio.sleep(0.2)
                        log.info("  [DiDi] address input focused inside popup container")
                        return True
                    except Exception:
                        continue
            except Exception:
                continue

        selectors = list(self.ADDRESS_INPUTS) + ['input[placeholder*="entrega" i]']
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() == 0:
                    continue
                try:
                    await el.wait_for(state="visible", timeout=1200)
                except Exception:
                    pass
                try:
                    await el.tap()
                except Exception:
                    try:
                        await el.click(force=True)
                    except Exception:
                        continue
                await asyncio.sleep(0.2)
                log.info(f"  [DiDi] address input focused via {sel}")
                return True
            except Exception:
                continue
        try:
            tapped = await page.evaluate(
                """
                () => {
                    const nodes = Array.from(document.querySelectorAll('div, span, button'));
                    for (const el of nodes) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const text = (el.innerText || el.textContent || '').toLowerCase();
                        if (text.includes('ingresar direccion') || text.includes('ingresa tu direccion')
                            || text.includes('direccion de entrega') || text.includes('buscar direccion')) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }
                """
            )
            if tapped:
                await asyncio.sleep(0.2)
                log.info("  [DiDi] tapped placeholder text to focus address input")
                return True
        except Exception:
            pass
        return False

    async def _fill_address_input_js(self, page: Page, address: str) -> bool:
        try:
            filled = await page.evaluate(
                """
                (value) => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
                    const inputs = Array.from(document.querySelectorAll('input, textarea, [contenteditable="true"]'));
                    for (const el of inputs) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const hint = norm(el.placeholder || '') + ' ' + norm(el.getAttribute('aria-label') || '') + ' ' + norm(el.className || '');
                        if (!(hint.includes('direccion') || hint.includes('entrega') || hint.includes('domicilio'))) continue;
                        if (el.matches('[contenteditable="true"]')) {
                            el.innerText = value;
                        } else {
                            el.value = value;
                        }
                        for (const evt of ['input','change','keyup']) {
                            el.dispatchEvent(new Event(evt, { bubbles: true }));
                        }
                        el.focus();
                        return true;
                    }
                    return false;
                }
                """,
                address,
            )
            if filled:
                await asyncio.sleep(0.3)
                log.info("  [DiDi] address input populated via JS fallback")
                return True
        except Exception:
            pass
        return False

    async def _set_address(self, page: Page, addr: dict, force_modal: bool = False) -> bool:
        target = addr.get("address")
        if not target:
            return False
        # Cuando se fuerza, abrimos el modal sí o sí para asegurar el cambio explícito.
        if not force_modal:
            if await self._wait_for_address_confirmation(page, addr):
                log.info("  [DiDi] dirección del entry-point ya activa")
                return True
        else:
            log.info("  [DiDi] forzando reapertura del modal de dirección")
        for attempt in range(4):
            opened = await self._open_address_modal(page, addr)
            if not opened:
                await delay(0.8, 1.0)
                continue
            await self._focus_address_input(page)
            typed = await find_and_fill_input(page, self.ADDRESS_INPUTS, target, use_keyboard=True)
            if not typed:
                typed = await self._fill_address_input_js(page, target)
            if not typed:
                typed = await self._insert_text_with_keyboard(page, target, context_label="address input")
            if not typed:
                await self._handle_login_and_persist(page)
                await delay(0.8, 1.2)
                continue
            await delay(1.5, 2)
            await click_first_suggestion(page)
            await delay(2, 3)
            if await self._wait_for_address_confirmation(page, addr):
                log.info("  [DiDi] dirección confirmada en el header")
                return True
            log.warning("  [DiDi] la dirección no apareció en el header, reintentamos")
        return False

    async def _set_search_value_via_js(self, page: Page, query: str) -> bool:
        try:
            return await page.evaluate(
                """
                (value) => {
                    const norm = (s = '') => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
                    const candidates = Array.from(document.querySelectorAll('input, textarea, [contenteditable="true"]'));
                    for (const el of candidates) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const ph = norm(el.placeholder || '');
                        const aria = norm(el.getAttribute('aria-label') || '');
                        const role = norm(el.getAttribute('role') || '');
                        const cls = norm(el.className || '');
                        const name = norm(el.getAttribute('name') || '');
                        const id = norm(el.id || '');
                        const looksSearch = ph.includes('buscar') || ph.includes('restaurante') || ph.includes('comida')
                            || aria.includes('buscar') || aria.includes('search') || role.includes('search')
                            || cls.includes('search') || name.includes('search') || id.includes('search');
                        if (!looksSearch) continue;
                        if (el.matches('[contenteditable="true"]')) {
                            el.innerText = value;
                        } else {
                            el.value = value;
                        }
                        const events = ['input','change','keyup'];
                        for (const evt of events) {
                            el.dispatchEvent(new Event(evt, { bubbles: true }));
                        }
                        el.focus();
                        try { el.setSelectionRange(value.length, value.length); } catch (err) {}
                        return true;
                    }
                    return false;
                }
                """,
                query,
            )
        except Exception:
            return False

    async def _insert_text_with_keyboard(self, page: Page, text: str, context_label: str = "input") -> bool:
        try:
            await page.keyboard.insert_text(text)
            await asyncio.sleep(0.3)
            log.info(f"  [DiDi] keyboard insert_text fallback used for {context_label}")
            return True
        except Exception:
            return False

    async def _open_search_results_direct(self, page: Page, query: str, addr: Optional[dict] = None) -> bool:
        raw_query = (query or "").strip()
        if not raw_query:
            return False
        slug = quote_plus(raw_query)

        try:
            current_url = page.url or ""
        except Exception:
            current_url = ""

        sources = [current_url] + self.ENTRY_URLS
        candidates: list[str] = []

        for src in sources:
            if not src:
                continue
            try:
                parsed = urlparse(src)
            except ValueError:
                continue
            if not parsed.scheme or not parsed.netloc:
                continue

            # Preserve existing query params (pl carries full address context)
            query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
            query_dict: dict[str, list[str]] = {}
            for key, value in query_pairs:
                query_dict.setdefault(key, []).append(value)
            query_dict.pop("keyword", None)
            query_dict.pop("searchId", None)
            query_dict["keyword"] = [raw_query]

            path = parsed.path or ""
            if "/food/feed" in path:
                path = path.replace("/food/feed", "/food/search")
            elif "/food/search" not in path:
                path = "/food/search/"

            new_query = urlencode(query_dict, doseq=True)
            candidate = urlunparse(parsed._replace(path=path, query=new_query, params=""))
            candidates.append(candidate)

        base = self._DEFAULT_DIDI_HOME.rstrip("/")
        fallback_urls = [
            f"{base}/food/search/?keyword={slug}",
            f"{base}/food/search/?keyword={slug}&from=home",
            f"{base}/food/search/{slug}",
        ]
        candidates.extend(fallback_urls)

        ordered = []
        seen = set()
        for url in candidates:
            if not url or url in seen:
                continue
            seen.add(url)
            ordered.append(url)

        for url in ordered:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await delay(1.2, 2.2)
                current = (page.url or "").lower()
                if "search" not in current:
                    continue
                if addr:
                    await self._wait_for_address_confirmation(page, addr)
                log.info(f"  [DiDi] opened search results directly via {url}")
                return True
            except Exception as exc:
                log.warning(f"  [DiDi] direct search URL failed {url}: {exc}")
                continue
        return False

    async def _type_search_query(self, page: Page, query: str) -> tuple[bool, bool]:
        focused = await self._focus_search_input(page)
        typed = await find_and_fill_input(page, self.SEARCH_INPUTS, query, use_keyboard=True)
        if not typed:
            typed = await self._set_search_value_via_js(page, query)
        if not typed and focused:
            typed = await self._insert_text_with_keyboard(page, query, context_label="search")

        if typed:
            log.info("  [DiDi] query 'McDonalds' escrita en el buscador")
            return True, True

        chip_clicked = await self._click_by_keywords(page, self.SEARCH_CHIP_KEYWORDS)
        if chip_clicked:
            log.info("  [DiDi] usando chip de búsquedas populares para McDonald's")
            await delay(1, 2)
            return True, False

        log.warning("  [DiDi] no se pudo interactuar con el buscador de DiDi")
        return False, False

    async def _wait_for_search_results(self, page: Page, timeout_ms: int = 8000) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + (timeout_ms / 1000)
        selectors = [
            '.shop-item',
            '[data-testid*="shop" i]',
            'a[href*="/store"]',
            'div:has-text("McDonald")',
            'div:has-text("No encontramos")',
        ]
        while loop.time() < deadline:
            for sel in selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0:
                        return
                except Exception:
                    continue
            await asyncio.sleep(0.4)

    async def _dump_search_debug(self, page: Page, addr: Optional[dict], stage: str) -> None:
        try:
            debug_dir = Path("logs/didi_debug")
            debug_dir.mkdir(parents=True, exist_ok=True)
            addr_id = (addr or {}).get("id", "addr")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = debug_dir / f"{addr_id}_{stage}_{ts}.html"
            html_path.write_text(await page.content(), encoding="utf-8")
            png_path = debug_dir / f"{addr_id}_{stage}_{ts}.png"
            await page.screenshot(path=str(png_path), full_page=True)
            log.info(f"  [DiDi] search debug dump guardado: {html_path.name}")
        except Exception as exc:
            log.warning(f"  [DiDi] no se pudo guardar debug search: {exc}")

    async def _open_store_from_current_results(self, page: Page, r: PlatformResult) -> bool:
        # Find McDonald's card and open it — use JS click to bypass sticky header
        for attempt in range(4):
            try:
                result = await page.evaluate("""
                    () => {
                        const norm = (s = '') => s
                            .normalize('NFD')
                            .replace(/[\\u0300-\\u036f]/g, '')
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, '');
                        // Look for shop-item cards or links containing McDonald
                        const candidates = Array.from(document.querySelectorAll(
                            '.shop-item, a[href*="store"], a[href*="restaurant"], [data-id], div[class*="card"]'
                        ));
                        // Also check all anchors and divs
                        candidates.push(...Array.from(document.querySelectorAll('a, div')));
                        const seen = new Set();
                        for (const el of candidates) {
                            if (seen.has(el)) continue;
                            seen.add(el);
                            if (!el.isConnected || el.offsetParent === null) continue;
                            const text = norm(el.innerText || el.textContent || '');
                            if (!text.includes('mcdonald')) continue;
                            // Skip if it's a tiny element (just text node) — we want the card container
                            const rect = el.getBoundingClientRect();
                            if (rect.width < 50 || rect.height < 30) continue;
                            const token = `ci-mc-${Date.now()}-${Math.random().toString(16).slice(2)}`;
                            el.setAttribute('data-ci-mc-card', token);
                            // Check for href first (best way to navigate)
                            const href = el.getAttribute('href') || el.querySelector('a')?.getAttribute('href') || '';
                            // Extract card info
                            return {
                                text: (el.innerText || '').substring(0, 200),
                                href: href,
                                x: rect.left + rect.width / 2,
                                y: rect.top + rect.height / 2,
                                token,
                            };
                        }
                        return null;
                    }
                """)
                if result:
                    card_text = result.get("text", "")
                    log.info(f"  [DiDi] found McDonald's card: {card_text[:80]}")

                    # Extract info from card
                    r.restaurant_name = card_text[:60]
                    r.rating = r.rating or extract_rating(card_text)
                    r.eta_min = r.eta_min or extract_eta(card_text)
                    r.delivery_fee = r.delivery_fee or extract_delivery_fee(card_text)
                    r.review_count = r.review_count or extract_review_count(card_text)
                    if not r.promo_general_pct:
                        r.promo_general_pct = extract_promo(card_text)

                    href = result.get("href", "")
                    if href:
                        # Navigate directly via href — most reliable
                        if href.startswith("http"):
                            await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                        else:
                            base = page.url.split("/food/")[0] if "/food/" in page.url else "https://www.didi-food.com"
                            await page.goto(f"{base}{href}", wait_until="domcontentloaded", timeout=30000)
                        await delay(3, 4)
                        return True
                    else:
                        # No href — first try clicking the tagged card directly to bypass sticky headers
                        token = result.get("token")
                        clicked = False
                        if token:
                            try:
                                clicked = await page.evaluate(
                                    """
                                    (token) => {
                                        const sel = `[data-ci-mc-card="${token}"]`;
                                        const el = document.querySelector(sel);
                                        if (el) {
                                            el.scrollIntoView({behavior: 'auto', block: 'center'});
                                            el.click();
                                            return true;
                                        }
                                        return false;
                                    }
                                    """,
                                    token,
                                )
                            except Exception:
                                clicked = False
                        if not clicked:
                            # Fall back to clicking by screen coordinates (with sticky header risk)
                            clicked = await page.evaluate("""
                                (coords) => {
                                    const el = document.elementFromPoint(coords.x, coords.y);
                                    if (el) {
                                        let target = el;
                                        for (let i = 0; i < 5; i++) {
                                            if (target.tagName === 'A' || target.onclick || target.getAttribute('data-id')) {
                                                target.click();
                                                return true;
                                            }
                                            target = target.parentElement;
                                            if (!target) break;
                                        }
                                        el.click();
                                        return true;
                                    }
                                    return false;
                                }
                            """, {"x": result["x"], "y": result["y"]})
                        if clicked:
                            await delay(3, 4)
                            return True
            except Exception as e:
                log.warning(f"  [DiDi] store search attempt {attempt+1} failed: {e}")

            await delay(1, 2)

        # Fallback: click any McDonald's element via JS
        if await self._click_keyword_store(page):
            return True
        return False

    async def _search_and_open_store(self, page: Page, r: PlatformResult, addr: Optional[dict] = None) -> bool:
        success, needs_enter = await self._type_search_query(page, "McDonalds")
        if success:
            if needs_enter:
                try:
                    await page.keyboard.press("Enter")
                except Exception:
                    pass
                await delay(3, 5)

            await self._wait_for_search_results(page)
            # Capture search results text for promo hook ("Hasta X% dto.")
            try:
                search_text = await page.evaluate("() => document.body.innerText")
                promo_m = re.search(r'[Hh]asta\s+(\d+)\s*%\s*(?:dto|desc)', search_text)
                if promo_m:
                    r.promo_general_pct = float(promo_m.group(1))
                    log.info(f"  [DiDi] promo from search: {r.promo_general_pct}%")
            except Exception:
                pass

            if await self._open_store_from_current_results(page, r):
                return True

            log.warning("  [DiDi] búsqueda manual no arrojó tarjetas de McDonald's")
            await self._dump_search_debug(page, addr, "search_ui")

        # Manual search failed or couldn't type — try direct search URL
        if await self._open_search_results_direct(page, "McDonalds", addr):
            await self._wait_for_search_results(page)
            if await self._open_store_from_current_results(page, r):
                return True
            log.warning("  [DiDi] búsqueda directa tampoco encontró McDonald's")
            await self._dump_search_debug(page, addr, "search_direct")
        else:
            log.warning("  [DiDi] no se pudo abrir la búsqueda directa de McDonald's")

        return False

    async def _click_category_tabs_and_collect(self, page: Page) -> str:
        """Click through category tabs on DiDi restaurant page to load all products.
        DiDi organizes products in tabs (Mc para Todos, A la Carta Comida, Bebidas, etc.)
        Each tab lazy-loads its content, so we need to click each one and collect text."""

        all_text_parts = []

        # First, collect the header area (rating, ETA, delivery, review count)
        try:
            header_text = await page.evaluate("() => document.body.innerText")
            all_text_parts.append(header_text)
        except Exception:
            pass

        # Find category tabs — they are usually horizontal scrollable buttons/tabs
        tab_targets = []

        try:
            tab_info = await page.evaluate("""
                () => {
                    const candidates = Array.from(document.querySelectorAll(
                        '[role="tab"], [data-testid*="tab" i], button, [class*="tab" i], [class*="category" i] > *'
                    ));
                    const tabs = [];
                    for (const el of candidates) {
                        if (!el.isConnected || el.offsetParent === null) continue;
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 40 || rect.height < 20 || rect.height > 90) continue;
                        const text = (el.innerText || el.textContent || '').trim();
                        if (!text || text.length > 40) continue;
                        tabs.push({text: text, x: rect.left + rect.width/2, y: rect.top + rect.height/2});
                    }
                    const seen = new Set();
                    return tabs.filter(t => {
                        if (seen.has(t.text)) return false;
                        seen.add(t.text);
                        return true;
                    });
                }
            """)
            if tab_info:
                filtered = []
                skip = {"agregar","añadir","add"}
                for tab in tab_info:
                    label = (tab.get("text") or "").strip()
                    if not label:
                        continue
                    lower = label.lower()
                    if lower in skip or lower.startswith("mx$"):
                        continue
                    filtered.append(tab)
                if filtered:
                    log.info(f"  [DiDi] found {len(filtered)} category tabs: {[t['text'] for t in filtered]}")
                    tab_targets = [{"mode": "coords", "text": t["text"], "x": t["x"], "y": t["y"]} for t in filtered]
        except Exception as e:
            log.warning(f"  [DiDi] tab detection failed: {e}")

        if not tab_targets:
            log.info("  [DiDi] no tabs detected, using fallback keywords")
            tab_targets = [{"mode": "keyword", "text": kw} for kw in self.CATEGORY_FALLBACKS]

        collected_any = False
        seen_labels = set()

        for tab in tab_targets:
            label = (tab.get("text") or "").strip()
            if not label or label in seen_labels:
                continue
            clicked = False
            if tab["mode"] == "coords":
                try:
                    try:
                        await page.touchscreen.tap(tab["x"], tab["y"])
                    except Exception:
                        await page.mouse.click(tab["x"], tab["y"])
                    clicked = True
                except Exception as e:
                    log.warning(f"  [DiDi] failed to click tab '{label}': {e}")
            else:
                clicked = await self._click_by_keywords(page, [label])
            if not clicked:
                continue
            seen_labels.add(label)
            collected_any = True
            await asyncio.sleep(1.5)
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
                await asyncio.sleep(0.5)
            try:
                tab_text = await page.evaluate("() => document.body.innerText")
                all_text_parts.append(tab_text)
                log.info(f"  [DiDi] collected text from tab '{label}' ({len(tab_text)} chars)")
            except Exception as e:
                log.warning(f"  [DiDi] failed to read tab '{label}': {e}")
            try:
                await page.evaluate("window.scrollTo(0, 0)")
            except Exception:
                pass
            await asyncio.sleep(0.3)

        if not collected_any:
            log.info("  [DiDi] no category clicks succeeded, scrolling full page")
            return await scroll_and_collect_text(page, pause=0.7, max_scrolls=30)

        return "\n".join(all_text_parts)

    async def _add_products_to_cart(self, page: Page, products: list) -> float | None:
        """After finding products, add them to cart and tap 'Ver carrito'
        to capture the real subtotal from DiDi's cart view."""
        if not products:
            return None

        # Scroll back to top to find product cards
        try:
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
        except Exception:
            pass

        added = 0
        for prod in products:
            prod_name_lower = prod.name.lower()
            # Find "Agregar" or "+" button near the product
            try:
                btn_coords = await page.evaluate("""
                    (prodName) => {
                        const norm = (s = '') => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                        const target = norm(prodName);
                        const els = Array.from(document.querySelectorAll('div, span, h3, h4, p'));
                        for (const el of els) {
                            if (!el.isConnected || el.offsetParent === null) continue;
                            const text = norm(el.innerText || el.textContent || '');
                            if (!text.includes(target)) continue;
                            let container = el.parentElement;
                            for (let i = 0; i < 5 && container; i++) {
                                const btns = container.querySelectorAll('button, [role="button"], div[class*="add" i], span[class*="add" i]');
                                for (const btn of btns) {
                                    const btnText = norm(btn.innerText || btn.textContent || '');
                                    if (btnText.includes('agregar') || btnText === '+' || btnText.includes('anadir')
                                        || btnText.includes('añadir')) {
                                        const rect = btn.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0) {
                                            return { x: rect.left + rect.width/2, y: rect.top + rect.height/2 };
                                        }
                                    }
                                }
                                container = container.parentElement;
                            }
                            break;
                        }
                        return null;
                    }
                """, prod_name_lower)
                if btn_coords:
                    try:
                        await page.touchscreen.tap(btn_coords["x"], btn_coords["y"])
                    except Exception:
                        await page.mouse.click(btn_coords["x"], btn_coords["y"])
                    added += 1
                    log.info(f"  [DiDi] added to cart: {prod.name}")
                    await asyncio.sleep(1)
            except Exception:
                continue

        if added == 0:
            log.info("  [DiDi] no products added to cart — skipping cart view")
            return None

        await asyncio.sleep(1)

        # Tap "Ver carrito" button at bottom
        cart_keywords = ["ver carrito", "ver pedido", "ir al carrito"]
        cart_tapped = False
        for kw in cart_keywords:
            try:
                loc = page.locator(f'text=/{kw}/i').first
                if await loc.count() > 0:
                    try:
                        await loc.tap()
                    except Exception:
                        await loc.click(force=True)
                    cart_tapped = True
                    log.info(f"  [DiDi] tapped '{kw}'")
                    break
            except Exception:
                continue

        if not cart_tapped:
            cart_tapped = await self._click_by_keywords(page, cart_keywords)

        if not cart_tapped:
            log.info("  [DiDi] no 'Ver carrito' button found")
            return None

        await asyncio.sleep(2)

        # Extract subtotal from cart view
        try:
            cart_text = await page.evaluate("() => document.body.innerText")
            subtotal_m = re.search(r'[Ss]ubtotal\s*\$?\s*([\d,]+(?:\.\d{1,2})?)', cart_text)
            if subtotal_m:
                val = float(subtotal_m.group(1).replace(",", ""))
                log.info(f"  [DiDi] cart subtotal: ${val}")
                return val
            total_m = re.search(r'[Tt]otal\s*\$?\s*([\d,]+(?:\.\d{1,2})?)', cart_text)
            if total_m:
                val = float(total_m.group(1).replace(",", ""))
                log.info(f"  [DiDi] cart total: ${val}")
                return val
        except Exception:
            pass

        return None

    async def scrape(self, page: Page, addr: dict, sdir: Path, take_shots: bool) -> PlatformResult:
        """DiDi Food scraping flow:
        1. Load entry URL (with address pre-encoded in pl= param)
        2. Login: phone + terms + Siguiente
        3. WAIT for user to enter OTP code manually (SMS verification)
        4. After OTP: user lands on restaurant feed
        5. Set address in top bar (if not already set by URL)
        6. Tap search icon → search for McDonald's
        7. From search results: capture promo hook, rating, review count
        8. Click on McDonald's restaurant
        9. Inside restaurant: capture ETA, delivery fee, prices via tab navigation
        10. Add products to cart → tap 'Ver carrito' → capture subtotal
        """
        r = PlatformResult(platform=self.PLATFORM)
        try:
            # ── 1. Load entry URL ──
            loaded = False
            for url in self.ENTRY_URLS:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await delay(2, 3)
                    loaded = True
                    log.info(f"  [DiDi] loaded: {url}")
                    break
                except Exception as e:
                    log.warning(f"  [DiDi] failed to load {url}: {e}")
                    continue

            if not loaded:
                r.status = "error"
                r.error_detail = "No fue posible abrir DiDi Food"
                return r

            # ── 2. Login (phone + terms + Siguiente + manual OTP) ──
            try:
                page = await self._ensure_logged_in(page)
            except RuntimeError as otp_err:
                r.status = "error"
                r.error_detail = str(otp_err)
                log.warning(f"  [DiDi] {otp_err}")
                return r

            # ── 3. After login, navigate to feed with address ──
            try:
                await page.goto(self.ENTRY_URLS[0], wait_until="domcontentloaded", timeout=25000)
                await delay(2, 3)
            except Exception as e:
                log.warning(f"  [DiDi] failed to reload entry after login: {e}")

            # Handle any remaining popups/overlays
            if await self._click_by_keywords(page, self.ENTER_KEYWORDS):
                log.info("  [DiDi] clicked enter/landing button")
                await delay(2, 3)

            try:
                ctx_pages = page.context.pages
                if ctx_pages and ctx_pages[-1] is not page:
                    page = ctx_pages[-1]
                    await page.wait_for_load_state("domcontentloaded")
                    log.info("  [DiDi] switched to popup landing page")
            except Exception:
                pass

            try:
                log.info(f"  [DiDi] url after landing: {page.url}")
            except Exception:
                pass

            # Try setting address — but the entry URL already has it encoded
            # in the pl= param, so if we can't confirm it via UI that's OK.
            # Do NOT abort here — just log and continue to search.
            addr_set = await self._set_address(page, addr, force_modal=True)
            if not addr_set:
                r.status = "error"
                r.error_detail = "No se pudo cambiar la dirección en DiDi"
                log.warning("  [DiDi] no se pudo confirmar la dirección — abortamos")
                return r

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "feed", sdir)

            # ── 4. Search for McDonald's in the search bar ──
            # Do NOT scroll the feed — go straight to search
            if not await self._search_and_open_store(page, r, addr):
                r.status = "partial_no_store"
                log.warning("  [DiDi] no McDonalds store found")
                return r

            r.restaurant_available = True
            if not r.restaurant_name.strip():
                try:
                    heading = await page.locator("h1").first.inner_text(timeout=3000)
                    if heading:
                        r.restaurant_name = heading.strip()[:60]
                except Exception:
                    try:
                        title_text = await page.title()
                        if title_text:
                            r.restaurant_name = title_text.split("|")[0].strip()[:60]
                    except Exception:
                        pass
            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "store", sdir)

            await delay(2, 3)

            # DiDi organizes products in category tabs — click through each
            # to load all products before extracting text
            full_text = await self._click_category_tabs_and_collect(page)

            try:
                dump_path = sdir / f"{addr['id']}_didifood_text_dump.txt"
                dump_path.write_text(full_text, encoding="utf-8")
            except Exception:
                pass

            ft_lower = full_text.lower()
            for kw in ["home office", "big mac", "hamburguesa doble", "coca-cola", "coca cola"]:
                log.info(f"  [DiDi] keyword '{kw}' found: {kw in ft_lower}")

            r.products = extract_products_from_text(full_text)
            r.delivery_fee = r.delivery_fee or extract_delivery_fee(full_text)
            r.eta_min = r.eta_min or extract_eta(full_text)
            r.promo_general_pct = r.promo_general_pct or extract_promo(full_text)
            r.rating = r.rating or extract_rating(full_text)
            r.review_count = r.review_count or extract_review_count(full_text)

            log.info(f"  [DiDi] products={len(r.products)} fee={r.delivery_fee} eta={r.eta_min} promo={r.promo_general_pct}%")

            # ── 10. Add to cart and capture subtotal ──
            if r.products:
                try:
                    cart_subtotal = await self._add_products_to_cart(page, r.products)
                    if cart_subtotal and cart_subtotal > 0:
                        r.subtotal = cart_subtotal
                        log.info(f"  [DiDi] using cart subtotal: ${cart_subtotal}")
                except Exception as e:
                    log.warning(f"  [DiDi] cart flow failed: {e}")

            r.compute_financials(self.PLATFORM)
            r.status = "success" if len(r.products) > 0 else "partial"

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "final", sdir)

        except Exception as e:
            r.status = "error"
            r.error_detail = str(e)[:300]
            log.warning(f"[DiDi] {addr['id']} {type(e).__name__}: {str(e)[:100]}")

        return r


# ── Orchestrator ──────────────────────────────────────────────────────────────

def _to_dict(r: PlatformResult) -> dict:
    return {
        "platform": r.platform, "status": r.status,
        "restaurant_name": r.restaurant_name, "restaurant_available": r.restaurant_available,
        "rating": r.rating, "review_count": r.review_count,
        "eta_min": r.eta_min, "delivery_fee": r.delivery_fee,
        "promo_general_pct": r.promo_general_pct,
        "products": [{"name":p.name,"price_original":p.price_original,
                      "price_discounted":p.price_discounted,"discount_pct":p.discount_pct}
                     for p in r.products],
        "subtotal": r.subtotal, "service_fee_estimated": r.service_fee_estimated,
        "total_estimated": r.total_estimated,
        "screenshot_path": r.screenshot_path, "error_detail": r.error_detail,
    }

def _csv(results, path):
    rows = []
    for rec in results:
        for plat in PLATFORMS:
            if plat not in rec: continue
            p = rec[plat]
            prods = {pr["name"]:pr for pr in p.get("products",[])}
            bm  = prods.get("Combo Big Mac mediano",{})
            hdq = prods.get("Hamburguesa doble con queso",{})
            cc  = prods.get("Coca-Cola mediana",{})
            rows.append({
                "scraped_at":rec.get("scraped_at"), "address_id":rec.get("address_id"),
                "city":rec.get("city"), "zone":rec.get("zone"), "zone_type":rec.get("zone_type"),
                "platform":plat, "status":p.get("status"),
                "restaurant_available":p.get("restaurant_available"),
                "rating":p.get("rating"),
                "eta_min":p.get("eta_min"), "delivery_fee_mxn":p.get("delivery_fee"),
                "promo_general_pct":p.get("promo_general_pct"),
                "bm_price_orig":bm.get("price_original"), "bm_price_disc":bm.get("price_discounted"), "bm_disc_pct":bm.get("discount_pct"),
                "hdq_price_orig":hdq.get("price_original"), "hdq_price_disc":hdq.get("price_discounted"), "hdq_disc_pct":hdq.get("discount_pct"),
                "cc_price_orig":cc.get("price_original"), "cc_price_disc":cc.get("price_discounted"), "cc_disc_pct":cc.get("discount_pct"),
                "subtotal_mxn":p.get("subtotal"), "service_fee_mxn":p.get("service_fee_estimated"),
                "total_estimated_mxn":p.get("total_estimated"), "error":p.get("error_detail",""),
            })
    if not rows: return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    log.info(f"CSV: {path} ({len(rows)} rows)")


async def run_scraper(addresses=None, max_addresses=25, headless=True, platforms=None, take_shots=True):
    targets = (addresses or ADDRESSES)[:max_addresses]
    active  = platforms or PLATFORMS
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sdir = Path(f"screenshots/{ts}")
    if take_shots: sdir.mkdir(parents=True, exist_ok=True)
    out = Path(f"data/competitive_data_{ts}.json")
    results = []
    scrapers = {"rappi":RappiScraper(), "ubereats":UberEatsScraper(), "didifood":DiDiFoodScraper()}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--no-sandbox","--disable-blink-features=AutomationControlled"],
        )
        for i, addr in enumerate(targets, 1):
            log.info(f"\n[{i}/{len(targets)}] {addr['id']} — {addr['zone']} ({addr['zone_type']})")
            row = {"scraped_at":datetime.now().isoformat(),"address_id":addr["id"],
                   "city":addr["city"],"zone":addr["zone"],"zone_type":addr["zone_type"],
                   "address":addr["address"],"restaurant_compared":"McDonald's"}

            for plat in active:
                is_mobile = (plat == "didifood")
                storage_state = None
                if is_mobile and DIDI_STORAGE_PATH.exists():
                    storage_state = str(DIDI_STORAGE_PATH)
                ctx = await iphone_ctx(browser, storage_state=storage_state) if is_mobile else await desktop_ctx(browser)
                page = await ctx.new_page()
                try:
                    pr = await scrapers[plat].scrape(page, addr, sdir, take_shots)
                except Exception as e:
                    pr = PlatformResult(platform=plat, status="error", error_detail=str(e)[:200])
                finally:
                    await ctx.close()

                row[plat] = _to_dict(pr)
                st = {"success":"OK","partial":"PARTIAL","error":"FAIL"}.get(pr.status, pr.status)
                log.info(f"  {st:8s} [{plat:10s}] eta={pr.eta_min}m fee={pr.delivery_fee} products={len(pr.products)} total={pr.total_estimated}")
                await delay(2, 4)

            results.append(row)
            with open(out,"w",encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            if i < len(targets): await delay(4, 7)

        await browser.close()

    _csv(results, out.with_suffix(".csv"))
    ok = sum(1 for r in results for plat in active if r.get(plat,{}).get("status")=="success")
    log.info(f"\nDone: {len(results)} addresses | {ok} successful platform scrapes")
    log.info(f"Output: {out}")
    return results, str(out)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--max-addresses", type=int, default=25)
    p.add_argument("--visible", action="store_true")
    p.add_argument("--city", choices=["cdmx","gdl","mty"])
    p.add_argument("--platforms", nargs="+", choices=PLATFORMS)
    p.add_argument("--no-screenshots", action="store_true")
    args = p.parse_args()

    cmap = {"cdmx":"Ciudad de Mexico","gdl":"Guadalajara","mty":"Monterrey"}
    targets = [a for a in ADDRESSES if a["city"]==cmap[args.city]] if args.city else ADDRESSES

    asyncio.run(run_scraper(
        addresses=targets, max_addresses=args.max_addresses,
        headless=not args.visible, platforms=args.platforms,
        take_shots=not args.no_screenshots,
    ))
