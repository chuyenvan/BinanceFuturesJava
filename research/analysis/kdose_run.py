#!/usr/bin/env python3
"""KDOSE — D2/D3: lieu-dap ung loi nen phut luc quyet dinh. Pre-reg docs/prereg/PREREG_KDOSE.md (403f3302).

Du lieu dung T = ticker HO26 (=242) + sua bang Vision (kho loi kdose_data.py d1). Engine feature gate = devexport_202609.Engine +
features_row (port KDIV D4a) nuoi tu RAM; md INLINE vector hoa (kiem bit-exact voi md_inline.InlineMD). ONNX fold_20. Gate G0/G1/G2.
0 cham 242 (funding/mapper = pickle tu Aerospike Oracle-local), 0 REST, 0 Java. Stage: base | d2 | report.
"""
import glob, gzip, json, logging, math, os, pickle, sys, time
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
sys.path.insert(0, "/home/ubuntu/claude_master/1010/kdose")
import kdose_data as KD          # noqa: E402
import devexport_202609 as dx    # noqa: E402
import md_inline                 # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kdose")
WD = KD.WD
MN, H, D, TZ, U0, NM = KD.MN, KD.H, KD.D, KD.TZ, KD.U0, KD.NM
IW0, IW1, IG0 = KD.IW0, KD.IW1, KD.IG0
I_START = IW0 - 2880                                   # warm-up 48 h (nhu devexport WARMUP_HOURS)
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"
BINS = "/home/ubuntu/claude_master/1009/ho26/bins2026Ax"
SYMMAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
KDIV = "/home/ubuntu/claude_master/1003/kdiv"
OUTK = "/home/ubuntu/kaggle_sim/out/"
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
FEATS = dx.V3FULL
DYN_MIN, SCORE_BASE, DYN_MULT = np.float32(0.26787), np.float32(0.15), np.float32(1.28760)
GS, PCT, BASE = np.float32(1.55), np.float32(0.999950829), np.float32(0.008)
GRID = [0.005, 0.01, 0.02, 0.05, 0.15]
NREP, SEED0 = 20, 20261010
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
ALPHA, FLOORF = 0.5, 0.25
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT"}
COST, PEN, CRASH = 0.000982 + 2 * 0.000067, 0.01675, -0.01
G = {}


def load_ticker_T(workers=3, nsmax=760):
    """-> PT[NM, nsym, 5] float32 (bo cuc theo phut: doc 1 phut lien tuc), names."""
    days = [x.strftime("%Y%m%d") for x in pd.date_range(pd.Timestamp(U0, unit="ms"), periods=70, freq="D")]
    SI, t0 = {}, time.time()
    with Pool(workers) as pool:
        PT = np.full((NM, nsmax, 5), np.nan, np.float32)
        for day, syms, A in pool.imap_unordered(KD.parse_day, days):
            assert syms is not None, day
            g0 = (int(pd.Timestamp(day).value // 10 ** 6) - U0) // MN
            idx = np.array([SI.setdefault(s, len(SI)) for s in syms])
            assert len(SI) <= nsmax, len(SI)
            PT[g0:g0 + 1440, idx, :] = A.transpose(2, 0, 1)
    names = [None] * len(SI)
    for s, i in SI.items():
        names[i] = s
    log.info("ticker T: nsym %d %.0fs", len(SI), time.time() - t0)
    return PT, names


def setup():
    PT, names = load_ticker_T()
    z = np.load(WD + "/kdose_err.npz")
    zn = list(z["names"])
    cur = {s: i for i, s in enumerate(names)}
    assert set(zn) == set(names), (len(zn), len(names))
    perm = np.array([cur[s] for s in zn], np.int64)
    si, mi, ms, val = perm[z["si"].astype(np.int64)], z["mi"].astype(np.int64), z["msk"], z["val"]
    pc = np.zeros(256, np.int64)
    for v in range(256):
        pc[v] = bin(v).count("1")
    off = np.concatenate([[0], np.cumsum(pc[ms])])[:-1]
    assert off[-1] + pc[ms[-1]] == len(val)
    v242 = PT[mi, si, :].copy()
    assert np.all(np.isfinite(v242[:, 3]))
    for f in range(5):
        has = ((ms >> f) & 1).astype(bool)
        rk = pc[ms & ((1 << f) - 1)]
        PT[mi[has], si[has], f] = val[off[has] + rk[has]]
    inw = z["inw"]
    o = np.argsort(mi[inw], kind="mergesort")
    G.update(PT=PT, names=names, NAMES=np.array(names, dtype=object), nsym=len(names),
             CMI=mi[inw][o], CSI=si[inw][o], CBIN=z["bin"][inw][o].astype(np.int64), CV=v242[inw][o],
             N_b=z["N_b"], E_b=z["E_b"])
    log.info("truth: sua %d o (trong W %d), nsym %d", len(mi), int(inw.sum()), len(names))
    fp = pickle.load(open(WD + "/kdose_fund.pkl", "rb"))
    G["mapper"], G["fund"] = fp["mapper"], fp["fund"]
    G["died"] = dx.load_died_set(REPO + "/config.properties")
    G["died_m"] = np.array([s in G["died"] for s in names])
    G["btc"] = cur["BTCUSDT"]
    G["iw_sel"] = None


def _avg_low(keys, period=100):
    """md_inline.cal_rate_change_avg tren tap khoa PHAN BIET (dict Python gop khoa trung)."""
    if len(keys) == 0:
        return 0.0
    u = np.unique(keys)
    n = len(u)
    p = period if period <= n * 4 // 5 else n * 4 // 5
    p = max(1, min(p, n))
    t = 0.0
    for v in u[:p].tolist():          # cong tuan tu nhu Java/port
        t += v
    return t / p


class VecMD:
    """Vector hoa md_inline.InlineMD (WINDOW 15, MIN_SYMBOLS 50) theo chi so symbol; ho tro ghi de o (R1)."""

    def __init__(self, nsym, died_m, btc):
        self.HH = np.full((nsym, 15), -np.inf)
        self.LL = np.full((nsym, 15), np.inf)
        self.cnt = np.zeros(nsym, np.int64)
        self.pos = np.zeros(nsym, np.int64)
        self.died, self.btc = died_m, btc

    def update(self, pres, arr):
        nd = ~self.died[pres]
        s = pres[nd]
        a = arr[nd].astype(np.float64)
        self.HH[s, self.pos[s]] = a[:, 1]
        self.LL[s, self.pos[s]] = a[:, 2]
        self.pos[s] = (self.pos[s] + 1) % 15
        self.cnt[s] += 1
        if len(s) < md_inline.MIN_SYMBOLS:
            return None
        bi = np.flatnonzero(pres == self.btc)
        if len(bi) == 0:
            return None
        if int((self.cnt[s] >= 15).sum()) < md_inline.MIN_SYMBOLS:
            return None
        b = arr[bi[0]].astype(np.float64)
        rate_btc = (b[3] - b[0]) / b[0]
        o, c = a[:, 0], a[:, 3]
        with np.errstate(divide="ignore", invalid="ignore"):
            rc = np.where(o != 0, (c - o) / np.where(o != 0, o, 1.0), 0.0)
        keep = ~(((rate_btc > -0.004) & (rc < -0.15)) | (rc > 0.3))
        mx = self.HH[s].max(1)
        km = keep & (mx != 0)
        rm = (c[km] - mx[km]) / mx[km]
        return (_avg_low(rc[keep]), 0.0, _avg_low(rm))

    def restore(self, sidx, arr_true):
        nd = ~self.died[sidx]
        s = sidx[nd]
        a = arr_true[nd].astype(np.float64)
        last = (self.pos[s] - 1) % 15
        self.HH[s, last] = a[:, 1]
        self.LL[s, last] = a[:, 2]


class FStore:
    def __init__(self, fund):
        self.fund = fund

    def get_funding_map(self, sym, prefer_local=False):
        return self.fund.get(sym)


CSV_IDX = [dx.CSV_FEAT_NAMES.index(f) for f in FEATS]


def sess():
    if "sess" not in G:
        import onnxruntime as ort
        o = ort.SessionOptions()
        o.intra_op_num_threads = 1
        G["sess"] = ort.InferenceSession(MODEL, o, providers=["CPUExecutionProvider"])
    return G["sess"]


def p15_of(X):
    s = sess()
    return s.run(None, {s.get_inputs()[0].name: X})[0].reshape(-1).astype(np.float32)


def select(e, rep):
    """chi so o (vao mang CMI.. sap theo phut) bi loi: moi bin b lay round(e/ebar*|E_b|) o deu, khong lap."""
    if e is None:
        return None
    if e == "all":
        return np.arange(len(G["CMI"]))
    ebar = G["E_b"].sum() / G["N_b"].sum()
    fr = min(1.0, e / ebar)
    rng = np.random.default_rng(SEED0 + 1000 * (GRID.index(e) + 1) + rep)
    out = []
    for b in range(7):
        ib = np.flatnonzero(G["CBIN"] == b)
        nb = int(round(fr * len(ib)))
        if nb:
            out.append(rng.choice(ib, nb, replace=False))
    return np.sort(np.concatenate(out)) if out else np.zeros(0, np.int64)


def run_engine(sel, regime, out_idx, md_check=0):
    """Nuoi Engine phut I_START..IW1-1 voi o loi `sel` (R1: chi tick hien tai; R2: bam lich su).
    Tra p15 (float32) tai cac phut out_idx (mang chi so phut tang dan; phut khong co du lieu -> NaN)."""
    PT, NAMES, nsym = G["PT"], G["NAMES"], G["nsym"]
    eng = dx.Engine(dict(G["mapper"]))
    md = VecMD(nsym, G["died_m"], G["btc"])
    chk = md_inline.InlineMD(G["died"]) if md_check else None
    fst = FStore(G["fund"])
    if sel is not None and len(sel):
        smi, ssi, sv = G["CMI"][sel], G["CSI"][sel], G["CV"][sel]
    else:
        smi = np.zeros(0, np.int64)
    want = np.zeros(NM, bool)
    want[out_idx] = True
    inv = np.full(nsym, -1, np.int64)
    rows, got, nchk, nbad = [], [], 0, 0
    lo = int(np.searchsorted(smi, I_START))
    for i in range(I_START, IW1):
        row = PT[i]
        pres = np.flatnonzero(np.isfinite(row[:, 3]))
        if len(pres) == 0:
            continue
        arr = row[pres]
        hi = lo
        while hi < len(smi) and smi[hi] == i:
            hi += 1
        pos = None
        if hi > lo:
            inv[pres] = np.arange(len(pres))
            pos = inv[ssi[lo:hi]]
            assert np.all(pos >= 0)
            atrue = arr[pos].copy()
            arr[pos] = sv[lo:hi]
        syms = NAMES[pres].tolist()
        ts = U0 + i * MN
        active = eng.update(ts, syms, arr)
        eng.check_rank(ts, active)
        rate = md.update(pres, arr)
        if chk is not None and nchk < md_check:
            r2 = chk.update({s: (float(a[0]), float(a[1]), float(a[2]), float(a[3])) for s, a in zip(syms, arr)})
            nchk += 1
            nbad += int((r2 is None) != (rate is None) or (r2 is not None and (r2[0] != rate[0] or r2[2] != rate[2])))
        if want[i]:
            rows.append(dx.features_row(eng, fst, ts, syms, arr, rate))
            got.append(i)
        if pos is not None and regime == "R1":
            eng.update(ts, [syms[p] for p in pos.tolist()], atrue)
            md.restore(pres[pos], atrue)
        lo = hi
        if md_check and (i - I_START) % 20000 == 0:
            log.info("engine phut %d/%d, rows %d", i - I_START, IW1 - I_START, len(rows))
    X = np.array([[float(r[1 + j]) for j in CSV_IDX] for r in rows], np.float32).reshape(-1, len(FEATS))
    p = p15_of(X) if len(X) else np.zeros(0, np.float32)
    out = np.full(len(out_idx), np.nan, np.float32)
    out[np.searchsorted(out_idx, np.array(got, np.int64))] = p
    if md_check:
        log.info("md vector vs InlineMD: %d phut, lech %d", nchk, nbad)
    return out


def kdiv_hist():
    """p15 lich su truoc diem gay tu CSV feature KDIV (242 truoc 04-01, vis 04-01..gay) -> (ts, p15)."""
    def lf(pat):
        df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(KDIV + pat))], ignore_index=True)
        df = df.drop_duplicates("ts", keep="first").sort_values("ts").reset_index(drop=True)
        return df["ts"].to_numpy(np.int64), p15_of(df[FEATS].to_numpy(np.float32))
    t2, p2 = lf("/kdiv_gate_242_*.csv.gz")
    tv, pv = lf("/kdiv_gate_vis_*.csv.gz")
    V0, BRK = 1774976400000, U0 + IW0 * MN               # 2026-04-01 00:00 +07, diem gay
    ts = np.concatenate([t2[t2 < V0], tv[(tv >= V0) & (tv < BRK)]])
    p = np.concatenate([p2[t2 < V0], pv[(tv >= V0) & (tv < BRK)]])
    G["kdiv"] = dict(t2=t2, p2=p2, tv=tv, pv=pv)
    return ts, p


def load_bins():
    """bins2026Ax -> T15, SP[n,24] (sp tang), SY[n,24] symId."""
    T, SP, SY = [], [], []
    for f in sorted(glob.glob(BINS + "/predict_wf_2026*.bin")):
        a = np.fromfile(f, dtype=REC)
        p0 = a["p0"].astype(np.float32)
        ok = ~np.isnan(p0)
        ts, sc, sy = a["ts"][ok].astype(np.int64), (np.float32(1) - p0[ok]), a["sym"][ok].astype(np.int64)
        o = np.lexsort((sc, ts))
        ts, sc, sy = ts[o], sc[o], sy[o]
        u, st = np.unique(ts, return_index=True)
        grp = np.repeat(np.arange(len(u)), np.diff(np.append(st, len(ts))))
        rk = np.arange(len(ts)) - st[grp]
        k = rk < 24
        M = np.full((len(u), 24), np.nan, np.float32)
        S = np.full((len(u), 24), -1, np.int64)
        M[grp[k], rk[k]] = sc[k]
        S[grp[k], rk[k]] = sy[k]
        T.append(u)
        SP.append(M)
        SY.append(S)
    return np.concatenate(T), np.vstack(SP), np.vstack(SY)


def build_cfgs(TS):
    """Cau hinh gate tren luoi phut TS (lich su + cua so): G0 (K24 khong khoa), G1_<seed> (K24+khoa+skipFull), G2 (K16+khoa b0)."""
    import gate_offline as go
    import gate_skipfull_offline as gsf
    T15, SP, SY = load_bins()
    fi = np.searchsorted(T15, TS, "right") - 1
    ok = (fi >= 0) & (TS - T15[np.maximum(fi, 0)] <= 15 * MN)
    SPm = np.where(ok[:, None], SP[np.maximum(fi, 0)], np.nan).astype(np.float32)
    SYm = np.where(ok[:, None], SY[np.maximum(fi, 0)], -1)
    mp = pd.read_csv(SYMMAP)
    s2id = dict(zip(mp.symbol.astype(str).str.strip().str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    G["id2sym"] = dict(zip(mp.symId.astype(int), mp.symbol.astype(str).str.strip()))
    specs = {"G0": (24, None, False)}
    for s in SEEDS:
        specs["G1_%d" % s] = (24, "ho26-k24-s-s%d" % s, True)
    specs["G2"] = (16, "ho26-b0-s-s42", False)
    C, BRK = {}, U0 + IW0 * MN
    win = TS >= BRK
    for name, (K, tag, sf) in specs.items():
        sp = SPm[:, :K]
        fac = np.maximum(DYN_MIN, (sp / SCORE_BASE * DYN_MULT).astype(np.float32)).astype(np.float32)
        valid = ~np.isnan(sp)
        info, d = {}, None
        if tag:
            d, _ = go.load_pd("A1", s2id, tag)
            lock = go.lock_mask(TS, SYm[:, :K], d)
            valid &= ~lock
            info["lock_cells"] = int(lock.sum())
            if sf:
                full, U, nsnap = gsf.full_mask(dict(d=d, ts=TS), tag)
                valid &= ~full[:, None]
                info.update(full_min_win=int((full & win).sum()), nsnap=int(nsnap))
        hrs = TS // H
        h0 = int(hrs[valid.any(1)][0])
        cnt = np.bincount((np.repeat(hrs, valid.sum(1)) - h0), minlength=int(hrs[-1]) - h0 + 1)
        qh = np.unique(hrs[win & valid.any(1)])
        C[name] = dict(K=K, fac=fac, facGS=(fac * GS).astype(np.float32), valid=valid, h0=h0,
                       cum=np.concatenate([[0], np.cumsum(cnt)]), first=int(TS[valid.any(1)][0]), qh=qh,
                       SY=SYm[:, :K], d=d, tag=tag, info=info)
        log.info("cfg %s: K %d o hop le %d, %s", name, K, int(valid.sum()), info)
    G["C"], G["TS"], G["win"] = C, TS, win
    G["s2id"] = s2id


def gate_eval(P15, c, floor=None):
    """-> (PASS tren hang cua so [nwin,K] bool, q theo gio c['qh'] float32 (NaN = warm), ok_floor).
    floor=None: cay top-J tren MOI r (nhu gate_offline.hourly_q); floor: chi r >= floor, dem m day du (phai trung)."""
    import gate_offline as go
    TS, win = G["TS"], G["win"]
    valid = c["valid"]
    r = (P15[:, None] / c["facGS"]).astype(np.float32)
    rows, cols = np.nonzero(valid)
    vals = r[rows, cols]
    hv = TS[rows] // H - c["h0"]
    if floor is not None:
        k = vals >= floor
        vals, hv = vals[k], hv[k]
    nH = len(c["cum"]) - 1
    tree = go.TopTree(hv.astype(np.int64), vals, nH, 256)
    tree.cum = c["cum"]
    q = np.full(len(c["qh"]), np.nan, np.float32)
    ok = True
    for i, hh in enumerate(c["qh"].tolist()):
        if hh * H - c["first"] < 7 * D:
            continue
        hi = hh - c["h0"]
        lo = max(0, hi - 90 * 24)
        m = int(c["cum"][hi] - c["cum"][lo])
        if m == 0:
            continue
        kk = min(m - 1, max(0, int(math.floor(PCT * (m - 1)))))
        v = tree.kth(lo, hi, m - 1 - kk)
        if not np.isfinite(v):
            ok = False
        q[i] = v
    tw = TS[win] // H
    pos = np.clip(np.searchsorted(c["qh"], tw), 0, max(len(c["qh"]) - 1, 0))
    hit = (len(c["qh"]) > 0) & (c["qh"][pos] == tw)
    qq = np.where(hit, q[pos], np.nan)
    qq = np.where(np.isnan(qq), BASE, qq).astype(np.float32)
    fac = c["fac"][win]
    thr = ((qq[:, None] * fac).astype(np.float32) * GS).astype(np.float32)
    PASS = ~(P15[win][:, None] < thr) & valid[win]
    return PASS, q, ok


def winit():
    G.pop("sess", None)


def flip_stats(P0, Pe, valid_w, wg):
    f = (P0 != Pe) & valid_w
    f, P0g, Peg = f[wg], P0[wg], Pe[wg]
    uni = int((P0g | Peg).sum())
    return dict(flips=int(f.sum()), union=int(uni), pass0=int(P0g.sum()), passe=int(Peg.sum()),
                flip_pass_pct=100.0 * f.sum() / max(uni, 1), pairs=int(valid_w[wg].sum()),
                flip_pair_pct=100.0 * f.sum() / max(valid_w[wg].sum(), 1), min_any_pct=100.0 * f.any(1).mean(),
                add=int((f & Peg).sum()), rem=int((f & P0g).sum()))


def eval_all(P15, floor):
    """Gate moi cau hinh, so voi base (G['PASS0'], G['Q0'])."""
    wg = G["TS"][G["win"]] >= U0 + IG0 * MN
    out, flips = {}, {}
    for name, c in G["C"].items():
        Pe, q, ok = gate_eval(P15, c, floor)
        P0 = G["PASS0"][name]
        vw = c["valid"][G["win"]]
        st = flip_stats(P0, Pe, vw, wg)
        q0 = G["Q0"][name]
        m = np.isfinite(q0) & np.isfinite(q) & (q0 > 0)
        dq = np.abs(q[m] / q0[m] - 1.0) if m.any() else np.zeros(1)
        st.update(ok_floor=bool(ok), dq_p50=float(np.percentile(dq, 50)), dq_p99=float(np.percentile(dq, 99)),
                  dq_max=float(dq.max()), q_hours_neq=int((q[m] != q0[m]).sum()))
        out[name] = st
        if name.startswith("G1_"):
            f = (P0 != Pe) & vw & wg[:, None]
            r_, k_ = np.nonzero(f)
            flips[name] = np.stack([r_, k_, np.where(Pe[r_, k_], 1, -1)], 1).astype(np.int64)
    return out, flips


def scen(task):
    e, rep, regime = task
    t0 = time.time()
    sel = select(e, rep)
    pw = run_engine(sel, regime, G["MS_IDX"])
    P15 = G["P15_0"].copy()
    ok = np.isfinite(pw)
    P15[G["MS_POS"][ok]] = pw[ok]
    base = G["P15_0"][G["MS_POS"]]
    wgm = G["TS"][G["MS_POS"]] >= U0 + IG0 * MN
    dp = np.abs(pw[ok & wgm] / base[ok & wgm] - 1.0)
    st, flips = eval_all(P15, G["floor"])
    res = dict(e=e, rep=rep, regime=regime, ncell=int(0 if sel is None else len(sel)), gate=st,
               dp15_p50=float(np.percentile(dp, 50)) if len(dp) else 0.0,
               dp15_p99=float(np.percentile(dp, 99)) if len(dp) else 0.0, sec=time.time() - t0)
    return res, {k: v.tolist() for k, v in flips.items()}


def _full_job(task):
    kind = task
    if kind == "e0":
        return kind, run_engine(None, "R2", G["OUT_IDX"], md_check=3000)
    return kind, run_engine(select("all", 0), "R2", G["OUT_IDX"])


def stage_base():
    setup()
    hts, hp = kdiv_hist()
    G["OUT_IDX"] = np.arange(IW0, IW1)
    G.pop("sess", None)
    with Pool(2, initializer=winit) as pool:
        R = dict(pool.map(_full_job, ["e0", "eR2"]))
    p0, pR2 = R["e0"], R["eR2"]
    okm = np.isfinite(p0)
    assert np.array_equal(okm, np.isfinite(pR2))
    widx = G["OUT_IDX"][okm]
    TS = np.concatenate([hts, U0 + widx * MN])
    P15_0 = np.concatenate([hp, p0[okm]])
    P15_R2 = np.concatenate([hp, pR2[okm]])
    log.info("base: phut cua so %d (khong du lieu %d), lich su %d", len(widx), int((~okm).sum()), len(hts))
    build_cfgs(TS)
    res = dict(window_minutes=int(len(widx)), hist_minutes=int(len(hts)), cfg={k: c["info"] for k, c in G["C"].items()})
    G["PASS0"], G["Q0"] = {}, {}
    full_R2 = {}
    for name, c in G["C"].items():
        P0, q0, _ = gate_eval(P15_0, c, None)
        G["PASS0"][name], G["Q0"][name] = P0, q0
        full_R2[name] = gate_eval(P15_R2, c, None)
    qmin = min(float(np.nanmin(q)) for q in G["Q0"].values())
    floor = np.float32(FLOORF * qmin)
    G["floor"] = floor
    chk_floor = {}
    for name, c in G["C"].items():
        P0f, q0f, okf = gate_eval(P15_0, c, floor)
        P2f, q2f, ok2 = gate_eval(P15_R2, c, floor)
        chk_floor[name] = bool(okf and ok2 and np.array_equal(P0f, G["PASS0"][name]) and
                               np.array_equal(P2f, full_R2[name][0]) and
                               np.array_equal(q0f, G["Q0"][name], equal_nan=True) and
                               np.array_equal(q2f, full_R2[name][1], equal_nan=True))
    res.update(qmin=qmin, floor=float(floor), check_floor=chk_floor)
    log.info("floor %.6f check %s", floor, chk_floor)

    # M*: phut cua so co max_k r_0 (G0, khong khoa) >= ALPHA * min_cfg q_0(gio)
    win = G["win"]
    tw = TS[win] // H
    qrow = np.full(len(tw), np.inf)
    for name, c in G["C"].items():
        pos = np.clip(np.searchsorted(c["qh"], tw), 0, len(c["qh"]) - 1)
        qq = np.where(c["qh"][pos] == tw, G["Q0"][name][pos], np.nan)
        qq = np.where(np.isnan(qq), BASE, qq)
        qrow = np.minimum(qrow, qq)
    c0 = G["C"]["G0"]
    r0 = np.where(c0["valid"][win], P15_0[win][:, None] / c0["facGS"][win], -np.inf).max(1)
    ms_w = np.flatnonzero(r0 >= ALPHA * qrow)
    MS_POS = np.flatnonzero(win)[ms_w]
    MS_IDX = (TS[MS_POS] - U0) // MN
    # kiem (i): eR2 chi thay o M* -> PASS trung tuyet doi ban day du
    P15_M = P15_0.copy()
    P15_M[MS_POS] = P15_R2[MS_POS]
    chk_ms = {}
    for name, c in G["C"].items():
        Pm, qm, okm2 = gate_eval(P15_M, c, floor)
        chk_ms[name] = bool(okm2 and np.array_equal(Pm, full_R2[name][0]) and
                            np.array_equal(qm, full_R2[name][1], equal_nan=True))
    wg = TS[win] >= U0 + IG0 * MN
    d3 = {name: flip_stats(G["PASS0"][name], full_R2[name][0], c["valid"][win], wg) for name, c in G["C"].items()}
    # parity voi CSV KDIV tren W_g
    kd = G["kdiv"]
    tg = TS[win][wg]
    par = {}
    for lab, kt, kp, mine in (("e0_vs_kdiv_vis", kd["tv"], kd["pv"], P15_0), ("eR2_vs_kdiv_242", kd["t2"], kd["p2"], P15_R2)):
        cm, ia, ib = np.intersect1d(tg, kt, return_indices=True)
        a = mine[win][wg][ia]
        b = kp[ib]
        par[lab] = dict(n=int(len(cm)), eq_pct=100.0 * float(np.mean(a == b)),
                        dp_p99_pp=float(np.percentile(np.abs(a.astype(np.float64) - b), 99) * 100),
                        dp_max_pp=float(np.max(np.abs(a.astype(np.float64) - b)) * 100))
    res.update(mstar=int(len(MS_POS)), mstar_pct=100.0 * len(MS_POS) / max(int(win.sum()), 1), check_mstar=chk_ms,
               d3_eR2_full=d3, parity=par)
    np.savez(WD + "/kdose_base.npz", TS=TS, P15_0=P15_0, P15_R2=P15_R2, MS_POS=MS_POS, MS_IDX=MS_IDX, floor=floor,
             **{"PASS0_" + k: v for k, v in G["PASS0"].items()}, **{"Q0_" + k: v for k, v in G["Q0"].items()})
    json.dump(res, open(WD + "/kdose_base.json", "w"), indent=1, default=float)
    log.info("BASE %s", json.dumps({k: v for k, v in res.items() if k != "cfg"}, default=float))


def stage_smoke():
    setup()
    oi = np.arange(IW0, IW0 + 300)
    t0 = time.time()
    a = run_engine(None, "R2", oi, md_check=3500)
    t1 = time.time()
    b = run_engine(select("all", 0), "R1", oi)
    t2 = time.time()
    c = run_engine(select(0.05, 0), "R2", oi[::10])
    t3 = time.time()
    kd = G.get("kdiv")
    log.info("smoke: e0 %.0fs, eR1 %.0fs, e5 %.0fs; p15 e0 %s | eR1 %s | e5 %s", t1 - t0, t2 - t1, t3 - t2,
             a[:5], b[:5], c[:5])
    df = pd.read_csv(KDIV + "/kdiv_gate_vis_20260401_20260430.csv.gz")
    m = df.set_index("ts").reindex(U0 + oi * MN)
    pk = p15_of(m[FEATS].to_numpy(np.float32))
    log.info("smoke parity e0 vs KDIV vis (300 phut sau gay): eq %.2f%%, max |d| %.5f pp", 100 * np.mean(pk == a),
             100 * np.nanmax(np.abs(pk.astype(np.float64) - a)))
    fd = {}
    log.info("smoke n_sel all %d, 5%% %d", len(select("all", 0)), len(select(0.05, 0)))




def load_base():
    z = np.load(WD + "/kdose_base.npz")
    TS = z["TS"]
    build_cfgs(TS)
    G["P15_0"], G["MS_POS"], G["MS_IDX"], G["floor"] = z["P15_0"], z["MS_POS"], z["MS_IDX"], np.float32(z["floor"])
    G["PASS0"] = {k: z["PASS0_" + k] for k in G["C"]}
    G["Q0"] = {k: z["Q0_" + k] for k in G["C"]}


def tasks_all():
    T = [("all", 0, "R1"), ("all", 0, "R2")]
    ebar = G["E_b"].sum() / G["N_b"].sum()
    for e in GRID:
        if e >= ebar:          # pre-reg §3: e >= ebar -> thay bang ebar (= tap "all", tat dinh) — khong lap 20 lan
            continue
        for rep in range(NREP):
            for rg in ("R1", "R2"):
                T.append((e, rep, rg))
    return T


def stage_d2():
    setup()
    load_base()
    raw = WD + "/kdose_d2_raw.jsonl"
    done = set()
    if os.path.exists(raw):
        for ln in open(raw):
            j = json.loads(ln)
            done.add((j["res"]["e"], j["res"]["rep"], j["res"]["regime"]))
    todo = [t for t in tasks_all() if t not in done]
    log.info("d2: %d task, da xong %d, con %d; M* %d phut", len(tasks_all()), len(done), len(todo), len(G["MS_IDX"]))
    G.pop("sess", None)
    t0 = time.time()
    with Pool(int(os.environ.get("KDOSE_POOL", "4")), initializer=winit) as pool, open(raw, "a") as fh:
        for n, (res, flips) in enumerate(pool.imap_unordered(scen, todo)):
            fh.write(json.dumps(dict(res=res, flips=flips)) + "\n")
            fh.flush()
            g0 = res["gate"]
            log.info("[%d/%d %.0fs] e=%s rep=%d %s: G0 flip %.2f%% G1 %.2f%% G2 %.2f%% (%.0fs)", n + 1, len(todo),
                     time.time() - t0, res["e"], res["rep"], res["regime"], g0["G0"]["flip_pass_pct"],
                     g0["G1_42"]["flip_pass_pct"], g0["G2"]["flip_pass_pct"], res["sec"])


def proxy(si, i):
    """proxy thoat qsleeve_q0 (nhu ho26_luck_audit.proxy) tren du lieu DUNG: vao close phut i. -> (ret, exit_i) | None."""
    key = (int(si), int(i))
    if key in G["RET"]:
        return G["RET"][key]
    import qsleeve_q0 as QS
    PT = G["PT"]
    c0, o0 = float(PT[i, si, 3]), float(PT[i, si, 0])
    if not (np.isfinite(c0) and c0 > 0):
        G["RET"][key] = None
        return None
    cr = bool(np.isfinite(o0) and o0 > 0 and c0 / o0 - 1.0 <= CRASH)
    st = QS.new_state("x", U0 + i * MN)
    st["E"] = c0
    a, last_c = i + 1, np.nan
    while a < IW1 and not st["done"]:
        b = min(IW1, a + 20000)
        X = PT[a:b, si, :4].T.astype(np.float64)
        ok = np.all(np.isfinite(X), axis=0) & np.all(X > 0, axis=0)
        ix = np.flatnonzero(ok)
        if len(ix):
            QS.seg(st, X[1, ix], X[2, ix], X[0, ix], X[3, ix], U0 + (a + ix) * MN)
            last_c = X[3, ix[-1]]
        a = b
    if st["done"]:
        px, ex = st["px"], int((int(st["exit_t"]) - U0) // MN) if st["exit_t"] is not None else IW1
    else:
        px, ex = (last_c if np.isfinite(last_c) else c0), IW1
    r = (px / c0 - 1.0 - COST - (PEN if cr else 0.0), ex)
    G["RET"][key] = r
    return r


def load_legs():
    import ho26_luck_audit as HLA
    cur = {s: i for i, s in enumerate(G["names"])}
    g0, g1 = U0 + IG0 * MN, U0 + IW1 * MN
    L = {}
    for s in SEEDS:
        d = HLA.load_pd("ho26-k24-s-s%d" % s)
        d = d[d["leg0"] & (d["ts"] >= g0) & (d["ts"] < g1)].copy()
        d["si"] = d["symt"].map(cur)
        d["i0"] = (d["ts"] - U0) // MN
        L[s] = d
    return L


def econ_prep(L):
    cur = {s: i for i, s in enumerate(G["names"])}
    G["cur"] = cur
    G["MARG"], G["MED"] = {}, {}
    Dsum, Dabs, nmiss = 0.0, 0.0, 0
    for s in SEEDS:
        d = L[s]
        pr = d[d["level"] == "PREDICT_SYMBOL_TRADE"]
        G["MARG"][s] = {(a, int(b)): float(m) for a, b, m in zip(pr["symt"], pr["ts"], pr["margin"])}
        G["MED"][s] = float(pr["margin"].median()) if len(pr) else float(d["margin"].median())
        for si, i0, m in zip(d["si"], d["i0"], d["margin"]):
            if not np.isfinite(si):
                nmiss += 1
                continue
            r = proxy(int(si), int(i0))
            if r is None:
                nmiss += 1
                continue
            Dsum += m * r[0]
            Dabs += abs(m * r[0])
    G["D"] = dict(sum=Dsum, abs=Dabs, miss=nmiss, legs={s: int(len(L[s])) for s in SEEDS},
                  pred_legs={s: int((L[s]["level"] == "PREDICT_SYMBOL_TRADE").sum()) for s in SEEDS},
                  med_margin=G["MED"])
    log.info("econ D: %s", G["D"])


def econ(flips):
    TSw = G["TS"][G["win"]]
    tot, nadd, nrem, nskip, nmiss = 0.0, 0, 0, 0, 0
    for s in SEEDS:
        fl = sorted(map(tuple, flips.get("G1_%d" % s, [])))
        SYw = G["C"]["G1_%d" % s]["SY"][G["win"]]
        openu = {}
        for row, k, sg in fl:
            ts = int(TSw[row])
            sym = G["id2sym"].get(int(SYw[row, k]))
            si = G["cur"].get(sym)
            pr = proxy(si, (ts - U0) // MN) if si is not None else None
            if pr is None:
                nmiss += 1
                continue
            notional = G["MARG"][s].get((sym, ts), G["MED"][s])
            if sg < 0:
                tot -= notional * pr[0]
                nrem += 1
            else:
                i = (ts - U0) // MN
                if i < openu.get(si, -1):
                    nskip += 1
                    continue
                tot += notional * pr[0]
                openu[si] = pr[1]
                nadd += 1
    return dict(dpnl=tot, add=nadd, rem=nrem, skip=nskip, miss=nmiss)


def entry_prep(L):
    """chan leg0 PREDICT trong W_g (8 seed): chi so o kho loi tai nen quyet dinh (phut start) hoac -1."""
    nsym = G["nsym"]
    ks = G["CMI"] * nsym + G["CSI"]
    o = np.argsort(ks, kind="mergesort")
    rows = []
    for s in SEEDS:
        d = L[s]
        d = d[(d["level"] == "PREDICT_SYMBOL_TRADE") & d["si"].notna()]
        rows += [(int(a), int(b), float(e)) for a, b, e in zip(d["si"], d["i0"], d["entry"])]
    si = np.array([r[0] for r in rows], np.int64)
    i0 = np.array([r[1] for r in rows], np.int64)
    ent = np.array([r[2] for r in rows])
    key = i0 * nsym + si
    p = np.clip(np.searchsorted(ks[o], key), 0, len(ks) - 1)
    idx = np.where(ks[o][p] == key, o[p], -1)
    PT = G["PT"]
    ct = PT[i0, si, 3].astype(np.float64)
    c242 = np.where(idx >= 0, G["CV"][np.maximum(idx, 0), 3], ct)
    cprev = PT[i0 - 1, si, 3].astype(np.float64)
    m = lambda a, b: float(np.mean(np.abs(a / b - 1) <= 1e-6))
    G["ENT"] = dict(si=si, i0=i0, idx=idx, ct=ct)
    chk = dict(n=int(len(si)), entry_eq_close242_i0=m(ent, c242), entry_eq_truth_i0=m(ent, ct),
               entry_eq_close_im1=m(ent, cprev))
    log.info("entry check %s", chk)
    return chk


def entry_metric(sel):
    E = G["ENT"]
    mask = np.zeros(len(G["CMI"]), bool)
    if sel is not None and len(sel):
        mask[sel] = True
    aff = (E["idx"] >= 0) & mask[np.maximum(E["idx"], 0)]
    d = np.zeros(len(E["si"]))
    d[aff] = (G["CV"][E["idx"][aff], 3].astype(np.float64) / E["ct"][aff] - 1) * 1e4
    return dict(frac_aff=float(aff.mean()), mean_bps_all=float(d.mean()),
                mean_bps_aff=float(d[aff].mean()) if aff.any() else 0.0,
                mean_abs_bps_aff=float(np.abs(d[aff]).mean()) if aff.any() else 0.0)


def s1_prep():
    """moc gio t trong W_g: close gio t = close nen 1m open t-1m (chi so it); close gio truoc = it-60."""
    it = np.arange(IG0, IW1, 60) - 1
    PT = G["PT"]
    stb = np.array([s in STABLE for s in G["names"]])
    C1, C0 = PT[it, :, 3].astype(np.float64), PT[it - 60, :, 3].astype(np.float64)
    hmap = np.full(NM, -1, np.int64)
    hmap[it] = np.arange(len(it))
    G["S1"] = dict(it=it, C1=C1, C0=C0, stb=stb, hmap=hmap)
    G["S1"]["base"] = s1_sets(C1, C0)


def s1_sets(C1, C0):
    out = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        R = C1 / C0 - 1.0
    ok = np.isfinite(R) & (C0 > 0) & ~G["S1"]["stb"][None, :] if "S1" in G else None
    for h in range(R.shape[0]):
        ix = np.flatnonzero(ok[h])
        o = ix[np.argsort(R[h, ix], kind="mergesort")]
        for K in (16, 24):
            out[(h, K, "top")] = frozenset(o[-K:].tolist())
            out[(h, K, "bot")] = frozenset(o[:K].tolist())
    return out


def s1_metric(sel, regime):
    S = G["S1"]
    C1, C0 = S["C1"].copy(), S["C0"].copy()
    if sel is not None and len(sel):
        mi, si, cv = G["CMI"][sel], G["CSI"][sel], G["CV"][sel, 3].astype(np.float64)
        h1 = S["hmap"][mi]
        k = h1 >= 0
        C1[h1[k], si[k]] = cv[k]
        if regime == "R2":
            h0 = S["hmap"][np.minimum(mi + 60, NM - 1)]
            k = (h0 >= 0) & (mi + 60 < NM)
            C0[h0[k], si[k]] = cv[k]
    sets = s1_sets(C1, C0)
    res = {}
    for K in (16, 24):
        for side in ("top", "bot"):
            ch, jac = [], []
            for h in range(C1.shape[0]):
                a, b = S["base"][(h, K, side)], sets[(h, K, side)]
                ch.append(a != b)
                jac.append(len(a & b) / max(len(a | b), 1))
            res["K%d_%s_changed_pct" % (K, side)] = 100.0 * float(np.mean(ch))
            res["K%d_%s_jac" % (K, side)] = float(np.mean(jac))
    return res


def ci(v):
    v = np.asarray(v, float)
    return dict(mean=float(v.mean()), lo=float(np.percentile(v, 2.5)), hi=float(np.percentile(v, 97.5)), n=int(len(v)))


def stage_post():
    setup()
    load_base()
    G["RET"] = {}
    L = load_legs()
    econ_prep(L)
    ent_chk = entry_prep(L)
    s1_prep()
    Dden = abs(G["D"]["sum"])
    flag = Dden < 0.2 * G["D"]["abs"]
    den = G["D"]["abs"] if flag else Dden
    rows = []
    for ln in open(WD + "/kdose_d2_raw.jsonl"):
        j = json.loads(ln)
        r = j["res"]
        sel = select(r["e"], r["rep"])
        ec = econ(j["flips"])
        rows.append(dict(e=r["e"], rep=r["rep"], regime=r["regime"], gate=r["gate"], dp15_p50=r["dp15_p50"],
                         dp15_p99=r["dp15_p99"], econ=ec, dpnl_pct=100.0 * ec["dpnl"] / den,
                         entry=entry_metric(sel), s1=s1_metric(sel, r["regime"])))
    agg = {}
    for rg in ("R1", "R2"):
        for e in ["all"] + GRID:
            R = [x for x in rows if x["regime"] == rg and x["e"] == e]
            if not R:
                continue
            a = dict(n=len(R))
            for g in ("G0", "G1_42", "G2"):
                for m in ("flip_pass_pct", "flip_pair_pct", "min_any_pct", "dq_p50", "dq_p99"):
                    a["%s_%s" % (g, m)] = ci([x["gate"][g][m] for x in R])
            a["G1_8seed_flip_pass_pct"] = ci([np.mean([x["gate"]["G1_%d" % s]["flip_pass_pct"] for s in SEEDS]) for x in R])
            a["dp15_p50"] = ci([x["dp15_p50"] for x in R])
            a["dp15_p99"] = ci([x["dp15_p99"] for x in R])
            a["dpnl_pct"] = ci([x["dpnl_pct"] for x in R])
            a["dpnl_usd"] = ci([x["econ"]["dpnl"] for x in R])
            a["econ_add_rem"] = [float(np.mean([x["econ"]["add"] for x in R])), float(np.mean([x["econ"]["rem"] for x in R]))]
            for k in R[0]["entry"]:
                a["entry_" + k] = ci([x["entry"][k] for x in R])
            for k in R[0]["s1"]:
                a["s1_" + k] = ci([x["s1"][k] for x in R])
            agg["%s|%s" % (rg, e)] = a
    out = dict(D=G["D"], den=den, den_flag_abs=bool(flag), entry_check=ent_chk, agg=agg, n_rows=len(rows),
               n_proxy=len(G["RET"]))
    json.dump(out, open(WD + "/kdose_post.json", "w"), indent=1, default=float)
    json.dump(rows, open(WD + "/kdose_rows.json", "w"), default=float)
    log.info("POST xong: %d dong, D %s, den %.1f flag %s", len(rows), G["D"]["sum"], den, flag)


if __name__ == "__main__":
    {"smoke": stage_smoke, "base": stage_base, "d2": stage_d2, "post": stage_post}[sys.argv[1]]()
