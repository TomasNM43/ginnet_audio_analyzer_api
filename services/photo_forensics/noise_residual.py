"""
Módulo 5 - Residuo de ruido (SRM) y varianza por bloque.

Extrae el residuo de la imagen con filtros SRM, estima el nivel de ruido por bloque
(MAD) y marca los bloques cuyo ruido es inconsistente con el resto de la imagen.
"""
import cv2
import numpy as np

from .common import ForensicImage, heatmap_to_regions, make_result, robust_zscore

MODULE = "noise_residual"
BLOCK = 32

_KV = np.array([[-1, 2, -2, 2, -1],
                [2, -6, 8, -6, 2],
                [-2, 8, -12, 8, -2],
                [2, -6, 8, -6, 2],
                [-1, 2, -2, 2, -1]], dtype=np.float32) / 12.0
_SECOND = np.array([[-1, 2, -1], [2, -4, 2], [-1, 2, -1]], dtype=np.float32) / 4.0
_FIRST = np.array([[0, 0, 0], [0, -1, 1], [0, 0, 0]], dtype=np.float32)
SRM_KERNELS = (_FIRST, _SECOND, _KV)


def srm_residual(gray: np.ndarray) -> np.ndarray:
    """Residuos SRM apilados (3, h, w)."""
    g = gray.astype(np.float32)
    return np.stack([cv2.filter2D(g, -1, k, borderType=cv2.BORDER_REFLECT) for k in SRM_KERNELS])


def analyze(ctx: ForensicImage):
    gray = ctx.gray
    h, w = gray.shape
    ny, nx = h // BLOCK, w // BLOCK
    if ny < 4 or nx < 4:
        return make_result(MODULE, skipped="imagen demasiado pequeña")

    res = srm_residual(gray)[:, :ny * BLOCK, :nx * BLOCK]
    g = gray[:ny * BLOCK, :nx * BLOCK].astype(np.float32)

    def blockify(a):
        return a.reshape(ny, BLOCK, nx, BLOCK).transpose(0, 2, 1, 3).reshape(ny, nx, -1)

    log_sigma = np.zeros((ny, nx), dtype=np.float32)
    for r in res:
        b = blockify(r)
        med = np.median(b, axis=-1, keepdims=True)
        log_sigma += np.log(np.median(np.abs(b - med), axis=-1) * 1.4826 + 1e-3)
    log_sigma /= len(res)

    texture = blockify(g).std(axis=-1)
    brightness = blockify(g).mean(axis=-1)
    # los bloques muy texturados o saturados sesgan el ruido: se estima solo con los "limpios"
    clean = (texture <= np.percentile(texture, 70)) & (brightness > 15) & (brightness < 240)
    if clean.sum() < 8:
        return make_result(MODULE, score=0.0, details={"note": "pocos bloques limpios"})

    z = np.abs(robust_zscore(log_sigma, clean))
    heat = np.clip((z - 2.5) / 3.0, 0, 1).astype(np.float32)
    heat[~clean] = 0.0
    heat = cv2.GaussianBlur(heat, (3, 3), 0)

    sig = heat > 0.4
    n, labels, stats, _ = cv2.connectedComponentsWithStats(sig.astype(np.uint8), connectivity=8)
    frac = 0.0
    comp_mean = 0.0
    max_area = 0
    if n > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        k = 1 + int(np.argmax(areas))
        max_area = int(areas.max())
        frac = float(max_area / (ny * nx))
        comp_mean = float(heat[labels == k].mean())
    if 0.005 <= frac <= 0.45 and max_area >= 2:
        score = float(np.clip(0.25 + 0.5 * comp_mean + 0.8 * frac, 0, 0.8))
    else:
        score = float(np.clip(frac * 2, 0, 0.2))

    regions = heatmap_to_regions(heat, MODULE, "ruido inconsistente", threshold=0.4, min_area_ratio=0.0, max_regions=4)
    details = {"blocks": [int(ny), int(nx)], "largest_inconsistent_fraction": round(frac, 4),
               "mean_z_inconsistent": round(comp_mean, 3)}
    return make_result(MODULE, score=score, regions=regions, heatmap=heat, details=details,
                       flags=["ruido_inconsistente"] if score >= 0.5 else [])
