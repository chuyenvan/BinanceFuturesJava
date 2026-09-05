# T2_FULLFLOW — ghep selector C2b vao LUONG DAY DU (big_down + DCA)

Cau hoi cua user (nguyen van): *"ghep c2b vao luong sim hien tai (luong don c2b hien tai dang
khong co big_down va dca ma no dang dung SL cung 7d thi phai, toi muon test thu kieu thay c2b
voi selector cu ay)"*.

Pre-reg `docs/PREREG_T2.md`, commit TRUOC khi chay. DEV 2022-01-01..2024-06-30
(`SIM_END_DATE=20240630`). Khong chay VAL. jar `target/binance-java-sdk-1.2.4.jar`, code `acd9469`.

---

## 1. KHAM PHA — doc code, khong doan

### 1.1 `big_down` la gi

**KHONG co key cau hinh nao ten `big_down`.** Do la `MarketLevelChange.BIG_DOWN` — mot trong hai
NGUON LEG ENTRY cua engine (nguon kia la `PREDICT_SYMBOL_TRADE` = sleeve selector).

Co hoc, ba manh:

1. **Sinh tin hieu** — `MarketBigChangeDetector.getMarketStatus1M()`
   (`src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java:174-185`):
   ```java
   if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) return MarketLevelChange.BIG_DOWN;
   return null;   // co OFF_FLAT_HARD da go 2026-09-03 -> chi con MOT nhanh song
   ```
   `rateDownAvg` = trung binh rate-change 1M cua ~100 coin giam manh nhat trong tick.
   `Configs.MS_DOWN_BIG_AVG = -0.03157f` (`Configs.java:369`, hardcode; key env
   `SIM_MS_DOWN_BIG_AVG` co ton tai nhung KHONG profile nao khai). Tuc: **thi truong sap
   trung binh > 3.157% trong 1 phut => BIG_DOWN**. Day la co che **bat day**, khong phai
   co che chan lenh hay dong lenh.

2. **Tieu thu tin hieu (leg entry)** — `SimulatorMarketLevelTicker1MStopLoss.java:246-278`:
   khi `levelChange != null`, engine lay `NUMBER_ENTRY_EACH_SIGNAL` coin tot nhat theo
   `predict2Symbol` roi mo leg voi `levelChange = BIG_DOWN`. **Vong lap nay nam trong**
   ```java
   if (!Configs.SELECTOR_ONLY_ENTRY) { ... createOrderBUY(symbolId, ticker, levelChange, ...) }
   ```
   => `SELECTOR_ONLY_ENTRY=1` **TAT hoan toan leg BIG_DOWN**. Day dung la cai user goi ten.
   Ten cu cua no trong lich su repo: ablation `A2_nobigdown`
   (`/home/ubuntu/java/dev_abl.sh:43`: `run A2_nobigdown $D1E SELECTOR_ONLY_ENTRY=1  # bo leg BIG_DOWN`).

3. **BIG_DOWN BO QUA GATE AI** — `SimulatorMarketLevelTicker1MStopLoss.java:817`:
   ```java
   if (!levelChange.equals(MarketLevelChange.BIG_DOWN)) { ...AIRejectFilter...; if REJECT return; }
   ```
   Leg BIG_DOWN khong di qua `checkSignalDynamic`/`checkSignal`. Day la **rui ro so 1** cua
   viec bat lai: gate duoc `RUNBOOK muc 4` xac nhan la **load-bearing** (`v3_g1_nomom` = 10,305
   voi 14,007 lenh), ma nhanh BIG_DOWN di vong qua no — dung luc thi truong sap manh nhat.

**Trong `c2b_min`: BIG_DOWN dang TAT** (`profiles/c2b_min.properties:13` `SELECTOR_ONLY_ENTRY=1`).
Khong khai key => `"1".equals(null)` = false => BIG_DOWN BAT (default = luong day du).

### 1.2 DCA dang tat bang duong nao

Hai co che rieng, dung mot cong ra:

- **Leg DCA_LEVEL1** (`DcaProcessor.getDCA`, goi o `Simulator...:290-305`) — cac vong lap nay
  **KHONG** nam trong guard `SELECTOR_ONLY_ENTRY`, tuc chung VAN chay trong `c2b_min`.
- Nhung moi leg deu di qua `createOrder`, va o day
  (`Simulator...:889-898`) co cong grid:
  ```java
  if (Configs.DCA_GRID_ENABLED) {
      int legIdx = (cur == null) ? 0 : cur.size();
      float ratio = DcaUtils.gridLegWeightRatio(legIdx);
      if (ratio <= 0f) return;          // het bac grid -> khong mo them leg
      budget *= ratio;
  }
  ```
  `DCA_GRID_WEIGHTS=1,0,0,0` => `w[1]=w[2]=w[3]=0` => moi leg thu 2 tro di bi chan. Leg
  DCA_LEVEL1 chi nham vao coin DA co lenh chay (`getActiveOrderMap()`) nen `legIdx >= 1`
  **luon** => **DCA tat 100%**, dung nhu `W1_SWEEP muc 7` da ghi.

**Dinh chinh `C2B_SPEC.md:73`**: dong do ghi `SELECTOR_ONLY_ENTRY=1` -> "tat BIG_DOWN / DCA_LEVEL1".
Doc code thi **chi BIG_DOWN** bi key do tat; DCA_LEVEL1 bi `DCA_GRID_WEIGHTS` tat.
=> **hai co che TACH DUOC thanh 2 co doc lap** — nen chan `T2_full_c2b_noDCA` la kha thi.

### 1.3 Exit hien tai — user nho dung

`c2b_min` khong co stop-loss cung. Duong exit: arm `SIM_RATE_PROFIT_STOP_MARKET=0.07` roi
trailing `gap = min(peak*0.5, cap)` voi cap = `TS_MAX_GAP_WEAK=0.03` (W1 chung minh 100% lenh
di nhanh WEAK), cong **time-stop `SIM_LOSER_TIME_STOP_HOURS=168`** (= 7 ngay) cho cum chua arm.
Status `STOP_LOSS_DONE` trong `printDone.csv` **la time-stop 168h, khong phai SL**. `HARD_SL_PCT`
va `COND_EXIT_HOURS` deu = 0 (tat).

### 1.4 "Luong day du" — chon profile nao va TAI SAO

**Khong co profile nao trong `profiles/` co `SELECTOR_ONLY_ENTRY=0`** (36/36 file deu ke thua
`c2b_min`). Ung vien lich su co luong day du:

| ung vien | o dau | tinh trang |
|---|---|---|
| `devrun/D0_full` | `SELECTOR_ONLY_ENTRY=false`, 1688 lenh, b:48763 | jar `fs.jar` (khac), dataset `wfo_ds_sealed25` **da bi xoa**, cau hinh qua env (khong co profile) |
| `devrun/G1_giveback5` | base cu cua `AUDIT_APPLIED A1` (b:48352, 1736 lenh) | cung the: jar + dataset cu, khong tai lap |
| `devrun/A2_nobigdown` | = D1 + `SELECTOR_ONLY_ENTRY=1`, 1754 lenh | cung the |
| `configs/sim_dev.properties` | chi con tham so HA TANG | khong chua tham so giao dich nao |

**Quyet dinh: KHONG dung so lich su lam neo.** Ly do la mot bay da xay ra hai lan trong repo nay:
`W1_SWEEP muc 8` ghi `N4_a8s175` ban 2026-09-03 = 61,148/974 lenh, chay lai tren jar+dataset hien
tai = 61,592/918 — "khac jar va khac duong cau hinh, khong duoc ghep 2 so nay trong mot so sanh";
va `AUDIT_APPLIED` ghi su co `dev_h1.sh` da so nham baseline vi thieu 3 key.

**Dinh nghia dung trong T2**: "luong day du" = `c2b_min` **tru hai cong nghien cuu**, delta toi
thieu **2 key**:

| key | `c2b_min` (nghien cuu) | T2 "day du" |
|---|---|---|
| `SELECTOR_ONLY_ENTRY` | `1` (tat leg BIG_DOWN) | **`0`** |
| `DCA_GRID_WEIGHTS` | `1,0,0,0` (tat DCA) | **`1,1,3,8`** (luoi thiet ke, = default `Configs.java:190`, = `GRIDW` mac dinh cua `dev_abl.sh:20`) |

Moi truc khac (exit arm 7% + trailing + time-stop 168h, gate 0.008, `DCA_GRID_SCALE=1.5`,
`TIER_FLAT=1`, `CAPITAL_START=35000`, funding, breaker OFF) **giu y nguyen c2b_min**. Nho vay
`T2_full_c2b` vs `T2_c2b_ref` do dung 2 co che user hoi, va `T2_full_c2b` vs `T2_full_old` do
dung selector — khong tron them truc nao.

**Tham so AN duoc hoi sinh khi bat BIG_DOWN (bat buoc ghi truoc):**
- `Configs.NUMBER_ENTRY_EACH_SIGNAL = 2` (`Configs.java:106`) — so leg mo moi tick BIG_DOWN.
  Key nay **da bi xoa khoi `configs/sim_dev.properties`** trong dot don 20 key "khong ai doc"
  (dung, vi voi `SELECTOR_ONLY_ENTRY=1` no la key chet). Bat BIG_DOWN => no song lai va chay
  bang **default hardcode Java**, khong nam trong profile. Da ghi vao pre-reg nhu mot bien co
  dinh, KHONG quet.
- `Configs.MS_DOWN_BIG_AVG = -0.03157f` — nguong BIG_DOWN, cung la hardcode, cung khong quet.
- `DCA_TIME_BIG_DOWN=8`, `DCA_LOSS_BIG_DOWN=-0.15f` — chi duoc doc o `DcaUtils.getDcaConfig(BIG_DOWN)`,
  ma nhanh do chi chay khi `DCA_GRID_ENABLED=false`. Voi grid bat, chung **van tro**.

### 1.5 "Selector cu" la gi

Selector cua C2b = **S1** (XGBRanker, 9 feature), bins `/home/ubuntu/predwf_map_s1a2`.
Selector cu = **G015**. Ban goc `predwf_G015x26` **KHONG tai lap duoc** (mat training export —
`RUNBOOK muc 5`, single point of failure) va **khong con tren dia**. Ban tai lap duoc la
**`/home/ubuntu/predwf_G015_v2`** (10 file bins + `MANIFEST.sha256`, 386MB), da duoc dung lam
selector cu trong `profiles/c3.properties` (`docs/G015REBUILD_RESULT.md`).

Kem theo: `c3.properties` **hieu chuan gate** `SIM_MIN_MOMENTUM_15M` 0.008 -> **0.014052**
(he so c=1.75654) de dua admit-rate cua G015_v2 ve dung diem van hanh cua ban cu. T2 giu nguyen
hieu chuan do cho chan `T2_full_old` — neu khong, phep so selector se tron them mot cu soc tan suat.
**Day la mot sai lech co y va da ghi truoc**: `T2_full_old` khac `T2_full_c2b` o **2 bien**
(bins + gate calib), khong phai 1.

### 1.6 `CONFIG_STRICT` — 5 key chet

`configs/c2b.properties` chua 5 key chet (`DISABLE_PREDICT_SYMBOL`, `HARD_STOP_LOSS_RATE`,
`TIME_STOP_HOURS`, `TS_GAP_CONST`, `TS_MIN_GAP`) => `CONFIG_STRICT=1` se STOP. Ba profile T2
duoc sinh bang `sed` tu **`c2b_min`** (16 key, `PROFILE_HASH=a2f859b2463108fe`, da PASS strict),
chi doi 4 dong + them `DCA_GRID_LEVELS` => **khong key chet nao**. `DCA_GRID_LEVELS` duoc doc o
`Configs.java:188` nen khong bi `Cfg.auditProfile()` bao.

---

## 2. PARITY

*(dien sau khi chay)*

## 3. BANG RATE + PHAN BO STATUS

*(dien sau khi chay)*

## 4. RANG BUOC CUNG

*(dien sau khi chay)*

## 5. PHAN QUYET

*(dien sau khi chay)*

## 6. EQUITY — KHONG PHAI TIEU CHI

*(dien sau khi chay)*

## 7. CONFOUND SIZING

*(dien sau khi chay)*
