"""CHAN DOAN (KHONG FIT): ap luat phan vi cuon W=30 ngay len CHINH chuoi p15 LIVE 2026.

Nguon: /tmp/live242_ts_p15.txt (242 full.log, 12/08/2026-27/09/2026, READ-ONLY).
Muc dich: uoc TY LE PASS cua phuong an A tren nguon live (khong dung de chon Q/W/nguong).
Causal: cua so [t-W, t); ky phap nearest-rank (giong EntryGate.buildP15Rolling).
"""
import json
import math
from datetime import datetime

P = "/tmp/live242_ts_p15.txt"
OUT = "/home/ubuntu/src/BinanceFuturesJava/docs/result/RESULT_GATE_ROOTCAUSE.json"
QS = [0.995, 0.998, 0.999]
WMS = 30 * 86400000
TICK_MS = 15 * 60 * 1000


def parse_ts(s):
    s = s.split(".")[0]
    return datetime.strptime(s, "%d/%m/%Y %H:%M:%S").timestamp() * 1000.0


def main():
    rows = []
    for ln in open(P):
        p = ln.split()
        if len(p) < 3:
            continue
        try:
            rows.append((parse_ts(p[0] + " " + p[1]), float(p[2])))
        except ValueError:
            pass
    rows.sort()
    t = [r[0] for r in rows]
    v = [r[1] for r in rows]
    n = len(v)
    days = (t[-1] - t[0]) / 86400000.0
    res = {"n": n, "days": round(days, 2),
           "first": datetime.fromtimestamp(t[0] / 1000).strftime("%Y-%m-%d"),
           "last": datetime.fromtimestamp(t[-1] / 1000).strftime("%Y-%m-%d")}
    # ticks thuc (moi 15') = so moc thoi gian rieng biet lam tron ve phut
    ticks = len(set(int(x // TICK_MS) for x in t))
    res["distinct_ticks"] = ticks
    res["ticks_per_day"] = round(ticks / days, 2)
    res["samples_per_tick"] = round(n / ticks, 2)

    for q in QS:
        # rolling causal: giu mang cua so da sort (n nho, O(n*w) chap nhan voi n=9k va w~6k)
        pass_n = 0
        start_i = 0
        last_thr = None
        hi = 0
        j = 0  # con tro cua so
        win = []
        # don gian: dung vong lap + bisect (n=9k, w~6k => ~5e7 phep, chap nhan)
        import bisect
        for i in range(n):
            while hi < i:
                bisect.insort(win, v[hi])
                hi += 1
            cut = t[i] - WMS
            while j < hi and t[j] < cut:
                x = v[j]
                k = bisect.bisect_left(win, x)
                if k < len(win) and win[k] == x:
                    win.pop(k)
                j += 1
            m = len(win)
            if m <= 0:
                last_thr = None
                continue
            rank = int(math.ceil(q * m))
            rank = max(1, min(m, rank))
            thr = win[rank - 1]
            last_thr = thr
            if v[i] >= thr:
                pass_n += 1
        res["q%g" % q] = {"pass_n": pass_n, "pass_frac": round(pass_n / n, 5),
                          "pass_per_day": round(pass_n / days, 3),
                          "thr_last_pct": round(last_thr, 4) if last_thr else None}
    # "hom nay" (cua so 30 ngay cuoi) quantile
    tail = [x for tt, x in zip(t, v) if tt >= t[-1] - WMS]
    res["last30d"] = {"n": len(tail), "p99": round(sorted(tail)[int(0.99 * len(tail)) - 1], 4),
                      "p99.5": round(sorted(tail)[int(0.995 * len(tail)) - 1], 4),
                      "p99.8": round(sorted(tail)[int(0.998 * len(tail)) - 1], 4),
                      "max": round(max(tail), 4)}
    d = json.load(open(OUT))
    d["live_rolling_diag"] = res
    json.dump(d, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
