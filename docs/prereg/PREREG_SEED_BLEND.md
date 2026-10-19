# PREREG_SEED_BLEND — chia vốn qua k mô hình (seed) để tăng số lệnh mà KHÔNG tăng tổng rủi ro

Ngày 2026-10-19. Chỉ ĐO offline trên run có sẵn — không sim mới, không đổi 242/shadow, không Binance REST. Commit TRƯỚC khi chạy.

## 0. Câu hỏi (owner 10-19)
Owner không muốn tăng size; muốn tăng số lệnh/năm với mục tiêu GIẢM rủi ro. Bằng chứng cũ (N_DEEP 3ee1f50e, NSEL f24acb13):
thêm lệnh từ CÙNG một mô hình (nới gate/K) cho lệnh tương quan cao (ngày 0,84–0,96) và đẩy lệnh tốt ra ⇒ DD không giảm.
Câu hỏi còn mở: chia cùng tổng vốn cho k mô hình khác seed (mỗi mô hình 1/k vốn, chạy độc lập) — số lệnh ×k, mỗi lệnh 1/k —
có làm maxDD MTM nông hơn và Calmar tốt hơn so với 1 mô hình không?

## 1. Dữ liệu (cố định)
- 8 run OFF `gqsf-{a1,s7,s13,s21,s99,s123,s777,s2024}` (K24+skipFull, jar 0944841c), printDone + daily sim.out.
- MTM: `~/claude_master/gvz/gvz_mtm.py` (close kline1m Vision, đã tái lập cache gqsf trùng tuyệt đối — ISO_RISK add 1). Bắt buộc `missing = 0`.

## 2. Định nghĩa
- Sim scale-invariant (size ∝ equity, trần ∝ equity) ⇒ k tài khoản con vốn 35k/k chạy độc lập ≡ trung bình k run 35k.
  Blend G (nhóm k seed): gộp chân của k run, nhân `quantity, margin, notional, pnl` × 1/k; daily = trung bình (b, unP, equity).
- Nhóm cố định (thứ tự SEEDS): k=2: (A1,S7) (S13,S21) (S99,S123) (S777,S2024); k=4: (A1,S7,S13,S21) (S99,S123,S777,S2024); k=8: cả 8.
- Chỉ số (N.arm_metrics, như ISO_RISK): CAGR22, maxDD MTM 2022+ (dd_mtm22), maxDD toàn kỳ, Calmar22, UW22, lệnh/năm (tổng chân, và chân
  khác nhau theo (sym, start)).
- Δ của nhóm = chỉ số blend − trung bình chỉ số các seed thành viên (chạy đơn).

## 3. Kiểm hợp lệ (PASS trước khi đọc)
- V1: blend k=1 (mỗi seed tự nó) tái lập ISO_RISK OFF (CAGR22, dd_mtm22) sai lệch ≤ 0,01pp.
- V2: missing = 0 mọi blend. V3: ΣPnL blend = trung bình ΣPnL thành viên (≤ 1 USD).

## 4. Luật (chốt trước)
- GO "chia vốn đa mô hình giảm rủi ro" nếu: k=4 cả 2 nhóm ΔmaxDD22 ≥ +2,0pp (nông hơn) VÀ ΔCalmar22 ≥ +0,15; VÀ k=2 ≥ 3/4 nhóm ΔmaxDD22 ≥ +1,0pp.
- Ngược lại NO-GO ⇒ đóng giả thuyết "nhiều lệnh từ cùng tín hiệu giảm rủi ro" ở mức mô hình.
- k=8 chỉ mô tả. Chẩn đoán (mô tả): tương quan return ngày giữa các seed; tỉ lệ chân trùng (sym, start); DD ngày tệ nhất (2022-05).

## 5. Giới hạn / ngoài phạm vi
- Một lịch sử thị trường duy nhất: DD được quyết định bởi vài đợt sập chung (LUNA, FTX) ⇒ không có CI thật; đây là đo cơ học.
- Live: k mô hình trên 242 (RAM), làm tròn lot/min notional ở vốn nhỏ (10k/k) — chưa xét. GO ⇒ pre-reg riêng khả thi live + HO4 2026.
- Không chọn tổ hợp seed "tốt nhất" từ kết quả này.
