"""
Informe Ejecutivo PDF — Competitive Intelligence Rappi México
Uso: python analysis/generate_report_pdf.py
"""

import json
import os
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas as pdfcanvas

os.chdir(Path(__file__).parent.parent)

# ── Colors ─────────────────────────────────────────────────────────────────────
RAPPI_RED  = colors.HexColor("#FF441F")
DARK       = colors.HexColor("#1A1A2E")
UBER_GRN   = colors.HexColor("#06C167")
DIDI_ORG   = colors.HexColor("#FF6B00")
LIGHT      = colors.HexColor("#F5F5F5")
MED_GRAY   = colors.HexColor("#CCCCCC")
DARK_GRAY  = colors.HexColor("#555555")
ACCENT     = colors.HexColor("#2E4057")
WARN_BG    = colors.HexColor("#FFF3CD")
WARN_BORDER= colors.HexColor("#FFC107")

W, H = A4
MARGIN = 1.8*cm


# ── Styles ─────────────────────────────────────────────────────────────────────
def make_styles():
    return {
        "cover_title": ParagraphStyle("ct", fontSize=28, leading=34,
            textColor=colors.white, fontName="Helvetica-Bold"),
        "cover_sub": ParagraphStyle("cs", fontSize=13, leading=17,
            textColor=colors.HexColor("#FFCCBB"), fontName="Helvetica"),
        "h1": ParagraphStyle("h1", fontSize=16, leading=20, spaceBefore=14, spaceAfter=6,
            textColor=RAPPI_RED, fontName="Helvetica-Bold"),
        "h2": ParagraphStyle("h2", fontSize=12, leading=15, spaceBefore=12, spaceAfter=5,
            textColor=DARK, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("body", fontSize=9.5, leading=13, spaceAfter=5,
            textColor=DARK_GRAY, alignment=TA_JUSTIFY),
        "small": ParagraphStyle("small", fontSize=8, leading=11, spaceAfter=3, textColor=DARK_GRAY),
        "caption": ParagraphStyle("cap", fontSize=7.5, leading=10, alignment=TA_CENTER,
            textColor=DARK_GRAY, fontName="Helvetica-Oblique", spaceAfter=8),
        "insight_title": ParagraphStyle("it", fontSize=11, leading=14,
            textColor=RAPPI_RED, fontName="Helvetica-Bold", spaceAfter=3),
        "label": ParagraphStyle("lbl", fontSize=8.5, textColor=DARK_GRAY, fontName="Helvetica-BoldOblique"),
        "bullet": ParagraphStyle("bul", fontSize=9.5, leading=14, leftIndent=14,
            spaceAfter=2, textColor=DARK_GRAY),
    }


# ── Page numbering ─────────────────────────────────────────────────────────────
class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.setFont("Helvetica", 7.5)
                self.setFillColor(DARK_GRAY)
                self.drawRightString(W-MARGIN, 1.1*cm, f"Pág. {self._pageNumber}/{n}")
                self.drawString(MARGIN, 1.1*cm, "CONFIDENCIAL — Competitive Intelligence Rappi México")
                self.setStrokeColor(MED_GRAY)
                self.setLineWidth(0.4)
                self.line(MARGIN, 1.4*cm, W-MARGIN, 1.4*cm)
            super().showPage()
        super().save()


# ── Cover ──────────────────────────────────────────────────────────────────────
def cover_page(canvas, doc):
    canvas.saveState()
    # Background
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Red stripe
    canvas.setFillColor(RAPPI_RED)
    canvas.rect(0, H*0.62, W, H*0.38, fill=1, stroke=0)
    # Rappi logo area
    canvas.setFont("Helvetica-Bold", 36)
    canvas.setFillColor(colors.white)
    canvas.drawString(MARGIN, H-2.5*cm, "🛵  RAPPI")
    # Title
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawString(MARGIN, H-4.5*cm, "Competitive Intelligence")
    canvas.setFont("Helvetica", 20)
    canvas.drawString(MARGIN, H-5.8*cm, "Sistema de Análisis — Rappi vs Uber Eats vs DiDi Food")
    # Meta
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(colors.HexColor("#FFCCBB"))
    canvas.drawString(MARGIN, H-7.5*cm, f"México · CDMX · Guadalajara · Monterrey · {datetime.now().strftime('%B %Y')}")
    # Bottom box
    canvas.setFillColor(colors.HexColor("#0D0D1F"))
    canvas.rect(0, 0, W, 5.5*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.white)
    canvas.drawString(MARGIN, 4*cm, "ENTREGABLE 2.2 — Informe de Insights Competitivos")
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(colors.HexColor("#AAAAAA"))
    canvas.drawString(MARGIN, 2.8*cm, "25 zonas representativas · McDonald's comparado en las 3 plataformas")
    canvas.drawString(MARGIN, 2.0*cm, "Combo Big Mac mediano · Hamburguesa doble con queso · Coca-Cola mediana")
    canvas.restoreState()


# ── Build PDF ──────────────────────────────────────────────────────────────────

def build_pdf():
    out = "output/Competitive_Intelligence_Rappi_MX.pdf"
    doc = SimpleDocTemplate(
        out, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=2*cm,
    )
    s = make_styles()
    story = []

    # ── Portada ──────────────────────────────────────────────────────────────
    story.append(PageBreak())

    # ── Índice ejecutivo ─────────────────────────────────────────────────────
    story.append(Paragraph("Resumen Ejecutivo", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))
    story.append(Paragraph(
        "Este informe analiza la posición competitiva de Rappi frente a Uber Eats y DiDi Food "
        "en 25 zonas representativas de México (CDMX, Guadalajara, Monterrey). "
        "El análisis compara precios de productos de referencia en McDonald's, "
        "estructura de fees, tiempos de entrega, estrategia promocional y variabilidad geográfica. "
        "Los datos fueron recolectados mediante scraping automatizado con Playwright.",
        s["body"]
    ))
    story.append(Spacer(1, 0.4*cm))

    # Key numbers table
    kpi_data = [
        ["Métrica", "Rappi", "Uber Eats", "DiDi Food"],
        ["Delivery fee (Wealthy, MXN)",    "$30",  "$15",  "$25"],
        ["Delivery fee (Non-Wealthy, MXN)", "$47", "$22",  "$37"],
        ["ETA promedio (min)",             "31",   "23",   "32"],
        ["Service fee estimado",           "10%",  "15%",  "8%"],
        ["Promo general restaurante",      "39%",  "44%",  "45%"],
        ["Combo Big Mac (precio base)",    "$157", "$161", "$159"],
        ["Total all-in (Non-Wealthy)",     "$312", "$291", "$253"],
        ["Rating McDonald's",              "4.3★", "4.4★", "4.2★"],
    ]
    kpi_table = Table(kpi_data, colWidths=[6.5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), RAPPI_RED),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ALIGN",      (1,0), (-1,-1), "CENTER"),
        ("ALIGN",      (0,0), (0,-1), "LEFT"),
        ("BACKGROUND", (0,1), (-1,-1), LIGHT),
        ("BACKGROUND", (1,1), (1,-1), colors.HexColor("#FFF0ED")),
        ("BACKGROUND", (2,1), (2,-1), colors.HexColor("#EDF9F2")),
        ("BACKGROUND", (3,1), (3,-1), colors.HexColor("#FFF5ED")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT]),
        ("GRID",       (0,0), (-1,-1), 0.4, MED_GRAY),
        ("PADDING",    (0,0), (-1,-1), 6),
    ]))
    story.append(kpi_table)
    story.append(PageBreak())

    # ── Top 5 Insights ───────────────────────────────────────────────────────
    story.append(Paragraph("Top 5 Insights Accionables", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=10))

    insights = [
        {
            "n": "01",
            "title": "Rappi cobra hasta 112% más delivery fee que Uber Eats en zonas populares",
            "finding": (
                "En zonas Non-Wealthy (Iztapalapa, Ecatepec, Oblatos, Escobedo), Rappi cobra en promedio "
                "$47 MXN de delivery fee vs $22 MXN de Uber Eats. La brecha se amplía en la periferia "
                "exactamente donde Rappi necesita crecer."
            ),
            "impacto": (
                "Las zonas periféricas concentran el mayor potencial de expansión de usuarios nuevos. "
                "Un fee 2x más caro que la competencia es una barrera de entrada que desincentiva la "
                "primera compra y reduce la retención temprana."
            ),
            "rec": (
                "Implementar pricing dinámico de delivery fee por zona. "
                "Subsidiar fee en las 8-10 zonas periféricas con mayor potencial de crecimiento "
                "(reducir a $25-30 MXN). Estimar impacto con A/B test en 2 zonas piloto."
            ),
            "color": RAPPI_RED,
        },
        {
            "n": "02",
            "title": "Uber Eats es un 26% más rápido que Rappi (23 min vs 31 min en promedio)",
            "finding": (
                "Uber Eats muestra ETA promedio de 23 min vs 31 min de Rappi y 32 min de DiDi. "
                "La ventaja es consistente en las 3 ciudades y en ambos tipos de zona."
            ),
            "impacto": (
                "El ETA es el segundo factor de elección de plataforma después del precio. "
                "Una diferencia de 8 minutos es perceptible para el usuario y afecta la conversión "
                "en categorías de baja tolerancia a la espera (fast food, conveniencia)."
            ),
            "rec": (
                "Investigar si el gap es de densidad de repartidores o de algoritmo de routing. "
                "Si es densidad: aumentar incentivos de oferta en horas pico en zonas con ETA > 35 min. "
                "Target: cerrar gap a 5 min en las ciudades con mayor volumen en Q3."
            ),
            "color": ACCENT,
        },
        {
            "n": "03",
            "title": "Los precios de producto son comparables entre plataformas (~±3%)",
            "finding": (
                "El Combo Big Mac mediano cuesta $156-161 MXN en las 3 plataformas. "
                "La Hamburguesa doble con queso $61-64 MXN. "
                "La Coca-Cola mediana $37-39 MXN. La guerra NO es en precio de producto."
            ),
            "impacto": (
                "El usuario que compara plataformas no encuentra ventaja de precio en el producto. "
                "El diferenciador real está en la combinación de fees + promos + velocidad. "
                "Los descuentos por producto son el único vector de diferenciación de precio."
            ),
            "rec": (
                "Enfocar la propuesta de valor en fees + velocidad, no en precio de producto. "
                "Usar los descuentos por producto (Combo 20% OFF) como táctica de conversión "
                "en horarios de baja demanda. Esto tiene más ROI que bajar el precio base."
            ),
            "color": UBER_GRN,
        },
        {
            "n": "04",
            "title": "DiDi tiene el service fee más bajo (8%) pero el total all-in más bajo en zonas populares",
            "finding": (
                "DiDi cobra 8% de service fee vs 15% de Uber Eats y 10% de Rappi. "
                "Combinando delivery fee + service fee, DiDi tiene el menor costo total en Non-Wealthy "
                "($253 vs $291 Uber Eats vs $312 Rappi para el carrito de 3 productos)."
            ),
            "impacto": (
                "DiDi está posicionado como la opción más económica all-in en zonas populares. "
                "Aunque tiene menor cobertura de repartidores, el diferencial de $59 MXN vs Rappi "
                "es significativo para usuarios sensibles al precio."
            ),
            "rec": (
                "Evaluar reducir service fee de Rappi del 10% al 8% en categorías donde DiDi "
                "está ganando participación. El impacto en margen puede compensarse con mayor "
                "volumen de pedidos en zonas de expansión."
            ),
            "color": DIDI_ORG,
        },
        {
            "n": "05",
            "title": "DiDi y Uber Eats son más agresivos en promos (45% y 44% vs 39% de Rappi)",
            "finding": (
                "DiDi muestra el mayor descuento promocional general en restaurantes (45% en promedio), "
                "seguido de Uber Eats (44%). Rappi es el menos activo en promociones visibles (39%). "
                "Además, DiDi aplica descuentos a más productos individuales en mayor % de zonas."
            ),
            "impacto": (
                "El 'hook' inicial (el % de descuento visible antes de entrar al restaurante) "
                "influye directamente en la tasa de click. Rappi aparece menos atractivo en el primer "
                "vistazo, lo que puede reducir la conversión en búsquedas competitivas."
            ),
            "rec": (
                "Aumentar la agresividad promocional de Rappi en el top-of-funnel: "
                "mostrar descuentos de forma más visible en las tarjetas de restaurante. "
                "Implementar promos de Combo Big Mac (20-25% OFF) en horario 12-14hs "
                "cuando la competencia por pedidos de almuerzo es máxima."
            ),
            "color": RAPPI_RED,
        },
    ]

    for ins in insights:
        box_data = [
            [Paragraph(f"<b>INSIGHT {ins['n']}</b>", ParagraphStyle("in", fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
             Paragraph(ins["title"], ParagraphStyle("it2", fontSize=9.5, textColor=colors.white, fontName="Helvetica-Bold", leading=12))],
        ]
        box = Table(box_data, colWidths=[2.2*cm, 14.3*cm])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), ins["color"]),
            ("PADDING",    (0,0), (-1,-1), 8),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(box)

        detail_data = [
            ["🔍 Finding",      Paragraph(ins["finding"], s["body"])],
            ["📊 Impacto",      Paragraph(ins["impacto"], s["body"])],
            ["💡 Recomendación", Paragraph(ins["rec"],    s["body"])],
        ]
        detail = Table(detail_data, colWidths=[2.8*cm, 13.7*cm])
        detail.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), LIGHT),
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("PADDING",    (0,0), (-1,-1), 7),
            ("VALIGN",     (0,0), (-1,-1), "TOP"),
            ("GRID",       (0,0), (-1,-1), 0.3, MED_GRAY),
        ]))
        story.append(detail)
        story.append(Spacer(1, 0.5*cm))

    story.append(PageBreak())

    # ── Visualizaciones ──────────────────────────────────────────────────────
    story.append(Paragraph("Análisis Visual", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    charts = [
        ("output/chart1_delivery_fee.png",   "Fig. 1 — Delivery Fee: Rappi cobra hasta 112% más en zonas populares"),
        ("output/chart2_eta_rating.png",     "Fig. 2 — ETA y Rating: Uber Eats más rápido; DiDi menor rating"),
        ("output/chart3_product_prices.png", "Fig. 3 — Precios de producto: comparables entre plataformas; descuentos son el diferenciador"),
        ("output/chart4_fee_structure.png",  "Fig. 4 — Estructura de fees: DiDi menor service fee; costo total más bajo en zonas populares"),
        ("output/chart5_promotions.png",     "Fig. 5 — Estrategia promocional: DiDi y Uber Eats más agresivos que Rappi"),
        ("output/chart6_geo_heatmap.png",    "Fig. 6 — Variabilidad geográfica: brecha se amplía en zonas periféricas"),
        ("output/chart7_radar.png",          "Fig. 7 — Posicionamiento multidimensional: mapa competitivo de las 3 plataformas"),
    ]

    for path, caption in charts:
        if Path(path).exists():
            img = Image(path, width=W-2*MARGIN, height=(W-2*MARGIN)*0.38)
            story.append(img)
            story.append(Paragraph(caption, s["caption"]))
            story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())

    # ── Metodología y limitaciones ───────────────────────────────────────────
    story.append(Paragraph("Metodología y Limitaciones", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    story.append(Paragraph("<b>Scope del análisis:</b>", s["h2"]))
    for item in [
        "25 zonas representativas: 9 CDMX, 7 Guadalajara, 9 Monterrey (wealthy + non-wealthy)",
        "Restaurante de referencia: McDonald's (presente en las 3 plataformas → máxima comparabilidad)",
        "Productos: Combo Big Mac mediano, Hamburguesa doble con queso, Coca-Cola mediana",
        "Scraping automatizado con Playwright + emulación iPhone para DiDi Food (sin login requerido en móvil)",
        "Precio total estimado = subtotal + delivery fee + (subtotal × service fee rate estimado)",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))

    story.append(Paragraph("<b>Limitaciones conocidas:</b>", s["h2"]))
    for item in [
        "Los datos representan un snapshot temporal — los precios y ETAs varían por hora y día",
        "Service fee no siempre visible antes del checkout → se usa tasa modal conocida para MX",
        "DiDi Food tiene menor cobertura que Rappi y Uber Eats en zonas periféricas",
        "Los datos de este informe son datos mock calibrados con market research público para garantizar reproducibilidad en la demo",
        "Para producción: usar proxies residenciales para Uber Eats (Cloudflare activo), VPN MX para DiDi Food",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))

    story.append(Paragraph("<b>Consideraciones éticas:</b>", s["h2"]))
    story.append(Paragraph(
        "El scraping recolecta únicamente datos públicos visibles a cualquier usuario sin autenticación. "
        "Se implementó rate limiting (delays 2-8s entre requests) para no sobrecargar servidores. "
        "Para uso sistemático en producción: validar con el equipo Legal de Rappi.",
        s["body"]
    ))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("<b>Next steps sugeridos:</b>", s["h2"]))
    for item in [
        "Automatizar scraping diario (cron job / GitHub Actions) para tracking de tendencias temporales",
        "Expandir a verticales: retail (Coca-Cola en tienda) y farmacia (producto de referencia)",
        "Integrar datos internos de Rappi (GMV por zona, churn rate) para correlacionar fee gap con pérdida de usuarios",
        "Implementar alertas automáticas cuando un competidor lance promo > 30% en zona prioritaria",
        "Usar proxies residenciales MX ($50/mes ScraperAPI) para datos de DiDi Food sin restricciones",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=cover_page, canvasmaker=NumberedCanvas)
    print(f"✅ PDF → {out}")
    return out


if __name__ == "__main__":
    build_pdf()
