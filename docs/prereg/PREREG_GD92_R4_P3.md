# PREREG_GD92_R4_P3 — AMENDMENT: D1 @stress + độ bền P3 (tiếp TASK D, theo đúng §6 PREREG_GD92_R4)

**Chốt TRƯỚC khi chạy số.** Ngày: 2026-09-29 (TASK D3). Nhánh `module`, HEAD `68a2836`.
Nguồn yêu cầu: MASTER `TASK_D3_gd92p3.md` (owner Uni chốt 09-29). Tiếp theo **§6 PREREG_GD92_R4**
(`2a759de`): D1 đã **PASS cả 4 tầng @base** (n 2141, Calmar_MTM 1,758); nay chạy **@stress** + **độ bền P3**
để trả lời dứt khoát luật kết luận §6.

Ràng buộc cứng: sim chạy **TRÊN KAGGLE** (0 sim Oracle; bundle `sim-x1-2021-bundle` + dataset jar
`sim-jar-gd92r4`) · **DÙNG LẠI jar GD92 đã build** (sha256 `1433f3d7138bdb0f71586d87b6efbe0cc350c80d747a9abba36362da9e5a69f3`)
· **KHÔNG build lại** · **KHÔNG merge `gd92-recheck`** · KHÔNG chạm 242/shadow/ONNX/LIVE · **DEV ≤ 2025-12-31**
(2026 = HOLDOUT, không đọc/không dùng) · KHÔNG push dữ liệu · output tool nhỏ.

---

## 0. MỤC ĐÍCH (1 câu)

Trên nền R4 (KEEPLEG0, nhịp 1', `F_BASE 0.015`, `K=16`, gate scale `1.55`, phí base), arm **D1** (GD92:
`SIM_GATE_ROLLING_PCT=0.92`, `SIM_GATE_ROLLING_DAYS=90`) đã qua 4 tầng @base; nay kiểm **@stress** và **độ bền P3**
(cặp D1 vs D0 ở CẢ @base và @stress) để theo **§6**: chỉ đề xuất D1 thay R4 khi cả 3 điều kiện — (i) PASS 4 tầng
@base+@stress, (ii) jackknife D1 không tệ hơn D0, (iii) CI chênh Calmar không âm ngoài 0.

---

## 1. ARM MỚI (khoá trước — KHÔNG arm nào khác)

Nền chung mọi arm = profile **`profiles/r4_kg0_k16_f015_g155.properties`** (chính là baseline R4). Jar GD92
(same binary đã chạy D0/D1/D2 @base), dataset `sim-jar-gd92r4`, bundle `sim-x1-2021-bundle`, `sim_end_date=20251231`.

| arm | thay đổi so R4 | ghi chú |
|---|---|---|
| **D0s** | + `SIM_SLIPPAGE_RATE=0.000259` (giữ `SIM_RATE_FEE=0.000982`) ⇒ `0,150 %/vòng` | **D0 @stress = mốc**. Parity BẮT BUỘC `md5(printDone) = 84402b57c2fa43b72f86a918e3e54e11` (R4@stress = `p2-r4-stress`, n 2027, eq 103 351) |
| **D1s** | + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90` + `SIM_SLIPPAGE_RATE=0.000259` | **D1 @stress = ứng viên** |

- `SIM_GATE_P15_Q` (GATE-RECAL W=30d, cơ chế KHÁC) **KHÔNG khai** ở mọi arm.
- **Parity:** R4@stress đã tồn tại (`~/kaggle_sim/out/p2-r4-stress`, `RESULT_RESET_RULE_P2` §1) ⇒ **D0s phải khớp md5
  `84402b57…`**. Lệch ⇒ DỪNG (không chấm tiếp), báo FAIL parity.
- `k = 1` ứng viên (chỉ D1) nhưng cấu hình GD92 đã được chọn qua 2 vòng trước ⇒ **`inflate(k=2) = sqrt(2·ln2) = 1,1774`**
  cho tầng 3, seed `20260905`, NREP 2000, block 72h (giữ nguyên như @base).

## 2. CHẤM 4 TẦNG @stress — CÙNG CODE NHƯ @base

Dùng lại `research/analysis/reset_rule_gd92r4_driver.py` (gọi `reset_rule_score.py` + áp §9 T1–T4 đúng) với
`TAGS = {gd92-r4-d0-stress, gd92-r4-d1-stress}`, `B_STAR = gd92-r4-d0-stress`, chấm "as-is" (phí stress đã nằm trong
artifact, không hiệu chỉnh lại). Các tầng §9 giữ nguyên:
- **T1** RÀO RỦI RO: maxDD MTM-phút năm xấu nhất ≤ 40 % · UW ≤ 250 ngày · quý xấu nhất ≥ −20 % · 0 năm âm (CỨNG) · conc 1 coin ≤ 15 % (CỨNG).
- **T2** RÀO ĐỘ BỀN: `q* ≥ 15 %` · `%PnL top-1% lệnh ≤ 25 %`.
- **T3** NON-INFERIORITY vs D0s: `win% ≥ −2,0 pp` · `TSloss% ≤ +2,5 pp` (điểm ước lượng).
- **T4** MỤC TIÊU (ưu tiên số lệnh): `Calmar_MTM ≥ 0,90 × D0s` · `conc ≤ D0s` (`n` là mục tiêu chính, báo cáo).

## 3. ĐỘ BỀN P3 — cặp (D1 vs D0) ở CẢ @base và @stress

Định nghĩa **episode y như `RESULT_RESET_RULE_P3`**: ngày-vào liên tiếp cách **≤ 2 ngày trống**. Sắp episode theo
**ΣPnL giảm dần**.

**T1 — episode jackknife bỏ top-1/3/5** (mỗi mức k ∈ {1,3,5}, cả @base và @stress):
- Dựng đường equity `35000 + cumΣPnL_còn` (theo ngày-vào); đo `ΣPnL_còn(k)`, `CAGR_còn(k)`, `maxDD_còn(k)` (ngày),
  `Calmar_còn(k) = CAGR_còn / |maxDD_còn|`.
- **"D1 không tệ hơn D0" tại mức k ⟺ `ΣPnL_còn(D1,k) > 0` VÀ `Calmar_còn(D1,k) ≥ Calmar_còn(D0,k)`.**
- **PASS ⟺ đúng ở MỌI k ∈ {1,3,5} ở CẢ @base và @stress.**

**T2 — bootstrap cụm episode (5000 rep, seed `20260928`), paired lưới khối CHUNG** (episode của hợp ngày-vào 2 arm):
- `CI95` của **ΔCalmar** (`= D1 − D0`, đường dựng lại theo ngày — đúng như `RESULT_RESET_RULE_P3` §7.1; điểm
  `ΔCalmar_MTM` từ bảng 4-tầng báo RIÊNG làm tham chiếu), **ΔCAGR**, **Δn**, **ΔΣPnL**.
- **"CI chênh Calmar không âm ngoài 0" ⟺ `lo(ΔCalmar) > 0`.**

## 4. LUẬT KẾT LUẬN (giữ nguyên §6 — KHÔNG nới)

Đề xuất **D1 thay R4** ⟺ **PASS 4 tầng @base + @stress** VÀ **jackknife D1 không tệ hơn D0** (mọi mức bỏ 1/3/5) VÀ
**CI chênh Calmar không âm ngoài 0**. **Thiếu 1 điều ⇒ "D1 ≈ R4, không thay"** (giữ R4).

## 5. CHẨN ĐOÁN MÔ TẢ (ghi trước để KHÔNG bị coi là tune — KHÔNG phải cổng)

**(a) Ngưỡng GD92 hiệu dụng theo QUÝ (D0 vs D1):**
- Tái dựng chuỗi nguỡng cuộn (92-phân-vị predReturn15M, W=90d, causal, nearest-rank KHÔNG nội suy — đúng code
  `GateRollingThreshold.init`) từ `pred.bin` DEV (`wfo_ds_x1_2021`); xác nhận min/max khớp log `[GATE-ROLL]`
  (`0,00456 / 0,01265`) trước khi dùng.
- Báo **median/p10/p90 theo quý** của nguỡng cuộn, so hằng `0.008`; và **% giờ gate mở theo quý** = fraction mẫu 15'
  có `predReturn15M ≥ nguỡng hiệu dụng` (D0 dùng hằng 0,008; D1 dùng nguỡng cuộn).

**(b) Bảng quý ĐẦY ĐỦ 2021Q3..2025Q4 (mọi quý, kể cả 2025Q4)** cho D0/D1 (`~/claude_master/0929/qstat_r4.py <tag>`):
`n (sel/BD/DCA) · win% · TSloss% · meanP% · PnL · maxDD quý`.

**(c) Ngưỡng GD92 tại mốc cuối DEV 2025-12-31** so hằng `0.008` — **chỉ đọc `pred.bin` DEV, KHÔNG tính trên dữ liệu 2026**.

## 6. RỦI RO (khai trước)

- Đây là lần test **THỨ 3** cùng cấu hình GD92 (pct `.92`/W90 được chọn từ vòng DEV cũ — `AUDIT_GATEDYN_GD92`) ⇒
  `inflate(k=2)` **chưa tính lịch sử chọn** (L2 leak). Kết luận "D1 thay R4" (nếu có) vẫn là một quan sát duy nhất,
  không phải bằng chứng đa vòng độc lập.
- Bootstrap `Calmar` dùng đường dựng lại **theo ngày** (không MTM phút) — đúng hạn chế `RESULT_RESET_RULE_P3` §7.1;
  điểm `ΔCalmar_MTM` (tầng 4) báo riêng, không trộn hai định nghĩa.

## 7. KỶ LUẬT

Không merge `gd92-recheck` vào `module`. Không build lại jar. 0 sim Oracle. Không chạm 242/holdout 2026.
Không quét biến thể (pct khác 0.92, W khác 90d, scale khác 1.55). Không đổi incumbent production. Không port LIVE ở task này.
