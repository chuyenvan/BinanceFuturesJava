# HOLDOUT 2026H1 — VERDICT (MASTER, 2026-10-10)

Pre-reg: docs/prereg/PREREG_HOLDOUT2026H1.md (35d03784 + ADDENDUM-1 0e3282a6 + ADDENDUM-2 1682a311/2691816d/8fe35b23). Seal mở 10-09 10:22; 48/48 kernel parity PASS.
Scorer A: defs 269fc9ad → kết quả b89575bf (docs/result/ho26/HO26_RESULT_A.*). Scorer B (độc lập, không import thước): defs c835b9a8 → kết quả db4f3ce8 (HO26_RESULT_B.*). Cả hai commit định nghĩa TRƯỚC khi đọc dữ liệu 2026.

## Đối chiếu A/B (J-F)
- Mọi số trong luật trùng tuyệt đối: n, ΣPnL_S, ROI, maxDD từng cfg; Δ ghép cặp; số seed đạt. Lệch duy nhất ngoài luật: Sharpe (A 2,87/2,64/2,01 vs B 2,90/2,66/2,01, ≤1,1%) và định nghĩa "số đợt" khác nhau (A 6,8 vs B 46 cho k24) — không dùng trong luật.
- Tự kiểm: phần trước 2026 của ho26-k24-s-s42 trùng nsel-nen-s42 (3517/3517 lệnh, equity 105640); equity MTM khớp log Update ≤0,0017%. B: equity cuối lệch result.json 0,02–0,32% do 1–7 chân còn mở lúc sim dừng 07-01 06:59 (ngoài cửa sổ) — giải thích được, không ảnh hưởng luật.

## Kết quả (stress in-sim 1,675%, 2026-01-01→06-30 +07, 8 seed, mean [min..max])
| cfg | n | ΣPnL_S | ROI % | maxDD % | Sharpe |
|---|---|---|---|---|---|
| B0 K16 | 187 [174..199] | 9 590 [7 446..13 341] | 8,25 | −4,69 | ~2,9 |
| K24+skipFull | 255 [221..274] | 10 229 [8 359..14 018] | 8,36 [6,68..11,33] | −5,50 | ~2,65 |
| K24+skipFull+NSEL M2 | 470 [449..497] | 10 174 [6 390..15 093] | 8,08 | −6,68 | 2,01 |

## Verdict
- E0 PASS: K24+skipFull ΣPnL_S > 0 ở 8/8 seed.
- H-A XÁC NHẬN: K24 − B0 ΔΣPnL_S +639 (7/8), ΔmaxDD −0,81pp. Bootstrap MTM CI chứa 0 ⇒ K24 "không kém" K16, chưa chứng minh tốt hơn.
- H-B KHÔNG xác nhận: Δn +215, ΔΣPnL −55, ΔDD −1,18pp đạt; số seed đạt 4/8 < 5 ⇒ không port NSEL (khớp quyết định owner 10-09: go-live K24+skipFull).

## Đọc kết quả
- CAGR năm hoá K24 17,6% vs DEV 27,6% (tỉ lệ 0,64 ⇒ chiết khấu ~36%, nằm trong vùng ước lượng 30–45%). Sharpe holdout cao hơn DEV vì 6 tháng DD nhỏ — Sharpe 6 tháng rất nhiễu, không dùng làm kỳ vọng.
- Lãi dồn cục: tháng 6 chiếm ~62% ΣPnL K24; tháng 3–4 gần như không có lệnh; không lệnh mới từ 06-25. Phí gốc: K24 ΣPnL 14 439 (8/8 dương).
- Rủi ro còn lại: 2026H1 từng là VAL (nhiễm tầng thiết kế); 6 tháng ≈ 1/8 DEV; chi phí khớp thật trong nến sập vẫn CHƯA đo.
