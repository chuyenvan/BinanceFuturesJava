---
id: 039
status: CANCELLED
depends_on: [037, 038, 024]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: true
max_retry: 2
report: docs/reports/039.md
require_review: true
---

# TASK-039: Funding F5 — ghép feature + train SELECTOR + beat rule (OOS)

- **status:** TODO. `depends_on: [037, 038]` (feature) + `[024]` (label triple-barrier 47.86M dòng đã xong).
- **Nền:** ADR-0011 §5.2/§5.5 + §2.2 (khung đo).

## Việc
- **Ghép:** feature (037 + 038) + label triple-barrier (024) → dataset train selector. Align mốc, **de-overlap per-symbol** (horizon), purge.
- **Train** (XGBoost — như `train_fundingfee_xgboost_optuna`): split theo thời gian, **KHÔNG shuffle, KHÔNG scale** (live không có scaler), purge horizon. **KHOÁ thứ tự lớp** — ADR-0011 §6: `symbolPred = pred[0] = P(fail)`, rank ưu tiên P(fail) THẤP; đổi thứ tự output = sai dấu âm thầm.
- **Đo:** conditional hit-rate / LIFT vs base-rate + z-test (chính); rank-IC/t-stat/block-bootstrap (phụ). Gate: LIFT≥1.20, N≥100, z≥2, |t-IC|≥2. Holdout 12 tháng.
- **ACCEPTANCE KINH TẾ (§5.5):** selector phải **BEAT rule baseline** (vd "funding-percentile cao + volume-z cao + OI tăng") trên OOS → không beat thì dùng rule, bỏ ML (như gate).

## ✅ Đã chốt (2026-06-20)
- **Target = `+6%`** (user chốt). Win triple-barrier: chạm **+6%** TRƯỚC khi chạm -Y% trong horizon H.
- **Feature = đủ 45** (Tool1 #1-40 + OI #41-45).

## Data-plan & nguồn (chốt 2026-06-20)
Ghép bằng `merge_asof(by=symId, on=ts, backward)`:
1. **Tool1 40 cột (#1-40):** `features_export_python_v3/ff_YYYYMM.bin.gz` 2021-01→2026-06 (66 tháng, đã áp EntrySignalFilter — TASK-106). Gộp local `/d/claudedata/funding-ff-full/` (hiện 65/66, chờ nốt `ff_202101` re-run tay trên 226). Record 170B = ts(8)+symId(2)+40×float.
2. **OI #41-45:** `oi_percoin_*.bin.gz` (30B = ts+symId+5×float), **nguồn = Aerospike 226 re-export** (`ExportFundingOiPerCoin`, source mặc định).
   - Lý do chọn Aerospike (KHÔNG vision-direct): đo cùng BTC cùng kỳ → Aerospike ≡ vision (cùng `VisionMetricsClient` backfill); chọn Aerospike vì export RẸ (đọc 226 local, không tải vision toàn lịch sử mỗi lần).
   - **Hạn chế đã biết:** lsToptrader (#44) **2022 thiếu ~87%** (BTC) do **parse-bug `VisionMetricsClient.parseDay`** với file 2022 — nguồn data.binance.vision ĐẦY ĐỦ (đo T3/T6/T9/T12 = 0 empty), KHÔNG phải nguồn thiếu. Các năm khác 0%. Để NaN (XGBoost handle), **KHÔNG fill 0**. Fix parseDay là việc riêng — chỉ làm NẾU feature-importance cho thấy lsToptrader đáng giá.
3. **Label triple-barrier (024):** `funding_label.csv` 47.86M dòng / 9.4GB trên Kaggle dataset `chuyendinh/export-funding-label`. KHÔNG tải về dev — chain dataset trên Kaggle. Áp barrier +6% ở train từ maxFav/maxAdv/nBars theo H={4h,12h,24h,72h}.

## Các bước (mỗi bước TRÒN — verify bằng số trước khi sang bước sau)
- **B1.** Hoàn tất Tool1: re-run `ff_202101` (tay/226) → gộp đủ. VERIFY: `ls funding-ff-full/ff_*.bin.gz | wc -l == 66`.
- **B2.** Re-export OI 2021-2026 từ Aerospike (226). VERIFY: NaN% theo năm (2022 toptrader cao — parse-bug đã biết; năm khác ~0); records>0.
- **B3.** Đẩy Tool1 + OI thành Kaggle dataset. VERIFY: đủ tháng, size hợp lý.
- **B4.** Viết script train (MỚI — code 2025 đã mất): mount 3 nguồn → merge_asof → barrier +6% → split thời gian (no shuffle/scale, purge horizon) → XGBoost, **khoá `pred[0]=P(fail)`**. VERIFY: leak-check (train<val<test theo ts), base-rate.
- **B5.** Train Kaggle (chain dataset). VERIFY: IC/LIFT/z + beat-rule OOS 12T.

## Acceptance (PRE-REGISTER — chốt TRƯỚC khi xem kết quả)
- Gate ML: **LIFT≥1.20**, N≥100, z≥2, |t-IC|≥2 (OOS holdout 12 tháng).
- Kinh tế: selector phải **BEAT rule baseline** (funding-percentile cao + volume-z cao + OI tăng) trên OOS. Không beat → dùng rule, bỏ ML.

## Bàn giao job nền (cập nhật 2026-06-21 sáng)
- **SMOKE PASS** (cửa quan trọng nhất): 202401 ghép 64709 rows, OI NaN ~18% (merge_asof + symId↔symbol OK), base_rate +6%/24h=21.8%, 45 feat. Code `ml/funding_selector/train_funding_selector.py` verify. (202101 OI toàn NaN vì 2021-01 chỉ BTC có OI, label alt-only — KHÔNG phải lỗi.)
- **Bug đã sửa khi smoke**: merge_asof cần sort theo `ts` toàn cục (không phải [symId,ts]).
- **Label full**: đang export 226 (setsid, log `/home/chuyennd/label_full.log`, `ExportFundingLabel` no-arg = 20210101→nay), ~1-2h → upload Kaggle `chuyendinh/funding-label-full` (file `funding_label.csv`).
- **OI full**: `oi_percoin_full.bin.gz` 2.6GB/113.7M dòng + `symbol_map.csv` → Kaggle `chuyendinh/funding-oi-percoin` (đang upload).
- **Tool1**: 66 file 4.6GB → Kaggle `chuyendinh/funding-tool1-features` (đang upload).
- **Kernel**: `D:/claudedata/k039/kernel/` (funding_selector_train.py + kernel-metadata.json), HORIZONS=12h,24h,72h (lặp K=3 NỘI BỘ kernel, không LLM). Ghi `metrics_<H>.json` mỗi horizon.
- **Còn lại**: chờ label full + 3 upload → `kaggle kernels push` → đo IC/LIFT/z + beat-baseline OOS 12T cho 3 H → đối chiếu acceptance.
- **ExportFundingLabel** đã thêm tham số `[start end out]` (mặc định full) để xuất nhanh 1 tháng cho smoke.

## Validate (require_review)
- Pre-register gate (LIFT/z/N/IC) + beat-rule TRƯỚC khi xem kết quả. OOS holdout 12T. Không look-ahead (purge + expanding). Khoá thứ tự lớp.

## (Code / Kết quả điền)
