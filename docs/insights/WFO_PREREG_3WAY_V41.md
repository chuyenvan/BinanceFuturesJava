# PRE-REGISTER: thí nghiệm 3 vế V4.1 (ghi TRƯỚC khi thấy số — 2026-07-02 23:20)

## 3 vế (cùng jar V4.1, cùng Oracle, cùng seed deterministic, cùng ticker aerospike Oracle-local, funding fee OFF)
| vế | dataset | funding nguồn | trả lời câu gì (so cặp) |
|---|---|---|---|
| A | wfo_dataset_wf | leak-free per-fold, coverage ~9-34 | verdict chính (3 tiêu chí đã chốt) |
| B | wfo_dataset_leaked_restricted | model leaked, coverage = mask của A | B−A = **leak thuần** (cùng coverage) |
| C | wfo_dataset (leaked full) | model leaked, coverage 78-545 | C−B = **giá của coverage** |

## Tiêu chí (không đổi so với bản chốt trong WFO_FRAMEWORK_DESIGN §6)
- Verdict PASS/FAIL chỉ áp cho vế A: WFE_median ≥ 0.5 · %OOS-dương ≥ 70% · worst OOS maxDD ≤ 50% vốn.
- Cặp B−A, C−B: báo cáo Δ trên 3 metric trên + per-window; KHÔNG có ngưỡng PASS/FAIL (diagnostic).
- LOW_TRADES đếm không-dương như V4 semantics (V4.1 chỉ thêm cột diag_*, không đổi verdict).

## Caveat ghi trước
- WFO loại 1 (pred cố định); IS chồng lấn 9/12 tháng → window không độc lập; N=30 mỏng.
- Mask restricted = giao (coverage lệch nhẹ đầu kỳ: 8.0 vs 9.0 coins/tick 2021Q1 — coin có ở A thiếu ở C tại tick).
- Provenance nhãn set của C cần verify (read-set hardcode — đã ghi ROADMAP).

---
## APPENDIX (pre-register 2026-07-04 06:4x, TRƯỚC khi thấy số): thí nghiệm N-NOISE trên Kaggle

**Câu hỏi:** WFE_median thấp có phải do selection-noise vì N=30 mẫu / 18 gene quá mỏng?
**Thiết kế:** 2 run TRỌN VẸN trên Kaggle (5 worker, ticker Aerospike 226, jar V4.1 38b503dd, dataset wf leak-free,
jobstore 226 ns=ticker) — chỉ khác đúng 1 biến: **N=30** vs **N=100**. Chạy tuần tự cùng fleet.
**Đọc kết quả (diagnostic, KHÔNG phải verdict):**
- So WFE_med / %OOS-dương / worst-maxDD giữa 2 run: nếu N=100 cải thiện WFE_med đáng kể (>2x) → noise là nghi phạm chính,
  đòn bẩy đúng là tăng N + thu gọn gene. Nếu gần như không đổi → WFE thấp là tín hiệu thật của pipeline (edge yếu OOS).
- KHÔNG so số tuyệt đối với các run Oracle (khác nguồn ticker — quy tắc 1-experiment-1-node).
**Caveat ghi trước:** run N=30-Kaggle cũng cho phép đối chiếu THÔ với vế A N=30-Oracle để lượng hoá độ lệch nguồn ticker
(chỉ báo cáo Δ, không kết luận).

## PHỤ LỤC (ghi 2026-07-04 06:3x — TRƯỚC khi có số Kaggle): replication trên Kaggle
- Chạy lại trọn bộ thí nghiệm (bắt đầu vế A) trên fleet Kaggle: cùng jar V4.1, cùng dataset file (md5 verify),
  jobstore = 226 thật, ticker = Aerospike 226 (KHÁC nguồn Oracle-local — đã đo file≠aerospike lệch số).
- Quy tắc đọc: chỉ so Δ NỘI BỘ mỗi node-type (Kaggle-A vs Kaggle-B...); KHÔNG so số tuyệt đối chéo node.
  Giá trị: nếu hướng và bậc của Δ trùng giữa 2 node-type → kết luận robust hơn với nguồn ticker.
- Test-1-kernel đo tốc độ trước khi fleet (KAGGLE_RULES §6).
