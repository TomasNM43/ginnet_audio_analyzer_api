"""
Módulo 7 - Bordes rectangulares (señal secundaria).

Canny + contornos + approxPolyDP para hallar rectángulos (parches pegados, etiquetas,
ediciones de texto) y gradiente de ruido por borde: si el ruido dentro del rectángulo
difiere de forma consistente del ruido de fuera en sus lados, es sospechoso.
"""
import cv2
import numpy as np

from .common import ForensicImage, make_region, make_result
from .noise_residual import srm_residual

MODULE = "rect_edges"
MAX_CANDIDATES = 40
MIN_AREA_RATIO = 0.003
MAX_AREA_RATIO = 0.5
MAX_SCORE = 0.7


def _side_log_ratio(noise, inside_mask, p, q, band):
    side = np.zeros(noise.shape, np.uint8)
    cv2.line(side, tuple(int(v) for v in p), tuple(int(v) for v in q), 255, 2 * band + 1)
    inside = (side > 0) & (inside_mask > 0)
    outside = (side > 0) & (inside_mask == 0)
    if inside.sum() < 30 or outside.sum() < 30:
        return None
    return float(np.log((noise[inside].mean() + 1e-3) / (noise[outside].mean() + 1e-3)))


def analyze(ctx: ForensicImage):
    gray = ctx.gray
    h, w = gray.shape
    med = float(np.median(gray))
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), int(max(0, 0.66 * med)), int(min(255, 1.33 * med + 30)))
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    noise = cv2.GaussianBlur(np.abs(srm_residual(gray)[2]), (0, 0), 1.5)
    img_area = float(h * w)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:MAX_CANDIDATES * 3]

    regions, candidates = [], []
    heat = np.zeros((h, w), np.float32)
    margin = 3
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (MIN_AREA_RATIO * img_area <= area <= MAX_AREA_RATIO * img_area):
            continue
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        (_, (rw, rh), _) = cv2.minAreaRect(approx)
        if rw * rh <= 0 or area / (rw * rh) < 0.85:
            continue
        x, y, bw, bh = cv2.boundingRect(approx)
        if x <= margin or y <= margin or x + bw >= w - margin or y + bh >= h - margin:
            continue  # marco de la propia imagen

        pts = approx.reshape(4, 2)
        inside_mask = np.zeros((h, w), np.uint8)
        cv2.fillConvexPoly(inside_mask, pts, 255)
        band = int(max(6, min(20, 0.08 * np.sqrt(area))))
        ratios = [r for r in (_side_log_ratio(noise, inside_mask, pts[i], pts[(i + 1) % 4], band) for i in range(4))
                  if r is not None]
        if len(ratios) < 3:
            continue
        signs = np.sign(ratios)
        consistent = max((signs > 0).sum(), (signs < 0).sum())
        if consistent < 3:
            continue
        strength = float(np.mean(np.abs(ratios)))
        score = float(np.clip(strength / np.log(2.0), 0, 1)) * MAX_SCORE
        if score < 0.15:
            continue
        candidates.append({"score": round(score, 3), "log_noise_ratios": [round(r, 3) for r in ratios]})
        regions.append(make_region(MODULE, "borde rectangular", score, ctx.norm_box(x, y, x + bw, y + bh)))
        cv2.fillConvexPoly(heat, pts, score)
        if len(regions) >= 5:
            break

    if not regions:
        return make_result(MODULE, score=0.0, details={"rectangles_checked": len(contours)})
    return make_result(MODULE, score=max(r["score"] for r in regions) * 0.8, regions=regions, heatmap=heat,
                       details={"candidates": candidates}, flags=["rectangulo_con_ruido_distinto"])
