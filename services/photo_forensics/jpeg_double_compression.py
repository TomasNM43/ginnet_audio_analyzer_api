"""
Módulo 2 - Doble compresión JPEG.

- Histograma de coeficientes DCT: la doble cuantización deja un patrón periódico
  (picos/huecos) en el histograma de las frecuencias bajas.
- Desalineación de la cuadrícula 8x8: regiones pegadas desde otra imagen (o recortadas)
  tienen la cuadrícula de bloques desplazada respecto al resto.

Usa jpeglib/jpegio si están instalados para leer los coeficientes reales; si no, los
estima con una DCT 8x8 sobre los píxeles decodificados y la tabla de cuantización
(Pillow).
"""
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from .common import ForensicImage, dct_matrix, heatmap_to_regions, make_result

MODULE = "jpeg_double_compression"

MAX_CROP = 2880          # lado máximo del recorte (múltiplo de 8) para acotar costo
TILE = 128
FREQS = [(0, 1), (1, 0), (1, 1), (0, 2), (2, 0), (2, 1), (1, 2)]

_ZIGZAG = np.array([
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27,
    20, 13, 6, 7, 14, 21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63])


def _qtable(path: str) -> Optional[np.ndarray]:
    with Image.open(path) as im:
        tables = getattr(im, "quantization", None)
    if not tables:
        return None
    zz = np.array(tables[min(tables.keys())], dtype=np.float32)
    if zz.size != 64:
        return None
    nat = np.zeros(64, dtype=np.float32)
    nat[_ZIGZAG] = zz
    return nat.reshape(8, 8)


def _coefficients_from_library(path: str) -> Optional[Tuple[np.ndarray, str]]:
    """Coeficientes cuantizados reales (bh, bw, 8, 8) vía jpeglib o jpegio."""
    try:
        import jpeglib
        im = jpeglib.read_dct(path)
        return np.asarray(im.Y, dtype=np.float32), "jpeglib"
    except Exception:
        pass
    try:
        import jpegio
        jpg = jpegio.read(path)
        arr = np.asarray(jpg.coef_arrays[0], dtype=np.float32)
        bh, bw = arr.shape[0] // 8, arr.shape[1] // 8
        return arr[:bh * 8, :bw * 8].reshape(bh, 8, bw, 8).transpose(0, 2, 1, 3), "jpegio"
    except Exception:
        return None


def _crop_gray(ctx: ForensicImage) -> np.ndarray:
    """Gris a resolución completa, recortado al centro con origen múltiplo de 8."""
    gray = np.asarray(ctx.pil.convert("L"), dtype=np.float32)
    h, w = gray.shape
    ch, cw = min(h, MAX_CROP) // 8 * 8, min(w, MAX_CROP) // 8 * 8
    y0, x0 = ((h - ch) // 2) // 8 * 8, ((w - cw) // 2) // 8 * 8
    return gray[y0:y0 + ch, x0:x0 + cw]


def _pixel_dct(gray: np.ndarray, qt: np.ndarray) -> np.ndarray:
    bh, bw = gray.shape[0] // 8, gray.shape[1] // 8
    blocks = (gray[:bh * 8, :bw * 8] - 128.0).reshape(bh, 8, bw, 8).transpose(0, 2, 1, 3)
    c = dct_matrix(8)
    coefs = c @ blocks @ c.T
    return np.round(coefs / qt)


def _comb_score(coefs: np.ndarray) -> Tuple[float, dict]:
    """Periodicidad del histograma de coeficientes (ya cuantizados)."""
    per_freq = {}
    vals = []
    for (u, v) in FREQS:
        c = coefs[:, :, u, v].ravel().astype(np.int32)
        c = c[(np.abs(c) <= 30)]
        if c.size < 2000:
            continue
        hist = np.bincount(c + 30, minlength=61).astype(np.float64)
        # se ignora el cero (domina) y los extremos poco poblados
        core = hist[30 - 20:30 + 21]
        smooth = cv2.medianBlur(core.astype(np.float32).reshape(1, -1), 5).ravel()
        mask = np.ones_like(core, dtype=bool)
        mask[20] = False
        total = core[mask].sum()
        if total < 500:
            continue
        comb = float(np.abs(core - smooth)[mask].sum() / total)
        per_freq[f"{u},{v}"] = round(comb, 4)
        vals.append(comb)
    if not vals:
        return 0.0, per_freq
    top = float(np.mean(sorted(vals, reverse=True)[:3]))
    return top, per_freq


def _fold_profile(profile: np.ndarray) -> np.ndarray:
    """Perfil de blocking plegado módulo 8 y normalizado por su media (8 valores)."""
    n = (profile.size // 8) * 8
    folded = profile[:n].reshape(-1, 8).mean(axis=0)
    return folded / (folded.mean() + 1e-6)


def _peakiness(f: np.ndarray) -> Tuple[int, float]:
    """Posición del máximo y su prominencia frente a los dos bins vecinos (circular).

    El blocking JPEG es un pico estrecho en un único bin; el contenido de la imagen
    produce perfiles anchos, por eso se compara contra los vecinos y no contra la media.
    """
    m = int(np.argmax(f))
    neigh = 0.5 * (f[(m - 1) % 8] + f[(m + 1) % 8])
    return m, float(f[m] / (neigh + 1e-6))


def _grid_map(gray: np.ndarray):
    """Por tesela: perfiles plegados (ny, nx, 2[x,y], 8), offset y fuerza del pico."""
    h, w = gray.shape
    ny, nx = h // TILE, w // TILE
    folded = np.zeros((ny, nx, 2, 8), dtype=np.float32)
    offsets = np.full((ny, nx, 2), -1, dtype=np.int16)
    strengths = np.zeros((ny, nx), dtype=np.float32)
    for ty in range(ny):
        for tx in range(nx):
            tile = gray[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE]
            if tile.std() < 4.0:
                continue
            fx = _fold_profile(np.abs(np.diff(tile, axis=1)).sum(axis=0))
            fy = _fold_profile(np.abs(np.diff(tile, axis=0)).sum(axis=1))
            folded[ty, tx, 0], folded[ty, tx, 1] = fx, fy
            ms = [_peakiness(f) for f in (fx, fy)]
            offsets[ty, tx] = ((ms[0][0] + 1) % 8, (ms[1][0] + 1) % 8)
            strengths[ty, tx] = min(ms[0][1], ms[1][1])
    return offsets, strengths, folded


def _misaligned_tiles(offsets, strengths, folded, dom):
    """Teselas cuyo pico de blocking está en otra posición que el dominante, con claridad.

    El pico propio debe superar de forma clara al valor que tiene la tesela en la posición
    dominante; así se descartan las teselas con blocking débil cuyo máximo es casual.
    """
    valid = offsets[..., 0] >= 0
    mis = np.zeros(valid.shape, dtype=bool)
    for axis in (0, 1):
        m_dom = (dom[axis] - 1) % 8
        own = folded[..., axis, :].max(axis=-1)
        at_dom = folded[..., axis, m_dom]
        differs = offsets[..., axis] != dom[axis]
        mis |= valid & differs & (strengths > 1.2) & (own / (at_dom + 1e-6) >= 1.15)
    return mis


def analyze(ctx: ForensicImage):
    if not ctx.is_jpeg:
        return make_result(MODULE, skipped="la imagen no es JPEG")

    qt = _qtable(ctx.path)
    gray = _crop_gray(ctx)
    if gray.shape[0] < 2 * TILE or gray.shape[1] < 2 * TILE:
        return make_result(MODULE, skipped="imagen demasiado pequeña")

    details = {}

    # --- Histograma DCT ---
    lib = _coefficients_from_library(ctx.path)
    if lib is not None:
        coefs, source = lib
    elif qt is not None:
        coefs, source = _pixel_dct(gray, qt), "pixel_dct"
    else:
        coefs, source = None, "none"
    details["coefficient_source"] = source
    dq_score, per_freq = 0.0, {}
    if coefs is not None:
        comb, per_freq = _comb_score(coefs)
        dq_score = float(np.clip((comb - 0.12) / 0.35, 0.0, 1.0))
        details["comb_strength"] = round(comb, 4)
    details["comb_per_frequency"] = per_freq
    details["double_quantization_score"] = round(dq_score, 3)

    # --- Cuadrícula 8x8 ---
    offsets, strengths, folded = _grid_map(gray)
    confident = (offsets[..., 0] >= 0) & (strengths > 1.15)
    flags = []
    heatmap = None
    regions = []
    grid_score = 0.0
    if confident.sum() >= 4:
        pairs = offsets[confident]
        codes = pairs[:, 0] * 8 + pairs[:, 1]
        dominant = int(np.bincount(codes, minlength=64).argmax())
        dom = (dominant // 8, dominant % 8)
        raw_mis = _misaligned_tiles(offsets, strengths, folded, dom)
        # una región pegada abarca varias teselas contiguas; las teselas aisladas son ruido
        n_cc, lab, st, _ = cv2.connectedComponentsWithStats(raw_mis.astype(np.uint8), connectivity=4)
        misaligned = np.zeros_like(raw_mis)
        for i in range(1, n_cc):
            if st[i, cv2.CC_STAT_AREA] >= 3:
                misaligned |= lab == i
        no_grid = (offsets[..., 0] >= 0) & (strengths <= 1.02)
        frac_mis = float(misaligned.sum() / confident.sum())
        details["dominant_grid_offset"] = list(dom)
        details["misaligned_tiles"] = int(misaligned.sum())
        details["confident_tiles"] = int(confident.sum())

        heatmap = np.zeros(offsets.shape[:2], dtype=np.float32)
        heatmap[misaligned] = 1.0
        if confident.sum() >= 0.5 * (offsets[..., 0] >= 0).sum():
            heatmap[no_grid] = np.maximum(heatmap[no_grid], 0.55)
        heatmap = cv2.resize(heatmap, (offsets.shape[1] * 4, offsets.shape[0] * 4), interpolation=cv2.INTER_NEAREST)

        if misaligned.sum() >= 3 and 0.01 <= frac_mis <= 0.5:
            grid_score = float(np.clip(0.45 + 0.8 * frac_mis + 0.02 * misaligned.sum(), 0, 0.95))
            flags.append("cuadricula_8x8_desalineada_localizada")
            regions = heatmap_to_regions(heatmap, MODULE, "grid 8x8", threshold=0.9, min_area_ratio=0.0)
        elif dom != (0, 0) and frac_mis < 0.2:
            grid_score = 0.35
            flags.append("cuadricula_global_desplazada (posible recorte tras compresión)")
    else:
        details["grid_note"] = "sin bloques con blocking suficiente"

    if dq_score >= 0.5:
        flags.append("doble_cuantizacion_en_histograma_dct")
    score = max(0.8 * dq_score, grid_score)
    details["grid_score"] = round(grid_score, 3)
    return make_result(MODULE, score=score, regions=regions, heatmap=heatmap, details=details, flags=flags)
