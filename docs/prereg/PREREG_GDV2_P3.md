# PREREG_GDV2_P3 — AMENDMENT: G2 @stress + độ bền P3 + phân rã quý chết 2025 (tiếp TASK GDV2)

**Chốt TRƯỚC khi chạy số.** Ngày: 2026-09-29 (TASK GDV2_P3). Nhánh `module`, HEAD `39944db`.
Nguồn yêu cầu: MASTER `TASK_GDV2_P3.md` (owner Uni chốt 09-29). Tiếp theo **§6 PREREG_GDV2_EVEN**
(`2b4dcbd`): G2 (GDV2 W90) đã **PASS cả 4 tầng @base** + **đều hơn G0** (CVn 0,505 < 0,693; min n 26 > 6);
nay chạy **@stress** + **độ bền P3** (cặp G2 vs G0 ở CẢ @base và @stress) để trả lời dứt khoát luật §6.

Khuôn P3 = y hệt `PREREG_GD92_R4_P3.md` (`15e3d40`, đã chạy cho D1) + `RESULT_GD92_R4_P3.md`.

Ràng buộc cứng: sim chạy **TRÊN KAGGLE** (0 sim Oracle; bundle `sim-x1-2021-bundle` + dataset jar
`sim-jar-gdv2`) · **DÙNG LẠI jar GDV2 đã build** (sha256 `7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a`)
· **KHÔNG build lại** · **KHÔNG merge** · KHÔNG chạm 242/shadow/ONNX/LIVE · **DEV ≤ 2025-12-31** (2026 =
HOLDOUT, không đọc/không dùng) · KHÔNG push dữ liệu · output tool nhỏ · `nice -n 10`.

---

## 0. MỤC ĐÍCH (1 câu)

Trên nền R4 (KEEPLEG0, nhịp 1', `F_BASE 0.015`, `K=16`, gate scale `1.55`, phí base), arm **G2** (GDV2:
`SIM_GATE_ROLLING_MODE=ratio`, `SIM_GATE_ROLLING_PCT=0.99995083`, `SIM_GATE_ROLLING_DAYS=90`) đã qua 4
tầng @base; nay kiểm **@stress** và **độ bền P3** (cặp G2 vs G0 ở CẢ @base và @stress) để theo **§6**:
chỉ đề xuất G2 thay R4 khi cả 3 điều kiện — (i) PASS 4 tầng @base+@stress, (ii) jackknife G2 không tệ
hơn G0, (iii) CI chênh Calmar không âm ngoài 0.

---

## 1. ARM MỚI (khoá trước — KHÔNG arm nào khác)

Nền chung mọi arm = profile **`profiles/r4_kg0_k16_f015_g155.properties`** (chính là baseline R4). Jar
GDV2 (same binary đã chạy G0/G1/G2 @base), dataset `sim-jar-gdv2`, bundle `sim-x1-2021-bundle`,
`sim_end_date=20251231`, `code_sha=2b4dcbd+cp1db0613`.

| arm | thay đổi so R4 | ghi chú |
|---|---|---|
| **G0s** | + `SIM_SLIPPAGE_RATE=0.000259` (giữ `SIM_RATE_FEE=0.000982`) ⇒ `0,150 %/vòng` | **G0 @stress = mốc**. Parity BẮT BUỘC `md5(printDone) = 84402b57c2fa43b72f86a918e3e54e11` (= R4@stress `p2-r4-stress`, n 2027, eq 103 351) |
| **G2s** | + `SIM_GATE_ROLLING_MODE=ratio` + `SIM_GATE_ROLLING_PCT=0.99995083` + `SIM_GATE_ROLLING_DAYS=90` + `SIM_SLIPPAGE_RATE=0.000259` | **G2 @stress = ứng viên** |

- `SIM_GATE_P15_Q` (GATE-RECAL) **KHÔNG khai** ở mọi arm.
- **Parity:** R4@stress đã tồn tại (`kaggle_sim/out/p2-r4-stress`, `RESULT_RESET_RULE_P2` §1) ⇒ **G0s phải
  khớp md5 `84402b57…`**. Lệch ⇒ DỪNG (không chấm tiếp), báo FAIL parity.
- `k = 2` ứng viên (G1/G2 từ GDV2_EVEN) ⇒ **`inflate(k=2) = sqrt(2·ln2) = 1,1774`** cho tầng 3, seed
  `20260905`, NREP 2000, block 72h (giữ nguyên như @base).

---

## 2. CHẤM 4 TẦNG @stress — CÙNG CODE NHƯ @base

Dùng lại `research/analysis/reset_rule_gdv2_driver.py` (gọi `reset_rule_score.py` + áp §9 T1–T4 đúng) với
`TAGS = {gdv2-g0-stress, gdv2-g2-stress}`, `B_STAR = gdv2-g0-stress`, chấm "as-is" (phí stress đã nằm trong
artifact, không hiệu chỉnh lại). Các tầng §9 giữ nguyên:
- **T1** RÀO RỦI RO: maxDD MTM-phút năm xấu nhất ≤ 40 % · UW ≤ 250 ngày · quý xấu nhất ≥ −20 % · 0 năm âm (CỨNG) · conc 1 coin ≤ 15 % (CỨNG).
- **T2** RÀO ĐỘ BỀN: `q* ≥ 15 %` · `%PnL top-1% lệnh ≤ 25 %`.
- **T3** NON-INFERIORITY vs G0s: `win% ≥ −2,0 pp` · `TSloss% ≤ +2,5 pp` (điểm ước lượng).
- **T4** MỤC TIÊU (ưu tiên số lệnh): `Calmar_MTM ≥ 0,90 × G0s` · `conc ≤ G0s` (`n` là mục tiêu chính, báo cáo).

---

## 3. ĐỘ BỀN P3 — cặp (G2 vs G0) ở CẢ @base và @stress

Định nghĩa **episode y như `RESULT_RESET_RULE_P3`**: ngày-vào liên tiếp cách **≤ 2 ngày trống**. Sắp episode
theo **ΣPnL giảm dần**.

**T1 — episode jackknife bỏ top-1/3/5** (mỗi mức k ∈ {1,3,5}, cả @base và @stress):
- Dựng đường equity `35000 + cumΣPnL_còn` (theo ngày-vào); đo `ΣPnL_còn(k)`, `CAGR_còn(k)`, `maxDD_còn(k)`
  (ngày), `Calmar_còn(k) = CAGR_còn / |maxDD_còn|`.
- **"G2 không tệ hơn G0" tại mức k ⟺ `ΣPnL_còn(G2,k) > 0` VÀ `Calmar_còn(G2,k) ≥ Calmar_còn(G0,k)`.**
- **PASS ⟺ đúng ở MỌI k ∈ {1,3,5} ở CẢ @base và @stress.**

**T2 — bootstrap cụm episode (5000 rep, seed `20260928`), paired lưới khối CHUNG** (episode của hợp ngày-vào 2 arm):
- `CI95` của **ΔCalmar** (`= G2 − G0`, đường dựng lại theo ngày — đúng như `RESULT_RESET_RULE_P3` §7.1; điểm
  `ΔCalmar_MTM` từ bảng 4-tầng báo RIÊNG làm tham chiếu), **ΔCAGR**, **Δn**, **ΔΣPnL**.
- **"CI chênh Calmar không âm ngoài 0" ⟺ `lo(ΔCalmar) > 0`.**

---

## 4. LUẬT KẾT LUẬN (giữ nguyên §6 — KHÔNG nới)

Đề xuất **G2 thay R4** ⟺ **PASS 4 tầng @base + @stress** VÀ **jackknife G2 không tệ hơn G0** (mọi mức bỏ
1/3/5) VÀ **CI chênh Calmar không âm ngoài 0**. **Thiếu 1 điều ⇒ "G2 ≈ R4 về rủi ro-lợi nhuận, không thay"**
(giữ R4). **GHI RIÊNG** kết luận về **ĐỘ ĐỀU** (mục tiêu owner — T4 đặt `n` là mục tiêu chính) dù verdict
rủi ro-lợi nhuận thế nào.

---

## 5. CHẨN ĐOÁN MÔ TẢ (ghi trước để KHÔNG bị coi là tune — KHÔNG phải cổng)

**(a) Bảng quý ĐẦY ĐỦ 2021Q3..2025Q4 cho G0/G1/G2/D1** (`~/claude_master/0929/qstat_r4.py <tag>` + log
`[GATE-RATIO]`): `n (sel/BD/DCA)` · **số lần đánh giá ứng viên (seen)** · **số pass gate (pass)** · **tỉ lệ
pass (pass/seen)** · `win%` · `TSloss%` · `PnL` · `maxDD quý`.
- G0/G1/G2: seen/pass/pass-rate theo quý lấy từ dòng `[GATE-RATIO] ... | YYYYQn:pass/seen` (chính xác).
- D1 (GD92): `[GATE-ROLL]` **KHÔNG log per-quarter** (chỉ tổng `n_cand/n_pass` = 35 350 708 / 1895). ⇒ cột
  seen/pass của D1 báo tổng, đánh dấu "n/a theo quý" (GD92 gate khác cơ chế, không cùng thước).

**(b) PHÂN RÃ 2025Q2 (G0 33 → G2 26) và 2025Q3 — gate hay chỗ trống/CONC/top-K:**
- Chỉ số chính (đo chính xác từ log per-quarter): candidate evals (seen), gate pass (pass), pass rate
  (pass/seen) của G0 (base gate hằng 0.008) vs G2 (rolling ratio) ở 2025Q2/Q3; so pass rate hai arm để tách
  "gate (cửa sổ 90d còn nhớ 2025Q1 nóng)" khỏi "chỗ trống/CONC/top-K" (gate pass count vs actual PREDICT
  trades trong printDone ⇒ vacancy = pass − trades).
- **GIỚI HẠN (khai rõ):** jar GDV2 `GateRollingRatio` CHỈ log tổng per-quarter (không log `q_t` per-tuần/per-giờ
  như GD92 `[GATE-ROLL]` min/max). KHÔNG rebuild jar (kỷ luật) ⇒ **KHÔNG có `q_t` theo tuần trực tiếp**. Thay
  bằng (i) pass-rate theo quý — quan sát trực tiếp hiệu ứng của `q_t`; (ii) **[SUY LUẬN]** tái dựng dải nguỡng
  cuộn từ `pred.bin` DEV (phân vị cực của `p15` tại `pct=0.99995083`, W=90d, causal, cùng thuật toán
  `gd92_gate_diag.py` đổi PCT) làm minh hoạ XU HƯỚNG `q_t` — vì `r = p15/(factor×gs)` với `factor` gần hằng cho
  top-K (sp∈[0,25;0,34] ⇒ factor∈[2,2;2,9], floor 0,26787 hiếm bind) ⇒ xu hướng `q_t` ≈ xu hướng phân vị cực
  của `p15`. (Sai lệch: `pred.bin` là lưới 15' còn buffer thật là 1' — nên chỉ đọc XU HƯỚNG, không đọc giá trị.)

**(c) `q_t` tại 2025-12-31 so median `q_t` toàn kỳ** (dự báo trạng thái gate khi port live đầu 2026):
- Dùng pass-rate 2025Q4 (quan sát trực tiếp từ log, chính xác) + [SUY LUẬN] chuỗi nguỡng cuộn tái dựng từ
  `pred.bin` DEV tại mốc cuối DEV. **Chỉ đọc log sim DEV + `pred.bin` DEV, KHÔNG đụng dữ liệu 2026.**

---

## 6. RỦI RO (khai trước)

- Đây là lần test **~27 trên cùng DEV** (GDV2_EVEN ghi "lần thử ~26"; GD92 P3 = lần 3 cùng cấu hình GD92).
  `inflate(k=2)` **chưa tính lịch sử chọn** (L2 leak). Kết luận "G2 thay R4" (nếu có) vẫn là một quan sát duy nhất.
- **"Cùng tổng lượng mở" KHÔNG đạt**: G2 n 2 509 = **1,24× G0** (2 027) — vì phân vị 99,995 % trên cửa sổ HỮU
  HẠN 90d đánh giá thấp đuôi cực ⇒ `q_t` thấp hơn mức "cùng tổng" ⇒ mở nhiều hơn. ⇒ lợi ích **ĐỘ ĐỀU** lẫn với
  **tăng số lệnh**; không tách sạch hai hiệu ứng.
- Bootstrap `Calmar` dùng đường dựng lại **theo ngày** (không MTM phút) — đúng hạn chế `RESULT_RESET_RULE_P3`
  §7.1; điểm `ΔCalmar_MTM` (tầng 4) báo riêng, không trộn hai định nghĩa.

---

## 7. KỶ LUẬT

Không build lại jar · Không merge · 0 sim Oracle · Không chạm 242/shadow/holdout 2026 · Không quét biến thể
(pct khác 0.99995083, W khác 90d, scale khác 1.55, phí khác base/stress) · Không đổi incumbent production ·
Không port LIVE ở task này.
