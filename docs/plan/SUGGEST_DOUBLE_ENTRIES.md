# SUGGEST_DOUBLE_ENTRIES — Từ `G2 + FLAT3`: (a) gấp đôi số lệnh · (b) giảm margin tiếp

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Loại:** CHỈ ĐỌC + THIẾT KẾ (**0 sim / 0 train**).
**Baseline:** `profiles/g2_flat3.properties` = `r4_kg0_k16_f015_g155` + GDV2 rolling gate
(`SIM_GATE_ROLLING_MODE=ratio`, `PCT=0.99995083`, `DAYS=90`) + FLAT3 exit
(`TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`).
Số chuẩn: `@base` B0 = n **2517** · eq **131 908** · md5 `650c386f…` (`RESULT_FEAT_ADD_V1`);
`@stress` n **2509** · eq **129 642** · CAGR **33,79 %** · ddPhút −18,00 % · UW 128,9 · q* 23,7 ·
top-1 17,59 % · conc 4,09 % · Calmar_MTM **1,877** · **PASS 4 tầng** (`RESULT_GDV2_P3`, `b7f0358f`).
**Luật:** `docs/runbooks/RISK_APPETITE.md` §9 — T4: `n` là **MỤC TIÊU CHÍNH**, `Calmar_MTM ≥ 0,90×baseline`,
`conc ≤ baseline`.
**Ràng buộc:** không chạm 242/ONNX/LIVE · DEV ≤ 2025-12-31 · không push file dữ liệu.

---

## 0. TRẢ LỜI THẲNG

> **NULL.** Từ `G2 + FLAT3` **không có đường CONFIG** đạt đồng thời *gấp đôi `n`* **và** *giảm margin*.
> Lý do **cơ học, có số** (không phải thiếu try):
> 1. **`n` bị chặn bởi GATE, không bởi slot/vốn.** `RESULT_CAPACITY_DIAG` (`aedf535`): trên T170/DEV
>    `max U = margin/equity = 0,469 < 0,54`, **0/1644 ngày** chạm trần, `NO_BUDGET=0` trên 10,2 M quyết định;
>    17,9 M ứng viên → **841 PASS (0,0047 %)**. ⇒ **giảm size** hay **rút ngắn time-stop** *không* mở thêm lệnh.
> 2. **Giảm margin một mình = 0 lệnh thêm, CAGR tụt.** `RESULT_SIZE_COUNT` (`87a9f5c7`): B0 ×1 K8 → n **744**;
>    B1 ×0,5 K8 → n **745** (**y hệt**) nhưng CAGR 17,29 → **11,22**. `RESULT_2X_HALFSIZE`: chỉ nổ ×2 khi
>    **mở gate** (gate 1,30 + K12), và khi đó UW 92 → **223** (FAIL) · CAGR −7,9 pp.
> 3. **Mọi cách THẬT để tăng `n` đều là MỞ GATE, và đã đo là hạ chất lượng.** Xem bảng §1 — D2
>    (`pct 0,92` + `dyn_scale 1.00`) n **4287** (2,1× baseline) nhưng **FAIL CẢ 4 TẦNG**.
>
> **Còn 1 cửa hẹp chưa thử** (§2): giữ **nguyên** rolling gate G2, chỉ mở **K** (16 → 24/32) và hạ **size**.
> Ước lượng **+30…+65 % `n`** (→ ~3 300…4 100), **KHÔNG tới 2×**, và T1/T2/T3 nhiều khả năng vỡ.
> **Muốn thật sự gấp đôi SỰ KIỆN** ⇒ phải **thêm nguồn sự kiện thứ 2** (§3.2, OFI V3).

---

## 1. VIỆC 1 — INVENTORY LEVER (số THẬT)

`n` của baseline = **2 509**. Cột "Δn" là so với baseline đó (quy đổi nơi nền khác).

| # | lever (key) | đã thử? | kết quả `n` / chất lượng (số thật · commit) | trần chặn |
|---|---|---|---|---|
| 1 | `SELECTOR_RANK_TOPK` (K) | ✅ | `RESULT_K_DENSITY` (`1579f5a`): K8→12→16 = n 1089→1409→1730 (+59 %); **coverage tuần 33,8 % và gap dài nhất 129,24 ngày Y HỆT** cả 3 K ⇒ K chỉ dày **trong tuần gate mở**. Chất lượng: TSloss 9,73→11,79 · meanP 5,24→4,82 (XAU, ngoài CI). `RESULT_SIZE_COUNT`: B0 K8 744 → B2 K16 1152 → **B4 K32 1878** (×2,52) nhưng **UW 277 > 250**. | T2/T3 (chất lượng ↓ đơn điệu) · T1 (UW) ở K32 |
| 2 | `SIM_F_BASE` (size/margin) | ✅ | `RESULT_SIZE_COUNT`: B1 ×0,5 K8 = n **745 ≈ B0 744** ⇒ **giảm size KHÔNG thêm lệnh**; CAGR 17,29→11,22. `RESULT_2X_HALFSIZE`: size ×0,5 + mở gate ⇒ CAGR −5…−8 pp, UW ~222. | không phải lever `n` (0 lệnh); hạ CAGR |
| 3 | `SIM_GATE_DYN_SCALE` | ✅ | `RESULT_GATESCALE_KEEPLEG0` (`a75c00a`): 1,70→1,00 = n 1085→**2549 (×2,35)** nhưng UW 147→**248**, conc 7,12→**12,48 %**, meanP 5,15→3,26, TSloss 10,3→15,6 (**1 rate XAU ngoài CI**). `RESULT_GATESCALE_SWEEP` (`a450046`): **NULL — 0 điểm scale nào qua S1**; mọi thứ rủi ro XAU đơn điệu theo n. | T3 (TSloss) · T1 (UW/conc) |
| 4 | `SIM_GATE_ROLLING_MODE/PCT/DAYS` | ✅ | `RESULT_GDV2_EVEN` (`39944db`): W30 → n **3199** nhưng **FAIL 4/4** (2022 âm, UW 472,6). W90 (`pct=1−ρ`) → n **2509** **PASS 4/4** = **chính baseline**. `RESULT_GD92_R4` (`68a2836`): D1 (`pct 0,92`+scale 1,55) n 2141 · D2 (`pct 0,92`+**scale 1,00**) n **4287** → **FAIL 4/4** (UW 278 · q* 10,2 · top-1 26,03 · win −4,43 pp · TSloss +6,18 pp · Calmar 1,400). | T1–T4 (D2) · T4 (D1 n chỉ +5,6 %) |
| 5 | `SIM_ENTRY_SAMPLE_MIN` (nhịp) | ✅ | `RESULT_R4_CADENCE` (`7f5ed6b8`): 1' = **MAX** (nhịp 15' → n 1287 = 63,5 %, Calmar 75,8 %). `RESULT_SIM_CADENCE_MATCH`: key chỉ áp **leg selector** (BD/DCA giữ 1'). | đã ở trần (1') |
| 6 | `SIM_LOSER_TIME_STOP_HOURS` (168h) | ✅ | `RESULT_EXIT_STRUCT` (`6b9e29b4`): A1 **BỎ** TS168 → n 744→**780 (+4,8 %)** mà UW 166→**318**, CAGR −8,23 pp. `PREREG_EXIT` (168/120/96/72), `PREREG_X2` đi cùng hướng. | không thêm lệnh thật; T1 (UW) |
| 7 | TP / TS-giveback / FLAT3 | ✅ | `RESULT_EXIT_HIGH_N` (`33f0b77`): 6/6 chân exit **0 TỐT/0 XẤU ngoài CI** trên nền 2 632/2 559 leg. `RESULT_EXIT_FIT` (`cb9078f`): NULL (F3 CI chứa 0). | không có lever điều chỉnh `n` |
| 8 | `DCA_GRID_*` | ✅ | `RESULT_DCA_MORELEGS_V4` (`b4548b5`): **NULL 8/8**. `RESULT_DCA_GATEWIDEN_V3` (`f95d928`): n 3015 nhưng **UW 221**. `RESULT_HOLDDCA` (`877694c`): **0/3 PASS**. `RESULT_EXIT_STRUCT` A2/A3: **KÉM A0** (dCAGR −10,18/−11,57 pp). | T1 (UW) · T3 |
| 9 | `CONC_CAP_PERCOIN_PCT` (15 %) | ✅ (chỉ 15 %) | `RESULT_CONC_CAP_HIGHN` (`a93982f`): cap **bind thật** (T100 27,23→10,83 %, chặn 44 leg) · **không rate nào XAU ngoài CI** · giá PnL ≤5,5 %. Trên KEEPLEG0 = **NO-OP** (`blocked=0`). | cap **chặn** leg ⇒ `n` ↓ nhẹ; là lever **rủi ro**, không phải lever `n` |
| 10 | universe (số coin) | ✅ (chỉ để cắt) | `RESULT_COST_LIQUIDITY` (`cd5e758`): decile **kém thanh khoản nhất LÃI NHIỀU NHẤT** (+4,93 %/lệnh) ⇒ **cắt universe làm mất 10–64 % lãi**, không cải thiện chất lượng (rho ≈ 0). Sim đã phủ ~863 mapper / live ~664 symbol. | **không có dư địa mở rộng** bằng lọc |
| 11 | nguồn sự kiện / signal thứ 2 | ⛔ **CHƯA** | OFI V3 (630 symbol) mới chỉ là **ỨNG VIÊN** (`RESULT_S1_FREE_OFI_V3_MULTISEED` PASS multi-seed, **chưa tích hợp**). | — (xem §3.2) |

**Đọc bảng:** 10/11 lever **đã chặn**. Cái duy nhất chưa đụng là **nguồn sự kiện thứ 2** — và đó cũng là
cái duy nhất **về mặt cơ học** có thể gấp đôi *sự kiện* (K_DENSITY: gap 129,24 ngày giống nhau ở mọi K ⇒
không K nào lấp được tuần gate đóng).

---

## 2. VIỆC 2 — VÙNG CHƯA THỬ + ƯỚC LƯỢNG (suy luận, ghi rõ)

| vùng chưa thử | vì sao chưa | ước lượng Δn (SUY LUẬN) | rủi ro T1–T3 |
|---|---|---|---|
| **2-D (K, size)** — K=24/32 × size ×0,67/×0,5, **GIỮ gate G2** (không `dyn_scale 1.00`) | `SIZE_COUNT`/`K_DENSITY` chạy trên nền **KEEPLEG0/T170** và **không bật rolling gate**; `D2` bật gate nhưng **mở luôn scale 1,00** ⇒ ô "K rộng + gate G2 **ĐÓNG**" **trống** | K16→24 ≈ **×1,25–1,35** → ~3 100–3 400; K16→32 ≈ **×1,55–1,65** → ~3 900–4 100. Size gần như **không đổi n** (bằng chứng #2) | **T3 (TSloss↑) gần chắc với K≥24**; **T1 (UW) với K32** (SIZE_COUNT B4 UW 277); T2 q* ↓ |
| **Rút ngắn TS 168h → 96/72h** | chỉ thử **bỏ hẳn** TS, chưa thử 96/72 | **+2…+6 %** (A1: +4,8 % khi bỏ hẳn) — vì CAPACITY_DIAG: **không kẹt slot** | thấp nếu chỉ rút; nhưng lợi ích ≈ 0 |
| **`CONC_CAP_PERCOIN` 15 % → 10/7,5 %** | mới thử 15 % (đúng/bằng nhau trên 2 nền) | **−2…−8 %** (cap **chặn leg** khi bind) | giảm conc (TỐT cho T1), PnL ≤5 % — nhưng **ngược mục tiêu `n`** |
| **gate scale × K** (1,30–1,45 × K24, gate G2 ON) | `GATESCALE_*` chạy trên nền **KEEPLEG0 K8**, không có rolling gate; `GDV2` giữ scale 1,55 | scale 1,40 ≈ **×1,13**; 1,30 ≈ **×1,25** trên nền G2 (theo sweep KEEPLEG0) | T3 (TSloss) — nhưng **đây là ô có khả năng cân bằng nhất** (đổi 2 chiều nhỏ thay vì 1 chiều lớn) |
| **Mở rộng universe** | `COST_LIQUIDITY` chỉ đo **cắt**, không đo **thêm** | **~0** (universe đã phủ gần hết symbol có dữ liệu) | — |

⚠️ **CẢNH BÁO CỨNG:** *gấp đôi `n`* và *giảm margin* là **HAI MỤC TIÊU CĂNG NHAU**. Giảm size đơn thuần
**không thêm lệnh** (#2) mà chỉ **hạ CAGR**. Muốn thêm lệnh **bắt buộc** mở gate (scale<1,55 / gate rộng hơn /
K rộng hơn / nguồn mới), và **mọi lần mở gate đã đo đều hạ chất lượng** (D2, G1, B3/B4, GDV2 W30).
⇒ Không có đường nào *vừa* ×2 *vừa* giảm margin **mà giữ chất lượng** trong các lever config hiện có.

---

## 3. VIỆC 3 — ĐỀ XUẤT

### 3.1 SÁU ARM KHOÁ TRƯỚC (1 đợt sim Kaggle · nhịp 1' · `CONC_CAP 15 %` · phí base · **CHƯA CHẠY**)

Nền chung: `profiles/g2_flat3.properties` (**giữ nguyên** `SIM_GATE_ROLLING_*` = gate G2, FLAT3, KEEPLEG0,
`SIM_ENTRY_SAMPLE_MIN=1`). Chỉ override `SELECTOR_RANK_TOPK` + `SIM_F_BASE`.

| arm | K | `SIM_F_BASE` | Δ so baseline | dự báo `n` (SUY LUẬN) | lý do qua/trượt T3 |
|---|---|---|---|---|---|
| **P1** | 16 | 0,015 | **parity anchor** (y baseline) | **2 509** (md5 `650c386f…`) | cổng DỪNG: tái lập byte-for-byte mới tin số P2–P6 |
| **P2** | 24 | 0,015 | K↑ | ~**3 100–3 400** | K vừa ⇒ TSloss nhích nhẹ; **có thể PASS T3** (K_DENSITY: +2,06 pp ở K16 *trên nền T170*; trên nền G2 biên rộng hơn) |
| **P3** | 32 | 0,015 | K↑↑ | ~**3 900–4 100** | **DỰ BÁO TRƯỢT T3/T2** (TSloss↑, q*↓; tiền lệ B4 UW 277) — arm này để **vẽ đường biên**, không phải ứng viên |
| **P4** | 24 | 0,010 | K↑ + margin ×0,67 | ~**3 100–3 400** (=P2; size ≠ lever n) | như P2, nhưng margin/conc thấp hơn ⇒ **ứng viên "giảm margin" duy nhất còn hợp lý** |
| **P5** | 32 | 0,0075 | K↑↑ + margin ×0,5 | ~**3 900–4 100** | **DỰ BÁO TRƯỢT T3/T2**; nếu T1 UW vỡ thì là bằng chứng đóng ô K=32 |
| **P6** | 16 | 0,010 | margin ×0,67 (giữ K) | ~**2 509** (±1 %) | **DỰ BÁO T3 PASS nhưng T4 TRƯỢT** (`n` không tăng) ⇒ **chứng minh ×2 không tới từ size** |

**Đọc kết quả dự kiến:** ngay cả arm tốt nhất (P2/P4) cũng chỉ ~**+30 %** `n`, **không tới ×2**.
Nếu owner muốn thử đúng ô cân bằng nhất, **thay P3/P5 bằng 2 arm `SIM_GATE_DYN_SCALE` ∈ {1,40 ; 1,30}
× K=16** (giữ gate G2) — ô này **chưa từng chạy** và có khả năng PASS T3 cao hơn K=32.

### 3.2 PRE-REG RIÊNG (chưa chạy — chờ owner duyệt)

- **Điều kiện DỪNG:** P1 phải tái lập **md5 `650c386f0d0dfea334af9d55ca2f21d4`** (n 2517) trước khi đọc P2–P6.
- **Cổng parity:** mỗi arm `diff` profile vs `g2_flat3.properties` = **đúng 1–2 dòng**; ghi `PROFILE_HASH`.
- **Luật 4 tầng §9:** `n` (mục tiêu) · `Calmar_MTM ≥ 0,90×1,877 = 1,689` · `conc ≤ 4,09 %` · T1 MTM phút ·
  T2 (`q* ≥ 15`, top-1 ≤ 25) · T3 (`win% ≥ −2,0 pp`, `TSloss% ≤ +2,5 pp`, CI block-72h, 2000 rep, seed
  **20260905**, `inflate(k)`).
- **Chi phí:** 6 chân Kaggle CPU = **0**; **0 sim Oracle**; DEV ≤ 2025-12-31; **không** chạm 2026.

### 3.3 HAI HƯỚNG CẤU TRÚC (khi lever config không đủ)

1. **OFI V3 (Binance Vision aggTrades, 630 symbol) — nguồn sự kiện THỨ 2.**
   `RESULT_S1_FREE_OFI_V3_MULTISEED` = **PASS multi-seed** (chỉ là **ứng viên**, chưa tích hợp).
   **Vì sao CHỈ cách này mới thật sự gấp đôi SỰ KIỆN:** K_DENSITY chứng minh *burstiness là thuộc tính của
   GATE, không của K* — coverage tuần **33,8 %** và **gap dài nhất 129,24 ngày giống hệt** ở K=8/12/16.
   Gate đóng ~66 % số tuần vì **S1 không có tín hiệu**, không phải vì thiếu slot. Một tín hiệu **độc lập**
   (OFI ≠ funding) mới lấp được tuần gate funding đóng ⇒ tăng **số sự kiện**, không chỉ số leg/tuần.
2. **`ENTRY_CASCADE` (`PLAN_CASCADE_ENTRY`, commit sẵn, default OFF).**
   94 % thời gian 1 lượt là predict toàn universe ⇒ cascade lọc rẻ trước. Đây **KHÔNG** phải lever `n`
   mà là lever **độ trễ**: nó mới làm nhịp 1' **khả thi trên LIVE** (hiện lượt ~228 s ⇒ lưới 1' bất khả thi).
   **Bật cascade = đổi đường LIVE ⇒ phải owner duyệt.**

### 3.4 MỤC BỎ + LÝ DO

- **Bỏ "giảm margin để tăng `n`"** làm trục nghiên cứu: bằng chứng #2 (B1 = B0, 0 lệnh thêm).
- **Bỏ "rút ngắn TS để giải phóng slot"**: CAPACITY_DIAG — **không kẹt slot** (0/1644 ngày chạm trần).
- **Bỏ "cắt universe để tăng chất lượng"**: `COST_LIQUIDITY` — decile kém thanh khoản **lãi nhất**.
- **Bỏ `(a)/(b′)`** (đã bỏ từ §9): bất khả thi toán học (Sharpe năm ≈ 8,1 / ≈ 3,6).
- **Không dùng `dyn_scale 1.00` / gate W30 / `pct 0,92`+scale1,00**: đã FAIL 4/4 tầng (D2, G1).
