"""Tao profiles/g2_flat3.properties = r4_kg0_k16_f015_g155 + gate ratio W90 + FLAT3 exit, roi doi chieu voi
prof_run.properties cua kernel trail2-g2-flat3 (cau hinh hieu luc da cho md5 650c386f)."""
import re
import sys

REPO = "/home/ubuntu/src/BinanceFuturesJava"
BASE = REPO + "/profiles/r4_kg0_k16_f015_g155.properties"
OUT = REPO + "/profiles/g2_flat3.properties"
RUN = "/home/ubuntu/kaggle_sim/out/trail2-g2-flat3/prof_run.properties"
SET = [("SIM_GATE_ROLLING_MODE", "ratio"), ("SIM_GATE_ROLLING_DAYS", "90"),
       ("SIM_GATE_ROLLING_PCT", "0.999950829"),
       ("TS_GIVEBACK_RATIO", "1.0"), ("SIM_TS_MAX_GAP", "0.03"), ("SIM_TS_MAX_GAP_WEAK", "0.03")]


def parse(p):
    d = {}
    for ln in open(p):
        s = ln.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


lines = open(BASE).read().split("\n")
todo = dict(SET)
out = []
for ln in lines:
    m = re.match(r"^\s*([A-Za-z0-9_]+)\s*=", ln)
    if m and m.group(1) in todo and not ln.lstrip().startswith("#"):
        out.append("%s=%s" % (m.group(1), todo.pop(m.group(1))))
    else:
        out.append(ln)
hdr = ["# ============================================================================",
       "# PROFILE G2 + FLAT3 = BASELINE B0 (owner chot 2026-09-29, PREREG_FEAT_CUT_RVOL15M buoc 0)",
       "# = r4_kg0_k16_f015_g155 + gate ratio W90 (PCT 0.999950829) + FLAT3 exit (giveback 1.0, gap 0.03/0.03),",
       "# giu SIM_RATE_PROFIT_STOP_MARKET=0.07. Doi chieu: sim Kaggle (jar sim-jar-gdv2) => printDone md5 650c386f0d0dfea334af9d55ca2f21d4; xem RESULT_TRAIL2_G2.md (n 2517, eq 131908).",
       "# ============================================================================", ""]
tail = ["", "# --- G2 gate (ratio) + FLAT3 exit (ghi de/bo sung so voi r4_kg0_k16_f015_g155) ---"]
for k, v in SET:
    if k in todo:
        tail.append("%s=%s" % (k, v))
open(OUT, "w").write("\n".join(hdr + out).rstrip("\n") + "\n" + "\n".join(tail) + "\n")
mine, run = parse(OUT), parse(RUN)
mine.pop("WFO_FUNDING_PRED_DIR", None)
run.pop("WFO_FUNDING_PRED_DIR", None)
diff = {k: (mine.get(k), run.get(k)) for k in set(mine) | set(run) if mine.get(k) != run.get(k)}
print("keys profile=%d run=%d diff=%s" % (len(mine), len(run), diff))
sys.exit(0 if not diff else 4)
