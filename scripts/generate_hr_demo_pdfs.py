#!/usr/bin/env python3
"""Generate fictional HR PDFs used by the local recruiting/payroll demo."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "platform_api"))

from app.config import Settings  # noqa: E402
from app.people import PeopleService  # noqa: E402
from app.store import ScenarioStore  # noqa: E402


def generate_candidate_profile(target: Path) -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleBlue",
        parent=styles["Title"],
        textColor=colors.HexColor("#173f5f"),
        fontSize=22,
        leading=26,
    )
    heading = ParagraphStyle(
        "HeadingBlue",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#173f5f"),
        fontSize=12,
        leading=15,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    )
    normal = styles["BodyText"]
    normal.fontSize = 9.5
    normal.leading = 13
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Bewerbungsprofil Lea Muster - FIKTIVE DEMODATEN",
        author="Open Manufacturing Demo GmbH",
    )
    story = [
        Paragraph("Bewerbungsprofil", title),
        Paragraph("Lea Muster · APP-0001 · FIKTIVE DEMODATEN", styles["Heading3"]),
        Spacer(1, 3 * mm),
        Table(
            [
                ["Bewerbung auf", "Mechatroniker/in Produktion"],
                ["Eingang", "22.10.2026 über Karriereseite"],
                ["Kontakt", "lea.muster@example.invalid · +49 30 5550101"],
                ["Aktuelle Phase", "Gespräch"],
            ],
            colWidths=[42 * mm, 120 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eef2")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cad2d8")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
        Paragraph("Kurzprofil", heading),
        Paragraph(
            "Fiktive Bewerberin mit Ausbildung im Bereich Mechatronik und drei Jahren "
            "Erfahrung in Montage, elektrischer Prüfung und strukturierter "
            "Fertigungsdokumentation. Dieses Dokument enthält ausschließlich "
            "Demodaten und darf nicht als echte Bewerbung verwendet werden.",
            normal,
        ),
        Paragraph("Qualifikationen", heading),
        Paragraph(
            "• Montage elektromechanischer Baugruppen<br/>"
            "• Lesen technischer Zeichnungen und Arbeitsanweisungen<br/>"
            "• Sicht- und Funktionsprüfung mit digitaler Rückmeldung<br/>"
            "• Grundkenntnisse ERP/MES und Seriennummernverfolgung",
            normal,
        ),
        Paragraph("Prozess- und Datenschutzhinweis", heading),
        Paragraph(
            "Zugriff: DMS-Bereich-HR-Recruiting. Die Bewerbung wird nach Abschluss "
            "entsprechend der hinterlegten Aufbewahrungsregel geprüft und gelöscht "
            "oder bei dokumentierter Rechtsgrundlage gesperrt aufbewahrt. Download "
            "und Weitergabe außerhalb des Recruiting-Prozesses sind nicht vorgesehen.",
            normal,
        ),
        Spacer(1, 10 * mm),
        Paragraph(
            "FIKTIVE DEMODATEN · Bewerberakte APP-0001 · Stand 30.10.2026",
            ParagraphStyle(
                "Notice",
                parent=normal,
                textColor=colors.HexColor("#8a3b12"),
                backColor=colors.HexColor("#fff1e8"),
                borderPadding=8,
                borderColor=colors.HexColor("#e0a47f"),
                borderWidth=0.6,
            ),
        ),
    ]
    doc.build(story)


def generate_sample_payslip(target: Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        settings = Settings(
            data_file=temp / "scenario.json",
            seed_file=ROOT / "services/platform_api/seed/scenario.json",
        )
        service = PeopleService(ScenarioStore(settings.data_file, settings.seed_file), settings)
        preview = service.prepare_payroll("PAY-2026-10", "HR-USER-001")
        run = service.approve_payroll(
            "PAY-2026-10", "HR-USER-002", preview["token"]
        )["run"]
        target.write_bytes(
            service.payslip_pdf(run["id"], "DEMO-EMP-001", "HR-USER-001")
        )


def main() -> None:
    output = ROOT / "output" / "pdf"
    output.mkdir(parents=True, exist_ok=True)
    generate_candidate_profile(output / "Bewerbung_APP-0001_Lea-Muster.pdf")
    generate_sample_payslip(
        output / "Entgeltabrechnung_PAY-2026-10_DEMO-EMP-001.pdf"
    )
    print("Generated 2 fictional HR demo PDFs")


if __name__ == "__main__":
    main()
