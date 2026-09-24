# TASK B2 Bước 7 — Gate LIÊN TỤC theo breadth-score (ý Uni "giãn động") — thiết kế MASTER 2026-09-21

Người soạn: MASTER. Thực thi: agent Sonnet. Chủ quyết định: Uni.
Tiền đề: `VALIDATE_BREADTH_ROBUST.md` (`30191b2`) — breadth-regime ROBUST (MA200 12/12 tổ hợp đạt phủ cả UW-2022 lẫn UW-2025; all-coin ổn định nhất, proxy-independent). Bước 6 (BR nhị phân breadth<50%→1.7): PASS khẩu vị 5/5 (lần đầu), UW-2025 sập 227→58, NHƯNG n_eff chỉ ×1.22 (u1 fail) và cắt quá tay 2025 (return 2025 22.9% < T170 32.7%) vì gate 1.7 cứng khi breadth<50%. Breadth-score cho thấy 2025 nếu gate LIÊN TỤC chỉ ~1.33 (vừa) → có thể giữ return-2025.

## Giả thuyết
Gate co giãn liên tục theo breadth-score (breadth cao→gate 1.0 lấy breadth; breadth thấp→gate chặt DẦN tới 1.7) sẽ: (a) giữ return-2025 tốt hơn BR nhị phân (2025 gate ~1.33 thay 1.7) → n_eff cao hơn; (b) vẫn phòng thủ bear-2022 (breadth~0→gate~1.7) giữ UW thấp; (c) 2023/24 khỏe → gate 1.0 giữ breadth. Kỳ vọng biến BR từ "+3% khiêm tốn, u1 fail" thành "hơn rõ T170".
Dự báo cảnh báo (khoá trước): có thể vẫn không đạt u1 (n_eff ×1.5) vì breadth thấp phần lớn thời gian; hoặc continuous chỉ nhỉnh hơn nhị phân chút. Sim phân giải.

## 0. LUẬT — như B2
An toàn (HOLDOUT/242/push/thư mục bảo vệ/index.lock); **1 job nặng/lần** (dừng shadow-c3 trước sim, bật ngay sau, ghi mốc); PREREG trước; cổng tái lập T170 md5 `efb793e2`; **cổng OFF byte-identical**; `x1_rates.py --appetite current --k`; per-year; logging chuẩn.

## 1. CƠ CHẾ (khoá lý lẽ, causal)
`breadth_score(t)` = % coin sống trên MA200 của chính nó (all-coin-sống, causal ≤ t−1). Chuỗi đã tính sẵn `research/analysis/out/breadth_score_series.csv` (cột all-coin/MA200).
`gate(t) = gate_up + (gate_down − gate_up) × clip((thr − breadth_score(t)) / thr, 0, 1)`, với **gate_up=1.0, gate_down=1.7, thr=0.50** (khoá theo lý lẽ robust: gate_up/down = biên đã dùng ở BR; thr=50% = trung tâm sweep robust MA200). breadth≥50%→gate 1.0; breadth 0→gate 1.7; tuyến tính giữa. Cập nhật gate theo NGÀY, causal.

## 2. RECON hạ tầng (trong agent, trước PREREG)
`RegimeSchedule`/`GATE_REGIME_ADAPTIVE` hiện là NHỊ PHÂN (regime up/down → SCALE_UP/NOTUP). Gate liên tục cần đọc **một giá trị gate float/ngày** từ CSV. Kiểm: có thể mở rộng `RegimeSchedule` đọc trực tiếp cột gate-value từ CSV (mỗi ngày 1 float) thay vì cờ up/down không? Sửa Java TỐI THIỂU (thêm chế độ đọc gate-value; giữ đường cũ + OFF byte-identical: khi không bật hoặc gate toàn 1.7... thực ra OFF = flag tắt → T170 nguyên). Nếu sửa, commit TRƯỚC sim, verify OFF md5 `efb793e2`.

## 3. BIẾN THỂ (khoá PREREG)
Baseline (không tính k): T170, gate-1.0, **BR nhị phân** (Bước 6, dùng lại số — để so continuous vs binary), BR0.
- **BRC (chính, khoá)**: gate liên tục §1, all-coin/MA200/thr50/1.0→1.7.
- **BRC0 (đối chứng)**: gate cố định đều khớp tổng n ≈ BRC (tách "giãn theo breadth" khỏi "giảm chung").
k phán quyết = 1 (BRC). Nếu muốn so all-coin vs top50 cho BRC → top50 là sweep MÔ TẢ, không phán quyết.

## 4. TIÊU CHÍ (khoá trước)
- u1 breadth: n_eff_total(BRC) ≥ 1.5× T170 (=909).
- u2 khẩu vị: PASS hiện hành, UW≤200 mọi năm + CAGR ≥ CI-floor T170.
- u3 vs incumbent: maxDD ≤ −14.8% VÀ UW ≤ 115.
- u4 giãn đúng: UW(BRC) < UW(BRC0) VÀ **return-2025(BRC) > return-2025(BR nhị phân)** (bằng chứng gate liên tục giữ được 2025 mà nhị phân cắt mất).
- u5 giữ uptrend: CAGR 2023&2024 BRC ≥ 90% gate-1.0.
- THẮNG = BRC đạt u1-u5. Ngay cả khi u1 chưa đạt ×1.5, nếu BRC **vượt trội T170 rõ** (CAGR cao hơn đáng kể + maxDD/UW trong khẩu vị + giữ 2025) thì ghi là "ứng viên incumbent mạnh" (khác NULL trắng) — MASTER đánh giá, KHÔNG tự tuyên THẮNG nếu u1 fail nhưng nêu rõ mức vượt T170.

## 5. ĐO — metric tổng hợp/phân phối, per-year, cùng cửa sổ 2021-07..2025-12.

## 6. QUY TRÌNH
PREREG `docs/prereg/PREREG_BREADTH_CONT.md` (cơ chế + gate formula + biến thể + u1-u5 + dự báo + phán quyết) commit TRƯỚC → recon+sửa RegimeSchedule tối thiểu (nếu cần) + sinh CSV gate-value từ breadth-score + profile BRC/BRC0 → cổng OFF T170 md5 `efb793e2` → dừng shadow-c3 → sim tuần tự (T170 verify, BRC, BRC0) → bật shadow-c3 verify → tính u1-u5 (`bigdown_struct.py`+`x1_rates.py`) per-year, so BR nhị phân → `docs/result/RESULT_BREADTH_CONT.md` verdict + đối chiếu dự báo + bảng BRC vs BR vs T170 → commit branch `module` (KHÔNG push) → dọn wfo_ds tạm, giữ printDone/sim.out.
OFF không byte-identical → DỪNG, báo MASTER.

## 7. Ý nghĩa
BRC vượt trội T170 rõ (giữ 2025 + UW thấp + CAGR cao + khẩu vị pass) ⇒ ý Uni (breadth + giãn động) thành công ⇒ shadow forward BRC song song trước khi bàn đổi incumbent. BRC ≈ BR (continuous không hơn binary) hoặc vẫn u1/u2 fail ⇒ breadth đã tới giới hạn, đóng với BR/BRC là cải tiến khiêm tốn (shadow nếu muốn), TASK D là hướng chính.

## 8. Sau khi xong: cập nhật project memory (`round...`+`MEMORY.md`), báo MASTER: bảng T170/gate-1.0/BR/BRC/BRC0 (n_eff, ICC, maxDD, UW, CAGR+CI, per-year), u1-u5 ✅/❌, **so BRC vs BR nhị phân (continuous có giữ được return-2025 không)**, verdict + mức vượt T170, cổng OFF PASS, mốc shadow, diff Java.
