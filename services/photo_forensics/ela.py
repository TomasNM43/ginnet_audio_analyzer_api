"""
Módulo 6 - Error Level Analysis (ELA). Solo señal de apoyo.

Recomprime la imagen a calidad 90 y mide la diferencia por bloque. Su score está
acotado a propósito porque produce falsos positivos con bordes, texturas y PNG.
"""
import io

import cv2
import numpy as np
from PIL import Image

from .common import ForensicImage, heatmap_to_regions, make_result, robust_zscore

MODULE = "ela"
QUALITY = 90
BLOCK = 16
MAX_SCORE_JPEG = 0.6
MAX_SCORE_OTHER = 0.3


def analyze(ctx: ForensicImage):
    buf = io.BytesIO()
    ctx.pil.save(buf, "JPEG", quality=QUALITY)
    buf.seek(0)
    recompressed = np.asarray(Image.open(buf).convert("RGB"), dtype=np.float32)
    original = np.asarray(ctx.pil, dtype=np.float32)
    ela = np.abs(original - recompressed).mean(axis=2)

    h, w = ela.shape
    if h < 4 * BLOCK or w < 4 * BLOCK:
        return make_result(MODULE, skipped="imagen demasiado pequeña")
    blk = cv2.resize(ela, (w // BLOCK, h // BLOCK), interpolation=cv2.INTER_AREA)
    z = robust_zscore(blk)
    heat = np.clip((z - 3.0) / 5.0, 0, 1).astype(np.float32)
    heat = cv2.GaussianBlur(heat, (3, 3), 0)

    cap = MAX_SCORE_JPEG if ctx.is_jpeg else MAX_SCORE_OTHER
    sig = (heat > 0.4).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(sig, connectivity=8)
    score = 0.05
    if n > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        k = 1 + int(np.argmax(areas))
        frac = float(areas.max() / sig.size)
        if 0.003 <= frac <= 0.5:
            score = 0.15 + 0.5 * float(heat[labels == k].mean()) + 0.5 * frac
    score = float(min(score, cap))

    regions = heatmap_to_regions(heat, MODULE, "ELA", threshold=0.4, min_area_ratio=0.0, max_regions=3)
    for r in regions:
        r["score"] = min(r["score"], cap)
    details = {"quality": QUALITY, "median_ela": round(float(np.median(ela)), 3),
               "p99_ela": round(float(np.percentile(ela, 99)), 3), "support_only": True}
    return make_result(MODULE, score=score, regions=regions, heatmap=heat * cap, details=details)
