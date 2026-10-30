#!/usr/bin/env python3
"""ing_qf_check.py — cham PREREG_INGEST_QUICKFIX (+ADD1/1b/1c). CHAY TREN ORACLE, CHI DOC 242, KHONG goi REST fapi tu Oracle.
  python3 ing_qf_check.py                 # moi gio: Q1,Q2,Q4-Q7,Q10,Q11,O1 (+ bao cao lanh_ngoai_3p, loop_escalations) tu log collectData 242 + record kline_1m_opt ton tai
  python3 ing_qf_check.py --vision DAY    # Q3: 30 symbol x 1440 phut ngay UTC DAY (YYYY-MM-DD) so Vision daily (data.binance.vision)
Ghi 1 dong JSON vao ~/claude_master/ing1030/qf_check.jsonl. Goi y cron: 23 * * * * (gio) va 40 9 * * * --vision hom-truoc."""
import sys, io, json, time, random, struct, zipfile, subprocess, urllib.request, datetime, re
sys.path.insert(0, "/home/ubuntu/ops")
import kline_backfill_242 as kb
MN = 60000
OUT = "/home/ubuntu/claude_master/ing1030/qf_check.jsonl"
SSH = ["ssh", "-p", "2222", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", "/home/ubuntu/.ssh/id_rsa_chuyennd", "root@103.157.218.242"]
LOGF = "/home/chuyennd/java/collectData/logs/nohup.out"

def f32(x): return struct.unpack("<f", struct.pack("<f", float(x)))[0]
def ulp(a, b):
    ia = struct.unpack("<i", struct.pack("<f", a))[0]; ib = struct.unpack("<i", struct.pack("<f", b))[0]
    return abs(ia - ib) <= 1

def ssh(cmd):
    return subprocess.run(SSH + [cmd], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120).stdout.splitlines()

def grab(lines, k):
    v = []
    for l in lines:
        m = re.search(r"\b" + re.escape(k) + r"=(-?\d+)", l)
        if m: v.append(int(m.group(1)))
    return v

def hourly():
    now = int(time.time() * 1000)
    since = datetime.datetime.fromtimestamp((now - 3600000) / 1000).strftime("%Y-%m-%d %H:%M")
    pat = r"\[REST-BUDGET\] calls=\|\[KLINE-COVER\]\|Restart: Reset\|REST banned\|REST cooldown\|KLINE-RECON\|\[PRICE-AGE\]\|OutOfMemoryError\|\[SUPERVISOR\]\|OI/LS/taker forward: ghi\|\[REST-BAN\]"
    lines = ssh("awk -v t='%s' 'substr($0,1,16)>=t' %s | grep -a '%s'" % (since, LOGF, pat))
    bud = [l for l in lines if "[REST-BUDGET] calls=" in l]
    cov = [l for l in lines if "[KLINE-COVER]" in l]
    cov_ss = [l for l in cov if "khoi_dong=0" in l]
    # Q2: phut M-2 (>= +90 s) con o chua chot, hoac bo_kiem tang => TRUOT; + moi phut co record
    q2_bad = [l[:23] + " " + l[l.find("phut="):l.find("phut=") + 60] for l in cov_ss if not re.search(r"chua_chot_truoc=0 ", l)]
    bo = grab(cov, "bo_kiem")
    last = now // MN * MN - 3 * MN
    db = kb.AS("103.157.218.242", 3222)
    no_rec = [kb.k7(m) for m in range(last - 59 * MN, last + MN, MN) if db.get(m)[0] is None]
    w, pk, hd, pg, pa = grab(bud, "weight"), grab(bud, "peak60s"), grab(bud, "hdr_max"), grab(bud, "price_gap_max_ms"), grab(bud, "price_age_ms")
    sw = grab([l for l in lines if "OI/LS/taker forward: ghi" in l], "sweep_ms")
    res = dict(ts=datetime.datetime.now().isoformat(timespec="seconds"), mode="hourly", since=since,
               Q1_restart_lines=sum(1 for l in lines if "Restart: Reset" in l), Q1_oom=sum(1 for l in lines if "OutOfMemoryError" in l),
               Q2_cover_lines=len(cov_ss), Q2_bad=len(q2_bad), Q2_ex=q2_bad[:5], Q2_bo_kiem_max=max(bo) if bo else None, Q2_no_record=no_rec,
               Q4_weight_mean=round(sum(w) / len(w), 1) if w else None, Q4_peak_max=max(pk) if pk else None,
               Q4_fdata_peak_max=max(grab(bud, "fdata_peak60s")) if bud else None, Q4_lines=len(w),
               Q5_hdr_max=max(hd) if hd else None, Q6_429_418=sum(grab(bud, "http429")) + sum(grab(bud, "http418")),
               Q6_ban_lines=sum(1 for l in lines if "REST banned" in l or "REST cooldown" in l),
               Q7_price_gap_max=max(pg) if pg else None, Q7_gt5s=sum(1 for x in pg if x > 5000), Q7_price_age_max=max(pa) if pa else None,
               Q7_price_age_warn=sum(1 for l in lines if "[PRICE-AGE]" in l),
               Q8_recon_warn=sum(1 for l in lines if "KLINE-RECON" in l), Q10_supervisor_lines=sum(1 for l in lines if "[SUPERVISOR]" in l),
               O1_sweep_min=[round(x / 60000, 1) for x in sw],
               Q11_sent_banned=max(grab(bud, "sent_banned_total") or [0]),
               Q11_vi_pham_lines=sum(1 for l in lines if "Q11 VI PHAM" in l),
               R_lanh_ngoai_3p=sum(grab(cov, "lanh_ngoai_3p")), R_loop_escalations=max(grab(bud, "loop_escalations") or [0]))
    hard = (res["Q1_restart_lines"] or res["Q1_oom"] or res["Q2_bad"] or (res["Q2_bo_kiem_max"] or 0) > 0 or no_rec
            or (res["Q4_peak_max"] or 0) > 300 or (res["Q4_fdata_peak_max"] or 0) > 150 or res["Q6_429_418"] or res["Q6_ban_lines"]
            or (res["Q7_price_gap_max"] or 0) > 15000 or any(x > 35 for x in res["O1_sweep_min"])
            or res["Q11_sent_banned"] or res["Q11_vi_pham_lines"])
    res["verdict_gio"] = "VI_PHAM" if hard else ("THIEU_SO_DO" if not bud or not cov_ss else "OK")
    return res

def vision(day):
    """Q3: 30 symbol (15 top QV + 15 ngau nhien theo ngay) x 1440 phut ngay UTC `day` so Vision daily klines 1m."""
    d0 = int(datetime.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    db = kb.AS("103.157.218.242", 3222)
    recs = {}
    for m in range(d0, d0 + 1440 * MN, MN):
        r = db.get(m)[0]
        recs[m] = kb.decode(r) if r is not None else None
    ref = recs[d0 + 720 * MN] or {}
    top = sorted(ref, key=lambda s: -ref[s][4])[:15]
    pool = sorted(set(ref) - set(top))
    syms = top + random.Random(day).sample(pool, min(15, len(pool)))
    cells = bad = miss = noviz = 0; ex = []
    for s in syms:
        url = "https://data.binance.vision/data/futures/um/daily/klines/%sUSDT/1m/%sUSDT-1m-%s.zip" % (s, s, day)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
        except Exception:
            noviz += 1; continue
        rows = z.read(z.namelist()[0]).decode().splitlines()
        V = {}
        for row in rows:
            c = row.split(",")
            if not c[0].isdigit(): continue   # bo header
            V[int(c[0])] = (f32(c[1]), f32(c[2]), f32(c[3]), f32(c[4]), f32(c[7]))
        for m, vv in V.items():
            rec = recs.get(m)
            if rec is None or s not in rec:
                miss += 1; continue
            cells += 1
            if not all(ulp(x, y) for x, y in zip(rec[s], vv)):
                bad += 1
                if len(ex) < 8: ex.append("%s@%s" % (s, kb.k7(m)))
        time.sleep(0.2)
    return dict(ts=datetime.datetime.now().isoformat(timespec="seconds"), mode="vision", day=day, symbols=len(syms),
                Q3_cells=cells, Q3_bad=bad, Q3_missing_242=miss, Q3_no_vision=noviz, Q3_ex=ex,
                no_record_minutes=sum(1 for v in recs.values() if v is None),
                verdict="OK" if bad == 0 and miss == 0 and cells > 0 else "VI_PHAM" if bad or miss else "THIEU_SO_DO")

if __name__ == "__main__":
    res = vision(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--vision" else hourly()
    open(OUT, "a").write(json.dumps(res) + "\n")
    print(json.dumps(res))
