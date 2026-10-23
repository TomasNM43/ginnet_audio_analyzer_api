"""
Pipeline forense: ejecuta los módulos por orden de prioridad y fusiona el resultado.
"""
import time
from typing import Dict, Iterable, Optional

import numpy as np

from . import (copy_move_blocks, copy_move_keypoints, dl_localizer, ela, jpeg_double_compression,
               metadata, noise_residual, rect_edges)
from .common import ForensicImage, make_result
from .fusion import fuse, load_config

# Orden de prioridad (1 = más importante)
MODULES = (
    metadata,
    jpeg_double_compression,
    copy_move_keypoints,
    copy_move_blocks,
    noise_residual,
    ela,
    rect_edges,
    dl_localizer,
)


def analyze_image(path: str, modules: Optional[Iterable] = None) -> Dict:
    """Analiza una foto. Un módulo que falla no interrumpe a los demás.

    Devuelve el resultado de `fuse()` más `modules` (resumen por módulo) y `image` (BGR
    con orientación corregida, la misma sobre la que se trabajó) para visualizar.
    """
    ctx = ForensicImage(path)
    results: Dict[str, Dict] = {}
    for mod in (modules or MODULES):
        name = mod.MODULE
        t0 = time.time()
        try:
            res = mod.analyze(ctx)
        except Exception as e:  # un módulo roto no debe tumbar el análisis
            res = make_result(name, error=f"{type(e).__name__}: {e}")
        res["elapsed_s"] = round(time.time() - t0, 3)
        results[name] = res

    fused = fuse(results, ctx.width, ctx.height, load_config())
    fused["modules"] = results
    fused["image"] = ctx.full_bgr
    return fused


def result_to_dict(result: Dict) -> Dict:
    """Versión serializable a JSON (sin arreglos numpy ni la imagen)."""
    out = {k: v for k, v in result.items() if k not in ("heatmap", "image", "modules")}
    out["modules"] = {}
    for name, m in result.get("modules", {}).items():
        out["modules"][name] = {k: v for k, v in m.items() if k != "heatmap"}
        out["modules"][name]["has_heatmap"] = m.get("heatmap") is not None
    return _jsonable(out)


def _jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
