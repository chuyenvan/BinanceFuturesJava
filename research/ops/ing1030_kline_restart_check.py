#!/usr/bin/env python3
# ing1030: doi chieu kline_1m_opt 242 (CHI DOC) vs REST fapi final quanh cac lan restart collectData 10-30. Nhe: tuan tu, <=1 call/0.3s.
import sys, json, time, random, datetime, urllib.request, urllib.error, struct
sys.path.insert(0, "/home/ubuntu/ops")
import kline_backfill_242 as kb
MN = 60000
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
def t7(s):
    return int(datetime.datetime.strptime("2026-10-30 " + s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ7).timestamp() * 1000)
WIN = [("00:38", "00:46"), ("03:00", "03:14"), ("03:40", "03:52"), ("04:14", "04:20"), ("07:20", "07:35"), ("08:57", "09:03"), ("20:38", "20:44")]
def f32(x): return struct.unpack("<f", struct.pack("<f", float(x)))[0]
def ulp(a, b):
    ia = struct.unpack("<i", struct.pack("<f", a))[0]; ib = struct.unpack("<i", struct.pack("<f", b))[0]
    return abs(ia - ib) <= 1
db = kb.AS("103.157.218.242", 3222)
out = {"windows": []}
calls = 0
for a, b in WIN:
    m0, m1 = t7(a), t7(b)
    mins = list(range(m0, m1 + MN, MN))
    recs = {}
    for m in mins:
        r = db.get(m)
        recs[m] = kb.decode(r[0]) if r[0] is not None else None
    sizes = {kb.k7(m)[9:]: (len(v) if v else 0) for m, v in recs.items()}
    ref = recs[mins[-1]] or {}
    top = sorted(ref, key=lambda s: -ref[s][4])[:15]
    pool = sorted(set(ref) - set(top))
    rnd = random.Random(m0).sample(pool, min(15, len(pool)))
    cells = bad = miss = err = 0; ex = []
    for s in top + rnd:
        u = "https://fapi.binance.com/fapi/v1/klines?symbol=%sUSDT&interval=1m&startTime=%d&endTime=%d&limit=30" % (s, m0, m1)
        try:
            with urllib.request.urlopen(u, timeout=10) as r:
                rows = json.loads(r.read()); calls += 1
        except urllib.error.HTTPError as e:
            err += 1
            if e.code in (418, 429):
                print("STOP REST", e.code); out["stop"] = e.code; break
            continue
        except Exception:
            err += 1; continue
        R = {int(x[0]): (f32(x[1]), f32(x[2]), f32(x[3]), f32(x[4]), f32(x[7])) for x in rows}
        for m in mins:
            rec = recs[m]
            if rec is None or s not in rec:
                if m in R: miss += 1
                continue
            if m not in R: continue
            cells += 1
            if not all(ulp(x, y) for x, y in zip(rec[s], R[m])):
                bad += 1
                if len(ex) < 6: ex.append("%s@%s q=%.4f c242=%g cR=%g" % (s, kb.k7(m)[9:], rec[s][4] / R[m][4] if R[m][4] else -1, rec[s][3], R[m][3]))
        time.sleep(0.3)
    w = dict(win="%s-%s" % (a, b), sizes=sizes, cells=cells, bad=bad, miss=miss, err=err, ex=ex)
    out["windows"].append(w); print(json.dumps(w))
    if "stop" in out: break
out["rest_calls"] = calls
json.dump(out, open("/home/ubuntu/claude_master/ing1030/kchk.json", "w"), indent=1)
print("DONE calls", calls)
