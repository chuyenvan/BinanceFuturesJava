# ADDENDUM24_PILOTFID - ERRATA6 (DU THAO DEV vong 3, 2026-11-24, CHUA COMMIT) - commit TRUOC luot chinh thuc R-LIVE #2
Goc: prereg 6ee84f17 + ERRATA1-5. Can cu: v12/RLIVE_RUN_1124.md, v12/rlive_1124_run.log, v12/A1_ADD24_ERRATA6.md (A1 duyet 274f55eb
PASS-WITH-MINOR, neu B1/M1/M2/m1-m5; DELTA VONG 2: U1, rut lai M1), v12/ADD24_ERRATA6_DEV.md (vong 1 + vong 2).
Harness: add24_wt nhanh v1.2/add24-harness, HEAD cu 3e6da6eba28be4aaae1c509e2dca60d4c44a0fd3 -> 274f55eb (vong 1) -> HEAD moi
2671cb769b8bf93cb6096dd2b469533733b4b689 (vong 2) -> HEAD moi
a66109c12220de59ed8d5b065d33d0eb8875d5bf (vong 3, U1). File: tools/add24/rlive/run_rlive.sh, rlive_fixture.py, buf_check.py (moi).
Loai: plumbing + cong fail-closed (dung TRUOC khi cham). Khong noi / doi nguong, nhan, tieu chi nao. A1 phai duyet delta 2671cb76..a66109c12220de59ed8d5b065d33d0eb8875d5bf.

## A. Su kien luot chinh thuc #1 (KHONG CHAM - loi ky thuat truoc khi doc du lieu)
- Bat dau 2026-11-24 09:02:35 +07, ket thuc 09:02:51 +07, EXIT 11. HEAD 3e6da6eb (A1_APPROVED 3e6da6eba28be4aaae1c509e2dca60d4c44a0fd3),
  P1 e451154e (docs/prereg/OWNER_DECISION_PILOT_1121_ADD4.md), EXINFO c3live_exchangeInfo_242_20261122_195538.json.
- Log v12/rlive_1124_run.log sha256 b59141db3ffe035e9d065e1ce3a561c5a856ed5fa4d4c85b551ff681513353d6 (KHONG ghi de).
- Output /dev/shm/add24/rlive_official_1124_090235 RONG (0 file); khong thu muc keep; khong gates/score/conclusion.
- Truoc loi: P1 gate, ghi khoa, build_wt RC=0. Loi o buoc tinh DAYS, TRUOC live_log_parse => KHONG dong log bot, kline, mark nao cua
  OW2 duoc doc; khong lane java nao chay; KHONG tieu chi nao duoc cham.
- Dong khoa (a/OFFICIAL_ADD24_RLIVE.lock, sha256 3956d04f44f670ddf8c4a6a7d8fe4500699d743e432b961b54699537a122f009):
  2026-11-24T09:02:35+07:00 head=3e6da6eb a1=3e6da6eba28be4aaae1c509e2dca60d4c44a0fd3 p1=e451154e errata= exinfo_sha256=dcfa03c72c38a658e7de7df812e876bbca903f9e0dfd81ab02b1aeb61f3a1684 out=/dev/shm/add24/rlive_official_1124_090235

## B. Nguyen nhan + sua
- P1 (nguyen nhan luot #1): `read TCUT TDAY < <(... print(*F.tcut()))`, tcut() tra ('2026-11-24 07:00','2026-11-23') => read tach theo
  dau cach => TCUT='2026-11-24', TDAY='07:00 2026-11-23' => DAYS rong => live_log_parse --days thieu doi so => exit 11.
  Sua: in bang '|' + `IFS='|' read -r`; assert exit 15: TCUT ~ ^2026-11-2[0-4] 07:00$, TDAY ~ ^2026-11-(19|2[0-3])$, TCUT = TDAY+1 07:00,
  DAYS bat dau 2026-11-19 va ket thuc TDAY. Khoi nay (chi kiem file COMPLETE) nay chay TRUOC dong ghi khoa.
- P2: prep_fixture.py (def1f034) doc --exinfo bang gzip.open, EXINFO E-A7 la .json THO => BadGzipFile (exit 12 SAU khi doc log OW2).
  Sua o rlive_fixture.py (KHONG dong prep_fixture): ban sao gz (mtime=0) cho prep; assert byte-identical; assert sha256(fx/exinfo.json)
  == sha256 EXINFO goc. Noi dung exinfo rig/REF dung KHONG doi.
- B1 (A1 BLOCKER-van-hanh): Vision ngay UTC cuoi OW2 chua phat hanh => fetch() 404 => truoc day chi liet ke, fixture hong im lang.
  (i) run_rlive.sh: TRUOC dong ghi khoa, HTTP HEAD klines 1m + markPriceKlines 1m BTCUSDT ngay TDAY (mau URL cua rlive_fixture);
  khac 200 => exit 16, KHONG ghi khoa. (ii) rlive_fixture.py: moi (symbol, ngay UTC) Vision thieu (404 hoac loi mang sau 3 lan) ma
  KHONG giai thich duoc tat dinh tu EXINFO => dung (exit 12) TRUOC prep / lane / cham, ghi <out>_vision_missing.json. Giai thich duoc
  CHI khi: onboardDate >= het ngay UTC do (niem yet sau), hoac status != TRADING va deliveryDate <= dau ngay do (huy niem yet truoc).
  (iii) Plumbing phat hien khi kiem (ii) tren ngay DEV 2026-11-10: 5 symbol PERPETUAL USDT TRADING ten KHONG ASCII trong EXINFO
  (\u54c8\u57fa\u7c73USDT, \u5e01\u5b89\u4eba\u751fUSDT, \u6211\u8e0f\u9a6c\u6765\u4e86USDT, \u725b\u6765USDT, \u9f99\u867eUSDT)
  => urllib UnicodeEncodeError => fetch() tra None. URL nay ma hoa % (urllib.parse.quote - giu, vo hai voi symbol ASCII).
  (iv) U1 (A1 DELTA VONG 2, MASTER quyet LOAI): live KHONG ingest cac symbol nay. Dieu kien live, chep nguyen:
  TickerIngestor2AerospikeNew.java:134 `symbol = obj.getString("symbol").toUpperCase(); symbol.endsWith("USDT") &&
  symbol.matches("^[A-Z0-9]+$") && !Constants.diedSymbol.contains(symbol)`; cung regex o :517 (redis: endsWithIgnoreCase USDT +
  matches + !died) va :557 (repair: matches). rlive_fixture.live_ingest_ok() = toUpperCase + endsWith USDT + fullmatch [A-Z0-9]+
  (diedSymbol do rig tu loai, MarketReplay:107). allsym va cand loc truoc khi tai; danh sach loai ghi manifest_ow2.json
  'excluded_not_live_ingest' (tren EXINFO hien tai: dung 5 symbol tren). => mkt.csv.gz KHONG co 5 symbol nay, = universe ingest live
  (truoc delta chung cung vang mat nhung do loi ngau nhien).
- M1 (A1 MAJOR vong 1) - KET LUAN: KHONG THAT (kiem bang metadata, khong doc gia tri r); A1 da RUT LAI o DELTA VONG 2:
  * Rig (CrashDayRig:255-271) chi nap ban ghi ts < START tu fx/gate_ratio_live.bin (= anh pull --buffer-day 2026-11-19); sau START rig
    tu tinh r va tu cuon buffer; q_h = phan vi tren ban ghi trong [h - 90d, h) (GateRatioBuffer.computeQ). Khong nap anh theo ngay.
  * Persist live append-only (GateRatioPersist; chi viet lai khi seed / chunk hong): moi anh pull242 11-03 -> 11-23 la TIEN TO BYTE cua
    anh sau (19/19 cap; 11-19 vs 11-20 khac chi vi 11-19 chup muon hon - 11-20 la tien to cua 11-19/11-21). Moi anh 11-18..11-23 co
    ban ghi cu nhat 2026-10-01 13:00 => KHONG bi cat dau; cua so 90 ngay o moi phut OW2 (>= 2026-08-21) phu toan bo buffer.
  * Ban ghi ts < START (2026-11-19 09:31): anh 11-19, 11-20, 11-21, 11-22, 11-23 cung 1 606 970 ban ghi, cung sha256 byte.
    Anh 11-18 (chup 19/11 08:23) la tien to byte cua anh 11-19 => de xuat "seed = anh 11-18 + ban ghi [08:23, 09:31) cua anh sau"
    cho DUNG tap ban ghi rig dang dung. => KHONG gio OW2 nao bi anh huong. Dev1105/fx1105 cung tinh chat (ban ghi cu nhat 10-01).
  * Rui ro tiem an tim them: LiveGateRollingRatio.init() cat persist theo DONG HO THAT (System.currentTimeMillis() - 90d), khong theo
    START. Hien vo hai (now - 90d ~ 2026-08-26 < 2026-10-01) nhung se cat seed neu chay sau ~2026-12-29.
  * Cong fail-closed moi (tools/add24/rlive/buf_check.py; run_rlive.sh exit 17, TRUOC cham): pre - ban ghi ts < START cua fx buffer ==
    ban ghi ts < START cua LIVEBUF (anh TDAY): cung so luong + sha256 byte, ts tang, 0 chunk hong, ban ghi cu nhat >= now - 90d + 1 ngay;
    post - moi lane (L0, L0-FOLLOW, L0-DRY, L-10K) result.json buffer_init_records == buffer_after_load == n_pre.
  * Cach da LOAI: (a) hop nhat anh 11-18 + anh muon hon - cho ket qua byte-identical voi hien tai (thua code, them rui ro);
    (b) seed = anh 11-23 cat ts < START - cung byte-identical; (c) ghi gioi han "lech gate do buffer" - khong can vi khong co lech dau vao.

### Diff day du (3e6da6eb..a66109c12220de59ed8d5b065d33d0eb8875d5bf)
```diff
diff --git a/tools/add24/rlive/buf_check.py b/tools/add24/rlive/buf_check.py
new file mode 100644
index 00000000..04963e25
--- /dev/null
+++ b/tools/add24/rlive/buf_check.py
@@ -0,0 +1,83 @@
+#!/usr/bin/env python3
+"""ADD24 R-LIVE [ERRATA6 M1] cong buffer gate fail-closed. CHI dung ts + so sanh BYTE; KHONG in / thong ke gia tri r.
+Can cu: persist live (GateRatioPersist) append-only - moi anh pull242/<D>/run/gate_ratio_live.bin.gz la tien to byte cua anh sau
+(kiem 11-03..11-23); rig (CrashDayRig:255-271) nap ban ghi ts < START cua fixture, init() production cat theo dong ho THAT (now - DAYS).
+pre : ban ghi ts < START cua buffer fixture == ban ghi ts < START cua anh live muon nhat (LIVEBUF): cung so luong, cung sha256 byte (ts,r);
+      ts tang dan; 0 chunk hong; ban ghi cu nhat >= now - DAYS + 1 ngay (khong ban ghi nao bi init() cat theo dong ho that).
+post: moi lane: result.json buffer_init_records == buffer_after_load == n_pre cua buoc pre.
+usage: buf_check.py pre --fx-buf F --live-buf G --start 'YYYY-MM-DD HH:MM' --out J [--days 90]
+       buf_check.py post --pre J --lanes DIR1,DIR2,...
+exit 0 = dat; 3 = truot (run_rlive => exit 17, KHONG cham)."""
+import argparse, gzip, hashlib, json, os, struct, sys, time
+from datetime import datetime, timedelta, timezone
+
+MAGIC = 0x47525231
+DAY = 86400000
+TZ7 = timezone(timedelta(hours=7))
+
+
+def raw_records(p):
+    """Bytes ban ghi (12 B: ts>q + r>f) noi tiep theo thu tu file + so chunk hong (dung la 0)."""
+    import snappy
+    b = (gzip.open(p, 'rb') if p.endswith('.gz') else open(p, 'rb')).read()
+    i, out, bad = 0, [], 0
+    while i + 12 <= len(b):
+        m, n, _ = struct.unpack('>iii', b[i:i + 12])
+        if m != MAGIC or n < 0 or i + 12 + n > len(b):
+            bad += 1
+            break
+        raw = snappy.uncompress(b[i + 12:i + 12 + n])
+        out.append(raw[:len(raw) - len(raw) % 12])
+        i += 12 + n
+    if i != len(b):
+        bad += 1
+    return b''.join(out), bad
+
+
+def pre_part(p, start):
+    raw, bad = raw_records(p)
+    n, last, mono, first = 0, None, True, None
+    for (t,) in struct.iter_unpack('>q', b''.join(raw[k:k + 8] for k in range(0, len(raw), 12))):
+        if first is None:
+            first = t
+        if last is not None and t < last:
+            mono = False
+        last = t
+        if t < start:
+            n += 1
+    seg = raw[:n * 12]
+    return {'file': p, 'n_all': len(raw) // 12, 'n_pre': n, 'sha256_pre': hashlib.sha256(seg).hexdigest(), 'bad_chunks': bad,
+            'monotone': mono, 'min_ts': first}
+
+
+def main():
+    ap = argparse.ArgumentParser()
+    ap.add_argument('mode', choices=['pre', 'post'])
+    ap.add_argument('--fx-buf'); ap.add_argument('--live-buf'); ap.add_argument('--start'); ap.add_argument('--out')
+    ap.add_argument('--days', type=int, default=90); ap.add_argument('--pre'); ap.add_argument('--lanes', default='')
+    ap.add_argument('--now-ms', type=int, default=0, help='CHI test')
+    a = ap.parse_args()
+    if a.mode == 'pre':
+        S = int(datetime.strptime(a.start, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
+        fx, lv = pre_part(a.fx_buf, S), pre_part(a.live_buf, S)
+        now = a.now_ms or int(time.time() * 1000)
+        chk = {'same_n_pre': fx['n_pre'] == lv['n_pre'] and fx['n_pre'] > 0, 'same_sha_pre': fx['sha256_pre'] == lv['sha256_pre'],
+               'no_bad_chunk': fx['bad_chunks'] == 0 and lv['bad_chunks'] == 0, 'monotone': fx['monotone'] and lv['monotone'],
+               'no_wallclock_trim': fx['min_ts'] is not None and fx['min_ts'] >= now - a.days * DAY + DAY}
+        res = {'start': S, 'days': a.days, 'now_ms': now, 'fx': fx, 'live': lv, 'checks': chk, 'ok': all(chk.values())}
+        json.dump(res, open(a.out, 'w'), indent=1)
+    else:
+        pre = json.load(open(a.pre))
+        n = pre['fx']['n_pre']
+        lanes = {}
+        for d in [x for x in a.lanes.split(',') if x]:
+            r = json.load(open(os.path.join(d, 'result.json')))
+            lanes[d] = {'buffer_init_records': r.get('buffer_init_records'), 'buffer_after_load': r.get('buffer_after_load')}
+            lanes[d]['ok'] = lanes[d]['buffer_init_records'] == lanes[d]['buffer_after_load'] == n
+        res = {'n_pre': n, 'pre_ok': bool(pre.get('ok')), 'lanes': lanes, 'ok': bool(pre.get('ok')) and bool(lanes) and all(v['ok'] for v in lanes.values())}
+    print(json.dumps({'mode': a.mode, 'ok': res['ok'], 'checks': res.get('checks'), 'lanes': {k: v['ok'] for k, v in res.get('lanes', {}).items()}}))
+    return 0 if res['ok'] else 3
+
+
+if __name__ == '__main__':
+    sys.exit(main())
diff --git a/tools/add24/rlive/rlive_fixture.py b/tools/add24/rlive/rlive_fixture.py
index 3b7c7d32..9906373d 100644
--- a/tools/add24/rlive/rlive_fixture.py
+++ b/tools/add24/rlive/rlive_fixture.py
@@ -7,7 +7,7 @@
 4) mark.csv.gz (symbol,t,o,h,l,c) tu markPriceKlines; manifest_ow2.json (sha256 moi dau vao, V1).
 usage: rlive_fixture.py --out /dev/shm/add24/fx_ow2 --live <parse dir> --exinfo <json.gz> [--tcut-override 'YYYY-MM-DD HH:MM' (chi errata)]
 """
-import argparse, csv, glob, gzip, hashlib, io, json, logging, os, sys, time, urllib.request, zipfile
+import argparse, csv, glob, gzip, hashlib, io, json, logging, os, re, sys, time, urllib.parse, urllib.request, zipfile
 from datetime import datetime, timedelta, timezone
 
 H = os.path.dirname(os.path.abspath(__file__))
@@ -33,6 +33,42 @@ def tcut():
     return d.strftime('%Y-%m-%d') + ' 07:00', days[-1]
 
 
+def exinfo_gz(src, dst):
+    """[ERRATA6 P2] prep_fixture.py (def1f034) doc --exinfo bang gzip.open; EXINFO (ERRATA1 E-A7) la .json THO => nen ban sao
+    (mtime=0) cho prep; noi dung giai nen = NGUYEN BYTE goc (assert). Tra (duong dan cho prep, sha256 goc)."""
+    raw = open(src, 'rb').read()
+    sha = hashlib.sha256(raw).hexdigest()
+    if raw[:2] == b'\x1f\x8b':
+        return src, hashlib.sha256(gzip.decompress(raw)).hexdigest()
+    with open(dst, 'wb') as fh, gzip.GzipFile(filename='', mode='wb', fileobj=fh, mtime=0) as fo:
+        fo.write(raw)
+    if gzip.open(dst, 'rb').read() != raw:
+        raise SystemExit('TU CHOI (ERRATA6): ban gzip exinfo khac nguyen ban')
+    return dst, sha
+
+
+def live_ingest_ok(sym):
+    """[ERRATA6 U1] CHEP NGUYEN dieu kien ingest live TickerIngestor2AerospikeNew.java:134 (symbol = getString("symbol").toUpperCase();
+    symbol.endsWith("USDT") && symbol.matches("^[A-Z0-9]+$") && !Constants.diedSymbol.contains(symbol)); cung regex o :517, :557.
+    diedSymbol KHONG ap o day: rig tu loai (MarketReplay:107, Constants.diedSymbol production)."""
+    u = sym.upper()
+    return u.endswith('USDT') and re.fullmatch('[A-Z0-9]+', u) is not None
+
+
+def onboard_map(ex):
+    """[ERRATA6 B1] symbol -> (onboardDate, deliveryDate, status) tu EXINFO (0 = khong co)."""
+    return {x['symbol']: (int(x.get('onboardDate') or 0), int(x.get('deliveryDate') or 0), x.get('status')) for x in ex.get('symbols', [])}
+
+
+def vision_explained(item, onb):
+    """[ERRATA6 B1] 'SYM@YYYY-MM-DD' (ngay UTC) thieu tren Vision la GIAI THICH DUOC (tat dinh, chi tu EXINFO) khi: symbol niem yet
+    (onboardDate) SAU khi ngay do ket thuc, hoac symbol khong TRADING va deliveryDate <= dau ngay do (huy niem yet truoc ngay)."""
+    s, d = item.rsplit('@', 1)
+    d0 = int(datetime.strptime(d, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000); d1 = d0 + 86400000
+    o, dl, st = onb.get(s, (0, 0, None))
+    return bool((o and o >= d1) or (st is not None and st != 'TRADING' and dl and dl <= d0))
+
+
 def ms7(s):
     return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
 
@@ -42,7 +78,8 @@ def fetch(kind, sym, day, root):
     if os.path.exists(p):
         return p
     os.makedirs(os.path.dirname(p), exist_ok=True)
-    url = '%s/%s/%s/1m/%s-1m-%s.zip' % (VBASE, kind, sym, sym, day)
+    q = urllib.parse.quote(sym)   # [ERRATA6 B1] symbol khong ASCII (5 symbol TRADING trong EXINFO) => URL ma hoa %, truoc day loi im lang
+    url = '%s/%s/%s/1m/%s-1m-%s.zip' % (VBASE, kind, q, q, day)
     for i in range(3):
         try:
             with urllib.request.urlopen(url, timeout=60) as r:
@@ -66,6 +103,7 @@ def main():
     if not a.out.startswith('/dev/shm/add24/'):
         raise SystemExit('TU CHOI: fixture chi o /dev/shm/add24')
     end, dcomp = (a.tcut_override, 'override') if a.tcut_override else tcut()
+    exi, exsha = exinfo_gz(a.exinfo, a.out.rstrip('/') + '_exinfo.json.gz')
     S, E = ms7(OW2_START), ms7(end)
     vroot = '/dev/shm/add24/vision'
     d0 = datetime.fromtimestamp(S / 1000, timezone.utc).date(); d1 = datetime.fromtimestamp((E - 1) / 1000, timezone.utc).date()
@@ -87,6 +125,9 @@ def main():
     ex = json.load(gzip.open(a.exinfo, 'rt') if a.exinfo.endswith('.gz') else open(a.exinfo))
     allsym |= {x['symbol'] for x in ex.get('symbols', []) if x.get('contractType') == 'PERPETUAL' and x.get('quoteAsset') == 'USDT'
                and x.get('status') == 'TRADING'}
+    # [ERRATA6 U1] universe rig = universe ingest live: symbol live khong ingest (vd 5 symbol ten khong ASCII) => LOAI, khong tai
+    noingest = sorted(x for x in allsym | cand if not live_ingest_ok(x))
+    allsym -= set(noingest); cand -= set(noingest)
     miss = {'klines': [], 'markPriceKlines': []}
     for s in sorted(allsym):
         for d in udays:
@@ -96,10 +137,20 @@ def main():
         for d in udays:
             if not fetch('markPriceKlines', s, d, vroot):
                 miss['markPriceKlines'].append(s + '@' + d)
+    # [ERRATA6 B1] Vision thieu (404 / loi mang sau 3 lan) ma KHONG giai thich duoc tu EXINFO => DUNG truoc prep / lane / cham
+    onb = onboard_map(ex)
+    unexp = {k: [x for x in v if not vision_explained(x, onb)] for k, v in miss.items()}
+    if any(unexp.values()):
+        jf = a.out.rstrip('/') + '_vision_missing.json'
+        json.dump({'missing': miss, 'unexplained': unexp}, open(jf, 'w'), indent=1)
+        raise SystemExit('TU CHOI (ERRATA6 B1): Vision thieu khong giai thich: klines %d markPriceKlines %d (%s)'
+                         % (len(unexp['klines']), len(unexp['markPriceKlines']), jf))
     import prep_fixture as P
     P.VIS = vroot + '/klines'
-    sys.argv = ['prep_fixture.py', '--out', a.out, '--start', OW2_START, '--end', end, '--buffer-day', '2026-11-19', '--exinfo', a.exinfo]
+    sys.argv = ['prep_fixture.py', '--out', a.out, '--start', OW2_START, '--end', end, '--buffer-day', '2026-11-19', '--exinfo', exi]
     P.main()
+    if hashlib.sha256(open(a.out + '/exinfo.json', 'rb').read()).hexdigest() != exsha:
+        raise SystemExit('TU CHOI (ERRATA6): fx/exinfo.json khac sha256 EXINFO goc')
     n = 0
     with gzip.open(a.out + '/mark.csv.gz', 'wt') as fo:
         w = csv.writer(fo, lineterminator='\n'); w.writerow(['symbol', 't', 'o', 'h', 'l', 'c'])
@@ -113,7 +164,8 @@ def main():
                         if x and x[0][:1].isdigit() and S - 5 * 60000 <= int(x[0]) < E:
                             w.writerow([s, int(x[0]), x[1], x[2], x[3], x[4]]); n += 1
     man = {'p1': why, 'START': S, 'END': E, 'tcut': end, 'tcut_from_complete_day': dcomp, 'udays': udays, 'symbols_klines': len(allsym),
-           'symbols_mark': len(cand) + 1, 'mark_rows': n, 'missing': miss,
+           'exinfo_src': a.exinfo, 'exinfo_src_sha256': exsha, 'exinfo_passed_to_prep': exi,
+           'symbols_mark': len(cand) + 1, 'mark_rows': n, 'missing': miss, 'missing_unexplained': unexp, 'excluded_not_live_ingest': noingest,
            'sha256': {f: hashlib.sha256(open(os.path.join(a.out, f), 'rb').read()).hexdigest() for f in sorted(os.listdir(a.out))}}
     json.dump(man, open(a.out + '/manifest_ow2.json', 'w'), indent=1)
     log.info('fixture OW2 xong tcut=%s miss_k=%d miss_m=%d', end, len(miss['klines']), len(miss['markPriceKlines']))
diff --git a/tools/add24/rlive/run_rlive.sh b/tools/add24/rlive/run_rlive.sh
index d66e8679..402f9d0e 100755
--- a/tools/add24/rlive/run_rlive.sh
+++ b/tools/add24/rlive/run_rlive.sh
@@ -25,19 +25,34 @@ if [ "$MODE" = official ]; then
   [ -z "$(git -C $W status --porcelain --untracked-files=no)" ] || { echo "TU CHOI: worktree co thay doi chua commit"; exit 2; }
   python3 -c "import sys; sys.path.insert(0,'$T'); import p1_gate; print(p1_gate.require_p1())" || exit 2
   [ -n "${EXINFO:-}" ] && [ -f "$EXINFO" ] || { echo "TU CHOI: thieu EXINFO (ERRATA1 E-A7)"; exit 2; }
+  # [ERRATA6 P1] T_cut co dau cach => in bang '|' + assert fail-closed (exit 15); [ERRATA6 B1] tinh TRUOC dong ghi khoa (chi kiem COMPLETE)
+  IFS='|' read -r TCUT TDAY < <(python3 -c "import sys; sys.path.insert(0,'$T'); import rlive_fixture as F; print('|'.join(F.tcut()))")
+  [[ "${TCUT:-}" =~ ^2026-11-2[0-4]\ 07:00$ ]] || { echo "TU CHOI (ERRATA6): TCUT='${TCUT:-}' sai dang"; exit 15; }
+  [[ "${TDAY:-}" =~ ^2026-11-(19|2[0-3])$ ]] || { echo "TU CHOI (ERRATA6): TDAY='${TDAY:-}' sai dang"; exit 15; }
+  [ "$(date -d "$TDAY +1 day" +%F) 07:00" = "$TCUT" ] || { echo "TU CHOI (ERRATA6): TCUT $TCUT != TDAY $TDAY + 1 ngay 07:00"; exit 15; }
+  START='2026-11-19 09:31'; END="$TCUT"; CAP=1000; FLAGS=on; APPLY=on
+  DAYS=$(python3 -c "
+from datetime import date,timedelta; d=date(2026,11,19); e=date.fromisoformat('$TDAY'); print(','.join(str(d+timedelta(i)) for i in range((e-d).days+1)))")
+  case "${DAYS:-}" in 2026-11-19*) ;; *) echo "TU CHOI (ERRATA6): DAYS='${DAYS:-}' khong bat dau 2026-11-19"; exit 15;; esac
+  case "$DAYS" in *"$TDAY") ;; *) echo "TU CHOI (ERRATA6): DAYS='$DAYS' khong ket thuc $TDAY"; exit 15;; esac
+  echo "ERRATA6 TCUT=$TCUT TDAY=$TDAY DAYS=$DAYS"
+  # [ERRATA6 B1] Vision ngay UTC cuoi OW2 (= TDAY) phai da phat hanh (HTTP HEAD, khong tai) - khong => exit 16, KHONG ghi khoa
+  VB=https://data.binance.vision/data/futures/um/daily
+  for KD in klines markPriceKlines; do
+    HC=$(curl -s -o /dev/null -I -w '%{http_code}' --max-time 30 "$VB/$KD/BTCUSDT/1m/BTCUSDT-1m-$TDAY.zip")
+    [ "$HC" = 200 ] || { echo "TU CHOI (ERRATA6 B1): Vision chua phat hanh $KD BTCUSDT $TDAY (HTTP $HC) - KHONG ghi khoa"; exit 16; }
+  done
   LOCK=$A/OFFICIAL_ADD24_RLIVE.lock
   [ -e $LOCK ] && [ -z "${E2E_ERRATA:-}" ] && { echo "TU CHOI: da chay chinh thuc (khoa $LOCK); mo lai CHI voi E2E_ERRATA moi"; exit 2; }
   [ -n "${E2E_ERRATA:-}" ] && grep -q "errata=${E2E_ERRATA} " $LOCK 2>/dev/null && { echo "TU CHOI: errata da dung"; exit 2; }
   echo "$(date -Is) head=$HEAD a1=$A1_APPROVED p1=$ADD24_P1_APPROVED errata=${E2E_ERRATA:-} exinfo_sha256=$(sha256sum < $EXINFO | cut -c1-64) out=$OUT " >> $LOCK
   bash $T/../build_wt.sh || { echo "TU CHOI: build test-classes"; exit 9; }
-  read TCUT TDAY < <(python3 -c "import sys; sys.path.insert(0,'$T'); import rlive_fixture as F; print(*F.tcut())")
-  START='2026-11-19 09:31'; END="$TCUT"; CAP=1000; FLAGS=on; APPLY=on
-  DAYS=$(python3 -c "
-from datetime import date,timedelta; d=date(2026,11,19); e=date.fromisoformat('$TDAY'); print(','.join(str(d+timedelta(i)) for i in range((e-d).days+1)))")
   LIVEBUF=$HOME/claude_master/pull242/$TDAY/run/gate_ratio_live.bin.gz
   python3 -I $T/live_log_parse.py --days $DAYS --start "$START" --end "$END" --out $OUT/live --mode full || exit 11
   python3 $T/rlive_fixture.py --out $OUT/fx --live $OUT/live --exinfo $EXINFO || exit 12
   FX=$OUT/fx; MARK="--mark $FX/mark.csv.gz"; export E2E_OFFICIAL=1
+  # [ERRATA6 M1] buffer seed cua rig (ts < START) == dung ban ghi live co truoc START (anh LIVEBUF), khong bi init() cat theo dong ho that
+  python3 $T/buf_check.py pre --fx-buf $FX/gate_ratio_live.bin --live-buf $LIVEBUF --start "$START" --out $OUT/buf_pre.json || { echo "TU CHOI (ERRATA6 M1): buffer seed"; exit 17; }
   L0N=L0; L0LANE=(FAKE $CAP $FLAGS)
 else
   START='2026-11-05 07:00'; END='2026-11-14 07:00'; CAP=10000; FLAGS=off; APPLY=off
@@ -71,6 +86,9 @@ $H $LANE $L0N ${L0LANE[@]} $BLK | tee -a $OUT/run_all.txt
 $H $LANE L0-FOLLOW FAKE $CAP $FLAGS $BLK E2E_FOLLOW_FILLS=$OUT/live/follow.csv | tee -a $OUT/run_all.txt
 [ "$MODE" = official ] && $H $LANE L0-DRY DRY $CAP $FLAGS $BLK | tee -a $OUT/run_all.txt
 [ "$MODE" = official ] && $H $LANE L-10K FAKE 10000 $FLAGS $BLK | tee -a $OUT/run_all.txt
+if [ "$MODE" = official ]; then   # [ERRATA6 M1] moi lane nap du seed (khong cat)
+  python3 $T/buf_check.py post --pre $OUT/buf_pre.json --lanes $OUT/$L0N,$OUT/L0-FOLLOW,$OUT/L0-DRY,$OUT/L-10K > $OUT/buf_post.txt 2>&1 || { cat $OUT/buf_post.txt; echo "TU CHOI (ERRATA6 M1): buffer lane"; exit 17; }
+fi
 LANES=$L0N,L0-FOLLOW; [ "$MODE" = official ] && LANES=$LANES,L0-DRY
 python3 $T/v10_buffer.py --rig $OUT/$L0N --live $OUT/live --live-buffer $LIVEBUF --start "$START" --end "$END" --cap $CAP --out $OUT/V10.json > $OUT/v10.txt 2>&1
 python3 $T/rlive_gates.py --out-dir $OUT --fx $FX --live $OUT/live --start "$START" --end "$END" --v4-grep "$V4" --lanes $LANES --v8-lane $L0N \
@@ -90,7 +108,7 @@ if [ "$MODE" = official ]; then
 fi
 python3 $T/conclude.py --gates $OUT/gates.json --score $OUT/score_L0/score.json $DRYS --c0b $A/C0B.json ${RSIM_JSON:+--rsim $RSIM_JSON} --out $OUT/conclusion.json
 K=$A/rlive_${MODE}_$TS; mkdir -p $K
-cp -r $OUT/score_L0* $OUT/gates.json $OUT/gates.txt $OUT/V8.json $OUT/V10.json $OUT/v4b.json $OUT/conclusion.json $OUT/run_all.txt $K/ 2>/dev/null
+cp -r $OUT/score_L0* $OUT/gates.json $OUT/gates.txt $OUT/V8.json $OUT/V10.json $OUT/v4b.json $OUT/conclusion.json $OUT/run_all.txt $OUT/buf_pre.json $OUT/buf_post.txt $K/ 2>/dev/null
 cp $OUT/live/counts.json $K/live_counts.json
 for L in ${LANES//,/ } L-10K; do [ -d $OUT/$L ] && python3 $T/sanitize.py $OUT/$L $K/$L; done
 echo "R-LIVE $MODE xong head=$HEAD out=$OUT keep=$K gates_rc=$GRC"
```

## C. KHONG doi
Nguong, nhan, cua so OW2 (2026-11-19 09:31 -> T_cut), T_cut (2026-11-24 07:00 +07 theo pull 2026-11-23 COMPLETE; fallback giu nguyen),
dau vao (EXINFO sha256 dcfa03c72c38a658e7de7df812e876bbca903f9e0dfd81ab02b1aeb61f3a1684 byte-identical vao rig; buffer seed byte-identical
nhu truoc), jar stub (md5 cf0f479241265de68836716ee66a1866), env whitelist / override, lane, logic cham (rlive_gates / rlive_score /
v10_buffer / conclude / v4b / live_log_parse / prep_fixture KHONG doi 1 dong). Universe thi truong cua rig = universe ingest live (U1: 5 symbol khong khop ^[A-Z0-9]+$ bi LOAI, liet ke trong manifest_ow2.json).
Nhanh dev1105: chi them 2 file vao danh sach cp (2>/dev/null), cac buoc moi deu trong
`if official`.

## D. Quy tac chay lai
- Luot #2: E2E_ERRATA=E6, A1_APPROVED=<HEAD A1 duyet delta 2671cb76..a66109c1>, ADD24_P1_APPROVED=e451154e, cung EXINFO,
  E2E_OFFICIAL_LOCK=a/OFFICIAL_ADD24_RLIVE.lock (metadata). Chay bang w3/add24/run_rlive_e6.sh <HEAD> (preflight) roi
  run_rlive_e6.sh <HEAD> go. Log luot #2 = FILE MOI v12/rlive_1124_run2.log. KHONG boc flock. Tranh trung gio watcher parity (m5).
- Dieu kien tien quyet (run_rlive_e6.sh kiem, truot => khong chay): errata nay commit vao vz_e1_wt va nhac HEAD; Vision HEAD DAY DU
  (khong tai) moi symbol PERPETUAL USDT TRADING cua EXINFO khop ingest live (517) + BTCUSDT x {klines 1m, markPriceKlines 1m} x moi
  ngay UTC OW2 (2026-11-19..11-23) = 5 170 request: moi non-200 phai giai thich duoc bang onboardDate/deliveryDate; import python cua
  cac buoc official (snappy, numpy, grr_lib - chi o ~/.local, cac buoc nay goi python3 KHONG -I; live_log_parse goi -I chi dung stdlib);
  /dev/shm/add24/vision KHONG ton tai (fetch dung lai file cache khong kiem, prep glob moi zip vao mkt); oracle_heavy.lock ranh (kiem
  lai ngay truoc nohup); canh bao neu watcher parity watch_daily_v12.sh dang song. Gioi han: symbol chi co trong sel_dump OW2 (khong
  TRADING trong EXINFO) khong duoc preflight kiem (khong doc sel_dump truoc luot) - neu thieu Vision => exit 12 SAU khoa.
- Thoat TRUOC dong ghi khoa (exit 2, 8, 9 stub, 15, 16) = KHONG tinh la mot luot (khoa khong co dong errata=E6), duoc chay lai sau khi
  sua nguyen nhan van hanh (khong doi code). Moi loi SAU khi dong "errata=E6" da ghi (exit 9 build, 11, 12, 13 do loi ky thuat - vd lane
  khong chay vi flock het han / java crash / traceback, 17) = luot #2 HONG KY THUAT => DUNG; MASTER trinh owner TRUOC moi luot tiep.
- Bao cao CA HAI luot: luot #1 "KHONG CHAM - loi ky thuat truoc khi doc du lieu" (muc A); luot #2 la luot cham.
- M2 (A1): exit 14 cua run_rlive.sh la nhanh chet (rlive_gates.py:121 gop V10a vao ok => exit 13). KHONG doi code. Quy tac: exit 13 ma
  trong $OUT/gates.json tap {k : gates[k] la dict co 'ok' va gates[k]['ok'] == false} == {'V10a'} (may kiem:
  python3 -c "import json,sys; g=json.load(open(sys.argv[1])); b=sorted(k for k,v in g.items() if isinstance(v,dict) and 'ok' in v and not v['ok']); sys.exit(0 if b==['V10a'] else 1)" $OUT/gates.json)
  => ap ERRATA5 B(ii): A1 phan xu tu $OUT/V10.json + $OUT/V10_diag.json (trong /dev/shm - GIU, chep ve a/ truoc moi viec khac),
  chay lai toi da 1 lan, tinh RIENG voi quy tac luot hong ky thuat o tren. Exit 13 voi cong khac truot => thu tuc cong V (errata dau vao).

## E. Danh sach van de vong ERRATA6
- P1, P2 (sua, muc B). B1 (sua: preflight truoc khoa + fail-closed fixture + URL ma hoa). U1 (sua: loc theo dieu kien ingest live).
- M1: A1 neu o vong 1, DEV phan bac (metadata: append-only, khong cat dau, ts < START trung byte), A1 rut lai - khong thay doi code
  ngoai cong buf_check (exit 17).
- M2: khong sua code; quy tac may kiem o muc D. m1-m3: muc D. m4 dia sat nguong (exit 8 truoc khoa, vo hai). m5 watcher: preflight
  canh bao + kiem lock ngay truoc khi chay.
- Chi BAO CAO (khong sua, MASTER/A1 xem): so bo loc universe market level live vs rig - live (DetectEntrySignal2TradeNormal:270-300)
  bo diedSymbol, !isTickerAvailable, SimpleSymbolMapper.isQuarantined, big dump/pump, va (c3Idx) TradFi cho rateDown/Up; rig
  (MarketReplay:105-115) bo diedSymbol, a1Excluded (TradFi/INDEX/PREMARKET, CrashDayRig:899-905), isTickerAvailable, dump/pump - KHONG
  co isQuarantined. Fixture chi tai PERPETUAL+USDT+TRADING: live ingest con 245 TRADIFI_PERPETUAL (rig/live deu loai TradFi khoi
  market level) va 137 symbol SETTLING/PENDING (live chi tinh neu ticker con "available") - khong tai trong fixture.
