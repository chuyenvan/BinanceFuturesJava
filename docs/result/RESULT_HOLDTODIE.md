# RESULT — HOLDTODIE: TẮT time-stop 168h ("hold to die") trên nền `G2 + FLAT3` — có MỞ THÊM entry không?

Pre-reg: `docs/prereg/PREREG_HOLDTODIE.md` (commit `9fa9ab88`, chốt **TRƯỚC** khi chạy). Luật: `docs/runbooks/RISK_APPETITE.md` §9.
Nhánh `module`. Sim **TRÊN KAGGLE** (0 sim Oracle) · bundle `sim-x1-2021-bundle`, **jar DÙNG LẠI `sim-jar-gdv2`**
(sha256 `7368be46…`, KHÔNG build/merge; đo được `7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a`) ·
`sim_end_date=20251231` · DEV ≤ 2025-12-31 · không đọc 2026 · `symbol_mapper=863`.
Nền: `profiles/r4_kg0_k16_f015_g155` + **6 override = `g2_flat3`** (như trail2/double-entries).

**Cách TẮT TS 168h (file:line):** `SIM_LOSER_TIME_STOP_HOURS=0` — cổng điều kiện
`SimulatorMarketLevelTicker1MStopLoss.java:1026` `if (loserTsHours > 0 && priceSL == null)` ⇒ `<= 0` = nhánh KHÔNG chạy
(= "0 = tắt", `Configs.java:477`/`:481`; parse `:903`). **H1 = `=0`; H0 = giữ `=168` (y `g2_flat3`, 0 override).**
H1 giữ nguyên `DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0` — đúng lưới **4 leg, KHÔNG thêm level**.

## 0. CỔNG PARITY — PASS

| cổng | yêu cầu | đo được | kết |
|---|---|---|---|
| **H0 = baseline `g2_flat3`** | `md5(printDone)=650c386f0d0dfea334af9d55ca2f21d4`, n 2517, eq 131 908 | **`650c386f0d0dfea334af9d55ca2f21d4`** · n **2517** · eq **131 908** | **PASS** (byte-identical) |
| jar DÙNG LẠI | sha256 `7368be46…` | `7368be46edb3fa…a82d6a` | **PASS** |
| `[GATE-RATIO]` bật thật | mode `ratio` `pct=0.99995083` `days=90` | `GATE-RATIO on pct=0.99995083 days=90 …` | **PASS** |
| `[CONC-PC]` 15 % | `blocked=0` | `[CONC-PC] SUMMARY blocked=0 pct=0.15` | **PASS** |

Kernel `chuyendinh/sim-htd-h0` / `sim-htd-h1` (both COMPLETE). H1 md5 `b00f344f9003684a155eb0bd8ae17572`.

## 1. BẢNG 2 ARM — 4 TẦNG §9 (as-is, phí base 0,112 %/vòng; `k=1`, `inflate=1,0`, seed `20260905`, block-72h)

| arm | n | Δn | equity | CAGR% | ddPhút% | UW(ngày) | q*% | top-1% | conc% | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **H0**=baseline | 2 517 | — | 131 908 | 34,31 | −17,68 | **87,1** | 26,4 | 14,97 | 4,09 | **1,940** | PASS | PASS | ref | ref |
| **H1** hold-to-die | **2 314** | **−203 (−8,07 %)** | **38 558** | **2,18** | −28,15 | **1472,4** | **1,2** | **94,69** | 4,53 | **0,077** | **FAIL** | **FAIL** | PASS | **FAIL** |

**H1 vỡ 3/4 tầng:**
- **T1 FAIL:** `UW 1472,4 > 250` (×**5,9** trần) **và** `0 năm âm` FAIL (**2022, 2025 âm**). (`maxDD phút/năm −26,19 ≥ −40` ✓; qmin −19,49 ✓.)
- **T2 FAIL:** `q* 1,2 < 15` **và** `%PnL top-1% 94,69 > 25` — lãi dồn hết vào **1 % lệnh**.
- **T3 PASS** (nhưng **vô nghĩa về chất lượng**): `win% +2,86 pp` · `TSloss% −13,96 pp` — vì `TSloss% = 0,35 %`
  (cụm gần như **không bao giờ đóng bằng cắt lỗ**, chỉ nằm mở).
- **T4 FAIL:** `Calmar 0,077 < 0,90×1,940 = 1,746` (**còn 4 %** baseline) **và** `conc 4,53 > 4,09`.

Ngưỡng T4 áp đo được: `Calmar ≥ 1,746` · `conc ≤ 4,09`.

## 2. BẢNG THEO NĂM và QUÝ (`n` · ΣPnL (đã thực hiện) · win %)

**H0 (control):** 2021 `434 · +6 486 · 83,9` · 2022 `423 · +4 609 · 81,1` · 2023 `527 · +24 918 · 85,4` · 2024 `599 · +30 842 · 89,5` · 2025 `534 · +30 054 · 87,1`.
**H1 (hold-to-die):** 2021 `425 · +2 959 · 93,9` · 2022 `274 · −1 772 · 74,8` · 2023 `433 · +1 814 · 95,6` · 2024 `591 · +754 · 91,5` · 2025 `591 · −330 · 83,9`.

- `n` H1 **thấp hơn H0 ở 4/5 năm** (2021 425<434, 2022 274<423, 2023 433<527, 2024 591≈599); 2025 nhích 591>534.
- **Quý tệ nhất (ΣPnL):** H0 `2022Q2 −334`; H1 `2021Q4 −2 712`, `2022Q1 −1 423`, `2024Q2 −1 122` — **hơn H0 nhiều lần**.
- ⚠️ ΣPnL ở đây là phần **ĐÃ THỰC HIỆN**; H1 giữ **cụm zombie MỞ** nên `equity 38 558` << `b_final 57 375`
  (unrealized **−18 817**) — lỗ khổng lồ **chưa chốt** vẫn ăn EQUITY.
- (Bảng quý đầy đủ: `docs/result/holdtodie.json` → `metrics.*.yq.Q`.)

## 3. TRẢ LỜI DỨT KHOÁT

**(1) Tắt TS 168h có MỞ THÊM entry không? — KHÔNG. `n` GIẢM.**
`n` **2 517 → 2 314 = −203 (−8,07 %)**. Không có thêm dòng lệnh nào; ngược lại mất 8 % số lệnh.

**(2) Chất lượng (T3) và RỦI RO thay đổi bao nhiêu?** — Chất lượng **trông tốt hơn nhưng giả**; **RỦI RO VỠ**:
- T3: `win% +2,86 pp` · `TSloss% −13,96 pp` (**PASS**, nhưng chỉ vì cụm không chốt ⇒ không ghi nhận SL).
- **Rủi ro vỡ trần:** `UW 87,1 → 1472,4 ngày` (**VƯỢT trần `UW ≤ 250` — 5,9 lần**); `ddPhút −17,68 → −28,15`
  (maxDD phút/năm −26,19 vẫn < 40 nên trần 40 **không** bind); **2 năm âm (2022, 2025)**; `top-1% 94,69` (trần 25);
  `q* 1,2` (sàn 15); `equity −70,8 %`, `CAGR 34,31 → 2,18 %`.

**(3) Vì sao `n` đổi — time-stop 168h có "giữ slot" không? — ĐÚNG, và bằng chứng ĐỊNH LƯỢNG rõ:**
| | H0 | H1 |
|---|---|---|
| số vị thế **đồng thời tối đa** | **55** | **210** |
| số vị thế **đồng thời TB** | 2,51 | **98,70** |
| **thời gian giữ TB** (cụm) | **38,4 h** | **1674,8 h (~70 ngày)** |
⇒ Time-stop 168h trước đây **cắt cụm thua lỗ để TRẢ SLOT/VỐN**. Tắt nó ⇒ cụm "trôi" ~70 ngày, **hai chục→trăm vị thế mở cùng lúc**
⇒ **không còn chỗ/margin cho entry mới** ⇒ **`n` giảm** −8 %, đồng thời **khoá vốn vào lỗ chưa chốt** (unrealized −18 817).

**(4) KẾT LUẬN — H1 = NULL (không đáng giữ làm baseline/ứng viên).**
H1 **KHÔNG qua 4 tầng §9** (vỡ T1, T2, T4; T3 PASS vô nghĩa). Đối chiếu bằng chứng cũ
(`RULERS_CURRENT.md` §10.4 + `RESULT_EXIT_STRUCT.md` A1, bối cảnh 15′/K=8: **`UW 166 → 318`**):
**xu hướng y hệt nhưng NẶNG HƠN nhiều trong bối cảnh MỚI** (G2, 1′, K=16, rolling gate) — `UW 87 → 1472`
(so với 166→318 cũ). **Trả lời owner: OFF hold-to-die = PHÁ HOẠI, không phải "mở rộng entry".**
Tắt TS 168h **làm mất 8 % lệnh** và **giết tail**; **GIỮ `SIM_LOSER_TIME_STOP_HOURS=168`.**

## 4. MỤC BỎ + LÝ DO

- **BỎ trục "tắt time-stop 168h để mở thêm entry"**: `n` **giảm** −203 (−8,07 %) vì cụm zombie
  giữ slot (đồng thời TB 2,51 → 98,70) ⇒ **time-stop 168h là VAN ĐIỀU TIẾT SLOT, không phải vật cản entry**.
- **BỎ "hold-to-die" như ứng viên chất lượng**: vỡ T1 (`UW 1472`), T2 (`q* 1,2`/`top-1% 94,69`), T4 (`Calmar 0,077`);
  2 năm âm. Đây là **countdown rủi ro**, không phải alpha.
- **Xác nhận luật hiện hành:** giữ `SIM_LOSER_TIME_STOP_HOURS=168` (+ FLAT3) làm baseline; muốn mở rộng `n`
  phải bằng **CẤU TRÚC (nguồn sự kiện thứ 2, OFI V3)** — đúng kết luận `RESULT_DOUBLE_ENTRIES.md` §4 / `DECISION 0013`.

## 5. LƯU VẤT

- Runner: `research/analysis/holdtodie_run.py` · chấm: `research/analysis/holdtodie_driver.py` (gọi `reset_rule_score.py`) · thô: `docs/result/holdtodie.json`.
- Artifact Kaggle: `~/kaggle_sim/out/htd-h0` (md5 `650c386f…`) · `~/kaggle_sim/out/htd-h1` (md5 `b00f344f…`).
- 0 sim Oracle · 2 kernel Kaggle CPU (0 quota) · không chạm 242/ONNX/LIVE/2026 · không push dữ liệu.
