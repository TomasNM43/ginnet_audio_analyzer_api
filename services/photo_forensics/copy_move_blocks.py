"""
Módulo 4 - Copy-move por bloques (zonas con poca textura).

DCT por bloques solapados -> ordenación lexicográfica de las características -> votación
por vector de desplazamiento. Un desplazamiento con muchos votos indica que un bloque
de píxeles fue duplicado en otra posición.

Los coeficientes DCT de baja frecuencia de TODOS los bloques (stride 1) se obtienen con
`filter2D` usando la base DCT como kernel, sin materializar los bloques. Así se detectan
clones con cualquier desplazamiento entero.
"""
import cv2
import numpy as np

from .common import ForensicImage, dct_matrix, make_region, make_result

MODULE = "copy_move_blocks"

BLOCK = 16
LOW_FREQ = 4              # se usan los coeficientes DCT [0:4, 0:4]
ANALYSIS_SIDE = 512
QUANT = 16.0              # paso de cuantización para el orden lexicográfico
FEATURE_EPS = 8.0         # distancia máxima entre características de bloques "iguales"
NEIGHBORS = 16            # ventana de comparación tras ordenar
MIN_STD = 2.0             # descarta bloques planos (coincidirían con cualquier cosa)
MIN_VOTES = 300           # bloques que deben compartir el mismo desplazamiento (~32x32 px)
MAX_SHIFTS = 3


def _feature_maps(g: np.ndarray) -> np.ndarray:
    """Coeficientes DCT bajos por bloque (posición = esquina superior izquierda) -> (H, W, 16)."""
    c = dct_matrix(BLOCK)
    maps = []
    for u in range(LOW_FREQ):
        for v in range(LOW_FREQ):
            kernel = np.outer(c[u], c[v]).astype(np.float32)
            maps.append(cv2.filter2D(g, -1, kernel, anchor=(0, 0), borderType=cv2.BORDER_REFLECT))
    return np.stack(maps, axis=-1)


def analyze(ctx: ForensicImage):
    g = ctx.gray
    scale = min(1.0, ANALYSIS_SIDE / float(max(g.shape)))
    if scale < 1.0:
        g = cv2.resize(g, (int(g.shape[1] * scale), int(g.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    g = g.astype(np.float32)
    h, w = g.shape
    if h < 3 * BLOCK or w < 3 * BLOCK:
        return make_result(MODULE, skipped="imagen demasiado pequeña")

    ny, nx = h - BLOCK + 1, w - BLOCK + 1  # posiciones válidas de bloque
    feats = _feature_maps(g)[:ny, :nx].reshape(-1, LOW_FREQ ** 2)
    mean = cv2.boxFilter(g, -1, (BLOCK, BLOCK), anchor=(0, 0), normalize=True)
    sq = cv2.boxFilter(g * g, -1, (BLOCK, BLOCK), anchor=(0, 0), normalize=True)
    std = np.sqrt(np.maximum(sq - mean * mean, 0))[:ny, :nx].ravel()

    valid = np.flatnonzero(std >= MIN_STD)
    if valid.size < 200:
        return make_result(MODULE, score=0.0, details={"valid_blocks": int(valid.size), "max_votes": 0})

    F = feats[valid]
    py, px = np.divmod(valid, nx)
    min_shift = max(2 * BLOCK, 0.05 * max(h, w))

    code_parts = []
    # dos pasadas con la rejilla de cuantización desplazada: evita perder pares que caen en
    # lados opuestos de un borde de bin y quedan lejos en el orden lexicográfico
    for phase in (0.0, 0.5):
        keys = np.floor(F / QUANT + phase).astype(np.int32)
        order = np.lexsort(keys.T[::-1])
        for off in range(1, NEIGHBORS + 1):
            a, b = order[:-off], order[off:]
            close = np.linalg.norm(F[a] - F[b], axis=1) < FEATURE_EPS
            a, b = a[close], b[close]
            far = np.hypot(py[b] - py[a], px[b] - px[a]) >= min_shift
            a, b = a[far], b[far]
            lo, hi = np.minimum(a, b), np.maximum(a, b)
            code_parts.append(lo.astype(np.int64) * len(F) + hi)

    codes = np.unique(np.concatenate(code_parts)) if code_parts else np.empty(0, np.int64)
    if codes.size == 0:
        return make_result(MODULE, score=0.0, details={"valid_blocks": int(valid.size), "max_votes": 0})
    ia, ib = codes // len(F), codes % len(F)
    dy = py[ib] - py[ia]
    dx = px[ib] - px[ia]
    flip = (dy < 0) | ((dy == 0) & (dx < 0))  # orientación canónica del vector
    dy, dx = np.where(flip, -dy, dy), np.where(flip, -dx, dx)
    ia, ib = np.where(flip, ib, ia), np.where(flip, ia, ib)

    hist = np.zeros((h + 1, 2 * w + 1), dtype=np.float32)
    np.add.at(hist, (dy, dx + w), 1)
    summed = cv2.boxFilter(hist, -1, (3, 3), normalize=False)  # tolera ±1 px de desplazamiento

    regions, heat, shifts = [], np.zeros((h, w), dtype=np.float32), []
    cover = np.ones((BLOCK, BLOCK), np.uint8)
    for _ in range(MAX_SHIFTS):
        peak = np.unravel_index(np.argmax(summed), summed.shape)
        votes = float(summed[peak])
        if votes < MIN_VOTES:
            break
        sdy, sdx = int(peak[0]), int(peak[1]) - w
        summed[max(0, peak[0] - BLOCK):peak[0] + BLOCK, max(0, peak[1] - BLOCK):peak[1] + BLOCK] = 0

        sel = (np.abs(dy - sdy) <= 1) & (np.abs(dx - sdx) <= 1)
        boxes = []
        masks = []
        for idx in (ia[sel], ib[sel]):
            m = np.zeros((h, w), np.uint8)
            m[py[idx], px[idx]] = 1
            # cada punto marcado es la esquina de un bloque: se cubre todo el bloque
            m = cv2.dilate(m, cover, anchor=(BLOCK - 1, BLOCK - 1))
            n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
            if n <= 1:
                break
            big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            x, y, bw, bh, _ = stats[big]
            boxes.append((x, y, x + bw, y + bh))
            masks.append(labels == big)
        if len(boxes) != 2:
            continue
        for m in masks:
            heat[m] = 1.0

        score = float(np.clip(0.4 + 0.6 * votes / (6.0 * MIN_VOTES), 0, 1))
        box_a = ctx.norm_box(*boxes[0], w=w, h=h)
        box_b = ctx.norm_box(*boxes[1], w=w, h=h)
        regions.append(make_region(MODULE, "copy-move bloques", score, box_a, linked_region=box_b))
        regions.append(make_region(MODULE, "copy-move bloques", score, box_b, linked_region=box_a))
        shifts.append({"shift_xy": [sdx, sdy], "votes": int(votes)})

    details = {"valid_blocks": int(valid.size), "shifts": shifts,
               "max_votes": max((s["votes"] for s in shifts), default=0), "min_votes_required": MIN_VOTES}
    if not regions:
        return make_result(MODULE, score=0.0, details=details)
    return make_result(MODULE, score=max(r["score"] for r in regions), regions=regions, heatmap=heat,
                       details=details, flags=[f"copy_move_bloques_{details['max_votes']}_votos"])
