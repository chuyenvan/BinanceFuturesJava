# PREREG_R5P2_MAX15_GATE — R5 Pha 2: kiểm tra KINH TẾ của MAX15 bằng sim (q cập nhật theo PHÚT) — 2026-11-11

Trạng thái: PRE-REG (MASTER chốt nội dung 11-11), commit TRƯỚC mọi build/hiệu chỉnh/sim. Không push. Ứng viên chỉ cho forward shadow paper; KHÔNG đổi v1.2.
Người thực hiện: agent Opus R3. Nền: prereg R5 200a29a3, kết quả ef42873f / ddd2111f (MAX15 ĐẠT: Δfwd72 khử cụm 2024–25 +7,6 pp CI90 [+2,8; +12,3], dương cả 2 năm), chẩn đoán a770d70c.

## 0. Khai báo
- Họ gate đã thử ≥ 15 biến thể (GATE_SMART S1–S5, R3 G1–G5, R3b B1/B2, R4 C1–C3, cùng K_FRONTIER, K32, GATE_VZ, ENTRY_CONFIRM, MKT_UP, UP_TRIG, BURST_COOLDOWN). Đã thấy TOÀN BỘ kết quả R3 (P1, futility G3), R3b (hiệu chỉnh, futility B2), R4, R5.
- Mẫu R5 mỏng: ~8 đợt khử cụm/năm cho MAX15 ở tập xác nhận, trễ trung vị 5′, bắt 37 % đợt của RAW.
- LATCH (G4) là họ hàng gần (sau pass hạ ngưỡng 15′) — LOẠI ở sàng quota R3 (1,37), chưa chấm PnL.
- R3b đo được: q theo GIỜ + tín hiệu dai ⇒ pass dồn cụm, quota lệch (q đóng băng trong giờ giải thích ~70 % phần vượt). Vì vậy M1 dùng q theo PHÚT; M0 tách tác động của riêng nhịp q.
- Tiên nghiệm: thấp (R4/R3: thay cách đọc p15 thường chỉ đổi ô lấy ô ngang hoặc kém; lệnh trong đợt lớn là lãi nhất).

## 1. Định nghĩa (nhánh PREDICT_SYMBOL_TRADE; mọi thứ khác = B0)
- B0 (A0): r = p15/(fac·gs), fac = max(0,26787, sp/0,15·1,2876), gs = 1,55; buffer r các ô hợp lệ (top-24 sp, loại coin giữ, không skipFull); q_h = phần tử k = floor(pct·(m−1)) của r có ts ∈ [h−90d, h), tính ở truy vấn đầu mỗi GIỜ; warm-up 7d ⇒ 0,008; PASS ⇔ !(p < q·fac·gs) (float32).
- **q theo PHÚT** (key `SIM_GATE_Q_MINUTE=true`): như trên nhưng tại phút t = floor(ts/60 000)·60 000, q_t = phần tử k của r có ts ∈ [t−90d, t) (chỉ ô phút TRƯỚC t), tính ở truy vấn đầu mỗi PHÚT, rồi mới nạp ô của phút t. Warm-up: t − ts đầu < 7d ⇒ 0,008.
- **MAX15** (key `SIM_GATE_P15_SMOOTH=15:12`, `SIM_GATE_P15_AGG=max`): p̃(t) = max p15 trên các phút τ ∈ [t−14′, t] (thời gian thật, gồm t) có giá trị hữu hạn, cần ≥ 12; thiếu ⇒ ô REJECT, không nạp buffer. r̃ = p̃/(fac·gs); buffer và q trên r̃; PASS ⇔ !(p̃ < q·fac·gs). DCA_LEVEL1, điều kiện "có pred", BIG_DOWN giữ p15 điểm.
- Arm: **A0** = B0 (`n4f-b0-*`). **M1** = MAX15 + q theo phút + pct_M1. **M0** (chẩn đoán, KHÔNG chấm GO) = B0 + q theo phút + pct_M0.

## 2. Hiệu chỉnh pct (iso-count, chỉ năm 2022, chỉ đếm)
- `gate_offline` (pred n4f-b0 8 seed, held printDone n4f-b0-*, không mô hình skipFull/U_MAX), mô phỏng đúng q theo phút §1. Cấm mở pnl/MTM.
- T = Σ 8 seed cell pass A0 (q giờ, pct 0,999950829) năm 2022 (+07) = 4 345 (R3b, đã đo).
- Riêng cho M1 và M0: một pct chung 8 seed; tìm nhị phân pct ∈ [0,99990; 0,999999], ép float32 mỗi bước, dừng |N/T − 1| ≤ 0,05, ≤ 40 vòng; không hội tụ ⇒ arm không chạy. Ghi `r5p2_iso.json` (pct dạng chuỗi 9 chữ số) + commit TRƯỚC push Kaggle.
- KHÔNG loại arm theo quota các năm sau; quota năm 2023–25 chỉ BÁO CÁO. Chênh số lệnh được kiểm soát bằng tiêu chí rủi ro §3 (ΔCAGR22).

## 3. Tiêu chí GO (M1 vs A0; 8 seed ghép cặp 42/7/13/21/99/123/777/2024; DEV 2022-01-01..2026-01-01 +07; MTM)
Calmar = CAGR22 (equity MTM cuối ngày +07, 4 năm) / |maxDD MTM phút DEV| (như `research/r3_gate/r3_score.py`). Phải đạt ĐỦ:
1. ΔCalmar > 0 ở ≥ 7/8 seed.
2. Mean 8 seed ΔmaxDD ≥ −2 pp (không sâu hơn 2 pp).
3. Mean 8 seed ΔCAGR22 ≥ −2 pp.
4. ≥ 3/4 năm (2022–2025) có mean 8 seed ΔPnL năm ≥ 0.
- **Futility sau 4 seed (42/7/21/99):** ≥ 2/4 seed ΔCalmar ≤ 0 ⇒ DỪNG M1 (không chạy 4 seed còn lại).
- HO 2026 chỉ MÔ TẢ (đã dùng nhiều lần). GO ⇒ chỉ forward shadow paper; không đổi v1.2.
- M0: chạy 4 seed (42/7/21/99), báo cáo ΔCalmar/ΔCAGR22/ΔDD/leg vs A0 — chẩn đoán, không cổng.

## 4. Hợp lệ (trước khi chấm)
- G0 jar mới, mọi cờ TẮT ⇒ printDone + equity_summary trùng byte `n4f-b0-a1`.
- Kernel `enable_internet=false`, mapper + funding từ FILE (`sim-as-dump-1111b`), log 0 lần chạm Aerospike (cổng 3222 đã đóng từ 11-11 16:40).
- Override vào profile; result ok; MTM missing = 0, đối chứng dd_dev khớp.
- Jar STUB, jar_sec_check ×2; unit test (q theo phút = quickselect trên cửa sổ [t−90d, t); MAX causal, phủ, không lookahead; cờ tắt ⇒ đường cũ).

## 5. Báo cáo bắt buộc
Số leg; quota năm (cell pass offline + leg PREDICT sim theo năm); số/tỉ lệ ứng viên va skipFull (sổ đầy U ≥ U_MAX) từ log GATE-RATIO; phân bố độ trễ vào lệnh so với A0 (với mỗi đợt leg PREDICT A0 — cụm cách > 60′ — phút leg đầu của arm trong [s−60′, s+240′]: trung vị, tỉ lệ bắt); M0 vs A0.

## 6. Tài nguyên
Oracle: hiệu chỉnh (flock oracle_heavy) < 1 h; build jar ~10′. Kaggle (≤ 2 kernel): G0 1 + M1 4 + M0 4 + MTM 1 ≈ 10 kernel × ~50′ ⇒ ~4–5 h wall; nếu qua futility +4 M1 + MTM ≈ 2,5 h. Vòng tự chạy trên Oracle có điểm DỪNG + log.

## 7. Rủi ro
Underpowered (~8 đợt/năm); HARKing (§0); iso-count 2022 có thể lệch năm sau (chỉ báo cáo); MAX giữ cửa mở sau spike ⇒ có thể vào muộn hơn đỉnh sập hoặc dồn lệnh ⇒ va U_MAX; q theo phút trong live cần cấu trúc thứ tự (TreeMap) thay quickselect theo giờ — chi phí/parity mới nếu triển khai.
