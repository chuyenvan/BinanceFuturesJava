"""GATE-ROOTCAUSE runner — docs/prereg/PREREG_GATE_ROOTCAUSE.md VIEC 3.

Nen = PRODUCTION KEEPLEG0 (= prof_x1_gs_t170 + DCA_GRID_WEIGHTS=1,1,1,1 / DCA_GRID_SCALE=6.0),
cua so DEV 2021-07-01..2025-12-31, nhip selector 15' (SIM_ENTRY_SAMPLE_MIN=15) = khop thiet ke live.

Jar: `sim-jar-cadence` (sha 43888ebd...) — code 3b6c6e9, sim path da parity-verified
(0ef84514/fec652e va 43888ebd/3b6c6e9 deu cho md5 production). KHONG sua code => dung key CO SAN.

  parity  : rc-par-kg0  -> md5 99e42b75cf1a2142f9cd14dc72e371ba / n1085 / eq103083
            rc-par-t170 -> md5 efb793e2468ca3a7318da0f0ad23d4fc / n1089 / eq111070
  pa A    : rc-a-qNNN = KEEPLEG0 + SIM_ENTRY_SAMPLE_MIN=15 + SIM_GATE_P15_Q=Q + SIM_GATE_DYN_SCALE=0.001
            => thr = max(base, quantile_cuon) = "thay dyn bang phan vi cuon" (dyn -> ~1e-6 < base).

Chi phi Kaggle = 0. Khong chay Java/sim tren Oracle. Khong push git.
Dung: python3 research/analysis/gate_rootcause_run.py <name|all|par|a> [--no-wait]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
TICKER_MIN = 1826
SHA = "3b6c6e9+prereg-gate-rootcause"
JAR_DS = "sim-jar-cadence"

KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
SEL15 = {"SIM_ENTRY_SAMPLE_MIN": 15}
DYN_OFF = {"SIM_GATE_DYN_SCALE": 0.001}


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


def arm(Q):
    return _ov(KEEP, SEL15, DYN_OFF, {"SIM_GATE_P15_Q": Q})


JOBS = {
    "par-kg0":  dict(tag="rc-par-kg0",  profile="x1_gs_t170", overrides=_ov(KEEP)),
    "par-t170": dict(tag="rc-par-t170", profile="x1_gs_t170", overrides={}),
    "a-q995":   dict(tag="rc-a-q995",   profile="x1_gs_t170", overrides=arm(0.995)),
    "a-q998":   dict(tag="rc-a-q998",   profile="x1_gs_t170", overrides=arm(0.998)),
    "a-q999":   dict(tag="rc-a-q999",   profile="x1_gs_t170", overrides=arm(0.999)),
}
ALIAS = {"par": ["par-kg0", "par-t170"], "a": ["a-q995", "a-q998", "a-q999"],
         "all": ["par-kg0", "par-t170", "a-q995", "a-q998", "a-q999"]}


def submit_one(name, push=True):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA, push=push)
    print("SUBMIT %-9s -> %s overrides=%s" % (name, ref, json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    print("FETCH  %-9s %s" % (name, json.dumps(out["result"])), flush=True)
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
