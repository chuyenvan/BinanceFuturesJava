"""shadow_vs_sim — doc log bot SHADOW (duong live) thanh mot bang lenh de doi chung voi sim.

Vi sao can: shadow chay tren duong LIVE, sim chay tren duong SIM. Hai ben khong co dinh dang
chung. Tool nay dua log shadow ve dung cac cot ma `printDone.csv` cua sim co, de ghep cap
tung lenh theo (symbol, ts_entry).

CANH BAO PHAM VI (doc truoc khi tin so):
  * Shadow KHONG co equity that (`docs/L1_SHADOW_C3.md` muc 3e) => cot `profit` o day la
    ke toan giay tinh tu gia, KHONG phai PnL tai khoan. Khong duoc so `mean(margin)`/equity
    voi sim.
  * Duong live KHONG co time-stop 168h => nhom lenh ma sim dong bang `STOP_LOSS_DONE`
    khong co doi ung o shadow. Ghep cap se thieu ho o do; do la co hoc, khong phai bug.
  * `symbolPred` cua shadow sinh tu `Funding_Classifier_Final.onnx`, cua sim tu
    `predwf_G015x26` — KHAC HIEU CHUAN. Phai tach STRONG/WEAK truoc khi so.

LUAT LOG CUA REPO: dung module `logging`, khong dung ham in san co.

usage:
  python3 shadow_vs_sim.py parse <full.log> <out.csv>
  python3 shadow_vs_sim.py pair  <shadow_ledger.csv> <sim_printDone.csv> <out.csv>
"""

import bisect
import csv
import logging
import os
import re
import sys
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger(__name__)

TZ = timezone(timedelta(hours=7))          # log 242 ghi gio GMT+7
TS_RE = re.compile(r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\.\d{3}")

# 06/09/2026 11:58:10.374 ... [SHADOW] would-BUY BUY XUSDT entry: 1.23 quantity: 4.0 time:20260906 11:57 market level: PREDICT_SYMBOL_TRADE
WOULD_BUY_RE = re.compile(
    r"\[SHADOW\] would-BUY (?P<side>BUY|SELL) (?P<sym>\w+) entry: (?P<entry>[0-9.eE+-]+)"
    r" quantity: (?P<qty>[0-9.eE+-]+) time:(?P<t>\d{8} \d{2}:\d{2}) market level: (?P<lvl>\w+)"
)
# AI PASS [XUSDT] Reason: ... symbolPred: 0.0541
AI_PASS_RE = re.compile(r"AI PASS \[(?P<sym>\w+)\].*symbolPred: (?P<pred>[0-9.eE+-]+|null)")
# Market level:20260906 11:57 PREDICT_SYMBOL_TRADE XUSDT 32.3 4.0 1.23
MKT_LVL_RE = re.compile(
    r"Market level:(?P<t>\d{8} \d{2}:\d{2}) (?P<lvl>\w+) (?P<sym>\w+) "
    r"(?P<budget>[0-9.eE+-]+) (?P<qty>[0-9.eE+-]+) (?P<px>[0-9.eE+-]+)"
)
REMOVE_RE = re.compile(r"Remove symbol trade success: \[?(?P<syms>[^\]]*)\]?")


def _log_ms(line):
    """ts cua DONG LOG (GMT+7) -> epoch ms. None neu dong khong co timestamp."""
    m = TS_RE.match(line)
    if not m:
        return None
    dt = datetime.strptime(m.group(1), "%d/%m/%Y %H:%M:%S").replace(tzinfo=TZ)
    return int(dt.timestamp() * 1000)


def _entry_ms(s):
    """truong time:YYYYMMDD HH:MM trong dong would-BUY (GMT+7) -> epoch ms."""
    dt = datetime.strptime(s, "%Y%m%d %H:%M").replace(tzinfo=TZ)
    return int(dt.timestamp() * 1000)


def parse(log_path, out_path):
    """Quet full.log -> ledger lenh shadow. Idempotent: doc lai ca file, ghi de out_path.

    HAI LUOT, co chu dich: log live la da luong (`pool-1` sinh tin hieu, `pool-3` xu ly lenh)
    nen `AI PASS` / `Market level:` KHONG dam bao xuat hien TRUOC `would-BUY` trong file.
    Luot 1 gom moc phu (symbolPred, budget), luot 2 gom lenh roi gan nguoc theo thoi gian.
    Ban mot-luot truoc day am tham mat cot `symbol_pred` khi thu tu bi dao.
    """
    if not os.path.exists(log_path):
        LOG.error("KHONG co file log: %s", log_path)
        return 2
    pred_hist = {}     # sym -> [(ts_log_ms, pred)] tang dan
    budget = {}        # (sym, "YYYYMMDD HH:MM") -> budget live da cap
    n_line = 0
    with open(log_path, "r", errors="replace") as fh:
        for line in fh:
            n_line += 1
            if "symbolPred:" in line:
                m = AI_PASS_RE.search(line)
                if m:
                    t = _log_ms(line)
                    if t is not None:
                        p = m.group("pred")
                        pred_hist.setdefault(m.group("sym"), []).append(
                            (t, None if p == "null" else float(p)))
            elif "Market level:" in line:
                m = MKT_LVL_RE.search(line)
                if m:
                    budget[(m.group("sym"), m.group("t"))] = float(m.group("budget"))
    for v in pred_hist.values():
        v.sort(key=lambda x: x[0])

    def pred_at(sym, ts):
        """symbolPred duoc log GAN NHAT TRUOC ts (khong lay gia tri tuong lai)."""
        h = pred_hist.get(sym)
        if not h:
            return None
        i = bisect.bisect_right([x[0] for x in h], ts) - 1
        return h[i][1] if i >= 0 else None

    orders = {}        # (sym, ts_entry) -> dict
    closes = []        # (ts_log, sym)
    with open(log_path, "r", errors="replace") as fh:
        for line in fh:
            if "would-BUY" in line:
                m = WOULD_BUY_RE.search(line)
                if m:
                    ts = _entry_ms(m.group("t"))
                    tlog = _log_ms(line)
                    orders[(m.group("sym"), ts)] = {
                        "sym": m.group("sym"),
                        "ts_entry": ts,
                        "ts_log": tlog,
                        "side": m.group("side"),
                        "entry": float(m.group("entry")),
                        "qty": float(m.group("qty")),
                        "market_level": m.group("lvl"),
                        "symbol_pred": pred_at(m.group("sym"), tlog if tlog else ts),
                        "budget": budget.get((m.group("sym"), m.group("t"))),
                        "ts_exit": None,
                    }
            elif "Remove symbol trade success" in line:
                m = REMOVE_RE.search(line)
                if m:
                    t = _log_ms(line)
                    for s2 in [x.strip() for x in m.group("syms").split(",") if x.strip()]:
                        closes.append((t, s2))
    # FIFO: moi lan dong khop lenh MO SOM NHAT cua symbol do (khong the phan biet hon tu log)
    for t, sym in sorted(closes, key=lambda x: (x[0] is None, x[0])):
        cands = [k for k in orders if k[0] == sym and orders[k]["ts_exit"] is None
                 and (t is None or k[1] <= t)]
        if cands:
            orders[min(cands, key=lambda k: k[1])]["ts_exit"] = t
    cols = ["sym", "ts_entry", "ts_log", "side", "entry", "qty", "market_level",
            "symbol_pred", "budget", "ts_exit"]
    with open(out_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for k in sorted(orders):
            w.writerow(orders[k])
    n_open = sum(1 for o in orders.values() if o["ts_exit"] is None)
    n_nopred = sum(1 for o in orders.values() if o["symbol_pred"] is None)
    LOG.info("doc %d dong -> %d lenh shadow (%d chua dong, %d thieu symbolPred) -> %s",
             n_line, len(orders), n_open, n_nopred, out_path)
    if not orders:
        LOG.warning("KHONG co dong would-BUY nao. Kiem: SHADOW_NO_PUSH=true? budget > 0?"
                    " (xem docs/L1_SHADOW_C3.md muc 1.1 - shadow 242 dang bi chan budget)")
    return 0


def pair(shadow_csv, sim_csv, out_path):
    """Ghep cap (sym, ts_entry) giua ledger shadow va printDone.csv cua sim.

    KHONG tinh ty le chat luong o day — chi ghep cap va bao do phu. Cham diem lam rieng,
    va PHAI tach STRONG/WEAK (docs/L1_SHADOW_C3.md muc 7.2).
    """
    sh = {}
    with open(shadow_csv) as fh:
        for r in csv.DictReader(fh):
            sh[(r["sym"], int(r["ts_entry"]))] = r
    sim = {}
    with open(sim_csv) as fh:
        rd = csv.DictReader(fh)
        if not rd.fieldnames:
            LOG.error("printDone.csv rong")
            return 2
        c_sym = next((c for c in rd.fieldnames if c.lower() in ("symbol", "sym")), None)
        c_ts = next((c for c in rd.fieldnames if "start" in c.lower() or c.lower() == "ts"), None)
        if not c_sym or not c_ts:
            LOG.error("khong nhan ra cot symbol/ts trong %s: %s", sim_csv, rd.fieldnames)
            return 2
        for r in rd:
            try:
                sim[(r[c_sym], int(float(r[c_ts])))] = r
            except (ValueError, KeyError):
                continue
    keys = sorted(set(sh) | set(sim))
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sym", "ts_entry", "in_shadow", "in_sim",
                    "shadow_pred", "shadow_entry", "sim_row"])
        for k in keys:
            a, b = sh.get(k), sim.get(k)
            w.writerow([k[0], k[1], int(a is not None), int(b is not None),
                        a["symbol_pred"] if a else "", a["entry"] if a else "",
                        "1" if b else ""])
    both = len(set(sh) & set(sim))
    LOG.info("shadow %d | sim %d | ghep cap %d (%.1f%% cua shadow, %.1f%% cua sim)",
             len(sh), len(sim), both,
             100.0 * both / max(len(sh), 1), 100.0 * both / max(len(sim), 1))
    LOG.info("Do phu thap la DU KIEN: K=5 vs K=8, selector khac he"
             " (docs/L1_SHADOW_C3.md muc 2.2). Khong doc nhu loi.")
    return 0


def main(argv):
    if len(argv) < 2:
        LOG.error(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "parse" and len(argv) == 4:
        return parse(argv[2], argv[3])
    if cmd == "pair" and len(argv) == 5:
        return pair(argv[2], argv[3], argv[4])
    LOG.error(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
