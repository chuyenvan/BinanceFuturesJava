"""test_tl.py - test TONG HOP cho GRIDV2 S2 (khong du lieu that). Chay: python3 test_tl.py [ten_test ...] -> dev_out/test_results.json.
Test (prereg S2 muc 11): T1 bao nhau; T2 dap an giai tich; T3 truong hop bien; T4 engine vs tl_ref >= 5000 don vi; T5 khong nhin
tuong lai; T6 lay mau; T7 fetch_reduce tren zip gia; T8 run_s2 luat L2-A/B/C (+ W fail); T9 size kiem 1 o tren null cum; T10 e2e."""
import glob
import json
import logging
import os
import sys
import time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
S1DIR = os.environ.get("GRIDV2S2_S1CODE", os.path.expanduser("~/claude_master/vz_e1_wt/research/gridv2_s1"))
sys.path.insert(1, S1DIR)
import tl_engine as E  # noqa: E402
import tl_ref as R  # noqa: E402
import synth_trades as S  # noqa: E402

log = logging.getLogger("test_tl")
DS = E.DATA_START_MS
DAY = 86400000
MIN = 60000
D0 = DS + 1000 * DAY            # ngay tong hop (2024-01-26), < 2026
OUT = os.path.join(HERE, "dev_out")
RES = {}
FLOAT_COLS = ("xpx", "gross", "fee", "fee_stress", "slip", "fund", "net", "net_stress")
INT_COLS = ("filled", "excl", "tf", "tx", "kind", "n_maker")


def U_from_rows(rows):
    return {k: np.array([r[k] for r in rows]) for k in ("t0", "side", "L", "X", "tick", "W", "T", "slip", "dl_end")}


def ms_of(tr):
    return E.collapse_ms(tr["t"], tr["aid"], tr["p"], tr["ibm"])


def ref_list(tr):
    return R.prepare(list(zip(tr["t"].tolist(), tr["aid"].tolist(), tr["p"].tolist(), tr["ibm"].tolist())))


def compare(eng, refs, idx=None):
    """So engine (dict mang) voi list ket qua ref. Tra (so lech, max |dfloat|, vi du lech)."""
    nbad, mx, ex = 0, 0.0, None
    for i, r in enumerate(refs):
        bad = False
        for c in INT_COLS:
            if int(eng[c][i]) != int(r[c]):
                bad = True
        for c in FLOAT_COLS:
            a, b = float(eng[c][i]), float(r[c])
            if np.isnan(a) != np.isnan(b):
                bad = True
            elif not np.isnan(a):
                mx = max(mx, abs(a - b))
                if abs(a - b) > 1e-9:
                    bad = True
        if bad:
            nbad += 1
            if ex is None:
                ex = dict(i=i, eng={c: (eng[c][i].item() if hasattr(eng[c][i], "item") else eng[c][i]) for c in E.OUT_COLS},
                          ref=r)
    return nbad, mx, ex


def make_path(rng, day0, variant):
    """1 symbol tong hop 2 ngay [day0, day0 + 2 ngay) + don vi 24 gio ngay dau (BUY + SELL) + funding 8 gio."""
    tick = [0.1, 0.01, 0.001][variant % 3]
    k0 = int(rng.integers(5000, 30000))
    mg = [500.0, 2000.0, 6000.0][(variant // 3) % 3]
    quiet = []
    if variant % 4 == 1:
        a = day0 + int(rng.integers(1, 20)) * 3600000 + int(rng.integers(0, 3600000))
        quiet = [(a, a + int(rng.choice([59, 61, 75])) * MIN)]
    stop = None
    dl_end = -1
    if variant % 7 == 3:
        stop = day0 + int(rng.integers(3, 22)) * 3600000 + int(rng.integers(0, 3600000))
    tr = S.gen_trades(rng, day0, 2 * DAY, k0, tick, mean_gap_ms=mg, same_ms_p=0.2, jump_p=[0.0, 0.03][variant % 2],
                      ibm_flip=[0.0, 0.1][(variant // 2) % 2], quiet=quiet, stop_ms=stop)
    if stop is not None and tr["t"].size:
        dl_end = (int(tr["t"][-1]) // MIN + 1) * MIN
    bars = E.minute_bars(ms_of(tr))
    bc = dict(zip(bars["mi"].tolist(), bars["c"].tolist()))
    d = [0.002, 0.004, 0.008][variant % 3]
    rows = S.units_from_bars(bc, None, [day0 + h * 3600000 for h in range(24)], [d] * 24, tick, 115, 115,
                             float(rng.choice([2e-4, 5e-4, 1e-3])), dl_end)
    ft = np.arange(day0, day0 + 2 * DAY, 8 * 3600000, dtype=np.int64)
    fr = rng.normal(1e-4, 3e-4, ft.size)
    return tr, rows, ft, fr, bars, dl_end


def t4_engine_vs_ref():
    rng = np.random.default_rng(2026112301)
    nu, nbad, mx, ex, nfill = 0, 0, 0.0, None, {m: 0 for m in E.MODELS + E.DIAG_MODELS}
    kinds = {m: {} for m in E.MODELS + E.DIAG_MODELS}
    nexcl = {m: 0 for m in E.MODELS + E.DIAG_MODELS}
    v = 0
    while nu < 5000:
        day0 = D0 + v * 2 * DAY
        tr, rows, ft, fr, _, _ = make_path(rng, day0, v)
        v += 1
        if not rows:
            continue
        MS, P = ms_of(tr), ref_list(tr)
        U = U_from_rows(rows)
        for m in E.MODELS + E.DIAG_MODELS:
            eng = E.simulate(MS, U, m, day0, day0 + 2 * DAY, ft, fr)
            refs = [R.ref_unit(P, r, m, day0, day0 + 2 * DAY, list(zip(ft.tolist(), fr.tolist()))) for r in rows]
            b, x, e = compare(eng, refs)
            nbad += b
            mx = max(mx, x)
            ex = ex or e
            nfill[m] += int(eng["filled"].sum())
            nexcl[m] += int(eng["excl"].sum())
            for kk in eng["kind"][eng["filled"] == 1].tolist():
                kinds[m][kk] = kinds[m].get(kk, 0) + 1
        nu += len(rows)
    ok = nbad == 0 and all(len(kinds[m]) >= 3 for m in kinds) and all(nexcl[m] > 0 for m in nexcl) and \
        kinds["TOUCH"].get(E.EX_TAKER_BEYOND, 0) == 0
    return ok, dict(units=nu, paths=v, mismatches=nbad, max_abs_float_diff=mx, filled=nfill, exit_kinds=kinds, excl=nexcl,
                    example=ex)


def _grid_from_bars(bars, day0, nmin):
    """Luoi phut lien tuc [day0, day0 + nmin) tu nen dung lai (phut khong co giao dich = NaN, nhu lake S1)."""
    m0 = (day0 - DS) // MIN
    O = np.full(nmin, np.nan); H = O.copy(); L = O.copy(); C = O.copy()
    ii = bars["mi"] - m0
    k = (ii >= 0) & (ii < nmin)
    O[ii[k]], H[ii[k]], L[ii[k]], C[ii[k]] = bars["o"][k], bars["h"][k], bars["l"][k], bars["c"][k]
    return O, H, L, C, np.isfinite(C)


def t1_containment():
    """TL_THROUGH khop => TL_TOUCH khop (tf_TOUCH <= tf_THROUGH); TL_TOUCH khop => K_OPT (klite S1 tren nen dung lai) khop o
    phut <= ; K_PESS tren nen dung lai khop DUNG tap TL_THROUGH, cung phut khop."""
    import klite
    rng = np.random.default_rng(2026112302)
    viol = dict(thr_not_touch=0, touch_late=0, touch_not_kopt=0, kopt_late=0, kpess_ne_thr=0, kpess_min_ne=0)
    n = dict(units=0, thr=0, touch=0, kopt=0, kpess=0)
    for v in range(60):
        day0 = D0 + v * 2 * DAY
        tr, rows, ft, fr, bars, dl_end = make_path(rng, day0, v)
        if not rows:
            continue
        MS = ms_of(tr)
        U = U_from_rows(rows)
        a = E.simulate(MS, U, "THROUGH", day0, day0 + 2 * DAY)
        b = E.simulate(MS, U, "TOUCH", day0, day0 + 2 * DAY)
        O, H, L_, C, valid = _grid_from_bars(bars, day0, 2 * 1440)
        dl_idx = -1 if dl_end < 0 else int((dl_end - day0) // MIN) - 1
        G = klite.prepare_grid(O, H, L_, C, valid, dl_idx)
        t0i = np.array([(r["t0"] - day0) // MIN for r in rows])
        side = np.array([r["side"] for r in rows])
        dd = np.array([r["d"] for r in rows])
        tk = np.array([r["tick"] for r in rows])
        Ko = klite.run_units(G, t0i, dd, 115, 115, tk, 5e-4, "OPT", side)
        Kp = klite.run_units(G, t0i, dd, 115, 115, tk, 5e-4, "PESS", side)
        assert np.allclose(np.where(side == 1, Ko["Lb"], Ko["Ls"]), U["L"], rtol=0, atol=1e-12)
        fa, fb = a["filled"] == 1, b["filled"] == 1
        ma = np.where(fa, (a["tf"] - day0) // MIN, -1)
        mb = np.where(fb, (b["tf"] - day0) // MIN, -1)
        viol["thr_not_touch"] += int(np.sum(fa & ~fb))
        viol["touch_late"] += int(np.sum(fa & fb & (b["tf"] > a["tf"])))
        viol["touch_not_kopt"] += int(np.sum(fb & ~Ko["filled"]))
        viol["kopt_late"] += int(np.sum(fb & Ko["filled"] & (Ko["f"] > mb)))
        viol["kpess_ne_thr"] += int(np.sum(fa != Kp["filled"]))
        viol["kpess_min_ne"] += int(np.sum(fa & Kp["filled"] & (Kp["f"] != ma)))
        n["units"] += len(rows); n["thr"] += int(fa.sum()); n["touch"] += int(fb.sum())
        n["kopt"] += int(Ko["filled"].sum()); n["kpess"] += int(Kp["filled"].sum())
    ok = sum(viol.values()) == 0 and n["touch"] > n["thr"] and n["kopt"] >= n["touch"] and n["units"] > 2000
    return ok, dict(violations=viol, counts=n)


def t2_analytic():
    """Buoc ngau nhien +-1 tick (martingale), khoang cach giao dich >= 300 ms (khong co 2 giao dich trong 250 ms), ibm theo huong
    buoc. Dap an giai tich (dinh ly dung tuy chon): THROUGH: E[Z] = 0 voi Z = side (xpx - L)/tick + 1 + 1{thoat limit} (vao 1 tick
    TREN gia thi truong, thoat limit 1 tick DUOI); TOUCH: E[side (xpx - L)/tick] = 0. Kiem |TB| <= 3 SE (SE theo cum duong gia).
    Kiem luc: bien the SAI (bo +1 o THROUGH) phai bi bac |z| > 3. W = T = 30 phut, d = 5 tick de co nhieu don vi."""
    rng = np.random.default_rng(2026112303)
    Z = {m: [] for m in E.MODELS}
    Zw = []
    nfill = {m: 0 for m in E.MODELS}
    nlim = {m: 0 for m in E.MODELS}
    gsum = {m: 0.0 for m in E.MODELS}
    tick = 0.01
    for pth in range(9000):
        day0 = DS + 100 * DAY + (pth % 1500) * DAY + (pth // 1500) * 4 * 3600000
        tr = S.gen_trades(rng, day0, 4 * 3600000, int(rng.integers(9000, 11000)), tick, mean_gap_ms=1700.0, same_ms_p=0.0,
                          p_up=0.4, p_dn=0.4, jump_p=0.0, min_gap_ms=300)
        MS = ms_of(tr)
        t0 = day0 + 3600000
        m0 = float(MS["pl"][np.searchsorted(MS["t"], t0) - 1])
        Lb, Ls = m0 - 5 * tick, m0 + 5 * tick
        Xb, Xs = Lb + 5 * tick, Ls - 5 * tick
        U = dict(t0=np.array([t0, t0]), side=np.array([1, -1]), L=np.array([Lb, Ls]), X=np.array([Xb, Xs]),
                 tick=np.array([tick, tick]), W=np.array([30, 30]), T=np.array([30, 30]), slip=np.zeros(2),
                 dl_end=np.array([-1, -1]))
        for m in E.MODELS:
            o = E.simulate(MS, U, m, day0, day0 + 4 * 3600000)
            zz, zw = 0.0, 0.0
            for i in range(2):
                if o["filled"][i] == 1 and o["excl"][i] == 0:
                    ticks = round(U["side"][i] * (o["xpx"][i] - U["L"][i]) / tick, 6)
                    lim = int(o["kind"][i] == E.EX_LIMIT)
                    zz += ticks + (1 + lim if m == "THROUGH" else 0)
                    zw += ticks + lim
                    gsum[m] += ticks
                    nfill[m] += 1
                    nlim[m] += lim
            Z[m].append(zz)
            if m == "THROUGH":
                Zw.append(zw)
    det = {}
    ok = True
    for m in E.MODELS:
        z = np.array(Z[m])
        mu = z.sum() / nfill[m]
        se = z.std(ddof=1) * np.sqrt(z.size) / nfill[m]
        det[m] = dict(n_fill=nfill[m], p_lim=nlim[m] / nfill[m], mean_Z_ticks=mu, se=se, z=mu / se,
                      mean_gross_ticks=gsum[m] / nfill[m],
                      gross_expected_ticks=(-(1 + nlim[m] / nfill[m]) if m == "THROUGH" else 0.0))
        ok &= abs(mu) <= 3 * se and nfill[m] > 5000
    zw = np.array(Zw)
    muw = zw.sum() / nfill["THROUGH"]
    sew = zw.std(ddof=1) * np.sqrt(zw.size) / nfill["THROUGH"]
    det["power_check_wrong_identity_z"] = muw / sew
    ok &= abs(muw / sew) > 3
    return ok, det


def _edge_env():
    """Moi truong bien: tick 0.1, L 100.0 (BUY) / X 101.0; giao dich dem moi 10 phut tai 100.5 (khong cham muc nao)."""
    t0 = D0 + 3600000
    filler = [(D0 + i * 600000, 100.5, False) for i in range(0, 2 * 144)]
    return t0, filler


def _run_edge(t0, trades, side=1, L=100.0, X=101.0, dl_end=-1, fund=(), W=115, T=115, slip=5e-4):
    tr = sorted(trades)
    t = np.array([x[0] for x in tr], np.int64)
    p = np.array([x[1] for x in tr])
    ib = np.array([x[2] for x in tr])
    aid = np.arange(t.size, dtype=np.int64)
    MS = E.collapse_ms(t, aid, p, ib)
    U = dict(t0=np.array([t0]), side=np.array([side]), L=np.array([L]), X=np.array([X]), tick=np.array([0.1]),
             W=np.array([W]), T=np.array([T]), slip=np.array([slip]), dl_end=np.array([dl_end]))
    ft = np.array([f[0] for f in fund], np.int64)
    fr = np.array([f[1] for f in fund])
    out = {}
    P = R.prepare(list(zip(t.tolist(), aid.tolist(), p.tolist(), ib.tolist())))
    urow = {k: (v[0].item() if hasattr(v[0], "item") else v[0]) for k, v in U.items()}
    for m in E.MODELS:
        e = E.simulate(MS, U, m, D0, D0 + 2 * DAY, ft, fr)
        r = R.ref_unit(P, urow, m, D0, D0 + 2 * DAY, list(fund))
        nb, _, _ = compare(e, [r])
        out[m] = {c: (e[c][0].item() if hasattr(e[c][0], "item") else e[c][0]) for c in E.OUT_COLS}
        out[m]["ref_agree"] = nb == 0
    return out


def t3_edges():
    t0, fil = _edge_env()
    cases = {}
    chk = []
    # E1 xuyen dung 1 tick: cham (ibm True) truoc, xuyen sau
    o = _run_edge(t0, fil + [(t0 + 1000, 100.0, True), (t0 + 2000, 99.9, False)])
    cases["E1_through_1tick"] = o
    chk.append(o["THROUGH"]["tf"] == t0 + 2000 and o["TOUCH"]["tf"] == t0 + 1000)
    # E2 cham khong xuyen (ibm True) -> TOUCH khop, THROUGH khong
    o = _run_edge(t0, fil + [(t0 + 1000, 100.0, True)])
    cases["E2_touch_only"] = o
    chk.append(o["THROUGH"]["filled"] == 0 and o["TOUCH"]["filled"] == 1)
    # E3 cham sai ben (ibm False = mua chu dong tai 100.0) -> BUY khong khop ca hai
    o = _run_edge(t0, fil + [(t0 + 1000, 100.0, False)])
    cases["E3_touch_wrong_side"] = o
    chk.append(o["THROUGH"]["filled"] == 0 and o["TOUCH"]["filled"] == 0)
    # E4 tre 250 ms: xuyen X cung ms va +249 ms khong tinh; +250 ms tinh
    tf = t0 + 1000
    o = _run_edge(t0, fil + [(tf, 99.9, True), (tf, 101.2, False), (tf + 249, 101.2, False), (tf + 250, 101.1, False)])
    cases["E4_latency_250"] = o
    # (R-11: giao dich tf + 249 o 101.2 da vuot X -> THROUGH thoat TAKER tai X luc tf + 250; TOUCH thoat limit luc tf + 250)
    chk.append(o["THROUGH"]["kind"] == E.EX_TAKER_BEYOND and o["THROUGH"]["tx"] == tf + 250 and o["TOUCH"]["kind"] == E.EX_LIMIT
               and o["TOUCH"]["tx"] == tf + 250)
    # E5 thoat dung te (tinh) va te + 1 (khong -> het han; gia het han = giao dich cuoi <= te)
    te = tf + 115 * MIN
    o = _run_edge(t0, fil + [(tf, 99.9, True), (te, 101.1, False)])
    o2 = _run_edge(t0, fil + [(tf, 99.9, True), (te + 1, 101.1, False)])
    cases["E5_at_te"], cases["E5_after_te"] = o, o2
    lastp = 100.5
    chk.append(o["THROUGH"]["kind"] == E.EX_LIMIT and o["THROUGH"]["tx"] == te)
    chk.append(o2["THROUGH"]["kind"] == E.EX_TIMEOUT and o2["THROUGH"]["tx"] == te and abs(o2["THROUGH"]["xpx"] - lastp) < 1e-12)
    # E6 phi het han: THROUGH = maker vao + taker ra + truot s; TOUCH = maker 2 chan, khong truot
    g = (lastp - 100.0) / 100.0 * 1e4
    r = lastp / 100.0
    chk.append(abs(o2["THROUGH"]["net"] - (g - (2e-4 + 5e-4 * r) * 1e4 - 5e-4 * r * 1e4)) < 1e-9)
    chk.append(abs(o2["TOUCH"]["net"] - (g - (2e-4 + 2e-4 * r) * 1e4)) < 1e-9 and o2["TOUCH"]["slip"] == 0.0)
    chk.append(abs(o2["THROUGH"]["net_stress"] - (g - (4e-4 + 5e-4 * r) * 1e4 - 5e-4 * r * 1e4)) < 1e-9)
    # E7 cua so vuot nua dem: t0 = 23:00, khop 00:30 ngay sau, thoat 01:10
    t0b = D0 + 23 * 3600000
    o = _run_edge(t0b, fil + [(D0 + DAY + 1800000, 99.9, True), (D0 + DAY + 4200000, 101.1, False)])
    cases["E7_midnight"] = o
    chk.append(o["THROUGH"]["tf"] == D0 + DAY + 1800000 and o["THROUGH"]["tx"] == D0 + DAY + 4200000)
    # E8 lo: im lang dung 60 phut -> khong loai; 60 phut + 1 ms -> loai
    a = t0 + 600000
    base = [x for x in fil if not (a < x[0] < a + 3600001)]
    o = _run_edge(t0, base + [(a, 100.5, False), (a + 3600000, 100.5, False)])
    o2 = _run_edge(t0, [x for x in base if x[0] != a + 3600000] + [(a, 100.5, False), (a + 3600001, 100.5, False)])
    cases["E8_gap_60min"], cases["E8_gap_60min_1ms"] = o, o2
    chk.append(o["THROUGH"]["excl"] == 0 and o2["THROUGH"]["excl"] == 1 and o2["TOUCH"]["excl"] == 1)
    # E9 delist giua don vi: khop t0+60s, delist t0+30', khong thoat -> gia cuoi truoc delist, taker, THROUGH + 50 bps
    dl = t0 + 30 * MIN
    o = _run_edge(t0, [x for x in fil if x[0] < dl] + [(t0 + 60000, 99.9, True), (t0 + 120000, 100.3, False)], dl_end=dl)
    cases["E9_delist"] = o
    r = 100.3 / 100.0
    chk.append(o["THROUGH"]["kind"] == E.EX_DELIST and abs(o["THROUGH"]["xpx"] - 100.5) < 1e-12 if any(
        x[0] > t0 + 120000 and x[0] < dl for x in fil) else o["THROUGH"]["kind"] == E.EX_DELIST)
    lastd = [x for x in sorted(fil + [(t0 + 120000, 100.3, False)]) if x[0] < dl][-1][1]
    rr = lastd / 100.0
    chk.append(abs(o["THROUGH"]["slip"] - 50e-4 * rr * 1e4) < 1e-9 and abs(o["TOUCH"]["slip"]) < 1e-12
               and abs(o["TOUCH"]["fee"] - (2e-4 + 5e-4 * rr) * 1e4) < 1e-9)
    # E10 funding: moc = tf (khong), tf + 1 (co), = tx (co), tx + 1 (khong)
    tx = tf + 20 * MIN
    fund = [(tf, 0.001), (tf + 1, 0.0002), (tx, 0.0003), (tx + 1, 0.05)]
    o = _run_edge(t0, fil + [(tf, 99.9, True), (tx, 101.1, False)], fund=fund)
    cases["E10_funding"] = o
    mk1 = 99.9                                  # gia giao dich cuoi < tf + 1
    mk2 = [x for x in sorted(fil + [(tf, 99.9, True)]) if x[0] < tx][-1][1]
    exp_f = -(0.0002 * mk1 + 0.0003 * mk2) / 100.0 * 1e4
    chk.append(abs(o["THROUGH"]["fund"] - exp_f) < 1e-9 and o["THROUGH"]["tx"] == tx)
    # E11 bien cua so vao: giao dich xuyen tai t0 + W phut (khong) / t0 + W phut - 1 ms (co)
    we = t0 + 115 * MIN
    o = _run_edge(t0, fil + [(we, 99.9, True)])
    o2 = _run_edge(t0, fil + [(we - 1, 99.9, True)])
    chk.append(o["THROUGH"]["filled"] == 0 and o2["THROUGH"]["filled"] == 1)
    # E12 SELL doi xung E1: L 101.0, X 100.0
    o = _run_edge(t0, fil + [(t0 + 1000, 101.0, False), (t0 + 2000, 101.1, True)], side=-1, L=101.0, X=100.0)
    cases["E12_sell"] = o
    chk.append(o["THROUGH"]["tf"] == t0 + 2000 and o["TOUCH"]["tf"] == t0 + 1000)
    # E13 giao dich truoc t0 (xuyen) khong tinh
    o = _run_edge(t0, fil + [(t0 - 1, 99.0, True)])
    chk.append(o["THROUGH"]["filled"] == 0 and o["TOUCH"]["filled"] == 0)
    # E14 TOUCH: gia < L (ben mua chu dong) van khop BUY
    o = _run_edge(t0, fil + [(t0 + 1000, 99.95, False)], L=100.0)
    chk.append(o["TOUCH"]["filled"] == 1 and o["THROUGH"]["filled"] == 0)
    # E15 bien the chi bao cao THROUGH_LAT5S: vao tu t0 + 5 s, thoat tu tf + 5 s (engine va tl_ref); LAT5S: gia da vuot X luc
    # lenh thoat co hieu luc (t0 + 11 s) -> TAKER tai X (R-11 ap cho LAT5S)
    tr = sorted(fil + [(t0 + 4999, 99.9, True), (t0 + 6000, 99.9, True), (t0 + 6300, 101.1, False), (t0 + 11000, 101.1, False)])
    tt = np.array([x[0] for x in tr], np.int64)
    pp = np.array([x[1] for x in tr])
    bb = np.array([x[2] for x in tr])
    ai = np.arange(tt.size, dtype=np.int64)
    MSx = E.collapse_ms(tt, ai, pp, bb)
    Ux = dict(t0=np.array([t0]), side=np.array([1]), L=np.array([100.0]), X=np.array([101.0]), tick=np.array([0.1]),
              W=np.array([115]), T=np.array([115]), slip=np.array([5e-4]), dl_end=np.array([-1]))
    a5 = E.simulate(MSx, Ux, "THROUGH_LAT5S", D0, D0 + 2 * DAY)
    a0 = E.simulate(MSx, Ux, "THROUGH", D0, D0 + 2 * DAY)
    Px = R.prepare(list(zip(tt.tolist(), ai.tolist(), pp.tolist(), bb.tolist())))
    ur = {k: (v[0].item() if hasattr(v[0], "item") else v[0]) for k, v in Ux.items()}
    r5 = R.ref_unit(Px, ur, "THROUGH_LAT5S", D0, D0 + 2 * DAY)
    chk.append(int(a0["tf"][0]) == t0 + 4999 and int(a0["kind"][0]) == E.EX_LIMIT and int(a0["tx"][0]) == t0 + 6300
               and int(a5["tf"][0]) == t0 + 6000 and int(a5["kind"][0]) == E.EX_TAKER_BEYOND and int(a5["tx"][0]) == t0 + 11000
               and compare(a5, [r5])[0] == 0 and compare(a0, [R.ref_unit(Px, ur, "THROUGH", D0, D0 + 2 * DAY)])[0] == 0)
    # E16 (R-11) THROUGH: giao dich gan nhat truoc tf + 250 ms da vuot X >= 1 tick -> thoat TAKER tai X luc tf + 250, khong truot;
    # TOUCH giu maker (thoat o giao dich cham ke tiep sau tf + 250)
    o = _run_edge(t0, fil + [(tf, 99.9, True), (tf + 100, 101.2, False), (tf + 400, 101.3, False)])
    cases["E16_taker_beyond"] = o
    rb = 101.0 / 100.0
    chk.append(o["THROUGH"]["kind"] == E.EX_TAKER_BEYOND and o["THROUGH"]["tx"] == tf + 250 and o["THROUGH"]["xpx"] == 101.0
               and abs(o["THROUGH"]["fee"] - (2e-4 + 5e-4 * rb) * 1e4) < 1e-9 and o["THROUGH"]["slip"] == 0.0
               and o["THROUGH"]["n_maker"] == 1 and o["TOUCH"]["kind"] == E.EX_LIMIT and o["TOUCH"]["tx"] == tf + 400)
    # E17 gia gan nhat dung BANG X (chua vuot 1 tick) -> khong taker; thoat limit khi xuyen sau do
    o = _run_edge(t0, fil + [(tf, 99.9, True), (tf + 100, 101.0, False), (tf + 400, 101.1, False)])
    cases["E17_at_X_not_beyond"] = o
    chk.append(o["THROUGH"]["kind"] == E.EX_LIMIT and o["THROUGH"]["tx"] == tf + 400)
    # E18 SELL doi xung: ban tai 101.0, X 100.0, gia 99.9 truoc tf + 250 -> taker tai 100.0
    o = _run_edge(t0, fil + [(tf, 101.1, False), (tf + 200, 99.9, True)], side=-1, L=101.0, X=100.0)
    cases["E18_sell_beyond"] = o
    chk.append(o["THROUGH"]["kind"] == E.EX_TAKER_BEYOND and o["THROUGH"]["xpx"] == 100.0 and o["THROUGH"]["tx"] == tf + 250)
    agree = all(v[m]["ref_agree"] for v in cases.values() for m in E.MODELS)
    return all(chk) and agree, dict(checks=chk, n_checks=len(chk), ref_agree_all=agree)


def t5_no_lookahead():
    """Rac sau moc tc: don vi co (ket thuc + 60') < tc GIONG HET moi cot; don vi ket thuc < tc giong het tru cot excl
    (dinh nghia lo can toi 60' sau ket thuc - nhu lgc S1)."""
    rng = np.random.default_rng(2026112304)
    n_full = n_out = d_full = d_out = 0
    for v in range(40):
        day0 = D0 + v * 2 * DAY
        tr, rows, ft, fr, _, _ = make_path(rng, day0, v)
        if not rows:
            continue
        U = U_from_rows(rows)
        tc = day0 + int(rng.integers(6, 30)) * 3600000 + int(rng.integers(0, 3600000))
        tr2 = {k: v_.copy() for k, v_ in tr.items()}
        j = tr2["t"] >= tc
        tr2["p"][j] = np.round(tr2["p"][j] * rng.uniform(0.9, 1.1, j.sum()) / U["tick"][0]) * U["tick"][0]
        tr2["ibm"][j] = rng.random(j.sum()) < 0.5
        for m in E.MODELS:
            a = E.simulate(ms_of(tr), U, m, day0, day0 + 2 * DAY, ft, fr)
            b = E.simulate(ms_of(tr2), U, m, day0, day0 + 2 * DAY, ft, fr)
            end = np.where(a["filled"] == 1, a["tx"], np.minimum(U["t0"] + 115 * MIN,
                                                                np.where(U["dl_end"] >= 0, U["dl_end"], 1 << 62)))
            for i in range(len(rows)):
                same_all = all((a[c][i] == b[c][i]) or (np.isnan(a[c][i]) and np.isnan(b[c][i])) for c in E.OUT_COLS)
                same_out = all((a[c][i] == b[c][i]) or (np.isnan(a[c][i]) and np.isnan(b[c][i])) for c in E.OUT_COLS
                               if c != "excl")
                if end[i] + E.GAP_MS < tc:
                    n_full += 1
                    d_full += int(not same_all)
                if end[i] < tc:
                    n_out += 1
                    d_out += int(not same_out)
    return d_full == 0 and d_out == 0 and n_full > 500, dict(n_units_end_plus60_before_tc=n_full, diff_all_cols=d_full,
                                                            n_units_end_before_tc=n_out, diff_outcome_cols=d_out)


# ------------------------------------------------------------------------------------------------ T6 - T10 (pipeline)
import shutil  # noqa: E402
import pandas as pd  # noqa: E402
import sample as SM  # noqa: E402
import fetch_reduce as FR  # noqa: E402
import run_s2 as RS  # noqa: E402


def _fake_events_table(rng, nclus=900):
    rows = []
    syms = ["S%02dUSDT" % i for i in range(60)]
    for c in range(nclus):
        s = syms[int(rng.integers(0, 60))]
        day = int(rng.integers(SM.STUDY_DAY + 5, SM.NDAY - 3))
        tier = 1 + (hash((s, day)) % 3)
        for h in sorted(set(rng.integers(0, 24, int(rng.integers(1, 4))).tolist())):
            for side in (1, -1):
                ok = rng.random() < 0.7
                rows.append(dict(sym=s, day=day, tier=tier, t0_ms=DS + day * DAY + h * 3600000, side=side,
                                 o_filled=int(ok), o_excl=0, o_ok=int(ok), o_net=float(rng.standard_t(3) * 200 + 20),
                                 p_filled=int(ok), p_excl=0, p_ok=int(ok), p_net=float(rng.standard_t(3) * 250 - 15)))
    ev = pd.DataFrame(rows).drop_duplicates(["sym", "t0_ms", "side"])
    ev["date"] = pd.to_datetime(DS + ev.day * DAY, unit="ms").dt.strftime("%Y-%m-%d")
    return ev


def t6_sampling():
    rng = np.random.default_rng(2026112306)
    ev = _fake_events_table(rng)
    d1, d2 = os.path.join(OUT, "_t6a"), os.path.join(OUT, "_t6b")
    fm = {"A": 0.3, "B": 0.2}
    fr1, m1 = SM.make_sample(ev, d1, fm)
    fr2, m2 = SM.make_sample(ev.sample(frac=1.0, random_state=7).reset_index(drop=True), d2, fm)
    chk = dict(same_sha=m1["sample_csv_sha256"] == m2["sample_csv_sha256"])
    g = fr1.groupby("stratum")
    prop = all(int(x.selected.sum()) == min(len(x), max(1, int(round(fm[x.half.iloc[0]] * len(x) + 1e-9)))) for _, x in g)
    chk["proportional"] = prop
    chk["selected_are_first_ranks"] = all((x.selected == (x["rank"] < x.selected.sum())).all() for _, x in g)
    chk["rank_by_key"] = all(list(x.sort_values("rank").key) == sorted(x.key) for _, x in g)
    late = fr1[fr1.files.str.contains(";")]
    chk["next_day_when_late"] = len(late) > 0 and all(
        (ev[(ev.sym == r.sym) & (ev.date == r.date)].t0_ms.max() + (115 + 115 + 61) * MIN > DS + (r.day + 1) * DAY)
        for r in late.itertuples())
    evd = ev.copy()
    evd["dl_end_ms"] = -1
    r0 = late.iloc[0]
    evd.loc[(evd.sym == r0.sym) & (evd.date == r0.date), "dl_end_ms"] = DS + (int(r0.day) + 1) * DAY - 5 * MIN
    cf = SM.cluster_frame(evd)
    chk["no_next_day_if_delisted"] = ";" not in cf[(cf.sym == r0.sym) & (cf.date == r0.date)].files.iloc[0]
    for h in ("A", "B"):
        a = fr1[(fr1.half == h) & fr1.audit]
        chk["audit_" + h] = bool(a.selected.all() and (a.n_units.sum() >= SM.AUDIT_MIN_UNITS or len(a) == (fr1.half == h).sum()))
    se = [SM.se_pred(SM.se_parts(ev, "B", "p"), f) for f in SM.F_GRID]
    chk["se_pred_decreasing"] = all(np.diff(se) <= 1e-12)
    ch = SM.choose_f(ev)
    fB = ch["B"]["f"]
    i = SM.F_GRID.index(fB)
    chk["auto_f_smallest"] = (max(ch["B"]["table"][str(fB)].values()) <= SM.SE_TARGET or fB == 1.0) and (
        i == 0 or max(ch["B"]["table"][str(SM.F_GRID[i - 1])].values()) > SM.SE_TARGET)
    ev26 = ev.copy()
    ev26.loc[ev26.index[0], "date"] = "2026-01-02"
    try:
        SM.cluster_frame(ev26.assign(t0_ms=ev26.t0_ms))
        os.makedirs(os.path.join(OUT, "_t6c"), exist_ok=True)
        ev26.to_parquet(os.path.join(OUT, "_t6c", "events_s0.parquet"))
        SM.load_events(os.path.join(OUT, "_t6c"))
        chk["block_2026"] = False
    except RuntimeError:
        chk["block_2026"] = True
    # MASTER D2: tran tai -> f LON NHAT trong luoi con <= tran (HEAD gia: moi file 1 MB)
    d3 = os.path.join(OUT, "_t6d")
    SM.make_sample(ev, d3, {"A": 0.5, "B": 0.5})
    frx = SM.read_csv(os.path.join(d3, "sample.csv"))[0]
    rows_h = [dict(sym=s, date=d, status=200, bytes=10**6) for s, ff in zip(frx[frx.selected].sym, frx[frx.selected].files)
              for d in ff.split(";")]
    rows_h = list({(r["sym"], r["date"]): r for r in rows_h}.values())
    json.dump(dict(rows=rows_h), open(os.path.join(d3, "head.json"), "w"))
    cap0 = SM.CAP_BYTES
    try:
        SM.CAP_BYTES = 1e15
        m_nc = SM.apply_cap(ev, d3, os.path.join(d3, "head.json"))
        SM.CAP_BYTES = len(rows_h) * 1e6 * 0.45
        m_c = SM.apply_cap(ev, d3, os.path.join(d3, "head.json"))
    finally:
        SM.CAP_BYTES = cap0
    fa = m_c["cap"]["f_after"]["B"]
    nxt = [f for f in SM.F_GRID if f > fa and f <= 0.5]
    chk["cap_not_applied_under"] = m_nc["cap"]["applied"] is False
    chk["cap_largest_f_within"] = m_c["cap"]["applied"] and m_c["cap"]["total_bytes"] <= len(rows_h) * 1e6 * 0.45 and fa < 0.5
    shutil.rmtree(d3, ignore_errors=True)
    try:
        SM.read_csv(os.path.join(d1, "sample.csv"), "0" * 64)
        chk["sha_guard"] = False
    except RuntimeError:
        chk["sha_guard"] = True
    for d in (d1, d2, os.path.join(OUT, "_t6c")):
        shutil.rmtree(d, ignore_errors=True)
    return all(chk.values()), dict(checks=chk, f_auto=dict(A=ch["A"]["f"], B=fB), se_pred_B=dict(zip(map(str, SM.F_GRID), se)))


def _day_ms(date):
    return int(pd.Timestamp(date, tz="UTC").value // 10**6)


def build_world(root, seed=2026112307):
    """The gioi gia day du: 3 symbol (tier 1/2/3) x 8 ngay (4 nua A, 4 nua B) + ngay ke tiep, zip dang Vision, danh sach su kien
    (ket qua K_OPT/K_PESS tinh bang klite S1 tren nen dung lai -> W2/W3 phai 100 %), kline cua so, funding, validate/manifest."""
    import klite
    rng = np.random.default_rng(seed)
    vroot = os.path.join(root, "vision")
    evd = os.path.join(root, "events")
    os.makedirs(evd, exist_ok=True)
    syms = [("AAAUSDT", 0.1, 20000, 1), ("BBBUSDT", 0.001, 15000, 2), ("CCCUSDT", 0.01, 12000, 3)]
    dates = ["2022-03-14", "2022-08-02", "2023-05-20", "2023-11-07", "2024-02-10", "2024-09-15", "2025-03-03", "2025-07-21"]
    ev_rows, kw_rows, fu_rows = [], [], []
    for sym, tick, k0, tier in syms:
        aid0 = 10**6
        for date in dates:
            d0 = _day_ms(date)
            delist = sym == "CCCUSDT" and date == "2024-09-15"
            stop = d0 + 16 * 3600000 if delist else None
            tr1 = S.gen_trades(rng, d0, DAY, k0, tick, mean_gap_ms=2500.0, same_ms_p=0.2, jump_p=0.02, ibm_flip=0.05,
                               stop_ms=stop, aid0=aid0, quiet=[(d0 + 5 * 3600000, d0 + 5 * 3600000 + 70 * MIN)] if tier == 3 else ())
            aid0 = int(tr1["aid"][-1]) + 1
            kl = int(round(tr1["p"][-1] / tick))
            tr2 = S.gen_trades(rng, d0 + DAY, DAY, kl, tick, mean_gap_ms=2500.0, same_ms_p=0.2, jump_p=0.02, ibm_flip=0.05,
                               aid0=aid0) if not delist else S.gen_trades(rng, d0 + DAY, 1, kl, tick, aid0=aid0)
            aid0 = (int(tr2["aid"][-1]) + 1) if tr2["t"].size else aid0
            nd = pd.Timestamp(d0 + DAY, unit="ms").strftime("%Y-%m-%d")
            S.write_vision_zip(vroot, sym, date, tr1, header=(tier != 2), bool_style="lower" if tier != 3 else "title")
            S.write_vision_zip(vroot, sym, nd, tr2, header=True)
            tr = S.concat(tr1, tr2)
            MS = E.collapse_ms(tr["t"], tr["aid"], tr["p"], tr["ibm"])
            bars = E.minute_bars(MS)
            bc = dict(zip(bars["mi"].tolist(), bars["c"].tolist()))
            dl_end = ((int(tr1["t"][-1]) // MIN + 1) * MIN) if delist else -1
            hours = [1, 3, 5, 7, 9, 11, 13, 15] if delist else [1, 3, 5, 7, 9, 11, 13, 15, 17, 22]
            shat = float(rng.choice([4e-4, 1e-3, 3e-3]))
            slip = max(klite.SLIP_TIER_FLOOR[tier], shat / 2)
            rows = S.units_from_bars(bc, None, [d0 + h * 3600000 for h in hours], [0.004] * len(hours), tick, 115, 115, slip,
                                     dl_end)
            base = (d0 - DS) // MIN
            O, H, L_, C, valid = _grid_from_bars(bars, d0, 2 * 1440)
            dl_idx = -1 if dl_end < 0 else (dl_end - d0) // MIN - 1
            G = klite.prepare_grid(O, H, L_, C, valid, dl_idx)
            ft = np.arange(d0, d0 + 2 * DAY, 8 * 3600000, dtype=np.int64)
            frt = rng.normal(1e-4, 2e-4, ft.size)
            fu_rows += [dict(sym=sym, ts=int(a), rate=float(b)) for a, b in zip(ft, frt)]
            t0i = np.array([r["t0_min"] - base for r in rows])
            side = np.array([r["side"] for r in rows])
            out = {}
            for model, pre in (("OPT", "o_"), ("PESS", "p_")):
                Rk = klite.run_units(G, t0i, 0.004, 115, 115, tick, slip, model, side, (ft - d0) // MIN, frt)
                ok = Rk["filled"] & (Rk["excl"] == 0)
                out.update({pre + "filled": Rk["filled"].astype(int), pre + "excl": Rk["excl"].astype(int),
                            pre + "ok": ok.astype(int), pre + "f_ms": np.where(Rk["f"] >= 0, d0 + Rk["f"] * MIN, -1),
                            pre + "x_ms": np.where(Rk["x"] >= 0, d0 + Rk["x"] * MIN, -1), pre + "kind": Rk["kind"].astype(int),
                            pre + "xpx": Rk["xpx"], pre + "gross": Rk["gross"], pre + "fee": Rk["fee"], pre + "slipc": Rk["slip"],
                            pre + "fund": Rk["fund"], pre + "net": Rk["net"], pre + "n_maker": Rk["n_maker"]})
            for i, r in enumerate(rows):
                er = dict(sym=sym, t0_min=r["t0_min"], side=r["side"], m0=r["m0"], d=0.004, sigma_1d=0.02, tick=tick, L=r["L"],
                          X=r["X"], tier=tier, slip=slip, day=(d0 - DS) // DAY, W=115, T=115, s_hat=shat, t0_ms=r["t0"],
                          date=date, dl_end_ms=dl_end, first_ms=DS)
                er.update({k: (v[i].item() if hasattr(v[i], "item") else v[i]) for k, v in out.items()})
                ev_rows.append(er)
            need = set()
            for r in rows:
                need.update(range(r["t0_min"] - 61, r["t0_min"] + 115 + 115 + 62))
            for m in sorted(need):
                j = m - base
                if 0 <= j < 2 * 1440:
                    kw_rows.append(dict(sym=sym, mi=m, valid=bool(valid[j]), o=O[j], h=H[j], l=L_[j], c=C[j]))
    ev = pd.DataFrame(ev_rows)
    kw = pd.DataFrame(kw_rows)
    fu = pd.DataFrame(fu_rows)
    for i in range(5):
        sl = [s for j, (s, _, _, _) in enumerate(syms) if j % 5 == i]
        ev[ev.sym.isin(sl)].to_parquet(os.path.join(evd, "events_s%d.parquet" % i), index=False)
        kw[kw.sym.isin(sl)].to_parquet(os.path.join(evd, "kline_win_s%d.parquet" % i), index=False)
        fu[fu.sym.isin(sl)].to_parquet(os.path.join(evd, "funding_ev_s%d.parquet" % i), index=False)
        json.dump(dict(all_pass=True), open(os.path.join(evd, "validate_s%d.json" % i), "w"))
        json.dump(dict(shard="%d/5" % i, prereg_constants=False, inputs={}, code={}),
                  open(os.path.join(evd, "manifest_s%d.json" % i), "w"))
    return vroot, evd, ev


def _fetch(vroot, evd, smp, sha, out, extra=()):
    return FR.main(["--sample", smp, "--sample-sha", sha, "--events", evd, "--out", out, "--base-url", "file://" + vroot,
                    "--workers", "3", "--batch", "5", "--min-free-gb", "0.5", "--max-temp-gb", "1"] + list(extra), _test=True)


class _A:
    pass


def _run_s2(evd, fout, smp, sha, resd, nboot=300):
    a = _A()
    a.events, a.fetch, a.sample, a.sample_sha, a.expected_sha, a.run2, a.s1code, a.out = evd, fout, smp, sha, None, None, S1DIR, resd
    return RS.run(a, allow_test=True, nboot=nboot)


def t7_fetch_reduce():
    """zip gia dinh dang Vision: tieu de co/khong, bool true/True, checksum SAI (thu lai roi = thieu), file THIEU -> thay the tu
    danh sach du phong dung tang; chan 2026; gioi han dia; khoi dong lai tu checkpoint; xoa file tho."""
    root = os.path.join(OUT, "_t7")
    shutil.rmtree(root, ignore_errors=True)
    vroot, evd, ev = build_world(root)
    fr, man = SM.make_sample(ev, os.path.join(root, "smp"), {"A": 0.5, "B": 0.5})
    smp, sha = os.path.join(root, "smp", "sample.csv"), man["sample_csv_sha256"]
    sel = fr[fr.selected].sort_values("key")
    m1, m2 = sel.iloc[0], sel.iloc[1]
    os.remove(os.path.join(vroot, "data/futures/um/daily/aggTrades", m1.sym, "%s-aggTrades-%s.zip" % (m1.sym, m1.date)))
    S.write_vision_zip(vroot, "ZZZUSDT", "2024-01-01", S.gen_trades(np.random.default_rng(1), _day_ms("2024-01-01"), 3600000,
                                                                     100, 0.1))
    ckp = os.path.join(vroot, "data/futures/um/daily/aggTrades", m2.sym, "%s-aggTrades-%s.zip.CHECKSUM" % (m2.sym, m2.date))
    h, nm = open(ckp).read().split()
    open(ckp, "w").write(("0" if h[0] != "0" else "1") + h[1:] + "  " + nm + "\n")
    fout = os.path.join(root, "fetch")
    st = _fetch(vroot, evd, smp, sha, fout)
    chk = {}
    chk["missing_two"] = st["done"]["%s|%s" % (m1.sym, m1.date)]["status"] == "missing" and \
        st["done"]["%s|%s" % (m2.sym, m2.date)]["status"] == "missing"
    subs = {s["missing"]: s for s in st["subs"]}
    chk["substituted_same_stratum"] = all(subs[k]["sub"] is not None and subs[k]["stratum"] == r.stratum
                                          for k, r in (("%s|%s" % (m1.sym, m1.date), m1), ("%s|%s" % (m2.sym, m2.date), m2)))
    chk["subs_done_ok"] = all(st["done"][subs[k]["sub"]]["status"] == "ok" for k in subs)
    fl = [json.loads(x) for x in open(os.path.join(fout, "files.jsonl"))]
    chk["checksum_retried"] = any(r["status"] == "checksum" and r["tries"] == FR.RETRY + 1 for r in fl)
    chk["w6_fail_when_17pct"] = st["W6"]["ok"] is False
    chk["tmp_empty"] = len(os.listdir(os.path.join(fout, "tmp"))) == 0
    nparts = len(glob.glob(os.path.join(fout, "res", "*.parquet")))
    st2 = _fetch(vroot, evd, smp, sha, fout)
    chk["resume_no_rework"] = len(glob.glob(os.path.join(fout, "res", "*.parquet"))) == nparts and st2["done"] == st["done"]
    try:
        FR.url_of("file://x", "AAAUSDT", "2026-01-01")
        chk["block_2026"] = False
    except RuntimeError:
        chk["block_2026"] = True
    try:
        _fetch(vroot, evd, smp, sha, os.path.join(root, "fetch_disk"), extra=["--min-free-gb", "1e9"])
        chk["disk_guard"] = False
    except RuntimeError:
        chk["disk_guard"] = True
    try:
        _fetch(vroot, evd, smp, "f" * 64, os.path.join(root, "fetch_sha"))
        chk["sample_sha_guard"] = False
    except RuntimeError:
        chk["sample_sha_guard"] = True
    t, aid, p, ibm, c1 = FR.parse_zip(os.path.join(vroot, "data/futures/um/daily/aggTrades/BBBUSDT",
                                                   "BBBUSDT-aggTrades-%s.zip" % "2022-03-14"), "2022-03-14")
    chk["no_header_parsed"] = t.size > 1000 and c1["id_gaps"] == 0 and c1["n_outside_day"] == 0
    t, aid, p, ibm, c3 = FR.parse_zip(os.path.join(vroot, "data/futures/um/daily/aggTrades/CCCUSDT",
                                                   "CCCUSDT-aggTrades-%s.zip" % "2022-03-14"), "2022-03-14")
    chk["title_bool_parsed"] = 0 < ibm.sum() < ibm.size
    res = _run_s2(evd, fout, smp, sha, os.path.join(root, "res_fail"))
    chk["run_s2_W_FAIL_no_M"] = res["rule"] == "TEST_ONLY:W_FAIL" and "models" not in res
    return all(chk.values()), dict(checks=chk, W6=st["W6"], n_files_log=len(fl))


def t10_e2e():
    """Pipeline day du tren the gioi gia (khong file thieu): sample -> fetch_reduce -> run_s2: W0-W6 PASS (W2/W3 100 %, W5 0 lech
    tren >= 200 don vi audit), luat duoc tinh, TEST_ONLY."""
    root = os.path.join(OUT, "_t10")
    shutil.rmtree(root, ignore_errors=True)
    vroot, evd, ev = build_world(root, seed=2026112310)
    fr, man = SM.make_sample(ev, os.path.join(root, "smp"), {"A": 0.5, "B": 0.5})
    smp, sha = os.path.join(root, "smp", "sample.csv"), man["sample_csv_sha256"]
    fout = os.path.join(root, "fetch")
    st = _fetch(vroot, evd, smp, sha, fout)
    res = _run_s2(evd, fout, smp, sha, os.path.join(root, "res"))
    W = res["W"]
    ok = res["W_all_pass"] and res["rule"].startswith("TEST_ONLY:L2-") and W["W2_bars_vs_kline"]["frac_low_high_equal"] == 1.0 \
        and W["W3_klite_rebuilt"]["K_OPT"]["agree_all"] == 1.0 and W["W3_klite_rebuilt"]["K_PESS"]["agree_all"] == 1.0 \
        and W["W5_ref"]["n_units"] >= 200 and W["W4_no_lookahead"]["n_full"] > 0
    # kiem luc W: (a) kline lake lech low o 2 % phut -> W2 FAIL; (b) sua 1 ket qua da luu -> W5 (phat lai) FAIL;
    # (c) S1 K_OPT ghi sai phut khop 10 % don vi da khop -> W3 FAIL
    ev2 = os.path.join(root, "events2")
    shutil.copytree(evd, ev2)
    rngp = np.random.default_rng(5)
    for f in glob.glob(os.path.join(ev2, "kline_win_s*.parquet")):
        k = pd.read_parquet(f)
        j = (rngp.random(len(k)) < 0.02) & k.valid.to_numpy()
        k.loc[j, "l"] = k.loc[j, "l"] * 0.999
        k.to_parquet(f, index=False)
    ra = _run_s2(ev2, fout, smp, sha, os.path.join(root, "res_a"))
    ev3 = os.path.join(root, "events3")
    shutil.copytree(evd, ev3)
    for f in glob.glob(os.path.join(ev3, "events_s*.parquet")):
        e = pd.read_parquet(f)
        if len(e):
            j = (rngp.random(len(e)) < 0.10) & (e.o_filled.to_numpy() == 1)
            e.loc[j, "o_f_ms"] = e.loc[j, "o_f_ms"] + MIN
            e.to_parquet(f, index=False)
    rc = _run_s2(ev3, fout, smp, sha, os.path.join(root, "res_c"))
    pf = sorted(glob.glob(os.path.join(fout, "res", "part_*.parquet")))[0]
    r0 = pd.read_parquet(pf)
    i = int(np.flatnonzero(r0.filled.to_numpy() == 1)[0])
    r0.loc[r0.index[i], "net"] = r0.loc[r0.index[i], "net"] + 0.5
    r0.to_parquet(pf, index=False)
    rb = _run_s2(evd, fout, smp, sha, os.path.join(root, "res_b"))
    power = dict(W2_detects=ra["W"]["W2_bars_vs_kline"]["ok"] is False and ra["rule"].endswith("W_FAIL"),
                 W3_detects=rc["W"]["W3_klite_rebuilt"]["ok"] is False and rc["rule"].endswith("W_FAIL"),
                 W5_detects=rb["W"]["W5_ref"]["ok"] is False and rb["rule"].endswith("W_FAIL"))
    ok = ok and all(v for v in power.values() if isinstance(v, bool))
    power["W3_agree_all_perturbed"] = rc["W"]["W3_klite_rebuilt"]["K_OPT"]["agree_all"]
    keep = dict(W_power=power, W={k: v for k, v in W.items()}, rule=res["rule"],
                M={m: {h: res["models"][m][h]["M"] for h in "AB"} for m in res["models"]} if "models" in res else None)
    shutil.rmtree(root, ignore_errors=True)
    return ok, keep


def _rule_units(rng, mu_thr, mu_tch, n_per_day=3, sd=150.0, days=None):
    rows = []
    days = days if days is not None else range(SM.STUDY_DAY, SM.NDAY)
    for d in days:
        y = int(pd.Timestamp(DS + d * DAY, unit="ms").year)
        for j in range(n_per_day):
            e = rng.standard_t(4) * sd
            for m, mu in (("THROUGH", mu_thr), ("TOUCH", mu_tch)):
                rows.append(dict(model=m, day=d, sym="S%02dUSDT" % int(rng.integers(0, 40)), tier=1 + j % 3, year=y, w=1.0,
                                 s_hat=4e-4, filled=1, excl=0, net=mu + e, net_stress=mu + e - 2.0, n_maker=1,
                                 kind=1, gross=mu + e + 4, fee=4.0, slip=0.0, fund=0.0))
    return pd.DataFrame(rows)


def t8_rules():
    _, stats = RS.import_s1(S1DIR)
    rng = np.random.default_rng(2026112308)
    sc = {"L2-A": (25.0, 30.0), "L2-B": (-15.0, 25.0), "L2-C": (-15.0, -5.0)}
    got = {}
    for want, (a, b) in sc.items():
        U = _rule_units(rng, a, b)
        R = {m: RS.analyze(stats, U, m, nboot=300) for m in E.MODELS}
        got[want] = (RS.decide(R), {m: (round(R[m]["B"]["M"], 2), round(R[m]["B"]["p"], 4), R[m]["PASS"]) for m in R})
    U = _rule_units(rng, 25.0, 30.0, days=range(SM.STUDY_DAY, SM.STUDY_DAY + 40))
    R = {m: RS.analyze(stats, U, m, nboot=200) for m in E.MODELS}
    got["L2-INS"] = (RS.decide(R), None)
    U = _rule_units(rng, 25.0, 30.0)
    ev_d = (U.day >= 1620) & (U.day <= 1626)
    thr_b = (U.model == "THROUGH") & (U.day >= SM.HALF_B_DAY)
    U.loc[thr_b & ~ev_d, "net"] -= 35.0
    U.loc[thr_b & ev_d, "net"] = 3000.0
    R = {m: RS.analyze(stats, U, m, nboot=200) for m in E.MODELS}
    got["event_cond"] = (RS.decide(R), R["THROUGH"]["conditions"], round(R["THROUGH"]["B"]["M"], 2),
                         round(R["THROUGH"]["B"]["M_drop_events"], 2))
    U = _rule_units(rng, 25.0, 30.0)
    R = {m: RS.analyze(stats, U, m, nboot=200) for m in E.MODELS}
    Ud = U[U.model == "THROUGH"].assign(model="THROUGH_LAT5S")
    Ud["net"] = Ud["net"] - 40.0
    Rd = {"THROUGH_LAT5S": RS.analyze(stats, Ud, "THROUGH_LAT5S", nboot=200)}
    got["infra"] = (RS.infra_label(RS.decide(R), R, Rd), RS.infra_label(RS.decide(R), R, {"THROUGH_LAT5S": R["THROUGH"]}))
    ok = got["infra"] == ("L2-A-INFRA", "L2-A") and RS.ALPHA_B == 0.04
    ok = ok and all(got[k][0] == k for k in sc) and got["L2-INS"][0] == "L2-INS" and got["event_cond"][0] != "L2-A" \
        and got["event_cond"][1]["e_events"] is False and got["event_cond"][2] > 4
    return ok, {k: str(v) for k, v in got.items()}


def _null_day_sums(rng, D, regime):
    lam = np.exp(rng.normal(np.log(8.0), 0.8, D))
    ncl = rng.poisson(lam)
    S_ = np.zeros(D)
    N_ = np.zeros(D)
    reg = np.repeat(rng.standard_t(3, -(-D // 30)) * 15.0, 30)[:D] if regime else np.zeros(D)
    for d in range(D):
        if ncl[d] == 0:
            continue
        k = rng.integers(1, 7, ncl[d])
        de = rng.standard_t(3) * 40.0 + reg[d]
        ce = rng.standard_t(3, ncl[d]) * 80.0
        S_[d] = float(((4.0 + de + ce) * k).sum() + rng.standard_t(3, int(k.sum())).sum() * 150.0)
        N_[d] = k.sum()
    return S_, N_


def t9_size():
    """Size kiem 1 o (bootstrap-t studentized khoi 20 ngay, 1 phia, stats.py S1) tren null CUM, M that = 4 bps = san:
    'cum' = hieu ung ngay + cum (sym, ngay) + nhieu t3, so cum / ngay thay doi (phu thuoc < 20 ngay -> dung gia dinh khoi);
    'cum+che_do30' = them hieu ung che do 30 ngay (phu thuoc DAI HON khoi 20 ngay - chi bao cao, xem rui ro R-3).
    PASS (luat test) = size null 'cum' <= alpha + 1,96 SE_MC o ca 2 nua. Bao cao size o alpha danh nghia 0,02-0,10."""
    _, stats = RS.import_s1(S1DIR)
    res = {}
    ok = True
    for variant, regime in (("cum", False), ("cum+che_do30", True)):
        for h, D, alpha, R_ in (("B", 731, 0.05, 800), ("A", 914, 0.10, 400)):
            rng = np.random.default_rng(2026112309 + (7 if regime else 0) + (1 if h == "A" else 0))
            ps = []
            for r in range(R_):
                S_, N_ = _null_day_sums(rng, D, regime)
                st = stats.cell_stats(S_[:, None], N_[:, None], 4.0, 1000 + r, B=400)
                ps.append(float(st["p_marg"][0]))
            ps = np.array(ps)
            se = np.sqrt(alpha * (1 - alpha) / R_)
            size = float(np.mean(ps <= alpha))
            res["%s_%s" % (variant, h)] = dict(R=R_, alpha=alpha, size=size, mc_se=se, limit=alpha + 1.96 * se,
                                               size_at={str(a_): float(np.mean(ps <= a_)) for a_ in (0.02, 0.03, 0.04, 0.05, 0.075, 0.10)})
            if variant == "cum":
                ok &= size <= alpha + 1.96 * se
    return ok, res


def t11_events_kernel():
    """events_kernel tren LAKE GIA cua S1 (synth.write_fake_lake, dung slug allowlist): 5 shard -> validate all_pass (V0a/V0b/V1/V2/
    V3/V6/E1a), prereg_constants False (test_overrides: registry lake gia, mkt AAAUSDT, COND_A vmult 0,5 de co su kien); tong theo
    (mo hinh, ngay) cua su kien == reduced/agg o 20 cua runner S1 GHIM chay tren CUNG lake (E1b); build tao 5 kernel, sha wrapper."""
    import subprocess
    import synth
    root = os.path.join(OUT, "_t11")
    shutil.rmtree(root, ignore_errors=True)
    kd, lake, evd, s1o = (os.path.join(root, x) for x in ("code", "lake", "events", "s1run/d0"))
    for d in (kd, evd, s1o):
        os.makedirs(d, exist_ok=True)
    for f in ("klite.py", "kref.py", "stats.py", "runner_kaggle.py"):
        shutil.copy(os.path.join(S1DIR, f), kd)
    shutil.copy(os.path.join(HERE, "events_kernel.py"), kd)
    meta = synth.write_fake_lake(lake)
    tov = dict(registry={int(k_): v for k_, v in meta["rows"].items()}, mkt_sym="AAAUSDT", cond={"A": dict(z=2.5, vmult=0.5)})
    env = dict(os.environ, GRIDV2S2_INPUT=lake, GRIDV2S2_OUT=evd)
    t = time.time()
    for i in range(5):
        env["GRIDV2S2_SHARD"] = "%d/5" % i
        rc = subprocess.run([sys.executable, "-c", "import events_kernel as k; k.run_events(%r)" % tov], cwd=kd, env=env,
                            capture_output=True, text=True)
        if rc.returncode != 0:
            return False, dict(shard=i, stderr=rc.stderr[-1500:])
    t_ev = time.time() - t
    env1 = dict(os.environ, GRIDV2_INPUT=lake, GRIDV2_OUT=s1o, GRIDV2_SHARD="0/1")
    code = "import runner_kaggle as r; r.run(test_overrides=%r)" % tov
    rc = subprocess.run([sys.executable, "-c", code], cwd=kd, env=env1, capture_output=True, text=True)
    if rc.returncode != 0:
        return False, dict(s1_stderr=rc.stderr[-1500:])
    vals = [json.load(open(os.path.join(evd, "validate_s%d.json" % i))) for i in range(5)]
    mans = [json.load(open(os.path.join(evd, "manifest_s%d.json" % i))) for i in range(5)]
    ev, _ = SM.load_events(evd)
    e1b = RS.e1b_vs_run2(ev, os.path.join(root, "s1run"))
    kw = pd.concat([pd.read_parquet(f) for f in glob.glob(os.path.join(evd, "kline_win_s*.parquet"))])
    w0 = RS.w0_events(evd, None, allow_test=True)
    kb = os.path.join(root, "kernels")
    exp, shas = __import__("events_kernel").build(kb, S1DIR)
    built = sorted(os.listdir(kb))
    chk = dict(all_pass=all(v["all_pass"] for v in vals), prereg_false=all(m["prereg_constants"] is False for m in mans),
               e1a=all(v["E1a"]["ok"] for v in vals), e1b=e1b["ok"], n_units=len(ev) > 100, both_sides=set(ev.side) == {1, -1},
               kline_rows=len(kw) > 0, w0_allow_test=w0["ok"], build=len([b_ for b_ in built if b_.startswith("kernel_e")]) == 5,
               cols=all(c in ev.columns for c in ("o_net", "p_net", "o_ok", "p_ok", "L", "X", "s_hat", "slip", "dl_end_ms", "tier")))
    det = dict(checks=chk, n_units=int(len(ev)), n_clusters=int(ev.groupby(["sym", "date"]).ngroups), e1b=e1b,
               seconds_events_5shards=round(t_ev, 1), units_by_sym=ev.groupby("sym").size().to_dict(), wrappers=shas)
    shutil.rmtree(lake, ignore_errors=True)
    return all(chk.values()), det


TESTS = [("T1_containment", t1_containment), ("T2_analytic_rw", t2_analytic), ("T3_edges", t3_edges),
         ("T4_engine_vs_ref", t4_engine_vs_ref), ("T5_no_lookahead", t5_no_lookahead), ("T6_sampling", t6_sampling),
         ("T7_fetch_reduce", t7_fetch_reduce), ("T8_rules", t8_rules), ("T9_size_null", t9_size), ("T10_e2e", t10_e2e),
         ("T11_events_kernel_fake_lake", t11_events_kernel)]


def main():
    os.makedirs(OUT, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    want = sys.argv[1:]
    for name, fn in TESTS:
        if want and name not in want:
            continue
        t = time.time()
        try:
            ok, det = fn()
        except Exception as e:  # noqa
            import traceback
            ok, det = False, dict(error=repr(e), tb=traceback.format_exc())
        RES[name] = dict(ok=bool(ok), seconds=round(time.time() - t, 1), detail=det)
        log.info("%s %s %.1fs %s", name, "PASS" if ok else "FAIL", time.time() - t, json.dumps(det, default=str)[:600])
    npass = sum(r["ok"] for r in RES.values())
    log.info("TONG %d/%d PASS", npass, len(RES))
    fn = os.path.join(OUT, "test_results.json" if not want else "test_results_partial.json")
    json.dump(dict(n_pass=npass, n_total=len(RES), results=RES), open(fn, "w"), indent=1, default=str)
    return npass == len(RES)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
