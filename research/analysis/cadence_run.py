"""CADENCE-MATCH runner — docs/prereg/PREREG_GATE_RECAL.md AMENDMENT §7.

Tra loi: "SIM dang 15' hay 1'?" va "selector 15' + BIG_DOWN/DCA 1' khac baseline 1' bao nhieu?"

Nen = PRODUCTION KEEPLEG0 (= prof_x1_gs_t170 + DUNG 2 dong DCA_GRID_WEIGHTS=1,1,1,1 /
DCA_GRID_SCALE=6.0), cua so DEV 2021-07-01..2025-12-31, bundle sim-x1-2021-bundle.

Jar: dataset CHI chua sim.jar `chuyendinh/sim-jar-cadence` (build tu commit code 3b6c6e9 —
FIX pham vi SIM_ENTRY_SAMPLE_MIN = CHI selector-entry).

  parity (TAT = y nguyen):
    cd-par-kg0  : KEEPLEG0                        -> md5 99e42b75cf1a2142f9cd14dc72e371ba / n1085 / eq103083
    cd-par-t170 : x1_gs_t170 (khong override)      -> md5 efb793e2468ca3a7318da0f0ad23d4fc / n1089 / eq111070
  arms (selector 15' + BIG_DOWN/DCA 1'):
    cd-sel15      : KEEPLEG0 + SIM_ENTRY_SAMPLE_MIN=15
    cd-sel15-q998 : KEEPLEG0 + SIM_ENTRY_SAMPLE_MIN=15 + SIM_GATE_P15_Q=0.998
    cd-sel15-q999 : KEEPLEG0 + SIM_ENTRY_SAMPLE_MIN=15 + SIM_GATE_P15_Q=0.999

Chi phi Kaggle = 0. KHONG chay Java/sim tren Oracle. KHONG push git.
Dung: python3 research/analysis/cadence_run.py <name|all|arms|par> [--no-wait]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
TICKER_MIN = 1826
SHA = "3b6c6e9+prereg-amend-cadence"
JAR_DS = "sim-jar-cadence"

KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


def sel15(*extra):
    return _ov(KEEP, {"SIM_ENTRY_SAMPLE_MIN": 15}, *extra)


JOBS = {
    "par-kg0":    dict(tag="cd-par-kg0",    profile="x1_gs_t170", overrides=_ov(KEEP)),
    "par-t170":   dict(tag="cd-par-t170",   profile="x1_gs_t170", overrides={}),
    "sel15":      dict(tag="cd-sel15",      profile="x1_gs_t170", overrides=sel15()),
    "sel15-q998": dict(tag="cd-sel15-q998", profile="x1_gs_t170", overrides=sel15({"SIM_GATE_P15_Q": 0.998})),
    "sel15-q999": dict(tag="cd-sel15-q999", profile="x1_gs_t170", overrides=sel15({"SIM_GATE_P15_Q": 0.999})),
}
ALIAS = {"par": ["par-kg0", "par-t170"],
         "arms": ["sel15", "sel15-q998", "sel15-q999"],
         "all": ["par-kg0", "par-t170", "sel15", "sel15-q998", "sel15-q999"]}


def submit_one(name, push=True):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA, push=push)
    print("SUBMIT %-11s -> %s overrides=%s" % (name, ref, json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    print("FETCH  %-11s %s" % (name, json.dumps(out["result"])), flush=True)
    print("       printDone=%s" % out["print_done"], flush=True)
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    do_wait = "--no-wait" not in sys.argv
    names = []
    for x in (a or ["all"]):
        names.extend(ALIAS.get(x, [x]))
    print("free_slots=%d" % ks.free_slots(), flush=True)
    refs = [submit_one(n) for n in names]
    if do_wait:
        print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        fetch_one(n)
