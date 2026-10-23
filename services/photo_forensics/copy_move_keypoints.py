"""
Módulo 3 - Copy-move por puntos clave.

SIFT (ORB como fallback) -> matching kNN de la imagen contra sí misma -> RANSAC afín.
Filtra regiones lisas (descriptores poco confiables) y repetitivas (ratio test sobre
los vecinos más cercanos) y exige un mínimo de matches geométricamente coherentes.
"""
import cv2
import numpy as np

from .common import ForensicImage, make_region, make_result

MODULE = "copy_move_keypoints"

MIN_INLIERS_SIFT = 8
MIN_INLIERS_ORB = 12
RATIO = 0.6
MAX_CLUSTERS = 4


def _detector():
    try:
        det = cv2.SIFT_create(nfeatures=6000, contrastThreshold=0.02)
        return det, cv2.NORM_L2, MIN_INLIERS_SIFT, "SIFT"
    except (AttributeError, cv2.error):
        return cv2.ORB_create(nfeatures=8000, fastThreshold=10), cv2.NORM_HAMMING, MIN_INLIERS_ORB, "ORB"


def _local_std(gray: np.ndarray) -> np.ndarray:
    g = gray.astype(np.float32)
    mean = cv2.blur(g, (15, 15))
    sq = cv2.blur(g * g, (15, 15))
    return np.sqrt(np.maximum(sq - mean * mean, 0))


def _hull_box(points: np.ndarray, pad: float, w: int, h: int):
    x0, y0 = points.min(axis=0)
    x1, y1 = points.max(axis=0)
    px, py = (x1 - x0) * pad, (y1 - y0) * pad
    return x0 - px, y0 - py, x1 + px, y1 + py


def analyze(ctx: ForensicImage):
    gray = ctx.gray
    h, w = gray.shape
    det, norm, min_inliers, name = _detector()
    kps, des = det.detectAndCompute(gray, None)
    if des is None or len(kps) < 20:
        return make_result(MODULE, score=0.0, details={"detector": name, "keypoints": 0})

    pts = np.float32([k.pt for k in kps])
    std = _local_std(gray)
    xi = np.clip(pts[:, 0].astype(int), 0, w - 1)
    yi = np.clip(pts[:, 1].astype(int), 0, h - 1)
    textured = std[yi, xi] > 4.0  # descarta puntos en zonas lisas

    knn = cv2.BFMatcher(norm).knnMatch(des, des, k=5)
    min_dist = max(24.0, 0.06 * max(w, h))

    src_idx, dst_idx = [], []
    for i, cands in enumerate(knn):
        if not textured[i]:
            continue
        others = [m for m in cands if m.trainIdx != i]
        if len(others) < 3:
            continue
        nn, second = others[0], others[1]
        # ratio vs. el 2º vecino: si hay muchas copias parecidas (patrón repetitivo) se descarta
        if nn.distance >= RATIO * max(second.distance, 1e-6) and second.distance > 1e-6:
            continue
        j = nn.trainIdx
        if not textured[j] or np.linalg.norm(pts[i] - pts[j]) < min_dist:
            continue
        src_idx.append(i)
        dst_idx.append(j)

    details = {"detector": name, "keypoints": len(kps), "candidate_matches": len(src_idx)}
    if len(src_idx) < min_inliers:
        return make_result(MODULE, score=0.0, details=details)

    src_idx = np.array(src_idx)
    dst_idx = np.array(dst_idx)
    alive = np.ones(len(src_idx), dtype=bool)
    regions, clusters = [], []
    heat = np.zeros((h, w), dtype=np.uint8)

    for _ in range(MAX_CLUSTERS):
        if alive.sum() < min_inliers:
            break
        idx = np.flatnonzero(alive)
        M, inl = cv2.estimateAffinePartial2D(
            pts[src_idx[idx]], pts[dst_idx[idx]], method=cv2.RANSAC,
            ransacReprojThreshold=3.0, maxIters=3000, confidence=0.995)
        if M is None or inl is None or int(inl.sum()) < min_inliers:
            break
        inl = inl.ravel().astype(bool)
        chosen = idx[inl]
        a = pts[src_idx[chosen]]
        b = pts[dst_idx[chosen]]
        scale = float(np.sqrt(abs(np.linalg.det(M[:, :2]))))

        # se retiran los inliers y sus pares inversos (A->B y B->A son la misma copia)
        forward = set(zip(src_idx[chosen].tolist(), dst_idx[chosen].tolist()))
        for k in idx:
            if (src_idx[k], dst_idx[k]) in forward or (dst_idx[k], src_idx[k]) in forward:
                alive[k] = False

        hull_a = cv2.convexHull(a.astype(np.float32))
        hull_b = cv2.convexHull(b.astype(np.float32))
        area_a = cv2.contourArea(hull_a)
        # exige dispersión espacial: no puntos colineales ni un único parche minúsculo
        if not (0.4 <= scale <= 2.5) or area_a < 0.0008 * w * h:
            continue

        n_in = int(len(chosen))
        score = float(np.clip(0.3 + 0.7 * n_in / (3.0 * min_inliers), 0, 1))
        box_a = ctx.norm_box(*_hull_box(a, 0.05, w, h))
        box_b = ctx.norm_box(*_hull_box(b, 0.05, w, h))
        regions.append(make_region(MODULE, "copy-move", score, box_a, linked_region=box_b))
        regions.append(make_region(MODULE, "copy-move", score, box_b, linked_region=box_a))
        cv2.fillConvexPoly(heat, hull_a.astype(np.int32), 255)
        cv2.fillConvexPoly(heat, hull_b.astype(np.int32), 255)
        clusters.append({"inliers": n_in, "scale": round(scale, 3),
                         "rotation_deg": round(float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))), 2),
                         "translation": [round(float(M[0, 2]), 1), round(float(M[1, 2]), 1)]})

    if not clusters:
        return make_result(MODULE, score=0.0, details=details)

    best = max(c["inliers"] for c in clusters)
    details.update({"clusters": clusters, "max_inliers": best, "min_inliers_required": min_inliers})
    score = max(r["score"] for r in regions)
    return make_result(MODULE, score=score, regions=regions, heatmap=(heat > 0).astype(np.float32),
                       details=details, flags=[f"copy_move_{best}_matches_coherentes"])
