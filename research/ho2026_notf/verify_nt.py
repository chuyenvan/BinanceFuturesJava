#!/usr/bin/env python3
"""Kiem DOC LAP 24 kernel A1 (khong dung lai q.check): metadata Kaggle, source CFG, result.json, log, printDone.
Xuat verify_nt.json"""
import ast, glob, hashlib, json, os, re, sys
import pandas as pd

W = "/home/ubuntu/claude_master/ho_tradfi_wk"
OUT = "/home/ubuntu/kaggle_sim/out"
KD = "/tmp/nt_kmd"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
X = set(open(W + "/X_notf_v2.txt").read().split())
ARTS = json.load(open(W + "/arts_nt.json"))
SHA_EXP = "877d9ffade1daac377cb6aea1f070f57de23e5b44b03cd39e024f13ae8baf883"
SHA_TSX = "cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe"
PRED_BASE = "22f69456381d9d1abd1592382c3b0319"
FLAGS1 = "20260205-20260214,20260216-20260217,20260224-20260225,20260606-20260607,20260610-20260611"
BASE_OV = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90, "SIM_GATE_ROLLING_PCT": 0.999950829,
           "TS_GIVEBACK_RATIO": 1.0, "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03,
           "SELECTOR_RANK_TOPK": 24, "GATE_QUOTA_SKIP_WHEN_FULL": "true"}


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def expected(tag):
    if tag.startswith("nt-x14"):
        cfg, sha = "x14", SHA_TSX
    elif tag.startswith("a0p2-k24-s"):
        cfg, sha = "k24sA0", SHA_EXP
    elif tag.startswith("a0p2-k24-b"):
        cfg, sha = "k24bA0", SHA_EXP
    elif tag.startswith("nt-k24-s"):
        cfg, sha = "k24s", SHA_EXP
    elif tag.startswith("nt-k24-b"):
        cfg, sha = "k24b", SHA_EXP
    elif tag.startswith("a0p-x14"):
        cfg, sha = "x14A0", SHA_TSX
    else:
        raise SystemExit("tag? " + tag)
    m = re.search(r"s(42|7|13|21|99|123|777|2024)$", tag)
    seed = int(m.group(1))
    ov = dict(BASE_OV)
    if cfg in ("k24s", "k24sA0"):
        ov["SIM_CRASH_ENTRY_PENALTY"] = "0.01675"
    if cfg == "x14":
        ov["SIM_LOSER_TS_EXT_HOURS"] = 336
        ov["SIM_LOSER_TS_EXT_DAYS"] = FLAGS1
    if cfg == "x14A0":
        ov["SIM_LOSER_TS_EXT_HOURS"] = 336
        ov["SIM_LOSER_TS_EXT_DAYS"] = "20260205-20260214,20260216-20260217,20260224-20260225,20260611-20260611"
    return cfg, sha, seed, ov


def getsrc(tag):
    fs = [f for f in glob.glob(KD + "/d_" + tag + "/*.py")]
    assert len(fs) == 1, fs
    s = open(fs[0]).read()
    m = re.search(r"CFG = json\.loads\(('.*?')\)", s, re.S)
    cfg = json.loads(ast.literal_eval(m.group(1)))
    return s, cfg


def main():
    tags = []
    for s in SEEDS:
        tags += ["nt-k24-s-s%d" % s, "nt-k24-b-s%d" % s, "nt-x14-s%d" % s]
    tags += ["a0p2-k24-s-s42", "a0p2-k24-b-s42", "a0p-x14-s42"]
    res = {}
    for t in tags:
        cfg, sha, seed, ov = expected(t)
        s, kc = getsrc(t)
        md = json.load(open(KD + "/d_" + t + "/kernel-metadata.json"))
        ds = set(md["dataset_sources"]); ks = set(md["kernel_sources"])
        r = json.load(open(OUT + "/" + t + "/result.json"))
        pdp = OUT + "/" + t + "/storage/printDone.csv"
        md5 = md5f(pdp)
        logs = ""
        for fn in ("logs/full.log", "logs/sim.out"):
            if os.path.exists(OUT + "/" + t + "/" + fn):
                logs += open(OUT + "/" + t + "/" + fn, errors="ignore").read()
        for p in glob.glob(OUT + "/" + t + "/*.log"):
            try:
                logs += "".join(x.get("data", "") for x in json.load(open(p)))
            except Exception:
                logs += open(p, errors="ignore").read()
        d = pd.read_csv(pdp, index_col=False, dtype=str)
        d["S"] = d.sym.str.strip() + "USDT"
        xm = d.S.isin(X)
        x26 = d.loc[xm & ((d.start >= "20260101 00:00") | (d.end >= "20260101 00:00"))]
        pens = [float(x) for x in re.findall(r"\[CRASH-PENALTY\] SUMMARY penalty=([0-9.eE+-]+)", logs)]
        tsx = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+) deferTicks=(\d+) deferClusters=(\d+) cutAfterDefer=(\d+)", logs)
        want_jar_ds = "sim-jar-tsx" if cfg.startswith("x14") else "ho2026-notf-sim-jar"
        a0 = cfg.endswith("A0")
        mk_ok = ("ho4p1-chain-y26" if a0 else "nt-chain-y26")
        tk_ok = ("ho4p1-tk26" if a0 else "nt-tk26")
        chk = {
            "cfg_tag": kc.get("tag") == t,
            "cfg_jar_ds": kc.get("jar_ds") == want_jar_ds,
            "cfg_market": kc.get("market_ds") == mk_ok,
            "cfg_tk": kc.get("tk_ho4p1", {}).get("src") == tk_ok,
            "cfg_tk_md5_n": len(kc.get("tk_ho4p1", {}).get("md5", {})) == 273,
            "cfg_tk_md5_eq_arts": kc.get("tk_ho4p1", {}).get("md5") == (kc.get("tk_ho4p1", {}).get("md5") if a0 else ARTS["tk_md5"]),
            "cfg_pred": kc.get("want_pred_md5") == (kc.get("want_pred_md5") if a0 else ARTS["preds"][str(seed)]),
            "cfg_pred_base": kc.get("want_pred_base") == PRED_BASE,
            "cfg_pred_ds": kc.get("pred_ds") == "pred_s%d" % seed,
            "cfg_ov": kc.get("overrides") == ov,
            "cfg_end": kc.get("sim_end_date") == "20261001",
            "cfg_min_days": kc.get("ticker_min_days") == 2099,
            "cfg_unseal": kc.get("extra_env") == {"HOLDOUT_UNSEAL": "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026"},
            "meta_jar": any(x.endswith("/" + want_jar_ds) for x in ds),
            "meta_no_bad_jar": not ({"ho4p1-jar-exp", "sim-jar-nsel"} & {x.split("/")[-1] for x in ds}),
            "meta_ks": ks == ({"chuyendinh/ho4p1-tk26", "chuyendinh/ho4p1-chain-y26"} if a0 else {"chuyendinh/nt-tk26", "chuyendinh/nt-chain-y26"}),
            "r_ok": r.get("ok") is True,
            "r_jar": r.get("jar_sha256") == sha,
            "r_ov": r.get("overrides") == ov,
            "r_mapper": isinstance(r.get("symbol_mapper"), int) and r["symbol_mapper"] >= 800,
            "r_pred": r.get("pred_md5_used") == (r.get("pred_md5_used") if a0 else ARTS["preds"][str(seed)]),
            "r_n": isinstance(r.get("n_trades"), int) and r["n_trades"] > 0,
            "log_tk": "TICKER_HO4P1 ok=273 bad=0 miss=0 extra=0 other=0" in logs,
            "log_fund": "FUND_HO4_OK" in logs and "FUND_HO4_SELFCHECK keys_equal=True" in logs,
            "log_ov": ("overrides=" + json.dumps(ov)) in logs,
            "log_unseal": "HOLDOUT_UNSEAL DUNG" in logs,
            "log_pen": (all(abs(p - 0.01675) < 1e-12 for p in pens) and len(pens) > 0) if cfg in ("k24s", "k24sA0") else all(p == 0.0 for p in pens),
            "log_tsx": (tsx[-1][0] == "336" and tsx[-1][1] == ("15" if cfg == "x14A0" else "18")) if cfg.startswith("x14") else (tsx == [] or tsx[-1][0] == "0"),
            "v3_no_x_2026": len(x26) == 0,
            "x_legs_all": int(xm.sum()),
            "x_legs_dates": sorted(set(d.loc[xm, "start"].str[:6]))[:6],
            "md5_printDone": md5,
            "n_trades": r.get("n_trades"),
            "pass": None,
        }
        _skip = ("md5_printDone", "n_trades", "x_legs_all", "x_legs_dates", "pass")
        if cfg.endswith("A0"):
            _skip = _skip + ("v3_no_x_2026",)
        chk["pass"] = all(v for k, v in chk.items() if k not in _skip)
        res[t] = dict(cfg=cfg, seed=seed, chk=chk)
        print(t, chk["pass"], [k for k, v in chk.items() if v is False and k not in _skip], chk["md5_printDone"][:8], chk["x_legs_dates"], flush=True)
    json.dump(res, open(W + "/verify_nt.json", "w"), indent=1)
    print("ALL", all(v["chk"]["pass"] for v in res.values()))


if __name__ == "__main__":
    main()
