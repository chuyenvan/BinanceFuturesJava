# RESULT — DOUBLE_ENTRIES: SWEEP K × size (P1–P6) trên nền `G2 + FLAT3` — "gấp đôi tập lệnh" (n ≈ 5000)?

Pre-reg: `docs/prereg/PREREG_DOUBLE_ENTRIES.md` (commit `9188b063`, chốt **TRƯỚC** khi chạy).
Nguồn: `docs/plan/SUGGEST_DOUBLE_ENTRIES.md` §3.1/§3.2 (`8c0cd751`). Luật: `docs/runbooks/RISK_APPETITE.md` §9.
Nhánh `module`. Sim **TRÊN KAGGLE** (0 sim Oracle) · bundle `sim-x1-2021-bundle`, **jar DÙNG LẠI `sim-jar-gdv2`**
(sha256 `7368be46…`, KHÔNG build/merge) · `sim_end_date=20251231` · DEV ≤ 2025-12-31 · không đọc 2026.

**Cách dựng nền `g2_flat3`:** bundle không chứa `prof_g2_flat3` ⇒ dùng `profiles/r4_kg0_k16_f015_g155.properties`
+ **6 override** `=(g2_flat3)` (3 key gate + `TS_GIVEBACK_RATIO=1.0` + 2 key `SIM_TS_MAX_GAP`) — y hệt trail2
flat3. Chỉ thêm `SELECTOR_RANK_TOPK`/`SIM_F_BASE` cho từng arm.

## 0. CỔNG PARITY — PASS

| cổng | yêu cầu | đo được | kết |
|---|---|---|---|
| **P1 = baseline** | `md5(printDone)=650c386f0d0dfea334af9d55ca2f21d4`, n 2517, eq 131 908 | **`650c386f0d0dfea334af9d55ca2f21d4`** · n **2517** · eq **131 908** · `profile_hash c47b73f3133521a1` | **PASS** (byte-identical `g2flat3-val`) |
| jar DÙNG LẠI | sha256 `7368be46…` | `7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a` | **PASS** |
| `[GATE-RATIO]` bật thật | mode `ratio` `pct=0.99995083` `days=90` | `GATE-RATIO on pct=0.99995083 days=90` | **PASS** |
| `[CONC-PC]` 15 % | `blocked=0` | `CONC-PC] SUMMARY blocked=0 pct=0.15` | **PASS** |

Kernel `chuyendinh/sim-de-p1..p6` (all COMPLETE, `symbol_mapper=863`, phí base trong artifact).

## 1. BẢNG 6 ARM — 4 TẦNG §9 (as-is, phí base 0,112 %/vòng; `k=5`, `inflate=1,79412`, seed `20260905`, block-72h)

| arm | K | F_BASE | n | Δn | equity | CAGR% | ddPhút% | UW(ngày) | q*% | top-1% | conc% | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **P1**=baseline | 16 | 0,015 | 2 517 | — | 131 908 | 34,31 | −17,68 | 87,1 | 26,4 | 14,97 | 4,09 | **1,940** | PASS | PASS | ref | ref |
| **P2** | 24 | 0,015 | 3 526 | ×1,40 | 144 974 | 37,16 | −22,21 | 117,3 | 21,6 | 16,16 | 6,48 | 1,673 | PASS | PASS | PASS | **FAIL** |
| **P3** | 32 | 0,015 | 4 092 | ×1,63 | 115 531 | 30,41 | −27,81 | **419,9** | 16,0 | 18,37 | 6,39 | 1,093 | **FAIL** | PASS | **FAIL** | FAIL |
| **P4** | 24 | 0,010 | 3 553 | ×1,41 | 111 947 | 29,49 | −19,29 | 106,9 | 24,7 | 15,66 | 4,38 | 1,529 | PASS | PASS | PASS | **FAIL** |
| **P5** | 32 | 0,0075 | 4 604 | ×1,83 | 97 721 | 25,64 | −20,41 | 164,7 | 21,6 | 18,07 | 3,28 | 1,257 | PASS | PASS | **FAIL** | FAIL |
| **P6** | 16 | 0,010 | 2 519 | ×1,00 | 100 696 | 26,48 | −14,35 | 81,7 | 30,1 | 14,96 | 3,18 | **1,845** | PASS | PASS | PASS | **PASS** |

Ngưỡng T4 áp đo được: `Calmar ≥ 0,90×1,940 = 1,746` · `conc ≤ 4,09`. (Brief nêu P1 1,900 ⇒ ngưỡng 1,710; P2 1,673
< 1,710 < 1,746 ⇒ FAIL cả hai cách; P4 1,529 FAIL; P6 1,845 PASS cả hai.)
T1-P3 FAIL vì **UW 419,9 > 250** và **có năm âm (2022)**, `qmin −17,41` (tiền lệ `SIZE_COUNT` B4 UW 277).
T3: P3 `win% −3,43` (< −2,0, `worse_sig`) · P5 `win% −2,60` (< −2,0) ⇒ FAIL; P2/P4/P6 trong trần.

## 2. TRẢ LỜI DỨT KHOÁT

**(1) Có arm nào đạt `n ≥ 2×` (≥ 5 034) không? — KHÔNG.**
Mức `n` cao nhất đạt được = **4 604 (P5, K32 F0,0075) = 1,83×** — và arm đó **vỡ T3**. Kế tiếp: P3 4 092 (1,63×),
P4 3 553 (1,41×), P2 3 526 (1,40×). Trần K×size = **1,83×, không tới 2×**.

**(2) Có arm nào QUA CẢ 4 TẦNG không? — CÓ, đúng MỘT: P6** (`K16 F0,010`; Calmar 1,845 ≥ 1,746 · conc 3,18 ≤ 4,09 ·
T1 PASS · T2 PASS · T3 PASS) — **nhưng `n 2 519 ≈ baseline (+2 lệnh)** ⇒ qua cổng mà **không tăng `n`**.
Arm `n` **cao nhất mà vẫn PASS**: nếu tính **cả 4 tầng** ⇒ **P6 (n 2 519)**; nếu tính **T1–T3** ⇒ **P2 (n 3 526)**
(P2/P4 trượt T4: Calmar 1,673 / 1,529 < 1,746; P2 thêm conc 6,48 > 4,09, P4 conc 4,38 > 4,09).

**(3) K24 vs K16/K32** (tại F0,015):

| | K16 (P1) | K24 (P2) | K32 (P3) |
|---|---|---|---|
| `n` | 2 517 | **3 526 (+40 %)** | 4 092 (+63 %) |
| `win%` (Δ) | 85,86 | 84,63 (−1,23) | 82,43 (**−3,43**) |
| `TSloss%` (Δ) | 14,30 | 16,02 (+1,72) | 18,08 (**+3,78**) |

**K24 ĐÚNG là điểm cân bằng:** lấy ~⅔ mức tăng `n` (K32) mà T3 vẫn trong trần (§9: ≥−2,0 / ≤+2,5); **K32 vỡ T3**
(win% −3,43) và ở F0,015 còn vỡ T1 (UW 419,9 · 2022 âm).

**(4) Lever CONFIG đã CẠN chưa? — CẠN cho mục tiêu ×2.** Trần 2-D (K×size) đo được **1,83×** và arm đạt trần
**vỡ T3**; arm duy nhất qua 4 tầng (P6) thêm **~0 lệnh**. Giảm size **không** phải lever `n` ở K thấp (P6 2 519 ≈
P1 2 517), chỉ **hạ CAGR** (34,31→26,48). Muốn thật sự ×2 sự kiện ⇒ **chuyển sang CẤU TRÚC: nguồn sự kiện thứ 2
(OFI V3)** như `SUGGEST §3.3` — `K_DENSITY`: coverage tuần 33,8 % và gap dài nhất 129,24 ngày **giống hệt** ở mọi K
⇒ gate đóng không phải vì thiếu slot/K.

## 3. GHI NHẬN PHỤ (chỉ báo, không đổi luật)

- **Size LÀ một lever `n` nhẹ khi K lớn** (khác SUGGEST §1 #2 đo trên KEEPLEG0/K8): cùng K32, `F 0,015→0,0075`
  đẩy `n 4 092 → 4 604 (+12,5 %)` và `conc 6,39 → 3,28`. ⇒ đòn "giảm margin" **có** thêm lệnh trong ô K rộng.
- Baseline brief (`n 2 509` · `Calmar 1,900`) là **arm G2 trước FLAT3**; mốc parity/baseline ở đây là
  `g2_flat3` đo được (`n 2 517` · `Calmar 1,940`).

## 4. MỤC BỎ + LÝ DO

- **Bỏ trục `K × size` để đạt ×2**: trần 1,83× (P5) và arm đạt trần vỡ T3; K32 vỡ T3 (và T1 ở F0,015).
- **Bỏ "giảm margin để tăng `n`"**: P6 (margin ×0,67) = **+2 lệnh**, chỉ hạ CAGR.
- **Giữ K24** như điểm cân bằng nếu owner muốn `n` +40 % (`n` 3 526) — **phải amendment T4** (Calmar −13,8 %,
  conc +58,6 %) hoặc chấp nhận hạ chuẩn; **không** dùng K32.
- Hướng còn lại: **OFI V3 (nguồn sự kiện thứ 2)** — cấu trúc, không phải config.

## 5. LƯU VẾT

- Runner: `research/analysis/double_entries_run.py` · chấm: `research/analysis/double_entries_driver.py`
  (gọi `reset_rule_score.py`) · thô: `docs/result/double_entries.json`.
- Artifact Kaggle: `~/kaggle_sim/out/de-p1..de-p6` (`printDone.csv` md5 lần lượt `650c386f`/`6802c08e`/`5e60998e`/
  `351f61c5`/`eb752ffb`/`22be5eb2`); MTM cache `/tmp/double_entries_mtm.json`.
- 0 sim Oracle · 6 kernel Kaggle CPU (0 quota) · không chạm 242/ONNX/LIVE/2026 · không push dữ liệu.
