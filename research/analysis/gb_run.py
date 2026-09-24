"""GB runner — day 3 chan moi cua docs/prereg/PREREG_GIVEBACK_RATIO.md len Kaggle CPU kernel.

Nen = PRODUCTION FLATGRID KEEPLEG0 (= prof_x1_gs_t170 + DUNG 2 dong
DCA_GRID_WEIGHTS=1,1,1,1 / DCA_GRID_SCALE=6.0).

  gb-r1  TS_GIVEBACK_RATIO=1   (moc = 0.5 = `kg0-g170`, DA CO, khong chay lai)
  gb-r2  TS_GIVEBACK_RATIO=2
  gb-r5  TS_GIVEBACK_RATIO=5

CHI doi DUY NHAT TS_GIVEBACK_RATIO so voi moc. Bundle `sim-x1-2021-bundle`, KHONG jar_ds
(jar bundle = 2c2f8aef = CUNG jar voi moc). Cua so DEV 2021-07-01..2025-12-31.
Chi phi Kaggle = 0. KHONG chay Java/sim tren Oracle. KHONG push.

Dung: python3 research/analysis/gb_run.py <r1|r2|r5|all|fetch>
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
SHA = "bca8575+gbratio"

# KEEPLEG0 = x1_gs_t170 + DUNG 2 dong (docs/decisions/DECISION_SHADOW_FLATGRID_KEEPLEG0.md)
KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}


def _ov(ratio):
    o = dict(KEEP)
    o["TS_GIVEBACK_RATIO"] = ratio
    return o


JOBS = {
    "r1": dict(tag="gb-r1", profile="x1_gs_t170", overrides=_ov(1)),
    "r2": dict(tag="gb-r2", profile="x1_gs_t170", overrides=_ov(2)),
    "r5": dict(tag="gb-r5", profile="x1_gs_t170", overrides=_ov(5)),
}
ALL = ["r1", "r2", "r5"]


def submit_one(name):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE,
                    sim_end_date=END, code_sha=SHA)
    print("SUBMIT %-3s -> %s overrides=%s" % (name, ref, json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    r = out["result"] or {}
    print("FETCH  %-3s eq=%s n=%s secs=%s mapper=%s jar=%s" % (
        name, r.get("equity_final"), r.get("n_trades"), r.get("secs"),
        r.get("symbol_mapper"), (r.get("jar_sha256") or "")[:8]), flush=True)
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
