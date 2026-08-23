# Gate label 24h — VERDICT (đóng thí nghiệm) — 2026-08-19

## Bối cảnh / yêu cầu user
"chạy tiếp với label 24h rồi cắt lớp phân grid và chạy giống netall 15m vừa rồi đi — tôi ko tin
ko cải tiến được gate tốt hơn."
Giả thuyết user: label 15m quá ngắn cho đánh lướt; kéo horizon ra 24h (basketMaxGain 24h +
retAll 24h) may lọc gate tốt hơn, đặc biệt bắt được đường cong volume 12–24h.

## Hạ tầng đã build
- ExportGateDataset.java: thêm 2 cột label — label_max24h (basketMaxGain basketOld, horizon 96×15m),
  label_retall24h (basketRetEnd allMkt, 96×15m). Sample-once optimization trong basketMaxGain/basketRetEnd
  (stepMin = horizonMs/60000/150) để replay 24h không nổ O(n×basket).
- WFOGateRunner.java + train_gate_fold.py: GATE_PURGE_MS = 24h cho label "24h" (purge embargo đúng horizon,
  tránh leak label vào train fold).
- Fanout 3 threshold (percentile arm p10/p05/p03) trên Oracle.

## Kết quả (TOTAL_12w, 12 window chung, cao = tốt)
| Gate label | TOTAL_12w | vs old5m |
|---|---:|---:|
| **old5m (basketMaxGain 15m @5m)** | **12,660** | champion |
| netall5m tốt nhất (g0003) | 11,475 | −9% |
| max24h p10 (arm lỏng nhất) | 8,239 | −35% |
| max24h p05 | 7,591 | −40% |
| max24h p03 (arm chặt nhất) | 6,527 | −48% |

## VERDICT — label 24h THUA, đóng hướng "tối ưu gate"
- Kéo horizon ra 24h làm gate **TỆ ĐI ĐỀU ĐẶN**, không tốt lên. Ngược hoàn toàn giả thuyết.
- Càng siết threshold (p10→p03) càng tệ (8239→6527): signal 24h **không có edge để lọc** —
  siết chỉ cắt bớt trade tốt chứ không loại được trade xấu.
- Lý do gốc (khớp thí nghiệm nuôi/volume trước): momentum 24H **non-stationary**, OOS AUC ~0.5.
  Horizon càng dài, regime (bull/crash) càng nuốt signal. Gate 15m ăn được vì nó đo đúng thứ nó cần:
  momentum ngắn để **lọc điểm vào lệnh**, KHÔNG phải dự báo xu hướng dài.
- **old5m (basketMaxGain 15m @tick 5m) = TRẦN của gate.** Không label nào (net 15m/60m, max/net 24h) vượt.

## Hệ quả chiến lược
- Hết đường cải thiện P&L qua GATE. Đòn bẩy còn lại nằm ở **TRAILING/EXIT**:
  (a) selector per-coin pred thay gate market pred cho gap trailing (đã xác nhận AUC 0.601 vs 0.521,
      corr GATE-vs-SEL = −0.43 → gate đẩy gap sai chiều);
  (b) dead-zone: arm SL sớm hơn ở regime crash (mult 2.5 arm 12.5% > live 5.21847 arm 26% trong 2025Q4).
- KHÔNG đổi gate live. Giữ max/oldbasket, SIM_MIN_MOMENTUM_15M=0.008, workers đã restore.

## Files
- DONE_gateab_max24h_p10/p05/p03.txt; REPORT_gateab_max24h_*.md
- ExportGateDataset.java, WFOGateRunner.java, train_gate_fold.py (đã có label 24h + purge 24h)
