# RESULT_GATEFEAT — đánh giá 33 feature V3FULL gate p15 (WFO OOS)

Pre-reg: `docs/prereg/PREREG_GATEFEAT.md` (`8fc7d90`). Harness:
`research/pipeline/gate_feat_study/{run_cycle,score_cycle,ci_cycle,cmp_goc}.py`.
So sánh MỌI chu trình với **STAGE0** (retrain 33 feature, harness deterministic: dup
`max|d|=0`). Metric chính: Spearman IC(pred, label_oldbasket) de-overlap 15m, gộp toàn chuỗi
OOS 19 fold DEV; CI = bootstrap block 72h × 1.21, N=2000, seed 20260909. Mỗi dòng là 1 chu
trình ĐÃ chạy xong + quyết định (không sửa kết quả cũ).

## Stage 0 — CONTROL (33 feature, retrain đủ)
- IC = **0.5335** (gộp, de-overlap 15m) | IC per-fold mean 0.3728 (min 0.2657 / max 0.4815)
- lift top-decile: +1% 3.719 / +2% 6.774 / +3% 7.581 | n de-overlap = 166,656
- vs p15 GỐC (`wfo_gate_pred.csv`): spearman 0.997792, max|d| 1.8e-2 → **retrain-noise**
  (nguồn data train của model gốc khác store này); harness tự nhất quán tuyệt đối
  (chạy lại = `max|d| 0.0`) nên mọi diff giữa chu trình là do feature.
- Phase 1 (tái hiện bằng model gốc + store, không retrain): **19/19 fold PASS**
  spearman ≥ 0.999997 → store/model/file p15 đang chạy nhất quán.

## CYC1 — bỏ `basketVolSpike` (univariate IC 0.0006 — yếu nhất)  [GIỮ]
IC = 0.5320, diff vs STAGE0 = **−0.0015**, CI95×1.21 **[−0.0025, −0.0004]** (trọn dưới 0),
P(diff>0)=0.001. => bỏ làm IC GIẢM ngoài CI → **GIỮ** (feature đóng góp dù univariate yếu).

## CYC2 — bỏ `basketMomentum1H` (univariate 0.0014)  [GIỮ]
IC = 0.5324, diff = **−0.0011**, CI95×1.21 [−0.0023, +0.0001] (raw trọn dưới 0, mở rộng ×1.21
chạm 0), P(diff>0)=0.015. => nghiêng giảm, không có bằng chứng "bỏ vô hại" → **GIỮ**.

## CYC3 — bỏ `rsi14` (univariate 0.0027)  [BỎ]
IC = 0.5348, diff = **+0.0013**, CI95×1.21 **[+0.0003, +0.0023]** (trọn trên 0),
P(diff>0)=0.998. => bỏ làm IC TĂNG ngoài CI → **BỎ `rsi14`** (feature yếu, gỡ cải thiện nhẹ).

## Tổng kết hiện tại (sau 3/6 chu trình)
- Đã bỏ: `rsi14`. Đã giữ (không bỏ được): `basketVolSpike`, `basketMomentum1H`.
- Nhận xét sơ bộ: univariate IC thấp KHÔNG đồng nghĩa bỏ được — 2 feature yếu nhất đều có
  đóng góp kết hợp có ý nghĩa; `rsi14` là feature đầu tiên bỏ được (cải thiện nhẹ).
- Các chu trình còn lại theo pre-reg: CYC4 `monthOfYear`, CYC5 `momentumAcceleration`,
  CYC6 `fundingRateRaw` (nhóm BACKWARD-greedy cũ đề xuất loại — kiểm chứng ở WFO OOS).

## CYC4 — bỏ `monthOfYear` (BACKWARD cu loai; univariate IC −0.0762, am nhat)  [BỎ]
IC = 0.5480, diff = **+0.0144**, CI95×1.21 **[+0.0079, +0.0208]** (tron tren 0), P(diff>0)=1.000.
=> bỏ lam IC TANG ro ret → **BO `monthOfYear`** — time-proxy dai han (thang) gay overfit, dung
loai FEAT40_LOOKAHEAD canh bao. Ket qua quan trong nhat cua dot nay.

## CYC5 — bỏ `momentumAcceleration` (univariate IC 0.4831 — MANH NHAT)  [GIỮ]
IC = 0.5293, diff = **−0.0042**, CI95×1.21 **[−0.0059, −0.0025]** (tron duoi 0), P(diff>0)=0.000.
=> bỏ lam IC GIAM ro ret → **GIU** (feature manh nhat cua gate).

## CYC6 — bỏ `fundingRateRaw` (BACKWARD cu loai)  [BỎ]
IC = 0.5359, diff = **+0.0024**, CI95×1.21 **[+0.0011, +0.0036]**, P(diff>0)=1.000.
=> bỏ lam IC TANG co y nghia → **BO `fundingRateRaw`**.

## CYC_COMBO — bỏ ca 3: `rsi14` + `monthOfYear` + `fundingRateRaw` (30 feature)  [BỎ CA 3 — CONFIG DE XUAT]
IC = 0.5483, diff vs STAGE0 = **+0.0148**, CI95×1.21 **[+0.0084, +0.0211]**, P(diff>0)=1.000.
=> hieu ung CONG DON giu nguyen (khong tuong tac am). **Config de xuat: 33 − 3 = 30 feature.**

## Tổng kết toàn bộ (6/6 chu trình + 1 combo)
| Feature | Quyet dinh | diff IC | CI95×1.21 |
|---|---|---|---|
| `basketVolSpike` | GIU | −0.0015 | [−0.0025, −0.0004] |
| `basketMomentum1H` | GIU | −0.0011 | [−0.0023, +0.0001] |
| `rsi14` | **BO** | +0.0013 | [+0.0003, +0.0023] |
| `monthOfYear` | **BO** | +0.0144 | [+0.0079, +0.0208] |
| `momentumAcceleration` | GIU | −0.0042 | [−0.0059, −0.0025] |
| `fundingRateRaw` | **BO** | +0.0024 | [+0.0011, +0.0036] |
| COMBO 3 feature | **BO ca 3** | +0.0148 | [+0.0084, +0.0211] |
| **CYC7 (27f: bo them hourOfDay/dayOfWeek/weekOfMonth)** | **BO 6 total** | +0.0159 vs STAGE0 | [+0.0093, +0.0224] |
| CYC7 vs CYC_COMBO (30f) | bo 3 calendar them | +0.0011 | [−0.0003, +0.0025] P=0.974 |

## CYC7 — bo them 3 calendar: `hourOfDay`, `dayOfWeek`, `weekOfMonth` (27 feature total)  [BO — CHAY SIM]
IC = 0.5494 (vs STAGE0 +0.0158 CI [0.0093, 0.0224] P=1.000; vs CYC_COMBO 30f +0.0011
CI [−0.0003, +0.0025] P=0.974 — khong hai, co loi nhe khong chac). User duyet 2026-09-09 09:14:
bo luon nhom calendar roi chay sim 48 thang. => **Config SIM: 27 feature** (bo rsi14,
monthOfYear, fundingRateRaw, hourOfDay, dayOfWeek, weekOfMonth).

## SIM48 — X1_C3_FULL_GF27 (gate 27-feature, 48 thang 2022-2025, TICKER_SOURCE=file)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| X1_C3_FULL_PARITY (33f, doi chung) | 2,266 | 84.69 | 14.96 | 7.333 | −19.570 | 3.308 | 1,945 | −12.46 | 227 | 111,428 |
| X1_C3_FULL_GF27 (27f) | 2,272 | 84.11 | 15.54 | 7.330 | −18.983 | 3.242 | 1,818 | −12.93 | 223 | 107,101 |

printDone md5: GF27 `64687fd4…` vs parity `2478e90d…`. PROFILE_HASH khop `135750e0…` (cung
profile x1_c3_full, chi khac WFO_SET_PRED → pred.bin). Dataset wfo_ds_x1_gf27 4.0G (da xoa sau cham).

### Tieu chi rate + CI (khoi 72h x1.21, tool x1_rates.py)
- **TOAN CUA SO 48 thang: 0/5 rate chat luong ngoai CI** (win% −0.576 CI [−2.10,+0.94];
  TSloss% +0.577 [−1.05,+2.00]; mP|SM −0.003; mP|SL +0.586; meanP −0.066) — KHONG phan biet duoc.
- Theo nam: 2022 0/5, 2023 0/5, **2024 1/5 (TSloss% +1.26 CI [+0.08,+2.66] — huong XAU cho 27f)**, 2025 0/5.
- `mMargin` −126 ngoai CI nhung la bien KIEM SOAT sizing (B3 compound) — tool loai khoi rate chat luong.
- Rang buoc cung: ca hai deu FAIL nhu nhau (UW 223 vs 227 — da FAIL san o baseline, khong phai do gate).
  DCA leg2+ PnL: 2023 GF27 +486 vs parity 0 (GF27 co 1 leg, mau qua nho).

### Phan quyet SIM48: NULL o tang sim — GIU gate 33-feature
Dieu kien thang (>=2 rate cung huong ngoai CI) KHONG dat: toan cua so 0/5, chi 1 rate ngoai CI
theo nam (TSloss% 2024, huong XAU). **Gate 27-feature co IC OOS cao hon (+0.0159, muc 6) nhung
KHONG chuyen thanh cai thien sim** — lap lai dung tien le F4/CI_REAUDIT #9 (gate value o tang sim
chua chung minh doc lap; n_eff muc lenh 173-174 qua nho). Equity 107,101 < 111,428 (-3.9%) bao
rieng, KHONG phai tieu chi, huong trung voi mMargin giam. => **KHONG de xuat thay doi gate p15**
lam baseline. Bai hoc: feature ablation cua GATE nen danh gia o tang sim (rate), IC OOS la dieu
kien can khong phai du.

## TONG KET GATEFEAT (toan bo)
- Gate p15 33-feature hien tai: giu nguyen (khong bot feature nao vao san xuat).
- 3 feature bot duoc o tang IC (`rsi14`, `monthOfYear`, `fundingRateRaw`) va 3 calendar nua
  (`hourOfDay`, `dayOfWeek`, `weekOfMonth`) → 27f IC tot hon that (+0.0159, P=1.000) nhung sim
  KHONG cai thien → khong dung. Giu lai toan bo cong cu (`run_cycle.py`, `ci_cycle.py`, CSV
  p15_CYC7.csv, set Aerospike `ai_pred_market_gate_wfo_gf27`) cho tai su dung.

- **Config gate de xuat: 30 feature** = 33 − {`rsi14`, `monthOfYear`, `fundingRateRaw`}.
- Chat luong do duoc (IC de-overlap 15m, 166,656 moc OOS 19 fold DEV): 0.5335 → **0.5483**
  (+0.0148, ~+2.8% tuong doi).
- Luu y: chat luong gate OOS tot hon KHONG tu dong = sim tot hon (F4/CI_REAUDIT #9) — buoc sim
  48 thang la pre-reg rieng, cho user duyet config 30-feature truoc.
- Feature calendar con lai (`hourOfDay` +0.0723, `dayOfWeek` +0.021, `weekOfMonth` −0.0112):
  `hourOfDay` co the la seasonality that; chua nam trong 6 chu trinh nay — muon do tiep phai pre-reg mo rong.
