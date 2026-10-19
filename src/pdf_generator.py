"""Informe PDF de aptitud de suelos (ReportLab), con la disposición del informe de ejemplo.

Toma del informe de la EEAOC (ejemplo Pawnee, elaborado por AGQ) el bloque de
identificación, los títulos de sección en banda, la tabla de resultados con la
escala Muy Bajo..Muy Alto y el pie con nota legal y firma. Se limita a las 4
variables aprobadas: no agrega parámetros ni rangos que la EEAOC no haya definido.
"""
from __future__ import annotations

import io
import os
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from src import grafico
from src.evaluator import Evaluacion

VERDE_OSC = colors.HexColor("#1b4332")
VERDE = colors.HexColor("#2d6a4f")
GRIS_BORDE = colors.HexColor("#d1d5db")
GRIS_FONDO = colors.HexColor("#f5f6f7")
TINTA = colors.HexColor("#1f2933")
TINTA_2 = colors.HexColor("#52606d")
COLOR_ESTADO = {k: colors.HexColor(v) for k, v in grafico.COLOR.items()}

# --- equivalencia entre los niveles de la EEAOC y las 5 columnas del informe de ejemplo ---
ESCALA_5 = ("Muy Bajo", "Bajo", "Normal", "Alto", "Muy Alto")
# orden ascendente de cada variable -> columna de la escala de 5
INDICE_5 = {
    "mo": ("Bajo", "Normal", "Alto"),
    "fosforo": ("Bajo", "Normal", "Alto", "Muy Alto"),
    "ce": ("Normal", "Alto", "Muy Alto"),
}
# pH: la escala de la EEAOC no es de 5 niveles; se ubica cada clase sobre un gradiente
# de acidez a alcalinidad y se marca la columna más cercana a esa posición.
INDICE_PH = {
    "Ultra ácido": 0, "Extremadamente ácido": 0, "Muy fuertemente ácido": 1,
    "Fuertemente ácido": 1, "Moderadamente ácido": 2, "Ligeramente ácido": 2,
    "Neutro": 2, "Ligeramente alcalino": 3, "Moderadamente alcalino": 3,
    "Fuertemente alcalino": 4, "Muy fuertemente alcalino": 4,
}
FIRMA_NOMBRE = "Ing. Agr. MSc. Francisco A. Sosa"
FIRMA_CARGO = "Jefe de Sección Suelos y Nutrición Vegetal"
NOTA_LEGAL = ("Los resultados corresponden únicamente a la muestra analizada tal como fue recibida. "
              "Queda prohibida la reproducción parcial de este informe sin la aprobación por escrito de la EEAOC.")


def columna_5(clave: str, nivel: str, orden: int) -> int | None:
    """Columna (0..4) de la escala Muy Bajo..Muy Alto que corresponde al nivel obtenido.

    Devuelve None si el valor no clasificó (nivel 'Sin clasificar' o 'Sin dato').
    """
    if orden <= 0:
        return None
    if clave == "ph":
        return INDICE_PH.get(nivel)
    escala = INDICE_5.get(clave)
    return None if escala is None or orden > len(escala) else orden - 1


def _estilos():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=TINTA)
    return {
        "titulo": ParagraphStyle("titulo", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=17,
                                 textColor=VERDE_OSC, alignment=1),
        "sub": ParagraphStyle("sub", parent=base, fontSize=9, textColor=TINTA_2, alignment=1),
        "seccion": ParagraphStyle("seccion", parent=base, fontName="Helvetica-Bold", fontSize=11, leading=14,
                                  textColor=VERDE, spaceBefore=6, spaceAfter=4),
        "base": base,
        "chico": ParagraphStyle("chico", parent=base, fontSize=8, leading=10, textColor=TINTA_2),
        "th": ParagraphStyle("th", parent=base, fontName="Helvetica-Bold", textColor=colors.white),
        "aviso": ParagraphStyle("aviso", parent=base, fontSize=8.5, leading=11, textColor=colors.HexColor("#7a4b00")),
        "pend": ParagraphStyle("pend", parent=base, fontName="Helvetica-Oblique", textColor=TINTA_2),
    }


def _fmt(v):
    return "—" if v is None else f"{v:g}".replace(".", ",")


class PDFReportGenerator:
    def __init__(self, filename: str | Path = "informe_suelo_eeaoc.pdf"):
        self.filename = str(filename)

    def generar_informe(self, ev: Evaluacion, output_path: str | Path | None = None) -> str:
        path = str(output_path or self.filename)
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.generar_bytes(ev))
        return path

    def generar_bytes(self, ev: Evaluacion) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                                topMargin=12 * mm, bottomMargin=18 * mm,
                                title=f"Informe de aptitud de suelo - {ev.muestra.identificacion}",
                                author="EEAOC - Sección Suelos y Nutrición Vegetal")
        doc.build(self._contenido(ev, doc.width), onFirstPage=self._pie, onLaterPages=self._pie)
        return buf.getvalue()

    # ------------------------------------------------------------------
    def _pie(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(TINTA_2)
        canvas.drawString(16 * mm, 12 * mm, "Clasificación según los valores de referencia de la Sección Suelos y Nutrición Vegetal "
                                            "de la EEAOC para el cultivo indicado.")
        canvas.drawString(16 * mm, 9 * mm, "Los resultados corresponden únicamente a la muestra analizada.")
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Página {doc.page}")
        canvas.setStrokeColor(GRIS_BORDE)
        canvas.line(16 * mm, 26 * mm, A4[0] - 16 * mm, 26 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(VERDE_OSC)
        canvas.drawCentredString(A4[0] - 45 * mm, 20 * mm, FIRMA_NOMBRE)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(TINTA_2)
        canvas.drawCentredString(A4[0] - 45 * mm, 17 * mm, FIRMA_CARGO)
        canvas.restoreState()

    def _contenido(self, ev: Evaluacion, ancho: float) -> list:
        e = _estilos()
        m = ev.muestra
        story = [
            Paragraph("ESTACIÓN EXPERIMENTAL AGROINDUSTRIAL OBISPO COLOMBRES", e["titulo"]),
            Paragraph("Sección Suelos y Nutrición Vegetal — Informe de aptitud de suelo", e["sub"]),
            Spacer(1, 4),
            HRFlowable(width="100%", thickness=1.2, color=VERDE, spaceAfter=8),
        ]

        pendientes = sum(1 for r in ev.resultados if r.valor is not None and not r.recomendacion_validada)
        if pendientes:
            banda = Table([[Paragraph(
                "<b>Versión de prueba.</b> Este informe usa criterios que todavía están en validación con la EEAOC "
                f"({pendientes} {'recomendación' if pendientes == 1 else 'recomendaciones'} sin definir). No entregar al productor.",
                e["aviso"])]], colWidths=[ancho])
            banda.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff6e0")),
                                       ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#fab219")),
                                       ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
            story += [banda, Spacer(1, 8)]

        # Identificación
        def celda(et, val):
            return Paragraph(f"<font color='#52606d'>{et}</font><br/><b>{val or '—'}</b>", e["base"])
        ident = Table([
            [celda("Identificación de la muestra", m.identificacion), celda("Cultivo", ev.cultivo),
             celda("Tipo de muestra", "Suelo agrícola")],
            [celda("Profundidad / Descripción", m.profundidad), celda("Fecha de muestreo", m.fecha),
             celda("Fecha de emisión", date.today().strftime("%d/%m/%Y"))],
            [celda("Laboratorio", "EEAOC · Sección Suelos y Nutrición Vegetal"), celda("Cliente", m.cliente),
             celda("Establecimiento / Lugar", m.lugar)],
        ], colWidths=[ancho / 3] * 3)
        ident.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
                                   ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                                   ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                                   ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
        story += [Paragraph("Identificación de la muestra", e["seccion"]), ident]

        # Resumen + gráfico
        story += [Paragraph("Diagnóstico", e["seccion"]), Paragraph(ev.resumen, e["base"]), Spacer(1, 4)]
        png = grafico.png(ev, dpi=220, ancho_pulg=7.2)
        alto_pulg = grafico.ALTO_FILA * len(ev.resultados) + 0.15
        alto = ancho * alto_pulg / 7.2 * 0.50          # gráfico más chico para entrar en una página
        story.append(Image(io.BytesIO(png), width=ancho, height=alto))

        # Tabla de resultados con la escala Muy Bajo..Muy Alto del informe de ejemplo
        story += [Paragraph("Resultados", e["seccion"]), self._tabla_escala(ev, ancho, e), Spacer(1, 6)]

        # Detalle por variable: escala real de la EEAOC, estado y recomendación
        story += [Paragraph("Detalle por variable", e["seccion"]), self._tabla_detalle(ev, ancho, e)]

        if ev.avisos:
            story.append(Paragraph("Avisos para revisión técnica", e["seccion"]))
            for a in ev.avisos:
                story.append(Paragraph(f"• {a}", e["aviso"]))
        if m.observaciones:
            story += [Paragraph("Observaciones", e["seccion"]), Paragraph(m.observaciones, e["base"])]

        story += [Spacer(1, 4), Paragraph(NOTA_LEGAL, e["chico"])]
        return story

    # ------------------------------------------------------------------
    def _tabla_escala(self, ev: Evaluacion, ancho: float, e: dict) -> Table:
        """Tabla Parámetro · Resultado · Unidad · Muy Bajo..Muy Alto (marca el nivel obtenido).

        Es la vista equivalente a la del informe de ejemplo. La columna marcada es una
        equivalencia de los niveles de la EEAOC a esas cinco bandas, no un rango nuevo.
        """
        filas = [[Paragraph(t, e["th"]) for t in ("Parámetro", "Resultado", "Unidad", *ESCALA_5, "Método")]]
        estilo = [("BACKGROUND", (0, 0), (-1, 0), VERDE),
                  ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE), ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (3, 1), (7, -1), "CENTER"),
                  ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        for i, r in enumerate(ev.resultados, 1):
            col = columna_5(r.clave, r.nivel, r.orden)
            filas.append([Paragraph(r.nombre, e["base"]), Paragraph(f"<b>{_fmt(r.valor)}</b>", e["base"]),
                          Paragraph(r.unidad, e["base"])]
                         + [Paragraph(f"<b>{ESCALA_5[k]}</b>" if k == col else ESCALA_5[k], e["base"])
                            for k in range(len(ESCALA_5))]
                         + [Paragraph("EEAOC", e["chico"])])
            if col is not None:                       # celda marcada sobre fondo tenue del estado
                tenue = colors.HexColor(grafico.COLOR[r.estado])
                estilo += [("BACKGROUND", (3 + col, i), (3 + col, i), tenue),
                           ("LINEBEFORE", (3 + col, i), (3 + col, i), 0.5, VERDE),
                           ("LINEAFTER", (3 + col, i), (3 + col, i), 0.5, VERDE)]
        tabla = Table(filas, colWidths=[ancho * f for f in (0.24, 0.12, 0.11, 0.09, 0.09, 0.09, 0.09, 0.09, 0.08)],
                      repeatRows=1)
        tabla.setStyle(TableStyle(estilo))
        return tabla

    def _tabla_detalle(self, ev: Evaluacion, ancho: float, e: dict) -> Table:
        """Escala real de la EEAOC por variable (niveles propios) y estado obtenido."""
        filas = [[Paragraph(t, e["th"]) for t in ("Variable", "Nivel (escala EEAOC)", "Estado", "Recomendación")]]
        estilo = [("BACKGROUND", (0, 0), (-1, 0), VERDE),
                  ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE), ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        for i, r in enumerate(ev.resultados, 1):
            est = e["base"] if r.recomendacion_validada else e["pend"]
            filas.append([Paragraph(r.nombre, e["base"]), Paragraph(f"<b>{r.nivel}</b>", e["base"]),
                          Paragraph(grafico.ETIQUETA[r.estado], e["base"]), Paragraph(r.recomendacion, est)])
            estilo.append(("LINEBEFORE", (2, i), (2, i), 4, COLOR_ESTADO[r.estado]))
        tabla = Table(filas, colWidths=[ancho * f for f in (0.26, 0.22, 0.14, 0.38)], repeatRows=1)
        tabla.setStyle(TableStyle(estilo))
        return tabla
