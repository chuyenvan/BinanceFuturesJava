# PREREG_BOOKCAP — overlay tang BOOK/VON: cap exposure dang mo tren X1_C3_FULL (48 thang)

Chot: 2026-09-11, commit TRUOC khi cai code / chay run. Nen `X1_C3_FULL` (canonical `devrun/X1_C3_FULL_PARITY_R`, md5
printDone `2478e90d...`, equity 111,428 / n=2,266). Cua so 2022-01-01..2025-12-31 (`SIM_END_DATE=20251231`), bins
`/home/ubuntu/predwf_map_s1a2_x1` KHONG rebuild, dataset `/home/ubuntu/wfo_ds_x1` (da co), `TICKER_SOURCE=file`,
`EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json`. KHONG cham HOLDOUT 2026, KHONG cham 242.

## 0. Vi sao (DEV_COLLAPSE_CHECK_20260911)
Book mo: median 4, p90 12-15, max 27-30 lenh. Book chi phinh trong dump va luc do 87-100% lenh dang mo la loser-tuong-lai;
25 collapse-day (>=4 time-stop/ngay) trong 48 thang, te nhat -8,641/ngay (2025-11-12). Khong gian EXIT da NULL (E1, X2_EXIT48),
gate/selector/K deu NULL. Tang duy nhat chua do: quyet dinh "co them exposure khi book da nang khong". Overlay nay KHONG doi
selector, KHONG doi exit, KHONG co model.

**Ky vong ghi truoc:** CAGR se KHONG phan biet duoc (sd_boot 3-5pp, xem AUDIT_GATEDYN_GD92). Cai do duoc la maxDD/UW theo nam
va so collapse-day (quan sat, khong CI). Cap se BO mot phan chain pump sinh lai (+32k trong DEV) — co the lam rate xau di.
Ket qua "khong phan biet duoc" la dau ra hop le.

## 1. Co che — chot cung
- 2 key moi qua `Cfg.get`, khai trong PROFILE (khong doc env truc tiep), `tools/check_cfg_gateway.sh` phai OK:
  `SIM_MAX_OPEN_POSITIONS` (int; khong khai/<=0 = TAT) va `SIM_MAX_OPEN_NOTIONAL_PCT` (float 0..1; khong khai/<=0 = TAT).
- Diem cam: `SimulatorMarketLevelTicker1MStopLoss.createOrder(...)`, CHI khi `levelChange == PREDICT_SYMBOL_TRADE`, SAU gate
  thi truong/AIRejectFilter va TRUOC budget/tier. Leg DCA_LEVEL1 / BIG_DOWN KHONG bi chan (khong doi luat leg cu).
- Dem: `n_open` = so lenh dang mo (moi status chua DONE, moi level). Notional = sum(entry x quantity) cua lenh dang mo;
  equity = balance thuc hien `b` tai tick (khong MTM, de tat dinh). Vi pham => reject, ghi `TickDecisionLog` reason moi
  `D_BOOK_CAP`, dem so lan chan va so tick co chan (in cuoi run).
- TAT (khong khai 2 key) => byte-identical: **CONG NGHIEM THU** chay lai `x1_c3_full.properties` bang jar moi, `cmp` printDone
  (bo header) voi PARITY_R phai rc=0, md5 = `2478e90d...`. FAIL => sua code, KHONG chay bien the.
- Java SLF4J; khong System.out/err/printStackTrace. Khong sua exit/gate/selector.

## 2. Bien the — DUNG 3, KHOA
| tag | profile | key |
|---|---|---|
| `X1_C3_FULL_CAP12` | `profiles/x1_c3_full_cap12.properties` | `SIM_MAX_OPEN_POSITIONS=12` (~p90 DEV) |
| `X1_C3_FULL_CAP16` | `profiles/x1_c3_full_cap16.properties` | `SIM_MAX_OPEN_POSITIONS=16` |
| `X1_C3_FULL_NOT40` | `profiles/x1_c3_full_not40.properties` | `SIM_MAX_OPEN_NOTIONAL_PCT=0.40` (= muc live 27 lenh/35k) |
Moi key khac y `x1_c3_full.properties`. Khong them cap khac, khong ket hop count+notional, khong doi nguong sau khi thay so.

## 3. Cham diem
- `research/analysis/x1_rates.py X1_C3_FULL_PARITY_R <tag>` cho tung bien the: 5 rate (win, TSloss, mP|SM, mP|SL, meanP; mMargin
  chi ghi) + CI khoi-72h, bang theo nam, rang buoc cung theo nam (tuyet doi HARD_DD 15 / HARD_UW 120 / nam>=0 / quy>=-5).
- Equity ngay mark-to-market: paired block-bootstrap (khuon `research/analysis/ci_gatedyn.py`: block 21, 2000 rep, seed 20260903),
  d CAGR toan cua so + theo nam, hieu chinh k=3 => nguong 1.4823*sd. **Chi bao cao, KHONG quyet dinh.**
- Quan sat theo nam: maxDD, UW, so collapse-day (>=4 SL/ngay), pnl ngay te nhat, max/p90 so lenh mo, so lan cap chan, % tick co chan.

## 4. QUY TAC QUYET DINH (chot)
Bien the **PASS** <=> dong thoi:
 (i) KHONG rate nao trong 5 rate xau di ngoai CI (toan cua so);
 (ii) maxDD quan sat TOT hon (it am hon) baseline o >= 3/4 nam VA khong nam nao xau hon qua 1.0pp;
 (iii) qua het rang buoc cung tuyet doi theo nam.
Cach doc: (a) >=1 PASS => nhanh GIU MO; buoc tiep la DE XUAT so giay thu 2 chay song song (forward), KHONG doi production, KHONG
mo holdout. (b) 0 PASS, khong vi pham => DONG "khong phan biet duoc / cap khong giup maxDD" (khong noi "cap thua"). (c) cap chan
< 5% tick o ca 3 bien the => co che TRO, ghi "chua co phep thu", khong ket luan. d CAGR khong doi duoc phan quyet du dau nao.

## 5. Thu tu — bat buoc
1. Commit file nay (hash ghi vao RESULT). 2. Cai code + 3 profile, `mvn -DskipTests package`, `check_cfg_gateway.sh`.
3. Cong nghiem thu muc 1 (byte-identical). 4. Chay 3 bien the (1 slot java, `pgrep -a java` rong truoc moi run, disk >= 8G).
5. Cham muc 3. 6. `docs/RESULT_BOOKCAP.md` theo dung muc 3/4 + entry QUEUE.md. Commit SAU. Khong `git push`.

## 6. Khong lam
Khong doi arm/time-stop/giveback/gate/TOPK/bins. Khong xoa devrun cua nguoi khac. Khong cham `shadow_c3`, `SHADOW_NO_PUSH`, 242.
