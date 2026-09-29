"""R4-1M parity runner — docs/plan/PLAN_R4_1M_SHADOW.md (CONG PARITY truoc deploy).

Muc dich: bang chung "OFF => y nguyen" cho patch dd8d063 (LIVE_ENTRY_GRID_MIN mac dinh 15,
CONC_CAP_PERCOIN live-port mac dinh false) bang cach chay lai 2 chan parity md5 TREN JAR MOI.

Jar: dataset chuyendinh/sim-jar-r4-1m = target/*.jar build tu dd8d063.
  sha256 = 8d93dad97fb4e2b8cd7b54d4e2448dc413af4c5731826d7d53088f7f5b45160d
Bundle: sim-x1-2021-bundle, cua so DEV 2021-07-01..2025-12-31, ticker_min 1826, 0 sim Oracle.

KY VONG (KHONG doi neu OFF — key moi KHONG khai):
  par-kg0   (KEEPLEG0: DCA_GRID_WEIGHTS=1,1,1,1 + DCA_GRID_SCALE=6.0) -> md5 99e42b75cf1a2142f9cd14dc72e371ba
  par-t170  (x1_gs_t170, khong override)                              -> md5 efb793e2468ca3a7318da0f0ad23d4fc
  Lech => DUNG, khong deploy.

Dung: python3 research/analysis/r4_1m_parity_run.py [--no-wait] [--fetch]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-r4-1m"
END = "20251231"
TICKER_MIN = 1826
SHA = "dd8d063+r4-1m"

KEEP0 = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}

JOBS = {
    "par-kg0":  dict(tag="r4-par-kg0",  profile="x1_gs_t170", overrides=dict(KEEP0)),
    "par-t170": dict(tag="r4-par-t170", profile="x1_gs_t170", overrides={}),
}
ALIAS = {"par": ["par-kg0", "par-t170"], "all": ["par-kg0", "par-t170"]}


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
    only_fetch = "--fetch" in sys.argv
    names = []
    for x in (a or ["all"]):
        names.extend(ALIAS.get(x, [x]))
    if not only_fetch:
        print("free_slots=%d" % ks.free_slots(), flush=True)
        refs = [submit_one(n) for n in names]
        if do_wait:
            print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        fetch_one(n)
