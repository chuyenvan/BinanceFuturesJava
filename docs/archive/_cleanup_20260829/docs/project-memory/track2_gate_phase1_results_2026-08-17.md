# Track 2 — PHASE 1 KẾT QUẢ (label cold-test) 2026-08-17

Chạy trên Oracle. Dataset `gate15m_v2_full.csv` = 189,765 rows (2021-01 → 2026-06), 4 label cùng feature
V3Full 33. Split: train<2025 (140,256) / inner-val 2025 (35,040) / **cold-test 2026 holdout** (14,469).
Chấm theo GROUND TRUTH KINH TẾ = net forward return của rổ (`label_ret15m`, `label_ret60m`), KHÔNG theo label train.
Script: `~/java/simulator/gate_label_coldtest.py` + `gate_tail_probe.py`. Kết quả CSV: `~/claudedata/gate_label_coldtest_results.csv`.

## VERDICT (thẳng): KHÔNG label nào cho gate edge thực OOS. Gate hiện tại còn hơi PHẢN TÁC DỤNG về tail.

### 1. IC & LIFT (spearman pred vs net truth) — tất cả ≈ nhiễu
| train_label | split | truth | IC | lift@decile |
|---|---|---|---|---|
| label_oldbasket (LIVE) | val2025 | ret15m | 0.0077 | +0.00024 |
| label_oldbasket | cold2026 | ret15m | 0.0143 | +0.00002 |
| label_oldbasket | cold2026 | ret60m | 0.0287 | **-0.00013** |
| label_selector | cold2026 | ret15m | 0.0112 | -0.00003 |
| label_ret15m | val2025 | ret15m | 0.0192 | +0.00030 |
| label_ret15m | cold2026 | ret15m | **0.0043** | -0.00002 |
| label_ret60m | cold2026 | ret60m | -0.0112 | -0.00017 |

- IC nằm trong dải 0.004–0.029 = nhiễu (gate cần ≫0.03 mới đáng tin). `label_ret15m` "đỡ nhất" trên val2025
  (0.019) nhưng **sụp còn 0.004 trên cold2026** → không ổn định OOS.
- LIFT@decile ≈ 0 ở mọi label; trên cold2026 phần lớn **âm** (top-decile của pred có net return TỆ HƠN trung bình).

### 2. Net-PnL sweep threshold (cold2026, truth=ret15m) — meanNet KHÔNG tăng theo threshold
- `label_oldbasket`/`label_selector`: model đoán gần như HẰNG SỐ → pass gần hết (14,469/14,469 ở thr≤0.002; vẫn
  11,792 ở 0.006), meanNet phẳng ~+0.00012→+0.00014. Threshold 0.008 gần như không gate được.
- `label_ret15m`/`label_ret60m`: có spread nhưng nâng threshold → mẫu tí xíu (5–27 windows) noise, sumNet lúc âm
  (thr0.002: 157 pass, sumNet **-0.017**).
- Gate tốt phải có meanNet TĂNG đơn điệu theo threshold. KHÔNG label nào có → không có selectivity value.
- meanNet baseline pass-hết ≈ +0.00012/15m ≈ 0.012% — **dưới phí round-trip** (futures ~0.04–0.1%). Không vượt phí.

### 3. Tail/downside probe (cold2026, mục đích gốc của gate = cắt maxDD) — gate hiện ANTI-protective
cold_all: mean +0.00012, p10 -0.00380, p05 -0.00529, frac<-0.5% = 0.057.
- `label_oldbasket @ thr=0.008` (ĐÚNG CONFIG LIVE):
  - PASS n=10,145: frac<-0.5% = **0.064**, p05 -0.00567
  - REJ  n=4,324 : frac<-0.5% = **0.041**, p05 -0.00455
  - → Gate PASS đúng các window RỦI RO ĐUÔI CAO HƠN, REJ các window an toàn hơn. Ngược mục đích.
- `@ thr=0.010`: PASS frac<-0.5% = 0.091 vs REJ 0.045 → càng nâng threshold càng gom vào tail-risk.
- `label_ret15m`: pass 8–15 window → không vận hành được như gate ở mọi threshold hữu dụng.

## Diễn giải (đã kiểm chứng, không thổi phồng)
- Feature market-level V3Full **không dự báo được net return 15m/60m của rổ trên 2026**. Đây là câu trả lời cho
  câu hỏi cốt lõi project "edge có thực không" — **ở tầng GATE: không** (mean phẳng, tail ngược, IC nhiễu).
- Điều này KHÔNG phủ định SELECTOR (per-coin, 45 feat gồm OI) — đó là model khác, chưa test ở đây.
- Config live hiện tại (`label_oldbasket @ 0.008`) trên dữ liệu mới nhất **hơi phản tác dụng về tail**, không chỉ vô dụng.

## Hệ quả cho roadmap (đề xuất, chờ Uni quyết)
- **DỪNG Phase 2 (threshold HPO)**: HPO trên tín hiệu IC≈0 = fit noise; net-PnL sweep đã cho thấy threshold vô nghĩa.
- **Cân nhắc gỡ/trung tính hóa gate live** (đưa về pass-through) vì @0.008 nó cắt nhầm — NHƯNG đây là thay đổi live,
  cần thêm ≥2–3 holdout window nữa để xác nhận, KHÔNG hành động chỉ trên 1 cold-test.
- **Chuyển trọng tâm** sang đúng câu hỏi project: (a) SELECTOR edge có thực không (chưa đo OOS kiểu này),
  (b) pivot EXIT/quản trị lệnh (SL chặn lỗ khi có lãi, nuôi lãi) — vì downside control phải đến từ exit/SL,
  gate không gánh được. Phase 3 (OI cho gate) tạm hoãn: thêm feature vào một premise đã hỏng ít khả năng cứu.

## Trạng thái
- Live KHÔNG đụng (baseline v1 giữ nguyên). Đây chỉ là nghiên cứu offline trên Oracle.
- File: `gate_label_coldtest.py`, `gate_tail_probe.py`, `gate_label_coldtest_results.csv` trên Oracle.
