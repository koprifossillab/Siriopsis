"""빛 묶음 1 번 컷의 자에서 배율(mm/px)을 잰다 (wetherilli 010).

**호스트에서 돈다 — 웹 이미지에 들어가지 않는다**(CLAUDE.md 「환경」, ForGIA 의 web/pipeline 경계).
NAS 원본은 읽기만 하고, DB 는 열지 않는다 — 운영 DB 는 호스트가 열 수 없다(data-safety §14).
들어오는 것은 `manage.py scale_targets` 가 낸 CSV(컷 경로·폭·높이), 나가는 것은 같은 열쇠(컷 경로)의 CSV 이고,
그것을 웹 이미지 안의 `manage.py import_scales` 가 테이블에 넣는다.

    pip install -r requirements-pipeline.txt
    python pipeline/ruler_scale.py --targets targets.csv --out scales.csv [--workers 10] [--debug <폴더>]

다시 돌리면 `--out` 에 이미 있는 경로는 건너뛴다(이어 돌리기). 처음부터는 `--out` 을 지우고.

**재는 법** — 자는 흰 종이 띠에 1 mm 눈금이다(사용자 — 빛 묶음 1 번 컷에는 늘 자가 있다).
1. 원본을 1/2 로 풀어(JPEG draft) 밝고 색이 옅은 곳을 고르고, 덩어리마다 기울어진 바깥 네모를 잰다.
   길쭉하고(긴 변 ≥ 2.2 × 짧은 변) 네모를 잘 채운 것이 자 후보다
2. 후보를 긴 변이 가로가 되게 돌려 잘라, 긴 변을 따라 어두움의 단면을 띠(높이 여섯 칸)마다 낸다 — 눈금은 한쪽 가장자리에서 자라므로
   눈금이 다 지나는 띠가 있다
3. 단면의 주기를 FFT 로 어림하고, 눈금 자리(어두운 꼭짓점)를 하나하나 찾아 번호 → 자리의 직선으로 맞춰 주기를 다듬는다.
   그 주기가 1 mm 다. 원본 화소로 되돌려 mm/px
4. **믿을 만한가** — 눈금 수(≥ 10), 직선에서 벗어난 정도(주기의 15 % 아래), 앞 절반·뒤 절반의 주기가 2 % 안에서 같은가.
   못 넘으면 `doubt`(값은 적되 반입이 넣지 않는다), 자를 못 찾으면 `none`. 둘 다 까닭을 `note` 에 남긴다

맞춤 전에는 같은 묶음의 크기가 같은 컷을 같은 배율로 본다(웹 쪽이 정한다 — 여기는 1 번 컷만 잰다).
"""
import argparse
import csv
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SOURCE_ROOT = os.environ.get("SIRIOPSIS_SOURCE_ROOT", "/nfs/temp-share/Sirius Passet Catalog")
FIELDS = ["path", "width", "height", "status", "mm_per_px", "px_per_mm", "ticks", "resid", "halves", "snr", "angle",
          "box", "note"]

# 믿을 만한 값의 문턱 — 손으로 확인한 표본으로 정했다(devlog 010 §정확도)
MIN_TICKS = 10
MAX_RESID = 0.15        # 눈금 자리가 직선에서 벗어난 정도(주기에 대한 비, 제곱평균)
MIN_SNR = 8.0          # 눈금 대비 ÷ 눈금 사이 흔들림
MAX_HALVES = 0.02       # 앞 절반·뒤 절반 주기의 차(비)
PX_PER_MM = (8.0, 400.0)  # 원본 화소 기준으로 있을 법한 범위 — 밖이면 자가 아니다


def load(path):
    """원본을 1/2 로 풀어 연다 → (RGB 배열, 원본 폭에 대한 비)"""
    with Image.open(path) as im:
        w0 = im.width
        im.draft("RGB", (im.width // 2, im.height // 2))
        im = im.convert("RGB")
        return np.asarray(im), w0 / im.width


def candidates(rgb):
    """흰 띠 후보 → [(바깥 네모 cv2.RotatedRect, 점수)] 큰 것부터"""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    # 눈금(가는 검은 줄)을 먼저 메운다 — 회색조 닫기. 메우지 않으면 띠 끝까지 자란 눈금이 자를 여러 조각으로 끊는다
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    v = cv2.morphologyEx(hsv[..., 2], cv2.MORPH_CLOSE, k)
    s = cv2.morphologyEx(hsv[..., 1], cv2.MORPH_OPEN, k)
    # 자는 사진에서 가장 밝은 쪽이다 — 문턱을 사진마다 밝은 끝에서 잡는다(노출이 달라도)
    hi = float(np.percentile(v, 99.5))
    thr = max(110.0, min(200.0, hi * 0.75))
    mask = ((v >= thr) & (s <= 90)).astype(np.uint8)
    # 돌의 반짝이는 알갱이·분필 점선을 떼어 낸다 — 자는 이보다 굵다
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    h, w = mask.shape
    out = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < h * w * 0.002:
            continue
        ys, xs = np.nonzero(lab[stats[i, 1]:stats[i, 1] + stats[i, 3], stats[i, 0]:stats[i, 0] + stats[i, 2]] == i)
        pts = np.stack([xs + stats[i, 0], ys + stats[i, 1]], 1).astype(np.float32)
        rect = cv2.minAreaRect(pts)
        (rw, rh) = rect[1]
        long_, short = max(rw, rh), min(rw, rh)
        if short < 8 or long_ < 2.2 * short:
            continue
        fill = area / (rw * rh)
        if fill < 0.45:
            continue
        out.append((rect, area * fill))
    out.sort(key=lambda t: -t[1])
    return out[:4]


WIN = 256      # 줄 단면을 나눠 보는 창의 폭(1/2 화소)


def periodic_regions(gray, pmin, pmax, transpose=False):
    """눈금처럼 고른 주기가 이어지는 곳 → [(cv2.RotatedRect 꼴, 점수)].

    밝기 문턱으로는 자를 돌과 가르지 못하는 사진이 있다(밝은 돌·노출이 센 사진). 그래서 밝기가 아니라 **주기**로 찾는다 —
    가로줄(세로 자는 세로줄)마다 창을 밀며 FFT 를 하고, 꼭짓점이 바닥보다 크게 솟고 주기가 이웃 창과 같은 곳을 모은다.
    자는 거의 언제나 사진 가장자리에 반듯이 놓여 가로·세로 두 방향만 본다(기운 자는 흰 띠 쪽이 맡는다).
    """
    g = gray.T if transpose else gray
    g = g.astype(np.float32)
    h, w = g.shape
    if w < WIN:
        return []
    step = WIN // 2
    xs = list(range(0, w - WIN + 1, step))
    rows = g[::2]                                   # 두 줄에 하나 — 눈금은 이보다 길다
    win = np.stack([rows[:, x:x + WIN] for x in xs], 1)      # (줄, 창, WIN)
    win = win - win.mean(-1, keepdims=True)
    sp = np.abs(np.fft.rfft(win * np.hanning(WIN), axis=-1))
    f = np.fft.rfftfreq(WIN)
    band = (f >= 1 / pmax) & (f <= 1 / pmin)
    if band.sum() < 3:
        return []
    sb = sp[..., band]
    j = sb.argmax(-1)
    peak = sb.max(-1)
    ratio = peak / (np.median(sb, -1) + 1e-6)
    per = 1 / f[band][j]
    # 셈: 꼭짓점이 바닥의 여섯 배 넘게 솟고, 대비가 있는 창(돌의 잔무늬가 아니라 검은 줄)
    strong = (ratio > 6) & (win.std(-1) > 12)
    # 주기가 위·아래 줄과 같아야 한다 — 우연히 솟은 창을 뗀다
    same = np.zeros_like(strong)
    same[1:-1] = (np.abs(per[1:-1] - per[:-2]) < 0.1 * per[1:-1]) & (np.abs(per[1:-1] - per[2:]) < 0.1 * per[1:-1])
    m = (strong & same).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    out = []
    for i in range(1, n):
        nr, nw = st[i, cv2.CC_STAT_HEIGHT], st[i, cv2.CC_STAT_WIDTH]
        if st[i, cv2.CC_STAT_AREA] < 6 or nr < 3:
            continue
        r0, c0 = st[i, cv2.CC_STAT_TOP], st[i, cv2.CC_STAT_LEFT]
        y0, y1 = r0 * 2, (r0 + nr) * 2
        x0, x1 = xs[c0], xs[c0 + nw - 1] + WIN
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        L, H = x1 - x0, max(y1 - y0, 4)
        score = float(ratio[lab == i].sum())
        if transpose:      # 세로 자 — 돌려 놓은 좌표를 되돌린다. 긴 변이 세로
            out.append((((cy, cx), (H, L), 0.0), score))
        else:
            out.append((((cx, cy), (L, H), 0.0), score))
    out.sort(key=lambda t: -t[1])
    return out[:4]


def straighten(gray, rect):
    """자 후보를 긴 변이 가로가 되게 돌려 잘라 낸다 → (자른 회색 배열, 돌린 각도)"""
    (cx, cy), (rw, rh), ang = rect
    if rw < rh:
        rw, rh = rh, rw
        ang += 90
    m = cv2.getRotationMatrix2D((cx, cy), ang, 1.0)
    m[0, 2] += rw / 2 - cx
    m[1, 2] += rh / 2 - cy
    crop = cv2.warpAffine(gray, m, (int(rw), int(rh)), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return crop, ang


def fft_period(prof, pmin, pmax):
    """단면의 주된 주기(화소)와 그 꼭짓점이 바닥보다 얼마나 솟았나."""
    x = prof - np.convolve(prof, np.ones(31) / 31, mode="same")
    x = x * np.hanning(len(x))
    n = 1 << int(math.ceil(math.log2(len(x) * 16)))
    sp = np.abs(np.fft.rfft(x, n))
    freqs = np.fft.rfftfreq(n)
    ok = (freqs >= 1 / pmax) & (freqs <= 1 / pmin)
    if not ok.any():
        return None, 0.0
    idx = np.nonzero(ok)[0]
    j = idx[np.argmax(sp[idx])]
    peak = sp[j]
    f0 = freqs[j]
    # 가는 눈금은 배음이 세다 — 반 주파수에도 꼭짓점이 있으면 그쪽이 바탕 주기다(한 단만)
    half = np.argmin(np.abs(freqs - f0 / 2))
    lo, hi = max(0, half - 3), half + 4
    if freqs[half] >= 1 / pmax and sp[lo:hi].max() > 0.6 * peak:
        j = lo + int(np.argmax(sp[lo:hi]))
        f0 = freqs[j]
        peak = sp[j]
    floor = float(np.median(sp[idx])) or 1e-9
    return 1 / f0, float(peak / floor)


def detrend(prof, p):
    w = max(3, int(p * 3)) | 1
    return prof - np.convolve(prof, np.ones(w) / w, mode="same")


def tick_fit(prof, p):
    """어림 주기 `p` 로 눈금 자리를 찾아 번호 → 자리의 직선. → (주기, 절편, 번호 배열, 자리 배열) 또는 None"""
    x = detrend(prof, p)
    pos = []
    n = len(x)
    half = max(1, int(p * 0.5))
    # 주기 하나씩 걸으며 그 안의 가장 어두운 곳 — 어림 주기가 맞으면 눈금마다 하나
    i = int(np.argmax(x[:max(2, int(p))]))
    while i < n:
        a, b = max(0, i - half), min(n, i + half + 1)
        j = a + int(np.argmax(x[a:b]))
        if x[j] > 0:
            # 꼭짓점을 포물선으로 다듬는다
            if 0 < j < n - 1:
                y0, y1, y2 = x[j - 1], x[j], x[j + 1]
                d = y0 - 2 * y1 + y2
                pos.append(j + (0.5 * (y0 - y2) / d if d != 0 else 0.0))
            else:
                pos.append(float(j))
            i = int(round(j + p))
        else:
            i = int(round(i + p))
    if len(pos) < 4:
        return None
    pos = np.array(pos)
    # 빠진 눈금(숫자·흠)이 있어도 번호가 이어지게 어림 주기로 번호를 매긴다
    k = np.round((pos - pos[0]) / p)
    for _ in range(3):
        a, b = np.polyfit(k, pos, 1)
        k = np.round((pos - b) / a)
    a, b = np.polyfit(k, pos, 1)
    keep = np.abs(pos - (a * k + b)) < 0.3 * a
    if keep.sum() < 4:
        return None
    a, b = np.polyfit(k[keep], pos[keep], 1)
    return float(a), float(b), k[keep], pos[keep]


def sample(x, at):
    return np.interp(at, np.arange(len(x)), x)


def tick_run(prof, a, b):
    """맞춘 격자에서 눈금이 정말 있는 가장 긴 구간 → (첫 번호, 끝 번호, 눈금마다의 대비, 한가운데 값들).

    자를 돌려 자른 띠는 흔히 자 바깥(돌)까지 이어진다 — 거기서 찾은 「눈금」은 잡티다. 눈금 자리의 어두움이 양옆 한가운데보다
    또렷한 칸만, 둘까지 빠진 것은 이어 준다(숫자가 눈금을 가린 자리).
    """
    x = detrend(prof, a)
    k0 = int(np.ceil((0 - b) / a + 0.5))
    k1 = int(np.floor((len(x) - 1 - b) / a - 0.5))
    if k1 - k0 < 3:
        return None
    ks = np.arange(k0, k1 + 1)
    on = sample(x, b + a * ks)
    mids = sample(x, b + a * (ks + 0.5))
    lc = on - (sample(x, b + a * (ks - 0.5)) + mids) / 2
    thr = 0.25 * float(np.percentile(lc, 90))
    good = lc > max(thr, 1e-6)
    best, cur, gap = (0, -1), None, 0
    for i, g in enumerate(good):
        if g:
            if cur is None:
                cur = i
            gap = 0
            if i - cur > best[1] - best[0]:
                best = (cur, i)
        else:
            gap += 1
            if gap > 2:
                cur, gap = None, 0
    if best[1] < 0:
        return None
    i0, i1 = best
    return ks[i0], ks[i1], lc[i0:i1 + 1], mids[i0:i1], float(good[i0:i1 + 1].mean())


def fit_ruler(prof, q, pmin, pmax):
    """어림 주기 `q` 로 맞춘 것을 눈금 구간으로 다듬는다 → dict 또는 None"""
    got = tick_fit(prof, q)
    if got is None:
        return None
    a, b, k, pos = got
    run = tick_run(prof, a, b)
    if run is None:
        return None
    kk0, kk1 = run[0], run[1]
    sel = (k >= kk0) & (k <= kk1)
    if sel.sum() < 4:
        return None
    a, b = np.polyfit(k[sel], pos[sel], 1)
    if not (pmin <= a <= pmax):
        return None
    pos, k = pos[sel], k[sel]
    resid = pos - (a * k + b)
    # 눈금 사이 한가운데(흰 종이)의 흔들림에 대한 눈금 대비 — 자는 크고 돌의 잔무늬는 작다
    run = tick_run(prof, a, b) or run
    lc, mids, occ = run[2], run[3], run[4]
    snr = float(np.median(lc) / (np.std(mids) + 1e-6)) if len(mids) >= 3 else 0.0
    return dict(a=float(a), b=float(b), nt=int(len(pos)), rms=float(np.sqrt(np.mean(resid ** 2)) / a), pos=pos,
                k=k, snr=snr, occ=occ)


MIN_OCC = 0.8      # 격자 칸 가운데 눈금이 든 칸의 몫 — 바탕 주기면 거의 다 찬다


def best_period(prof, p, pmin, pmax):
    """FFT 어림 `p` 의 몇 분의 일·몇 배 가운데 **칸이 거의 다 눈금으로 찬 가장 짧은 주기**.

    가는 눈금은 배음이 바탕만큼 세서 FFT 꼭짓점이 둘째·셋째 배음에 앉기도 한다(주기를 ½·⅓ 로 읽는다).
    그 주기로 격자를 그으면 칸의 절반·⅔ 가 비고, 바탕 주기의 두 배·세 배로 그으면 칸은 차지만 더 길다.
    그래서 찬 칸이 `MIN_OCC` 를 넘는 것 가운데 가장 짧은 것이 1 mm 다.
    """
    full, rest = [], []
    for m in (0.25, 1 / 3, 0.5, 1, 2, 3):
        q = p * m
        if not (pmin <= q <= pmax):
            continue
        r = fit_ruler(prof, q, pmin, pmax)
        if r is None:
            continue
        (full if r["occ"] >= MIN_OCC and r["nt"] >= 4 else rest).append(r)
    if full:
        return min(full, key=lambda r: r["a"])
    return max(rest, key=lambda r: r["occ"] * r["nt"], default=None)


def ruler_profile(crop):
    """돌린 자에서 눈금이 가장 또렷한 띠의 단면들 → [(단면, 띠 자리)]"""
    dark = 255.0 - crop.astype(np.float32)
    h = dark.shape[0]
    bands = []
    nb = 6
    for b in range(nb):
        a, z = int(h * b / nb), int(h * (b + 1) / nb)
        if z - a < 2:
            continue
        bands.append((dark[a:z].mean(0), (a, z)))
    # 두 띠를 묶은 것도 — 눈금이 짧으면 띠 하나에 다 들지 않는다
    for b in range(nb - 1):
        a, z = int(h * b / nb), int(h * (b + 2) / nb)
        bands.append((dark[a:z].mean(0), (a, z)))
    return bands


def measure_rgb(rgb, scale):
    """→ (결과 dict, 그림 그릴 거리)"""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    pmin0 = max(3.0, PX_PER_MM[0] / scale)
    pmax0 = min(WIN / 4, PX_PER_MM[1] / scale)
    cands = (candidates(rgb) + periodic_regions(gray, pmin0, pmax0)
             + periodic_regions(gray, pmin0, pmax0, transpose=True))
    if not cands:
        return {"status": "none", "note": "자를 못 찾음 — 흰 띠도, 고른 눈금 무늬도 없다"}, None
    best = None
    for rect, _ in cands:
        crop, ang = straighten(gray, rect)
        L = crop.shape[1]
        pmin = pmin0
        pmax = min(L / 6, PX_PER_MM[1] / scale)
        if pmax <= pmin:
            continue
        for prof, band in ruler_profile(crop):
            p, prom = fft_period(prof, pmin, pmax)
            if p is None:
                continue
            got = best_period(prof, p, pmin, pmax)
            if got is None:
                continue
            a, nt, rms, pos = got["a"], got["nt"], got["rms"], got["pos"]
            # 앞 절반·뒤 절반을 따로 맞춰 견준다
            mid = (pos[0] + pos[-1]) / 2
            halves = 1.0
            if nt >= 8:
                pa, pb = pos[pos < mid], pos[pos >= mid]
                if len(pa) >= 4 and len(pb) >= 4:
                    sa = np.polyfit(np.round((pa - pa[0]) / a), pa, 1)[0]
                    sb = np.polyfit(np.round((pb - pb[0]) / a), pb, 1)[0]
                    halves = abs(sa - sb) / a
            score = nt * got["snr"] / (1 + 10 * rms)
            cand = dict(got, halves=halves, prom=prom, rect=rect, ang=ang, band=band, crop=crop, score=score)
            if best is None or cand["score"] > best["score"]:
                best = cand
    if best is None:
        return {"status": "none", "note": "띠는 있으나 눈금 주기를 못 찾음"}, None
    px_per_mm = best["a"] * scale
    (cx, cy), (rw, rh), _ = best["rect"]
    res = {"px_per_mm": round(px_per_mm, 4), "mm_per_px": round(1 / px_per_mm, 7), "ticks": best["nt"],
           "resid": round(best["rms"], 4), "halves": round(best["halves"], 4), "snr": round(best["snr"], 2), "angle": round(best["ang"] % 180, 1),
           "box": f"{cx * scale:.0f},{cy * scale:.0f},{max(rw, rh) * scale:.0f},{min(rw, rh) * scale:.0f}"}
    why = []
    if best["nt"] < MIN_TICKS:
        why.append(f"눈금 {best['nt']} 개뿐")
    if best["rms"] > MAX_RESID:
        why.append(f"눈금 자리가 고르지 않다({best['rms']:.2f})")
    if best["snr"] < MIN_SNR:
        why.append(f"눈금이 흐리다(대비 {best['snr']:.1f})")
    if best["halves"] > MAX_HALVES:
        why.append(f"앞뒤 절반 주기가 {best['halves'] * 100:.1f} % 다르다")
    res["status"] = "doubt" if why else "ok"
    res["note"] = " · ".join(why)
    return res, best


def draw_debug(best, scale, out):
    """돌린 자 위에 맞춘 눈금 자리를 그어 낸다 — 사람이 눈으로 확인하는 그림."""
    crop = best["crop"]
    band = best["band"]
    # 높이만 줄인다 — 세로 줄은 세로로 남아 맞는지 보는 데 지장이 없다. 맞춘 자리는 위아래 덧댄 칸에 긋는다(눈금을 가리지 않게)
    h = min(crop.shape[0], 120)
    body = cv2.cvtColor(cv2.resize(crop, (crop.shape[1], h), interpolation=cv2.INTER_AREA), cv2.COLOR_GRAY2BGR)
    pad = np.full((14, crop.shape[1], 3), 255, np.uint8)
    img = np.vstack([pad, body, pad.copy(), pad.copy()])
    a, pos = best["a"], best["pos"]
    x = pos[0] - int(np.floor(pos[0] / a)) * a
    while x < crop.shape[1]:
        xi = int(round(x))
        cv2.line(img, (xi, 0), (xi, 13), (0, 0, 255), 1)
        cv2.line(img, (xi, 14 + h), (xi, 27 + h), (0, 0, 255), 1)
        x += a
    for p in pos:      # 찾은 눈금 자리
        cv2.circle(img, (int(round(p)), 14 + int((band[0] + band[1]) / 2 * h / crop.shape[0])), 2, (0, 160, 0), -1)
    cv2.putText(img, f"{a * scale:.2f} px/mm  n={best['nt']}  resid={best['rms']:.3f}  halves={best['halves']:.3f}  snr={best['snr']:.1f}",
                (4, 39 + h), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 0), 1)
    cv2.imwrite(str(out), img)


def measure(rel, debug=None):
    path = Path(SOURCE_ROOT) / rel
    row = {"path": rel}
    try:
        rgb, scale = load(path)
    except (OSError, ValueError) as e:
        row.update(status="none", note=f"못 읽음 — {type(e).__name__}")
        return row
    row["width"], row["height"] = round(rgb.shape[1] * scale), round(rgb.shape[0] * scale)
    res, best = measure_rgb(rgb, scale)
    row.update(res)
    if debug and best is not None:
        name = rel.replace("/", "__")
        draw_debug(best, scale, Path(debug) / (Path(name).stem + ".png"))
    return row


def _job(args):
    rel, debug = args
    try:
        return measure(rel, debug)
    except Exception as e:   # 한 장이 이상해도 나머지는 돈다 — 까닭은 note 에
        return {"path": rel, "status": "none", "note": f"오류 — {type(e).__name__}: {e}"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--targets", required=True, help="scale_targets 가 낸 CSV (path 열)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--debug", help="눈금을 그은 자 그림을 둘 폴더")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    with open(a.targets, newline="", encoding="utf-8") as fh:
        paths = [r["path"] for r in csv.DictReader(fh)]
    done = set()
    out = Path(a.out)
    if out.exists():
        with out.open(newline="", encoding="utf-8") as fh:
            done = {r["path"] for r in csv.DictReader(fh)}
    todo = [p for p in paths if p not in done]
    if a.limit:
        todo = todo[:a.limit]
    if a.debug:
        Path(a.debug).mkdir(parents=True, exist_ok=True)
    new = not out.exists()
    counts = {}
    with out.open("a", newline="", encoding="utf-8") as fh, ProcessPoolExecutor(a.workers) as ex:
        w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        for i, row in enumerate(ex.map(_job, [(p, a.debug) for p in todo], chunksize=4), 1):
            w.writerow(row)
            counts[row["status"]] = counts.get(row["status"], 0) + 1
            if i % 200 == 0:
                fh.flush()
                print(f"{i}/{len(todo)} {counts}", file=sys.stderr, flush=True)
    print(f"끝 — 새로 {len(todo)} · 이미 {len(done)} · {counts}", file=sys.stderr)


if __name__ == "__main__":
    main()
