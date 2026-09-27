"""FAMILY2-TP-SL runner (AMENDMENT) — docs/prereg/PREREG_FAMILY2_TP_SL.md (AMENDMENT 2026-09-27).

Ho MOI #1: BO MAY SINH-DUOI (TP nho + SL nho, KHONG DCA) — nay DUNG DUOC vi da them key GATED
`SIM_TAKE_PROFIT_RATE` (mac dinh 0 = OFF = byte-identical) vao nhanh SIM.

Jar MOI: dataset `sim-jar-tpsl` (jar build tu HEAD module + key TP gated, sanitized secrets).
Bundle `sim-x1-2021-bundle`, cua so DEV 2021-07-01..2025-12-31, ticker_min 1826, 0 sim Oracle.

VIEC 2 (CUA CONG): parity OFF (key KHONG khai) phai khop CA HAI md5:
  tp-par-kg0  -> 99e42b75cf1a2142f9cd14dc72e371ba / n1085 / eq103083   (KEEPLEG0)
  tp-par-t170 -> efb793e2468ca3a7318da0f0ad23d4fc / n1089 / eq111070   (T170)
Lech => DUNG, khong chay arm.

VIEC 4 (ARMS): nen `cd-sel15` (= KEEPLEG0 + SIM_ENTRY_SAMPLE_MIN=15). N0 DUNG LAI (da co).
  N1 tp-n1: TP=0.02 + PRE_ARM_SL=-0.01 + WFO_DISABLE_DCA=1
  N2 tp-n2: TP=0.01 + PRE_ARM_SL=-0.01 + WFO_DISABLE_DCA=1
  N3 tp-n3: TP=0.03 + PRE_ARM_SL=-0.015 + WFO_DISABLE_DCA=1
  N4 tp-n4: = N1 + SIM_LOSER_TIME_STOP_HOURS=24

Usage: python3 research/analysis/family2_tp_run.py par|n1|n2|n3|n4|arms [--no-wait] [--fetch]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-tpsl"
END = "20251231"
TICKER_MIN = 1826
SHA = "tp-sl-gated+prereg-family2-amend"

BASE = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0, "SIM_ENTRY_SAMPLE_MIN": 15}
KEEP0 = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
NODCA = {"WFO_DISABLE_DCA": "1"}


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


JOBS = {
    # --- parity (key TP KHONG khai) ---
    "par-kg0":  dict(tag="tp-par-kg0",  profile="x1_gs_t170", overrides=_ov(KEEP0)),
    "par-t170": dict(tag="tp-par-t170", profile="x1_gs_t170", overrides={}),
    # --- arms (nen cd-sel15 + DCA OFF qua env) ---
    "n1": dict(tag="tp-n1", profile="x1_gs_t170", extra_env=NODCA,
               overrides=_ov(BASE, {"SIM_TAKE_PROFIT_RATE": 0.02, "SIM_PRE_ARM_SL": -0.01})),
    "n2": dict(tag="tp-n2", profile="x1_gs_t170", extra_env=NODCA,
               overrides=_ov(BASE, {"SIM_TAKE_PROFIT_RATE": 0.01, "SIM_PRE_ARM_SL": -0.01})),
    "n3": dict(tag="tp-n3", profile="x1_gs_t170", extra_env=NODCA,
               overrides=_ov(BASE, {"SIM_TAKE_PROFIT_RATE": 0.03, "SIM_PRE_ARM_SL": -0.015})),
    "n4": dict(tag="tp-n4", profile="x1_gs_t170", extra_env=NODCA,
               overrides=_ov(BASE, {"SIM_TAKE_PROFIT_RATE": 0.02, "SIM_PRE_ARM_SL": -0.01,
                                    "SIM_LOSER_TIME_STOP_HOURS": 24})),
}
ALIAS = {"par": ["par-kg0", "par-t170"], "arms": ["n1", "n2", "n3", "n4"]}


def submit_one(name, push=True):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA,
                    extra_env=j.get("extra_env"), push=push)
    print("SUBMIT %-9s -> %s overrides=%s env=%s" % (name, ref, json.dumps(j["overrides"]),
                                                     json.dumps(j.get("extra_env") or {})), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    print("FETCH  %-9s %s" % (name, json.dumps(out["result"])), flush=True)
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    do_wait = "--no-wait" not in sys.argv
    only_fetch = "--fetch" in sys.argv
    names = []
    for x in (a or ["arms"]):
        names.extend(ALIAS.get(x, [x]))
    if not only_fetch:
        print("free_slots=%d" % ks.free_slots(), flush=True)
        refs = [submit_one(n) for n in names]
        if do_wait:
            print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        fetch_one(n)
