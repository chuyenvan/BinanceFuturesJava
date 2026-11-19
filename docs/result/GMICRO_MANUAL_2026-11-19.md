# GMICRO_MANUAL_2026-11-19 - bien ban MASTER chung nhan tay (ii) + smoke (ADD22 muc 2.5; tieu chi ADD21 muc 4 + ADD22 muc 2)

Lap: MASTER (Claude), 2026-11-19 ~09:30 +07. Moi so la so dem tren 242 (CHI DOC) luc 2026-11-19 09:21 +07 va tren Oracle.
Jar dich v_t_m: r4u3fin2 md5 641803565297d4065d90245e04a00f11 (dang chay, PID 19958). Ingestor md5 5e78ac0663b4a765551eac1c362bf194 (PID 27717).
smoke_start_ms=1794813510000 (16/11/2026 14:18:30 +07 = gio start that cua JVM co 2 co grid; parity_v12w/gmicro_target.json).

gmicro_ii: DAT
smoke: DAT

## 1. Khong restart
- v_t_m PID 19958 etime 2-19:02:52 luc 19/11 09:21:21 => start 16/11 14:18:29. `grep -a -c -F MainClass full.log` = 1 (file full.log bat dau 16/11 09:21).
- Ingestor PID 27717 etime 4-20:54:13 => start 14/11 12:27. Khong swap jar nao tu 16/11 14:18:30.

## 2. Smoke >= 24 h (cua so 16/11 14:18:30 -> 17/11 14:18:30 +07; dem tren CA file full.log 16/11 09:21 -> 19/11 09:21 = tap cha cua cua so)
Lenh dem (242): `cd /home/chuyennd/java/v_t_m/logs; nice -n 19 grep -a -c -F -- "<chuoi>" full.log`
| Truong (ADD21 muc 4 / ADD22 muc 2.2) | Yeu cau | Dem duoc |
|---|---|---|
| dong muc ` ERROR ` | 0 | 0 |
| LATCH | 0 | 0 |
| KHAN | 0 | 0 |
| FIN_KHONG_BIN | 0 | 0 |
| `[TELEGRAM] thieu env` | 0 | 0 |
| `[MINUTE-FIN] BAT` | co | 1 |
| `[LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true` | co | 1 |
| `[LIVE-DCA-GRID] LIVE_DCA_GRID_ENABLED=true ... applyRatio=true` | co | 1 (16/11/2026 14:18:31.015, levels=[-0.5, -0.75, -0.9] legs=3 scale=6.0) |
| `DCA_OFF` trong HOURLY ke tu JVM moi | 0 | 0 (ca file co 5 dong, dong cuoi 16/11/2026 14:11:17 = JVM cu, truoc smoke_start) |
collectData (`/home/chuyennd/java/collectData/logs/full.log`, cung lenh dem):
| `[KLINE-FIN] loi ghi` | 0 | 0 |
| `[TELEGRAM] thieu env` | 0 | 0 |
| `[KLINE-FIN] bin fin BAT` | co | 1 |
Token Telegram trong env 2 process (sha256 qua /proc/PID/environ, lenh da audit o deploy_ingest_fin.sh:199, KHONG in token):
PID 19958 sha8 = bdee1480; PID 27717 sha8 = bdee1480 (yeu cau bdee1480).
Harness (tham khao, khong phai can cu): parity_v12_gmicro.json smoke_24h=true, smoke_info ERROR=0 LATCH=0, win=[1794813510000, 1794899910000].

## 3. (ii) - ngay SACH chay tron tren cap jar ADD21 voi 2 co bat
- Ngay 2026-11-17 (UTC): watch_v12.log `2026-11-19T01:57:19Z DAY 2026-11-17 rc=0 verdict: DAT | SACH`. Day la ngay UTC tron DAU TIEN sau restart bat co
  (16/11 07:18 UTC). Ngay 2026-11-16 = XAM (restart) - khong tinh. Nhan `ii` cua 2026-11-15 KHONG dung (ADD22 muc 2.3).
- Dieu kien FIN cua ngay (ii) (ADD21 muc 4): `ly_do=FIN_KHONG_BIN` = 0; `[KLINE-FIN] loi ghi` = 0; FIN_THIEU = 0 (duoc phep, ghi so);
  MINUTE-INCOMPLETE = 0.
- md5 trong jars.json cua jar dich: parity_v12_gmicro.json target.md5_jars_json = 641803565297d4065d90245e04a00f11 (target_md5_ok=true).
- (i) (tham khao, truong gmicro_i lay tu report): 7 ngay SACH = 11-07, 11-08, 11-09, 11-11, 11-12, 11-15, 11-17.

## 4. Ghi nhan them (KHONG phai tieu chi ADD21/22; ghi de nguoi doc gate biet)
- SUBMIT c3 ke tu smoke_start: 0 (`grep -a -c -F SUBMIT full.log` = 0) => (iv) sizing = KHONG DO DUOC (xem SIZING_IV_2026-11-19.md).
- 17/11/2026 22:52:06 +07: tin hieu DCA cua LEGACY (`DCA big loss`, DCA_LEVEL1; alt -3,23 %/15 phut). Duong lenh that c3: HOURLY
  `entry{DCA_NOT_HOLDING=34}`, 0 SUBMIT, 0 `[LIVE-DCA-GRID] site` (dung thiet ke, khop AUDIT_LEGACY_DCA_1116.md). So GIAY: 12 dong
  `[SHADOW] would-BUY` + 12 `[SHADOW] add-leg ... leg=2` (leg co LEGACY ~590-840 USDT margin) => U giay 0,047 -> 0,2458; luc 19/11 09:21
  u=0.1170, n_skipfull=0. Tren live skipFull doc U cua so GIAY (GATE_LIMITS_MICRO.md muc B) => co the lam IT lenh hon sim.
- md5 model tren 242 (md5sum, khop AUDIT_GOLIVE_1116_D dong 65): net015 g015x26_f15_cut20251231.onnx e65e683b; S1 s1a2x1_cut20251231.onnx
  511add62; p15 Model_Regressor_Return15M.onnx 8ec99757 (WFO fold_20, train toi 2026-03-31).
- Tuoi model va khuyen nghi train lai truoc PILOT: docs/prereg/PREREG_DIAG_NOTRADE_1117.md + ~/claude_master/v12/DIAG_NOTRADE_1117_{A,B}.md.
