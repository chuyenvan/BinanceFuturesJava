# PILOT_M_DRAFT_NOTES - ghi chu nguon cho ban nhap PREREG_PILOT_M (agent soan thao, 2026-11-25 ~12:30 +07)
Code = git show 4fdda6f8:<path> trong ~/claude_master/w3/c3_hotfix (source jar live theo REVIEW_1124 muc 0). P = src/main/java/com/binance/chuyennd.
Log = pull242/<D>/logs/full.log*.gz (Oracle), CHI dong co thoi gian < 2026-11-24 07:00 +07 (gop 19..24/11, loc regex ngay, sort -u ->
/dev/shm/pm_pre.log, 216 921 dong, dong cuoi 24/11 06:59:37). Khong mo output rig, khong mo blind/.

## A. Hang so / chuoi log da xac nhan (gia tri - nguon)
| Muc | Gia tri | Nguon |
|---|---|---|
| arm | 0.07f | P/tradecore/selector/LiveProfileC3.java:51; banner log 19/11 09:31:12 "arm=0.07 timeStop=168h ... sizeCap=4.5%" |
| time-stop | 168 h | LiveProfileC3.java:53; TsMktExt.java:48 BASE_HOURS |
| X14 gia han | 336 h (toi 504 h) | TsMktExt.java:50, decide :105-112 |
| X14 PENDING / grace | FINAL_DEADLINE 20', PENDING_MAX 22', START_GRACE 20' | TsMktExt.java:53-55, flagFor :221-232 |
| X14 log | "[TS-EXT] defer-START/-END", "flag day=", "status ... flagToday=" | TsMktExt.java:368,377,386,282,402 |
| X14 file | run/ts_ext_daily.csv.a1 (khong phai ts_ext_daily.csv mac dinh :46) | banner log 20/11 06:17:45 "[TS-EXT] BAT ... file=..." |
| nhip exit | EXIT_EVERY_MS 10 000; vong ops 5 000; RECON 3 600 000; RESOLVE 30 000 | P/c3live/runtime/C3LiveRuntime.java:75-80 |
| guard Urgent | DEADLINE_MS 61 000; REASON STOP_LOST_61S | P/c3live/exit/C3StopProtector.java:33-34 |
| time-stop chi khi chua arm | priceSL NaN | P/c3live/exit/TrailingStopManager.java:207-231 |
| ratchet | nsl > sl moi doi | TrailingStopManager.java:232-238 |
| doi stop | >= cu + 1 tick VA >= cu x 1.001 | TrailingStopManager.java:55 (DEFAULT_MIN_MOVE_FRAC), syncStop ~:266-279 |
| log arm / stop / TS / reset / -4130 / -2021 | xem prereg muc 2 | TrailingStopManager.java:211,331,226,244,348,355 |
| trail | round((peak-gap)/0.005)*0.005, gap=min(peak*GIVEBACK, maxGap) | P/tradecore/TradeUtils.java:40-58 |
| gap / giveback live | 0.03 / 0.03 / 1 (KHONG phai mac dinh code 0.08 / 0.03 / 0.5 Configs :144,145,203-205) | REVIEW_1124 s3 (env whitelist 11-16) + A1_RLIVE_RUN3 4.1 (16/16 khop) - KHONG co trong banner |
| U_MAX | 0.60 | Configs.java:177; ERRATA2 s4 |
| F_BASE / SCALE / weights | 0.015 / 6.0 / [1,1,1,1], FIX_B2 | banner [LIVE-SIZING] log 20/11 06:17:35; DcaUtils.java:47-64 |
| sizeCap / minBudget | 4.5 % / 5 USDT | banner LiveProfileC3; C3LiveEntry.java:347 |
| managerBudget | C x F_BASE x (1-U/U_MAX) / tongW | TradeUtils.java:125-145 |
| lam tron | floor(b/px, marketStepSize); notional <= b; minNotional | P/c3live/filters/SymbolRules.java:117-157 |
| SUBMIT log | "[C3-LIVE] SUBMIT {sym} {lvl} SUBMITTED cid= qty= budget= legIdx= notional= U_before=" | C3LiveEntry.java:286-295, Result.toString |
| skip DEBUG | LEGACY, DCA_NOT_HOLDING, DCA_NOT_DUE, DCA_OFF khong vao log INFO | C3LiveEntry.java:296-301 |
| DCA levels | [-0.5,-0.75,-0.9], legs 3 | banner [LIVE-DCA-GRID] 20/11 06:17:35; Configs.java:217-218; DcaUtils.shouldDcaGrid :32-43 |
| DCA log | "[LIVE-DCA-GRID] site= due=", "live-only due=" | P/trading/DetectEntrySignal2TradeNormal.java:1222-1250 |
| tsFirstLeg | = nowMs khi tao cum; persist ts_first_leg | P/c3live/book/LiveBookC3.java:539,1070,1170 |
| ly do dong | TRAILING_STOP, LIQUIDATION, ADL, DELIST_SETTLE, EXTERNAL, BOT_CLOSE | P/c3live/fill/FillAccounting.java:49-54 |
| CLOS / BOOK log | "[C3-LIVE] cum {} DA DONG tren san ({})" / "[C3-LIVE-BOOK] dong cum ... realized= phi=" (CO PnL) | FillAccounting.java:421; LiveBookC3.java:737 |
| truot ra trailing | truot = 1 - px/stop | FillAccounting.java:233 |
| short | "[C3-LIVE] vi the AM (short)" | FillAccounting.java:280 |
| truot vao | FILL ... ref= slip=; C2 = fill/ref - 1 (mua) | P/c3live/exec/C3LiveOrderExecutor.java:435-437; P/ops/KillSwitchEngine.java:221-225 |
| C2 | warn 0.017, slip 0.025, count 3, 24 h, signed=1 | KillSwitchEngine.java:140-143; OpsConfig.java:130-133, env :117-121; banner [KILLSW] "C2 signed=1" |
| A40 / C6 / C4 | -0.40 / -0.40 / 90 vi the | KillSwitchEngine.java:101,99,97 |
| KILLSW log | "C2_WARN ... warn> slip>", "LATCH them", "HOURLY ... dd= acct_dd= latch=" | KillSwitchEngine.java:666,937,1176-1194 |
| RECON | equityTol 0.01, matchToRelease 2; "HOURLY khop: doi chieu qty c3 (n cum) ... streak=" (che do qty) | P/c3live/recon/Reconciler.java:62-63, 800-850 |
| RECON lop B / leo thang | xem prereg I11 | Reconciler.java:588,597,646 |
| Flattener | 5 lenh / 10 s | P/c3live/risk/C3LiveFlattener.java:46-47 |
| JVM start | "MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager"; "[C3-LIVE] khoi dong adapter=..." | log; C3LiveRuntime.java:433 |
| monitor | "TOM TAT: adapter= C3_CAPITAL= push= latch= so_c3= ... jar= ... deadman= ... khan_canh_bao=" | c3_ops6 082c10f5 golive_monitor.sh:284; cron log ~/claude_master/deploy/golive_monitor_cron.log |
| pull ngay D | ws_ms = D 00:00 UTC = D 07:00 +07 | pull242/2026-11-21/check.txt |

## B. Khac voi so trong khung MASTER
1. "MIN_MOMENTUM_15M = 0,008" cho DCA: KHONG co. MIN_MOMENTUM_15M mac dinh 0.02284 (Configs.java:437, env SIM_MIN_MOMENTUM_15M :843),
   chi la nguong du phong gate warm-up (LiveGateRollingRatio.java:381,405,410). DCA chi theo muc giam gia tu gia khop leg 0. => CHUA XAC
   DINH nguon 0,008; prereg khong dung.
2. "X14 / TS_MKT_EXT" la ly do dong: khong co trong jar; X14 chi hoan time-stop; ly do khi cat van la TIME_STOP_168H.
3. "time-stop dau tien 10:39-11:08": 10:39 la BLESSUSDT (da dong 21/11 12:47). 8 cum mo tai T_cut: MMT due 28/11 10:45:08, 7 cum
   con lai 28/11 11:08:08-11:08:22.
4. "RECON khop qty = 0 cho symbol": Reconciler khong in qty symbol da dong; thay bang I11 (a)-(c).
5. "ts_ext_daily": file live la run/ts_ext_daily.csv.a1; prereg cham bang dong log, khong doc file.
6. "golive_pilot_down.sh" cho bac DO: theo PILOT_DAY_1126 muc D, pilot_down chi khi phang; dung mo moi = golive_live_off.sh MODE=drain.
7. Sizing "x ~0,963": dung = x(1 - 0,0225/0,6) = 0,9625 tren (1 - U/0,6) moi leg (lam tron qty lam lech nhe).
8. Harness 8d397ce2 KHONG chay duoc nguyen trang cho ngay moi: run_rlive.sh:29-33 co dinh START 2026-11-19 09:31, CAP 1000, TCUT
   ^2026-11-2[0-4] 07:00$ (exit 15); rig bat dau so rong (A11). => can wrapper moi + A1.

## C. CHUA XAC DINH
- Nguong C2 HIEU LUC tren 242 (env LIVE_KILLSW_C2_* co the ghi de; banner khong in; khong co dong C2_WARN truoc T_cut). Cam doc env.
- TS_MAX_GAP / TS_GIVEBACK_RATIO HIEU LUC: chi gian tiep (whitelist 11-16 + A1 khop 16/16); banner khong in.
- Leg DCA qua so giay (createOrderBuyRequest) co bi entryGate chan hay khong - chua doc het duong (DetectEntrySignal2TradeNormal:1214-1400
  doc mot phan). Khong anh huong D1; anh huong D3 (prereg cho phep dong ly do chan).
- oracle_seen: chi log tren 242 /var/lib/c3_oracle_seen/oracle_seen.log + Telegram; khong co nguon Oracle.
- Banner 20/11: "tai_khoan=CHINH(pham vi c3)" va RECON chay che do QTY (nhanh tai khoan chinh), trong khi brief ghi "tai khoan con";
  monitor in "tk=SUB". Khong kiem duoc (cam doc env). MASTER xac nhan banner sau restart 26/11.
- marketStepSize ngay D: can file run/c3live_exchangeInfo.json (MASTER chep chi doc) - chua co quy trinh hang ngay.

## D. Khong kha thi theo khung -> thay the
- M-E "harness khong sua" -> wrapper moi (prereg 1.2) + M-E0 chi log (1.3).
- 7 bat bien "tren chinh log live": chi I3, I4 (E3, E4) chi log; I1, I2 can kline Vision; I5, I6 can mark Vision; I7 can rig.
- M-D "momentum 0,008" -> bo; "lich/khoang cach leg" = levels grid; DCA_NOT_DUE khong log => chieu nguoc can Vision (D3).
- M-K "RECON qty=0" -> K3 + I11; oracle_seen -> KHONG_CHAM_DUOC (Q4).
- Vision >= 10-01 cho ngay moi: ngoai pham vi ADD4 => can owner (Q1).

## E. Su co pham vi / nhin du lieu (khai bao trung thuc)
- Khi kiem duong dan cron monitor, lenh `tail -3 ~/claude_master/deploy/golive_monitor_cron.log` in 3 dong thoi diem 2026-11-25 12:02
  (SAU T_cut): dong DD tk con (tmb, tmb0), "OK deadman", "TOM TAT ... so_c3=7cum ...". Khong luu, khong dung cho bat ky nguong / thiet ke.
  (So 7 cum cung da co san trong PILOT_DAY_1126 muc C/F.) Ngoai dong nay: khong doc gi >= 2026-11-24 07:00.
- Grep banner 20/11 06:17-06:19 in ra 2 dong "Telegram respon" chua ten / id chat (khong phai secret API); khong chep vao file nao.
- Doc bao cao A1_RLIVE_RUN3 / RLIVE_RUN3 / MASTER_CONCLUSION (ket qua OW2, truoc T_cut) - da duoc phep; cac nguong moi lay tu code, khong
  tu so lieu do (ngoai le: bang 8 cum mo, lay tu log < T_cut).
- Thong ke tren log < T_cut chi de kiem kha thi: ERROR 0, KHAN 0, MainClass 5+ dong ngay 19/11, RECON streak reset ve 1 khi restart,
  LIVE-DCA-GRID 0 dong, -4130 1 su kien (BLESS 21/11 12:20:19).

## F. v2 sau A1_PILOT_M (FAIL v1 8cd03322) - 2026-11-25
v2 sha256 3cc4f815e9db6d18dd59be7692e33bacedc2bf5f195e92d15b7a6aac2c358bce, 332 dong; v1 giu tai v12/PREREG_PILOT_M_v1_draft.md
(diff: 141 dong bo / 202 dong them). Moi diem B duoc nguoi soan TU doc lai code 4fdda6f8 truoc khi sua:
| Muc | Sua o v2 | Xac nhan code |
| B1 | K4 (muc 8), M-T (A) (muc 3): final=true|false deu hop le | TsMktExt:251 finalPass = since >= FINAL_DEADLINE; log flag :280/:285 |
| B2 | muc 4: gate DCA (dong AI PASS / SKIP ORDER), D3 -> THEO DOI, ghi chu MIN_MOMENTUM sua | DetectEntrySignal2TradeNormal :1302-1316, :1333, :1338; AIRejectFilter :200-203; BIG_DOWN bypass :1302-1312 |
| B3 | D1(b) k == legCount (gom leg 0) | C3LiveEntry :242 legIdx = legCount |
| B4 | I4(b) cua so [t_STOP-5 s ; t_STOP+61 s] | log 21/11 12:16:22.000 ALGO NEW truoc 12:16:22.021 STOP (BLESS) |
| B5 | trang thai KCD_CAU_TRUC (muc 0), muc 10 phu kin, D1 VI_PHAM -> DO | - |
| B6 | muc 5: tierMul sau tran + minBudget, C_eff = min(3 nguon), r va VANG TIER/AVAIL | C3LiveEntry :263-268; tradecore/CoinRankManager.java ~:122-127 (A1 ghi :121-128); C3MainEquity :163-170, CANH BAO ky quy :174 |
| B7 | muc 3: tach thread [pool-3-thread-1], cua so (due-2 s ; due+120 s] | log 21/11 21:01:00 defer-START AIO/BEAT, 22/11 03:54 ETC tren [pool-3-thread-1] |
| B8 | M-E0 (b) BIG_DOWN, (d) them mau ket thuc khong khop | FillAccounting :211; Market level :365/:1474 |
| B9 | K2 luat moi + bo chep tmb/eq/dd | - |
| m1-m13 | DA AP tat ca: m1/m2 I11; m3 I2; m4 I9(b)+F float32; m5 I1; m6 ghi chu GAP; m7 M-X; m8 K6 + muc 10; m9 K1/K5; m10 Q1; m11 K2; m12 muc 0 + 11; m13 dau file | - |
So moi do nguoi soan dat o v2 (khong co trong A1 / code; MASTER duyet): K5 ngay 26/11 chap nhan khoang trong log <= 15 phut; D1(e) cua so
[dts+60 s ; t_SUBMIT] cho dong AI PASS; M-X median luy ke chi xet khi >= 10 leg.
Phan bien A1: KHONG co diem bat dong ve noi dung. Ghi chu nho: (1) B6 tham chieu CoinRankManager o goi tradecore (khong phai selector);
(2) B7 chua tung quan sat defer-START cua duong THAT (thread du kien [C3LIVE-OPS] theo TrailingStopManager chay trong opsLoop) -
neu thread that cung la pool-3 thi M-T(B) = KHONG_CHAM_DUOC, A1 nen xac nhan lai khi co su kien dau tien.
