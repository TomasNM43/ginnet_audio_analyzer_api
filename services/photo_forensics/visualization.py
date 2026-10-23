"""
Visualización de los resultados forenses sobre la misma foto (BGR, orientación ya corregida).
Las regiones están en coordenadas normalizadas (0-1).
"""
import unicodedata
from typing import Dict, List, Optional

import cv2
import numpy as np


def _px(box, w, h):
    return (int(round(box[0] * w)), int(round(box[1] * h)), int(round(box[2] * w)), int(round(box[3] * h)))


def clean_heatmap(heatmap: np.ndarray, threshold: float = 0.35, min_area_ratio: float = 0.001) -> np.ndarray:
    """Umbral + filtro de componentes conectadas con área mínima; devuelve el heatmap limpio."""
    hm = np.clip(heatmap.astype(np.float32), 0, 1)
    mask = (hm >= threshold).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = min_area_ratio * hm.shape[0] * hm.shape[1]
    keep = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            keep[labels == i] = 1
    return hm * keep


def overlay_heatmap(image: np.ndarray, heatmap: Optional[np.ndarray], alpha: float = 0.45,
                    threshold: float = 0.35, min_area_ratio: float = 0.001) -> np.ndarray:
    """Aplica colormap al heatmap (reescalado a la imagen) y lo mezcla con addWeighted.

    Solo se tiñen los píxeles que superan el umbral y pertenecen a componentes con área mínima.
    """
    if heatmap is None:
        return image.copy()
    h, w = image.shape[:2]
    hm = cv2.resize(np.asarray(heatmap, dtype=np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    hm = clean_heatmap(hm, threshold, min_area_ratio)
    if not hm.any():
        return image.copy()
    colored = cv2.applyColorMap((hm * 255).astype(np.uint8), cv2.COLORMAP_JET)
    blended = cv2.addWeighted(image, 1.0 - alpha, colored, alpha, 0)
    return np.where((hm > 0)[..., None], blended, image)


def draw_regions(image: np.ndarray, regions: List[Dict]) -> np.ndarray:
    """Rectángulos con etiqueta 'módulo score'."""
    out = image.copy()
    h, w = out.shape[:2]
    thickness = max(2, int(round(min(h, w) / 400)))
    font_scale = max(0.5, min(h, w) / 1200)
    for r in regions:
        x0, y0, x1, y1 = _px(r["bbox"], w, h)
        cv2.rectangle(out, (x0, y0), (x1, y1), (0, 0, 255), thickness)
        label = f"{r['module']} {r['score']:.2f}"
        (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        ty = y0 - 4 if y0 - th - base - 4 >= 0 else y0 + th + base + 4
        cv2.rectangle(out, (x0, ty - th - base), (x0 + tw + 4, ty + base // 2), (0, 0, 255), -1)
        cv2.putText(out, label, (x0 + 2, ty - 1), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def draw_copy_move_links(image: np.ndarray, regions: List[Dict]) -> np.ndarray:
    """Línea entre la región origen (linked_region) y la región clonada."""
    out = image.copy()
    h, w = out.shape[:2]
    thickness = max(2, int(round(min(h, w) / 500)))
    seen = set()
    for r in regions:
        link = r.get("linked_region")
        if not link:
            continue
        a = _px(r["bbox"], w, h)
        b = _px(link, w, h)
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        ca = ((a[0] + a[2]) // 2, (a[1] + a[3]) // 2)
        cb = ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)
        cv2.line(out, ca, cb, (0, 255, 255), thickness, cv2.LINE_AA)
        cv2.circle(out, ca, thickness * 3, (0, 255, 0), -1, cv2.LINE_AA)   # origen
        cv2.circle(out, cb, thickness * 3, (0, 0, 255), -1, cv2.LINE_AA)   # clon
    return out


def render_forensic_image(image: np.ndarray, result: Dict, alpha: float = 0.45) -> np.ndarray:
    """Composición final sobre la misma foto: heatmap + enlaces + regiones + cabecera."""
    out = overlay_heatmap(image, result.get("heatmap"), alpha=alpha)
    regions = result.get("regions", [])
    out = draw_copy_move_links(out, regions)
    out = draw_regions(out, regions)

    h, w = out.shape[:2]
    scale = max(0.6, min(h, w) / 900)
    text = (f"Score {result['score']:.2f} | confianza {result['confidence_level']} | "
            f"tipo {result['probable_type']}")
    # cv2.putText solo soporta ASCII
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
    band = th + base + 14
    cv2.rectangle(out, (0, 0), (w, band), (30, 30, 30), -1)
    cv2.putText(out, text, (8, th + 6), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2, cv2.LINE_AA)
    return out
