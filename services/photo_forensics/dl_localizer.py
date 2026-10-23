"""
Módulo 8 - Localizador por deep learning (TruFor / MVSS-Net).

Wrapper con carga perezosa del modelo. Si faltan los pesos o el modelo no se puede
construir, devuelve `error` y el resto del sistema sigue funcionando.

Configuración (variables de entorno):
- DL_LOCALIZER_ENABLED   "0" para desactivar el módulo (por defecto activo).
- DL_LOCALIZER_MODEL     "trufor" (defecto) o "mvssnet".
- DL_LOCALIZER_WEIGHTS   ruta a los pesos. Por defecto models/forensics/<modelo>.(pt|pth|pth.tar).
- DL_LOCALIZER_FACTORY   "paquete.modulo:funcion" que devuelve el nn.Module sin pesos
                         (el repo de TruFor/MVSS-Net debe estar en el PYTHONPATH).
                         No hace falta si los pesos son un TorchScript (.pt).
- DL_LOCALIZER_MAX_SIDE  lado máximo de entrada (defecto 1024; en CPU conviene 512).
"""
import os
import threading
from typing import Optional

import cv2
import numpy as np

from .common import ForensicImage, heatmap_to_regions, make_result

MODULE = "dl_localizer"
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()
_CACHE = {}


def _weights_path(name: str) -> Optional[str]:
    env = os.getenv("DL_LOCALIZER_WEIGHTS")
    if env:
        return env if os.path.isfile(env) else None
    for ext in (".pt", ".pth", ".pth.tar"):
        p = os.path.join(_BASE, "models", "forensics", name + ext)
        if os.path.isfile(p):
            return p
    return None


def _load(name: str):
    """Carga (y cachea) el modelo. Lanza RuntimeError con un mensaje claro si no se puede."""
    import torch

    with _LOCK:
        if name in _CACHE:
            return _CACHE[name]
        weights = _weights_path(name)
        if weights is None:
            raise RuntimeError(f"pesos de {name} no encontrados (DL_LOCALIZER_WEIGHTS o models/forensics/{name}.pt)")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = None
        try:
            model = torch.jit.load(weights, map_location=device)
        except Exception:
            factory = os.getenv("DL_LOCALIZER_FACTORY")
            if not factory or ":" not in factory:
                raise RuntimeError("los pesos no son TorchScript y falta DL_LOCALIZER_FACTORY='modulo:funcion'")
            mod_name, fn_name = factory.split(":", 1)
            import importlib
            try:
                net = getattr(importlib.import_module(mod_name), fn_name)()
            except Exception as e:
                raise RuntimeError(f"no se pudo construir el modelo con {factory}: {e}")
            state = torch.load(weights, map_location=device)
            if isinstance(state, dict):
                state = state.get("state_dict", state.get("model", state))
            net.load_state_dict(state, strict=False)
            model = net.to(device)
        model.eval()
        _CACHE[name] = (model, device)
        return _CACHE[name]


def _to_heatmap(out) -> np.ndarray:
    import torch
    if isinstance(out, dict):
        out = next((out[k] for k in ("map", "pred", "out", "anomaly") if k in out), next(iter(out.values())))
    if isinstance(out, (list, tuple)):
        out = out[0]
    t = out.detach().float().cpu()
    if t.dim() == 4:
        t = t[0]
    if t.dim() == 3:
        t = torch.softmax(t, dim=0)[1] if t.shape[0] == 2 else t[0]
    m = t.numpy()
    if m.min() < 0.0 or m.max() > 1.0:
        m = 1.0 / (1.0 + np.exp(-m))
    return m.astype(np.float32)


def analyze(ctx: ForensicImage):
    if os.getenv("DL_LOCALIZER_ENABLED", "1") == "0":
        return make_result(MODULE, skipped="desactivado (DL_LOCALIZER_ENABLED=0)")
    name = os.getenv("DL_LOCALIZER_MODEL", "trufor").lower()
    try:
        import torch
        model, device = _load(name)
        max_side = int(os.getenv("DL_LOCALIZER_MAX_SIDE", "1024"))
        rgb = cv2.cvtColor(ctx.bgr, cv2.COLOR_BGR2RGB)
        s = min(1.0, max_side / float(max(rgb.shape[:2])))
        if s < 1.0:
            rgb = cv2.resize(rgb, (int(rgb.shape[1] * s), int(rgb.shape[0] * s)), interpolation=cv2.INTER_AREA)
        x = rgb.astype(np.float32) / 255.0
        x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
        tensor = torch.from_numpy(x.transpose(2, 0, 1)).unsqueeze(0).to(device)
        with torch.no_grad():
            heat = _to_heatmap(model(tensor))
    except Exception as e:
        return make_result(MODULE, error=f"{type(e).__name__}: {e}")

    heat = np.clip(heat, 0, 1)
    top = float(np.percentile(heat, 99))
    mean_hi = float(heat[heat >= 0.5].size / heat.size)
    score = float(np.clip(top, 0, 1)) if mean_hi >= 0.002 else float(np.clip(top * 0.5, 0, 0.4))
    regions = heatmap_to_regions(heat, MODULE, name, threshold=0.5, min_area_ratio=0.002, max_regions=5)
    return make_result(MODULE, score=score, regions=regions, heatmap=heat,
                       details={"model": name, "device": str(device), "p99": round(top, 3),
                                "fraction_above_0.5": round(mean_hi, 4)})
