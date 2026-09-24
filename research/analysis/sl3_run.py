"""SL3 runner — day 5 chan cua docs/PREREG_SL_7_TO_3.md len Kaggle CPU kernel.

Nen = PRODUCTION FLATGRID KEEPLEG0 (= prof_x1_gs_t170 + DUNG 2 dong
DCA_GRID_WEIGHTS=1,1,1,1 / DCA_GRID_SCALE=6.0).

  sl3-base     khong override            (moc + CONG PARITY: md5 99e42b75, 1085 leg, eq 103083)
  sl3-v1-arm03 SIM_RATE_PROFIT_STOP_MARKET=0.03   (V1: arm 7% -> 3%)
  sl3-v2-sl3   SIM_PRE_ARM_SL=-0.03               (V2: SL cung -3% truoc arm)
  sl3-v3-both  ca hai                             (V3)
  sl3-v4-sl7   SIM_PRE_ARM_SL=-0.07               (V4: SL cung -7% truoc arm)

Bundle `sim-x1-2021-bundle` (snapshot: chi co 3 profile) => bien the dien dat bang OVERRIDE tren
prof_x1_gs_t170; kernel luu prof_run.properties lam bang chung. KHONG jar_ds => dung jar mac dinh
cua bundle (= jar da tao ra t170-x1-2021 md5 efb793e2). Cua so DEV 2021-07-01..2025-12-31.
Chi phi Kaggle = 0. KHONG chay Java/sim tren Oracle. KHONG push.

Dung: python3 research/analysis/sl3_run.py <base|v1|v2|v3|v4|all|fetch>
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
SHA = "ce353df+prereg-sl-7-to-3"

# KEEPLEG0 = x1_gs_t170 + DUNG 2 dong (docs/DECISION_SHADOW_FLATGRID_KEEPLEG0.md)
KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
ARM = {"SIM_RATE_PROFIT_STOP_MARKET": 0.03}       # V1
SL3 = {"SIM_PRE_ARM_SL": -0.03}                   # V2
SL7 = {"SIM_PRE_ARM_SL": -0.07}                   # V4


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


JOBS = {
    "base": dict(tag="sl3-base", profile="x1_gs_t170", overrides=_ov(KEEP)),
    "v1": dict(tag="sl3-v1-arm03", profile="x1_gs_t170", overrides=_ov(KEEP, ARM)),
    "v2": dict(tag="sl3-v2-sl3", profile="x1_gs_t170", overrides=_ov(KEEP, SL3)),
    "v3": dict(tag="sl3-v3-both", profile="x1_gs_t170", overrides=_ov(KEEP, ARM, SL3)),
    "v4": dict(tag="sl3-v4-sl7", profile="x1_gs_t170", overrides=_ov(KEEP, SL7)),
}
ALL = ["base", "v1", "v2", "v3", "v4"]


def submit_one(name):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE,
                    sim_end_date=END, code_sha=SHA)
    print("SUBMIT %-5s -> %s overrides=%s" % (name, ref, json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    r = out["result"] or {}
    print("FETCH  %-5s eq=%s n=%s secs=%s mapper=%s" % (
        name, r.get("equity_final"), r.get("n_trades"), r.get("secs"), r.get("symbol_mapper")),
        flush=True)
    return out


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    if a == ["fetch"]:
        for n in ALL:
            fetch_one(n)
    else:
        names = ALL if a == ["all"] else a
        refs = [submit_one(n) for n in names]
        print("STATUS", ks.wait(refs), flush=True)
        for n in names:
            fetch_one(n)
