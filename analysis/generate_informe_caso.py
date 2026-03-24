"""Genera el informe PDF del caso tecnico: como se resolvio, decisiones, limitaciones y proximos pasos."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT = Path("output/Informe_Caso_Tecnico_CI_Rappi.pdf")
MARGIN = 1.8 * cm
RAPPI_RED = colors.HexColor("#FF441F")
DARK = colors.HexColor("#0D0F1F")
TEXT = colors.HexColor("#1A1A2E")
LIGHT_BG = colors.HexColor("#F4F5FB")
ACCENT = colors.HexColor("#5B8EF0")


class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.setFont("Helvetica", 7)
                self.setFillColor(colors.HexColor("#6F7391"))
                self.drawRightString(A4[0] - MARGIN, 1.0 * cm, f"Pag. {self._pageNumber}/{total}")
                self.drawString(MARGIN, 1.0 * cm, "Informe del Caso Tecnico - Competitive Intelligence Rappi")
                self.setStrokeColor(colors.HexColor("#D7DAE7"))
                self.setLineWidth(0.4)
                self.line(MARGIN, 1.3 * cm, A4[0] - MARGIN, 1.3 * cm)
            super().showPage()
        super().save()


def cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    canvas.setFillColor(RAPPI_RED)
    canvas.rect(0, A4[1] * 0.6, A4[0], A4[1] * 0.4, stroke=0, fill=1)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(MARGIN, A4[1] - 2.8 * cm, "INFORME DEL CASO TECNICO")
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(MARGIN, A4[1] - 4.5 * cm, "Competitive Intelligence")
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(MARGIN, A4[1] - 5.8 * cm, "System para Rappi")

    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(colors.HexColor("#FFE9E0"))
    canvas.drawString(MARGIN, A4[1] - 7.4 * cm, f"Fecha: {datetime.now().strftime('%d %b %Y')}")

    canvas.setFillColor(colors.HexColor("#0F111C"))
    canvas.rect(0, 0, A4[0], 5.5 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(MARGIN, 4 * cm, "Caso: AI Engineer - Rappi")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(MARGIN, 3 * cm, "Sistema de scraping competitivo + analisis de insights accionables")
    canvas.drawString(MARGIN, 2.2 * cm, "Plataformas: Rappi vs Uber Eats vs DiDi Food | 25 direcciones | 3 ciudades")
    canvas.restoreState()


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TitleSmall", parent=styles["Heading1"], fontSize=15, textColor=TEXT))
    styles.add(ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, textColor=TEXT, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle("SubSection", parent=styles["Heading3"], fontSize=11, textColor=TEXT, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, leading=14, textColor=TEXT, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle("Bullet", parent=styles["BodyText"], fontSize=10, leading=14, textColor=TEXT,
                               leftIndent=20, bulletIndent=10))
    styles.add(ParagraphStyle("Note", parent=styles["BodyText"], fontSize=9, textColor=colors.HexColor("#555577"),
                               leftIndent=12, rightIndent=12, spaceBefore=6, spaceAfter=6))
    return styles


def make_table(data, col_widths=None):
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RAPPI_RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCD0E0")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B6BACB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def build_story(styles):
    s = styles
    story = []
    story.append(PageBreak())

    # =========================================================================
    # 1. RESUMEN EJECUTIVO
    # =========================================================================
    story.append(Paragraph("1. Resumen ejecutivo", s["TitleSmall"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))
    story.append(Paragraph(
        "Se construyo un sistema de Competitive Intelligence que recolecta datos de Rappi, Uber Eats y DiDi Food "
        "en 25 direcciones estrategicas de Mexico (Ciudad de Mexico, Guadalajara y Monterrey), compara precios, "
        "tiempos de entrega, fees y promociones del mismo restaurante (McDonald's) en las 3 plataformas, "
        "y genera insights accionables para los equipos de Strategy, Pricing y Operations.",
        s["Body"]
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "El sistema tiene 3 componentes principales: (1) un scraper automatizado con Playwright que funciona "
        "exitosamente para Rappi y Uber Eats, (2) un pipeline de analisis que genera 14 graficos, KPIs y 5 insights "
        "accionables, y (3) dos formatos de presentacion: un PDF ejecutivo y un dashboard interactivo HTML con "
        "Chart.js.",
        s["Body"]
    ))

    # =========================================================================
    # 2. LO QUE SE LOGRO
    # =========================================================================
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("2. Alcance logrado", s["TitleSmall"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    story.append(Paragraph("2.1 Scraping automatizado", s["Section"]))
    story.append(Paragraph(
        "Se logro implementar con exito el scraping automatizado para <b>Rappi</b> y <b>Uber Eats</b> utilizando "
        "Playwright como motor de automatizacion de browser. El scraper navega a cada direccion, busca McDonald's, "
        "entra al restaurante y extrae todos los datos relevantes de forma autonoma.",
        s["Body"]
    ))
    story.append(Spacer(1, 0.2 * cm))

    scraping_data = [
        ["Plataforma", "Estado", "Metodo", "Resultado"],
        ["Rappi", "Automatizado", "Playwright headless", "25/25 direcciones exitosas"],
        ["Uber Eats", "Automatizado", "Playwright headless", "23/25 direcciones exitosas"],
        ["DiDi Food", "Manual", "Recoleccion manual en las 25 dir.", "23/25 direcciones con datos"],
    ]
    story.append(make_table(scraping_data))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.2 Datos recolectados", s["Section"]))
    story.append(Paragraph(
        "Se recolectan las siguientes metricas por cada combinacion direccion-plataforma:",
        s["Body"]
    ))

    metrics_data = [
        ["Metrica", "Descripcion", "Fuente"],
        ["Precio de 3 productos", "Combo Big Mac, Hamburguesa Doble c/ Queso, Coca-Cola Mediana", "Scraping"],
        ["Descuento por producto", "% de rebaja sobre precio original de cada producto", "Scraping"],
        ["Promo hook", "% descuento visible en la tarjeta del restaurante en el feed", "Scraping"],
        ["ETA", "Tiempo de entrega estimado en minutos", "Scraping"],
        ["Rating", "Calificacion del restaurante en la plataforma", "Scraping"],
        ["Delivery fee", "Costo de envio (estandarizado a $15 MXN, ver decisiones)", "Scraping + ajuste"],
        ["Service fee", "Comision de la plataforma (estimado: R 10%, U 15%, D 8%)", "Estimado"],
        ["Total estimado", "Subtotal + delivery fee + service fee", "Calculado"],
        ["Disponibilidad", "Si el restaurante aparecio en la plataforma", "Scraping"],
        ["Zona / Ciudad / Tipo", "Clasificacion geografica y socioeconomica", "Configuracion"],
    ]
    story.append(make_table(metrics_data))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.3 Analisis e insights", s["Section"]))
    story.append(Paragraph(
        "El pipeline de analisis genera automaticamente:",
        s["Body"]
    ))
    bullets = [
        "<b>14 graficos</b> que cubren: precios de los 3 productos, ETA por zona, rating por ciudad, "
        "promo hook, distribucion de promos, delivery fee, service fee, total estimado, "
        "desglose de costos (stacked), comparacion Wealthy vs Non Wealthy, heatmaps de ETA y precios, "
        "scatter ETA vs promo, y disponibilidad por tipo de zona.",
        "<b>5 insights accionables</b> generados dinamicamente con Finding, Impacto y Recomendacion "
        "sobre: posicionamiento de precios, ventaja operacional, estrategia promocional, estructura de fees, "
        "y variabilidad geografica.",
        "<b>PDF ejecutivo</b> con glosario de terminos, tabla comparativa completa (3 productos + fees), "
        "tabla Wealthy vs Non Wealthy, los 5 insights, y los 14 graficos con explicacion de proposito y "
        "relevancia para Strategy/Pricing.",
        "<b>Dashboard interactivo HTML</b> con fondo blanco para legibilidad, glosario integrado, filtros por "
        "plataforma/ciudad/zona, interpretaciones automaticas debajo de cada grafico, KPIs expandidos con "
        "los 3 productos, y tabla detallada con todos los datos crudos.",
    ]
    for b in bullets:
        story.append(Paragraph(f"\u2022 {b}", s["Bullet"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.4 Cobertura geografica", s["Section"]))
    geo_data = [
        ["Ciudad", "Zonas Wealthy", "Zonas Non Wealthy", "Total"],
        ["Ciudad de Mexico", "Polanco, Condesa, Roma Norte, Santa Fe, Del Valle", "Iztapalapa, Ecatepec, Tepito, Tlalpan", "9"],
        ["Guadalajara", "Providencia, Chapalita, Zapopan, Andares", "Oblatos, Las Juntas, Tonala", "7"],
        ["Monterrey", "San Pedro, Valle, Cumbres, Tecnologico, Centrito", "Independencia, Apodaca, Escobedo, Guadalupe", "9"],
    ]
    story.append(make_table(geo_data))
    story.append(Paragraph(
        "La seleccion incluye zonas de alto y bajo nivel socioeconomico para analizar variabilidad geografica "
        "en la competitividad de cada plataforma.",
        s["Note"]
    ))

    # =========================================================================
    # 3. DECISIONES TECNICAS
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("3. Decisiones tecnicas y justificaciones", s["TitleSmall"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    story.append(Paragraph("3.1 Problema con DiDi Food y solucion adoptada", s["Section"]))
    story.append(Paragraph(
        "DiDi Food presento multiples desafios tecnicos que impidieron la automatizacion completa del scraping:",
        s["Body"]
    ))
    didi_problems = [
        "<b>Version desktop inutilizable:</b> La pagina web de DiDi Food en escritorio no muestra restaurantes "
        "ni precios sin estar logueado. Verificado manualmente: la version desktop no esta disenada para navegacion "
        "publica de menus.",
        "<b>Verificacion SMS obligatoria:</b> DiDi Food requiere verificacion por codigo OTP via SMS cada vez que "
        "se inicia sesion. Este paso no se puede automatizar ya que depende de recibir un SMS en un telefono real.",
        "<b>Variabilidad en el flujo de UI:</b> Al cambiar de direccion, la interfaz de DiDi Food muestra diferentes "
        "pasos y formularios dependiendo de la zona. En algunas direcciones solicita datos adicionales, en otras no. "
        "Esto hace extremadamente complejo entrenar un scraper robusto en un dia.",
        "<b>Emulacion mobile:</b> Se implemento la emulacion de iPhone (390x844) ya que DiDi requiere user-agent "
        "mobile. Se logro llegar hasta la pantalla de busqueda de restaurantes, pero la inestabilidad del flujo "
        "entre direcciones impidio la automatizacion completa.",
    ]
    for b in didi_problems:
        story.append(Paragraph(f"\u2022 {b}", s["Bullet"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "<b>Solucion adoptada:</b> Para no perder cobertura de la tercera plataforma y poder generar un analisis "
        "competitivo completo con las 3 apps, se realizo la recoleccion de datos de DiDi Food de forma manual "
        "en las 25 direcciones. Esto permitio completar el dataset y generar insights comparativos reales con "
        "datos de las 3 plataformas. Los datos crudos del scraping automatico (Rappi + Uber Eats) estan disponibles "
        "en <i>data/competitive_data_RAW.csv</i>, y el dataset completo con DiDi en "
        "<i>data/competitive_data_with_didi.csv</i>.",
        s["Body"]
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("3.2 Estimacion del service fee", s["Section"]))
    story.append(Paragraph(
        "El service fee no es visible en ninguna de las 3 plataformas sin estar logueado y llegar al checkout. "
        "Como solucion, se estima el service fee multiplicando el subtotal por una tasa fija por plataforma: "
        "Rappi 10%, Uber Eats 15%, DiDi Food 8%. Estas tasas se obtuvieron de observaciones manuales y son "
        "aproximaciones razonables para el analisis comparativo. La clase <i>PlatformResult.compute_financials()</i> "
        "calcula: total_estimated = subtotal + (delivery_fee o 0) + service_fee, redondeado a 2 decimales.",
        s["Body"]
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("3.3 Estandarizacion del delivery fee", s["Section"]))
    story.append(Paragraph(
        "El primer envio en todas las plataformas suele ser gratuito, lo que hace que el delivery fee capturado "
        "no sea representativo del costo real que paga un usuario recurrente. Para que el total estimado tenga "
        "mayor validez, se estandarizo un delivery fee de $15 MXN cuando el scraper detecta $0. Esto permite "
        "comparaciones mas realistas entre plataformas.",
        s["Body"]
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("3.4 Extraccion de texto vs selectores CSS", s["Section"]))
    story.append(Paragraph(
        "Se opto por una estrategia de extraccion basada en <i>document.body.innerText</i> (texto plano de toda "
        "la pagina) en lugar de selectores CSS especificos. Esta decision se baso en que los selectores CSS de "
        "Rappi y Uber Eats estan ofuscados y cambian frecuentemente, mientras que el texto visible al usuario "
        "es estable. Se implemento una ventana forward-only de 4 lineas para evitar capturar precios de productos "
        "adyacentes.",
        s["Body"]
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("3.5 Decisiones en el analisis", s["Section"]))
    analysis_decisions = [
        "<b>Exclusion de datos invalidos:</b> Las metricas solo consideran registros con status=success y "
        "restaurant_available=True para no sesgar promedios con datos incompletos.",
        "<b>Glosario en PDF y dashboard:</b> Todos los terminos y abreviaciones (ETA, SLA, BM, HDQ, CC, etc.) "
        "se explican al inicio del documento para que los equipos de Strategy y Pricing puedan interpretar "
        "los graficos sin ambiguedad.",
        "<b>Interpretaciones por grafico:</b> Cada uno de los 14 graficos incluye una explicacion de que muestra "
        "y por que es relevante para la toma de decisiones, pensando en que los usuarios finales son equipos "
        "no tecnicos.",
        "<b>Comparacion Wealthy vs Non Wealthy:</b> Se agrego un analisis especifico de variabilidad "
        "socioeconomica porque la competitividad de precios y ETA puede variar significativamente entre zonas "
        "de alto y bajo poder adquisitivo, lo cual tiene implicaciones directas para estrategia de expansion.",
        "<b>3 productos como benchmark:</b> Se eligieron Combo Big Mac Mediano, Hamburguesa Doble con Queso y "
        "Coca-Cola Mediana porque son productos estandarizados disponibles en todas las plataformas, lo que "
        "permite comparacion directa sin sesgos de disponibilidad.",
    ]
    for b in analysis_decisions:
        story.append(Paragraph(f"\u2022 {b}", s["Bullet"]))

    # =========================================================================
    # 4. ARQUITECTURA
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("4. Arquitectura del sistema", s["TitleSmall"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    story.append(Paragraph(
        "El sistema sigue un pipeline de 3 etapas que puede ejecutarse de forma completa con un solo comando "
        "(<i>python main.py</i>) o modulo por modulo:",
        s["Body"]
    ))

    arch_data = [
        ["Etapa", "Modulo", "Input", "Output"],
        ["1. Recoleccion", "competitive_scraper.py", "25 direcciones configuradas", "CSV + JSON + screenshots"],
        ["2. Analisis", "generate_analysis.py + insights_utils.py", "CSV de datos", "14 charts PNG + kpis.json + top_insights.json"],
        ["3. Presentacion", "generate_report_pdf.py + ci_dashboard.html", "JSON de KPIs + charts", "PDF ejecutivo + dashboard HTML"],
    ]
    story.append(make_table(arch_data))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Stack tecnologico:", s["SubSection"]))
    stack_data = [
        ["Componente", "Tecnologia", "Justificacion"],
        ["Scraping", "Playwright (Python)", "Soporte para SPA, emulacion mobile, anti-detection"],
        ["Datos", "pandas + numpy", "Manipulacion eficiente de datos tabulares"],
        ["Charts estaticos", "matplotlib", "Graficos de alta calidad para PDF"],
        ["Charts interactivos", "Chart.js (HTML)", "Dashboard sin backend, autocontenido"],
        ["PDF", "reportlab", "Control total del layout ejecutivo"],
        ["Pipeline", "main.py (subprocess)", "Orquestacion simple sin dependencias externas"],
    ]
    story.append(make_table(stack_data))

    # =========================================================================
    # 5. PRINCIPALES HALLAZGOS
    # =========================================================================
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("5. Principales hallazgos del analisis", s["TitleSmall"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    story.append(Paragraph(
        "Los siguientes son los 5 insights accionables generados automaticamente por el sistema a partir "
        "de los datos recolectados:",
        s["Body"]
    ))
    story.append(Spacer(1, 0.2 * cm))

    insights = [
        {
            "title": "Posicionamiento de precios",
            "finding": "Rappi promedia $291 MXN en total estimado vs Uber Eats en $240 MXN — una brecha del 21%.",
            "impact": "El precio total percibido define la eleccion de plataforma; una brecha >5% desplaza market share.",
            "rec": "Evaluar subsidios tacticos en zonas de alta elasticidad o remover delivery fee en horarios pico.",
        },
        {
            "title": "Ventaja operacional",
            "finding": "Uber Eats lidera en velocidad (16 min promedio) y rating (4.5). DiDi Food promete 31 min.",
            "impact": "Cada 5 minutos adicionales de ETA reduce la conversion ~3-4 puntos porcentuales.",
            "rec": "Reforzar flota en zonas con ETA alto y lanzar campana de reviews para cerrar brecha de percepcion.",
        },
        {
            "title": "Estrategia promocional",
            "finding": "Rappi comunica hooks de 49% en promedio — la mas agresiva. DiDi aplica 43% de descuento real en Big Mac.",
            "impact": "La visibilidad del descuento en el feed es el driver #1 de click-through rate (CTR).",
            "rec": "Armar playbook de promos por zona prioritaria; calendarizar ventanas de empuje donde la competencia es mas agresiva.",
        },
        {
            "title": "Estructura de fees",
            "finding": "DiDi Food tiene el service fee mas bajo (8%) y Uber Eats el mas alto (15%). El delivery fee de DiDi varia mas por zona.",
            "impact": "El usuario percibe el costo total; aun con precios de producto iguales, un fee mas alto destruye la propuesta de valor.",
            "rec": "Definir reglas de subsidio de delivery fee por zona y monitorear competencia en checkout.",
        },
        {
            "title": "Variabilidad geografica",
            "finding": "Rappi es $65 MXN mas caro en zonas Non Wealthy vs Wealthy, la mayor brecha entre las 3 plataformas.",
            "impact": "Las zonas de expansion pagan mas, lo que cede share donde se necesita crecer.",
            "rec": "Redisenar tabla de delivery/service fee por segmento socioeconomico; monitorear periferia.",
        },
    ]

    for idx, ins in enumerate(insights, 1):
        elements = [
            Paragraph(f"<b>Insight {idx}: {ins['title']}</b>", s["SubSection"]),
            Paragraph(f"<b>Finding:</b> {ins['finding']}", s["Body"]),
            Paragraph(f"<b>Impacto:</b> {ins['impact']}", s["Body"]),
            Paragraph(f"<b>Recomendacion:</b> {ins['rec']}", s["Body"]),
            Spacer(1, 0.15 * cm),
        ]
        story.append(KeepTogether(elements))

    # =========================================================================
    # 6. LIMITACIONES Y PROXIMOS PASOS
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("6. Limitaciones y proximos pasos", s["TitleSmall"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    story.append(Paragraph("6.1 Limitaciones actuales", s["Section"]))
    limitations = [
        "<b>DiDi Food no automatizado:</b> La verificacion por SMS y la variabilidad del flujo de UI impidieron "
        "la automatizacion completa. Los datos se recolectaron manualmente como solucion temporal.",
        "<b>Service fee estimado:</b> Sin acceso autenticado al checkout, el service fee se estima con tasas fijas. "
        "Los valores reales pueden variar.",
        "<b>Delivery fee del primer pedido:</b> El primer envio suele ser gratis, lo que no refleja el costo real "
        "para usuarios recurrentes. Se estandarizo a $15 MXN.",
        "<b>Snapshot temporal:</b> Los datos representan un momento especifico. Precios, ETAs y promociones varian "
        "por hora y dia de la semana.",
        "<b>Uber Eats Cloudflare:</b> Para scraping intensivo y recurrente, Uber Eats puede requerir proxies "
        "residenciales para evitar bloqueos.",
    ]
    for b in limitations:
        story.append(Paragraph(f"\u2022 {b}", s["Bullet"]))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("6.2 Proximos pasos con mas tiempo", s["Section"]))
    story.append(Paragraph(
        "Con tiempo adicional, las siguientes mejoras fortalecerian significativamente el sistema:",
        s["Body"]
    ))

    next_steps = [
        "<b>Completar automatizacion de DiDi Food:</b> Iterar sobre el manejo de sesion persistente para "
        "evitar el OTP repetido, y entrenar el scraper para manejar las variaciones de UI entre direcciones. "
        "El framework ya esta construido (emulacion mobile, navegacion al feed, busqueda); falta estabilizar "
        "el flujo post-login para las 25 direcciones.",
        "<b>Extraer review count:</b> Agregar al scraper la extraccion del numero de resenas que aparece junto "
        "al rating (ej: '4.5 (2,300+ opiniones)'). Con esta metrica se puede ponderar el rating por volumen "
        "de votos, inferir cuantos usuarios usan cada plataforma para ese restaurante, y comparar la "
        "representatividad del rating entre apps.",
        "<b>Extraer resenas textuales:</b> Capturar los textos de las resenas permitiria analizar con NLP "
        "las criticas al restaurante, comparar si los problemas (empaque, tiempos, temperatura) son los mismos "
        "entre plataformas o especificos de cada app.",
        "<b>Verticales adicionales:</b> En la branch <i>feature/verticales-wip</i> hay un avance para expandir "
        "el scraper a farmacia y supermercado. Para Rappi ya funciona; Uber Eats requiere iteracion adicional. "
        "Con unos dias mas de desarrollo, se podria cubrir el bonus de multiples verticales.",
        "<b>Automatizacion recurrente:</b> Configurar ejecucion periodica (cron/GitHub Actions) para construir "
        "series temporales y detectar cambios en estrategia de precios de la competencia.",
        "<b>Service fee real:</b> Implementar autenticacion persistente en las 3 plataformas para capturar "
        "el service fee real del checkout, eliminando la necesidad de estimacion.",
    ]
    for b in next_steps:
        story.append(Paragraph(f"\u2022 {b}", s["Bullet"]))

    # =========================================================================
    # 7. COMO REPRODUCIR
    # =========================================================================
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("7. Como reproducir los resultados", s["TitleSmall"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_RED, spaceAfter=8))

    story.append(Paragraph("Para regenerar el analisis completo:", s["Body"]))
    steps = [
        "Instalar dependencias: <i>pip install -r requirements.txt</i> y <i>playwright install chromium</i>",
        "Desde la carpeta <i>analysis/</i>, ejecutar: <i>python generate_analysis.py --source ../data/competitive_data_with_didi.csv</i>",
        "Generar el PDF ejecutivo: <i>python generate_report_pdf.py</i>",
        "Para el dashboard: abrir <i>dashboard/ci_dashboard.html</i> en el navegador y cargar <i>data/competitive_data_with_didi.csv</i>",
    ]
    for i, step in enumerate(steps, 1):
        story.append(Paragraph(f"<b>{i}.</b> {step}", s["Bullet"]))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Para ejecutar el scraper real:", s["Body"]))
    scraper_steps = [
        "Desde la raiz del repo: <i>python main.py --real --visible</i> (25 direcciones, browser visible)",
        "Para una prueba rapida: <i>python main.py --real --city cdmx --max-addresses 3 --visible</i>",
        "Los datos crudos se guardan en <i>data/</i> y las capturas en <i>screenshots/</i>",
        "Para ver solo los datos del scraping automatico (sin DiDi manual): revisar <i>data/competitive_data_RAW.csv</i>",
    ]
    for i, step in enumerate(scraper_steps, 1):
        story.append(Paragraph(f"<b>{i}.</b> {step}", s["Bullet"]))

    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=2 * cm,
    )
    story = build_story(styles)
    doc.build(story, onFirstPage=cover_page, canvasmaker=NumberedCanvas)
    print(f"[OK] Informe generado -> {OUTPUT}")


if __name__ == "__main__":
    main()
