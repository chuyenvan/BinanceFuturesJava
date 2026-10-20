# TS_MKT_EXT — xác nhận HO 2026 (W9) — kết quả 2026-10-20: **CONFIRM** (theo addendum 1 §7)

Prereg addendum 1 `docs/prereg/PREREG_TS_MKT_EXT.md` (737d9faa). Driver `~/claude_master/tsx/ho/{tsx_ho.py, tsx_ho_score.py}`, raw `ho_mtm.json`, `ts_mkt_ext_ho.json`, `ho_flags.json`.

## Validate
- V1: index ALT_EW Kaggle (vz-kline1m-2025/2026, tải về Oracle) 2025-10..12 khớp index.npz DEV 132 477/132 477 phút, max|Δ| = 0; cờ DEV tính lại = 214 = prereg. Cờ 2026: **15 ngày / 4 khoảng (T2 14, T6 1)**, đáy ALT_EW −40 % ngày 2026-02-05.
- V2: P0 `tsx-ho-p0-s42` (jar tsx cc0f9d11, không key) md5 = ho4-k24-b-s42 `7cc8864c…`, 12/12 check.
- V3: 8/8 run X14 PASS (q.check đủ, log `[TSX]`, lệnh start < 2025-12-24 trùng baseline 100 %); deferClusters 2026 = 12–16/seed (§5 đạt 8/8).
- V4: scorer ecm_mtm_h (giá Vision) — baseline W9 ROI TB 10,187 % = HO4 gốc (10,19); eqcheck final_ok 16/16; MTM miss 0.

## Kết quả W9 (2026-01-01→10-01, +07)
| Seed | ΔPnL W9 | ROI base→X14 | maxDD base→X14 | ΔQ1 / ΔQ2 / ΔQ3 |
|---|---|---|---|---|
| 42 | +1 800 | 11,77→13,00 | −5,14→−5,14 | +1 469 / +320 / +11 |
| 7 | +3 158 | 9,61→11,87 | −5,71→−5,40 | +2 540 / +660 / −41 |
| 13 | +4 348 | 11,34→14,27 | −6,05→−6,05 | +3 886 / +513 / −51 |
| 21 | +4 004 | 11,32→14,15 | −5,62→−5,62 | +3 631 / +394 / −21 |
| 99 | +3 673 | 12,58→15,01 | −5,61→−5,61 | +3 112 / +453 / +108 |
| 123 | +2 568 | 10,51→12,35 | −5,18→−5,18 | +2 350 / +281 / −63 |
| 777 | +4 193 | 5,67→8,41 | −6,67→−6,67 | +3 878 / +532 / −216 |
| 2024 | +3 039 | 8,68→10,84 | −5,99→−5,99 | +2 841 / +296 / −98 |
| **TB** | **+3 348 (8/8 > 0)** | **+2,30pp** | **Δ +0,04pp** | |

Luật §7: TB ΔPnL > 0 ✔, 8/8 seed ≥ 0 ✔, TB ΔmaxDD +0,04 ≥ −1 ✔ ⇒ **CONFIRM**.

## Giới hạn
- Toàn bộ hiệu ứng đến từ MỘT đợt sập (T2/2026, 14/15 ngày cờ) — xác nhận "luật giúp trong 1 đợt sập mới", không phải nhiều đợt. Q3 (không có cờ) ≈ 0 như kỳ vọng (path divergence nhỏ, hơi âm).
- HO4 đã dùng nhiều lần (không sạch hoàn toàn); 8 seed = nhiễu mô hình, không phải đường thị trường.
- Đuôi chưa kiểm: đợt sập kéo dài > 3 tuần (giữ loser tới 21 ngày).
- Chỉ là ứng viên v1.1 (owner 10-17: không sửa hệ cũ/shadow). Live cần ALT_EW cuối ngày từ Vision (không Binance REST trên Oracle) — phải kiểm độ trễ publish.
