#!/usr/bin/env python3
"""ing_qf_check.py — cham PREREG_INGEST_QUICKFIX (Q2-Q7) cho 1 gio vua qua. CHAY TREN ORACLE, CHI DOC 242.
Q2: moi phut [now-63', now-3'] doc record kline_1m_opt 242; o thieu = symbol co o phut truoc VA phut sau nhung vang.
Q3: 30 symbol (15 top QV + 15 ngau nhien theo gio) x 60 phut so REST final (limit 61, weight 1/symbol; dung ngay khi 429/418).
Q4-Q7: dong [REST-BUDGET] cua collectData 60' qua (ssh grep nohup.out).
Ghi 1 dong JSON vao ~/claude_master/ing1030/qf_check.jsonl. Dung: python3 ing_qf_check.py  (goi y cron: 23 * * * *)."""
import sys, json, time, random, struct, subprocess, urllib.request, urllib.error, datetime
sys.path.insert(0, "/home/ubuntu/ops")
import kline_backfill_242 as kb
MN = 60000
OUT = "/home/ubuntu/claude_master/ing1030/qf_check.jsonl"
SSH = ["ssh", "-p", "2222", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", "/home/ubuntu/.ssh/id_rsa_chuyennd", "root@103.157.218.242"]

def f32(x): return struct.unpack("<f", struct.pack("<f", float(x)))[0]
def ulp(a, b):
    ia = struct.unpack("<i", struct.pack("<f", a))[0]; ib = struct.unpack("<i", struct.pack("<f", b))[0]
    return abs(ia - ib) <= 1

now = int(time.time() * 1000)
last = now // MN * MN - 3 * MN
mins = [last - i * MN for i in range(61, -1, -1)]   # 62 phut: phut dau/cuoi chi lam bien cho Q2
db = kb.AS("103.157.218.242", 3222)
recs = {}
for m in mins:
    r = db.get(m)
    recs[m] = set(kb.decode(r[0]).keys()) if r[0] is not None else None
dec = {}
missing = []; absent_rec = []
for i in range(1, len(mins) - 1):
    m = mins[i]
    if recs[m] is None:
        absent_rec.append(kb.k7(m)); continue
    a, b = recs[mins[i - 1]] or set(), recs[mins[i + 1]] or set()
    for s in (a & b) - recs[m]:
        missing.append("%s@%s" % (s, kb.k7(m)[9:]))
# Q3
chk = mins[1:-1]
r_last = db.get(chk[-1])[0]
ref = kb.decode(r_last) if r_last is not None else {}
top = sorted(ref, key=lambda s: -ref[s][4])[:15]
pool = sorted(set(ref) - set(top))
rnd = random.Random(now // 3600000).sample(pool, min(15, len(pool)))
full = {m: kb.decode(db.get(m)[0]) for m in chk if recs[m] is not None}
cells = bad = err = 0; ex = []; stop = None
for s in top + rnd:
    u = "https://fapi.binance.com/fapi/v1/klines?symbol=%sUSDT&interval=1m&startTime=%d&endTime=%d&limit=61" % (s, chk[0], chk[-1])
    try:
        with urllib.request.urlopen(u, timeout=10) as r:
            rows = json.loads(r.read())
    except urllib.error.HTTPError as e:
        err += 1
        if e.code in (418, 429): stop = e.code; break
        continue
    except Exception:
        err += 1; continue
    R = {int(x[0]): (f32(x[1]), f32(x[2]), f32(x[3]), f32(x[4]), f32(x[7])) for x in rows}
    for m, rec in full.items():
        if s in rec and m in R:
            cells += 1
            if not all(ulp(x, y) for x, y in zip(rec[s], R[m])):
                bad += 1
                if len(ex) < 5: ex.append("%s@%s" % (s, kb.k7(m)[9:]))
    time.sleep(0.3)
# Q4-Q7 tu log 242
since = datetime.datetime.fromtimestamp((now - 3600000) / 1000).strftime("%Y-%m-%d %H:%M")
cmd = "awk -v t='%s' 'substr($0,1,16)>=t' /home/chuyennd/java/collectData/logs/nohup.out | grep -a '\\[REST-BUDGET\\] calls=\\|Restart: Reset\\|REST banned\\|REST cooldown\\|KLINE-RECON'" % since
lines = subprocess.run(SSH + [cmd], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60).stdout.splitlines()
def grab(k):
    v = []
    for l in lines:
        i = l.find(k + "=")
        if i >= 0:
            try: v.append(int(l[i + len(k) + 1:].split()[0]))
            except ValueError: pass
    return v
w, pk, hd, pg = grab("weight"), grab("peak60s"), grab("hdr_max"), grab("price_gap_max_ms")
res = dict(ts=datetime.datetime.now().isoformat(timespec="seconds"), win="%s..%s" % (kb.k7(chk[0]), kb.k7(chk[-1])),
           Q2_missing=len(missing), Q2_ex=missing[:8], Q2_no_record=absent_rec,
           Q3_cells=cells, Q3_bad=bad, Q3_ex=ex, Q3_rest_err=err, Q3_stop=stop,
           Q4_weight_mean=round(sum(w) / len(w), 1) if w else None, Q4_peak_max=max(pk) if pk else None, Q4_lines=len(w),
           Q5_hdr_max=max(hd) if hd else None, Q6_429_418=sum(grab("http429")) + sum(grab("http418")),
           Q6_ban_lines=sum(1 for l in lines if "REST banned" in l or "REST cooldown" in l),
           Q7_price_gap_max=max(pg) if pg else None, Q7_gt5s=sum(1 for x in pg if x > 5000),
           Q1_restart_lines=sum(1 for l in lines if "Restart: Reset" in l),
           Q8_recon_warn=sum(1 for l in lines if "KLINE-RECON" in l))
res["verdict_gio"] = "OK" if (res["Q2_missing"] == 0 and not absent_rec and bad == 0 and (res["Q4_peak_max"] or 0) <= 300
                              and res["Q6_429_418"] == 0 and res["Q6_ban_lines"] == 0 and res["Q1_restart_lines"] == 0
                              and (res["Q7_price_gap_max"] or 0) <= 15000) else "XEM"
open(OUT, "a").write(json.dumps(res) + "\n")
print(json.dumps(res))
