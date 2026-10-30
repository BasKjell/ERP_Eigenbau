#!/usr/bin/env python3
"""Generate polished, deterministic PDF fixtures for the Paperless demo."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#102126")
TEAL = colors.HexColor("#0D756C")
LIME = colors.HexColor("#C8F04A")
PAPER = colors.HexColor("#F4F2EB")
MUTED = colors.HexColor("#66767A")
LINE = colors.HexColor("#D7DAD4")
ORANGE = colors.HexColor("#F07A3A")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=7 * mm,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=TEAL,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=INK,
            spaceAfter=2.5 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=TEAL,
            tracking=1.2,
            uppercase=True,
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=INK,
            alignment=TA_CENTER,
        ),
    }


STYLES = styles()


def header_footer(canvas: Canvas, doc: BaseDocTemplate) -> None:
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFillColor(INK)
    canvas.rect(0, height - 17 * mm, width, 17 * mm, fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.rect(14 * mm, height - 12 * mm, 5 * mm, 5 * mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(23 * mm, height - 10.5 * mm, "OPEN MANUFACTURING")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - 14 * mm, height - 10.5 * mm, doc.subject)
    canvas.setStrokeColor(LINE)
    canvas.line(14 * mm, 14 * mm, width - 14 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(14 * mm, 9 * mm, "Management-PoC - kontrolliertes Beispieldokument")
    canvas.drawRightString(width - 14 * mm, 9 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def document(path: Path, subject: str, page_size=A4) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        str(path),
        pagesize=page_size,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=25 * mm,
        bottomMargin=19 * mm,
        title=subject,
        author="Open Manufacturing Demo",
        subject=subject,
    )
    width, height = page_size
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="branded", frames=frame, onPage=header_footer))
    return doc


def meta_table(rows: list[tuple[str, str]]) -> Table:
    data = [
        [Paragraph(key.upper(), STYLES["label"]), Paragraph(value, STYLES["body"])]
        for key, value in rows
    ]
    table = Table(data, colWidths=[40 * mm, 120 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PAPER),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ]
        )
    )
    return table


def data_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[Paragraph(h, STYLES["label"]) for h in headers]]
    data.extend([[Paragraph(str(value), STYLES["body"]) for value in row] for row in rows])
    table = Table(data, colWidths=[width * mm for width in widths], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ]
        )
    )
    return table


def approval_box() -> Table:
    table = Table(
        [
            [
                Paragraph("ERSTELLT", STYLES["label"]),
                Paragraph("GEPRUEFT", STYLES["label"]),
                Paragraph("FREIGEGEBEN", STYLES["label"]),
            ],
            [
                Paragraph("Engineering / 24.10.2026", STYLES["small"]),
                Paragraph("Quality / 27.10.2026", STYLES["small"]),
                Paragraph("Head of Operations / 28.10.2026", STYLES["small"]),
            ],
        ],
        colWidths=[53 * mm] * 3,
    )
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, TEAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), PAPER),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return table


def draw_technical(path: Path) -> None:
    page = landscape(A4)
    width, height = page
    canvas = Canvas(str(path), pagesize=page)
    canvas.setTitle("Technische Zeichnung SCU-100 Revision C")
    canvas.setAuthor("Open Manufacturing Demo")
    canvas.setFillColor(INK)
    canvas.rect(0, height - 18 * mm, width, 18 * mm, fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.rect(14 * mm, height - 13 * mm, 5 * mm, 5 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(24 * mm, height - 11.5 * mm, "SCU-100 - TECHNISCHE ZEICHNUNG")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 14 * mm, height - 11.5 * mm, "REVISION C / FREIGEGEBEN")

    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1.2)
    x, y, w, h = 34 * mm, 72 * mm, 150 * mm, 78 * mm
    canvas.roundRect(x, y, w, h, 4 * mm, fill=0, stroke=1)
    canvas.setStrokeColor(TEAL)
    canvas.rect(x + 13 * mm, y + 13 * mm, 88 * mm, 52 * mm, fill=0, stroke=1)
    canvas.setFillColor(PAPER)
    canvas.rect(x + 17 * mm, y + 17 * mm, 80 * mm, 44 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(INK)
    for px in (x + 120 * mm, x + 137 * mm):
        for py in (y + 23 * mm, y + 52 * mm):
            canvas.circle(px, py, 6 * mm, fill=0, stroke=1)
            canvas.circle(px, py, 2 * mm, fill=0, stroke=1)

    # Dimension lines
    canvas.setLineWidth(0.5)
    canvas.line(x, y - 12 * mm, x + w, y - 12 * mm)
    canvas.line(x, y - 15 * mm, x, y - 8 * mm)
    canvas.line(x + w, y - 15 * mm, x + w, y - 8 * mm)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(x + w / 2, y - 10 * mm, "320.0 +/- 0.5 mm")
    canvas.line(x - 13 * mm, y, x - 13 * mm, y + h)
    canvas.line(x - 16 * mm, y, x - 9 * mm, y)
    canvas.line(x - 16 * mm, y + h, x - 9 * mm, y + h)
    canvas.saveState()
    canvas.translate(x - 15 * mm, y + h / 2)
    canvas.rotate(90)
    canvas.drawCentredString(0, 0, "180.0 +/- 0.5 mm")
    canvas.restoreState()

    # Side view
    sx, sy = 205 * mm, 102 * mm
    canvas.setStrokeColor(INK)
    canvas.rect(sx, sy, 60 * mm, 35 * mm, fill=0, stroke=1)
    canvas.line(sx, sy - 10 * mm, sx + 60 * mm, sy - 10 * mm)
    canvas.drawCentredString(sx + 30 * mm, sy - 8 * mm, "Tiefe 72.0 +/- 0.5 mm")

    notes = [
        ["1", "Gehäuse: Aluminium EN AW-5754, pulverbeschichtet RAL 7016"],
        ["2", "Schutzart im montierten Zustand: IP54"],
        ["3", "Kanten entgraten; sichtbare Flächen frei von Kratzern"],
        ["4", "M12-Anschlüsse mit 1.5 Nm anziehen"],
    ]
    table = data_table(["NR", "TECHNISCHE HINWEISE"], notes, [13, 76])
    table.wrapOn(canvas, 90 * mm, 55 * mm)
    table.drawOn(canvas, 195 * mm, 27 * mm)

    canvas.setStrokeColor(INK)
    canvas.rect(14 * mm, 14 * mm, 174 * mm, 38 * mm, fill=0, stroke=1)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(18 * mm, 43 * mm, "SCU-100 / SONAR CONTROL UNIT")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 35 * mm, "Dokument: DRW-SCU-100-C")
    canvas.drawString(18 * mm, 29 * mm, "Massstab: 1:2    Einheit: mm    Blatt: 1/1")
    canvas.drawString(18 * mm, 23 * mm, "Status: FREIGEGEBEN    Datum: 28.10.2026")
    canvas.setFillColor(TEAL)
    canvas.rect(158 * mm, 14 * mm, 30 * mm, 38 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawCentredString(173 * mm, 29 * mm, "C")
    canvas.save()


def build_assembly(path: Path) -> None:
    doc = document(path, "Montageanweisung SCU-100 Revision D")
    story = [
        Paragraph("Montageanweisung SCU-100", STYLES["title"]),
        meta_table(
            [
                ("Dokument", "WI-SCU-100-D"),
                ("Revision", "D / freigegeben"),
                ("Gueltig fuer", "SCU-100 Revision C"),
                ("Arbeitsgang", "Mechanische und elektrische Montage"),
            ]
        ),
        Paragraph("Sicherheit und Vorbereitung", STYLES["h2"]),
        Paragraph(
            "ESD-Arbeitsplatz pruefen, persoenliches ESD-Band anlegen und Arbeitsbereich freigeben. Seriennummer sowie WO-2027-0042 scannen. Nur Bauteile der freigegebenen BOM-C verwenden.",
            STYLES["body"],
        ),
        Paragraph("Montagefolge", STYLES["h2"]),
        data_table(
            ["SCHRITT", "TAETIGKEIT", "PRUEFPUNKT"],
            [
                [
                    "10",
                    "Gehäuse auf Beschaedigung und richtige Revision pruefen.",
                    "CASE-100-C, ohne Kratzer",
                ],
                [
                    "20",
                    "Mainboard auf vier Abstandshalter setzen und kreuzweise befestigen.",
                    "0.8 Nm, Markierung sichtbar",
                ],
                [
                    "30",
                    "Netzteil einsetzen und Schutzleiter anschliessen.",
                    "PE-Verbindung < 0.1 Ohm",
                ],
                [
                    "40",
                    "Kabelsatz nach Verlegeplan anschliessen; J4 hoerbar verriegeln.",
                    "Zugprobe an J4",
                ],
                [
                    "50",
                    "Display-Modul montieren und Flachbandkabel verriegeln.",
                    "Keine Knick- oder Scheuerstelle",
                ],
                ["60", "M12-Steckverbinder einsetzen und abdichten.", "1.5 Nm"],
                [
                    "70",
                    "Sichtpruefung, Label und Seriennummer kontrollieren.",
                    "Zwei-Personen-Pruefung",
                ],
            ],
            [18, 91, 50],
        ),
        Spacer(1, 7 * mm),
        approval_box(),
        Paragraph("Rueckmeldung und Abweichung", STYLES["h2"]),
        Paragraph(
            "Ist-Zeit und Seriennummern auf der Job Card erfassen. Bei falscher Revision, fehlendem Teil, nicht erreichbarem Drehmoment oder sichtbarer Beschaedigung den Arbeitsgang stoppen und eine Abweichung anlegen. Fehler niemals durch Gutmeldung umgehen.",
            STYLES["body"],
        ),
    ]
    doc.build(story)


def build_test_plan(path: Path) -> None:
    doc = document(path, "Pruefplan SCU-100 Revision B")
    story = [
        Paragraph("Pruefplan SCU-100", STYLES["title"]),
        meta_table(
            [
                ("Dokument", "QP-SCU-100-B"),
                ("Revision", "B / freigegeben"),
                ("Pruefmittel", "PSU-24V-10A, DMM-42, CAN-TEST-7"),
                ("Aufzeichnung", "je Seriennummer; Aufbewahrung 10 Jahre (PoC-Annahme)"),
            ]
        ),
        Paragraph("Pruefumfang", STYLES["h2"]),
        data_table(
            ["NR", "MERKMAL", "SOLL / GRENZE", "REAKTION"],
            [
                [
                    "1",
                    "Identitaet / Revision",
                    "SCU-100 Rev. C; Label lesbar",
                    "Sperren bei Abweichung",
                ],
                ["2", "Schutzleiter", "Widerstand < 0.1 Ohm", "Major NCR"],
                ["3", "Versorgungsspannung", "24.0 V +/- 0.5 V", "Pruefaufbau kontrollieren"],
                ["4", "Stromaufnahme", "<= 2.0 A im Normalbetrieb", "Major NCR"],
                ["5", "Firmware", "Version 3.x; Signatur gueltig", "Firmware erneut laden"],
                ["6", "CAN-Kommunikation", "3 von 3 Telegrammen in 5 s", "J4 pruefen, dann NCR"],
                ["7", "Temperaturtest", "Selbsttest ohne Alarm", "Major NCR"],
                ["8", "Endsichtpruefung", "Keine Beschaedigung; Ports markiert", "Nacharbeit"],
            ],
            [11, 45, 55, 48],
        ),
        PageBreak(),
        Paragraph("Messwertprotokoll - Auftrag SO-4711", STYLES["h2"]),
        data_table(
            ["SERIENNUMMER", "SPANNUNG", "STROM", "CAN", "TEMP.", "STATUS"],
            [
                ["SN-10001", "24.1 V", "1.8 A", "3/3", "OK", "Freigegeben"],
                ["SN-10002", "24.0 V", "1.7 A", "3/3", "OK", "Freigegeben"],
                ["SN-10003", "24.1 V", "1.8 A", "3/3", "OK", "Freigegeben"],
                ["SN-10004", "24.1 V", "1.8 A", "0/3", "OK", "NCR-2027-0017"],
                ["SN-10005", "24.0 V", "1.8 A", "3/3", "OK", "Freigegeben"],
            ],
            [30, 25, 22, 20, 22, 39],
        ),
        Paragraph("Fehlerreaktion", STYLES["h2"]),
        Paragraph(
            "Bei nicht bestandenem Merkmal Seriennummer sofort sperren. Messwerte und Umgebungsbedingungen speichern, Major-Abweichung anlegen und den Fertigungsauftrag nicht fertigmelden. Nacharbeit dokumentieren und den vollstaendigen betroffenen Test wiederholen.",
            STYLES["body"],
        ),
        approval_box(),
    ]
    doc.build(story)


def build_certificate(path: Path) -> None:
    doc = document(path, "Lieferantenzertifikat Mainboard Charge BE-24117")
    story = [
        Paragraph("Certificate of Conformity", STYLES["title"]),
        Paragraph("BALTIC ELECTRONICS OY", STYLES["h2"]),
        Paragraph(
            "This document certifies that the listed products were manufactured and inspected in accordance with the purchase specification. This is a fictional sample certificate for the management demo.",
            STYLES["body"],
        ),
        meta_table(
            [
                ("Certificate", "COC-BE-24117"),
                ("Customer PO", "PO-2027-0088"),
                ("Part", "PCB-MAIN-42 / Mainboard SCU"),
                ("Lot", "BE-24117"),
                ("Quantity", "5"),
                ("Manufacturing date", "20.12.2026"),
            ]
        ),
        Paragraph("Inspection results", STYLES["h2"]),
        data_table(
            ["CHARACTERISTIC", "REQUIREMENT", "RESULT"],
            [
                ["Visual inspection", "No damage or contamination", "Pass"],
                ["Firmware blank check", "No customer firmware installed", "Pass"],
                ["Supply rail", "5.0 V +/- 0.1 V", "5.02 V mean"],
                ["Traceability", "Supplier lot on each board", "Pass"],
                ["RoHS declaration", "Supplier specification BE-Q-19", "Conform"],
            ],
            [65, 65, 30],
        ),
        Spacer(1, 3 * mm),
        KeepTogether(
            [
                Paragraph("Declaration", STYLES["h2"]),
                Paragraph("Authorized quality representative: Linnea Korhonen", STYLES["body"]),
                Paragraph("Digitally issued for demo purposes - 21.12.2026", STYLES["small"]),
            ]
        ),
    ]
    doc.build(story)


def build_acceptance(path: Path) -> None:
    doc = document(path, "Abnahmeprotokoll Auftrag 4711")
    story = [
        Paragraph("Abnahmeprotokoll Auftrag 4711", STYLES["title"]),
        meta_table(
            [
                ("Kunde", "NordMarine Systems GmbH"),
                ("Sales Order", "SO-4711"),
                ("Work Order", "WO-2027-0042"),
                ("Produkt", "SCU-100 Revision C"),
                ("Menge", "5 Stueck"),
                ("Status", "Entwurf - Freigabe nach Endpruefung"),
            ]
        ),
        Paragraph("Lieferumfang und Rueckverfolgbarkeit", STYLES["h2"]),
        data_table(
            ["SERIENNUMMER", "FUNKTIONSTEST", "ABWEICHUNG", "FREIGABE"],
            [
                ["SN-10001", "bestanden", "-", "Quality"],
                ["SN-10002", "bestanden", "-", "Quality"],
                ["SN-10003", "bestanden", "-", "Quality"],
                ["SN-10004", "Wiederholtest bestanden", "NCR-2027-0017 geschlossen", "Quality"],
                ["SN-10005", "bestanden", "-", "Quality"],
            ],
            [38, 52, 57, 23],
        ),
        PageBreak(),
        Paragraph("Mitgeltende Unterlagen", STYLES["h2"]),
        data_table(
            ["DOKUMENT", "REVISION", "DMS-REFERENZ"],
            [
                ["Technische Zeichnung SCU-100", "C", "DOC-DRW-100"],
                ["Montageanweisung SCU-100", "D", "DOC-WI-100"],
                ["Pruefplan SCU-100", "B", "DOC-QP-100"],
                ["Lieferantenzertifikat Mainboard", "BE-24117", "DOC-CERT-MB"],
            ],
            [78, 30, 50],
        ),
        Paragraph("Abnahmeerklaerung", STYLES["h2"]),
        Paragraph(
            "Die oben genannten Einheiten wurden nach dem vereinbarten Pruefplan geprueft. Die Abweichung an SN-10004 wurde nach dokumentierter Nacharbeit durch einen vollstaendigen Wiederholtest geschlossen. Dieses Beispieldokument besitzt keine rechtliche Wirkung.",
            STYLES["body"],
        ),
        Spacer(1, 8 * mm),
        approval_box(),
    ]
    doc.build(story)


GENERATORS: dict[str, tuple[str, Callable[[Path], None]]] = {
    "SCU-100_Technische_Zeichnung_Rev-C.pdf": ("Technische Zeichnung", draw_technical),
    "SCU-100_Montageanweisung_Rev-D.pdf": ("Montageanweisung", build_assembly),
    "SCU-100_Pruefplan_Rev-B.pdf": ("Pruefplan", build_test_plan),
    "Mainboard_Lieferantenzertifikat_BE-24117.pdf": ("Lieferantenzertifikat", build_certificate),
    "Auftrag-4711_Abnahmeprotokoll.pdf": ("Abnahmeprotokoll", build_acceptance),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output/pdf"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, (_, generator) in GENERATORS.items():
        generator(args.output / filename)
        print(args.output / filename)


if __name__ == "__main__":
    main()
