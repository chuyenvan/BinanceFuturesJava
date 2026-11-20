"""synth.py - bo sinh qua trinh TONG HOP + dap an (giai tich / mo phong doc lap muc giao dich) + lake gia.
KHONG dung du lieu that. Seed co dinh do noi goi truyen vao.
"""
import os
import math
import logging
import numpy as np

log = logging.getLogger("synth")
MIN_MS = 60000


# ------------------------------------------------------------------ qua trinh muc giao dich (don vi gia = tick)
def lattice_paths(rng, npath, ntrade, p0_ticks, p_up=0.5, phi=0.0, bounce_h=0):
    """mid = random walk +-1 tick moi giao dich. phi = tuong quan dau buoc lien tiep (AR(1) cua return; < 0 = mean reversion).
    p_up != 0,5 => drift. bounce_h > 0: gia giao dich = mid +- h tick (ben ngau nhien doc lap). Tra mang int64 (tick)."""
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
    """GBM martingale (drift log -sigma^2/2), tpm buoc con / phut; gia lam tron ve luoi tuong doi rat min."""
    s = sig_day / np.sqrt(1440.0 * tpm)
    z = rng.standard_normal((npath, nmin * tpm))
    lp = np.log(p0) + np.cumsum(s * z - 0.5 * s * s, axis=1)
    p = np.exp(lp)
    q = 10.0 ** (np.floor(np.log10(p0)) + np.round(np.log10(rel_lattice)))
    return np.round(p / q) * q, q


def bars_from_trades(px, tpm):
    """px: (npath, nmin*tpm) -> O,H,L,C (npath, nmin)."""
    npath, nt = px.shape
    a = px.reshape(npath, nt // tpm, tpm)
    return a[:, :, 0], a.max(2), a.min(2), a[:, :, -1]


def concat_grid(O, H, L, C):
    return O.ravel().astype(np.float64), H.ravel().astype(np.float64), L.ravel().astype(np.float64), C.ravel().astype(np.float64)


# ------------------------------------------------------------------ dap an muc giao dich (cai dat DOC LAP voi K-model)
def trade_engine_path(px, tpm, t0, d, W, T, tick, mode, side):
    """Don vi MOT BEN tren CHUOI GIAO DICH thuc (thu tu that). side +1: 1 lenh mua tai L_b; -1: 1 lenh ban tai L_s.
    mode 'touch' (px <= L) hoac 'through' (px <= L - tick). Lenh vao song tu giao dich dau phut t0 toi het phut t0+W-1;
    thoat song tu giao dich KE TIEP sau khop; het han = giao dich cuoi phut f+T. Tra (gross_bps, side, limit_exit) hoac None."""
    tol = 0.01 * tick
    pen = tick if mode == "through" else 0.0
    m0 = px[t0 * tpm - 1]
    a, b = t0 * tpm, (t0 + W) * tpm
    seg = px[a:b]
    if side == 1:
        entry = np.floor(m0 * (1 - d) / tick + 1e-7) * tick
        hit = np.nonzero(seg <= entry - pen + tol)[0]
        X = np.ceil(entry * (1 + d) / tick - 1e-7) * tick
    else:
        entry = np.ceil(m0 * (1 + d) / tick - 1e-7) * tick
        hit = np.nonzero(seg >= entry + pen - tol)[0]
        X = np.floor(entry * (1 - d) / tick + 1e-7) * tick
    if hit.size == 0:
        return None
    k = a + hit[0]
    f = k // tpm
    end = (f + T + 1) * tpm
    seg2 = px[k + 1:end]
    h = np.nonzero(seg2 >= X + pen - tol)[0] if side == 1 else np.nonzero(seg2 <= X - pen + tol)[0]
    if h.size:
        xp, lim = X, 1
    else:
        xp, lim = px[end - 1], 0
    return side * (xp - entry) / entry * 1e4, side, lim


# ------------------------------------------------------------------ lake GIA (cung schema vz-kline1m) cho runner
def _ms(s):
    return int(np.datetime64(s, "ms").astype("int64"))


def fake_specs():
    """Universe gia: cung lich 2021-05..2025-12 (warm-up 2 thang truoc 2021-07). sigma ngay CHUNG 4 % (dap an 1 so)."""
    return [
        dict(sym="AAAUSDT", p0=30000.0, start="2021-05-01", end="2026-01-01", qv=9e8, delist=None),
        dict(sym="BBBUSDT", p0=2000.0, start="2021-05-01", end="2026-01-01", qv=5e8, delist=None,
             gaps=[("2023-03-10T05:00", 30), ("2024-08-02T11:00", 180)]),
        dict(sym="DDDUSDT", p0=0.02, start="2021-05-01", end="2023-06-15", qv=2e8, delist="2023-06-14T23:59"),
        dict(sym="EEEUSDT", p0=5.0, start="2022-03-01", end="2023-01-01", qv=1e8, delist=None),
        dict(sym="USDCUSDT", p0=1.0, start="2021-05-01", end="2022-01-01", qv=3e9, delist=None, stable=True),
    ]


def beta_specs():
    """Lake drift + beta biet truoc: BTCUSDT (sigma 3 %, drift che do +-mu), 3 alt beta 0,8/1,2/1,4 cung sigma tong 4,5 %.
    Cung lich toan bo 2021-05..2025-12, khong delist/lo (test net_h)."""
    out = [dict(sym="BTCUSDT", p0=30000.0, start="2021-05-01", end="2026-01-01", qv=9e8, delist=None, sig=0.03, mu=0.006,
                beta=None)]
    for i, (b, p0) in enumerate(((0.8, 50.0), (1.2, 2.0), (1.4, 0.3))):
        out.append(dict(sym="AL%dUSDT" % i, p0=p0, start="2021-05-01", end="2026-01-01", qv=5e8 / (i + 1), delist=None,
                        sig=0.045, beta=b))
    return out


def write_fake_lake(root, seed=2026112031, sig_day=0.04, tpm=10, variant="null"):
    """Ghi lake gia theo dung slug allowlist (R3-7): <root>/datasets/x/vz-kline1m-YYYY/kline1m-YYYY-MM.parquet (row group =
    1 symbol), <root>/datasets/x/gridp-t1-funding/funding-YYYY.parquet, <root>/datasets/x/gridp-lifecycle/lifecycle.parquet.
    Tra dict meta (so dong/nam, dac ta)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pandas as pd
    rng = np.random.default_rng(seed)
    fd = os.path.join(root, "datasets/x/gridp-t1-funding")
    ld = os.path.join(root, "datasets/x/gridp-lifecycle")
    for p in [fd, ld] + [os.path.join(root, "datasets/x/vz-kline1m-%d" % y) for y in range(2021, 2026)]:
        os.makedirs(p, exist_ok=True)
    specs = fake_specs() if variant == "null" else beta_specs()
    months = [(y, m) for y in range(2021, 2026) for m in range(1, 13) if (y, m) >= (2021, 5)]
    series = {}
    btc_inc = {}
    for sp in specs:
        a, b = _ms(sp["start"]), _ms(sp["end"])
        nmin = (b - a) // MIN_MS
        ts = a + MIN_MS * np.arange(nmin, dtype=np.int64)
        if sp.get("stable"):
            c = np.round(1.0 + 1e-4 * rng.standard_normal(nmin), 4)
            O, H, L, C = c, c + 1e-4, c - 1e-4, c
        else:
            O = np.empty(nmin); H = np.empty(nmin); L = np.empty(nmin); C = np.empty(nmin)
            sg = sp.get("sig", sig_day)
            s = sg / np.sqrt(1440.0 * tpm)
            q = 10.0 ** (np.floor(np.log10(sp["p0"])) - 8)
            lp = np.log(sp["p0"])
            ch = 100000
            for i in range(0, nmin, ch):
                k = min(ch, nmin - i)
                if variant == "beta" and sp.get("beta") is None:
                    # BTC: drift theo che do (khoi 40 ngay: +mu / 0 / -mu / 0), martingale khi mu = 0
                    dayi = (ts[i:i + k] - _ms("2021-05-01")) // 86400000
                    reg = np.array([1.0, 0.0, -1.0, 0.0])[(dayi // 40) % 4]
                    mu = np.repeat(reg * sp["mu"] / (1440.0 * tpm), tpm)
                    inc = s * rng.standard_normal(k * tpm) - 0.5 * s * s + mu
                    btc_inc[i] = inc
                elif variant == "beta":
                    bi = btc_inc[i]
                    si = math.sqrt(max(sg * sg - (sp["beta"] * specs[0]["sig"]) ** 2, 0.0)) / np.sqrt(1440.0 * tpm)
                    sb = specs[0]["sig"] / np.sqrt(1440.0 * tpm)
                    inc = sp["beta"] * (bi + 0.5 * sb * sb) + si * rng.standard_normal(k * tpm) - 0.5 * s * s
                else:
                    inc = s * rng.standard_normal(k * tpm) - 0.5 * s * s
                path = lp + np.cumsum(inc)
                lp = path[-1]
                p = np.round(np.exp(path) / q) * q
                p = p.reshape(k, tpm)
                O[i:i + k], H[i:i + k], L[i:i + k], C[i:i + k] = p[:, 0], p.max(1), p.min(1), p[:, -1]
        active = np.ones(nmin, bool)
        keep = np.ones(nmin, bool)
        for (g0, glen) in sp.get("gaps", []):
            gi = (_ms(g0) - a) // MIN_MS
            keep[gi:gi + glen] = False          # phut thieu han trong lake
        if sp["sym"] == "AAAUSDT":
            gi = (_ms("2022-07-01T03:00") - a) // MIN_MS
            active[gi:gi + 20] = False           # phut co dong nhung active=False (coi nhu lo ngan)
        series[sp["sym"]] = (ts[keep], O[keep], H[keep], L[keep], C[keep], active[keep], sp["qv"])
    schema = pa.schema([("ts", pa.int64()), ("sym", pa.dictionary(pa.int32(), pa.string())), ("open", pa.float64()),
                        ("high", pa.float64()), ("low", pa.float64()), ("close", pa.float64()), ("volume", pa.float64()),
                        ("quote_volume", pa.float64()), ("active", pa.bool_())])
    rows = {}
    for (y, m) in months:
        a = _ms("%04d-%02d-01" % (y, m))
        b = _ms("%04d-%02d-01" % (y + (m == 12), m % 12 + 1))
        path = os.path.join(root, "datasets/x/vz-kline1m-%d" % y, "kline1m-%04d-%02d.parquet" % (y, m))
        w = pq.ParquetWriter(path, schema, compression="zstd", use_dictionary=["sym", "volume", "quote_volume"],
                             column_encoding={"ts": "DELTA_BINARY_PACKED", "open": "BYTE_STREAM_SPLIT",
                                              "high": "BYTE_STREAM_SPLIT", "low": "BYTE_STREAM_SPLIT",
                                              "close": "BYTE_STREAM_SPLIT", "active": "PLAIN"})
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
    # funding: 8h; BBB doi sang 4h tu 2023-01-01; rate co dinh theo symbol (dau khac nhau)
    for y in range(2021, 2026):
        fr = []
        for sp in specs:
            a0 = max(_ms(sp["start"]), _ms("%d-01-01" % y))
            b0 = min(_ms(sp["end"]), _ms("%d-01-01" % (y + 1)))
            if a0 >= b0:
                continue
            step = 4 if (sp["sym"] == "BBBUSDT" and y >= 2023) else 8
            t = np.arange(((a0 + 3600000 * step - 1) // (3600000 * step)) * 3600000 * step, b0, 3600000 * step) + 7
            rate = 1e-4 if sp["sym"] != "CCCUSDT" else -5e-5
            fr.append(pd.DataFrame({"ts": t.astype(np.int64), "sym": sp["sym"], "interval_h": np.int16(step),
                                    "rate": rate * (1 + 0.5 * rng.standard_normal(len(t)))}))
        pd.concat(fr).to_parquet(os.path.join(fd, "funding-%d.parquet" % y), index=False)
    life = pd.DataFrame({"symbol": [s["sym"] for s in specs] + ["NEWUSDT"],
                         "first_utc": pd.to_datetime([s["start"] for s in specs] + ["2026-02-01"], utc=True),
                         "last_utc": pd.to_datetime([s["delist"] if s["delist"] else None for s in specs] + [None], utc=True),
                         "ascii": [True] * (len(specs) + 1)})
    life.to_parquet(os.path.join(ld, "lifecycle.parquet"), index=False)
    return dict(rows=rows, specs=specs, sig_day=sig_day, tpm=tpm, seed=seed)
