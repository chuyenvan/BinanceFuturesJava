"""synth3.py - bo sinh qua trinh TONG HOP cho S3 + dap an muc giao dich DOC LAP + lake gia co / khong co "rau gia" (wick).
KHONG dung du lieu that. Seed co dinh do noi goi truyen vao. (lattice/gbm/bars copy tu synth.py S1.)
"""
import os
import math
import logging
import numpy as np

log = logging.getLogger("synth3")
MIN_MS = 60000


# ------------------------------------------------------------------ qua trinh muc giao dich (copy S1)
def lattice_paths(rng, npath, ntrade, p0_ticks, p_up=0.5, phi=0.0, bounce_h=0):
    """mid = random walk +-1 tick moi giao dich (p_up != 0,5 => drift; phi = AR(1) dau buoc); bounce_h: gia = mid +- h."""
    if phi == 0.0:
        steps = np.where(rng.random((npath, ntrade)) < p_up, 1, -1).astype(np.int64)
    else:
        steps = np.empty((npath, ntrade), np.int64)
        steps[:, 0] = np.where(rng.random(npath) < 0.5, 1, -1)
        same = rng.random((npath, ntrade)) < (1.0 + phi) / 2.0
        for t in range(1, ntrade):
            steps[:, t] = np.where(same[:, t], steps[:, t - 1], -steps[:, t - 1])
    mid = p0_ticks + np.cumsum(steps, axis=1)
    mid[:, 0] = p0_ticks
    if bounce_h > 0:
        eps = np.where(rng.random((npath, ntrade)) < 0.5, 1, -1)
        return mid + bounce_h * eps
    return mid


def gbm_paths(rng, npath, nmin, tpm, sig_day, p0=100.0, rel_lattice=1e-8):
    s = sig_day / np.sqrt(1440.0 * tpm)
    z = rng.standard_normal((npath, nmin * tpm))
    lp = np.log(p0) + np.cumsum(s * z - 0.5 * s * s, axis=1)
    p = np.exp(lp)
    q = 10.0 ** (np.floor(np.log10(p0)) + np.round(np.log10(rel_lattice)))
    return np.round(p / q) * q, q


def bars_from_trades(px, tpm):
    npath, nt = px.shape
    a = px.reshape(npath, nt // tpm, tpm)
    return a[:, :, 0], a.max(2), a.min(2), a[:, :, -1]


def concat_grid(O, H, L, C):
    return O.ravel().astype(np.float64), H.ravel().astype(np.float64), L.ravel().astype(np.float64), C.ravel().astype(np.float64)


# ------------------------------------------------------------------ dap an muc giao dich S3 (DOC LAP voi K-model va kref3)
def trade_engine_path3(px, tpm, t0, d, W, T, tick, mode, side, xfrac=0.5):
    """Don vi S3 MOT BEN tren CHUOI GIAO DICH (thu tu that). mode 'touch' (px <= L) / 'through' (px <= L - tick) / 'opt3'.
    Vao: giao dich dau phut t0 .. het phut t0+W-1. Thoat limit X = L(1 +- xfrac d) tu giao dich KE TIEP sau khop;
    het han = giao dich cuoi phut f+T (f = phut cua giao dich khop). Tra (gross_bps, limit_exit, f, dur_min) hoac None.
    'opt3' (R3-1, dap an DOC LAP cho K_OPT3 tu chuoi giao dich): vao cham; neu giao dich CUOI cua phut khop da vuot X -> thoat X
    o phut f; neu khong, thoat o giao dich DAU TIEN thuoc cac phut > f cham X; het han nhu tren."""
    tol = 0.01 * tick
    if mode == "opt3":
        return _opt3_path(px, tpm, t0, d, W, T, tick, side, xfrac)
    pen = tick if mode == "through" else 0.0
    m0 = px[t0 * tpm - 1]
    a, b = t0 * tpm, (t0 + W) * tpm
    seg = px[a:b]
    if side == 1:
        entry = math.floor(m0 * (1 - d) / tick + 1e-7) * tick
        hit = np.nonzero(seg <= entry - pen + tol)[0]
        X = math.ceil(entry * (1.0 + xfrac * d) / tick - 1e-7) * tick
    else:
        entry = math.ceil(m0 * (1 + d) / tick - 1e-7) * tick
        hit = np.nonzero(seg >= entry + pen - tol)[0]
        X = math.floor(entry * (1.0 - xfrac * d) / tick + 1e-7) * tick
    if hit.size == 0:
        return None
    k = a + int(hit[0])
    f = k // tpm
    end = (f + T + 1) * tpm
    seg2 = px[k + 1:end]
    h = np.nonzero(seg2 >= X + pen - tol)[0] if side == 1 else np.nonzero(seg2 <= X - pen + tol)[0]
    if h.size:
        xp, lim, xk = X, 1, k + 1 + int(h[0])
    else:
        xp, lim, xk = px[end - 1], 0, end - 1
    return side * (xp - entry) / entry * 1e4, lim, f, xk // tpm - f


def _opt3_path(px, tpm, t0, d, W, T, tick, side, xfrac):
    tol = 0.01 * tick
    m0 = px[t0 * tpm - 1]
    if side == 1:
        L = math.floor(m0 * (1 - d) / tick + 1e-7) * tick
        X = math.ceil(L * (1.0 + xfrac * d) / tick - 1e-7) * tick
    else:
        L = math.ceil(m0 * (1 + d) / tick - 1e-7) * tick
        X = math.floor(L * (1.0 - xfrac * d) / tick + 1e-7) * tick
    k = None
    for j in range(t0 * tpm, (t0 + W) * tpm):
        if (side == 1 and px[j] <= L + tol) or (side == -1 and px[j] >= L - tol):
            k = j
            break
    if k is None:
        return None
    f = k // tpm
    last_f = px[(f + 1) * tpm - 1]
    if (side == 1 and last_f >= X - tol) or (side == -1 and last_f <= X + tol):
        return side * (X - L) / L * 1e4, 1, f, 0
    for j in range((f + 1) * tpm, (f + T + 1) * tpm):
        if (side == 1 and px[j] >= X - tol) or (side == -1 and px[j] <= X + tol):
            return side * (X - L) / L * 1e4, 1, f, j // tpm - f
    xp = px[(f + T + 1) * tpm - 1]
    return side * (xp - L) / L * 1e4, 0, f, T


# ------------------------------------------------------------------ duong log-gia GBM + su kien "rau" / "nhay"
def event_offsets(rng, nmin, tpm, sig_day, lam_day, depth=(3.0, 4.0), rec=(3, 8), variant="wick", sign_p_down=1.0, mid=False):
    """Do lech log-gia (do dai nmin*tpm) cua cac su kien Poisson (lam_day / ngay). variant 'wick': cu roi -A (A = U(depth) x
    sig_day, ca phut su kien o day) roi hoi tuyen tinh ve 0 trong R = U{rec} phut (rau gia). variant 'jump': nhay VINH VIEN +-A
    (xac suat xuong sign_p_down), khong hoi (null: khong co loi the hoi). mid=True (R3-2): nhay o buoc con GIUA phut (1..tpm-1) =>
    open phut nhay = gia TRUOC nhay (null ma K_OPT cu ghi lai ao). Tra (offset, chi so phut su kien, dau)."""
    nev = rng.poisson(lam_day * nmin / 1440.0)
    mins = np.sort(rng.choice(np.arange(2, nmin - 20), size=min(nev, max(nmin - 22, 0)), replace=False)) if nev else np.zeros(0, int)
    off = np.zeros(nmin * tpm)
    jmp = np.zeros(nmin * tpm)
    sgn = np.where(rng.random(mins.size) < sign_p_down, -1.0, 1.0)
    for m, sg in zip(mins.tolist(), sgn.tolist()):
        A = rng.uniform(*depth) * sig_day
        if variant == "wick":
            R = int(rng.integers(rec[0], rec[1] + 1))
            a = m * tpm
            off[a:a + tpm] += sg * A
            for k in range(1, R + 1):
                off[(m + k) * tpm:(m + k + 1) * tpm] += sg * A * (1.0 - k / R)
        else:
            kk = int(rng.integers(1, tpm)) if (mid and tpm > 1) else 0
            jmp[m * tpm + kk] += sg * A
    if variant != "wick":
        off += np.cumsum(jmp)
    return off, mins, sgn


def path_with_events(rng, nmin, tpm, sig_day, p0, lam_day, variant, depth=(3.0, 4.0), common_inc=None, beta=None,
                     rel_lattice=1e-8, sign_p_down=1.0, mid=False):
    """Gia muc giao dich (nmin*tpm) = GBM martingale (hoac beta x BTC + rieng) + su kien. Lam tron ve luoi tuong doi rel_lattice."""
    s = sig_day / math.sqrt(1440.0 * tpm)
    if common_inc is None or beta is None:
        inc = s * rng.standard_normal(nmin * tpm) - 0.5 * s * s
    else:
        sb = float(np.std(common_inc)) if common_inc.size > 1 else 0.0
        si = math.sqrt(max(s * s - (beta * sb) ** 2, 1e-14))
        inc = beta * common_inc + si * rng.standard_normal(nmin * tpm) - 0.5 * s * s
    lp = math.log(p0) + np.cumsum(inc)
    if lam_day > 0:
        off, _, _ = event_offsets(rng, nmin, tpm, sig_day, lam_day, depth=depth, variant=variant, sign_p_down=sign_p_down, mid=mid)
        lp = lp + off
    q = 10.0 ** (math.floor(math.log10(p0)) + round(math.log10(rel_lattice)))
    return np.round(np.exp(lp) / q) * q, inc


# ------------------------------------------------------------------ lake GIA (cung schema vz-kline1m) cho runner3
def _ms(s):
    return int(np.datetime64(s, "ms").astype("int64"))


def lake_specs():
    """Universe gia 2021-05..2025-12: BTCUSDT (sigma 3 %), 3 alt (4 %), 1 alt delist giua ky, 1 stable (bi loai)."""
    return [
        dict(sym="BTCUSDT", p0=30000.0, start="2021-05-01", end="2026-01-01", qv=9e8, delist=None, sig=0.03),
        dict(sym="AAAUSDT", p0=2000.0, start="2021-05-01", end="2026-01-01", qv=5e8, delist=None, sig=0.04,
             gaps=[("2023-03-10T05:00", 30), ("2024-08-02T11:00", 180)]),
        dict(sym="BBBUSDT", p0=5.0, start="2021-05-01", end="2026-01-01", qv=3e8, delist=None, sig=0.04),
        dict(sym="CCCUSDT", p0=0.2, start="2021-05-01", end="2026-01-01", qv=2e8, delist=None, sig=0.04),
        dict(sym="DDDUSDT", p0=0.02, start="2021-05-01", end="2023-06-15", qv=1e8, delist="2023-06-14T23:59", sig=0.04),
        dict(sym="USDCUSDT", p0=1.0, start="2021-05-01", end="2022-01-01", qv=3e9, delist=None, stable=True, sig=0.0),
    ]


def write_lake3(root, seed=2026112131, tpm=4, variant="wick", lam_day=0.35, depth=(3.0, 4.0)):
    """Ghi lake gia theo dung 7 slug allowlist (variant 'null_mid' R3-2: nhay vinh vien GIUA phut). variant 'wick': rau gia (80 % cu roi sau / 20 % cu vot len, roi hoi trong vai
    phut) tren moi symbol khong stable; 'null': nhay VINH VIEN +-A cung tan suat (khong co loi the hoi). Tra meta."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pandas as pd
    rng = np.random.default_rng(seed)
    fd = os.path.join(root, "datasets/x/gridp-t1-funding")
    ld = os.path.join(root, "datasets/x/gridp-lifecycle")
    for p in [fd, ld] + [os.path.join(root, "datasets/x/vz-kline1m-%d" % y) for y in range(2021, 2026)]:
        os.makedirs(p, exist_ok=True)
    specs = lake_specs()
    months = [(y, m) for y in range(2021, 2026) for m in range(1, 13) if (y, m) >= (2021, 5)]
    series = {}
    nev = {}
    for sp in specs:
        a, b = _ms(sp["start"]), _ms(sp["end"])
        nmin = (b - a) // MIN_MS
        ts = a + MIN_MS * np.arange(nmin, dtype=np.int64)
        if sp.get("stable"):
            c = np.round(1.0 + 1e-4 * rng.standard_normal(nmin), 4)
            O, H, L, C = c, c + 1e-4, c - 1e-4, c
        else:
            px, _ = path_with_events(rng, nmin, tpm, sp["sig"], sp["p0"], lam_day, "wick" if variant == "wick" else "jump",
                                     depth=depth, sign_p_down=(0.8 if variant == "wick" else 0.5), mid=(variant == "null_mid"))
            p = px.reshape(nmin, tpm)
            O, H, L, C = p[:, 0], p.max(1), p.min(1), p[:, -1]
            nev[sp["sym"]] = int(round(lam_day * nmin / 1440.0))
        active = np.ones(nmin, bool)
        keep = np.ones(nmin, bool)
        for (g0, glen) in sp.get("gaps", []):
            gi = (_ms(g0) - a) // MIN_MS
            keep[gi:gi + glen] = False
        if sp["sym"] == "BBBUSDT":
            gi = (_ms("2022-07-01T03:00") - a) // MIN_MS
            active[gi:gi + 20] = False
        series[sp["sym"]] = (ts[keep], O[keep], H[keep], L[keep], C[keep], active[keep], sp["qv"])
    schema = pa.schema([("ts", pa.int64()), ("sym", pa.dictionary(pa.int32(), pa.string())), ("open", pa.float64()),
                        ("high", pa.float64()), ("low", pa.float64()), ("close", pa.float64()), ("volume", pa.float64()),
                        ("quote_volume", pa.float64()), ("active", pa.bool_())])
    rows = {}
    for (y, m) in months:
        a = _ms("%04d-%02d-01" % (y, m))
        b = _ms("%04d-%02d-01" % (y + (m == 12), m % 12 + 1))
        path = os.path.join(root, "datasets/x/vz-kline1m-%d" % y, "kline1m-%04d-%02d.parquet" % (y, m))
        w = pq.ParquetWriter(path, schema, compression="zstd")
        for sym, (ts, O, H, L, C, act, qv) in series.items():
            sel = (ts >= a) & (ts < b)
            k = int(sel.sum())
            if k == 0:
                continue
            day = (ts[sel] // 86400000)
            vol = np.where(day % 2 == 0, 1.0, 2.0)
            tb = pa.table({"ts": ts[sel], "sym": pa.array([sym] * k).dictionary_encode(), "open": O[sel], "high": H[sel],
                           "low": L[sel], "close": C[sel], "volume": vol, "quote_volume": vol * qv / 1440.0,
                           "active": act[sel]}, schema=schema)
            w.write_table(tb, row_group_size=k + 1)
            rows[y] = rows.get(y, 0) + k
        w.close()
    for y in range(2021, 2026):
        fr = []
        for sp in specs:
            a0 = max(_ms(sp["start"]), _ms("%d-01-01" % y))
            b0 = min(_ms(sp["end"]), _ms("%d-01-01" % (y + 1)))
            if a0 >= b0:
                continue
            step = 4 if (sp["sym"] == "AAAUSDT" and y >= 2023) else 8
            t = np.arange(((a0 + 3600000 * step - 1) // (3600000 * step)) * 3600000 * step, b0, 3600000 * step) + 7
            fr.append(pd.DataFrame({"ts": t.astype(np.int64), "sym": sp["sym"], "interval_h": np.int16(step),
                                    "rate": 1e-4 * (1 + 0.5 * rng.standard_normal(len(t)))}))
        pd.concat(fr).to_parquet(os.path.join(fd, "funding-%d.parquet" % y), index=False)
    life = pd.DataFrame({"symbol": [s["sym"] for s in specs] + ["NEWUSDT"],
                         "first_utc": pd.to_datetime([s["start"] for s in specs] + ["2026-02-01"], utc=True),
                         "last_utc": pd.to_datetime([s["delist"] if s["delist"] else None for s in specs] + [None], utc=True),
                         "ascii": [True] * (len(specs) + 1)})
    life.to_parquet(os.path.join(ld, "lifecycle.parquet"), index=False)
    return dict(rows=rows, specs=specs, tpm=tpm, seed=seed, variant=variant, lam_day=lam_day, depth=list(depth), n_events=nev)
