---
id: 140
status: DONE
depends_on: []
touches_live_process: false
writes_242_data: false
resource: kaggle_distributed
checkpoint: true
max_retry: 2
report: docs/reports/140.md
require_review: true
---

# TASK-140: Sweep backtest-lite MÒ MODEL — 45 combo, 5 kernel Kaggle song song

## Mục tiêu (1 câu)
Xếp hạng 45 tổ hợp {label × horizon × feature-set} theo **PnL thật (backtest-lite)**, tìm ứng viên
model tốt hơn `ret2` hiện tại cho mục tiêu ≥20%/năm + ổn định.

## Scope
**Trong scope:**
- Sửa nốt bug `load_oi` trong `python/tool/sweep_harness.py`: file OI 3.15GB gz bung 1 cú → treo/OOM.
  Fix: (a) filter OI theo `feat_ts` (tập ts của features) TRƯỚC khi build DataFrame; (b) HOẶC đọc theo
  chunk; (c) HOẶC thêm mode `SKIP_OI=1` cho các combo feature-set=`base` (không cần OI). Chọn cách rẻ nhất
  cho ra smoke sạch. (load_label đã fix pattern filter feat_ts — làm tương tự cho OI.)
- **Validate-small:** smoke 1 combo (NPART=45, PARTITION=0) + 2 fold (FOLDS=202401,202510) trên Oracle,
  RA `sweep_part0.json` sạch. Chỉ khi smoke ok mới scale.
- Chia 45 combo cho `PARTITION=0..4, NPART=5`, đóng 5 kernel Kaggle (dynamic path resolver), push cả 5,
  poll tới complete, gom `sweep_part{0..4}.json`.
- FOLDS full (regime-spanning): `202307,202401,202404,202407,202501,202510` (phẳng + sóng).

**Ngoài scope:**
- KHÔNG chốt combo nào là "thắng" — chỉ xếp hạng + báo top. Verdict thuộc Uni.
- KHÔNG đem vào engine Java (đó là bước roll-up của Desktop, task riêng).
- KHÔNG đổi công thức fitness đã pre-register trong harness.

## Bối cảnh
- `sweep_harness.py` đã viết xong: fitness = `cagr_lite * pct_q_pos / (1+3*maxdd_lite)`, backtest-lite
  (top-N=5 mỗi bước H giờ, thoát bằng retEnd_H, trừ phí). Lưới: 5 label {0.01,0.02,0.03,0.04,reg} ×
  3 horizon {12h,24h,72h} × 3 featset {base, oi, pump}. `pump` = base+oi+4 feature phái sinh
  (oi_z*taker_buy, |oi_delta24h|, ls_toptrader-ls_global, sign(oi_delta)*taker_buy) — mã hoá giả thuyết
  "hàng được pump giữ thanh khoản", KHÔNG cần data mới.
- Kaggle: 5 CPU slot, user `chuyendinh`, dataset `chuyendinh/funding-selector-wfo-data`, `.gz` tự giải nén.

## Pre-register (ghi TRƯỚC khi nhìn số, vào report 140.md)
- Combo "đáng đem sang Java" nếu: `cagr_lite ≥ 0.20` VÀ `pct_q_pos ≥ 0.6` VÀ `maxdd_lite ≤ 0.35`.
- Báo top-5 theo `composite` + so trực tiếp với combo `ret2 = "0.02|12h|oi"` (baseline hiện tại) trên
  cùng FOLDS. Nếu KHÔNG combo nào vượt baseline → kết luận thẳng "sweep này không tìm được cải thiện",
  KHÔNG tô hồng.

## Acceptance criteria (worker tự kiểm trước khi done)
- [ ] Smoke 1 combo/2 fold ra `sweep_part0.json` có đủ field {combo,cagr_lite,maxdd_lite,pct_q_pos,composite,folds}.
- [ ] 5 kernel Kaggle đều COMPLETE (không ERROR), gom đủ 5 file `sweep_part*.json` = 45 combo.
- [ ] Report 140.md: bảng 45 combo sort theo composite + top-5 + so baseline ret2 + pre-register verdict.
- [ ] Không dùng LIFT/IC làm tiêu chí xếp hạng (chỉ PnL-lite).
- [ ] Ghi rõ combo nào NaN/skip và vì sao (thiếu fold, thiếu data).

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
