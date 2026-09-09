# RESULT_GATEFEAT — đánh giá 33 feature V3FULL gate p15 (WFO OOS)

Pre-reg: `docs/PREREG_GATEFEAT.md` (`8fc7d90`). Harness:
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

- **Config gate de xuat: 30 feature** = 33 − {`rsi14`, `monthOfYear`, `fundingRateRaw`}.
- Chat luong do duoc (IC de-overlap 15m, 166,656 moc OOS 19 fold DEV): 0.5335 → **0.5483**
  (+0.0148, ~+2.8% tuong doi).
- Luu y: chat luong gate OOS tot hon KHONG tu dong = sim tot hon (F4/CI_REAUDIT #9) — buoc sim
  48 thang la pre-reg rieng, cho user duyet config 30-feature truoc.
- Feature calendar con lai (`hourOfDay` +0.0723, `dayOfWeek` +0.021, `weekOfMonth` −0.0112):
  `hourOfDay` co the la seasonality that; chua nam trong 6 chu trinh nay — muon do tiep phai pre-reg mo rong.
