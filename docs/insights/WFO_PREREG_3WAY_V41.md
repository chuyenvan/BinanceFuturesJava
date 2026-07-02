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
