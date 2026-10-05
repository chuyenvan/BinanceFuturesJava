#!/usr/bin/env python3
"""data_audit_v2.py — DATA AUDIT 2026-10-03: quet ffill/stale CLOSES_1H.bin (toan bo symbol), lineage symbol,
dung CLOSES_1H_v2.bin (+ mask), audit du lieu 0-sim, do anh huong len benchmark "ALL" (P0A / R3 / R2-R2b).

Stage (chay tuan tu): vision scan aero lineage build audit impact
  vision : tai lai Binance Vision UM kline 1h 2021-01..2025-12 GIU volume/ntrades -> WORK/vision1h.npz
  scan   : join CLOSES_1H v1 voi Vision theo (ts,sym) -> stale per-symbol (WORK/stale_v1.csv) + flag per-record
  aero   : Aerospike test.kline_1m_opt -> phut that (v>0) dau/cuoi + mau 1 ngay/thang -> WORK/aero_*.{json,parquet}
  lineage: -> data/meta/symbol_lineage_v2.csv
  build  : -> CLOSES_1H_v2.bin + CLOSES_1H_v2_mask.bin (canh v1, file MOI), data/meta/{DATA_MANIFEST_v2.json,listing_clean_v2.csv}
  audit  : coverage / gap / outlier / funding / qv / spot-check 30 sym -> WORK/audit.json
  impact : P0A ALL, R3 BRK/ALL, R2 all_ret7 (+R2b excess) v1 vs v2 -> WORK/impact.json
KHONG ghi de / xoa file du lieu co san. DEV <= 2025-12-31 (ts close <= 2026-01-01 00:00 UTC). Khong sua .java.
"""
import argparse, glob, hashlib, io, json, logging, os, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
V1 = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
V2 = "/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin"
V2M = "/home/ubuntu/java/fsrun/CLOSES_1H_v2_mask.bin"
MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
MAP_OLD = "/home/ubuntu/claudedata/.run/kernels/tools/_ev2out/symbol_map.csv"
QVDIR = "/home/ubuntu/claude_master/1002/p0a_cache/qv"
FUND = "/tmp/fund_cache.npz"
WORK = "/home/ubuntu/claude_master/1003/data_v2"
META = os.path.join(REPO, "data/meta")
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"
H, DAY, MIN = 3600000, 86400000, 60000
DEV_END_MS = 1767225600000            # 2026-01-01 00:00 UTC (close cua nen 2025-12-31 23:00)
T0_MS = 1609462800000                 # 2021-01-01 01:00 UTC = ts dau tien cua file
GAP_H = 24                            # run khong giao dich >= 24h giua chuoi -> NaN trong v2
RELIST_H = 24 * 30                    # gap >= 30 ngay roi giao dich lai -> relist
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
MDT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("flag", "u1")])
F_TAIL, F_GAP, F_SHORT0, F_UNVER, F_HEAD, F_FLATONLY = 1, 2, 4, 8, 16, 32
FLAG_DOC = {F_TAIL: "tail stale (sau last_real) -> BO record trong v2",
            F_GAP: "run khong giao dich >=24h giua chuoi -> close=NaN trong v2",
            F_SHORT0: "gio volume=0 le (<24h) -> GIU nguyen",
            F_UNVER: "record v1 khong co trong Vision hien tai (volume chua kiem duoc) -> GIU",
            F_HEAD: "head stale (truoc first_real, volume=0) -> BO record",
            F_FLATONLY: "stale suy ra chi tu close dung yen (Vision khong co record) — kem F_TAIL/F_GAP"}
VISION = "https://data.binance.vision/data/futures/um/monthly/klines"
MONTHS = [f"{y}-{m:02d}" for y in range(2021, 2026) for m in range(1, 13)]
INDEX = {"BTCDOMUSDT": "index BTC dominance", "DEFIUSDT": "index DeFi composite", "FOOTBALLUSDT": "index Football fan-token",
         "BLUEBIRDUSDT": "index Bluebird", "XAUUSDT": "commodity gold (TradFi perp)", "PAXGUSDT": "gold-backed token (commodity-like)"}
STABLE = {"USDCUSDT": "stablecoin", "BUSDUSDT": "stablecoin", "TUSDUSDT": "stablecoin", "FDUSDUSDT": "stablecoin",
          "USDPUSDT": "stablecoin", "USDEUSDT": "stablecoin", "EURUSDT": "fiat-like"}
# rename/migration/merge da biet (nguon: thong bao Binance; doi chieu heuristic trong stage lineage)
RENAME = {"RNDRUSDT": ("RENDERUSDT", "Render migration 1:1 (2024-07)"), "MATICUSDT": ("POLUSDT", "Polygon MATIC->POL 1:1 (2024-09)"),
          "KLAYUSDT": ("KAIAUSDT", "Klaytn->Kaia 1:1 (2024-10)"), "FTMUSDT": ("SUSDT", "Fantom->Sonic 1:1 (2025-01)"),
          "EOSUSDT": ("AUSDT", "EOS->Vaulta A 1:1 (2025)"), "MKRUSDT": ("SKYUSDT", "Maker->Sky 1:24000 (2025-09)"),
          "GALUSDT": ("GUSDT", "Galxe GAL->Gravity G 1:60 (2024-07)"), "BNXUSDT": ("FORMUSDT", "BinaryX BNX->Four FORM (2025)"),
          "TOMOUSDT": ("VICUSDT", "TomoChain->Viction 1:1 (2023-12)"), "AGIXUSDT": ("FETUSDT", "ASI merge vao FET (2024-07)"),
          "OCEANUSDT": ("FETUSDT", "ASI merge vao FET (2024-07)"), "NUUSDT": ("TUSDT", "NU+KEEP merge -> Threshold T (2022)"),
          "KEEPUSDT": ("TUSDT", "NU+KEEP merge -> Threshold T (2022)"), "DARUSDT": ("DUSDT", "Mines of Dalarnia DAR->D (2025)")}
RELIST = {"1000LUNCUSDT": "Terra Classic (LUNA cu, delist 2022-05) niem yet lai ten moi", "USTCUSDT": "UST cu (Terra) niem yet lai ten moi",
          "BSVUSDT": "BSV: Binance bo BSV 2019, futures BSVUSDT 2023 (prior auditor xep relist)",
          "RAYSOLUSDT": "Raydium (RAYUSDT delist 2022-11) niem yet lai ten moi"}
UNSURE = {"LUNA2USDT": "Terra 2.0 (chain moi sau sap LUNA 2022-05) — giu active/listing; prior auditor khong xep nhiem",
          "TUSDT": "Threshold T (merge NU+KEEP 2022) — futures T niem yet 2023-02, cach ~1 nam -> giu listing",
          "VICUSDT": "Viction (TOMO doi ten 2023-12) — futures VIC niem yet 2025-03, cach ~16 thang -> giu listing",
          "HANAUSDT": "niem yet 2h sau khi UXLINK dung, gia ~1:1 — trung hop (UXLINK bi hack/delist), khong phai rename"}
log = logging.getLogger("data_v2")


def tstr(ms):
    if ms is None or (isinstance(ms, float) and not np.isfinite(ms)):
        return None
    return str(pd.Timestamp(int(ms), unit="ms"))[:16]


def load_v(path):
    a = np.fromfile(path, dtype=DT)
    return a["ts"].astype(np.int64), a["sym"].astype(np.int64), a["c"].astype(np.float64)


def names_map():
    mp = pd.read_csv(MAP)
    return dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def runs_bool(m):
    """(start, end_excl) cua cac run True lien tiep."""
    d = np.diff(np.concatenate([[0], m.astype(np.int8), [0]]))
    return np.where(d == 1)[0], np.where(d == -1)[0]


def aero_key(min_ms):
    """phut open (UTC ms) -> key Aerospike YYYYMMDD-HHMM theo GMT+7."""
    return (pd.Timestamp(int(min_ms), unit="ms") + pd.Timedelta(hours=7)).strftime("%Y%m%d-%H%M")


class Aero:
    """Doc Aerospike kline_1m_opt (chi doc). get(minutes, want=None) -> {min_ms: {sym: (close, vol)}}."""
    def __init__(self):
        import aerospike, cramjam
        from short_state_0sim import parse_all_min
        self.cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
        self.dec = cramjam.snappy.decompress_raw
        self.parse = parse_all_min

    def get(self, minutes, want=None, chunk=4000):
        minutes = sorted(set(int(m) for m in minutes))
        out = {}
        for i in range(0, len(minutes), chunk):
            ms = minutes[i:i + chunk]
            keys = [("test", "kline_1m_opt", aero_key(m)) for m in ms]
            for m, rr in zip(ms, self.cli.batch_read(keys).batch_records):
                if rr.result != 0 or rr.record is None:
                    continue
                b = rr.record[2]
                if not b or "data" not in b:
                    continue
                d = self.parse(bytes(self.dec(b["data"])))
                w = None if want is None else want.get(m)
                out[m] = {s.decode(): (float(c), float(v)) for s, (c, v) in d.items()
                          if w is None or s.decode() in w}
        return out


# ───────────────────────── stage vision ─────────────────────────
def _vis_month(sym, ym):
    q = urllib.parse.quote(sym)
    url = f"{VISION}/{q}/1h/{q}-1h-{ym}.zip"
    for att in range(4):
        try:
            raw = urllib.request.urlopen(url, timeout=90).read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + att)
        except Exception:
            time.sleep(1 + att)
    else:
        return "FAIL"
    z = zipfile.ZipFile(io.BytesIO(raw))
    K = pd.read_csv(z.open(z.namelist()[0]), header=None, dtype=str)
    K = K[pd.to_numeric(K[0], errors="coerce").notna()]
    if len(K) == 0:
        return None
    K = K.iloc[:, :9].apply(pd.to_numeric, errors="coerce")
    return (K[0].to_numpy(np.int64), K[4].to_numpy(np.float64), K[5].to_numpy(np.float64),
            K[7].to_numpy(np.float64), K[8].to_numpy(np.float64))


def _vis_sym(sid, sym):
    parts, nfail = [], 0
    for ym in MONTHS:
        p = _vis_month(sym, ym)
        if isinstance(p, str):
            nfail += 1
        elif p is not None:
            parts.append(p)
    if not parts:
        return sid, None, nfail
    cols = [np.concatenate([p[i] for p in parts]) for i in range(5)]
    o = np.argsort(cols[0], kind="stable")
    cols = [c[o] for c in cols]
    _, keep = np.unique(cols[0], return_index=True)
    return sid, [c[keep] for c in cols], nfail


def stage_vision():
    _, sid, _ = load_v(V1)
    n2 = names_map()
    uni = [(int(s), n2[int(s)]) for s in np.unique(sid)]
    out = {k: [] for k in ("ts", "sid", "c", "v", "qv", "n")}
    fails, t0 = {}, time.time()
    with ThreadPoolExecutor(20) as ex:
        for i, (s, cols, nf) in enumerate(ex.map(lambda x: _vis_sym(*x), uni)):
            if nf:
                fails[n2[s]] = nf
            if cols is not None:
                out["ts"].append(cols[0] + H)
                out["sid"].append(np.full(len(cols[0]), s, np.int16))
                for k, c in zip(("c", "v", "qv", "n"), cols[1:]):
                    out[k].append(c)
            if (i + 1) % 100 == 0:
                log.info("vision %d/%d %.0fs", i + 1, len(uni), time.time() - t0)
    z = {k: np.concatenate(v) for k, v in out.items()}
    os.makedirs(WORK, exist_ok=True)
    np.savez(os.path.join(WORK, "vision1h.npz"), **z)
    info = dict(n=int(len(z["ts"])), nsym=int(len(np.unique(z["sid"]))), nsym_v1=len(uni), fails=fails,
                missing_sym=[n for s, n in uni if s not in set(np.unique(z["sid"]).tolist())])
    json.dump(info, open(os.path.join(WORK, "vision_info.json"), "w"), indent=1, ensure_ascii=False)
    log.info("vision rec=%d sym=%d/%d fails=%s missing=%s (%.0fs)", info["n"], info["nsym"], len(uni), fails,
             info["missing_sym"], time.time() - t0)


# ───────────────────────── stage scan ─────────────────────────
def _join_vision(ts, sid):
    z = np.load(os.path.join(WORK, "vision1h.npz"))
    k1 = ts * 1024 + sid
    k2 = z["ts"].astype(np.int64) * 1024 + z["sid"].astype(np.int64)
    o2 = np.argsort(k2)
    k2s = k2[o2]
    pos = np.minimum(np.searchsorted(k2s, k1), len(k2s) - 1)
    hit = k2s[pos] == k1
    vol = np.full(len(ts), np.nan)
    cvis = np.full(len(ts), np.nan)
    vol[hit] = z["v"][o2[pos[hit]]]
    cvis[hit] = z["c"][o2[pos[hit]]]
    vo = ~np.isin(k2, k1)
    extra = pd.DataFrame(dict(sid=z["sid"].astype(np.int64)[vo], ts=z["ts"].astype(np.int64)[vo], v=z["v"][vo]))
    return hit, vol, cvis, extra


def _sym_groups(sid, ts):
    order = np.lexsort((ts, sid))
    sids = sid[order]
    bnd = np.flatnonzero(np.diff(sids)) + 1
    return order, sids, np.concatenate([[0], bnd]), np.concatenate([bnd, [len(order)]])


def _scan_one(name, s, t, cc, vv, cvis, ex, gaps, outl):
    """Tra ve (flag per-record, dict hang bang stale)."""
    n = len(t)
    known = np.isfinite(vv)
    consec = np.concatenate([[False], np.diff(t) == H])
    flat = np.concatenate([[False], cc[1:] == cc[:-1]])
    zero = known & (vv == 0)
    stale = zero | (~known & flat & consec)
    nz = np.flatnonzero(~stale)
    if len(nz) == 0:
        log.warning("%s: khong co gio giao dich that nao -> giu nguyen", name)
        nz = np.arange(n)
    kf, kl = int(nz[0]), int(nz[-1])
    head = np.zeros(n, bool); head[:kf] = True
    tail = np.zeros(n, bool); tail[kl + 1:] = True
    mid = stale.copy(); mid[:kf] = False; mid[kl + 1:] = False
    st, en = runs_bool(mid)
    rl = (t[en - 1] - t[st]) // H + 1 if len(st) else np.zeros(0, np.int64)
    gapm = np.zeros(n, bool)
    for s0, e0, L in zip(st, en, rl):
        if L >= GAP_H:
            gapm[s0:e0] = True
            gaps.append(dict(symbol=name, start=tstr(t[s0]), end=tstr(t[e0 - 1]), hours=int(L),
                             n_zero_vol=int(zero[s0:e0].sum()), n_flat_only=int((~known[s0:e0]).sum()),
                             relist_like=bool(L >= RELIST_H)))
    fl = np.zeros(n, np.uint8)
    fl[tail] |= F_TAIL; fl[head] |= F_HEAD; fl[gapm] |= F_GAP
    fl[mid & ~gapm & zero] |= F_SHORT0
    fl[(tail | head | gapm) & ~known] |= F_FLATONLY
    fl[~known] |= F_UNVER
    hole = np.diff(t) // H - 1 if n > 1 else np.zeros(0, np.int64)
    dif = np.flatnonzero(cc != cc[-1])
    tail_flat_co = int((t[-1] - t[dif[-1] + 1]) // H) if len(dif) else int((t[-1] - t[0]) // H)
    fs, fe = runs_bool(flat & consec)
    frl = (t[fe - 1] - t[fs - 1]) // H if len(fs) else np.zeros(0, np.int64)   # gio dung yen = so buoc lien tiep
    nfv = 0
    for s0, e0, L in zip(fs, fe, frl):
        if L >= GAP_H - 1 and (known[s0:e0] & (vv[s0:e0] > 0)).any():
            nfv += 1
    r = np.full(n, np.nan)
    r[1:] = cc[1:] / cc[:-1] - 1
    for i in np.flatnonzero(consec & (np.abs(r) > 0.5)):
        outl.append(dict(symbol=name, ts=tstr(t[i]), ts_ms=int(t[i]), c_prev=float(cc[i - 1]), c=float(cc[i]),
                         ret=float(r[i]), vol=float(vv[i]), flag=int(fl[i])))
    mm = known & np.isfinite(cvis) & (np.abs(cc / np.where(cvis > 0, cvis, np.nan) - 1) > 1e-6)
    e = ex[ex.sid == s]
    row = dict(symbol=name, symId=int(s), first_ts=tstr(t[0]), last_ts=tstr(t[-1]), n_rec=int(n),
               first_real_h=tstr(t[kf]), last_real_h=tstr(t[kl]), first_real_ms=int(t[kf]), last_real_ms=int(t[kl]),
               head_stale_h=int((t[kf] - t[0]) // H), tail_stale_h=int((t[-1] - t[kl]) // H),
               tail_to_dev_end=bool(kl < n - 1 and t[-1] == DEV_END_MS),
               n_gap24=int(sum(1 for L in rl if L >= GAP_H)), h_gap24=int(sum(int(L) for L in rl if L >= GAP_H)),
               max_gap_h=int(rl.max()) if len(rl) else 0, n_short0=int((mid & ~gapm & zero).sum()),
               n_zero_vol=int(zero.sum()), n_unver=int((~known).sum()), missing_h=int(hole.sum()),
               max_hole_h=int(hole.max()) if len(hole) else 0, n_hole24=int((hole >= GAP_H).sum()),
               tail_flat_closeonly_h=tail_flat_co, max_flat_run_h=int(frl.max()) if len(frl) else 0,
               n_flat24_with_vol=int(nfv), n_out50=int((consec & (np.abs(r) > 0.5)).sum()),
               n_close_mismatch_vision=int(mm.sum()), vis_only=int(len(e)), vis_only_real=int((e.v > 0).sum()),
               vis_only_real_after_last=int(((e.ts > t[-1]) & (e.v > 0)).sum()),
               vis_only_real_before_first=int(((e.ts < t[0]) & (e.v > 0)).sum()), last_close=float(cc[-1]),
               first_real_close=float(cc[kf]), last_real_close=float(cc[kl]))
    row["severity_h"] = row["tail_stale_h"] + row["h_gap24"] + row["head_stale_h"]
    return fl, row


def stage_scan():
    t00 = time.time()
    ts, sid, c = load_v(V1)
    n2 = names_map()
    hit, vol, cvis, extra = _join_vision(ts, sid)
    log.info("v1 rec=%d, khop Vision=%d (%.4f%%), Vision-only=%d", len(ts), int(hit.sum()), 100 * hit.mean(), len(extra))
    flags = np.zeros(len(ts), np.uint8)
    order, sids, starts, ends = _sym_groups(sid, ts)
    rows, gaps, outl = [], [], []
    for a, b in zip(starts, ends):
        ix = order[a:b]
        s = int(sids[a])
        fl, row = _scan_one(n2[s], s, ts[ix], c[ix], vol[ix], cvis[ix], extra, gaps, outl)
        flags[ix] = fl
        rows.append(row)
    S = pd.DataFrame(rows).sort_values(["severity_h", "max_flat_run_h"], ascending=False)
    S.to_csv(os.path.join(WORK, "stale_v1.csv"), index=False)
    pd.DataFrame(gaps).to_csv(os.path.join(WORK, "gaps_v1.csv"), index=False)
    pd.DataFrame(outl).to_csv(os.path.join(WORK, "outliers_v1.csv"), index=False)
    np.save(os.path.join(WORK, "flags_v1.npy"), flags)
    yr = pd.to_datetime(ts, unit="ms").year
    info = dict(n_rec=int(len(ts)), n_sym=int(len(S)), n_vis_hit=int(hit.sum()), n_vis_only=int(len(extra)),
                n_vis_only_real=int((extra.v > 0).sum()),
                n_flag={k: int(((flags & f) > 0).sum()) for k, f in (("TAIL", F_TAIL), ("GAP", F_GAP), ("SHORT0", F_SHORT0),
                                                                    ("UNVER", F_UNVER), ("HEAD", F_HEAD), ("FLATONLY", F_FLATONLY))},
                fake_h_by_year={str(y): int((((flags & (F_TAIL | F_GAP | F_HEAD)) > 0) & (yr == y)).sum()) for y in range(2021, 2027)},
                n_sym_tail=int((S.tail_stale_h > 0).sum()), n_sym_tail24=int((S.tail_stale_h >= 24).sum()),
                n_sym_tail_dev_end=int(S.tail_to_dev_end.sum()), n_sym_gap24=int((S.n_gap24 > 0).sum()),
                n_gap24=int(S.n_gap24.sum()), n_sym_head=int((S.head_stale_h > 0).sum()),
                n_sym_flat24_vol=int((S.n_flat24_with_vol > 0).sum()), n_out50=int(len(outl)),
                n_close_mismatch_vision=int(S.n_close_mismatch_vision.sum()))
    json.dump(info, open(os.path.join(WORK, "scan_info.json"), "w"), indent=1)
    log.info("scan %s (%.0fs)", info, time.time() - t00)


# ───────────────────────── stage aero ─────────────────────────
def stage_aero():
    t00 = time.time()
    S = pd.read_csv(os.path.join(WORK, "stale_v1.csv"))
    A = Aero()
    want = {}
    for r in S.itertuples():
        if r.first_real_ms > T0_MS:
            o = r.first_real_ms - H                      # open cua gio that dau tien
            for m in range(o - H, o + H, MIN):
                want.setdefault(m, set()).add(r.symbol)
        o = r.last_real_ms - H
        for m in range(o, min(o + 2 * H, DEV_END_MS), MIN):
            want.setdefault(m, set()).add(r.symbol)
    log.info("aero refine: %d phut / %d sym", len(want), len(S))
    D = A.get(list(want), want=want)
    log.info("aero refine doc %d/%d phut co record (%.0fs)", len(D), len(want), time.time() - t00)
    rec = {}
    for r in S.itertuples():
        fo, lo = r.first_real_ms - H, r.last_real_ms - H
        fw = [m for m in range(fo - H, fo + H, MIN) if m in D and r.symbol in D[m]]
        lw = [m for m in range(lo, min(lo + 2 * H, DEV_END_MS), MIN) if m in D and r.symbol in D[m]]
        fr = [m for m in fw if D[m][r.symbol][1] > 0]
        lr = [m for m in lw if D[m][r.symbol][1] > 0]
        rec[r.symbol] = dict(
            first_real_min=None if r.first_real_ms <= T0_MS or not fr else int(fr[0]),
            first_min_prev_hour=bool(fr and fr[0] < fo), n_present_zero_before_first=int(sum(1 for m in fw if fr and m < fr[0])),
            last_real_min=int(lr[-1]) if lr else None, last_min_next_hour=bool(lr and lr[-1] >= lo + H),
            n_present_zero_after_last=int(sum(1 for m in lw if lr and m > lr[-1])),
            first_window_found=len(fw), last_window_found=len(lw))
    json.dump(rec, open(os.path.join(WORK, "aero_refine.json"), "w"), indent=0, ensure_ascii=False)
    # mau 1 ngay/thang (ngay 15) : moi (gio, sym) -> so phut co record, so phut v>0, close phut cuoi
    uni = set(S.symbol)
    rows = []
    for y in range(2021, 2026):
        for mo in range(1, 13):
            d = pd.Timestamp(f"{y}-{mo:02d}-15")
            m0 = int(d.value // 10**6)
            mins = list(range(m0, m0 + DAY, MIN))
            Dd = A.get(mins, want={m: uni for m in mins})
            agg = {}
            for m, dd in Dd.items():
                h = (m - m0) // H
                for s_, (cl, v) in dd.items():
                    a_ = agg.setdefault((h, s_), [0, 0, np.nan, -1])
                    a_[0] += 1
                    a_[1] += int(v > 0)
                    if m > a_[3]:
                        a_[3], a_[2] = m, cl
            for (h, s_), (npres, nreal, lc, lm) in agg.items():
                rows.append((str(d.date()), m0 + (h + 1) * H, s_, npres, nreal, lc, bool((lm - m0) % H == 59 * MIN)))
            log.info("aero sample %s: %d phut, %d sym-gio (%.0fs)", d.date(), len(Dd), len(agg), time.time() - t00)
    P = pd.DataFrame(rows, columns=["day", "ts", "sym", "nmin", "nmin_real", "lastc", "last_is_59"])
    P.to_parquet(os.path.join(WORK, "aero_sample.parquet"), index=False)
    log.info("aero done %d rows (%.0fs)", len(P), time.time() - t00)


# ───────────────────────── stage lineage ─────────────────────────
RATIOS = (1, 10, 100, 1000, 0.1, 0.01, 0.001, 60, 1 / 60, 24000, 1 / 24000)
END_ACTIVE = DEV_END_MS - DAY          # last_real >= 2025-12-31 00:00 -> con giao dich cuoi DEV
LIST0 = int(pd.Timestamp("2022-01-01").value // 10**6)
LIST1 = int(pd.Timestamp("2025-12-25").value // 10**6)   # R2 D_LAST = 2025-12-24


def _hourly_vol(S):
    """std log-ret 1h tren gio that (khong stale), de bat stable/fiat-like."""
    ts, sid, c = load_v(V1)
    fl = np.load(os.path.join(WORK, "flags_v1.npy"))
    n2 = names_map()
    order, sids, starts, ends = _sym_groups(sid, ts)
    out = {}
    for a, b in zip(starts, ends):
        ix = order[a:b]
        t, cc, f = ts[ix], c[ix], fl[ix]
        ok = (np.diff(t) == H) & ((f[1:] & (F_TAIL | F_GAP | F_HEAD)) == 0) & ((f[:-1] & (F_TAIL | F_GAP | F_HEAD)) == 0)
        lr = np.diff(np.log(cc))[ok]
        out[n2[int(sids[a])]] = float(np.std(lr)) if len(lr) > 48 else np.nan
    return out


def _vision_life():
    """Doi that theo Vision (gio volume>0): first/last, close tai do, gap >= 30 ngay giua 2 gio that."""
    z = np.load(os.path.join(WORK, "vision1h.npz"))
    n2 = names_map()
    k = z["v"] > 0
    ts, sid, c = z["ts"][k].astype(np.int64), z["sid"][k].astype(np.int64), z["c"][k]
    order, sids, starts, ends = _sym_groups(sid, ts)
    rows = {}
    for a, b in zip(starts, ends):
        ix = order[a:b]
        t = ts[ix]
        g = np.flatnonzero(np.diff(t) >= RELIST_H * H)
        rows[n2[int(sids[a])]] = dict(vfirst_ms=int(t[0]), vlast_ms=int(t[-1]), vfirst_c=float(c[ix][0]), vlast_c=float(c[ix][-1]),
                                      vgaps=["%s..%s (%dh)" % (tstr(t[i]), tstr(t[i + 1]), (t[i + 1] - t[i]) // H) for i in g])
    return rows


def _rename_candidates(S):
    cand = []
    for x in S.index:
        lx = S.at[x, "last_real_ms"]
        if lx >= END_ACTIVE:
            continue
        for y in S.index:
            fy = S.at[y, "first_real_ms"]
            known = RENAME.get(x, (None,))[0] == y
            if y == x or fy <= T0_MS or (not known and not (lx - 7 * DAY <= fy <= lx + 14 * DAY)):
                continue
            ratio = S.at[y, "first_real_close"] / S.at[x, "last_real_close"]
            cand.append(dict(old=x, new=y, old_last_real=tstr(lx), new_first_real=tstr(fy), dt_days=round((fy - lx) / DAY, 2),
                             ratio=float(ratio), ratio_match=bool(any(abs(ratio / m - 1) <= 0.10 for m in RATIOS)),
                             ratio_1to1=bool(abs(ratio - 1) <= 0.05),
                             in_window=bool(lx - 3 * DAY <= fy <= lx + 14 * DAY), known=bool(known)))
    return pd.DataFrame(cand)


def _first_last(S, R, x):
    """(first_real_ts, src, last_real_ts, src) — minute open UTC."""
    r = R.get(x, {})
    if S.at[x, "first_real_ms"] <= T0_MS:
        f, fs = None, "left_censored(<=2021-01-01 00:00, truoc dau du lieu)"
    elif r.get("first_real_min") is not None and S.at[x, "first_real_ms"] == S.at[x, "first_real_ms_v1"]:
        f, fs = r["first_real_min"], "aero_1m"
    else:
        f, fs = S.at[x, "first_real_ms"] - H, "vision_1h(open gio)"
    if r.get("last_real_min") is not None and S.at[x, "last_real_ms"] == S.at[x, "last_real_ms_v1"]:
        l, ls = r["last_real_min"], "aero_1m"
    else:
        l, ls = S.at[x, "last_real_ms"] - MIN, "vision_1h(phut cuoi gio)"
    return f, fs, l, ls


def stage_lineage():
    S = pd.read_csv(os.path.join(WORK, "stale_v1.csv")).set_index("symbol")
    R = json.load(open(os.path.join(WORK, "aero_refine.json")))
    try:
        G = pd.read_csv(os.path.join(WORK, "gaps_v1.csv"))
    except pd.errors.EmptyDataError:
        G = pd.DataFrame(columns=["symbol", "start", "end", "hours", "relist_like"])
    old = pd.read_csv(MAP_OLD) if os.path.exists(MAP_OLD) else pd.DataFrame(columns=["symId", "symbol"])
    oldm = dict(zip(old["symbol"].astype(str), old["symId"].astype(int))) if {"symbol", "symId"} <= set(old.columns) else {}
    hv = _hourly_vol(S)
    VL = _vision_life()
    for col in ("first_real_ms", "last_real_ms", "first_real_close", "last_real_close"):
        S[col + "_v1"] = S[col]
    for x in S.index:      # doi that = hop v1 (gio that) va Vision hien tai (v1 co the bi cat dau/cuoi)
        v = VL.get(x)
        if v and v["vfirst_ms"] < S.at[x, "first_real_ms"]:
            S.at[x, "first_real_ms"], S.at[x, "first_real_close"] = v["vfirst_ms"], v["vfirst_c"]
        if v and v["vlast_ms"] > S.at[x, "last_real_ms"]:
            S.at[x, "last_real_ms"], S.at[x, "last_real_close"] = v["vlast_ms"], v["vlast_c"]
    cand = _rename_candidates(S)
    cand.to_csv(os.path.join(WORK, "rename_candidates.csv"), index=False)
    new_from = {}
    for x, (y, note) in RENAME.items():
        if x in S.index and y in S.index and -7 * DAY <= S.at[y, "first_real_ms"] - S.at[x, "last_real_ms"] <= 60 * DAY:
            new_from.setdefault(y, []).append(x)       # ma moi niem yet <= 60 ngay sau khi ma cu dung -> khong phai listing that
    rel_gap = {}
    for g in G[G.relist_like.astype(bool)].itertuples():
        rel_gap.setdefault(g.symbol, []).append("v1 %s..%s (%dh)" % (g.start, g.end, g.hours))
    for x, v in VL.items():
        for s_ in v["vgaps"]:
            rel_gap.setdefault(x, []).append("Vision " + s_)
    z = np.load(FUND, allow_pickle=True)          # funding cache: ky funding dau tien som hon gio that dau >30 ngay -> ma cu
    fs_ = np.array([str(s) for s in z["syms"]])[z["sid"].astype(int)]
    fts = z["ts"].astype(np.int64)
    okf = fts > 1546300800000
    fmin = pd.Series(fts[okf]).groupby(fs_[okf]).min().to_dict()
    for x in S.index:
        fr0 = S.at[x, "first_real_ms"]
        if x in fmin and fr0 >= int(pd.Timestamp("2021-03-01").value // 10**6) and fmin[x] < fr0 - 30 * DAY:
            rel_gap.setdefault(x, []).append("funding_cache co ky tu %s, som hon gio that dau (%s) %d ngay" %
                                             (tstr(fmin[x]), tstr(fr0), (fr0 - fmin[x]) // DAY))
    rows = []
    for x in S.index:
        f, fs, l, ls = _first_last(S, R, x)
        notes, unc = [], []
        cx = cand[(cand.old == x) | (cand.new == x)] if len(cand) else cand
        delisted = bool(S.at[x, "last_real_ms"] < END_ACTIVE)
        if x in INDEX:
            status = "index"; notes.append(INDEX[x])
        elif x in STABLE:
            status = "stable/fiat-like"; notes.append(STABLE[x])
        elif x in RENAME:
            status = "renamed_to:" + RENAME[x][0]; notes.append(RENAME[x][1])
        elif x in new_from:
            status = "renamed_from:" + "+".join(new_from[x]); notes.append("; ".join(RENAME[o][1] for o in new_from[x]))
        elif x in RELIST or x in rel_gap:
            status = "relist"
            if x in RELIST:
                notes.append(RELIST[x])
            if x in rel_gap:
                notes.append("gap khong giao dich " + ", ".join(rel_gap[x]))
        else:
            status = "delisted" if delisted else "active"
        for c_ in cx.itertuples() if len(cx) else []:
            tag = "%s->%s dt=%+.1fd ratio=%.4g%s" % (c_.old, c_.new, c_.dt_days, c_.ratio, "" if c_.ratio_match else " (ratio lech)")
            if c_.known:
                notes.append("heuristic: " + tag)
                if not c_.in_window:
                    unc.append("rename da biet nhung ma moi niem yet ngoai cua so [-3d,+14d]: " + tag)
            elif c_.ratio_1to1 and c_.in_window:
                unc.append("ung vien rename heuristic (gia 1:1 +-5%, khong co trong danh sach da biet): " + tag)
        if x in UNSURE:
            unc.append(UNSURE[x])
        if x in RENAME and RENAME[x][0] not in S.index:
            unc.append("ma ke nhiem %s khong co trong CLOSES_1H" % RENAME[x][0])
        if np.isfinite(hv.get(x, np.nan)) and hv[x] < 0.002 and x not in STABLE and x not in INDEX:
            unc.append("bien dong 1h rat thap (std=%.4f) — co the stable/fiat-like" % hv[x])
        if x in rel_gap and x in RELIST:
            pass
        elif x in rel_gap and status != "relist":
            unc.append("co gap >=30 ngay: " + ", ".join(rel_gap[x]))
        if S.at[x, "first_real_ms"] < S.at[x, "first_real_ms_v1"] - DAY:
            unc.append("v1 THIEU dau doi: Vision co gio that tu %s (v1 tu %s) -> first_ts v1 khong phai listing" %
                       (tstr(S.at[x, "first_real_ms"]), tstr(S.at[x, "first_real_ms_v1"])))
        if S.at[x, "last_real_ms"] > S.at[x, "last_real_ms_v1"] + DAY:
            unc.append("v1 THIEU cuoi doi: Vision co gio that toi %s (v1 toi %s)" %
                       (tstr(S.at[x, "last_real_ms"]), tstr(S.at[x, "last_real_ms_v1"])))
        if S.at[x, "n_unver"] > 0.2 * S.at[x, "n_rec"]:
            unc.append("%d/%d record khong co trong Vision hien tai (volume chua kiem)" % (S.at[x, "n_unver"], S.at[x, "n_rec"]))
        fr_ms = S.at[x, "first_real_ms"]
        lflag = bool(fr_ms > T0_MS and LIST0 <= fr_ms - H < LIST1 and not status.startswith("renamed_from")
                     and status not in ("index", "stable/fiat-like", "relist"))
        rows.append(dict(symbol=x, symId=int(S.at[x, "symId"]), symId_old_map=oldm.get(x), first_ts_v1=S.at[x, "first_ts"],
                         last_ts_v1=S.at[x, "last_ts"], first_real_ts=tstr(f), first_real_src=fs, last_real_ts=tstr(l),
                         last_real_src=ls, first_real_h_v1=tstr(S.at[x, "first_real_ms_v1"]),
                         last_real_h_v1=tstr(S.at[x, "last_real_ms_v1"]), status=status, delisted_in_dev=delisted, listing_flag=lflag,
                         tail_stale_h=int(S.at[x, "tail_stale_h"]), n_gap24=int(S.at[x, "n_gap24"]), h_gap24=int(S.at[x, "h_gap24"]),
                         head_stale_h=int(S.at[x, "head_stale_h"]), std_1h=round(hv.get(x, np.nan), 5),
                         uncertain=" | ".join(unc), notes=" | ".join(notes),
                         source="v1 CLOSES_1H x Binance Vision 1h volume (2026-10-03) + Aerospike kline_1m_opt (phut v>0)"))
    Lg = pd.DataFrame(rows).sort_values("symbol")
    os.makedirs(META, exist_ok=True)
    Lg.to_csv(os.path.join(META, "symbol_lineage_v2.csv"), index=False)
    log.info("lineage status %s; listing_flag=%d; uncertain=%d", Lg.status.str.split(":").str[0].value_counts().to_dict(),
             int(Lg.listing_flag.sum()), int((Lg.uncertain != "").sum()))
    _listing_clean(Lg)


PRIOR16 = ['RENDERUSDT', 'POLUSDT', 'KAIAUSDT', 'SUSDT', 'AUSDT', 'SKYUSDT', 'GUSDT', 'FORMUSDT',
           'FOOTBALLUSDT', 'BLUEBIRDUSDT', 'PAXGUSDT', 'XAUUSDT', '1000LUNCUSDT', 'USTCUSDT', 'BSVUSDT', 'RAYSOLUSDT']


def _listing_clean(Lg):
    import short_v3_r2_listing as R2
    C, names, t_start, _ = R2.load_hourly()
    L, gap, _, _, _, _ = R2.find_listings(C, names, t_start, {})
    del C
    r2 = {r["sym"]: R2.dstr(r["D0"]) for r in L}
    r2g = {r["sym"] for r in gap}
    rows = []
    for r in Lg.itertuples():
        fr = pd.Timestamp(r.first_real_ts).value // 10**6 if isinstance(r.first_real_ts, str) else None
        inwin = fr is not None and LIST0 <= fr < LIST1
        if not (inwin or r.symbol in r2 or r.symbol in r2g):
            continue
        univ = r.symbol.endswith("USDT") and "_" not in r.symbol and r.symbol != "BTCUSDT"
        v1f = pd.Timestamp(r.first_real_h_v1).value // 10**6 - H
        head_cut = fr is not None and v1f > fr + DAY          # v1 bat dau muon hon gio that dau tien -> listing_day v1 sai
        keep = bool(r.listing_flag and univ and not head_cut)
        why = "" if keep else (r.status if r.status not in ("active", "delisted") else
                               ("ngoai universe USDT" if not univ else
                                ("listing_day v1 sai: v1 thieu dau doi (that tu %s)" % r.first_real_ts if head_cut
                                 else "first_real ngoai cua so 2022-01-01..2025-12-24")))
        rows.append(dict(symbol=r.symbol, first_real_ts=r.first_real_ts, first_real_src=r.first_real_src, first_ts_v1=r.first_ts_v1,
                         r2_D0_v1=r2.get(r.symbol), r2_gap_excluded=r.symbol in r2g, status=r.status, keep=keep, reason_excluded=why,
                         uncertain=r.uncertain))
    Lc = pd.DataFrame(rows).sort_values(["keep", "first_real_ts"], ascending=[False, True])
    Lc.to_csv(os.path.join(META, "listing_clean_v2.csv"), index=False)
    inr2 = Lc[Lc.r2_D0_v1.notna()]
    drop = sorted(inr2[~inr2.keep].symbol)
    info = dict(n_r2_L=len(r2), n_r2_gap=len(r2g), n_keep=int(Lc.keep.sum()), n_r2_dropped=len(drop), r2_dropped=drop,
                prior16_in_dropped=sorted(set(PRIOR16) & set(drop)), prior16_not_dropped=sorted(set(PRIOR16) - set(drop)),
                keep_not_in_r2=sorted(Lc[Lc.keep & Lc.r2_D0_v1.isna()].symbol))
    json.dump(info, open(os.path.join(WORK, "listing_info.json"), "w"), indent=1)
    log.info("listing_clean %s", info)


# ───────────────────────── stage build ─────────────────────────
def stage_build():
    for p in (V2, V2M):
        if os.path.exists(p) and os.environ.get("FORCE_V2") != "1":
            raise SystemExit("%s da ton tai — khong ghi de (FORCE_V2=1 neu chinh script nay tao)" % p)
    a = np.fromfile(V1, dtype=DT)
    fl = np.load(os.path.join(WORK, "flags_v1.npy"))
    assert len(fl) == len(a)
    drop = (fl & (F_TAIL | F_HEAD)) > 0
    isnan = (fl & F_GAP) > 0
    b = a[~drop].copy()
    b["c"][isnan[~drop]] = np.nan
    b.tofile(V2)
    mk = np.flatnonzero(fl > 0)
    m = np.empty(len(mk), dtype=MDT)
    m["ts"], m["sym"], m["flag"] = a["ts"][mk], a["sym"][mk], fl[mk]
    m.tofile(V2M)
    log.info("v2 ghi %d rec (bo %d, NaN %d); mask %d rec", len(b), int(drop.sum()), int(isnan.sum()), len(m))
    chk = _build_checks(a, drop, isnan)
    man = dict(created_utc=str(pd.Timestamp.utcnow())[:19], script="research/analysis/data_audit_v2.py (stage build)",
               rule=dict(tail="record sau last_real (gio Vision volume>0 cuoi cung; neu Vision thieu record: close dung yen) -> BO",
                         head="record truoc first_real (volume=0) -> BO",
                         gap="run khong giao dich (volume=0 / close dung yen khi Vision thieu) >= %dh giua chuoi -> close=NaN" % GAP_H,
                         short="run < %dh -> giu, chi danh dau mask" % GAP_H),
               format="14 B/rec big-endian [ts:int64 close-time ms][symId:int16][close:float32], sort (ts, ten symbol) nhu v1",
               mask_format="11 B/rec big-endian [ts:int64][symId:int16][flag:uint8], chi record v1 co flag != 0",
               flags={str(k): v for k, v in FLAG_DOC.items()}, symbol_map=MAP,
               v1=dict(path=V1, md5=md5(V1), n_rec=int(len(a)), bytes=os.path.getsize(V1)),
               v2=dict(path=V2, md5=md5(V2), n_rec=int(len(b)), n_nan=int(isnan.sum()), bytes=os.path.getsize(V2)),
               mask=dict(path=V2M, md5=md5(V2M), n_rec=int(len(m)), bytes=os.path.getsize(V2M)),
               vision_snapshot=json.load(open(os.path.join(WORK, "vision_info.json"))), checks=chk)
    for f in ("symbol_lineage_v2.csv", "listing_clean_v2.csv"):
        man[f] = dict(path="data/meta/" + f, md5=md5(os.path.join(META, f)))
    json.dump(man, open(os.path.join(META, "DATA_MANIFEST_v2.json"), "w"), indent=1, ensure_ascii=False)
    log.info("manifest %s", json.dumps({k: man[k] for k in ("v1", "v2", "mask")}))


def _build_checks(a, drop, isnan):
    import importlib
    b = np.fromfile(V2, dtype=DT)
    ts = b["ts"].astype(np.int64)
    key = ts * 1024 + b["sym"].astype(np.int64)
    chk = dict(n_rec=int(len(b)), ts_sorted=bool((np.diff(ts) >= 0).all()), dup_keys=int(len(key) - len(np.unique(key))),
               max_ts=tstr(ts.max()), n_nan=int(np.isnan(b["c"]).sum()), n_nan_expected=int(isnan.sum()),
               subset_identical=bool(np.array_equal(np.nan_to_num(b["c"][~np.isnan(b["c"])]),
                                                    a["c"][~drop & ~isnan])))
    P = importlib.import_module("short_v2_p0a_statemap")
    R2 = importlib.import_module("short_v3_r2_listing")
    TR = importlib.import_module("trend_rank_ic")
    old = (P.CLOSES, R2.CLOSES, TR.CLOSES)
    try:
        P.CLOSES = V2
        C, names, t0 = P.load_hourly()
        chk["p0a_load_hourly"] = dict(shape=list(C.shape), n_sym=len(names), finite=int(np.isfinite(C).sum()))
        del C
        R2.CLOSES = V2
        C, names, t0, info = R2.load_hourly()
        chk["r2_load_hourly"] = dict(info, note="assert luoi 1h PASS; n_rows_bad = so record NaN bi loai")
        del C
        TR.CLOSES = V2
        df = TR.load_closes()
        chk["trend_rank_ic_load_closes"] = dict(n=int(len(df)), n_nan_close=int(df.close.isna().sum()),
                                                note="loader dang dai KHONG loc NaN -> NaN lan vao rolling (on, khong am tham)")
    finally:
        P.CLOSES, R2.CLOSES, TR.CLOSES = old
    log.info("checks %s", chk)
    return chk


# ───────────────────────── stage audit ─────────────────────────
def _holes(t, s, fin):
    t, s = t[fin], s[fin]
    o = np.lexsort((t, s))
    t, s = t[o], s[o]
    same = s[1:] == s[:-1]
    h = (np.diff(t) // H - 1)[same]
    h = h[h > 0]
    bk = [(1, 1), (2, 5), (6, 23), (24, 167), (168, 719), (720, 10 ** 9)]
    return {"%d-%s" % (lo, hi if hi < 10 ** 9 else "inf"): dict(n=int(((h >= lo) & (h <= hi)).sum()),
                                                               hours=int(h[(h >= lo) & (h <= hi)].sum())) for lo, hi in bk}


def _month_active(t, s, fin):
    m = t[fin].astype("datetime64[ms]").astype("datetime64[M]")
    d = pd.DataFrame(dict(m=m, s=s[fin])).drop_duplicates()
    return d.groupby("m").s.size()


def _aud_cov(out):
    t1, s1, c1 = load_v(V1)
    t2, s2, c2 = load_v(V2)
    f1, f2 = np.isfinite(c1), np.isfinite(c2)
    y1 = t1.astype("datetime64[ms]").astype("datetime64[Y]").astype(int) + 1970
    y2 = t2.astype("datetime64[ms]").astype("datetime64[Y]").astype(int) + 1970
    out["coverage_sym_hours_by_year"] = {str(y): dict(v1=int((y1 == y).sum()), v2_finite=int((f2 & (y2 == y)).sum()),
                                                      v2_nan=int((~f2 & (y2 == y)).sum()), removed=int((y1 == y).sum() - (y2 == y).sum()))
                                         for y in range(2021, 2027)}
    a1, a2 = _month_active(t1, s1, f1), _month_active(t2, s2, f2)
    A = pd.DataFrame(dict(v1=a1, v2=a2)).fillna(0).astype(int)
    A["diff"] = A.v1 - A.v2
    out["active_sym_by_month"] = {str(k)[:7]: list(map(int, v)) for k, v in A.iterrows()}
    out["holes_v1"] = _holes(t1, s1, f1)
    out["holes_v2_finite"] = _holes(t2, s2, f2)
    log.info("coverage %s", out["coverage_sym_hours_by_year"])
    return t2, s2, c2


def _aud_outliers(out, A, t2, s2, c2, n2):
    o = np.lexsort((t2, s2))
    t, s, c = t2[o], s2[o], c2[o]
    ok = (s[1:] == s[:-1]) & (np.diff(t) == H) & np.isfinite(c[1:]) & np.isfinite(c[:-1])
    r = c[1:] / c[:-1] - 1
    ix = np.flatnonzero(ok & (np.abs(r) > 0.5)) + 1
    want = {}
    for i in ix:
        for m in (t[i] - MIN, t[i] - H - MIN):
            want.setdefault(int(m), set()).add(n2[int(s[i])])
    D = A.get(list(want), want=want)
    rows = []
    for i in ix:
        nm = n2[int(s[i])]
        a1 = D.get(int(t[i] - MIN), {}).get(nm); a0 = D.get(int(t[i] - H - MIN), {}).get(nm)
        ra = None if (a1 is None or a0 is None) else a1[0] / a0[0] - 1
        rows.append(dict(symbol=nm, ts=tstr(t[i]), ret_v2=float(r[i - 1]), ret_aero=ra,
                         match=None if ra is None else bool(abs(c[i] / a1[0] - 1) < 1e-3 and abs(c[i - 1] / a0[0] - 1) < 1e-3)))
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(WORK, "outliers_v2_vs_aero.csv"), index=False)
    out["outliers_v2"] = dict(n=len(R), n_checked=int(R.match.notna().sum()) if len(R) else 0,
                              n_match=int((R.match == True).sum()) if len(R) else 0,  # noqa: E712
                              n_mismatch=int((R.match == False).sum()) if len(R) else 0,  # noqa: E712
                              mismatch=R[R.match == False].head(30).to_dict("records") if len(R) else [])  # noqa: E712
    log.info("outliers %s", {k: v for k, v in out["outliers_v2"].items() if k != "mismatch"})


def _aud_spot(out, A, t2, s2, c2, n2):
    rng = np.random.default_rng(20261003)
    fin = np.isfinite(c2) & (t2 <= DEV_END_MS)
    cnt = pd.Series(s2[fin]).value_counts()
    pool = sorted(int(x) for x in cnt.index[cnt >= 48])
    pick = rng.choice(pool, 30, replace=False)
    rows, want, plan = [], {}, []
    for sid in pick:
        tt = t2[fin & (s2 == sid)]
        days = np.unique((tt - 1) // DAY)
        d = int(rng.choice(days))
        hrs = [d * DAY + (h + 1) * H for h in range(24)]
        plan.append((int(sid), d, hrs))
        for th in hrs:
            want.setdefault(th - MIN, set()).add(n2[int(sid)])
    D = A.get(list(want), want=want)
    for sid, d, hrs in plan:
        nm = n2[sid]
        m2 = dict(zip(t2[(s2 == sid) & np.isin(t2, hrs)], c2[(s2 == sid) & np.isin(t2, hrs)]))
        rel = []
        for th in hrs:
            a = D.get(th - MIN, {}).get(nm)
            v = m2.get(th)
            if a is not None and v is not None and np.isfinite(v):
                rel.append(abs(v / a[0] - 1))
        rows.append(dict(symbol=nm, day=str(pd.Timestamp(d * DAY, unit="ms").date()), n_v2=len(m2), n_cmp=len(rel),
                         max_rel=float(max(rel)) if rel else None, n_gt_1e4=int(sum(x > 1e-4 for x in rel))))
    out["spot30"] = rows
    log.info("spot30 n_cmp=%d max_rel=%s n_gt=%d", sum(r["n_cmp"] for r in rows),
             max((r["max_rel"] or 0) for r in rows), sum(r["n_gt_1e4"] for r in rows))


def _aud_funding(out, Lg):
    z = np.load(FUND, allow_pickle=True)
    syms = [str(x) for x in z["syms"]]
    ts = z["ts"].astype(np.int64); rt = z["rt"].astype(np.float64); sid = z["sid"].astype(np.int64)
    F = pd.DataFrame(dict(sym=np.array(syms)[sid], ts=ts, rt=rt))
    bad_ts = F[(F.ts < 1546300800000) | (F.ts > DEV_END_MS)]
    ext = F[(F.rt.abs() > 0.03)].sort_values("rt")
    res = dict(n=len(F), n_sym=int(F.sym.nunique()), n_bad_ts=len(bad_ts), bad_ts=bad_ts.head(10).astype(str).to_dict("records"),
               n_ts_not_on_hour=int((F.ts % H != 0).sum()), n_dup=int(F.duplicated(["sym", "ts"]).sum()),
               n_rate_out_3pct=len(ext), rate_out_3pct=ext.head(15).astype(str).to_dict("records"),
               rate_q=[float(x) for x in np.percentile(F.rt, [0.01, 0.1, 50, 99.9, 99.99])])
    F = F[(F.ts >= 1546300800000) & (F.ts <= DEV_END_MS)].sort_values(["sym", "ts"])
    d = F.groupby("sym").ts.diff()
    gap = d > 8 * H + 5 * MIN
    res["n_gap_gt8h"] = int(gap.sum()); res["n_sym_gap_gt8h"] = int(F.sym[gap].nunique())
    res["missing_periods_lb"] = int(((d[gap] // (8 * H)) - 1).clip(lower=0).sum() + gap.sum() * 0)
    g = F.groupby("sym").ts.agg(["min", "max", "size"])
    L = Lg.set_index("symbol")
    cmp = g.join(L[["first_real_ts", "last_real_ts", "status"]], how="right")
    lr = pd.to_datetime(cmp.last_real_ts).astype("int64") // 10**6
    fr = pd.to_datetime(cmp.first_real_ts).astype("int64") // 10**6
    res["n_v1sym_no_funding"] = int(cmp["size"].isna().sum())
    res["v1sym_no_funding"] = sorted(cmp.index[cmp["size"].isna()])[:40]
    res["n_sym_funding_after_last_real_8h"] = int((cmp["max"] > lr + 8 * H).sum())
    res["sym_funding_after_last_real_8h"] = sorted(cmp.index[cmp["max"] > lr + 8 * H])[:40]
    res["n_sym_funding_before_first_real"] = int((cmp["min"] < fr - H).sum())
    out["funding"] = res
    log.info("funding %s", {k: v for k, v in res.items() if not isinstance(v, list)})


def _aud_qv(out, Lg, t2, s2, c2, n2):
    q = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(QVDIR + "/*.parquet"))], ignore_index=True)
    q["date"] = pd.to_datetime(q["date"])
    nrec = q.groupby("date").nrec.max()
    L = Lg.set_index("symbol")
    q = q.join(L[["first_real_ts", "last_real_ts"]], on="sym")
    lr = pd.to_datetime(q.last_real_ts).dt.normalize()
    after = q.date > lr
    res = dict(n_rows=len(q), date_range=[str(q.date.min().date()), str(q.date.max().date())], n_sym=int(q.sym.nunique()),
               n_days_nrec_lt1440=int((nrec < 1440).sum()), n_days_nrec_lt1000=int((nrec < 1000).sum()),
               days_nrec_lt1000=[str(d.date()) for d in nrec[nrec < 1000].index][:30],
               n_qv0=int((q.qv == 0).sum()), n_qv_nan=int(q.qv.isna().sum()), n_sym_qv0=int(q.sym[q.qv == 0].nunique()),
               n_qv0_after_last_real=int(((q.qv == 0) & after).sum()), n_qv0_inside_life=int(((q.qv == 0) & ~after & q.last_real_ts.notna()).sum()),
               n_qvpos_after_last_real=int(((q.qv > 0) & after).sum()), n_sym_not_in_v1=int(q.last_real_ts.isna().groupby(q.sym).all().sum()))
    # ngay co close v1/v2 nhung qv cache = 0 / khong co
    fin = np.isfinite(c2)
    dd = pd.DataFrame(dict(sym=np.array([n2[int(x)] for x in np.unique(s2)])[np.searchsorted(np.unique(s2), s2[fin])],
                           date=pd.to_datetime((t2[fin] - 1) // DAY * DAY, unit="ms"))).drop_duplicates()
    m = dd.merge(q[["sym", "date", "qv"]], on=["sym", "date"], how="left")
    m = m[m.date >= pd.Timestamp("2021-09-01")]
    res["v2_days_with_qv0"] = int((m.qv == 0).sum()); res["v2_days_no_qv_row"] = int(m.qv.isna().sum())
    res["v2_days_total"] = len(m)
    out["qv_cache"] = res
    log.info("qv %s", {k: v for k, v in res.items() if not isinstance(v, list)})


def _aud_sample(out, n2):
    P = pd.read_parquet(os.path.join(WORK, "aero_sample.parquet"))
    uni = set(n2[int(x)] for x in np.unique(load_v(V1)[1]))
    P = P[P.sym.isin(uni)]
    tsset = np.unique(P.ts.to_numpy())
    res = {}
    for tag, path in (("v1", V1), ("v2", V2)):
        t, s, c = load_v(path)
        k = np.isin(t, tsset) & np.isfinite(c)
        V = pd.DataFrame(dict(ts=t[k], sym=[n2[int(x)] for x in s[k]], c=c[k]))
        M = P.merge(V, on=["ts", "sym"], how="outer", indicator=True)
        M["year"] = pd.to_datetime(M.ts, unit="ms").dt.year
        real = M.nmin_real.fillna(0) > 0
        inv = M._merge != "left_only"
        r = {}
        for y, g in M.groupby("year"):
            rg, ig = real[g.index], inv[g.index]
            r[str(y)] = dict(aero_real=int(rg.sum()), file=int(ig.sum()), missing_in_file=int((rg & ~ig).sum()),
                             file_not_real=int((ig & ~rg).sum()),
                             pct_missing=round(100 * float((rg & ~ig).sum()) / max(int(rg.sum()), 1), 3),
                             pct_file_not_real=round(100 * float((ig & ~rg).sum()) / max(int(ig.sum()), 1), 3))
        cm = M[inv & M.last_is_59.fillna(False).astype(bool) & M.lastc.notna()]
        rel = (cm.c / cm.lastc - 1).abs()
        r["close_vs_aero_last59"] = dict(n=len(cm), n_gt_1e4=int((rel > 1e-4).sum()), max_rel=float(rel.max()) if len(rel) else None)
        res[tag] = r
    out["sample_1day_per_month"] = res
    log.info("sample %s", json.dumps(res)[:3000])


def stage_audit():
    t00 = time.time()
    n2 = names_map()
    Lg = pd.read_csv(os.path.join(META, "symbol_lineage_v2.csv"))
    out = {}
    t2, s2, c2 = _aud_cov(out)
    A = Aero()
    _aud_outliers(out, A, t2, s2, c2, n2)
    _aud_spot(out, A, t2, s2, c2, n2)
    _aud_funding(out, Lg)
    _aud_qv(out, Lg, t2, s2, c2, n2)
    _aud_sample(out, n2)
    json.dump(out, open(os.path.join(WORK, "audit.json"), "w"), indent=1, ensure_ascii=False, default=str)
    log.info("audit done (%.0fs)", time.time() - t00)


# ───────────────────────── stage impact ─────────────────────────
def _pick(d, ks):
    return {k: d.get(k) for k in ks}


def _imp_p0a(path):
    import short_v2_p0a_statemap as P
    old, P.CLOSES = P.CLOSES, path
    try:
        res, df, S, close = P.stage_run()
        res = P.tables(res, df, S)
    finally:
        P.CLOSES = old
    k = {}
    for T in P.T_LIST:
        k["ALL|%d" % T] = _pick(res["A"]["ALL|%d" % T], ("n", "bleed_mean", "bleed_med", "pSQ10", "netproxy", "fund", "ci_raw", "ci_infl"))
        for y in (2022, 2023, 2024, 2025):
            k["ALL|%d|%d" % (T, y)] = _pick(res["B"]["ALL|%d|%d" % (T, y)], ("n", "bleed_mean", "pSQ10", "netproxy"))
    for g in ("LIQ", "BTCF", "BLEED", "BLEED'", "FLAT"):
        k["%s|7" % g] = _pick(res["A"]["%s|7" % g], ("n", "bleed_mean", "excess", "pSQ10", "netproxy", "ci_raw", "ci_infl"))
    k["F_kill"] = res["F_kill"]; k["verdict"] = res["verdict"]; k["cover"] = res["cover"]
    k["obs_by_T"] = {str(T): v["n_trunc"] for T, v in res["sanity"]["S_a"]["obs_by_T"].items()}
    d7 = df[df["T"] == 7][["date", "sym", "ret", "trunc"]].copy()
    del df
    return k, d7


def _imp_r3(path):
    import short_v2_p0a_statemap as P
    import short_v3_r3_breakdown as R3
    old, P.CLOSES = P.CLOSES, path
    try:
        res, df = R3.run()
        res = R3.tables(res, df)
    finally:
        P.CLOSES = old
    del df
    k = {kk: _pick(v, ("n", "bleed_mean", "excess_short", "excess_pnl", "pSQ10", "netproxy", "ci_raw", "years_pos"))
         for kk, v in res["A"].items() if kk.split("|")[0] in ("BRK", "BNV", "ALL")}
    k["E_go"] = res["E_go"]; k["verdict"] = res["verdict"]
    return k


def _imp_r2(path):
    import short_v3_r2_listing as R2
    old, R2.CLOSES = R2.CLOSES, path
    try:
        C, names, t_start, _ = R2.load_hourly()
        fund = R2.Fund()
        L, gap, _, ucols, fl, _ = R2.find_listings(C, names, t_start, {})
        usd_all = np.array([i for i, n in enumerate(names) if n.endswith("USDT") and "_" not in n])
        ren = R2.rename_like(L, names, usd_all, fl)
        D, _ = R2.build_arms(C, names, t_start, L, ucols, fund)
        st = R2.strategy(D, ren)
    finally:
        R2.CLOSES = old
    del C
    d0 = D["D0"][["sym", "t0", "ret7", "all_ret7", "n_all", "excess", "pnl", "year"]].copy()
    return dict(n_L=len(L), rename_like=ren, D0=_pick(st["D0"]["all"], ("n", "mean", "ret7_mean", "excess_mean", "excess_med", "ci_raw",
                                                                      "excess_ci_raw")), D0_GO=st["D0"]["GO"],
                D1_GO=st["D1"]["GO"]), d0


def stage_impact():
    if os.path.exists(LOCK):
        raise SystemExit("LOCK ton tai: %s" % open(LOCK).read())
    open(LOCK, "w").write("data_audit_v2 impact pid %d" % os.getpid())
    t00, out, d7, d0 = time.time(), {}, {}, {}
    try:
        for tag, path in (("v1", V1), ("v2", V2)):
            out["p0a_" + tag], d7[tag] = _imp_p0a(path)
            log.info("P0A %s ALL|7 %s verdict %s (%.0fs)", tag, out["p0a_" + tag]["ALL|7"], out["p0a_" + tag]["verdict"], time.time() - t00)
            out["r3_" + tag] = _imp_r3(path)
            log.info("R3 %s %s (%.0fs)", tag, out["r3_" + tag]["verdict"], time.time() - t00)
            out["r2_" + tag], d0[tag] = _imp_r2(path)
            log.info("R2 %s %s (%.0fs)", tag, out["r2_" + tag]["D0"], time.time() - t00)
    finally:
        os.remove(LOCK)
    m = d7["v1"].merge(d7["v2"], on=["date", "sym"], how="outer", suffixes=("_1", "_2"), indicator=True)
    both = m[m._merge == "both"]
    ch = (both.ret_1 - both.ret_2).abs() > 1e-9
    out["p0a_obs7_diff"] = dict(n_v1=len(d7["v1"]), n_v2=len(d7["v2"]), only_v1=int((m._merge == "left_only").sum()),
                                only_v2=int((m._merge == "right_only").sum()), ret_changed=int(ch.sum()),
                                syms_only_v1=sorted(m[m._merge == "left_only"].sym.unique())[:40],
                                syms_ret_changed=sorted(both[ch].sym.unique())[:40])
    r = d0["v1"].merge(d0["v2"], on=["sym", "t0"], suffixes=("_1", "_2"), how="outer", indicator=True)
    rb = r[r._merge == "both"]
    da = rb.all_ret7_2 - rb.all_ret7_1
    out["r2_d0_diff"] = dict(n_v1=len(d0["v1"]), n_v2=len(d0["v2"]), n_both=len(rb), d_all_mean=float(da.mean()),
                             d_all_absmax=float(da.abs().max()), d_nall_mean=float((rb.n_all_2 - rb.n_all_1).mean()),
                             excess_v1=float(rb.excess_1.mean()), excess_v2=float(rb.excess_2.mean()),
                             d_pnl_absmax=float((rb.pnl_2 - rb.pnl_1).abs().max()))
    out.update(_imp_r2b(rb))
    out.update(_imp_repro(out))
    json.dump(out, open(os.path.join(WORK, "impact.json"), "w"), indent=1, ensure_ascii=False, default=str)
    log.info("impact done (%.0fs) %s", time.time() - t00, json.dumps({k: out[k] for k in ("p0a_obs7_diff", "r2_d0_diff")}, default=str))


def _imp_r2b(rb):
    r = json.load(open(os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R2B.json")))
    tr = r["trades"]
    if isinstance(tr, dict):
        log.info("R2B trades keys %s", list(tr.keys()))
        tr = tr.get("D0", next(iter(tr.values())))
    T = pd.DataFrame(tr)
    if "arm" in T.columns:
        T = T[T.arm == "D0"]
    d = pd.DataFrame(dict(sym=rb.sym.to_numpy(), t0=rb.t0.to_numpy(), d_all=(rb.all_ret7_2 - rb.all_ret7_1).to_numpy()))
    T = T.merge(d, on=["sym", "t0"], how="left")
    T["excess_v2"] = T.excess + T.d_all.fillna(0)
    ex = ~T.sym.isin(PRIOR16)
    st = r.get("strategy", {}).get("D0", {}).get("all", {})
    import short_v3_r2b_listing1m as RB
    Lc = pd.read_csv(os.path.join(META, "listing_clean_v2.csv"))
    drop_clean = sorted(Lc[Lc.r2_D0_v1.notna() & ~Lc.keep.astype(bool)].symbol)
    dt = pd.to_datetime(T.t0, unit="ms")
    T["mi"] = (dt.dt.year - 2022) * 12 + dt.dt.month - 1
    arms = {}
    for tag, exl in (("all", []), ("-16", PRIOR16), ("-clean_v2(%d)" % len(drop_clean), drop_clean)):
        for ev, col in (("v1", "excess"), ("v2", "excess_v2")):
            g = T[~T.sym.isin(exl)].copy().reset_index(drop=True)
            g["excess"] = g[col]
            a = RB.arm_stats(g, "net1m", "sl1m", "fund1m")
            arms["D0 %s excess_%s" % (tag, ev)] = dict(n=int(len(g)), mean=a["all"]["mean"], ci_raw=a["all"]["ci_raw"],
                                                       ci_infl=a["all"]["ci_infl"], years_pos=a["GO"]["G2_years_pos"],
                                                       drop10=a["GO"]["G5_drop10_mean"], excess=a["all"]["excess_mean"],
                                                       G=[a["GO"][k] for k in ("G1", "G2", "G3", "G4", "G5")], GO=a["GO"]["PASS"])
            log.info("R2B %s %s", "D0 %s excess_%s" % (tag, ev), arms["D0 %s excess_%s" % (tag, ev)])
    return {"r2b_arms": arms, "r2b_drop_clean": drop_clean, "r2b_excess": dict(n=len(T), n_matched=int(T.d_all.notna().sum()), excess_json=st.get("excess_mean"),
                               excess_v1=float(T.excess.mean()), excess_v2=float(T.excess_v2.mean()),
                               excess_v1_ex16=float(T.excess[ex].mean()), excess_v2_ex16=float(T.excess_v2[ex].mean()),
                               G4_v1=bool(T.excess.mean() > 0), G4_v2=bool(T.excess_v2.mean() > 0),
                               note="excess_v2 = excess_v1 + (all_ret7_v2 - all_ret7_v1) cung (sym,t0); phan coin khong doi")}


def _imp_repro(out):
    R = os.path.join(REPO, "docs/result/")
    p = json.load(open(R + "RESULT_SHORT_V2_P0A.json"))
    r3 = json.load(open(R + "RESULT_SHORT_V3_R3.json"))
    r2 = json.load(open(R + "RESULT_SHORT_V3_R2.json"))
    a, b = p["A"]["ALL|7"], out["p0a_v1"]["ALL|7"]
    e3 = {k: (v["netproxy"], v["excess_short"]) for k, v in r3["E_go"].items()}
    f3 = {k: (v["netproxy"], v["excess_short"]) for k, v in out["r3_v1"]["E_go"].items()}
    return {"repro_v1": dict(p0a_ALL7_json=[a["n"], a["bleed_mean"], a["pSQ10"]], p0a_ALL7_rerun=[b["n"], b["bleed_mean"], b["pSQ10"]],
                             p0a_verdict_json=p["verdict"], r3_json=e3, r3_rerun=f3, r3_verdict_json=r3["verdict"],
                             r2_D0_json=[r2["strategy"]["D0"]["all"]["n"], r2["strategy"]["D0"]["all"]["mean"],
                                         r2["strategy"]["D0"]["all"]["excess_mean"]],
                             r2_D0_rerun=[out["r2_v1"]["D0"]["n"], out["r2_v1"]["D0"]["mean"], out["r2_v1"]["D0"]["excess_mean"]],
                             r2_verdict_json=r2["verdict"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="+", choices=["vision", "scan", "aero", "lineage", "build", "audit", "impact"])
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.makedirs(WORK, exist_ok=True)
    for s in a.stages:
        globals()["stage_" + s]()


if __name__ == "__main__":
    main()
