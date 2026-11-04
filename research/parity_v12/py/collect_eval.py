#!/usr/bin/env python3
"""PARITY_V12_DRY §5.5 (ingestor collectData): cham 1 ngay UTC D tu log collectData da keo (sh/collect_pull.sh, chi doc 242).
Luat prereg: collectData tu restart ('Too many symbol price errors') <= 2 lan/ngay. Mo ta them (khong phai luat): so MainClass,
[KLINE-COVER] phut chua_chot>0 / suspects, [REST-BUDGET] http429/http418/denied, [PRICE-AGE] canh bao + max ms.
argv: D [logfile.gz]  -> ~/claude_master/parity_v12w/d/<D>/work/collect_<tag>.json"""
import datetime as dt
import gzip
import json
import os
import re
import sys

PAT = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)")


def lt(ln):
    m = PAT.match(ln)
    if not m:
        return None
    d, mo, y, h, mi, s, ms = (int(x) for x in m.groups())
    return int(dt.datetime(y, mo, d, h, mi, s, tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000) + ms


def evaluate(lines, day):
    d0 = int(dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    d1 = d0 + 86400000
    r = {"day": day, "n_lines": 0, "first": None, "last": None, "restart_too_many": 0, "mainclass": 0,
         "kline_cover_lines": 0, "kline_cover_chua_chot_minutes": 0, "kline_cover_suspects": 0,
         "rest_budget_lines": 0, "http429_max": 0, "http418_max": 0, "denied_max": 0,
         "price_age_warn": 0, "price_age_max_ms": 0}
    for ln in lines:
        t = lt(ln)
        if t is None or not (d0 <= t < d1):
            continue
        r["n_lines"] += 1
        r["first"] = t if r["first"] is None else min(r["first"], t)
        r["last"] = t if r["last"] is None else max(r["last"], t)
        if "Too many symbol price errors" in ln:
            r["restart_too_many"] += 1
        if "MainClass:" in ln:
            r["mainclass"] += 1
        if "[KLINE-COVER]" in ln:
            r["kline_cover_lines"] += 1
            m = re.search(r"chua_chot=(\d+).*suspects=(\d+)", ln)
            if m:
                r["kline_cover_chua_chot_minutes"] += int(m.group(1)) > 0
                r["kline_cover_suspects"] += int(m.group(2))
        if "[REST-BUDGET]" in ln:
            r["rest_budget_lines"] += 1
            for k, key in (("http429", "http429_max"), ("http418", "http418_max"), ("denied", "denied_max")):
                m = re.search(r"\b%s=(\d+)" % k, ln)
                if m:
                    r[key] = max(r[key], int(m.group(1)))
        if "[PRICE-AGE]" in ln:
            r["price_age_warn"] += 1
            m = re.search(r"dung (\d+) ms", ln)
            if m:
                r["price_age_max_ms"] = max(r["price_age_max_ms"], int(m.group(1)))
    # do phu: can log phu ca ngay (dong dau <= D+5', dong cuoi >= D+1-5')
    r["covers_day"] = bool(r["first"] and r["first"] <= d0 + 300000 and r["last"] >= d1 - 300000)
    r["collectData_restart_le2"] = (r["restart_too_many"] <= 2) if r["covers_day"] else None
    return r


if __name__ == "__main__":
    day = sys.argv[1]
    root = os.environ.get("PV_ROOT") or os.path.expanduser("~/claude_master/parity_v12w")
    src = sys.argv[2] if len(sys.argv) > 2 else root + "/collect/collect_%s.log.gz" % day
    lines = gzip.open(src, "rt", errors="ignore").read().splitlines() if os.path.exists(src) else []
    r = evaluate(lines, day)
    r["src"] = src if os.path.exists(src) else None
    w = root + "/d/%s/work" % day
    os.makedirs(w, exist_ok=True)
    json.dump(r, open(w + "/collect_%s.json" % day.replace("-", ""), "w"), indent=1)
    print(json.dumps(r, indent=1))
