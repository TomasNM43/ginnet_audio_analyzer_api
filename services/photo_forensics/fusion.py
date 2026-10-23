"""
Fusión de las señales de los módulos forenses.

1. Reglas duras (evidencia contundente fija un piso al score).
2. Combinación ponderada configurable (YAML/env). El punto de extensión para un
   clasificador entrenado es `set_combiner()` (o la variable FORENSICS_COMBINER="modulo:funcion").
3. Salida: score global, nivel de confianza, tipo probable ("clásico" | "indeterminado"),
   regiones normalizadas (0-1) y heatmap al tamaño de la imagen original.
"""
import copy
import importlib
import os
from typing import Callable, Dict, List, Optional

import cv2
import numpy as np
import yaml

_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_config.yaml")

_DEFAULTS = {
    "method": "noisy_or",
    "weights": {
        "metadata": 0.6, "jpeg_double_compression": 0.7, "copy_move_keypoints": 0.95,
        "copy_move_blocks": 0.9, "noise_residual": 0.5, "ela": 0.2, "rect_edges": 0.25,
        "dl_localizer": 0.9,
    },
    "hard_rules": {
        "copy_move_keypoints_min_inliers": 15, "copy_move_keypoints_floor": 0.9,
        "copy_move_blocks_min_votes": 1500, "copy_move_blocks_floor": 0.85,
        "thumbnail_mismatch_floor": 0.75, "editor_plus_dates_floor": 0.7,
        "grid_misalignment_floor": 0.6,
    },
    "threshold_forgery": 0.5,
    "confidence_levels": {"bajo": 0.3, "medio": 0.5, "alto": 0.75},
    "min_region_score": 0.35,
    "max_regions": 20,
}

# Firma: combiner(module_results: Dict[str, dict], config: dict) -> float en [0, 1]
Combiner = Callable[[Dict[str, Dict], Dict], float]
_combiner: Optional[Combiner] = None


def load_config() -> Dict:
    cfg = copy.deepcopy(_DEFAULTS)
    path = os.getenv("FORENSICS_CONFIG", _DEFAULT_CONFIG_PATH)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for key, val in data.items():
            if isinstance(val, dict) and isinstance(cfg.get(key), dict):
                cfg[key].update(val)
            else:
                cfg[key] = val
    for name in list(cfg["weights"]):
        env = os.getenv(f"FORENSICS_WEIGHT_{name.upper()}")
        if env:
            cfg["weights"][name] = float(env)
    if os.getenv("FORENSICS_THRESHOLD_FORGERY"):
        cfg["threshold_forgery"] = float(os.environ["FORENSICS_THRESHOLD_FORGERY"])
    return cfg


def set_combiner(fn: Optional[Combiner]) -> None:
    """Sustituye la combinación ponderada (p. ej. por un clasificador entrenado)."""
    global _combiner
    _combiner = fn


def _resolve_combiner() -> Optional[Combiner]:
    if _combiner is not None:
        return _combiner
    spec = os.getenv("FORENSICS_COMBINER")
    if spec and ":" in spec:
        mod, fn = spec.split(":", 1)
        return getattr(importlib.import_module(mod), fn)
    return None


def weighted_combiner(results: Dict[str, Dict], cfg: Dict) -> float:
    weights = cfg["weights"]
    active = [(float(weights.get(n, 0.0)), r["score"]) for n, r in results.items() if r.get("score") is not None]
    if not active:
        return 0.0
    if cfg.get("method") == "mean":
        total = sum(w for w, _ in active)
        return float(sum(w * s for w, s in active) / total) if total > 0 else 0.0
    return float(1.0 - np.prod([1.0 - min(max(w, 0.0), 1.0) * s for w, s in active]))


def apply_hard_rules(results: Dict[str, Dict], cfg: Dict) -> List[Dict]:
    """Devuelve las reglas disparadas: [{rule, floor, evidence}]."""
    hr = cfg["hard_rules"]
    fired = []

    kp = results.get("copy_move_keypoints") or {}
    inliers = (kp.get("details") or {}).get("max_inliers", 0)
    if kp.get("score") is not None and inliers >= hr["copy_move_keypoints_min_inliers"]:
        fired.append({"rule": "copy_move_keypoints_matches_coherentes", "floor": hr["copy_move_keypoints_floor"],
                      "evidence": f"{inliers} matches coherentes (RANSAC)"})

    bl = results.get("copy_move_blocks") or {}
    votes = (bl.get("details") or {}).get("max_votes", 0)
    if bl.get("score") is not None and votes >= hr["copy_move_blocks_min_votes"]:
        fired.append({"rule": "copy_move_bloques_votos_altos", "floor": hr["copy_move_blocks_floor"],
                      "evidence": f"{votes} votos para un mismo desplazamiento"})

    md = results.get("metadata") or {}
    mdd = md.get("details") or {}
    if mdd.get("thumbnail_mismatch"):
        fired.append({"rule": "miniatura_exif_no_coincide", "floor": hr["thumbnail_mismatch_floor"],
                      "evidence": "la miniatura EXIF no corresponde a la imagen"})
    if mdd.get("editing_software") and mdd.get("date_issues"):
        fired.append({"rule": "software_edicion_y_fechas_inconsistentes", "floor": hr["editor_plus_dates_floor"],
                      "evidence": f"{', '.join(mdd['editing_software'])}; {', '.join(mdd['date_issues'])}"})

    jp = results.get("jpeg_double_compression") or {}
    if "cuadricula_8x8_desalineada_localizada" in (jp.get("flags") or []):
        fired.append({"rule": "cuadricula_jpeg_desalineada", "floor": hr["grid_misalignment_floor"],
                      "evidence": "regiones con la cuadrícula 8x8 desplazada"})
    return fired


def _confidence_level(score: float, cfg: Dict) -> str:
    lv = cfg["confidence_levels"]
    if score < lv["bajo"]:
        return "bajo"
    if score < lv["medio"]:
        return "medio"
    if score < lv["alto"]:
        return "alto"
    return "muy alto"


def _fuse_heatmaps(results: Dict[str, Dict], cfg: Dict, width: int, height: int) -> np.ndarray:
    """Máximo ponderado de los heatmaps de cada módulo, reescalados a la imagen original."""
    weights = cfg["weights"]
    wmax = max([weights.get(n, 0.0) for n in results] + [1e-6])
    fused = np.zeros((height, width), dtype=np.float32)
    for name, r in results.items():
        hm = r.get("heatmap")
        if hm is None or r.get("score") is None:
            continue
        hm = cv2.resize(np.asarray(hm, dtype=np.float32), (width, height), interpolation=cv2.INTER_LINEAR)
        fused = np.maximum(fused, np.clip(hm, 0, 1) * (weights.get(name, 0.0) / wmax))
    peak = float(fused.max())
    return fused / peak if peak > 1e-6 else fused


def fuse(results: Dict[str, Dict], width: int, height: int, cfg: Optional[Dict] = None) -> Dict:
    """Fusiona los resultados de los módulos. `width`/`height` son los de la imagen original."""
    cfg = cfg or load_config()

    combiner = _resolve_combiner() or weighted_combiner
    base = float(np.clip(combiner(results, cfg), 0.0, 1.0))
    fired = apply_hard_rules(results, cfg)
    score = max([base] + [f["floor"] for f in fired])

    classic_signal = any(
        (r.get("score") or 0) >= 0.5 for n, r in results.items() if n != "dl_localizer")
    probable_type = "clásico" if score >= cfg["threshold_forgery"] and (fired or classic_signal) else "indeterminado"

    regions = [dict(r) for res in results.values() if res.get("score") is not None for r in res.get("regions", [])
               if r["score"] >= cfg["min_region_score"]]
    regions.sort(key=lambda r: r["score"], reverse=True)

    return {
        "score": float(score),
        "weighted_score": base,
        "confidence_level": _confidence_level(score, cfg),
        "probable_type": probable_type,
        "image_width": int(width),
        "image_height": int(height),
        "regions": regions[:cfg["max_regions"]],
        "heatmap": _fuse_heatmaps(results, cfg, width, height),
        "rules_triggered": fired,
    }
