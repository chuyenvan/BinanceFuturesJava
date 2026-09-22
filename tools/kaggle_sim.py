"""kaggle_sim - chay Java sim cua repo tren Kaggle CPU kernel, NHIEU KERNEL SONG SONG.

Doc `docs/KAGGLE_SIM.md` truoc khi dung.

Neo (anchor): tren Kaggle sim luon chay `TICKER_SOURCE=file` (Kaggle khong co Aerospike
ticker) => equity cuoi cua `c2b_min` la **60395**, KHONG phai 60390 (so cua Oracle +
`TICKER_SOURCE=aerospike`). Lech dung 1 lenh/970 (FTT BUY 2022-11-09). Moi so sanh
Oracle<->Kaggle chi tin toi ~0.01%.

API cho agent khac:

    from tools.kaggle_sim import submit, wait, fetch
    ref = submit("x96", "c2b_min", {"SIM_LOSER_TIME_STOP_HOURS": 96})
    wait([ref])
    out = fetch("x96")
    # out["print_done"] -> .../storage/printDone.csv
    # out["sim_out"]    -> .../logs/sim.out
    # out["result"]     -> {"equity_final": 62370, "n_trades": ..., "secs": ...}
"""

from __future__ import annotations

import json
import logging
import os
import re
import time

LOG = logging.getLogger(__name__)

USER = "chuyendinh"
BUNDLE_DS = USER + "/sim-c2b-bundle"
# [X1_T170_48M 2026-09-22] cua so DEV thuc te cua T170/X1 la 2021-07-01..2025-12-31
#   (~54 thang, 1,645 ngay, xem leakFreeFrom trong manifest.txt cua wfo_ds_x1_2021) - can
#   THEM wfo-ticker-2021 (365 ngay) chu KHONG CHI 2024h2/2025h1/2025h2: AGENT_RUNBOOK cu
#   (2026-09-06) chi nhac 3 dataset nua sau nhung danh sach luc do van thieu ca nua dau
#   2021. Kiem tra thuc te tren Kaggle (KaggleApi.dataset_list_files, 2026-09-22): CA 7
#   dataset duoi day lien tuc, KHONG thieu ngay nao tu 2021-01-01 den 2025-12-31
#   (365+365+365+182+184+181+184 = 1,826 file).
TICKER_DS = [USER + "/wfo-ticker-2021",
             USER + "/wfo-ticker-2022", USER + "/wfo-ticker-2023",
             USER + "/wfo-ticker-2024h1", USER + "/wfo-ticker-2024h2",
             USER + "/wfo-ticker-2025h1", USER + "/wfo-ticker-2025h2"]
# So ngay ticker TOI THIEU kernel phai thay truoc khi chay (guard chong thieu ngay am tham).
#   1,826 = TONG so file cua CA 7 dataset TICKER_DS o tren (2021-01-01..2025-12-31, da
#   kiem KHONG thieu ngay nao). Day qua CFG["ticker_min_days"] vao kernel; run cua so
#   ngan hon truyen submit(..., ticker_min_days=<nho hon, vd 912>).
TICKER_MIN_DAYS = 1826
DATASETS = [BUNDLE_DS] + TICKER_DS

MAX_CONCURRENT = 5          # slot CPU toan account (docs/KAGGLE_RULES.md muc 1)
KERNEL_PREFIX = "sim"
WORKDIR = os.environ.get("KAGGLE_SIM_WORKDIR", "/home/ubuntu/kaggle_sim")
OUTDIR = os.environ.get("KAGGLE_SIM_OUTDIR", "/home/ubuntu/kaggle_sim/out")

DEFAULT_XMX = "22g"         # Kaggle CPU kernel: 31GB RAM / 4 core
DEFAULT_SIM_END = "20240630"
DEFAULT_TIMEOUT_S = 5400
TERMINAL = ("COMPLETE", "ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED")

_API = None


def _api():
    global _API
    if _API is None:
        from kaggle.api.kaggle_api_extended import KaggleApi
        _API = KaggleApi()
        _API.authenticate()
    return _API


def slug(tag: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(tag).lower()).strip("-")
    if not s:
        raise ValueError("tag rong sau khi slug hoa: %r" % tag)
    return s


def kernel_ref(tag: str) -> str:
    return "%s/%s-%s" % (USER, KERNEL_PREFIX, slug(tag))


def _status(ref: str) -> str:
    r = _api().kernels_status(ref)
    st = r.get("status") if isinstance(r, dict) else getattr(r, "status", None)
    return str(st).split(".")[-1].upper()


def free_slots() -> int:
    """So slot CPU con trong tren account (5 - dang running/queued)."""
    used = 0
    for k in _api().kernels_list(mine=True, page_size=50):
        try:
            st = _status(k.ref)
        except Exception:                      # kernel chua chay lan nao
            continue
        if st in ("RUNNING", "QUEUED"):
            used += 1
    return max(0, MAX_CONCURRENT - used)


KERNEL_TEMPLATE = r'''"""sim-runner kernel — SINH TU tools/kaggle_sim.py, KHONG sua tay."""
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
LOG = logging.getLogger("sim-runner")

CFG = json.loads(__CFG_JSON__)

IN, WORK = "/kaggle/input", "/kaggle/working"
# Cfg fail-fast: da co TRADING_PROFILE thi KHONG duoc con env tham so giao dich.
TRADING_PREFIX = ("SIM_", "DCA_", "TS_", "SELECTOR_", "TIER_", "CONF_SIZE_", "TRAIL_",
                  "GATE_", "LIVE_", "SIZE_MULT", "MAX_CONCURRENT", "TIME_STOP_HOURS",
                  "ENABLE_SHORT", "ABLATION_MODE", "SHORT_")
TRADING_KEYS = ("NUMBER_ORDER_BUDGET", "HARD_STOP_LOSS_RATE", "DISABLE_PREDICT_SYMBOL",
                "CAPITAL_START", "SEL_BACKTEST_SET", "SEL_BACKTEST_HORIZON_IDX",
                "WFO_FUNDING_PRED_DIR")


def f1(pat):
    m = sorted(glob.glob(pat, recursive=True))
    if not m:
        LOG.error("MISSING %s", pat)
        sys.exit(1)
    return m[0]


jar = f1(IN + "/**/sim.jar")
manifest = f1(IN + "/**/manifest.txt")
DS = os.path.dirname(manifest)                     # WFO_DATA_DIR
cfgp = f1(IN + "/**/config.properties")
basep = f1(IN + "/**/prof_" + CFG["profile"] + ".properties")
exinfo = f1(IN + "/**/exchange_info_pin.json")
# Mount Kaggle KHONG phang: dataset nam duoi /kaggle/input/datasets/<user>/<slug>/ .
# => loc theo slug tren duong dan da glob de quy, khong ghep tien to cung.
_BDS = CFG.get("bins_ds") or ""          # bins rieng cua 1 chan (dataset khac bundle)
_cand = sorted(glob.glob(IN + "/**/predict_wf_20220101.bin", recursive=True))
if _BDS:
    _cand = [c for c in _cand if ("/" + _BDS + "/") in c]
if not _cand:
    LOG.error("MISSING bins cho bins_ds=%r (ung vien=%s)", _BDS,
              sorted(glob.glob(IN + "/**/predict_wf_20220101.bin", recursive=True)))
    sys.exit(1)
PREDWF = os.path.dirname(_cand[0])

# ticker: loader doc RELATIVE "kaggle_data_hpo/" trong CWD; .gz co the bi Kaggle tu giai nen
link = os.path.join(WORK, "kaggle_data_hpo")
os.makedirs(link, exist_ok=True)
tk = sorted(glob.glob(IN + "/**/ticker_2*.bin*", recursive=True))
for t in tk:
    dst = os.path.join(link, os.path.basename(t))
    if not os.path.lexists(dst):
        os.symlink(t, dst)
LOG.info("jar=%s ds=%s predwf=%s ticker=%d", jar, DS, PREDWF, len(tk))
if len(tk) < CFG["ticker_min_days"]:
    LOG.error("chi thay %d file ticker, can >= %d (cua so do cua run nay)",
              len(tk), CFG["ticker_min_days"])
    sys.exit(1)

os.makedirs(WORK + "/storage", exist_ok=True)
os.makedirs(WORK + "/logs", exist_ok=True)
shutil.copy(cfgp, WORK + "/config.properties")     # Configs static-init doc CWD
os.chdir(WORK)

# --- profile: COPY roi sua, khong bao gio dat tham so giao dich qua env ---
pairs, order = {}, []
for ln in open(basep):
    s = ln.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    k = k.strip()
    if k not in pairs:
        order.append(k)
    pairs[k] = v.strip()
ov = dict(CFG["overrides"])
ov["WFO_FUNDING_PRED_DIR"] = PREDWF                 # bins pin: duong dan Oracle -> mount Kaggle
# [BRC B7] regime CSV (gate lien tuc/nhi phan): SIM_REGIME_FILE tro ten file -> resolve mount Kaggle.
#   No-op khi profile/overrides khong khai bao SIM_REGIME_FILE (T170/c2b...) => khong doi hanh vi cu.
_rf = ov.get("SIM_REGIME_FILE") or pairs.get("SIM_REGIME_FILE")
if _rf:
    ov["SIM_REGIME_FILE"] = f1(IN + "/**/" + os.path.basename(_rf))
    LOG.info("regime_file resolved=%s", ov["SIM_REGIME_FILE"])
for k, v in ov.items():
    if k not in pairs:
        order.append(k)
    pairs[k] = "true" if v is True else "false" if v is False else str(v)
prof = WORK + "/prof_run.properties"
with open(prof, "w") as f:
    for k in order:
        f.write("%s=%s\n" % (k, pairs[k]))
LOG.info("profile=%s overrides=%s", basep, json.dumps(CFG["overrides"]))

env = dict(os.environ)
for k in list(env):
    if k in TRADING_KEYS or k.startswith(TRADING_PREFIX):
        del env[k]
env.update({
    "WFO_DATA_DIR": DS,
    "WFO_SMART_CACHE": "1",
    "WFO_SET_PRED": "ai_pred_market_gate_wfo",
    "WFO_CODE_SHA": CFG["code_sha"],
    "SIM_END_DATE": CFG["sim_end_date"],
    "EXCHANGE_INFO_PATH": exinfo,
    "TRADING_PROFILE": prof,
})

LOGP, PDONE = WORK + "/logs/sim.out", WORK + "/storage/printDone.csv"
t0 = time.time()
try:
    with open(LOGP, "w") as lf:
        rc = subprocess.call(
            ["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx" + CFG["xmx"], "-cp", jar,
             "com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss"],
            env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=CFG["timeout_s"])
except subprocess.TimeoutExpired:
    rc = -9
secs = round(time.time() - t0, 1)

# rc=1 KHONG phai fail: tieu chi la log co "done:"+"b:" VA printDone.csv co dong.
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")
last, first, phash, ndone = None, None, "", 0
for ln in open(LOGP, errors="ignore"):
    m = RX.search(ln)
    if m:
        v = (m.group(1), int(m.group(2)) + int(m.group(3)), int(m.group(2)))
        first = first or v
        last = v
    if not phash:
        mh = re.search(r"PROFILE_HASH=(\w+)", ln)
        if mh:
            phash = mh.group(1)
# GUARD: SimpleSymbolMapper VAN doc Aerospike (khong co nhanh TICKER_SOURCE=file).
# Mat mapper => id symbol tu sinh => ket qua LECH AM THAM. Fail-fast, khong bao so sai.
mapper_n = 0
for ln in open(LOGP, errors="ignore"):
    mm = re.search(r"Loaded Symbol Mapper: (\d+) symbols", ln)
    if mm:
        mapper_n = int(mm.group(1))
        break
if mapper_n < 800:
    LOG.error("SYMBOL_MAPPER_FAIL n=%d — can >=800. Kernel phai co enable_internet=True "
              "VA Aerospike Oracle (AEROSPIKE_HOST_226 trong config.properties) phai song.",
              mapper_n)
    sys.exit(2)

n_trades = 0
if os.path.exists(PDONE):
    with open(PDONE, errors="ignore") as f:
        f.readline()
        n_trades = sum(1 for ln in f if ln.strip())

res = {"tag": CFG["tag"], "profile": CFG["profile"], "overrides": CFG["overrides"],
       "java_rc": rc, "secs": secs, "profile_hash": phash,
       "equity_start": first[1] if first else None,
       "equity_final": last[1] if last else None,
       "b_final": last[2] if last else None,
       "date_first": first[0] if first else None,
       "date_last": last[0] if last else None,
       "n_trades": n_trades, "symbol_mapper": mapper_n,
       "ok": bool(last and n_trades > 0)}
with open(WORK + "/result.json", "w") as f:
    json.dump(res, f, indent=1)
LOG.info("RESULT %s", json.dumps(res))

subprocess.call(["gzip", "-f", LOGP])              # sim.out ~ hang chuc MB
if not res["ok"]:
    LOG.error("SIM_FAIL rc=%s n_trades=%s", rc, n_trades)
    sys.exit(1)
LOG.info("SIM_DONE tag=%s equity=%s trades=%s secs=%s",
         res["tag"], res["equity_final"], n_trades, secs)
sys.exit(0)
'''


<<<<<<< HEAD
def submit(tag, profile, overrides=None, *, bins_ds=None, bundle_ds=None, code_sha="head",
=======
def submit(tag, profile, overrides=None, *, bins_ds=None, bundle_ds=None, extra_ds=None, code_sha="head",
>>>>>>> ab447a7389d84e41ed55949f5458acdcd70bd2c4
           sim_end_date=DEFAULT_SIM_END, ticker_min_days=TICKER_MIN_DAYS,
           xmx=DEFAULT_XMX, timeout_s=DEFAULT_TIMEOUT_S, enable_internet=True,
           push=True) -> str:
    """Day 1 sim len Kaggle. Tra ve kernel ref (`chuyendinh/sim-<tag>`).

    `overrides` la dict key=value ghi de LEN BAN COPY cua profile (khong bao gio dat
    qua env — `Cfg` fail-fast `exit 2` neu co env tham so giao dich kem TRADING_PROFILE).
    `bundle_ds` (moi, 2026-09-22): doi bundle du lieu chinh (mac dinh `BUNDLE_DS` =
    sim-c2b-bundle) sang dataset KHAC (vd bundle X1 48 thang) — truyen TEN dataset
    (KHONG prefix USER). `TICKER_DS` (ticker) va cach chon bins qua `bins_ds` khong doi.
    """
    ref = kernel_ref(tag)
    folder = os.path.join(WORKDIR, slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": str(tag), "profile": profile, "overrides": dict(overrides or {}),
           "sim_end_date": sim_end_date, "xmx": xmx, "timeout_s": timeout_s,
           "code_sha": code_sha, "bins_ds": bins_ds or "",
           "ticker_min_days": int(ticker_min_days)}
    code = KERNEL_TEMPLATE.replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    bundle_ref = (USER + "/" + bundle_ds) if bundle_ds else BUNDLE_DS
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py",
            "language": "python", "kernel_type": "script", "is_private": True,
            "enable_gpu": False, "enable_internet": enable_internet,
            "dataset_sources": [bundle_ref] + TICKER_DS
<<<<<<< HEAD
                                + ([USER + "/" + bins_ds] if bins_ds else []),
=======
                                + ([USER + "/" + bins_ds] if bins_ds else [])
                                + [(USER + "/" + d) for d in (extra_ds or [])],
>>>>>>> ab447a7389d84e41ed55949f5458acdcd70bd2c4
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = _api().kernels_push(folder)
        LOG.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def wait(refs, poll_s=60, timeout_s=13 * 3600):
    """Cho toi khi moi kernel ve trang thai terminal. Tra ve {ref: status}."""
    refs = list(refs)
    out, t0 = {}, time.time()
    while len(out) < len(refs):
        for ref in refs:
            if ref in out:
                continue
            try:
                st = _status(ref)
            except Exception as e:
                LOG.warning("status %s loi: %s", ref, e)
                continue
            if st in TERMINAL:
                out[ref] = st
                LOG.info("%s -> %s", ref, st)
        if len(out) == len(refs):
            break
        if time.time() - t0 > timeout_s:
            for ref in refs:
                out.setdefault(ref, "TIMEOUT")
            break
        time.sleep(poll_s)
    return out


def fetch(tag, out_dir=None):
    """Keo output kernel ve dia. Tra ve dict duong dan + result.json da parse."""
    ref = kernel_ref(tag)
    dest = out_dir or os.path.join(OUTDIR, slug(tag))
    os.makedirs(dest, exist_ok=True)
    _api().kernels_output(ref, path=dest, force=True, quiet=True)
    import gzip
    import glob as _g
    for gz in _g.glob(os.path.join(dest, "**", "sim.out.gz"), recursive=True):
        plain = gz[:-3]
        if not os.path.exists(plain):
            with gzip.open(gz, "rb") as fi, open(plain, "wb") as fo:
                fo.write(fi.read())

    def _one(pat):
        m = sorted(_g.glob(os.path.join(dest, "**", pat), recursive=True))
        return m[0] if m else None

    rj = _one("result.json")
    res = json.load(open(rj)) if rj else None
    return {"ref": ref, "dir": dest, "print_done": _one("printDone.csv"),
            "sim_out": _one("sim.out"), "result": res,
            "log": _one("%s.log" % slug(tag))}


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="chay sim tren Kaggle")
    ap.add_argument("cmd", choices=["submit", "wait", "fetch", "slots"])
    ap.add_argument("--tag")
    ap.add_argument("--profile", default="c2b_min")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    ap.add_argument("--code-sha", default="head")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.cmd == "slots":
        LOG.info("free_slots=%d", free_slots())
    elif a.cmd == "submit":
        ov = dict(s.split("=", 1) for s in a.set)
        LOG.info("ref=%s", submit(a.tag, a.profile, ov, code_sha=a.code_sha))
    elif a.cmd == "wait":
        LOG.info("%s", wait([kernel_ref(a.tag)]))
    else:
        LOG.info("%s", json.dumps(fetch(a.tag), indent=1))


if __name__ == "__main__":
    _cli()
