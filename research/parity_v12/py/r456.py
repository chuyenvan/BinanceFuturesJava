#!/usr/bin/env python3
"""PARITY_V12_DRY §6 — tai kiem harness TRUOC khi cham (R4, R5, R6). Ghi ~/claude_master/parity_v12w/r456.json (gop).
  r4 : ban do tang A1 — (a) code jar dry (git grep UniverseA1Filter tai commit jar) phai phu DU 7 tang §2.1;
       (b) log 1 ngay live co dau vet tung tang; (c) sim A1 (HO2026_NOTF) loai X o tang DU LIEU (exporter in_uni + chain id)
       => moi tang live deu thay du lieu da loai X => khong tang nao lech. Thieu tang => FAIL (DUNG).
  r6 : bo phan loai live (a1cls = port UniverseA1Classifier) vs tap X sim (X_notf_v2, 230) tren CUNG exchangeInfo 20261027;
       va tren anh chup dry moi nhat: chenh lech phai giai thich duoc bang PIT (onboard sau 10-27 / khong con trong file).
  r5 : OFF-BT-A1 vs OFF-NEW2-A1 tren Vision 2026-10-30 (ngay sap): CTL 100 % (cmp_ctl_gate rows_bit_nonfund & cmp_ctl_fund
       rows_tol_nonfund = 1,0). Chay day_prep/vision/universe/r0/harness/ctl voi PV_R5=1 (cua so = ca ngay, exchangeInfo
       = fixture 20261027 vi dry chua ton tai ngay 10-30 — chi kiem harness, khong cham parity).
argv: r4 | r6 | r5 | all"""
import glob
import gzip
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a1cls  # noqa: E402
W = os.path.expanduser("~/claude_master/parity_v12w")
OUTF = W + "/r456.json"
C3 = os.path.expanduser("~/claude_master/v12/c3live")
JAR_COMMIT = "1f505414"          # code r4n (A1_R4N.md) = jar fb6711ef
FIX27 = os.path.expanduser("~/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz")
XSIM = os.path.expanduser("~/claude_master/ho_tradfi_wk/X_notf_v2.txt")
LAYERS = {   # §2.1 tang -> file nguon phai goi UniverseA1Filter
    "MD/breadth": "tradecore/MarketBigChangeDetector.java",
    "feature/basket": "ai_ml/features/export/entry/LiveFeaturePipeline.java",
    "ALT_EW": "tradecore/selector/AltEwIndex.java",
    "TsMktExt": "tradecore/selector/TsMktExt.java",
    "S1/ung vien/gate": "trading/DetectEntrySignal2TradeNormal.java",
    "R7 thuc thi": "c3live/runtime/C3LiveRuntime.java",
    "offline replay (harness)": "ai_ml/features/export/gate/ExportGateDataset.java"}
LOG_MARK = {"filter BAT": "[UNIVERSE-A1] BAT", "R7+tin hieu": "UNIVERSE_A1=1: R7 + bo loc tin hieu",
            "ALT_EW A1": "ALT_EW/market level tren universe A1", "gate a1_bo": "a1_bo=", "TS-EXT": "[TS-EXT]"}


def load():
    return json.load(open(OUTF)) if os.path.exists(OUTF) else {}


def save(k, v):
    R = load()
    R[k] = v
    json.dump(R, open(OUTF, "w"), indent=1, default=str)
    print(json.dumps({k: v}, indent=1, default=str)[:3000])


def r4():
    r = subprocess.run(["git", "-C", C3, "grep", "-l", "UniverseA1Filter", JAR_COMMIT, "--", "src/main/java"],
                       capture_output=True, text=True)
    files = {x.split(":", 1)[1] for x in r.stdout.split()}
    code = {k: any(f.endswith(v) for f in files) for k, v in LAYERS.items()}
    logp = sorted(glob.glob(W + "/d/*/live/log_window.gz"))
    marks = {k: False for k in LOG_MARK}
    for p in logp:          # dong BAT/R7 chi in luc khoi dong => quet moi ngay da chuan hoa
        if "2026-10-30" in p:
            continue
        txt = gzip.open(p, "rt", errors="ignore").read()
        for k, v in LOG_MARK.items():
            marks[k] = marks[k] or (v in txt)
    res = {"jar_commit": JAR_COMMIT, "code_layers": code, "log_marks": marks, "log_file": logp[-1] if logp else None,
           "sim_A1": "HO2026_NOTF loai X o tang du lieu (exporter in_uni + chain DUP_IDS|X_IDS) => moi tang sim khong co X",
           "PASS": bool(all(code.values()) and marks and all(marks.values()))}
    save("R4", res)
    return res["PASS"]


def r6():
    X = {x.strip() for x in open(XSIM) if x.strip()}
    ex27 = a1cls.load(FIX27)
    t27 = int(ex27.get("serverTime", 0)) or 1793083200000
    L27 = a1cls.excluded(FIX27, 1 << 62)
    s27 = {s["symbol"]: s for s in ex27["symbols"]}
    HO_END = 1790787600000          # cua so sim A1 (HO 2026) ket thuc 2026-10-01 00:00 +07
    # giai thich PIT/niem yet (§2.3): (a) khong duoi USDT => ngoai universe (in_uni); (b) onboardDate sau cua so sim
    #   (vd MDTUSDT: ticker dung lai, crypto toi 10-13, TF Medtronic niem yet 10-21 — prereg HO2026_NOTF dong 13)
    expl = lambda s: (not s.endswith("USDT")) or int(s27.get(s, {}).get("onboardDate", 0)) > HO_END
    d27 = sorted((L27 - X) | (X - L27))
    same = {"live_cls_on_fix27": len(L27), "sim_X": len(X), "only_live": sorted(L27 - X), "only_sim": sorted(X - L27),
            "explained_PIT": [s for s in d27 if expl(s)], "unexplained": [s for s in d27 if not expl(s)]}
    snaps = sorted(glob.glob(W + "/exinfo/exinfo_*.json.gz"))
    dry = None
    if snaps:
        ex = a1cls.load(snaps[-1])
        sy = {s["symbol"]: s for s in ex["symbols"]}
        Ld = a1cls.excluded(snaps[-1], 1 << 62)
        new_after = {s for s in Ld - X if int(sy[s].get("onboardDate", 0)) > t27 or expl(s)}
        gone = {s for s in X - Ld if s not in sy}
        unexpl = sorted((Ld - X - new_after) | (X - Ld - gone))
        dry = {"snap": os.path.basename(snaps[-1]), "live_cls": len(Ld), "new_listing_after_1027": sorted(new_after),
               "not_in_file_delisted": sorted(gone), "unexplained": unexpl}
    res = {"same_file_1027": same, "dry_snapshot": dry,
           "PASS": bool(not same["unexplained"] and dry is not None and not dry["unexplained"])}
    save("R6", res)
    return res["PASS"]


def r5():
    env = dict(os.environ, PV_DAY="2026-10-30", PV_R5="1", LIVE_IS_SHADOW_HOST="true")
    R = os.path.dirname(HERE)
    vis = os.path.expanduser("~/claude_master/parity_v11w/vision/klines_1m")
    steps = [["python3", HERE + "/day_prep.py", "prep"],
             ["python3", HERE + "/vision_fetch.py", W + "/univ/ucand_20261030.txt", "2026-10-15", "2026-10-30", vis, "--threads", "16"],
             ["python3", HERE + "/day_prep.py", "universe"],
             ["python3", HERE + "/day_harness.py", "r0"],
             ["python3", HERE + "/day_harness.py", "main"]]
    log = []
    for s in steps:
        p = subprocess.run(s, env=env, capture_output=True, text=True)
        log.append({"step": " ".join(os.path.basename(x) for x in s[1:3]), "rc": p.returncode, "tail": (p.stdout + p.stderr)[-400:]})
        if p.returncode not in (0,):
            break
    run = W + "/d/2026-10-30/runs"
    cg = json.load(open(run + "/cmp_ctl_gate.json")) if os.path.exists(run + "/cmp_ctl_gate.json") else None
    cf = json.load(open(run + "/cmp_ctl_fund.json")) if os.path.exists(run + "/cmp_ctl_fund.json") else None
    ctl = {"rows_bit_nonfund_gate": cg.get("rows_bit_nonfund") if cg else None,
           "rows_tol_nonfund_fund": cf.get("rows_tol_nonfund") if cf else None}
    res = {"steps": log, "CTL": ctl, "exinfo": "fixture 20261027 (dry chua ton tai 10-30)",
           "PASS": bool(cg and cf and cg.get("rows_bit_nonfund") == 1.0 and cf.get("rows_tol_nonfund") == 1.0)}
    save("R5", res)
    return res["PASS"]


if __name__ == "__main__":
    c = sys.argv[1]
    fs = {"r4": [r4], "r6": [r6], "r5": [r5], "all": [r4, r6, r5]}[c]
    ok = [f() for f in fs]
    sys.exit(0 if all(ok) else 1)
