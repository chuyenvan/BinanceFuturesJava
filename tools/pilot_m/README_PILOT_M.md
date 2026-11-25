# README_PILOT_M - bo cham hang ngay phan CHI LOG cua PREREG_PILOT_M (prereg 2a21fe35 + ERRATA1 c0f35f3c + ERRATA2 efc4f9c1)
Trang thai: CHUA COMMIT, CHUA qua A1. Ket qua chi dung sau khi A1 duyet (prereg muc 12).

## Chay
- Chinh thuc (MASTER, sau A1):  `~/claude_master/vz_e1_wt/tools/pilot_m/pilot_m_daily.sh 2026-11-24 --official`
  - ngay 2026-11-26 them `--pilot-on-start "2026-11-26 HH:MM"` (gio bat dau lenh pilot_on, +07); thieu => K1, K2 = KHONG_CHAM_DUOC.
  - `--external-noted SYM,SYM` (cum dong EXTERNAL co ghi chep owner), `--delist-noted SYM,SYM` (MASTER co ghi chep huy niem yet, E4),
    `--drain-window "a;b"` (khung drain co ghi chep, K2).
  - `--official` TU CHOI neu gio hien tai < D+1 07:10 +07 (ERRATA2 F1); ghi `~/claude_master/v12/pilot_m/D_<yyyymmdd>.{md,json}`; KHONG ghi de file da co (prereg muc 0); cam di cung
    `--max-ts/--now/--pull-root/--cron-log/--state-start` khac mac dinh. Khong `--official` thi bat buoc `--out-dir` khac thu muc do.
- Thu / go loi: `pilot_m_daily.sh <D> --out-dir <dir> --max-ts "2026-11-24 07:00"` (`--max-ts` bo MOI dong log/cron >= moc,
  dong bi bo khong parse, khong dem, khong in).
- Test: `test/test_pilot_m_daily.sh` (du lieu tong hop trong `mktemp -d`, xoa sau khi chay) => "KET QUA x/y".
  Mutant: `test/run_mutants.sh` (17 mutant song cua A1 dung lai, chay ca bo test tren tung mutant) => "MUTANT GIET x/20" (17 cua A1 + S1, S1b, chan gio official).
- Dau vao: `pull242/<D>/{COMPLETE,check.txt,logs/full.log*.gz,dumps/sel_dump_*.csv.gz}` + pull cac ngay tu `--state-start`
  (mac dinh 2026-11-21, prereg muc 0) toi D-1 (chi cua so tung ngay, dung trang thai cum) + `golive_monitor_cron.log.1` va
  `golive_monitor_cron.log` (dong TOM TAT, E2).
  Cua so D = [D 07:00; D+1 07:00) +07; doc them <= 2 h SAU cua so trong CHINH file pull D (lookahead cho han 61 s/300 s/600 s).
  Banner khoi dong / [KILLSW] HOURLY / RECON HOURLY / C2_WARN / CANH BAO ky quy lay tu moi dong cua cac file da doc (ke ca truoc cua so)
  de biet JVM dang chay (C3_CAPITAL), eq_lo, streak.
- Dau ra: dong dau md `PILOT-M D=.. cham_luc=.. bac=.. prereg=2a21fe35+E1+E2 cong_cu=<sha256[:12] pilot_m_daily.py>`; bang 1 dong/muc
  (M-E, M-E0, M-I, M-T, M-D, M-S, M-X, M-G, M-K); dong equity chi ti le (dd, acct_dd); dong kiem_cheo de MASTER dien.
  json: moi muc {trang_thai, mau, so_vi_pham, su_kien_vi_pham[t, symbol, ly_do, dong_log da loc], su_kien_khong_cham_duoc, ...},
  bac_muc, hai_ngay_vang_lien_tiep_cung_muc (doc D_<D-1>.json cung thu muc), du_lieu (dong parse / khong parse theo mau).

## Muc -> ham -> dieu khoan (prereg 2a21fe35 + ERRATA1 c0f35f3c + ERRATA2 efc4f9c1)
| Muc | Ham | Prereg / ERRATA1 |
|---|---|---|
| M-E0 (a)(b)(c)(d) | chk_ME0 | 1.3 (dong 69-76); E10 (level leg 0 khac => VI_PHAM) |
| I3 | chk_I3 | 2.1 dong 101-102 |
| I4 (a)(b)(c) + L-K (-4130) | chk_I4 | 2.1 dong 103-106, muc 6 dong 247-248 |
| I4 (d) | chk_I4 | E3 (TRIGGERING/TRIGGERED cua cid STOP cuoi, +-61 s) |
| I8 | chk_I8 | 2.2 dong 114-116; E4 (DELIST_SETTLE chi khi --delist-noted) |
| I9 (a)=I3,(b) F float32,(c) | chk_I9 + trail_sl | 2.1 dong 89-93, 2.2 dong 117-119 |
| I10 | chk_I10 + win_clusters | dong 120-125; E4; E6 (cum dong = CLOS / BOOK / SFIL du qty; BOOK<->CLOS +-600 s) |
| I11 (a)(b)(c) | chk_I11 | dong 126-133 (moc = su kien dong dau tien theo E6) |
| I12 (a)(b)(c)(d) | chk_I12 | dong 134-135; E11 |
| M-T (A)(B) | chk_MT | muc 3 dong 138-169; E7 (RST sau ARM => lai thuoc time-stop); E13 (NA = OFF) |
| M-D D1 (a)-(e) + ghi 15M | chk_D1 | muc 4 dong 192-195; E8 (leg DCA khong khop: bo (a)) |
| M-S S1-S9 | chk_MS | muc 5 + E1/E5 + ERRATA2 F2 (S1 r_cap > 1,2(1+1e-6) DO; S1b (1+1e-6; 1,2(1+1e-6)] VANG TIER; S3 VANG EQ_DUOI; S5/S6 KCD_CAU_TRUC) |
| M-X | chk_MX | muc 6 dong 235-248 |
| K1 | chk_K1 | muc 8 dong 262-265; E12 (khung [pilot_on; +60']) |
| K2 | read_cron + chk_K2 | E2 (thay noi dung) + ERRATA2 F1 (cuoi ngay = min(D+1 07:00, thoi diem cham)) + R4 |
| K3..K6 | chk_K3..chk_K6 | muc 8 dong 272-282 (+R2) |
| fail-closed | classify / fam_bad | E9 (0 dung sai, tru MKT/AIPASS/SKIPORD/DCAGRID 0,1 %); A1 T1 (tien to + OTHER_TPL) |
| bac | bac_of / render | muc 10 dong 296-311 + E5; muc 9 dong 287-294; dong dau prereg=2a21fe35+E1+E2 |
| KCD_CAU_TRUC | KCDC_ITEMS | M-E, I1, I2, I5, I6, I7, D2, D3, D4, L-S, L-S2, M-G, K7 (Q4), M-S S5/S6 (R3) |

## Mau dong log (FAMS trong pilot_m_daily.py) - code c3_hotfix 4fdda6f8, P = src/main/java/com/binance/chuyennd
Header: `^dd/MM/yyyy HH:mm:ss.SSS LEVEL [thread] logger: msg` (HDR). Dong co tien to quan tam ma khong khop mau chat => "khong parse".
Dong dau md: `PILOT-M D=.. cham_luc=.. bac=.. prereg=2a21fe35+E1+E2 cong_cu=<sha256[:12]>`.

| Ho | Mau (tom tat) | Code |
|---|---|---|
| SUBMIT | `[C3-LIVE] SUBMIT <SYM> <LVL> SUBMITTED cid=c3-<SYM>-<barMin>-<k> qty= budget= legIdx= notional= U_before=` | P/c3live/entry/C3LiveEntry.java:295 |
| FILL_EXEC | `[C3-LIVE-EXEC] FILL <SYM> <cid> qty= avg= ref= slip=` | P/c3live/exec/C3LiveOrderExecutor.java:435 |
| FILL_STREAM | `[C3-LIVE-FILL] xac nhan qua stream <SYM> <cid> qty= avg= ref=` | P/c3live/fill/FillAccounting.java:202 |
| LEG_END | `[C3-LIVE-FILL] leg <SYM> <cid> ket thuc <X> khong khop => huy giu cho` | FillAccounting.java:211 |
| EXEC_END | `[C3-LIVE-EXEC] <SYM> <cid> ... => huy giu cho` / `executor tu choi cid=<cid> => huy giu cho` | C3LiveOrderExecutor.java:266,304,321,553,562 |
| PXCORR | `[C3-LIVE-EXEC|FILL] <SYM> <cid> PX_CORRECTED [<a>] -> <px>` | C3LiveOrderExecutor.java:440,504; FillAccounting.java:186 |
| ARM | `[C3-LIVE-TRAIL] arm <SYM> entry= px= peak= SL=` | P/c3live/exit/TrailingStopManager.java:211 |
| STOP | `[C3-LIVE-TRAIL] <SYM> <ARM|MOVE|..> stop= cid=c3s-.. mode=(closePosition|qty+reduceOnly) (cu=<cid|null> <px>)` | TrailingStopManager.java:331 |
| TS / RST | `TIME-STOP <SYM> entry= px= gio_giu= => dong MARKET reduce-only` / `<SYM> khong con arm (DCA reset) => huy stop <cid>` | TrailingStopManager.java:226 / :244 |
| E4130 / E2021 / STOPERR / CANCERR | `san tu choi stop closePosition thu 2 (-4130)` / `stop <P> se kich ngay (-2021` / `dat stop <cid> loi .. => thu lai nhip sau` / `huy stop <cid> loi => thu lai nhip sau` | TrailingStopManager.java:348/355/362/477 |
| ALGO | `[C3-LIVE-FILL] ALGO_UPDATE <SYM> caid=<cid> X=<..> ai=<..>` | FillAccounting.java:294 |
| SFIL | `[C3-LIVE-FILL] <SYM> stop khop <q>@<px> (stop=<P> truot=<s>)` | FillAccounting.java:233 |
| CLOS / BOOK | `[C3-LIVE] cum <SYM> DA DONG tren san (<r>) qty=` / `[C3-LIVE-BOOK] dong cum <SYM> ly do=<r> legs= qty= avg= exitQty=` | FillAccounting.java:421 / P/c3live/book/LiveBookC3.java:737 |
| VIAM | `[C3-LIVE] vi the AM (short) <SYM>` | FillAccounting.java:280 |
| RECON_H / LECH / van lech / lop B / GO | `[C3-LIVE-RECON] HOURLY khop: doi chieu qty c3 (<n> cum) lech max=..% streak=<s>` / `LECH QTY c3` / `van lech qty` / `<SYM>: cum so vua chot nhung .. (lop B)` / `<SYM>: 2 lan doc phang .. GO chan rieng symbol (lop B)` | P/c3live/recon/Reconciler.java:844 (778) / 834 / 840 / 588,291 / 646 |
| leo thang (dem chuoi) | `leo thang UNKNOWN` | Reconciler.java:276,597,635 |
| TSX_FLAG / STATUS / DEFER / NOFLAG | `[TS-EXT] flag day=<d> flag=<F> .. final=<b>` / `[TS-EXT] status now= flagToday=` / `[TS-EXT] defer-START <SYM> age_h= flag=` / `[TS-EXT] chua co co ngay` | P/tradecore/selector/TsMktExt.java:282(280) / 402 / 368 / 229 |
| KS_HOURLY / C2WARN / LATCH | `[KILLSW] HOURLY hour= .. eq= peak= dd= [acct_eq= acct_peak= acct_dd=] [latch=]` / `C2_WARN symbol= side= adverse= warn> slip>` / `LATCH action=.. code=` va `LATCH them code=` | P/ops/KillSwitchEngine.java:1176-1196 / 666 / 929, 937 |
| BANNER (chi logger *.C3LiveRuntime) / RECOV / RECON_START / MAINCLASS | `[C3-LIVE] khoi dong adapter= .. cum= .. c3_capital= .. killSwitchArmed= X14=` / `khoi phuc sau restart: con <n> leg treo` / `reconcile khoi dong XONG` / `MainClass: ..` | P/c3live/runtime/C3LiveRuntime.java:433 / 482 / 486; P/utils/Utils.java:621 |
| AIPASS / SKIPORD | `AI PASS [<SYM>] Reason: <..> symbolPred: <..>` / `SKIP ORDER [<SYM> <LVL>] due to ..` | P/trading/DetectEntrySignal2TradeNormal.java:1338 / 1333 |
| DCAGRID | `[LIVE-DCA-GRID] site=<s> due=[..]` / `site=<s> live-only due=<SYM>` | DetectEntrySignal2TradeNormal.java:1231 / 1245 |
| MKT | `Market level change: <yyyyMMdd HH:mm> level: <L> symbols:` / `Market level:<yyyyMMdd HH:mm> <L> <SYM> ..` | DetectEntrySignal2TradeNormal.java:365 / 1474 |
| EQWARN / NOPRICE / MERGED | `[C3-LIVE-EQ] CANH BAO ky quy` / `khong doc duoc gia realtime` / `KHAN: <SYM> MERGED`, `<SYM> het MERGED:` | P/c3live/risk/C3MainEquity.java:174 / C3LiveRuntime.java:582 / P/c3live/scope/C3MergedGuard.java:199,217 |
| Cron K2 | `^[yyyy-mm-dd HH:MM:SS] TOM TAT: adapter= C3_CAPITAL= push= latch= .. jar= .. deadman= .. khan= .. khan_canh_bao=<phan con lai>` | c3_ops6 ops/c3live/golive_monitor.sh:284 |
Dem chuoi con (khong parse): " ERROR ", "KHAN", "LECH QTY", "van lech qty", "CHAN vao lenh", "leo thang UNKNOWN", "[C3-LIVE-EXEC]"+" KHONG khop",
"(-4130)", "(-2021", "gui lai CUNG cid", "=> UNKNOWN", "TU CHOI", "[KILLSW] C2_WARN", "[KILLSW] LATCH".

## Lua chon cai dat con lai (A1 coi la hop le: so cu 2, 4, 8, 9, 11, 13, 14) + phat sinh moi
1. (cu 2) I3/I9(a): P > P_truoc va P*1000 >= P_truoc*1001*(1-1e-9) (Decimal; 1 tick suy tu P > P_truoc vi deu la boi tickSize);
   MOVE khong co STOP truoc trong cung pha => VI_PHAM.
2. (cu 4) D1(c)(e): "cung phut quyet dinh" = [dts+60 s ; t_SUBMIT].
3. (cu 8) I11(b): dong leo thang/LECH QTY cua cua so D trong [t; t+24 h] sau su kien dong; cum dong ngay truoc cham tiep ("mang sang").
   I11(c) cham vao ngay chua han 2 h. I11(a) n_ky_vong = cum mo co leg khop, khong leg treo, chua TS/SFIL, khong MERGED.
4. (cu 9) I4(c): cum chua dong, chua thay CANCELED stop bi thay => KHONG_CHAM_DUOC.
5. (cu 11) K3/K4 "tru gio JVM dung" = so gio trong cua so khong co dong log nao; dong RECON dau tien sau banner phai streak=1.
6. (cu 13) K2 ngay 26/11: khung mien = [pilot_on ; TOM TAT hop le dau tien push=ON va C3_CAPITAL=5000] (<= 60 phut).
7. (cu 14) M-X: phan vi nearest-rank; trang thai VI_PHAM khi cham nguong muc 6 (bac VANG), DAT neu co leg, KCSK neu 0 leg.
8. (moi, T1) Dong bat dau bang tien to A1 khong khop ho nao: neu khop mau OTHER_TPL (chuoi literal trich tu code 4fdda6f8 co tien to
   do, KHONG gom chuoi cua ho cham, so khop tien to, {} = bat ky; +3 mau ghep chuoi TrailingStopManager :307, Reconciler :276,
   KillSwitchEngine :1157) => bo qua; khong khop => khong parse cua gia-ho "PFX:<tien to>" (tinh cho moi ho co tien to do).
9. (moi, E6) BOOK dong cum trong trang thai (cum mo bi go tai BOOK neu CLOS chua toi). "SFIL du qty ma khong co CLOS trong 600 s"
   xet CLOS cung symbol trong [t_SFIL - 600 s ; t_SFIL + 600 s].
10. (moi, E2) Dong TOM TAT hop le thieu truong deadman= => KHONG_CHAM_DUOC dong do (log thieu truong, muc 0) - chi gap o cron truoc
   22/11 17:24. Dong khong hop le: (b) van xet latch != NONE (ke ca rong), khan=KHAN, jar (khi khong rong).
11. (ERRATA2 F1 xac nhan) moc cuoi doan cuoi ngay = min(D+1 07:00, thoi diem DOC cron = cham_luc, --max-ts), khong phai dong cuoi
   trong file (neu hieu la dong cuoi thi monitor chet khong bao gio sinh khoang trong - ca pha B10).
12. (ERRATA2 F3 xac nhan) flag=NA(->OFF) = OFF chi cho M-T; K4 van doi flag=(ON|OFF) => NA => K4 VI_PHAM (VANG).
13. (ERRATA2 F2) S1/S1b nhu bang tren; chu y: r_hi >= r_cap nen 1,02 < r_cap < 1,18 luon kem S2 => DO.

## An toan du lieu
san(): bo gia tri realized/phi/pnl*/tmb/tmb0/eq/acct_eq/acct_peak/equity/funding/avail*/bal*/margin/wallet*/upnl/fee/rp (=> <X>),
peak= trong dong [KILLSW]/TOM TAT, moi key chua WALLET/BALANCE, so_du*/equity_so/upl*/chot/moc/chuyen/dinh/tmb*/eq*,
noi dung ngoac sau "eq = C3_CAPITAL + (", dd=/key= trong TOM TAT, toan bo noi dung [C3-LIVE-EQ] va "Telegram respon", signature= => <SIG>,
token `[0-9]{8,10}:[A-Za-z0-9_-]{30,}` => <TOKEN>. eq= chi dung trong bo nho (M-S). Bao cao chi in ti le (r, dd, bps), khong so tien.

## Gioi han
Khong kiem duoc: gia tri env hieu luc (TS_MAX_GAP, giveback, C2*, MIN_MOMENTUM_15M) - I9(b) gia dinh GAP 0,03 / GIVEBACK 1 theo prereg;
stepSize/tickSize (khong co exchangeInfo); oracle_seen (K7); moi phan can Vision/rig. Lookahead chi trong file pull D (~83 phut).
Chua co du lieu that cho: DCA, TIME-STOP, defer-START [C3LIVE-OPS], PX_CORRECTED, lop B, LECH, LATCH, restart trong ngay - cac mau nay
chi kiem bang test tong hop + doi chieu chuoi code.
