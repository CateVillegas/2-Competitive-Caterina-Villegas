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
import asyncio, csv, json, logging, random, re, sys, io
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ── Logging UTF-8 (fix Windows cp1252) ───────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("screenshots").mkdir(exist_ok=True)

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
        if prices:
            self.subtotal = round(sum(prices), 2)
        if self.subtotal:
            rate = SERVICE_FEE.get(platform, 0.10)
            self.service_fee_estimated = round(self.subtotal * rate, 2)
            self.total_estimated = round(self.subtotal + (self.delivery_fee or 0) + self.service_fee_estimated, 2)

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

def valid_mcdo(name):
    return all(x not in name.lower() for x in ["postre","desayuno","breakfast","mcflurry","helado"])

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
        "keywords":    ["home office con big mac", "home office big mac", "home office"],
        "anti":        ["postre","mcflurry","nuggets","cuarto","quarter","triple",
                        "desayuno","tocino","favoritos","mctrío","mctrio"],
        "price_range": (80, 400),
    },
    {
        "name":        "Hamburguesa doble con queso",
        # Must match the standalone item, NOT combo descriptions like
        # "McPollo o Doble con Queso" or "Elige entre McPollo o Hamburguesa..."
        "keywords":    ["hamburguesa doble con queso"],
        "anti":        ["combo","papas","triple","mcnifica","mcpollo","elige","paquete","cajita"],
        "price_range": (40, 200),
    },
    {
        "name":        "Coca-Cola mediana",
        "keywords":    ["coca-cola mediana","coca cola mediana"],
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
    """Extract the number of reviews/ratings from page text."""
    patterns = [
        r"([\d.,]+)\+?\s*(?:calificaciones|calificaci[oó]n|rese[nñ]as|ratings|opiniones)",
        r"\(([\d.,]+)\+?\)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "").replace(".", "")
            try:
                return int(raw)
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

async def iphone_ctx(browser):
    return await browser.new_context(
        user_agent=IPHONE_UA,
        locale="es-MX",
        timezone_id="America/Mexico_City",
        viewport={"width":390,"height":844},
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True,
    )

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
        'input[placeholder*="Buscar" i]',
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
    DiDi Food requires mobile emulation — the desktop site forces login.
    We use iPhone UA + mobile viewport to bypass the login wall.
    Flow: home → address → search → store → extract text.
    """
    PLATFORM = "didifood"

    # DiDi Food Mexico URLs to try (they change domains sometimes)
    ENTRY_URLS = [
        "https://www.didifood.com/mx",
        "https://food.didiglobal.com/mx",
        "https://web.didiglobal.com/mx/food/",
    ]

    async def scrape(self, page: Page, addr: dict, sdir: Path, take_shots: bool) -> PlatformResult:
        r = PlatformResult(platform=self.PLATFORM)
        try:
            # ── 1. Try to load DiDi Food ──────────────────────────────────
            loaded = False
            for url in self.ENTRY_URLS:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await delay(2, 4)
                    content = await page.content()
                    # Check for domain parking / redirect
                    if any(x in content.lower() for x in ["available domain", "broker", "for sale", "domain for sale"]):
                        log.warning(f"  [DiDi] domain parking detected at {url}")
                        continue
                    loaded = True
                    log.info(f"  [DiDi] loaded: {url}")
                    break
                except Exception as e:
                    log.warning(f"  [DiDi] failed to load {url}: {e}")
                    continue

            if not loaded:
                r.status = "error"
                r.error_detail = "Could not load any DiDi Food URL"
                return r

            # ── 2. Handle the landing page flow ───────────────────────────
            # On the landing page, need to select city first
            city_name = {
                "Ciudad de Mexico": "Ciudad de México",
                "Guadalajara": "Guadalajara",
                "Monterrey": "Monterrey",
            }.get(addr["city"], "Ciudad de México")

            # Try to select city
            for sel in [
                f'a:has-text("{city_name}")',
                f'button:has-text("{city_name}")',
                f'text="{city_name}"',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.click()
                        log.info(f"  [DiDi] selected city: {city_name}")
                        await delay(2, 3)
                        break
                except Exception:
                    continue

            # Click "Entra" or "Ver restaurantes" button
            for sel in [
                'button:has-text("Entra")',
                'a:has-text("Entra")',
                'a:has-text("entra al sitio")',
                'button:has-text("Ver restaurantes")',
                'a:has-text("Ver restaurantes")',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.click()
                        await delay(2, 4)
                        log.info(f"  [DiDi] clicked enter button")
                        break
                except Exception:
                    continue

            # ── 3. Set address ────────────────────────────────────────────
            addr_sels = [
                'input[placeholder*="direcci" i]',
                'input[placeholder*="Ingresa" i]',
                'input[placeholder*="domicilio" i]',
                'input[type="text"]:not([hidden])',
            ]

            addr_ok = await find_and_fill_input(page, addr_sels, addr["address"], use_keyboard=True)
            if addr_ok:
                await delay(2, 3)
                await click_first_suggestion(page)
                await delay(2, 4)
            else:
                log.warning("  [DiDi] address input not found")

            # ── 4. Check for login wall ───────────────────────────────────
            page_text = await page.evaluate("() => document.body.innerText")
            if any(x in page_text.lower() for x in ["iniciar sesión", "iniciar sesion", "registr", "inicia sesión"]):
                r.status = "error"
                r.error_detail = "Login required - DiDi Food desktop requires authentication"
                log.warning("  [DiDi] login wall detected")
                if take_shots:
                    r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "login_wall", sdir)
                return r

            # ── 5. Search for McDonald's ──────────────────────────────────
            search_sels = [
                'input[placeholder*="Buscar" i]',
                'input[placeholder*="buscar" i]',
                'input[type="search"]',
                'input[placeholder*="restaurant" i]',
            ]

            typed = await find_and_fill_input(page, search_sels, "McDonalds", use_keyboard=True)
            if typed:
                await page.keyboard.press("Enter")
                await delay(3, 5)
            else:
                log.warning("  [DiDi] search input not found")

            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "search", sdir)

            # ── 6. Find and enter McDonalds store ─────────────────────────
            store_ok = False

            # Try clickable cards/links containing "mcdonald"
            card_sels = [
                'a:has-text("McDonald")',
                'a:has-text("Mc Donald")',
                '[class*="restaurant" i]:has-text("McDonald")',
                '[class*="RestaurantCard" i]:has-text("McDonald")',
                '[class*="store" i]:has-text("McDonald")',
            ]
            for sel in card_sels:
                try:
                    cards = await page.locator(sel).all()
                    for card in cards:
                        text = (await card.inner_text()).strip()
                        if "mcdonald" in text.lower() and valid_mcdo(text):
                            await card.click()
                            r.restaurant_name = text[:60]
                            store_ok = True
                            log.info(f"  [DiDi] store: {r.restaurant_name[:40]}")
                            await delay(3, 5)
                            break
                except Exception:
                    continue
                if store_ok:
                    break

            if not store_ok:
                r.status = "partial_no_store"
                log.warning("  [DiDi] no McDonalds store found")
                return r

            r.restaurant_available = True
            if take_shots:
                r.screenshot_path = await shot(page, addr["id"], self.PLATFORM, "store", sdir)

            # ── 7. Scroll and extract ─────────────────────────────────────
            await delay(2, 3)
            await ensure_full_scroll(page, pause=0.7, max_scrolls=20)

            full_text = await page.evaluate("() => document.body.innerText")

            r.products = extract_products_from_text(full_text)
            r.delivery_fee = extract_delivery_fee(full_text)
            r.eta_min = extract_eta(full_text)
            r.promo_general_pct = extract_promo(full_text)
            r.rating = extract_rating(full_text)

            log.info(f"  [DiDi] products={len(r.products)} fee={r.delivery_fee} eta={r.eta_min} promo={r.promo_general_pct}%")

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
        "rating": r.rating, "eta_min": r.eta_min, "delivery_fee": r.delivery_fee,
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
                ctx = await iphone_ctx(browser) if is_mobile else await desktop_ctx(browser)
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
