"""SELECTOR_ABLATION — B0REF: B0 thuan (tools/kaggle_sim.py HEAD, KHONG SA block) chay cung dot de tach nguyen nhan
md5 P0 khac 650c386f (anh Kaggle vs duong override). Cau hinh y het exit-time-p0."""
import sys, json, logging, hashlib
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
assert hashlib.md5(open("/home/ubuntu/src/BinanceFuturesJava/tools/kaggle_sim.py", "rb").read()).hexdigest() == "8b60b00afad39f2528aaa15092225c9b"
B0OV = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90, "SIM_GATE_ROLLING_PCT": 0.999950829,
        "TS_GIVEBACK_RATIO": 1.0, "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}
r = ks.submit("selab-b0ref", "r4_kg0_k16_f015_g155", B0OV, jar_ds="sim-jar-gdv2", bundle_ds="sim-x1-2021-bundle",
              sim_end_date="20251231", xmx="22g", timeout_s=5400, code_sha=sys.argv[1])
logging.info("PUSHED b0ref %s", r)
