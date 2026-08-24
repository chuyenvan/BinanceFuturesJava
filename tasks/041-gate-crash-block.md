---
id: 041
status: CANCELLED
owner: CDK+human
depends_on: []
touches_live_process: false
writes_242_data: false
resource: heavy_226 + kaggle
checkpoint: true
report: docs/reports/041.md
require_review: true
---

# TASK-041: Gate thị trường CHẶN-SẬP (việc 4)

Thực thi ADR-0010 (mục cập nhật 2026-06-21). Mục đích: gate market-level chặn mở long mới khi
thị trường sắp sập diện rộng. KHÔNG hiệu quả (không vượt rule trần) → bỏ ML gate, quay lại nâng cấp
features model 15m cũ. **Đo không đoán; pre-register acceptance; mẫu phủ nhiều regime gồm crash.**

## Bối cảnh đã chốt (ADR-0010)
- Label = 3-lớp forward-return thị trường H giờ: `giảm≥X% / trung tính / tăng≥Y%`. Vế "sập" là chính.
- Features = core (breadth/funding/volatility/momentum BTC 4 khung) − nhóm TIME + candidate ADR
  (price-vs-SMA, alignment ngắn-dài, regime MA200, ETH mom, đồng-pha BTC-ETH) + **OI market-level** → feature-selection tỉa.
- Model 15m cũ (regression, IC 0.52) KHÔNG dùng — để dành nếu gate chặn-sập thất bại.

## BƯỚC A0 — Đo phân bố cú sập TRƯỚC khi chốt H/X (đo không đoán)
Mục tiêu: với mỗi (H ∈ {4H,12H,24H}, X ∈ {−15%,−20%}) đếm số **cú sập độc lập** (de-overlap theo H) trong 2021–2026.
Quyết cấu hình theo số mẫu thực, KHÔNG chốt mò.

- **A0.1** Viết tool Java `ExportMarketCloseSeries` (package research): đọc Aerospike ticker, lấy chuỗi
  **giá thị trường 15m** — BTC close (đầu tàu) + tùy chọn market index (mean/median close toàn rổ coin sống) → ghi CSV `ts,btc_close,mkt_index` trên 226.
  - ⚠️ `readDataFromAerospike1M(day)` đọc CẢ ngày × mọi coin → OOM-prone (đã sập ở funding label). Chỉ giữ giá, GC mỗi ngày; `-Xmx11g`; monitor 3 điều kiện (DONE/Exception/pgrep) như `docs/rules/run-226.md`.
  - Build LOCAL (Maven, Corretto-17 --release 11) → scp jar 226 → `setsid java ... </dev/null >log 2>&1 &`.
  - Function-test 1 tháng trước khi chạy full.
- **A0.2** Python `analyze_crash_distribution.py`: đọc CSV → forward return H giờ (close-to-close) → đếm
  cú `≤ −X%` de-overlap (greedy 1 mẫu/H). Bảng (H,X) → n_cú_sập + %thời_gian. Pre-register ngưỡng tối thiểu:
  **mỗi (H,X) cần ≥ 30 cú sập độc lập** mới đáng train (nếu không → bỏ cấu hình đó).
- **Chốt H/X** theo A0.2 (báo user xác nhận trước khi sang B).

## BƯỚC B — Data export (sau khi chốt H/X)
- Sửa/viết tool export market features 3-lớp:
  - Features: bộ core − time + candidate ADR + OI market-level (aggregate per-coin: ΔOI% TT, taker buy/sell ratio TT, long/short ratio toàn cục).
  - Label: 3-lớp theo (H,X) đã chốt.
  - Phạm vi: BTC+ETH+breadth+funding+regime; toàn lịch sử 2021–2026.
- Build local → chạy 226 → dataset Kaggle `gate-crash-data-v1`.
- Function-test nhỏ; kiểm phân bố 3 lớp (lớp sập hiếm → biết tỉ lệ imbalance).

## BƯỚC C — Train (Kaggle)
- Classification 3-lớp, **xử imbalance** (class_weight / focal / undersample lớp trung tính) — phần quan trọng nhất.
- De-overlap theo H; train toàn lịch sử (không chỉ holdout 12 tháng); feature-selection tỉa candidate (correlation + importance).
- Lưu model + scaler (nếu cần) đúng convention live.

## BƯỚC D — Nghiệm thu (pre-register)
- **Precision/recall riêng lớp "sập"** trên OOS (đếm số cú sập độc lập trong test — đủ mẫu mới tin).
- **So rule trần** "breadth thấp VÀ funding cao": ML phải vượt rõ precision/recall. Không vượt → BỎ ML gate.
- Ổn định qua regime (per-quý) + không overfit 1-2 cú (LUNA/FTX): kiểm bằng leave-one-crash-out nếu mẫu cho phép.
- PASS → tích hợp (việc riêng). FAIL → quay lại nâng cấp features model 15m cũ.

## Rủi ro đã lường
- Horizon dài → ít mẫu de-overlap (futureReturn24H ~360 điểm/12 tháng). A0 sẽ lọc (H,X) đủ mẫu.
- Lớp sập hiếm → dễ overfit. Train toàn lịch sử + leave-one-crash-out.
- Aerospike đọc nặng → OOM. Tool A0/B phải GC theo ngày, test nhỏ trước.
