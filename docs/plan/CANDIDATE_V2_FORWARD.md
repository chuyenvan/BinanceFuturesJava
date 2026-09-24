# CANDIDATE V2 — DON UNG VIEN CHO FORWARD

> Mo ta (KHONG chay sim). Branch `module`. KHONG push. Viet 2026-09-17 sau khi chot huong
> (a) do do nhay BIG_DOWN + (b) don suc vao forward. Doc kem: `docs/decisions/DECISION_DCA_PERCOIN_CAP.md`,
> `docs/result/RESULT_DCA_AGG_PERCOIN.md`, `docs/audit/AUDIT_BIGDOWN_DEEP.md`, `docs/analysis/SHADOW_LOG.md`,
> `docs/experiment/L1_SHADOW_C3.md`.

## 0. Muc dich

Gom dung mot cho: (1) nhung gi DA CHOT/DA CHUNG MINH so voi T170, kem trang thai bang chung;
(2) nhung gi CHUA chung minh duoc; (3) ke hoach forward + ha tang shadow hien co; (4) tieu chi
doc forward ghi TRUOC. **Khong hua hen gi khong lam duoc.**

---

## 1. Da chot / da chung minh (so voi T170, nen = `x1_gs_t170`, md5 `efb793e2...`)

| # | ung vien | ket qua do duoc | trang thai bang chung |
|---|---|---|---|
| 1 | `DCA_GRID_LEVELS = -0.30,-0.55,-0.75` | DCA leg **20 -> 84** (n tong 1089 -> 1162); maxDD/nam **-11.84 -> -9.64**; 5 rate chat luong **TRUNG TINH** (0/5 XAU ngoai CI, nhung **khong rate nao TOT hon co y nghia**) | DEV-only; **rate trung tinh** = khong co alpha do duoc |
| 2 | `CONC_CAP_PERCOIN_ENABLED=true`, `CONC_CAP_PERCOIN_PCT=0.15` | guard binding **45 lan** (chan 2 deep-leg `w=8` EVAA + JELLYJELLY); tap trung 1 coin **17.15% -> 12.51%** (<= 15% ✓) | DEV-only; co che guard chay DUNG (log `[CONC-PC] SUMMARY blocked=45`) |
| 3 | tran aggregate 0.30 (`CONC_CAP_AGG_DCA_PCT=0.30`) | **BO (no-op)**: binding 0 lan, dinh tong DCA-grid 16.76% < 30% | DEV-only; `LOOSE_AGG30_PC15` == `LOOSE_PC15` byte-identical (`5cde7edd...`) |

Nguon so: `docs/result/RESULT_DCA_AGG_PERCOIN.md` (commit `7aa21a7`), `docs/decisions/DECISION_DCA_PERCOIN_CAP.md`.

**Cau hinh ung vien chot** (chua vao san xuat, flag van default OFF):
`DCA_GRID_LEVELS=-0.30,-0.55,-0.75` + `CONC_CAP_PERCOIN_ENABLED=true` +
`CONC_CAP_PERCOIN_PCT=0.15` + `CONC_CAP_AGG_DCA_ENABLED=false` (bo aggregate). Giu
`DCA_GRID_WEIGHTS=1,1,3,8`, `DCA_GRID_SCALE=19.5`.

---

## 2. Chua chung minh duoc (ghi ro, khong vo tron)

1. **Khong rate nao TOT hon co y nghia.** Ca 3 variant deu 0/5 rate XAU ngoai CI, nhung moi rate
   "tot" (mP|SL, mP|SM, meanP) deu **nam TRONG CI** => khong co bang chung alpha, chi la cai thien
   **kiem soat rui ro**.
2. **maxDD -11.84 -> -9.64 la so MOT-LAN-QUAN-SAT** (khong co CI). Khong duoc doc thanh "tot hon ve
   thong ke".
3. **Nguong BIG_DOWN `-0.03157` khong ro nguon goc** (co the overfit) — `docs/audit/AUDIT_BIGDOWN_DEEP.md`.
   Duoc do tiep bang bai do nhay `docs/prereg/PREREG_BD_THRESHOLD_FRAGILITY.md`.
4. **DEV-only.** Tat ca deu tren DEV 2021-07..2025-12. Chua co forward/holdout.

---

## 3. Hien trang ha tang shadow (doc `SHADOW_LOG.md` + `L1_SHADOW_C3.md`)

- **Co san:** shadow (off-trade) dang chay tren Oracle/242, log `would-BUY`, co `tools/shadow_vs_sim.py`
  parse log -> ledger.csv (`sym, ts, side, entry, qty, level, rank, symbol_pred, exit_ts, exit_px, profit`).
  `SHADOW_LOG.md` ghi nhat ky deploy; `L1_SHADOW_C3.md` ghi han 8 blocker B1-B8.
- **Nhung shadow do la cho duong C3/selector**, KHONG phai cho ung vien DCA nay. Van de COT LOI:

  > **Ung vien DCA nay la SIM-ONLY.** `DcaProcessor.getDCA` (sim) dung `DcaUtils.shouldDcaGrid`
  > (`DCA_GRID_LEVELS`) khi `DCA_GRID_ENABLED=true`; nhung `DcaProcessor.getDCAProduction` (LIVE,
  > goi tu `DetectEntrySignal2TradeNormal:297,315`) **dung `DcaUtils.shouldDca`** (logic cu:
  > `DCA_TIME_BIG_DOWN`/`DCA_LOSS_BIG_DOWN`/`calRateLoss`), **KHONG doc `DCA_GRID_LEVELS`**.
  > Tuong tu, guard `CONC_CAP_PERCOIN` nam trong `SimulatorMarketLevelTicker1MStopLoss.createOrder`
  > (sim), **KHONG co tren duong live**. => Chay cau hinh ung vien nay tren duong live hien tai
  > **KHONG DOI MOT BIT** (cac key bi pho lo, khong ai doc).

**Ket luan:** CHUA co harness ghi duoc "cau hinh ung vien nay chay song song T170" tren forward.

---

## 4. Can gi de forward duoc (ghi RO thay vi hua)

Muon forward-test ung vien DCA nay can **viet moi / mo rong duong live** (moi muc mot pre-reg rieng,
cong parity live khong doi khi tat):

1. **DCA grid tren duong live:** them nhanh `shouldDcaGrid` (dung `DCA_GRID_LEVELS`) vao
   `getDCAProduction` — hoac mot duong DCA grid live tuong duong sim. Hien tai live chi co `shouldDca`
   (logic cu). Day la khoang cach co che lon nhat giua sim va live.
2. **Per-coin cap tren duong live:** them guard `CONC_CAP_PERCOIN` vao duong tao lenh live
   (`DetectEntrySignal2TradeNormal`/`BinanceOrderTradingManager`), tinh `coinNow + legNew` / equity.
   Hien tai khong co tran per-coin nao tren live.
3. **Paper-equity cho sizing compound:** live khong co `SIM_FIX_B3` (compound equity) — xem
   `L1_SHADOW_C3.md` muc 3e (blocker B4: `BUDGET_PER_ORDER=0` khi khong API key; can key read-only
   hoac co `PAPER_EQUITY`).
4. **Redis rieng** (khong cuop lenh bot live) — `L1_SHADOW_C3.md` muc 3f.
5. **Log cho doi chung:** moi `would-BUY` phai ghi `sym, ts, side, entry, qty, level, rank,
   symbol_pred, exit_ts, exit_px, profit` (khung da co o `tools/shadow_vs_sim.py`). Noi ghi: log
   `[SHADOW]` tren Oracle; ai doc: `tools/shadow_vs_sim.py parse` -> `ledger.csv`, so voi sim tren
   dung cua so da troi qua.

**KHONG hua:** chua co mot muc nao trong 5 muc tren ton tai san; ke hoach forward chi co the bat dau
sau khi (1)+(2) duoc viet va parity live da chung minh.

---

## 5. Tieu chi doc forward (ghi TRUOC, KHONG doi nguong trong luc forward)

Ghi truoc de khoi "doc ket qua roi moi dat nguong". Hai lop:

### 5.1 XAC NHAN (confirm)

- **Co che chay dung tren forward:** per-coin cap binding khi 1 coin cham 15% equity (log co
  `[CONC-PC]` skip, tap trung forward <= 15% + dung sai nho).
- **Khong hong quality:** so sanh tren cua so forward da troi qua, 5 rate chat luong (win/tsloss/
  mP|SM/mP|SL/meanP) cua ung vien KHONG XAU ngoai CI so voi T170 (cung quy tac block-72h x1.21,
  2000 rep, seed 20260905). Day la **confirm "khong lam hong"**, khong phai "tot hon".
- **Rang buoc cung giu:** maxDD <= 30%/nam, UW <= 200 ngay, quy >= -15%, khong nam am.

### 5.2 BAC BO (reject)

- **Vi pham chan:** bat ky quy am < -15%, nam am, maxDD > 30%/nam, UW > 200 ngay, tap trung > 15%
  (guard hong/khong binding).
- **Hong quality co y nghia:** >= 1 rate XAU ngoai CI (nguoc huong tot) so voi T170 tren cua so forward.

### 5.3 GHI RO (khong doi nguong)

- Nguong so sanh (15%, 30%, -15%, 200, CI block-72h x1.21) da CHOT O TREN, **KHONG duoc tinh chinh
  lai trong luc forward**. Neu thay can doi, phai pre-reg moi TRUOC.
- **Cua so forward da troi qua = da tieu holdout** (quy tac unseal `L1_SHADOW_C3.md` muc 7.1). Moi
  tuan shadow chay la mot tuan holdout bi tieu — chap nhan tu dau.

---

## 6. Thu tu de xuat (khong phai quyet dinh)

1. Xong bai do nhay BIG_DOWN (`docs/result/RESULT_BD_THRESHOLD_FRAGILITY.md`) truoc — no quyet dinh nguong
   BIG_DOWN hien tai co dac biet khong, anh huong muc uu tien forward.
2. Mo duong DCA grid + per-coin cap tren live (muc 4.1 + 4.2), moi buoc mot pre-reg + parity live.
3. Chi khi (2) xong moi bat duoc shadow "ung vien DCA chay song song T170".
