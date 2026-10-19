# SEED_BLEND — chia vốn qua k mô hình (kết quả)

Ngày 2026-10-19. Pre-reg `docs/prereg/PREREG_SEED_BLEND.md` d860e5dc. Script `research/analysis/seed_blend.py`, JSON `docs/result/seed_blend/`.
Dữ liệu: 8 run OFF `gqsf-*`; MTM nguồn Vision (`gvz_mtm.py`).

## Kiểm hợp lệ
- V1 PASS: blend k=1 tái lập ISO_RISK OFF đúng tới 1e-4 (CAGR22, dd_mtm22) 8/8 seed.
- V2 PASS: missing = 0 mọi blend. V3 PASS: ΣPnL blend = trung bình thành viên (k=8: 110 047 = OFF).

## Kết quả (Δ = blend − trung bình các seed thành viên chạy đơn)

| Blend | Lệnh/năm | Chân khác nhau | ΣPnL | CAGR22 | maxDD22 | Calmar | UW | ΔDD22 | ΔCalmar |
|---|---|---|---|---|---|---|---|---|---|
| 1 mô hình (trung bình 8) | 742 | — | 110 047 | 37,0 | −22,5 | 1,65 | 116 | — | — |
| k2 A1+S7 | 1 477 | 4 423 | 107 954 | 36,3 | −22,5 | 1,61 | 117 | +0,00 | −0,000 |
| k2 S13+S21 | 1 480 | 4 383 | 109 956 | 36,8 | −23,8 | 1,55 | 107 | −0,01 | −0,004 |
| k2 S99+S123 | 1 510 | 4 580 | 110 196 | 37,0 | −22,1 | 1,68 | 117 | +0,22 | +0,012 |
| k2 S777+S2024 | 1 465 | 4 385 | 112 084 | 37,9 | −19,9 | 1,91 | 92 | +1,75 | +0,142 |
| k4 nhóm 1 | 2 958 | 5 342 | 108 955 | 36,5 | −23,1 | 1,58 | 117 | −0,00 | −0,003 |
| k4 nhóm 2 | 2 975 | 5 350 | 111 140 | 37,5 | −20,6 | 1,82 | 92 | +1,35 | +0,103 |
| k8 (cả 8) | 5 933 | 6 291 | 110 047 | 37,0 | −21,8 | 1,70 | 116 | +0,75 | +0,049 |

Chẩn đoán: tương quan lợi suất ngày giữa các seed 2022–24 trung bình **0,975** (thấp nhất 0,947);
**76 %** chân của một seed trùng hẳn (cùng coin, cùng phút) với seed khác.

## Luật ⇒ **NO-GO**
k=4: ΔDD22 = −0,00 / +1,35 (cần ≥ +2,0 cả 2 nhóm) — FAIL; k=2: 1/4 nhóm ≥ +1,0 (cần 3/4) — FAIL.

## Đọc
- Chia vốn cho 8 mô hình làm số lệnh ×8 (5 933/năm) nhưng DD chỉ nông hơn 0,75pp: các mô hình cùng mua cùng đợt sập,
  nên rủi ro là MỘT nhân tố chung (sập alt toàn thị trường), không đa dạng hoá được bằng cách nhân lệnh.
- Cùng kết luận với N_DEEP (3ee1f50e: lệnh thêm tương quan ngày 0,84–0,96), NSEL (f24acb13: +848 lệnh, DD xấu hơn 8/8),
  hướng breadth T170 (5 round, power_wall): **thêm lệnh long cùng tín hiệu không giảm rủi ro** — giờ đã kiểm cả ở tầng mô hình.
- Giảm rủi ro thật cần vị thế có phơi nhiễm NGƯỢC với nhân tố sập chung (hedge), hoặc giảm size.
