#!/usr/bin/env python3
"""rt_score_n.py - cham Lane N vs Lane L theo PREREG_RETRAIN_PILOT muc 7 + muc 16(d) (c796c7b3, ADD1-3). HOLDOUT_UNSEAL_2026_1121 e9095a02 (U2).
Dinh nghia = SCORE_DEFS_L5 (dung ham rows/updates/metr cua l5/score_l5.py, import chi doc). Q3 = 2026-07-01..2026-09-30 (+07).
ROI_Q3(s) = SigmaPnL_Q3 / E_start_Q3 (D5); d(s) = 100*(ROI_N - ROI_L); LB = mean(d) - 2.3646*sd(d,ddof=1)/sqrt(8); H-NI PASS <=> LB >= -1.0.
H-E0: mean SigmaPnL_Q3,N > 0 VA #seed > 0 >= 6. H-DD: mean maxDD_Q3,N < -0.2272 -> CANH BAO. Mo ta: E0b-kieu bootstrap tuan cua d (CI80,
rng 20261121, 10 000), so lenh theo thang (start) Q3 N vs L, n_pass gate tong (log sim chi in TONG; N-L = chenh tu Q3 vi 2 lane trung toi 06-30).
Usage: rt_score_n.py selftest            (N := L, phai ra d = 0 va ROI_Q3 L = RESULT_HO5 4,51 %)
       rt_score_n.py score --allow-n     (CHI chay khi MASTER cho phep sau audit)"""
import datetime as dt, gzip, json, logging, math, os, re, sys
import numpy as np
sys.path.insert(0, "/home/ubuntu/claude_master/w3/ho5/l5")
import score_l5 as S  # noqa: E402  (chi dung rows / updates / metr / F / day / SEEDS)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
L = logging.getLogger("rtscore")
L.info("HOLDOUT_UNSEAL_REF HOLDOUT_UNSEAL_2026_1121 e9095a02 (U2 RETRAIN)")
LDIR = os.environ.get("RT_LDIR", "/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-%s")
NDIR = os.environ.get("RT_NDIR", "/home/ubuntu/claude_master/w3/retrain/out/nsim/rt-n-l26-%s")
SPLIT = [("07", "2026-07-01", "2026-07-31"), ("08", "2026-08-01", "2026-08-31"), ("09", "2026-09-01", "2026-09-30"),
         ("0701-0709", "2026-07-01", "2026-07-09"), ("0710-0930", "2026-07-10", "2026-09-30")]
OUT = "/home/ubuntu/claude_master/w3/retrain/out/score"
Q3 = ("2026-07-01", "2026-09-30")
T975_7 = 2.3646
GATE = re.compile(r"\[GATE\] scale=\S+ base=\S+ n_cand=(\d+) n_pass=(\d+)")


def npass(d):
    p = [c for c in (d + "/logs/sim.out.gz", d + "/logs/sim.out") if os.path.exists(c)][0]
    op = gzip.open if p.endswith(".gz") else open
    v = None
    with op(p, "rt", errors="replace") as f:
        for ln in f:
            m = GATE.search(ln)
            if m:
                v = (int(m.group(1)), int(m.group(2)))
    return v


def lane(d, s):
    pdr, up = S.rows(d % s), S.updates(d % s)
    m = S.metr(pdr, up, S.day(Q3[0]), S.day(Q3[1]))
    assert m["d_start"] == "20260701", ("A5-1: dong Update E_start phai la 20260701", d % s, m["d_start"])  # A5-1(ii)
    m["roi_q3_d5"] = m["sum_pnl"] / m["E_start"]
    m["split"] = {}
    for nm, a, b in SPLIT:  # A5-3 + 16(d): MO TA
        lo_, hi_ = S.day(a), S.day(b) + dt.timedelta(days=1)
        m["split"][nm] = {"n_start": sum(1 for x in pdr if lo_ <= S.F(x["start"]) < hi_), "sum_pnl_end": sum(float(x["pnl"]) for x in pdr if lo_ <= S.F(x["end"]) < hi_),
                          "gate_pass_minutes": "khong co (log sim chi in tong)"}
    m["keys_q3"] = sorted({(x["symbol"] if "symbol" in x else x.get("sym"), x["start"]) for x in pdr if S.day(Q3[0]) <= S.F(x["start"]) < S.day(Q3[1]) + dt.timedelta(days=1)})
    lo = S.day(Q3[0]); nw = math.ceil(((S.day(Q3[1]) - lo).days + 1) / 7); w = np.zeros(nw)
    mon = {"2026-07": 0, "2026-08": 0, "2026-09": 0}
    for x in pdr:
        t = S.F(x["end"])
        if lo <= t < S.day(Q3[1]) + dt.timedelta(days=1):
            w[(t - lo).days // 7] += float(x["pnl"])
        st = S.F(x["start"])
        k = st.strftime("%Y-%m")
        if k in mon:
            mon[k] += 1
    m["weekly_pnl"] = w.tolist(); m["orders_by_month"] = mon; m["gate_ncand_npass_total"] = npass(d % s)
    return m


def pre_checks(ndir, selftest):
    """A5-1(i): check_n.json PASS 8/8 (Lane N) va check_l5.json PASS 8/8 (Lane L)."""
    for s in S.SEEDS:
        assert json.load(open(LDIR % s + "/check_l5.json"))["PASS"] is True, ("check_l5 FAIL", s)
        if not selftest:
            assert json.load(open(ndir % s + "/check_n.json"))["PASS"] is True, ("check_n FAIL", s)


def run(ndir, tag, selftest=False):
    pre_checks(ndir, selftest)
    res = {"tag": tag, "ndir": ndir, "ldir": LDIR, "seeds": {}}
    for s in S.SEEDS:
        res["seeds"][s] = {"N": lane(ndir, s), "L": lane(LDIR, s)}
        kn, kl = set(map(tuple, res["seeds"][s]["N"].pop("keys_q3"))), set(map(tuple, res["seeds"][s]["L"].pop("keys_q3")))
        res["seeds"][s]["q3_common_sym_start"] = {"N": len(kn), "L": len(kl), "common": len(kn & kl)}
    N = [res["seeds"][s]["N"] for s in S.SEEDS]; Lx = [res["seeds"][s]["L"] for s in S.SEEDS]
    sp = np.array([x["sum_pnl"] for x in N])
    res["H_E0"] = {"mean_sum_pnl_q3_N": float(sp.mean()), "n_pos": int((sp > 0).sum()), "PASS": bool(sp.mean() > 0 and (sp > 0).sum() >= 6)}
    d = 100.0 * np.array([a["roi_q3_d5"] - b["roi_q3_d5"] for a, b in zip(N, Lx)])
    sd = float(d.std(ddof=1)); lb = float(d.mean() - T975_7 * sd / math.sqrt(len(d))) if sd > 0 else float(d.mean())
    res["H_NI"] = {"d_pp": d.tolist(), "mean_d_pp": float(d.mean()), "sd_d_pp": sd, "LB_pp": lb, "PASS": bool(lb >= -1.0)}
    dm = 100.0 * np.array([a["roi"] - b["roi"] for a, b in zip(N, Lx)]); sdm = float(dm.std(ddof=1))
    res["desc_H_NI_MTM"] = {"note": "MO TA (khong luat): ROI MTM = E_end/E_start - 1 (cot ROI cua RESULT_HO5, 4,51 %); luat dung D5",
                            "d_pp": dm.tolist(), "mean": float(dm.mean()), "LB": float(dm.mean() - T975_7 * sdm / math.sqrt(len(dm))) if sdm > 0 else float(dm.mean())}
    mdd = float(np.mean([x["maxdd"] for x in N]))
    res["H_DD"] = {"mean_maxdd_q3_N": mdd, "WARN": bool(mdd < -0.2272)}
    wd = np.mean([np.array(a["weekly_pnl"]) / a["E_start"] - np.array(b["weekly_pnl"]) / b["E_start"] for a, b in zip(N, Lx)], axis=0) * 100
    rng = np.random.default_rng(20261121); idx = rng.integers(0, len(wd), size=(10000, len(wd))); bs = wd[idx].sum(axis=1)
    res["desc_d_weekly_boot_ci80_pp"] = [float(np.percentile(bs, 10)), float(np.percentile(bs, 90))]
    res["DECISION"] = "PASS -> T2" if res["H_E0"]["PASS"] and res["H_NI"]["PASS"] else "FAIL -> PILOT bi chan, DUNG"
    os.makedirs(OUT, exist_ok=True)
    p = OUT + "/score_n_%s.json" % tag
    json.dump(res, open(p, "w"), indent=1, default=str)
    return res, p


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        r, p = run(LDIR, "selftest_LvsL", selftest=True)
        roi = [r["seeds"][s]["L"]["roi_q3_d5"] for s in S.SEEDS]
        ok = all(abs(x) == 0 for x in r["H_NI"]["d_pp"])
        L.info("SELFTEST d==0 tat ca seed: %s | ROI_Q3 L (D5) theo seed: %s | %s", ok, [round(100 * x, 4) for x in roi], p)
    elif sys.argv[1] == "score" and "--allow-n" in sys.argv:
        r, p = run(NDIR, "laneN")
        L.info("H_E0 %s H_NI %s H_DD %s -> %s", r["H_E0"], {k: v for k, v in r["H_NI"].items() if k != "d_pp"}, r["H_DD"], r["DECISION"])
    else:
        raise SystemExit("score can --allow-n (chi sau khi MASTER cho phep)")
