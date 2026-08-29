# WFO Fanout Verdict — canon_k8 (N=1 frozen) — 2026-08-10

## Kết quả: ❌ FAIL/REVIEW

Run: `wfo_fanout wfo_ds_canon_1m_h4h gatecount.jar 1 42 2 0 canon_k8` (N=1, frozen genome loose_k8, WFO_HARNESS_FIX=true).
Dataset: canonical leak-free, leakFreeFrom=2023-01-01, foldCount=14, horizonIdx=0 (4h), codeSha=8741f85.

### Trạng thái window
- 16 window tổng: **14 DONE + 2 FAILED (OOM Java heap)**.
- 2 FAILED = w14, w15 (OOS 2025-07..2026-01) → chưa đánh giá được nửa cuối 2025 / đầu 2026.
- Trong 14 DONE: 4 window 2022 (w0–w3) = **ZERO_TRADES** vì dataset không có predict trước 2023-01-01 → 4 window này chết cấu trúc, không phải tín hiệu chiến lược.
- → Thực chất chỉ có **10 window có giao dịch** (2023-01 .. 2025-07).

### Ngưỡng pre-registered vs thực tế
| Metric | Ngưỡng | Thực tế | Đạt? |
|---|---|---|---|
| WFE median | ≥ 0.5 | **0.275** | ❌ (< 0.3 = overfit) |
| % window OOS dương | ≥ 70% | 50% (7/14) — bỏ 4 window chết → 70% (7/10) | ⚠️ biên |
| maxDD OOS xấu nhất | ≤ 50% vốn | 38.4% (win12, abs 13427) | ✅ |

posRatio strict = **0%** (không window nào dương theo thước đo strict); lenient = 50%.

### Hình dạng PnL (10 window thực)
- OOS_pnl từng window: +764, +2196, +806, +1326, **+7256**, −280, +1178, −38, **−9905**, +310.
- Tổng ≈ **+3613 / 100k vốn** qua ~2.5 năm = **~+3.6%** — gần như hòa vốn.
- win8 (2024 Q1) một mình gánh +7256; win12 (2025 Q1) một mình −9905 gần như xóa sạch.
- oosNote: 7 window `TOO_MUCH_CAPITAL_LOCK` (ăn nhỏ, khóa vốn); 3 window `BURN_ACCOUNT` (w9, w11, w12 — lỗ).

### Kết luận cốt lõi
**Xác nhận thesis của project: model "ăn ít đuôi lớn".** Frozen genome thắng nhỏ và đều (capital lock) nhưng thỉnh thoảng lỗ nặng (−10% vốn/window, DD 38%). Edge OOS yếu và overfit (WFE 0.275 = OOS chỉ giữ ~27% hiệu quả in-sample). Return/risk kém: +3.6% tổng đổi lấy 38% maxDD.

Verdict FAIL bị "khuếch đại" một phần bởi 2 artifact (4 window 2022 chết + 2 window OOM chưa chạy), nhưng WFE 0.275 và hình dạng win-nhỏ/lose-lớn là kết luận không đổi kể cả sau khi hiệu chỉnh.

### Gene stability
Tất cả gene min==max (frozen N=1, đúng thiết kế — không phải tín hiệu ổn định).

## Việc còn treo
- 2 window OOM (w14/w15, 2025 H2): cần tăng -Xmx worker rồi retry để có bức tranh đủ 2025.
- Câu hỏi mở với Uni chưa trả lời: universe train = filtered top-10% (run này) vs unfiltered như 08-02.
- Quyết định hướng đi: (A) fix OOM + hoàn tất 2025 H2, (B) pivot redesign chiến lược (tách scalp/hold, sửa asymmetry SL/TP — đúng nội dung project), (C) N=30 per-window HPO (nhưng N=1 đã FAIL nên rủi ro phí token).
