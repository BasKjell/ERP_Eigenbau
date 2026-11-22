"""FLOWDOC-Dateispeicher für Formate, die Paperless-ngx nicht verarbeitet (3D-Modelle STL).

Paperless prüft den Dateityp am Inhalt und weist binäre STL-Dateien (``application/octet-stream``)
ab. Deshalb gilt für solche Dateien:

- Die Originaldatei liegt unveränderlich unter ihrer SHA-256-Prüfsumme in einem eigenen Volume
  (inhaltsadressiert, nur lesbar; gleiche Datei = gleicher Ablageort, keine Dubletten).
- In FLOWDOC landet ein PDF-Begleitblatt mit Titel, Originalname, Größe und Prüfsumme. Suche,
  Status, Freigabe, Objektrechte und Aufbewahrung laufen damit weiter über Paperless.
- Heruntergeladen wird die Originaldatei nur über das Begleitblatt: Die Plattform liest es im Namen
  der angemeldeten Person (Paperless entscheidet über das Recht) und prüft die Datei beim Lesen
  erneut gegen die Prüfsumme.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import struct
from datetime import UTC, datetime
from pathlib import Path

MARKER = "FLOWDOC-Datei: sha256:"
NAME_MARKER = "Originaldatei: "
MARKER_PATTERN = re.compile(r"FLOWDOC-Datei:\s*sha256:\s*([0-9a-f]{64})")
NAME_PATTERN = re.compile(r"Originaldatei:\s*([^\r\n]{1,180}?\.stl)\b", re.IGNORECASE)
EXTERNAL_TYPES = {".stl": "3D-Modell (STL)"}


class FileStoreError(ValueError):
    """Datei ungültig oder Ablage nicht möglich."""


def inspect_stl(content: bytes) -> dict[str, object]:
    """Prüft, ob der Inhalt wirklich eine STL-Datei ist (binär oder ASCII)."""
    if len(content) >= 84:
        (triangles,) = struct.unpack_from("<I", content, 80)
        if 84 + 50 * triangles == len(content) and triangles > 0:
            return {"format": "binär", "triangles": int(triangles)}
    head = content[:512].lstrip().lower()
    if head.startswith(b"solid") and b"facet" in content[:65536].lower() and b"endsolid" in content[-4096:].lower():
        return {"format": "ASCII", "triangles": content.lower().count(b"endfacet")}
    raise FileStoreError("Die Datei ist kein gültiges STL-Modell (weder binär noch ASCII)")


class FileStore:
    """Inhaltsadressierte, unveränderliche Ablage unter <root>/<aa>/<sha256>.<endung>."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)

    def _path(self, digest: str, suffix: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or suffix not in EXTERNAL_TYPES:
            raise FileStoreError("Ungültige Prüfsumme oder Dateiendung")
        return self.root / digest[:2] / f"{digest}{suffix}"

    def put(self, content: bytes, suffix: str) -> str:
        digest = hashlib.sha256(content).hexdigest()
        target = self._path(digest, suffix)
        if target.exists():
            self.get(digest, suffix)  # vorhandene Ablage muss unversehrt sein
            return digest
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_bytes(content)
            os.chmod(temporary, 0o444)
            os.replace(temporary, target)
        except OSError as exc:
            raise FileStoreError(f"Dateiablage nicht möglich ({type(exc).__name__})") from None
        return digest

    def get(self, digest: str, suffix: str) -> bytes:
        target = self._path(digest, suffix)
        try:
            content = target.read_bytes()
        except FileNotFoundError:
            raise FileStoreError("Originaldatei nicht in der Ablage gefunden") from None
        if hashlib.sha256(content).hexdigest() != digest:
            raise FileStoreError("Originaldatei ist beschädigt (Prüfsumme stimmt nicht)")
        return content


def reference_in(content: str) -> dict[str, str] | None:
    """Liest Prüfsumme und Originalnamen aus dem erkannten Text eines Begleitblatts."""
    found = MARKER_PATTERN.search(content or "")
    if not found:
        return None
    name = NAME_PATTERN.search(content or "")
    clean = re.sub(r"[^A-Za-z0-9._ -]", "_", name.group(1)).strip() if name else f"{found.group(1)[:12]}.stl"
    return {"sha256": found.group(1), "name": clean, "suffix": ".stl"}


def cover_sheet(*, title: str, filename: str, digest: str, size: int, details: dict[str, object],
                uploaded_by: str) -> bytes:
    """PDF-Begleitblatt mit Textebene (Paperless liest den Text ohne Texterkennung)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    page.setTitle(title)
    page.setAuthor("FLOWDOC")
    width, height = A4
    y = height - 72
    page.setFont("Helvetica-Bold", 16)
    page.drawString(56, y, title[:80])
    y -= 22
    page.setFont("Helvetica", 10)
    page.drawString(56, y, "Begleitblatt zu einem 3D-Modell. Die Originaldatei liegt unveränderlich im FLOWDOC-Dateispeicher.")
    y -= 32
    rows = [
        ("Dateityp", EXTERNAL_TYPES[".stl"]),
        ("Format", str(details.get("format", ""))),
        ("Dreiecke", f"{int(details.get('triangles', 0)):,}".replace(",", ".")),
        ("Größe", f"{size:,} Byte".replace(",", ".")),
        ("Abgelegt von", uploaded_by),
        ("Abgelegt am", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")),
    ]
    for label, value in rows:
        page.setFont("Helvetica-Bold", 10)
        page.drawString(56, y, f"{label}:")
        page.setFont("Helvetica", 10)
        page.drawString(160, y, value[:90])
        y -= 16
    y -= 16
    page.setFont("Courier", 8.5)
    page.drawString(56, y, f"{NAME_MARKER}{filename[:120]}")
    y -= 14
    page.drawString(56, y, f"{MARKER}{digest}")
    y -= 28
    page.setFont("Helvetica", 9)
    page.drawString(56, y, "Herunterladen über FLOWDOC → Dokument öffnen → „Originaldatei herunterladen“.")
    page.drawString(56, y - 13, "Die Prüfsumme belegt, dass die Datei seit der Ablage nicht verändert wurde.")
    page.showPage()
    page.save()
    return buffer.getvalue()
