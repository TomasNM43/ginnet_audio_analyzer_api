"""
Utilidades comunes del análisis forense de fotos.

Convenciones:
- Todas las regiones usan coordenadas normalizadas (0-1) [x0, y0, x1, y1].
- Los heatmaps son arreglos float32 en [0, 1] de cualquier resolución; la fusión
  los reescala al tamaño de la imagen original.
- Cada módulo expone `analyze(ctx) -> dict` construido con `make_result`.
"""
import os
from typing import Dict, List, Optional, Sequence

import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_ANALYSIS_SIDE = int(os.getenv("FORENSICS_MAX_SIDE", "1600"))


class ForensicImage:
    """Imagen cargada una sola vez, con orientación EXIF aplicada.

    Todos los módulos trabajan sobre esta versión (`pil`/`bgr`/`gray`). Si la imagen
    se reduce para analizarla, `bgr`/`gray` quedan en tamaño de análisis, pero como
    las coordenadas se normalizan, las cajas siempre son válidas para la original.
    """

    def __init__(self, path: str, max_side: Optional[int] = None):
        self.path = str(path)
        max_side = max_side or MAX_ANALYSIS_SIDE

        with Image.open(self.path) as im:
            self.format = (im.format or "").upper()
            self.exif = im.getexif()
            self.orientation = int(self.exif.get(0x0112, 1) or 1)
            im.load()
            self.pil = ImageOps.exif_transpose(im).convert("RGB")

        self.is_jpeg = self.format in ("JPEG", "MPO")
        self.width, self.height = self.pil.size

        full_bgr = cv2.cvtColor(np.asarray(self.pil), cv2.COLOR_RGB2BGR)
        scale = min(1.0, max_side / float(max(self.width, self.height)))
        if scale < 1.0:
            size = (max(1, int(round(self.width * scale))), max(1, int(round(self.height * scale))))
            self.bgr = cv2.resize(full_bgr, size, interpolation=cv2.INTER_AREA)
        else:
            self.bgr = full_bgr
        self.full_bgr = full_bgr
        self.scale = scale
        self.gray = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2GRAY)
        self.h, self.w = self.gray.shape

    def norm_box(self, x0, y0, x1, y1, w=None, h=None) -> List[float]:
        w = w or self.w
        h = h or self.h
        return [
            float(np.clip(x0 / w, 0, 1)), float(np.clip(y0 / h, 0, 1)),
            float(np.clip(x1 / w, 0, 1)), float(np.clip(y1 / h, 0, 1)),
        ]


def make_result(module: str, score: Optional[float] = None, regions: Optional[List[Dict]] = None,
                heatmap: Optional[np.ndarray] = None, details: Optional[Dict] = None,
                error: Optional[str] = None, skipped: Optional[str] = None,
                flags: Optional[List[str]] = None) -> Dict:
    """Resultado estándar. `score` None = el módulo no aporta señal (error u omitido)."""
    if error is not None or skipped is not None:
        score = None
    elif score is not None:
        score = float(np.clip(score, 0.0, 1.0))
    return {
        "module": module,
        "score": score,
        "error": error,
        "skipped": skipped,
        "regions": regions or [],
        "heatmap": heatmap,
        "details": details or {},
        "flags": flags or [],
    }


def make_region(module: str, label: str, score: float, bbox: Sequence[float],
                linked_region: Optional[Sequence[float]] = None) -> Dict:
    """Región con bbox normalizado [x0, y0, x1, y1]; `linked_region` solo en copy-move."""
    return {
        "module": module,
        "label": label,
        "score": float(np.clip(score, 0.0, 1.0)),
        "bbox": [float(v) for v in bbox],
        "linked_region": [float(v) for v in linked_region] if linked_region is not None else None,
    }


def heatmap_to_regions(heatmap: np.ndarray, module: str, label: str, threshold: float = 0.5,
                       min_area_ratio: float = 0.002, max_regions: int = 5) -> List[Dict]:
    """Componentes conectadas del heatmap umbralizado -> regiones normalizadas."""
    if heatmap is None or heatmap.size == 0:
        return []
    h, w = heatmap.shape[:2]
    mask = (heatmap >= threshold).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = max(1.0, min_area_ratio * h * w)
    regions = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < min_area:
            continue
        score = float(heatmap[labels == i].mean())
        regions.append(make_region(module, label, score, [x / w, y / h, (x + bw) / w, (y + bh) / h]))
    regions.sort(key=lambda r: r["score"], reverse=True)
    return regions[:max_regions]


def robust_zscore(values: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Z-score robusto (mediana/MAD) calculado sobre los elementos de `mask`."""
    ref = values[mask] if mask is not None and mask.any() else values.ravel()
    med = np.median(ref)
    mad = np.median(np.abs(ref - med)) * 1.4826
    return (values - med) / (mad + 1e-6)


def dct_matrix(n: int) -> np.ndarray:
    """Matriz DCT-II ortonormal de n x n."""
    k = np.arange(n)[:, None]
    i = np.arange(n)[None, :]
    c = np.cos((2 * i + 1) * k * np.pi / (2 * n)) * np.sqrt(2.0 / n)
    c[0, :] = np.sqrt(1.0 / n)
    return c.astype(np.float32)
