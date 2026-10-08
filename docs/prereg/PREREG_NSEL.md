# PRE-REG NSEL — tăng số lệnh có chọn lọc quanh K24 (gate 2 tầng + LÕI cộng dồn)

Ngày: 2026-10-08. Tác giả: MASTER. Chốt TRƯỚC mọi kernel đo kết quả. Không đổi sau khi thấy số; mọi sửa đổi = ADDENDUM có hash, ghi rõ đã/chưa nhìn số.

## 1. Mục tiêu và lý do
- Owner (10-08): muốn thêm khoảng 1k lệnh/năm so với nền K24 (~740 chân/năm, 2022–25). Chấp nhận maxDD sâu hơn. "n tăng mà PnL giữ" cũng là thắng.
- Bằng chứng trước (DEV ≤ 2025-12-31):
  - N_DEEP 3ee1f50e: nới gate/K vô điều kiện (arm D = K32 pct 0,999915) thêm ~848 chân/năm nhưng ΔΣPnL stress −2,1k, iso-risk kém hơn.
  - NSEL_P0 data 0c68609c (J3): 97,6% lệnh nền bị MẤT ở arm D là do KHOÁ SYMBOL — arm đã vào cùng coin sớm hơn (trung vị 0,3–0,6h) bằng lệnh MỚI (ROI_S leg0 −1,15…−1,57%), chặn lệnh nền tốt hơn (+2,83…+3,20%). Gate 0%, sổ đầy ≤1,6%.
  - NSEL_P0B 15ea876b: sim và live đều 1 vị thế gộp/symbol; phương án (a) CORE_ADD khả thi ở sim; cận ΣPnL_S chân cộng dồn (size theo U) +20…+36k/seed (xấp xỉ, in-sample, KHÔNG phải bằng chứng).
  - NSEL_P0 code 23e4204a: nến quyết định = nến có close = giá vào cho mọi loại chân ⇒ bộ lọc nến sập NHÂN QUẢ. Stress post-hoc chỉ bắt 60–68% mức sụt PnL so với in-sim ⇒ luật GO dùng stress IN-SIM.
- Giả thuyết: (H1) Lệnh nới gate chỉ có hại vì chiếm chỗ lệnh nền cùng coin. Bỏ khoá đó (cho LÕI cộng dồn vào vị thế THÊM) ⇒ giữ được lệnh nền mà vẫn có lệnh thêm. (H2) Lọc thêm lệnh THÊM vào nến quyết định sập bỏ phần lệnh thêm có PnL stress ≈ 0.

## 2. Cơ chế (code trên branch feat/nsel; mọi key mặc định OFF ⇒ byte-identical với module)
- Tầng LÕI = gate hiện tại, không đổi: SELECTOR_RANK_TOPK 24, SIM_GATE_ROLLING_PCT 0,999950829, DAYS 90, GATE_QUOTA_SKIP_WHEN_FULL=true, buffer LÕI như cũ.
- Tầng THÊM (key NSEL_ADD_*): ứng viên hạng ≤ 32 (NSEL_ADD_TOPK=32) chỉ xét khi KHÔNG qua LÕI. Buffer rolling RIÊNG (instance thứ 2), quần thể = r của hạng ≤ 32 khi sổ không đầy, pct 0,999915, DAYS 90, warm-up 7 ngày như LÕI. THÊM không tiêu và không nạp buffer LÕI.
- Khoá symbol: coin đang giữ vẫn bị loại khỏi cả 2 tầng, TRỪ CORE_ADD.
- CORE_ADD (M1, M2): khi coin đang giữ bởi cụm có leg0 thuộc tầng THÊM và coin đó qua gate LÕI (hạng ≤ 24, r ≥ q_LÕI; dùng queryOnly — không nạp buffer cho coin đang giữ, giữ nguyên quần thể buffer LÕI như nền) ⇒ thêm 1 chân CORE_ADD vào cụm:
  - Size = size leg0 bình thường tại thời điểm đó (managerBudget/U hiện tại). Không vượt U_MAX/CONC-PC (nếu vượt ⇒ bỏ, đếm).
  - Tối đa 1 CORE_ADD/cụm. Không tính vào bậc DCA grid.
  - Gộp như DCA hiện có (giá bình quân, quy tắc thoát hiện có của cụm gộp).
  - Cập nhật mốc "lệnh LÕI" của cụm. Không đổi gì cho cụm có leg0 LÕI.
- F1 (chỉ M2): tầng THÊM chỉ vào leg0 khi nến quyết định close/open − 1 > −1% (NSEL_ADD_F1_MIN_BARRET=−0,01). Không áp lên LÕI, BIG_DOWN, DCA, CORE_ADD.
- Stress in-sim: port SIM_CRASH_ENTRY_PENALTY từ wt_crashpen (efd85d6d) lên module, ngưỡng nến quyết định close/open − 1 ≤ −1%, áp cho MỌI loại chân (PREDICT, BIG_DOWN, DCA, CORE_ADD). Counter [CRASH-PENALTY] chuyển ra SAU mọi return (đếm đúng chân thực sự vào).
- Dọn: key GATE_BUFFER_TOPK (d3fb1f00, claw) thay bằng NSEL (giữ hàm queryOnly nếu dùng lại), có test.
- Counter log [NSEL] cuối run: core_pass, add_pass, add_rej_f1, add_rej_cap, core_on_held_by_add (would/done), core_add_rej_cap, n chân theo tầng/loại.

## 3. Khớp nối bắt buộc (FAIL bất kỳ ⇒ dừng, không chấm arm)
- J-A Unit test: quyết định 2 tầng; THÊM không nạp buffer LÕI; CORE_ADD tối đa 1/cụm và chỉ khi leg0 THÊM; F1 chỉ áp tầng THÊM; penalty áp đúng nến/loại chân; OFF ⇒ hành vi cũ; fail-fast khi bật cùng key xung đột. Toàn bộ test module PASS.
- J-B OFF byte-identical trên Kaggle: jar mới, mọi NSEL OFF, penalty 0 ⇒ md5 printDone trùng gqsf-a1 (seed 42) và gqsf-s7 (seed 7).
- J-C Port penalty: jar mới chạy lại đúng cấu hình run in-sim của wt_crashpen (flat3-cp-p1 hoặc run tương đương có sẵn) ⇒ md5 printDone trùng; nếu không trùng ⇒ giải thích từng khác biệt (chỉ chấp nhận khác biệt do sửa counter, không đổi lệnh).
- J-D M0 ≈ D: M0 (2 tầng, KHÔNG CORE_ADD, KHÔNG F1, penalty 0) seed 42/7/21 so với gkf-l2-k32 / gkf2-l2k32-s7 / -s21: n/năm trong ±10%, tỉ lệ MẤT do khoá symbol ≥ 80%. Lệch ⇒ dừng, điều tra (2 tầng không tái hiện cơ chế đã đo).
- J-E Counter khớp printDone: số chân CORE_ADD trong printDone = counter; không cụm nào > 1 CORE_ADD; CONC ≤ 15% mọi phút; chân penalty = chân vào nến sập (đối chiếu nến 1m, 100%).
- J-F Hai scorer độc lập (2 agent, 2 script viết riêng) cho bảng chính; lệch > 0,1% ở số bất kỳ trong luật GO ⇒ hoà giải trước khi kết luận.

## 4. Arm và seed
- NỀN-S: jar mới, NSEL OFF, penalty 0,01675, 8 seed (42/7/13/21/99/123/777/2024).
- M1-S: 2 tầng + CORE_ADD, penalty 0,01675, 8 seed.
- M2-S: 2 tầng + CORE_ADD + F1, penalty 0,01675, 8 seed.
- Phụ (không vào luật GO): M0 penalty 0 seed 42/7/21 (J-D); M1, M2 penalty 0 seed 42/7/21 (so với gqsf-* base cost, báo cáo).
- pred.bin theo seed như các vòng gqsf/gkf (md5 verified). Profile g2_flat3 + override như gqsf-a1. Kernel tools/kaggle_sim.py HEAD (NOWRITE242). Tối đa 2 kernel song song.

## 5. Thước
- Cửa sổ 2022-01-01 … 2025-12-31 (DEV); 2026 niêm phong.
- n = số chân/năm (printDone, mọi loại). ΣPnL22–25, CAGR22, maxDD22 MTM phút, Calmar22 MTM, UW22, theo năm và quý.
- Δ ghép cặp theo seed vs NỀN-S. Paired t (df 7) + MTM block-10d bootstrap NREP 2000 seed 20260905 (báo cáo).
- Inflate cho so sánh nhiều arm: k = 2 (M1, M2) ⇒ cận một phía dùng t df 7 ở mức 1 − 0,10/2.

## 6. Luật GO (mỗi arm M1-S, M2-S, độc lập; cần TẤT CẢ)
- G1 Số lệnh: mean Δn ≥ +500 chân/năm.
- G2 PnL không kém: mean ΔΣPnL22–25 ≥ 0 VÀ cận dưới một phía (t df 7, mức 1 − 0,10/2) ≥ −8k (≈ 10% ΣPnL stress nền 81,7k).
- G3 Rủi ro: maxDD22 MTM ≤ 40% ở mọi seed; mean ΔmaxDD22 ≥ −8pp.
- G4 Hiệu quả: mean Calmar22 MTM ≥ 0,85 × NỀN-S.
- G5 Theo năm: mean ΔROI ≥ 0 ở ≥ 2/4 năm 2022–25 VÀ không năm nào mean ΔROI < −8pp.
- G6 Khớp nối J-A…J-F PASS.
- Chọn: nếu cả 2 GO ⇒ chọn arm có mean ΔΣPnL lớn hơn; chênh < 5k ⇒ chọn arm có n lớn hơn. Không arm nào GO ⇒ NO-GO, giữ K24 + skipFull.
- GO chỉ đủ điều kiện đi tiếp sang port live (resize STOP_MARKET khi thêm chân, giữ priceSL/timeStart, buffer + persist thứ 2, lastLeg0 khôi phục sau restart) + shadow. KHÔNG đưa thẳng lên tiền thật.

## 7. Kỳ vọng khai trước (MASTER)
- M1: Δn +1100…+1300 chân/năm; ΔΣPnL_S −5…+20k; ΔmaxDD −2…−6pp; P(GO) ~30%.
- M2: Δn +800…+950; ΔΣPnL_S 0…+20k; ΔmaxDD −1…−5pp; P(GO) ~35%.
- Rủi ro biết trước: giả thuyết sinh ra từ chính dữ liệu DEV này (N_DEEP/P0 nhìn 179 bộ lọc) ⇒ GO trên DEV vẫn có thiên lệch chọn lọc; CORE_ADD = trung bình giá xuống ⇒ tập trung 1 coin trong đợt sập; số đợt độc lập ~40/năm nên thêm lệnh trong cùng đợt không đa dạng hoá; live hiện chưa hỗ trợ resize SL khi thêm chân.
