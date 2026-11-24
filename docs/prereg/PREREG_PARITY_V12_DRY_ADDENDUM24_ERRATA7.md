# ADDENDUM24_PILOTFID - ERRATA7 (DU THAO DEV, 2026-11-24, CHUA COMMIT) - commit TRUOC luot chinh thuc R-LIVE #3 (LAN CHAY LAI CUOI)
Goc: prereg 6ee84f17 + ERRATA1-6 (ERRATA6 = 70d2840d). Can cu: v12/RLIVE_RUN2_1124.md (bao cao luot #2), v12/A1_RLIVE_RUN2_1124.md
(phan xu A1: 3 cong V truot deu loai X = bo kiem sai so voi prereg, 0 bang chung loai Z), quyet dinh MASTER cho V10a (phuong an CHAT),
v12/ADD24_ERRATA7_DEV.md (DEV).
Harness: add24_wt nhanh v1.2/add24-harness, HEAD cu a66109c12220de59ed8d5b065d33d0eb8875d5bf -> HEAD moi
8d397ce2dbbdf3db72da9dd7bb4399866c675911. File: tools/add24/rlive/rlive_gates.py, live_log_parse.py, v10_buffer.py,
tests/run_tests.sh, tests/test_errata7.py (moi).
Loai: sua 3 CONG KIEM CHUNG (V4b, V6, V10a) cho dung prereg / quyet dinh MASTER. KHONG doi nguong, nhan, tieu chi, logic CHAM.
A1 phai duyet delta a66109c1..8d397ce2 truoc luot #3.

## A. Su kien luot chinh thuc #2 (KHONG CHAM - cong V truot, exit 13)
- Bat dau 2026-11-24 18:04:53 +07, ket thuc 18:15:33 +07, EXIT 13. HEAD a66109c1 (A1_APPROVED a66109c12220de59ed8d5b065d33d0eb8875d5bf),
  P1 e451154e, E2E_ERRATA=E6, EXINFO c3live_exchangeInfo_242_20261122_195538.json (sha256 dcfa03c7...1684).
- Dong khoa (a/OFFICIAL_ADD24_RLIVE.lock, sha256 sau ghi 9e1cd8973c4b659347df05109710ab392e7a81c9f58f68ce155c5a49d7aca0dd):
  2026-11-24T18:04:54+07:00 head=a66109c1 a1=a66109c12220de59ed8d5b065d33d0eb8875d5bf p1=e451154e errata=E6 exinfo_sha256=dcfa03c72c38a658e7de7df812e876bbca903f9e0dfd81ab02b1aeb61f3a1684 out=/dev/shm/add24/rlive_official_1124_180454
- Log v12/rlive_1124_run2.log sha256 dcc07f473e95c260e0076058cd358337d24e874ca5b19c89d693886edb1ff6a3.
- Dien bien: build_wt RC=0; live_log_parse OK; fixture OW2 tcut=2026-11-24 07:00 miss_k=0 miss_m=0; buf_check pre/post ok; 4 lane
  (L0, L0-FOLLOW, L0-DRY, L-10K) RC=0; gates {"V1": true, "V2": true, "V3": true, "V4": true, "V4b": false, "V5": true, "V6": false,
  "V7": true, "V8": true, "V10a": false, "ok": false} => exit 13 TRUOC rlive_score / conclude => KHONG co score / conclusion.
- Output SAO LUU: v12/rlive_run2_backup_1124/rlive_official_1124_180454/ (165 file, danh sach sha256 v12/rlive_run2_backup_1124.sha256,
  sha256 cua chinh danh sach = c9713177c0e4227f2f5c2ab6a878108618b8a342b14b7c7ab7e865b9cac27ddf); gates.json 562e6792...b57c8,
  V10.json 45cb089c0d92bb23171dcca03c479a891c2183f21c5aa3d911fc0eefee1cafb4, v4b.json bab16969...107f.

## B. Phan xu A1 tung cong + sua
- V6 (X): rlive_gates.py:98 dat expect = do dai cua so (7049) thay vi so phut CO INPUT (prereg s11 "so phut xu ly == so phut input";
  s5 / s8 N1: phut khong co sel_dump = NO_INPUT; s9.2). Hut 276 = 275 phut N1 (JVM live khong chay, 0 sel_dump) + 1 phut cuoi (E-A11).
  Sua: expect = so ts phan biet cua fx/sel.csv.gz trong [START, END); GIU luat E-A11 (minutes in {expect, expect-1}) va 0 exception.
  Them vao output V6 moi lane: expect_window (do dai cua so), n_N1 (= expect_window - expect), n_last (= expect - minutes).
- V4b (X): live_log_parse.py thieu quy tac cho dong log production C3MainEquity.java:218 (jar 76134a52)
  `[C3-LIVE-EQ] doc income FUNDING_FEE loi {} => thu lai sau {} s` (dang "[C9-LIVE-EQ] ..." trong v4b.json la do shape() thay so -> 9).
  Sua: them quy tac EQ_INCOME_ERR vao RULES ngay sau FUNDING (tag '[C3-LIVE-EQ] doc income FUNDING_FEE loi', regex cung chuoi, khong cot,
  nguon C3MainEquity:218). CHI dem (eq_income_err.csv), KHONG dung cho cham; KHONG dua vao danh sach info (INFO_RX khong doi).
- V10a (X o tang dinh nghia cong; quyet dinh MASTER phuong an CHAT, muc D): (a) 554 phut: live dang GIU symbol ma rig khong giu =>
  rig ghi them ban ghi cua symbol do; o ca 554 phut multiset r live la tap con bit-exact cua rig. (b) 1 phut bien 2026-11-24 06:59
  (rig khong decide nen END-1'). Sua: (i) dieu kien dat cua phut theo muc D; (ii) bo nen END-1' ca hai phia (v10_buffer.py:39,50,
  va trace_dec cho nhat quan) - cung co che E-A11.

### Diff day du (a66109c12220de59ed8d5b065d33d0eb8875d5bf..8d397ce2dbbdf3db72da9dd7bb4399866c675911)
```diff
diff --git a/tools/add24/rlive/live_log_parse.py b/tools/add24/rlive/live_log_parse.py
index c77b656c..aba58bb8 100644
--- a/tools/add24/rlive/live_log_parse.py
+++ b/tools/add24/rlive/live_log_parse.py
@@ -75,6 +75,8 @@ RULES = [
     ('EQ_ACCOUNT', ('[C3-LIVE-EQ] account() loi',), r'\[C3-LIVE-EQ\] account\(\) loi', '', 'C3MainEquity:199'),
     ('EQ_KYQUY', ('[C3-LIVE-EQ] CANH BAO ky quy',), r'\[C3-LIVE-EQ\] CANH BAO ky quy', '', 'C3MainEquity:174 (K7)'),
     ('FUNDING', ('[C3-LIVE-EQ] funding c3',), r'\[C3-LIVE-EQ\] funding c3 (\S+) \((\d+) dong\) => cong don (\S+)', 'add,n,cum', 'C3MainEquity:247'),
+    # [ERRATA7 V4b] loi doc income => thu lai lan poll sau (khong mat funding, chi tre <= FUNDING_POLL_MS); CHI dem, khong dung cho cham
+    ('EQ_INCOME_ERR', ('[C3-LIVE-EQ] doc income FUNDING_FEE loi',), r'\[C3-LIVE-EQ\] doc income FUNDING_FEE loi', '', 'C3MainEquity:218'),
     ('KHAN', ('KHAN',), r'KHAN', '', 'alerts'),
     ('KS_LATCH', ('[KILLSW]', 'LATCH'), r'\[KILLSW\].*LATCH', '', 'OpsHooks'),
 ]
diff --git a/tools/add24/rlive/rlive_gates.py b/tools/add24/rlive/rlive_gates.py
index 8517ca07..6fdabf18 100644
--- a/tools/add24/rlive/rlive_gates.py
+++ b/tools/add24/rlive/rlive_gates.py
@@ -26,6 +26,14 @@ def ms7(s):
     return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
 
 
+def v6_lane(minutes, errors, n_sel, n_window):
+    """[ERRATA7 V6] expect = n_sel (phut co input); dat khi minutes in {expect, expect-1} (E-A11 phut cuoi) va 0 exception.
+    expect_window = do dai cua so; n_N1 = phut khong co sel (N1); n_last = expect - minutes (0 hoac 1 khi dat)."""
+    ok = minutes is not None and minutes in (n_sel, n_sel - 1) and errors == 0
+    return {'minutes': minutes, 'expect': n_sel, 'errors': errors, 'expect_window': n_window, 'n_N1': n_window - n_sel,
+            'n_last': (n_sel - minutes) if minutes is not None else None, 'ok': ok}
+
+
 def main():
     ap = argparse.ArgumentParser()
     ap.add_argument('--out-dir', required=True); ap.add_argument('--fx', required=True); ap.add_argument('--live', required=True)
@@ -92,12 +100,19 @@ def main():
     g['V5'] = {'ok': all(x['banners'] and all(x['banners'].values()) and x['env_missing_n'] == 0 and x['net_lines'] == 0
                          and x['jar_check_ok'] is True for x in v5.values()),
                'lanes': v5}
+    # [ERRATA7 V6] expect = so phut CO INPUT = so ts phan biet cua fx/sel.csv.gz trong [S, E) (prereg s11 "so phut xu ly == so phut input";
+    #   s5: phut khong co sel_dump = N1 NO_INPUT); truoc day expect = do dai cua so (sai so voi prereg)
+    selm = set()
+    for r in csv.DictReader(gzip.open(a.fx + '/sel.csv.gz', 'rt')):
+        t = int(r['ts'])
+        if S <= t < E:
+            selm.add(t)
     v6 = {}
     for ln in lanes:
         res = json.load(open(os.path.join(a.out_dir, ln, 'result.json')))
-        v6[ln] = {'minutes': (res.get('market') or {}).get('minutes'), 'expect': (E - S) // 60000, 'errors': len(res.get('errors', []))}
-    # rig 11-17 (fx1105) cung xu ly 12959/12960 phut: phut cuoi [END-1', END) khong co nen sau de quyet dinh => chap nhan expect-1 (ghi ro)
-    g['V6'] = {'ok': all(x['minutes'] in (x['expect'], x['expect'] - 1) and x['errors'] == 0 for x in v6.values()), 'lanes': v6}
+        v6[ln] = v6_lane((res.get('market') or {}).get('minutes'), len(res.get('errors', [])), len(selm), (E - S) // 60000)
+    # rig 11-17 (fx1105) cung xu ly 12959/12960 phut: phut cuoi [END-1', END) khong co nen sau de quyet dinh => chap nhan expect-1 (E-A11)
+    g['V6'] = {'ok': all(x['ok'] for x in v6.values()), 'lanes': v6}
     import ast   # V7: REF + bo cham KHONG import cau noi Java / chay tien trinh (kiem AST, khong theo chu trong comment)
     BADMOD = {'jpype', 'py4j', 'jnius', 'subprocess'}
     def java_hint(f):
@@ -118,6 +133,8 @@ def main():
     v10 = json.load(open(a.v10)) if a.v10 and os.path.exists(a.v10) else None
     g['V10a'] = {'ok': bool(v10 and v10.get('V10a_ok')), 'file': a.v10 or 'CHUA CHAY',
                  'domain_minutes': (v10 or {}).get('domain_minutes'), 'V10a_mismatch_minutes': (v10 or {}).get('V10a_mismatch_minutes')}
+    for k in ('V10a_rule', 'V10a_pass_eq', 'V10a_pass_subset', 'V10a_pass_subset_trans', 'V10a_not_bitexact_minutes', 'V10a_fail'):
+        g['V10a'][k] = (v10 or {}).get(k)
     g['ok'] = all(v['ok'] for k, v in g.items() if isinstance(v, dict) and 'ok' in v)
     json.dump(g, open(os.path.join(a.out_dir, 'gates.json'), 'w'), indent=1)
     print(json.dumps({k: (v['ok'] if isinstance(v, dict) else v) for k, v in g.items()}))
diff --git a/tools/add24/rlive/tests/run_tests.sh b/tools/add24/rlive/tests/run_tests.sh
index 67b36d8f..ba3c9c53 100755
--- a/tools/add24/rlive/tests/run_tests.sh
+++ b/tools/add24/rlive/tests/run_tests.sh
@@ -6,4 +6,5 @@ TEST_OUT=$A/test_score.json python3 $T/test_score.py > $A/test_score.txt 2>&1; R
 bash $T/test_parser_v4b.sh $A/test_parser_v4b.json > $A/test_parser_v4b.txt 2>&1; R2=$?
 bash $T/test_guard_gate.sh $A/test_guard_gate.json > $A/test_guard_gate.txt 2>&1; R3=$?
 bash $T/test_full_tier3_java.sh $A/test_full_tier3.json > $A/test_full_tier3.txt 2>&1; R4=$?
-echo "test_score(a,b,c,e)=$R1 test_parser_v4b(f)=$R2 test_guard_gate(d)=$R3 test_full_tier3(D1,tier3)=$R4 out=$A"; [ $R1$R2$R3$R4 = 0000 ]
+python3 $T/test_errata7.py > $A/test_errata7.txt 2>&1; R5=$?   # [ERRATA7] V10a (2) / V6 / V4b
+echo "test_score(a,b,c,e)=$R1 test_parser_v4b(f)=$R2 test_guard_gate(d)=$R3 test_full_tier3(D1,tier3)=$R4 test_errata7=$R5 out=$A"; [ $R1$R2$R3$R4$R5 = 00000 ]
diff --git a/tools/add24/rlive/tests/test_errata7.py b/tools/add24/rlive/tests/test_errata7.py
new file mode 100644
index 00000000..975a3157
--- /dev/null
+++ b/tools/add24/rlive/tests/test_errata7.py
@@ -0,0 +1,74 @@
+#!/usr/bin/env python3
+"""ADD24 ERRATA7 unit test (du lieu TONG HOP): V10a dieu kien (1)/(2) + phut chuyen trang thai; V6 expect theo phut co input; V4b quy tac
+EQ_INCOME_ERR (C3MainEquity:218). Exit 0 neu moi test dat."""
+import json, os, subprocess, sys, tempfile
+H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
+sys.path.insert(0, H)
+import v10_buffer as V
+import rlive_gates as G
+MIN = 60000
+res = {}
+# ---- V10a
+rows = [('AAAUSDT', 10), ('BBBUSDT', 20), ('CCCUSDT', 30)]
+R = [10, 20, 30]
+res['eq'] = V.minute_rule([10, 20, 30], R, rows, set(), set())[0] == 'eq'
+res['eq_bo_qua_S_m'] = V.minute_rule([10, 20, 30], R, rows, {'CCCUSDT'}, set())[0] == 'eq'
+res['subset_dung_S_m'] = V.minute_rule([10, 20], R, rows, {'CCCUSDT'}, set())[0] == 'subset'
+res['subset_2_symbol'] = V.minute_rule([10], R, rows, {'BBBUSDT', 'CCCUSDT'}, set())[0] == 'subset'
+k = V.minute_rule([10, 20], R, rows, {'BBBUSDT'}, set())
+res['thua_ngoai_S_m_truot'] = k[0] is None and k[1] == 'symbol_thua_khac_S_m'
+res['S_m_rong_thua_truot'] = V.minute_rule([10, 20], R, rows, set(), set())[0] is None
+res['S_m_thua_symbol_truot'] = V.minute_rule([10, 20], R, rows, {'CCCUSDT', 'BBBUSDT'}, set())[0] is None
+k = V.minute_rule([10, 20, 40], R, rows, set(), set())
+res['L_co_ban_ghi_R_khong_truot'] = k[0] is None and k[1] == 'L_khong_la_tap_con_R'
+k = V.minute_rule([10, 21], R, rows, {'CCCUSDT'}, set())     # 1 ulp float32 (bit + 1)
+res['lech_1_ulp_truot'] = k[0] is None and k[1] == 'L_khong_la_tap_con_R'
+k = V.minute_rule([10, 20, 20], R, rows, set(), set())       # multiset: L 2 ban sao, R 1
+res['multiset_dem_truot'] = k[0] is None
+k = V.minute_rule([10, 20], [10, 20, 30], [('AAAUSDT', 10), ('BBBUSDT', 20)], {'CCCUSDT'}, set())
+res['rig_trace_khac_appended_truot'] = k[0] is None and k[1] == 'rig_trace_khac_appended'
+# chuyen trang thai: S_m = {B, C}, rig thua chi C; B chuyen trang thai => dat; B khong chuyen => truot
+res['trans_cho_phep_thieu'] = V.minute_rule([10, 20], R, rows, {'BBBUSDT', 'CCCUSDT'}, {'BBBUSDT'})[0] == 'subset_trans'
+res['trans_cho_phep_thua'] = V.minute_rule([10], R, rows, {'CCCUSDT'}, {'BBBUSDT'})[0] == 'subset_trans'
+res['trans_khong_flex_truot'] = V.minute_rule([10, 20], R, rows, {'BBBUSDT', 'CCCUSDT'}, set())[0] is None
+res['trans_flex_symbol_khac_truot'] = V.minute_rule([10, 20], R, rows, {'BBBUSDT', 'CCCUSDT'}, {'AAAUSDT'})[0] is None
+# r_bits trung giua 2 symbol: chon duoc cach gan khop S_m
+rd = [('AAAUSDT', 10), ('BBBUSDT', 10)]
+res['bits_trung_gan_duoc'] = V.minute_rule([10], [10, 10], rd, {'BBBUSDT'}, set())[0] == 'subset'
+# cua so chuyen trang thai +-1 phut
+m = 100 * MIN
+lev = {m + MIN: {'XUSDT'}}; rtr = {m - MIN: {'YUSDT'}}
+res['flex_m_cong_1'] = 'XUSDT' in V.flex_at(m, lev, {}) and 'YUSDT' in V.flex_at(m, {}, rtr)
+res['flex_m_cong_2_khong'] = not V.flex_at(m, {m + 2 * MIN: {'XUSDT'}}, {m - 2 * MIN: {'YUSDT'}})
+res['flex_dung_phut'] = V.flex_at(m, {m: {'XUSDT'}}, {m: {'YUSDT'}}) == {'XUSDT', 'YUSDT'}
+# ---- V6
+x = G.v6_lane(6773, 0, 6774, 7049)
+res['v6_dat_N1_va_phut_cuoi'] = x['ok'] and x['n_N1'] == 275 and x['n_last'] == 1 and x['expect_window'] == 7049
+res['v6_dat_du_phut'] = G.v6_lane(6774, 0, 6774, 7049)['ok']
+res['v6_thieu_2_truot'] = not G.v6_lane(6772, 0, 6774, 7049)['ok']
+res['v6_exception_truot'] = not G.v6_lane(6773, 1, 6774, 7049)['ok']
+res['v6_thua_truot'] = not G.v6_lane(6775, 0, 6774, 7049)['ok']
+res['v6_none_truot'] = not G.v6_lane(None, 0, 6774, 7049)['ok']
+res['v6_cu_expect_cua_so_truot'] = not G.v6_lane(6773, 0, 7049, 7049)['ok']
+# ---- V4b (parser + v4b.sh tren log tong hop, ngoai pull242 => khong can P1)
+os.makedirs('/dev/shm/add24', exist_ok=True)
+d = tempfile.mkdtemp(dir='/dev/shm/add24', prefix='te7.')
+base = ('01/01/2026 00:22:00.000 WARN  [x] c.b.c.c.r.C3MainEquity: [C3-LIVE-EQ] doc income FUNDING_FEE loi '
+        'com.binance.chuyennd.c3live.api.GatewayException: x => thu lai sau 600 s\n'
+        '01/01/2026 00:23:00.000 INFO  [x] c.b.c.c.r.C3MainEquity: [C3-LIVE-EQ] funding c3 +0.01 (2 dong) => cong don 0.02\n')
+for name, extra in (('ok', ''), ('bad', '01/01/2026 00:24:00.000 WARN  [x] c.b.c.c.r.C3MainEquity: [C3-LIVE-EQ] doc income KHAC loi x\n')):
+    open(d + '/%s.log' % name, 'w').write(base + extra)
+    subprocess.run([sys.executable, '-I', H + '/live_log_parse.py', '--log-files', d + '/%s.log' % name, '--start', '2026-01-01 00:00',
+                    '--end', '2026-01-01 02:00', '--out', d + '/p_' + name, '--mode', 'full'], capture_output=True)
+    subprocess.run(['bash', H + '/v4b.sh', d + '/p_%s/counts.json' % name, '2026-01-01 00:00', '2026-01-01 02:00', d + '/v4b_%s.json' % name,
+                    d + '/%s.log' % name], capture_output=True)
+c = json.load(open(d + '/p_ok/counts.json'))
+vo, vb = json.load(open(d + '/v4b_ok.json')), json.load(open(d + '/v4b_bad.json'))
+res['v4b_eq_income_parsed'] = c['counts']['EQ_INCOME_ERR'] == {'tag_lines': 1, 'parsed': 1} and c['unmatched_c3live_lines'] == 0
+res['v4b_eq_income_khong_la_info'] = not c['info_lines_by_shape']
+res['v4b_ok_PASS'] = vo['ok'] is True and vo['rules']['EQ_INCOME_ERR'] == {'grep': 1, 'tag_lines': 1, 'parsed': 1, 'ok': True}
+res['v4b_dong_EQ_la_van_FAIL'] = vb['ok'] is False and vb['unmatched_c3live_lines'] == 1
+subprocess.run(['rm', '-rf', d])
+res['ok'] = all(res.values())
+print(json.dumps(res, indent=0))
+sys.exit(0 if res['ok'] else 1)
diff --git a/tools/add24/rlive/v10_buffer.py b/tools/add24/rlive/v10_buffer.py
index f2e0acac..30800e86 100644
--- a/tools/add24/rlive/v10_buffer.py
+++ b/tools/add24/rlive/v10_buffer.py
@@ -2,14 +2,19 @@
 """ADD24 cong V10 (ERRATA3 A4 + ERRATA4 C3). So (ts, r) rig nap vao buffer gate voi buffer live (file gate_ratio_live cua lan pull SAU cua so).
 V10a (truot => HUY): mien = phut ma rig va live co CUNG tap dang giu (giao voi ung vien phut do) VA cung trang thai so day, HOAC phut truoc
   lech L-E dau tien: multiset r (bit float32) phai TRUNG va lech dem = 0.
+[ERRATA7] mien V10a GIU NGUYEN; DIEU KIEN DAT cua mot phut m trong mien (L = multiset ban ghi live tai m, R = cua rig):
+  (1) L == R (bit); HOAC (2) L la tap con bit-exact cua R (multiset) VA tap symbol cua R\L == S_m = held_live(m) \ held_rig(m) (cung nguon
+  trang thai nhu V10_diag); symbol co PHUT CHUYEN TRANG THAI (live: mo/dong cum roi vao phut m-1, m, m+1; rig: co 'held' trong trace_dec doi
+  o phut m-1, m, m+1 so voi phut co trace truoc do) duoc nam o MOT TRONG HAI phia. Symbol cua ban ghi rig = trace_dec hang held=0 (assert
+  multiset r_bits == appended.csv.gz tung phut; khac => phut truot). V10a ok <=> 0 phut khong dat. Nen END-1' bi bo ca hai phia (E-A11).
 V10b (bao cao): phut lech dem NGOAI mien V10a -> outside_domain_mismatch_minutes; rlive_score.py --v10 xet thuoc cum lech co nhan, con lai =
   lech L-N KHONG GIAI THICH. Chi dem / so bit - khong in gia tri r.
 Dang giu live phut m = cum live co leg 0 SUBMIT truoc m+60 s va chua dong (dong dong cum) tai m+60 s (gate phut m chay o giay ~6 phut sau).
 So day live = tong notional leg mo / cap >= U_MAX (xap xi; rig: co bookfull trong trace_dec).
 usage: v10_buffer.py --rig <lane dir> --live <parse dir> --live-buffer <pull>/run/gate_ratio_live.bin.gz --start --end --cap --out V10.json
 """
-import argparse, csv, gzip, json, os, shutil, sys, tempfile
-from collections import defaultdict
+import argparse, csv, gzip, itertools, json, os, shutil, sys, tempfile
+from collections import Counter, defaultdict
 from datetime import datetime, timedelta, timezone
 import numpy as np
 
@@ -26,6 +31,53 @@ def bits(x):
     return int(np.array([x], dtype=np.float32).view(np.int32)[0])
 
 
+def rig_extra_sets(L, rows, cap=4096):
+    """[ERRATA7] L: list r_bits live tai phut m; rows: [(symbol, r_bits)] ban ghi rig tai m (moi symbol 1 ban ghi).
+    Tra None neu L KHONG la tap con multiset cua R; 'AMBIG' neu qua nhieu cach gan; nguoc lai tap cac tap symbol co the cua R\\L
+    (khi nhieu symbol cung r_bits thi moi cach chon deu duoc xet)."""
+    Lc, Rc = Counter(L), Counter(b for _, b in rows)
+    if any(Rc[b] < n for b, n in Lc.items()):
+        return None
+    out = {frozenset()}
+    for b in sorted(Rc):
+        k = Rc[b] - Lc.get(b, 0)
+        if k <= 0:
+            continue
+        syms = sorted(s for s, bb in rows if bb == b)
+        out = {o | frozenset(c) for o in out for c in itertools.combinations(syms, k)}
+        if len(out) > cap:
+            return 'AMBIG'
+    return out
+
+
+def minute_rule(L, R, rows, S_m, flex):
+    """[ERRATA7] dieu kien DAT cua mot phut trong mien V10a. L, R: list r_bits (live, rig); rows: [(symbol, r_bits)] cua rig;
+    S_m: set symbol live giu/cho ma rig khong giu; flex: set symbol co phut chuyen trang thai (m-1..m+1) o live hoac rig.
+    Tra (kieu, ly_do, X): kieu in {'eq', 'subset', 'subset_trans', None}; X = tap symbol R\\L da chon (None neu khong co)."""
+    if sorted(L) == sorted(R):
+        return 'eq', '', frozenset()
+    if Counter(b for _, b in rows) != Counter(R):
+        return None, 'rig_trace_khac_appended', None
+    sets = rig_extra_sets(L, rows)
+    if sets is None:
+        return None, 'L_khong_la_tap_con_R', None
+    if sets == 'AMBIG':
+        return None, 'gan_symbol_mo_ho', None
+    S_m, flex = frozenset(S_m), frozenset(flex)
+    for X in sorted(sets, key=sorted):
+        if X == S_m:
+            return 'subset', '', X
+    for X in sorted(sets, key=sorted):
+        if X - flex == S_m - flex:
+            return 'subset_trans', '', X
+    return None, 'symbol_thua_khac_S_m', min(sets, key=sorted)
+
+
+def flex_at(t, lev, rtr):
+    """[ERRATA7] symbol co phut chuyen trang thai tai t-1', t, t+1' (lev: live phut moc mo/dong; rtr: rig phut 'held' doi)."""
+    return set().union(*(lev.get(t + d, set()) | rtr.get(t + d, set()) for d in (-MIN, 0, MIN)))
+
+
 def main():
     ap = argparse.ArgumentParser()
     ap.add_argument('--rig', required=True); ap.add_argument('--live', required=True); ap.add_argument('--live-buffer', required=True)
@@ -33,10 +85,11 @@ def main():
     ap.add_argument('--u-max', type=float, default=0.6); ap.add_argument('--out', required=True)
     a = ap.parse_args()
     S, E = ms7(a.start), ms7(a.end)
+    E1 = E - MIN   # [ERRATA7] bo nen END-1' ca hai phia (E-A11: rig khong decide nen cuoi)
     rig = defaultdict(list)
     for x in csv.DictReader(gzip.open(a.rig + '/appended.csv.gz', 'rt')):
         t = int(x['ts'])
-        if S <= t < E:
+        if S <= t < E1:
             rig[t].append(int(x['r_bits']))
     d = tempfile.mkdtemp(dir='/dev/shm/add24')
     try:
@@ -47,18 +100,20 @@ def main():
     finally:
         shutil.rmtree(d)
     live = defaultdict(list)
-    m = (ts >= S) & (ts < E)
+    m = (ts >= S) & (ts < E1)
     for t, v in zip(ts[m], r[m]):
         live[int(t)].append(bits(v))
     # trang thai rig theo phut (trace_dec): ung vien, dang giu, so day
-    cand, rheld, rfull = defaultdict(set), defaultdict(set), {}
+    cand, rheld, rfull, rrows = defaultdict(set), defaultdict(set), {}, defaultdict(list)
     for x in csv.DictReader(gzip.open(a.rig + '/trace_dec.csv.gz', 'rt')):
         t = int(x['ts'])
-        if not (S <= t < E):
+        if not (S <= t < E1):
             continue
         cand[t].add(x['symbol'])
         if x['held'] == '1':
             rheld[t].add(x['symbol'])
+        else:
+            rrows[t].append((x['symbol'], int(x['r_bits'])))   # [ERRATA7] ban ghi rig nap buffer (held=0) - chi de biet symbol
         rfull[t] = rfull.get(t, False) or x['bookfull'] == '1'
     # cum live
     sub = [x for x in csv.DictReader(open(a.live + '/submit.csv')) if x['outcome'] == 'SUBMITTED']
@@ -81,8 +136,20 @@ def main():
     rk = {(int(x['decision_ts']), x['symbol'], x['level'], int(x['leg_idx'])) for x in csv.DictReader(open(a.rig + '/legs.csv')) if x['outcome'] == 'SUBMITTED'}
     dif = [k[0] for k in lk ^ rk if S <= k[0] < E]
     first_dev = min(dif) if dif else E
+    # [ERRATA7] phut chuyen trang thai: live = phut cua moc mo (leg dau) / dong cum; rig = phut 'held' doi so voi phut co trace truoc do
+    lev = defaultdict(set)
+    for c in cl:
+        lev[c['t0'] // MIN * MIN].add(c['symbol'])
+        if c['tc'] is not None:
+            lev[c['tc'] // MIN * MIN].add(c['symbol'])
+    rtr, prev = defaultdict(set), None
+    for t in sorted(cand):
+        if prev is not None:
+            rtr[t] = rheld.get(t, set()) ^ rheld.get(prev, set())
+        prev = t
     dom, in_bad, out_bad, n_dom = [], 0, [], 0
     diag = []
+    kinds = Counter(); fails = []; n_nbe = 0
     for t in sorted(set(live) | set(rig) | set(cand)):
         tg = t + MIN
         lheld = {c['symbol'] for c in cl if c['t0'] < tg and (c['tc'] is None or c['tc'] > tg)}
@@ -93,24 +160,39 @@ def main():
         A_, B_ = sorted(live.get(t, [])), sorted(rig.get(t, []))
         if t < first_dev or same:
             n_dom += 1
+            hl, hr = lheld & cand.get(t, set()), rheld.get(t, set())
+            S_m = hl - hr
+            flex = flex_at(t, lev, rtr)
+            kind, why, X = minute_rule(A_, B_, rrows.get(t, []), S_m, flex)
+            kinds[kind or 'fail'] += 1
             if A_ != B_:
-                in_bad += 1; dom.append(t)
+                n_nbe += 1
                 # chan doan (ERRATA5 B(ii)): tap r lech theo phut (bit), trang thai giu / so day hai ben - khong gia / kich thuoc lenh
                 diag.append({'ts': t, 'n_live': len(A_), 'n_rig': len(B_), 'r_bits_chi_live': sorted(set(A_) - set(B_))[:30],
-                             'r_bits_chi_rig': sorted(set(B_) - set(A_))[:30], 'held_live': sorted(lheld & cand.get(t, set())),
-                             'held_rig': sorted(rheld.get(t, set())), 'full_live': lfull, 'full_rig': rfull.get(t, False)})
+                             'r_bits_chi_rig': sorted(set(B_) - set(A_))[:30], 'held_live': sorted(hl),
+                             'held_rig': sorted(hr), 'full_live': lfull, 'full_rig': rfull.get(t, False),
+                             'e7_kieu': kind, 'e7_ly_do': why, 'e7_S_m': sorted(S_m), 'e7_X': sorted(X) if X is not None else None,
+                             'e7_flex': sorted(flex & (S_m | (X or set())))})
+            if kind is None:
+                in_bad += 1; dom.append(t)
+                fails.append({'ts': t, 'ly_do': why, 'n_live': len(A_), 'n_rig': len(B_), 'S_m': sorted(S_m),
+                              'X': sorted(X) if X is not None else None, 'flex': sorted(flex & (S_m | (X or set())))})
         elif len(A_) != len(B_) or A_ != B_:
             out_bad.append(t)
     n_l = sum(len(v) for v in live.values()); n_r = sum(len(v) for v in rig.values())
-    res = {'window': [S, E], 'live_records': n_l, 'rig_records': n_r, 'first_L_E_dev': first_dev, 'domain_minutes': n_dom,
+    res = {'window': [S, E], 'window_eff_end': E1, 'live_records': n_l, 'rig_records': n_r, 'first_L_E_dev': first_dev, 'domain_minutes': n_dom,
            'V10a_mismatch_minutes': in_bad, 'V10a_first': dom[:20], 'outside_domain_mismatch_minutes': out_bad,
            'live_buffer_bad_frames': bad, 'live_buffer': a.live_buffer}
+    res['V10a_rule'] = 'ERRATA7: (1) L==R bit; hoac (2) L tap con bit cua R va symbol(R\\L) == S_m (symbol chuyen trang thai m+-1 tu do)'
+    res['V10a_pass_eq'] = kinds['eq']; res['V10a_pass_subset'] = kinds['subset']; res['V10a_pass_subset_trans'] = kinds['subset_trans']
+    res['V10a_not_bitexact_minutes'] = n_nbe; res['V10a_fail'] = fails[:200]; res['V10a_fail_n'] = len(fails)
     res['V10a_ok'] = in_bad == 0 and bad == 0
     res['ok'] = res['V10a_ok']
     json.dump(res, open(a.out, 'w'), indent=1)
     json.dump(diag, open(a.out.replace('.json', '') + '_diag.json', 'w'), indent=0)
     res['diag_file'] = a.out.replace('.json', '') + '_diag.json'
-    print(json.dumps({k: res[k] for k in ('V10a_ok', 'live_records', 'rig_records', 'domain_minutes', 'V10a_mismatch_minutes')} | {'outside_n': len(out_bad)}))
+    print(json.dumps({k: res[k] for k in ('V10a_ok', 'live_records', 'rig_records', 'domain_minutes', 'V10a_mismatch_minutes', 'V10a_pass_eq',
+                                          'V10a_pass_subset', 'V10a_pass_subset_trans', 'V10a_not_bitexact_minutes')} | {'outside_n': len(out_bad)}))
     return 0 if res['ok'] else 1
 
 
```

## C. KHONG doi
- Nguong, nhan (N1-N12), trang thai PASS / INSUFFICIENT / FAIL, logic CHAM: rlive_score.py, conclude.py, ref_size.py KHONG doi 1 dong;
  run_rlive.sh, v4b.sh, buf_check.py, rlive_fixture.py, v8_check.py, sanitize.py, p1_gate.py KHONG doi.
- Cua so OW2 2026-11-19 09:31 -> T_cut 2026-11-24 07:00 +07 (pull 2026-11-23 COMPLETE); EXINFO sha256
  dcfa03c72c38a658e7de7df812e876bbca903f9e0dfd81ab02b1aeb61f3a1684; jar stub md5 cf0f479241265de68836716ee66a1866; env whitelist /
  override; lane (L0, L0-FOLLOW, L0-DRY, L-10K) va tham so lane.
- Y nghia khoa V10.json duoc rlive_score doc (outside_domain_mismatch_minutes = phut lech NGOAI mien V10a -> V10b) KHONG doi; mien V10a
  KHONG doi. V10a_mismatch_minutes nay = so phut KHONG DAT theo muc D (truoc day = so phut khong bit-exact; so cu nay ghi o
  V10a_not_bitexact_minutes). V10a_ok = (0 phut khong dat) va 0 chunk hong buffer live (nhu cu).
- Che do dev1105: V6 - fx1105 co sel o du 12960/12960 phut cua so => expect khong doi (12960); V10a - chi them duong dat (2) va bo nen
  END-1'; V4b - them 1 quy tac dem (khong co dong => 0 == 0). Khong buoc nao doi o nhanh dev.

## D. Dinh nghia moi dieu kien V10a (nguyen van quyet dinh MASTER) + cach hien thuc
Nguyen van: "Giu NGUYEN mien V10a (moi phut nhu hien tai), chi doi DIEU KIEN DAT cua mot phut m: goi L = multiset ban ghi buffer cua
live tai m, R = cua rig. Phut m DAT khi va chi khi: (1) L == R (bit-exact nhu hien tai); HOAC (2) L la tap con bit-exact cua R (multiset)
VA tap symbol cua R\L dung bang tap S_m = cac symbol ma live dang giu/dang cho (theo dung nguon trang thai ma v10 da dung de ra V10_diag)
con rig khong giu tai m; trong do tai PHUT CHUYEN TRANG THAI cua mot symbol o live hoac rig (thoi diem mo/dong roi vao phut m hoac phut
lien ke m+-1 do do phan giai 1 phut va do tre ghi) symbol do duoc phep nam o MOT TRONG HAI phia (duoc hoac khong duoc tinh vao S_m).
V10a ok <=> 0 phut khong dat. Bao them trong V10.json: so phut dat theo (1), theo (2), so phut dung toi luat phut chuyen trang thai, va
danh sach phut khong dat. Luat phai TONG QUAT."
Hien thuc (v10_buffer.py, khong nhac timestamp / symbol cu the):
- S_m = (held_live(m) giao ung_vien_rig(m)) \ held_rig(m) - dung cac tap held_live / held_rig da ghi trong V10_diag.
- Symbol cua ban ghi rig: buffer chi co (ts, r) => symbol lay tu trace_dec.csv.gz cua rig, hang held=0 (r_bits). Kiem tung phut: multiset
  r_bits cac hang held=0 == multiset appended.csv.gz (khac => phut KHONG DAT, ly do rig_trace_khac_appended). Tren output luot #2: trung
  o 6769/6769 phut. Khi nhieu symbol cung r_bits: xet moi cach gan (gioi han 4096; vuot => KHONG DAT 'gan_symbol_mo_ho').
- Phut chuyen trang thai: live = phut (floor) cua moc mo cum (SUBMIT leg dau) / dong cum (book_close) - cung nguon cl ma v10 dung cho
  held_live; rig = phut co trace ma tap held khac phut co trace lien truoc. flex(m) = symbol co chuyen trang thai o m-1', m, m+1'
  (live hoac rig). Dat (2) khi ton tai cach gan X = symbol(R\L) voi X == S_m (dem 'subset') hoac X \ flex == S_m \ flex (dem
  'subset_trans' = dung toi luat chuyen trang thai).
- V10.json them: V10a_rule, V10a_pass_eq, V10a_pass_subset, V10a_pass_subset_trans, V10a_not_bitexact_minutes, V10a_fail (<= 200 phan tu:
  ts, ly_do, so ban ghi, S_m, X, flex), V10a_fail_n, window_eff_end. V10_diag them e7_kieu, e7_ly_do, e7_S_m, e7_X, e7_flex.
- Unit test tests/test_errata7.py (30 ca): L==R; L tap con R voi dung S_m; symbol thua KHONG thuoc S_m => truot; S_m rong ma R thua
  => truot; L co ban ghi R khong co => truot; lech 1 ulp float32 => truot; dem multiset; trace khac appended => truot; chuyen trang thai
  (thieu / thua, flex dung symbol, flex sai symbol => truot); cua so m+-1 (m+-2 khong tinh); r_bits trung 2 symbol; V6 (7 ca); V4b (4 ca).
Ly do (theo A1): ERRATA5 B(ii)(3) chi coi la LECH LOGIC gate khi "cung dau vao + cung trang thai"; o phut khac trang thai giu, ban ghi
thua cua rig la he qua cua trang thai, con moi ban ghi live van phai co ban sao BIT-EXACT o rig. Phuong an nay CHAT hon phuong an dua
phut khac trang thai ra khoi mien (V10-2 cua A1): van HUY neu bat ky r nao lech 1 ulp, hoac ban ghi thua thuoc symbol khong nam trong
S_m. Khac biet trang thai giu (vi sao rig khong giu) KHONG duoc phan loai o V10a - thuoc buoc CHAM (L-X / L-T / L-SL / V10b).

## E. Ket qua tinh thu cong tren output luot #2 + kiem ong nuoc mu (HEAD 8d397ce2)
- Sandbox v12/add24_errata7_sandbox (ban sao output luot #2; KHONG chay lane, KHONG luot official). Chay lai: live_log_parse --mode full
  (cung lenh run_rlive.sh, out sandbox), dem V4 grep, v4b.sh, v10_buffer.py, rlive_gates.py (code moi).
- Parse moi vs parse luot #2 (so sha256 tung file, khong doc noi dung): 49 file output parse TRUNG BYTE (+ follow.csv chep lai); 0 file mat; counts.json khac
  (them khoa EQ_INCOME_ERR); them eq_income_err.csv.
- gates (sha256 ce49f521a10df2917214c8b2dec0cce77c08a61e0c43891df7f9747b47e29557): V1..V8, V10a = true, ok = true (rlive_gates rc 0;
  chay 2 lan cho gates.json trung byte).
  * V4 parsed 24 == grep 24. V4b ok: unmatched 0, bad_rules [], EQ_INCOME_ERR grep 1 == tag_lines 1 == parsed 1.
  * V6: moi lane L0 / L0-FOLLOW / L0-DRY minutes 6773, expect 6774, expect_window 7049, n_N1 275, n_last 1, errors 0.
  * V10a (V10.json sha256 ed10d944cc34669181daf57b5d304c44d5f1fb8ce78fefb1512ba12cd463a416): domain_minutes 6769 (6770 - nen END-1'),
    dat (1) 6215, dat (2) 554 = 553 'subset' (X == S_m dung) + 1 'subset_trans' (2026-11-21 16:29: S_m 2 symbol, rig thua 1 ban ghi,
    symbol con lai co moc dong cum live o phut lien ke - dung ca A1 da neu), khong dat 0, outside 0, chunk hong 0; live_records 136846
    (= 136866 - 20 ban ghi nen 06:59), rig_records 137601.
- Kiem ong nuoc MU buoc cham (chua tung chay that): dung lenh rlive_score (L0 co --follow --v10; L0-DRY) + conclude nhu run_rlive.sh:101-109,
  moi output vao sandbox/blind/. CHI xem ma thoat + ten / kich thuoc / sha256; KHONG ai mo noi dung. Ma thoat: score_L0 0, score_L0DRY 0,
  conclude 0; stderr 3 file deu 0 byte. 11 file (danh sach sha256: v12/add24_errata7_sandbox/blind.sha256); blind/ da chmod 000, khong xoa.
  sha256 (de so tinh tat dinh sau luot #3; luu y: score.json / conclusion.json co the chua duong dan out nen KHONG bat buoc trung byte):
  score_L0/score.json 22c05c0b72b7bcc88dbb9d3592bbb5505ac4b9ac884c64de293cfdff78ae5e1c (2679 B);
  score_L0/labels.csv 307b26ce1efdc9bfdd49700e374496a7c2daf7382cc448956cc9c31c51892c0a (10532 B);
  score_L0DRY/score.json 317c809f34e4182cc7f88b2c57c5d8050c856cffcecda2d5665705e5df88c0e9 (2694 B);
  score_L0DRY/labels.csv 6e20d3a5df4be1e81aeb3d8b8ebfd174af9bc6b4e10352d052ff85f39390275f (10691 B);
  conclusion.json 03dd8cb351ff71fa272fa651dd14c14068910d249aead46fe9202657c7ccefb7 (882 B).
- Test: bash -n (run_rlive.sh, v4b.sh, tests/*.sh), py_compile moi .py: OK; test_score.py 41/41; test_parser_v4b.sh ok; test_errata7.py
  30/30. Khong chay test_guard_gate / test_full_tier3_java (lane java + oracle_heavy.lock; code lien quan khong doi).

## F. CONG KHAI muc da biet truoc luot #3
- A1 (phan xu luot #2) da thay: first_L_E_dev = END trong V10.json (tap khoa SUBMIT live va rig L0 khong tach trong OW2 - mot phan ket qua
  L-E); V10_diag: 10 symbol + khoang thoi gian rig khong giu ma live giu (dau hieu khac biet duong thoat / giu); q_t live / rig; 1 dong
  log EQ (gio + ten exception).
- MASTER + DEV biet them (DEV liet ke dung nhung gi DEV da doc / thay): gates.json luot #2 va sandbox (V4 parsed 24 SUBMIT live = grep 24);
  bao cao RUN luot #2 (so dong tag theo quy tac trong dong log parse: SUBMIT 24, FILL_STREAM 23, EXEC_ACK 24, EXEC_FILL 1, CUM_DA_DONG 16,
  phan con lai bi cat khi in); V10.json / V10_diag.json moi: tap symbol S_m / X / flex o 554 phut khac trang thai (cung 10 symbol A1 da neu),
  so dong trace_dec rig theo held (held=1: 24855 dong-symbol-phut, held=0: 137601), r_bits trace_dec == appended tung phut (chi so sanh,
  khong in gia tri); ten + kich thuoc + sha256 file blind. DEV KHONG doc submit / exec / fill / order / trail / time_stop / leg / eq / cum
  noi dung, khong tinh / in gia, size, PnL, equity; v10_buffer.py (code) doc submit.csv / book_close.csv / legs.csv o muc symbol + moc
  thoi gian nhu truoc.
- A1 (vong duyet delta ERRATA7) da thay: keep/ (gates.json, V10.json, V10_diag.json moi: e7_S_m / X / flex tung phut), blind.sha256 +
  blind_rc (ma thoat 0), live_cmp.txt (ten file SAME/DIFF), bao cao + progress DEV; A1 tu tinh lai V10a (cung so 6215/553/1/0), dem
  chuyen trang thai held cua rig (187 phut / 250 su kien), counts.json parse mode format (so dong theo quy tac, khong gia tri).
- MASTER da thay: cac con so tong hop trong bao cao RUN / A1 / DEV: gates luot #2, so phut V6 / V10a, danh sach 10 symbol khac trang
  thai giu voi so phut (PONSUSDT 513, EVAAUSDT 134, PIEVERSEUSDT 48, ARIAUSDT 29, ...), V4 = 24 SUBMIT, dong dem tag FILL_STREAM 23 /
  EXEC_ACK 24 / EXEC_FILL 1 / CUM_DA_DONG 16. Ngoai ra sang 2026-11-24 MASTER da doc 24 dong SUBMIT ngay 2026-11-21 trong log live
  (thoi diem, symbol, qty, budget) de tra loi owner ve kich thuoc lenh - viec nay TRUOC luot #2 va SAU khi nguong da chot.
- CHUA AI thay score / conclusion (luot #2 khong cham; ban chay mu chi co ma thoat + sha).

## G. Owner dong y luot #3
- 2026-11-24 ~19:45 +07, nguyen van: "chay rlive luot 3 di" - sau khi MASTER trinh: ERRATA7 chi sua 3 cong, khong doi nguong cham; luot #3 la
  lan chay lai CUOI; truot cong V nao nua hoac loi ky thuat => R-LIVE = INSUFFICIENT.

## H. Quy tac luot #3
- E2E_ERRATA=E7, A1_APPROVED=8d397ce2dbbdf3db72da9dd7bb4399866c675911 (HEAD A1 duyet delta a66109c1..8d397ce2), ADD24_P1_APPROVED=e451154e,
  cung EXINFO, E2E_OFFICIAL_LOCK=a/OFFICIAL_ADD24_RLIVE.lock. Chay bang w3/add24/run_rlive_e7.sh <HEAD> (preflight) roi
  run_rlive_e7.sh <HEAD> go. Log = FILE MOI v12/rlive_1124_run3.log. KHONG boc flock.
- Dieu kien tien quyet (run_rlive_e7.sh kiem, giu NGUYEN moi preflight cua E6, ke ca Vision HEAD day du): errata nay commit vao vz_e1_wt
  va nhac HEAD 8d397ce2...; khoa chua co dong errata=E7; log luot #3 chua ton tai; /dev/shm/add24/vision KHONG ton tai; dia >= 15300 MB;
  oracle_heavy.lock ranh.
- Day la LAN CHAY LAI CUOI. Thoat TRUOC dong ghi khoa (exit 2, 8, 9 stub, 15, 16) = khong tinh la luot (sua van hanh, khong doi code).
  SAU khi dong "errata=E7" da ghi: bat ky cong V truot (exit 13 / 14) hoac loi ky thuat (exit 9 build, 11, 12, 17, crash / traceback,
  lane khong chay) => R-LIVE = INSUFFICIENT (KHONG phu), bao owner, KHONG co luot #4.
- NIEM PHONG: thu muc v12/add24_errata7_sandbox/blind/ (chay thu bo cham tren du lieu luot #2) da chmod 000; KHONG ai mo truoc khi
  luot #3 cham xong va A1 kiem. KHONG duoc dung thay ket qua neu luot #3 hong (khi do R-LIVE = INSUFFICIENT va blind/ van KHONG mo, tru
  khi owner quyet bang van ban). Sau luot #3 CHI dung de so tinh tat dinh: chuan hoa duong dan out (thay bang "<OUT>") roi moi so sha256.
- Dieu kien van hanh luot #3: TAM DUNG chuoi s2_chain_v2.sh (viec khac, dung oracle_heavy.lock) tu TRUOC preflight toi khi co EXIT_CODE
  (khong job nao khac giu / tranh oracle_heavy.lock trong luc chay); ghi manifest sha256 (ten, kich thuoc, sha256 tung zip) cua
  /dev/shm/add24/vision ra dia (v12/) TRUOC khi xoa thu muc do; chay TRUOC khi xuat hien pull242/2026-11-24/COMPLETE.
- Bao cao CA BA luot: #1 (muc A ERRATA6: khong cham, loi ky thuat truoc khi doc du lieu), #2 (muc A tren: khong cham, cong V truot,
  da phan xu A1), #3 (luot cham).
