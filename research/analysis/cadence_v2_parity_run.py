"""CADENCE-SPLIT-V2 parity runner — docs/plan/PLAN_CADENCE_SPLIT_V2.md §5 (CONG CUOI truoc deploy).

Muc dich: bang chung THUC NGHIEM cho "OFF => y nguyen" cua patch bd7c4cd (MARKET_SCAN_PRIORITY,
mac dinh 0 = OFF) bang cach chay lai 2 chan parity md5 TREN JAR BUILD TU HEAD bd7c4cd.

Jar: dataset chuyendinh/sim-jar-cadence-v2 = target/*.jar build tu bd7c4cd (HEAD, working tree sach).
  sha256 = 4aa42ceb03d34b91090a615260ad7dd1256ff6b22df79e2a083f2b9fb466f80c
Bundle: sim-x1-2021-bundle, cua so DEV 2021-07-01..2025-12-31, ticker_min 1826, 0 sim Oracle.

KY VONG (KHONG doi neu OFF):
  par-kg0   (KEEPLEG0, khong khai key moi)              -> md5 99e42b75cf1a2142f9cd14dc72e371ba / n1085 / eq103083
  par-t170  (x1_gs_t170, khong khai key moi)            -> md5 efb793e2468ca3a7318da0f0ad23d4fc / n1089 / eq111070
  par-bb    (KEEPLEG0 + MARKET_SCAN_MIN=0, MARKET_SCAN_PRIORITY=0 KHAI RO) -> md5 PHAI == par-kg0
  Lech => DUNG, khong deploy.

Dung: python3 research/analysis/cadence_v2_parity_run.py par|bb|all [--no-wait] [--fetch]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-cadence-v2"
END = "20251231"
TICKER_MIN = 1826
SHA = "bd7c4cd+cadence-split-v2"

KEEP0 = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
# belt-and-braces: khai RO rang = 0 (khong chi "khong khai") van phai y nguyen.
BB = dict(KEEP0, MARKET_SCAN_MIN=0, MARKET_SCAN_PRIORITY=0)


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


JOBS = {
    "par-kg0":  dict(tag="cadv2-par-kg0",  profile="x1_gs_t170", overrides=_ov(KEEP0)),
    "par-t170": dict(tag="cadv2-par-t170", profile="x1_gs_t170", overrides={}),
    "par-bb":   dict(tag="cadv2-par-bb",   profile="x1_gs_t170", overrides=_ov(BB)),
}
ALIAS = {"par": ["par-kg0", "par-t170"], "all": ["par-kg0", "par-t170", "par-bb"]}


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
