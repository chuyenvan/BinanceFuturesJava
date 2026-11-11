# PREREG R4_SIGNAL_SCREEN — sàng offline 3 chiến lược quyết định trên p15 (C1 SURPRISE60, C2 NOVELTY15, C3 META60)

Ngày 2026-11-11. Viết và commit TRƯỚC khi đếm hay chạy bất cứ thứ gì của R4. Nguồn thiết kế: `~/claude_master/res1109/r4_signal/PHA0.md` (sha256 f195af18…) §3–§4; MASTER duyệt chạy sàng cả 3, chưa sim.

## 0. Khai báo
- Họ gate đã thử ≥12 biến thể (G1–G5, B1–B2, GATE_SMART V-a..d qua S1–S5, GATE_VZ VA/VB, H60/RULE/NOCAL, GQSF, GKF). DEV 2022–25 và HO 2026 đã dùng nhiều lần.
- Tác giả ĐÃ THẤY trước khi viết: R3 P1, R3b, R3_FUTILITY (MEAN60/MTF-OR âm), GATE_SMART S4 (FALSE: chất lượng ô quanh ngưỡng phẳng), proxy novelty/surprise market-level (`novelty_1111.log`: 22,7 % phút top là đỉnh mới 15′; ACF15 của surprise 0,30; 90 vs 42 đợt). Xác suất tiên nghiệm thấp (PHA0 §5: qua sàng C1 ~20 %, C2 ~15 %, C3 ~10 %).
- Sàng này chỉ ĐO fwd return mô tả (không exit/DCA/U_MAX thật). Không PnL sim, không MTM. HO 2026 KHÔNG dùng.

## 1. Dữ liệu cố định
- pred gate 8 seed n4f-b0: `~/claude_master/res1109/r3_gate/pred/pred_s{42,7,13,21,99,123,777,2024}.bin` (md5 như PREREG_R3_GATE_FAMILY §3).
- Ô ứng viên: `gate_offline` (`research/analysis/gate_offline.py`), `cand_base.npz` (K=24), held = printDone `~/claude_master/nup4_fix/results/n4f-b0-*/storage/printDone.csv`. Không mô hình skipFull/U_MAX (giới hạn đã biết; xử lý bằng điều kiện (c) §4).
- B0 = `run_g2` pct 0.999950829, 90 ngày, q theo giờ, warm-up 7d.
- Cửa sổ DEV chấm: ts ∈ [2022-01-01, 2026-01-01) (+07). C3 dùng thêm 2021-07-01..2021-12-31 CHỈ để huấn luyện.
- fwd: kline1m Vision trên Kaggle `vz-kline1m-2021..2026`.

## 2. Ứng viên (tham số cố định, không quét lưới)
Chung: chỉ ô PREDICT (sp); không đổi K/held; thời gian thật theo phút; thiếu dữ liệu ⇒ fail-closed như mô tả.
- **C1 SURPRISE60**: b(t) = TB p15 các phút s ∈ [t−60′, t−1′] (cần ≥48 giá trị, thiếu ⇒ ô không hợp lệ); u(t) = p15(t) − b(t) (float32). r_u = u/(max(DYN_MIN, sp/0,15·1,2876)·1,55). Buffer nhận r_u của MỌI ô hợp lệ (như B0), q_u = phân vị pct_1 trên 90 ngày, theo giờ, warm-up 7d. PASS ⇔ !(u < q_u·fac·gs) VÀ p15(t) ≥ 0,008.
- **C2 NOVELTY15**: PASS ⇔ luật B0 (cùng r, buffer) với pct_2 VÀ p15(t) > max p15[t−15′, t−1′] (cần ≥12 giá trị, thiếu ⇒ không pass).
- **C3 META60**: tập CHÍNH = luật B0 với pct_3 sao cho Σ8 seed số ô DEV = 1,5 × B0 (±5 %). Bộ lọc: hồi quy logistic (sklearn `LogisticRegression(C=1.0, max_iter=1000)`, StandardScaler fit trên train, NaN điền trung vị train) — KHÔNG chỉnh siêu tham số. 7 feature (causal, theo từng seed): (1) r/q_3; (2) u(t) như C1; (3) TB p15 [t−59′, t] (cần ≥48); (4) số phút từ đầu đợt (đợt = cụm phút có ≥1 ô chính pass, cách >60′; tính tới t); (5) số ô chính pass toàn thị trường trong [t−60′, t−1′]; (6) hạng sp (1..24); (7) log(1 + số leg B0 đang mở tại t theo printDone B0 cùng seed). Nhãn y = 1{c72/c0 − 1 − 0,002 > 0}. WFO THEO NĂM: mô hình năm Y ∈ {2022..2025} huấn luyện trên ô chính cùng seed có ts < 01-01-Y − 72h (từ 2021-07-01), có nhãn. Giữ ô ⇔ prob ≥ τ(h); τ(h) = phân vị 1/3 của prob (mô hình năm hiện hành) trên ô chính cùng seed trong [h−90d, h); <50 ô ⇒ dùng phân vị 1/3 của prob trên tập train. Tỉ lệ giữ 2/3 cố định.

## 3. Iso-count và quota (chỉ ĐẾM, trước mọi fwd)
- pct_1, pct_2, pct_3 tìm bằng đếm: với mỗi seed tính số ô DEV theo một lưới pct cố định (60 điểm log-đều trên 1−pct ∈ [5e-6, 5e-4]), chọn pct có Σ8 seed gần mục tiêu nhất (C1, C2: T = Σ B0; C3: 1,5·T), rồi đếm lại đúng pct đó. Không đạt |N/target − 1| ≤ 5 % ⇒ LOẠI.
- Quota năm: với từng năm 2022..2025, median 8 seed của (số ô arm / số ô B0) ∈ [0,85; 1,15]; C3 áp cho tập SAU lọc (và tổng sau lọc phải ∈ ±5 % của T). Ngoài ⇒ LOẠI, không chỉnh.

## 4. Sàng fwd (chỉ ứng viên qua §3)
- Theo seed: THÊM = ô arm \ ô B0; BỚT = ô B0 \ ô arm (khoá (ts, sym)); gộp 8 seed theo (ts, sym, nhóm), trọng số n_seed (như S4).
- ret_H = close(t+1′+H)/close(t+1′) − 1 − 0,002; H = 72h (chính), 24h (phụ); giá lấy như `s4k.py` (bản ghi ≤5′ trước mốc); NaN bỏ, báo số.
- Bootstrap cụm NGÀY (+07): một danh sách 2 000 mẫu ngày (rng seed 20261111) trên hợp các ngày có ô THÊM/BỚT của cả 3 ứng viên, dùng chung. Thống kê = mean_w(THÊM) − mean_w(BỚT).
- QUA ⇔ đủ cả 4: (a) cận dưới CI hai phía 96,7 % (phân vị 1,65 / 98,35) > 0 (H72); (b) hiệu điểm > 0 ở ≥3/4 năm 2022–25; (c) hiệu điểm > 0 khi bỏ mọi ô (cả hai nhóm) ở phút sổ B0 "bão hoà" = số leg B0 đang mở ≥ phân vị 95 % của chính seed đó trên các phút DEV; (d) đạt §3.
- Báo kèm (không chấm): |THÊM|, |BỚT|, H24, Jaccard phút, số ô/giờ tối đa.

## 5. Luật sau sàng
- Qua sàng ⇒ chỉ được sim 8 seed (futility 4 seed) sau prereg Pha 1 riêng do MASTER duyệt. GO (nếu có) ⇒ chỉ forward shadow paper, KHÔNG đổi v1.2.
- Cả 3 trượt ⇒ ĐÓNG hướng "dùng p15 theo thời gian cho gate".
- Không đổi luật/tham số sau khi thấy số; lỗi code phát hiện sau ⇒ addendum ghi rõ, chạy lại toàn bộ.

## 6. Thực thi
- Oracle: đếm qua `flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10`, kiểm free ≥4000 MB, đĩa ≥15 GB. Code `research/r4_signal/`. Kaggle: 1 kernel fwd `r4s-fwd` (dataset `r4s-cells`, `enable_internet=false`, không jar), tái dùng logic `research/gate_smart/s4k.py`. Vòng tự chờ trên Oracle có file STOP + log.
