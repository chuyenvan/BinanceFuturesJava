# WFO Selection-Noise Analysis — seed42 vs seed142 (vế A leak-free, N=30) — 2026-07-06

**Mục đích:** WFE_median ~0.23 của vế A là (a) selection-noise do random-search N=30 quá mỏng, hay (b) đặc tính thật của strategy layer? Chạy lại vế A y hệt, chỉ đổi SEED_BASE 42→142.

## Kết quả
| | seed42 | seed142 |
|---|---|---|
| WFE median | 0.227 | 0.242 |
| Verdict | FAIL | FAIL |

- **Spearman rank corr giữa 2 seed (15 window có trade): 0.957** — thứ hạng window gần như bất biến.
- |ΔWFE| trung vị: 0.027 (Δ% ~14%).
- Chỉ 2/17 window đổi nhãn (w0, w3) — đều quanh ranh giới SUCCESS/TOO_FEW, WFE tuyệt đối nhỏ (~0.02–0.15), không đổi kết luận.
- Ngoại lệ w15: WFE 8.87 vs 3.31 — chênh lớn tuyệt đối nhưng CẢ HAI đều >>0.5 (window "vô địch"), không ảnh hưởng median.

## KẾT LUẬN
**WFE thấp KHÔNG phải selection-noise.** Đổi seed random-search → WFE_median gần như đứng yên (0.227→0.242),
thứ hạng window ổn định (ρ=0.96). Nếu là noise thì 2 seed sẽ cho bức tranh loạn — thực tế gần như trùng khít.
⇒ WFE ~0.23 là **đặc tính có cấu trúc của strategy layer** trên dữ liệu này, không phải nhiễu tối ưu.

**Hệ quả chiến lược:** tăng N (N-noise 100) hay robust-selection sẽ KHÔNG cứu được WFE — vì nút thắt không nằm ở
độ ổn định của random-search. Phải mổ CƠ CHẾ: vì sao IS fit tốt mà OOS fit rụng đồng đều? Ứng viên:
(1) regime shift IS→OOS (12m IS vs 3m OOS, market chuyển pha); (2) chiến lược DCA/martingale overfit tham số
vào đặc tính IS; (3) w13 ZERO cả 2 seed + cả A/D → tham số reject/funding quét sạch quý đó bất kể seed.
→ Mổ w13 + phân tích IS-vs-OOS regime là bước kế, KHÔNG phải tăng N.
