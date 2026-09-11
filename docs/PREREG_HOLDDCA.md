# PREREG_HOLDDCA — sim: BO time-stop, OM bag + DCA 1:1 toi da 3 leg theo nhip BIG_DOWN, arm/trail nhu C3, entry nho lai

Chot: 2026-09-11 (toi), commit TRUOC khi cai code / chay. Quyet dinh user (11/09): K = 3 leg; ràng buoc UW noi len **365 ngay/nam**
(= bo UW cho thi nghiem nay — la khau vi rui ro, quyet TRUOC khi thay so); "giam von entry ban dau cho phu hop" (tong von/coin khong phinh).
Nen `X1_C3_FULL` (canonical `devrun/X1_C3_FULL_PARITY_R`, md5 printDone `2478e90d...`, equity 111,428 / n=2,266), cua so 2022-01-01..
2025-12-31, bins `predwf_map_s1a2_x1` KHONG rebuild, dataset `wfo_ds_x1`, TICKER_SOURCE=file, EXCHANGE_INFO_PATH pin. KHONG cham 2026, KHONG cham 242.

## 0. Tai sao (RESULT_GRAVEYARD muc 6, counterfactual hourly, ngoai pre-reg)
Om bag + DCA 1:1 K=2..4 + ARM 7%/trailing C3 **hoa CAT trong nhieu** (chenh 180d +1..+5% von goc, CI [-11,+23]); edge nam o top-5% lenh
(39-94% |PnL CAT|); 2022 am -18..-23%; can them 84-153% von. Counterfactual KHONG mo hinh duoc: (a) budget/slot bi bag chiem => PST
sleeve doi, (b) nhip 1 phut, (c) MTM cuoi ky, (d) phi. Sim Java tra loi 4 cai do. **Ky vong ghi truoc:** entry nho => PST sleeve
(+59k, 77% pnl) co lai ~ty le entry; DCA sleeve bu khong du; 2022 vi pham rang buoc cung (nam am hoac quy < -5); tong "khong phan biet
duoc" hoac thua. Neu thang ro => bat ngo, dang di tiep. Ket qua NULL la hop le.

## 1. Co che — chot cung (moi key qua `Cfg.get`, khai trong PROFILE, `check_cfg_gateway.sh` OK; khong khai = TAT = byte-identical)
1. **Time-stop OFF**: `SIM_LOSER_TIME_STOP_HOURS=0` (key da co). Chua arm => KHONG SL, khong cat theo thoi gian.
2. **Arm/trail giu nguyen C3**: arm 0.07, TS_GIVEBACK 0.5 (cap STRONG/WEAK nhu hien tai), tinh tren **gia von trung binh** cua tat ca leg dang mo
   cua coin (neu code hien tai tinh tren gia leg dau, PHAI doi sang avg — ghi ro trong RESULT cach code hien tai lam).
3. **DCA 1:1 theo VON (USDT)**, toi da **3** leg them (tong 4 leg/coin): leg bang nhau `DCA_GRID_WEIGHTS=1,1,1,1` (kiem semantics cua
   `DCA_GRID_WEIGHTS`/`DCA_GRID_SCALE`/`TIER_FLAT` trong code truoc; neu weights khong tao leg bang nhau theo USDT thi cai key moi).
   Trigger leg: **tai tick BIG_DOWN cua market** (`MarketBigChangeDetector` — cung tin hieu sleeve BIG_DOWN dang dung, danh gia theo luoi
   1 phut cua sim) VA gia hien tai <= **0.80 x gia von TB** cua coin VA >= **24h** ke tu leg truoc cua coin VA coin chua arm.
   Key: `SIM_DCA_TRIGGER=BIG_DOWN`, `SIM_DCA_MIN_DROP=0.20`, `SIM_DCA_COOLDOWN_H=24`, `SIM_DCA_MAX_LEGS=3` (ten co the doi cho khop code,
   semantics KHONG doi). Leg DCA_LEVEL1/BIG_DOWN cu: TAT (`SIM_DCA_TRIGGER` thay the duong isDcaAlt) — de mot co che DCA duy nhat, do duoc.
4. **Von**: tran von moi coin C = getBudget() nhu hien tai (NUMBER_ORDER_BUDGET=50 giu nguyen — bag CHIEM slot, do la dieu can do).
   Entry = C x `SIM_ENTRY_FRACTION`, moi leg DCA = cung so USDT voi entry. Ba bien the khac nhau DUNG o `SIM_ENTRY_FRACTION`.
5. Vi the con mo cuoi 2025-12-31: MTM theo gia cuoi (b+unP), KHONG bo qua. Delist/het gia: gia cuoi cung (ghi so coin).
6. Java SLF4J; log moi leg DCA (`[DCA13] sym leg=k avg=.. px=..`) va dem tong. Khong sua selector/gate/bins.
7. **CONG NGHIEM THU**: jar moi, profile `x1_c3_full.properties` (khong khai key moi) => `cmp` printDone bo header voi PARITY_R rc=0, md5 khop,
   0 dong `[DCA13]`. FAIL => sua, KHONG chay bien the.

## 2. Bien the — DUNG 3, KHOA (khac nhau CHI o SIM_ENTRY_FRACTION)
| tag | profile | SIM_ENTRY_FRACTION | y nghia |
|---|---|---|---|
| `X1_HD_E25` | `profiles/x1_holddca_e25.properties` | 0.25 | entry = C/4, 3 leg DCA => toi da C/coin (= tran hien nay) — "giam von entry" theo user |
| `X1_HD_E50` | `profiles/x1_holddca_e50.properties` | 0.50 | entry = C/2 => toi da 2C/coin |
| `X1_HD_E100` | `profiles/x1_holddca_e100.properties` | 1.00 | entry = C (nhu nay) => toi da 4C/coin (= setup counterfactual) |
Moi key khac y `x1_c3_full.properties` + muc 1. Khong them bien the, khong doi 0.80/24h/3 leg/0.07 sau khi thay so.

## 3. Cham
- Equity ngay MTM: paired block-bootstrap vs PARITY_R (khuon `ci_bookcap.py`/`ci_gatedyn.py`: block 21, 2000 rep, seed 20260903),
  d CAGR toan cua so + theo nam, k=3 => nguong **1.4823 x sd_boot**.
- Rang buoc cung theo nam (**UW bo theo quyet dinh user**): maxDD >= -15%, nam >= 0, quy >= -5%. Bao cao UW nhung khong quyet.
- `x1_rates.py` 5 rate + CI (luu y TSloss% ~0 theo cau truc => chi ghi, khong doc la "tot").
- Co che: so leg DCA/nam, % PST co DCA, so vi the mo max/p90/cuoi ky + MTM cuoi ky, von khoa TB, entries/ngay (PST starvation),
  % pnl tu top-5% lenh (concentration), so collapse-day, coin het gia.

## 4. QUY TAC QUYET DINH (chot)
PASS <=> (i) **d CAGR > 1.4823 x sd_boot** (paired, block 21, toan cua so) VA (ii) qua het rang buoc cung muc 3 o **ca 4 nam**.
Cach doc: (a) >=1 PASS => nhanh MO, buoc tiep = so giay thu 2 forward (khong doi production, khong mo holdout). (b) 0 PASS, khong vi pham
=> "khong phan biet duoc" — DONG, ghi ro maxDD/2022/concentration de nguoi doc tu can khau vi. (c) DCA bắn < 100 leg/48 thang hoac
time-stop-off doi < 5% lenh => co che tro, "chua co phep thu". d CAGR am ro (CI tren < 0) => ghi "THUA" thang. Khong them bo loc hau kiem.

## 5. Thu tu — bat buoc
1. Commit file nay. 2. Doc code DCA/sizing/trail hien tai (DcaProcessor, MarketBigChangeDetector, BudgetManager*, TS_GIVEBACK) va ghi vao
RESULT muc 0 "code hien tai lam gi" TRUOC khi sua. 3. Cai + 3 profile, build, check_cfg_gateway. 4. Cong nghiem thu. 5. 3 run (1 slot java,
disk >= 8G). 6. Cham. 7. `docs/RESULT_HOLDDCA.md` + QUEUE. Commit SAU. Khong push. Khong xoa devrun cua nguoi khac. Khong cham 242.
