# PREREG NUP2 — Mở rộng NUP: size/leg, nhịp DCA, capacity, bộ lọc entry + KẾT HỢP (MASTER 2026-10-26)

Viết TRƯỚC khi có bất kỳ kết quả NUP nào. Bổ sung cho NUP (`~/claude_master/oc1026/oc1026_TASK_nup.md`, `docs/prereg/PREREG_NUP.md`), không thay thế: dùng chung baseline B0 (X14, jar cc0f9d11), chung thước đo §3 và cổng tái lập của NUP.

## 1. Lý do
- Owner 10-26: exit đã tốt (X14) nên có thể chịu entry hung hăng hơn. Muốn mở rộng sang giảm margin mỗi lệnh, tăng nhịp DCA, và cách KẾT HỢP các hướng.
- Giả thuyết H-X14: X14 cứu các vị thế kẹt, nên lever tăng lệnh từng NO-GO trước X14 (N700/GKF/N_DEEP) có thể đổi dấu.
- Giả thuyết H-INT: lever có tương tác. Size nhỏ hơn mua thêm "ngân sách DD" cho gate/K nới hơn ⇒ phải đo theo cặp/tổ hợp, không chỉ từng lever.
- Rủi ro đã biết, ghi để không tự lừa:
  - Lệnh crash-buy tương quan rất cao: SEED_BLEND tương quan ngày 0,975; N_DEEP 0,84–0,96. Thêm lệnh trong cùng đợt KHÔNG tăng số phép thử độc lập.
  - DCA từng NULL/FAIL (HOLDDCA 0/3).
  - DEV đã bị nhìn > 40 lần.

## 2. Lever bổ sung (Pha 1b, một-nhân-tố, cùng 4 seed a1/s7/s21/s99 như NUP Pha 1)
Mỗi arm = B0 + đổi đúng lever ghi. Key chính xác do agent đọc code Java xác định, ghi file:dòng vào ADDENDUM kỹ thuật TRƯỚC khi push. Không tìm được key đúng ngữ nghĩa ⇒ bỏ arm, ghi lý do, không tự chế lever khác.

| Arm | Lever | Mức |
|---|---|---|
| B1 | size/notional mỗi leg | ×0,50 (giữ U_MAX, K, gate) |
| B2 | nhịp DCA: khoảng cách giữa các bậc grid | ×0,67 (DCA kích sớm hơn); tổng ngân sách/cụm giữ nguyên |
| B3 | nhịp DCA: số bậc grid | 4 → 6 bậc, trọng số đều, tổng ngân sách/cụm giữ nguyên (mỗi bậc nhỏ hơn) |
| B4 | capacity U_MAX (ngưỡng sổ đầy ⇒ skipFull) | ×1,25 |
| B5 | bộ lọc entry `SIM_MIN_MOMENTUM_15M` | 0,008 → 0,005 |

Validate ngữ nghĩa sau khi chạy:
- B1: notional leg0 ∈ [0,47; 0,53]× B0.
- B2/B3: số leg DCA/cụm tăng, tổng notional/cụm max ≤ 1,02× B0.
- B4: U max tăng, số lần skipFull giảm.
- B5: số ứng viên qua bộ lọc tăng.

## 3. Pha 2b — kết hợp (factorial)
- Tập ứng viên: 12 lever đơn của NUP (A1–A5, A7; A6 là tổ hợp nên loại) và NUP2 (B1–B5).
- Lever "hữu ích" = ở Pha 1/1b có cụm/năm ≥ 1,10× B0 VÀ ΣPnL ≥ 0,80× B0 (median 4 seed).
  - Riêng B1 (size) luôn được coi hữu ích, vì nó là lever rủi ro, dùng để đổi DD lấy lệnh.
- Xếp lever hữu ích (trừ B1) theo hiệu suất E = (cụm/năm ÷ B0 − 1) ÷ max(0,5; |ΔmaxDD| pp). Lấy top-2 = X, Y. Hoà ⇒ ΣPnL cao hơn.
- Chạy full factorial 2³ trên {X, Y, B1} × 4 seed. Bỏ qua ô đã có (B0, X, Y, B1) ⇒ 4 ô mới: X+Y, X+B1, Y+B1, X+Y+B1.
  - Nếu X, Y cùng là A-gate (vd A1 và A2 cùng key) ⇒ thay Y bằng lever kế tiếp KHÁC key.
- Báo tương tác: Δ(X+Y) so với ΔX + ΔY, cho cụm/năm, ΣPnL, maxDD.
- Ít hơn 2 lever hữu ích ⇒ factorial trên những gì có (tối thiểu X + B1). Không có lever nào ⇒ bỏ Pha 2b, báo NO-GO kèm frontier.

## 4. Chuẩn hoá iso-DD (báo cáo, không phải tiêu chí chính)
- Với mỗi ô Pha 1/1b/2b: ước size s* để maxDD median = −30 %, theo xấp xỉ tuyến tính DD ∝ size (CROSS 1x, không đòn bẩy). Báo cụm/năm, ΣPnL·s*, Calmar tại s*.
- Kiểm xấp xỉ bằng 1 run thật: ô tốt nhất theo cụm/năm, chạy ở s* làm tròn 0,05, 1 seed s7. Lệch DD dự báo > 3pp ⇒ ghi "xấp xỉ tuyến tính không giữ", bỏ cột iso-DD.

## 5. Chỉ số bổ sung (mọi run, ngoài §3 NUP)
- **Số "phép thử độc lập" N_eff:** số đợt riêng biệt/năm (đợt = các lệnh cách nhau < 6h), số ngày có lệnh mới/năm, tương quan PnL ngày với B0, top-10 ngày % ΣPnL. Mục đích: phân biệt "nhiều lệnh" với "nhiều cơ hội độc lập". Báo cáo, không phải tiêu chí.
- Tách PnL theo leg đầu và leg DCA (B2/B3).

## 6. Pha 3 — xác nhận
- Ứng viên = mọi ô (NUP A1–A7, NUP2 B1–B5, Pha 2b) qua G1–G3 của NUP §4 ở 4 seed. Lấy tối đa 3 ô, cụm/năm cao nhất. Hoà ±5 % ⇒ ΣPnL.
  - Gộp với Pha 2 của NUP: tổng số ô xác nhận ≤ 3, không phải 2 + 3.
- Chạy 4 seed DEV còn lại + 8 seed HO. GO theo G1–G4 của NUP §4 (ngưỡng KHÔNG đổi).
- Nhiều ô GO ⇒ cụm/năm cao nhất. Không ô nào ⇒ NO-GO + frontier đầy đủ (cụm/năm × ΣPnL × maxDD × N_eff, cả iso-DD) để owner chọn.

## 7. Kỷ luật
- Trial ledger họ NUP + NUP2 ≤ 7 + 5 + 4 + 1 = 17 cấu hình; ghi trong result.
- KHÔNG thêm lever/mức/seed/kỳ sau khi thấy số. Bug ⇒ ADDENDUM + số trước/sau.
- HO chỉ xác nhận. Mọi GO = ứng viên v1.3, cần forward shadow ≥ 4 tuần trước khi chạm tiền. Không đổi v1.1/v1.2 trước D 12-08.
- Luật truy cập/đĩa/commit như NUP §7 và COMMON.
