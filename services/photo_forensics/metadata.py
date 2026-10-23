"""
Módulo 1 - Metadatos EXIF/XMP.

Detecta: software de edición, fechas inconsistentes y miniatura EXIF que no coincide
con la imagen. Usa Pillow (obligatorio) y exifread (opcional, completa etiquetas).
"""
import io
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import cv2
import numpy as np
from PIL import Image

from .common import ForensicImage, make_result

MODULE = "metadata"

EDITING_SOFTWARE = (
    "photoshop", "lightroom", "gimp", "affinity", "paint.net", "pixelmator", "snapseed",
    "canva", "picsart", "photopea", "adobe", "capture one", "darktable", "luminar",
    "fotor", "acdsee", "illustrator", "coreldraw", "corel", "paintshop", "krita",
    "inpaint", "facetune", "meitu", "pixlr", "ps express", "stable diffusion",
    "midjourney", "dall-e", "firefly",
)

_ORIENTATION_OPS = {
    2: [Image.Transpose.FLIP_LEFT_RIGHT],
    3: [Image.Transpose.ROTATE_180],
    4: [Image.Transpose.FLIP_TOP_BOTTOM],
    5: [Image.Transpose.TRANSPOSE],
    6: [Image.Transpose.ROTATE_270],
    7: [Image.Transpose.TRANSVERSE],
    8: [Image.Transpose.ROTATE_90],
}


def _parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    s = str(value).strip().replace("\x00", "")
    for fmt, ln in (("%Y:%m:%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%dT%H:%M:%S", 19)):
        try:
            return datetime.strptime(s[:ln], fmt)
        except ValueError:
            continue
    return None


def _tz_like(delta: timedelta) -> bool:
    """Diferencias múltiplos de 15 min (±1 min) hasta 14 h: parecen zona horaria."""
    secs = abs(delta.total_seconds())
    if secs > 14 * 3600 + 60:
        return False
    rem = secs % 900
    return min(rem, 900 - rem) <= 60


def _read_xmp(raw: bytes) -> Dict[str, List[str]]:
    start = raw.find(b"<x:xmpmeta")
    if start < 0:
        return {}
    end = raw.find(b"</x:xmpmeta>", start)
    xmp = raw[start:end + 12 if end > 0 else start + 65536].decode("utf-8", errors="ignore")
    out: Dict[str, List[str]] = {}
    patterns = {
        "creator_tool": r"xmp:CreatorTool(?:=\"([^\"]*)\"|>([^<]*)<)",
        "software_agent": r"stEvt:softwareAgent(?:=\"([^\"]*)\"|>([^<]*)<)",
        "create_date": r"xmp:CreateDate(?:=\"([^\"]*)\"|>([^<]*)<)",
        "modify_date": r"xmp:ModifyDate(?:=\"([^\"]*)\"|>([^<]*)<)",
        "metadata_date": r"xmp:MetadataDate(?:=\"([^\"]*)\"|>([^<]*)<)",
        "history_action": r"stEvt:action(?:=\"([^\"]*)\"|>([^<]*)<)",
    }
    for key, pat in patterns.items():
        vals = [a or b for a, b in re.findall(pat, xmp)]
        if vals:
            out[key] = vals
    return out


def _extract_exif_thumbnail(raw: bytes) -> Optional[bytes]:
    """Extrae la miniatura JPEG embebida en el APP1 Exif (si existe)."""
    pos = 2
    while pos + 4 < len(raw) and raw[pos] == 0xFF:
        marker = raw[pos + 1]
        seg_len = int.from_bytes(raw[pos + 2:pos + 4], "big")
        if marker == 0xE1 and raw[pos + 4:pos + 10] == b"Exif\x00\x00":
            payload = raw[pos + 10:pos + 2 + seg_len]
            first = payload.find(b"\xff\xd8\xff", 8)
            last = payload.rfind(b"\xff\xd9")
            if first > 0 and last > first:
                return payload[first:last + 2]
        if marker == 0xDA:
            break
        pos += 2 + seg_len
    return None


def _thumbnail_mismatch(ctx: ForensicImage, raw: bytes) -> Optional[Dict]:
    thumb_bytes = _extract_exif_thumbnail(raw)
    if not thumb_bytes:
        return None
    try:
        thumb = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
    except Exception:
        return None

    candidates = [thumb]
    for op in _ORIENTATION_OPS.get(ctx.orientation, []):
        candidates.append(thumb.transpose(op))

    main = cv2.cvtColor(ctx.bgr, cv2.COLOR_BGR2GRAY)
    main_aspect = ctx.width / float(ctx.height)
    best = None
    for cand in candidates:
        aspect = cand.width / float(cand.height)
        if abs(aspect - main_aspect) / main_aspect > 0.06:
            continue
        a = cv2.GaussianBlur(cv2.resize(np.asarray(cand.convert("L")), (64, 64), interpolation=cv2.INTER_AREA), (3, 3), 0)
        b = cv2.GaussianBlur(cv2.resize(main, (64, 64), interpolation=cv2.INTER_AREA), (3, 3), 0)
        a = a.astype(np.float32).ravel()
        b = b.astype(np.float32).ravel()
        if a.std() < 1e-3 or b.std() < 1e-3:
            continue
        ncc = float(np.corrcoef(a, b)[0, 1])
        if best is None or ncc > best:
            best = ncc
    if best is None:
        return {"ncc": None, "reason": "aspecto distinto", "thumb_size": thumb.size}
    return {"ncc": best, "reason": "correlación", "thumb_size": thumb.size}


def _exifread_tags(path: str) -> Dict[str, str]:
    try:
        import exifread
    except ImportError:
        return {}
    try:
        with open(path, "rb") as f:
            return {k: str(v) for k, v in exifread.process_file(f, details=False).items()}
    except Exception:
        return {}


def analyze(ctx: ForensicImage) -> Dict:
    flags: List[str] = []
    scores: List[float] = []
    details: Dict = {}

    with open(ctx.path, "rb") as f:
        raw = f.read()

    exif = ctx.exif
    ifd = {}
    try:
        ifd = exif.get_ifd(0x8769)
    except Exception:
        pass
    xr = _exifread_tags(ctx.path)

    software = exif.get(0x0131) or xr.get("Image Software")
    dt_modify = _parse_dt(exif.get(0x0132) or xr.get("Image DateTime"))
    dt_original = _parse_dt(ifd.get(0x9003) or xr.get("EXIF DateTimeOriginal"))
    dt_digitized = _parse_dt(ifd.get(0x9004) or xr.get("EXIF DateTimeDigitized"))
    xmp = _read_xmp(raw)

    details.update({
        "make": str(exif.get(0x010F)) if exif.get(0x010F) else None,
        "model": str(exif.get(0x0110)) if exif.get(0x0110) else None,
        "software": str(software) if software else None,
        "datetime_original": str(dt_original) if dt_original else None,
        "datetime_digitized": str(dt_digitized) if dt_digitized else None,
        "datetime_modified": str(dt_modify) if dt_modify else None,
        "xmp": {k: v[:3] for k, v in xmp.items()},
        "has_exif": bool(len(exif)),
    })

    # 1) Software de edición
    sw_candidates = [str(software)] if software else []
    sw_candidates += xmp.get("creator_tool", []) + xmp.get("software_agent", [])
    editors = sorted({s for s in sw_candidates if any(e in s.lower() for e in EDITING_SOFTWARE)})
    if editors:
        scores.append(0.6)
        flags.append(f"software_edicion: {', '.join(editors)}")
        details["editing_software"] = editors
    if "saved" in [a.lower() for a in xmp.get("history_action", [])] or "derived" in [a.lower() for a in xmp.get("history_action", [])]:
        scores.append(0.3)
        flags.append("historial_xmp_con_ediciones")

    # 2) Fechas inconsistentes
    date_issues = []
    if dt_original and dt_digitized and abs((dt_digitized - dt_original).total_seconds()) > 60:
        date_issues.append("DateTimeOriginal != DateTimeDigitized")
    if dt_original and dt_modify:
        delta = (dt_modify - dt_original).total_seconds()
        if delta < -60:
            date_issues.append("fecha de modificación anterior a la captura")
        elif delta > 120:
            date_issues.append("modificada después de la captura")
    xmp_modify = _parse_dt((xmp.get("modify_date") or [None])[0])
    xmp_create = _parse_dt((xmp.get("create_date") or [None])[0])
    ref = dt_original or xmp_create
    if xmp_modify and ref:
        d = xmp_modify - ref
        if abs(d.total_seconds()) > 120 and not _tz_like(d):
            date_issues.append("XMP ModifyDate difiere de la captura")
    if date_issues:
        scores.append(0.3 if len(date_issues) == 1 else 0.45)
        flags.extend(f"fechas: {i}" for i in date_issues)
    details["date_issues"] = date_issues

    # 3) Miniatura que no coincide
    if ctx.is_jpeg:
        thumb = _thumbnail_mismatch(ctx, raw)
        details["thumbnail"] = thumb
        if thumb is not None:
            ncc = thumb["ncc"]
            if ncc is None:
                scores.append(0.6)
                flags.append("miniatura_aspecto_distinto")
            elif ncc < 0.5:
                scores.append(0.85)
                flags.append(f"miniatura_no_coincide (ncc={ncc:.2f})")
            elif ncc < 0.8:
                scores.append(0.55)
                flags.append(f"miniatura_poco_similar (ncc={ncc:.2f})")

    if not details["has_exif"] and not xmp:
        flags.append("sin_metadatos")
        scores.append(0.1)

    score = 1.0 - float(np.prod([1.0 - s for s in scores])) if scores else 0.0
    details["thumbnail_mismatch"] = any(f.startswith("miniatura_no_coincide") for f in flags)
    return make_result(MODULE, score=score, details=details, flags=flags)
