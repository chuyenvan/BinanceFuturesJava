# PREREG_DOUBLE_ENTRIES — SWEEP K × size (P1–P6) trên nền `G2 + FLAT3`: "gấp đôi tập lệnh" (n ≈ 5000) có đạt?

**Chốt TRƯỚC khi có số.** Ngày: **2026-09-30** (TASK DoubleEntries). Nhánh `module`, HEAD `8c0cd751`.
Nguồn: `docs/plan/SUGGEST_DOUBLE_ENTRIES.md` §3.1/§3.2 (commit `8c0cd751`). Luật: `docs/runbooks/RISK_APPETITE.md` §9.

> **KHÔNG thêm/bớt arm, KHÔNG đổi dự báo `n` sau khi thấy số** (đúng §6 SUGGEST). Nếu kết quả lệch dự báo ⇒
> chỉ báo lệch, KHÔNG đổi luật.

---

## 0. MỤC ĐÍCH (1 câu)

Trên nền `G2 + FLAT3` (**giữ nguyên** rolling gate G2, FLAT3, KEEPLEG0, nhịp 1', `CONC_CAP 15 %`, phí base),
đo **6 arm khoá trước** chỉ đổi **`SELECTOR_RANK_TOPK` (K)** × **`SIM_F_BASE` (size)** để trả lời dứt khoát:
(1) có arm nào đạt `n ≥ 2× baseline (~5000)` không; (2) có arm nào qua **cả 4 tầng §9** không; (3) K24 vs
K16/K32; (4) lever CONFIG đã cạn chưa.

## 1. NỀN CHUNG + RÀNG BUỘC CỨNG

- Nền: `profiles/g2_flat3.properties` (= `r4_kg0_k16_f015_g155` + GDV2 rolling gate **ratio W90** `PCT 0.999950829`
  + FLAT3 exit `TS_GIVEBACK_RATIO=1.0`/`SIM_TS_MAX_GAP=0.03`/`WEAK=0.03`; KEEPLEG0, nhịp `SIM_ENTRY_SAMPLE_MIN=1`,
  `CONC_CAP_PERCOIN_PCT=0.15`, phí base `SIM_RATE_FEE=0.000982` + `SIM_SLIPPAGE_RATE=0.000067` ⇒ **0,112 %/vòng**).
  **KHÔNG mở gate** (`SIM_GATE_DYN_SCALE`/`PCT`/window giữ y G2).
- Sim chạy **TRÊN KAGGLE** (0 sim Oracle). Bundle `sim-x1-2021-bundle`, **jar DÙNG LẠI `sim-jar-gdv2`**
  (sha256 `7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a`) — **KHÔNG build lại, KHÔNG merge**.
  `sim_end_date=20251231`. Kaggle không chạy được ⇒ **DỪNG + báo RÕ**.
- **DEV ≤ 2025-12-31** (không đọc/không dùng 2026). **KHÔNG** chạm production/242/ONNX/LIVE. **KHÔNG push file dữ liệu**.

## 2. SÁU ARM KHOÁ TRƯỚC (đúng §3.1 SUGGEST — KHÔNG thêm/bớt)

Chỉ override **2 key** trên nền `g2_flat3`: `SELECTOR_RANK_TOPK` + `SIM_F_BASE`.

| arm | K | `SIM_F_BASE` | Δ so baseline | dự báo `n` (SUY LUẬN §3.1 SUGGEST) |
|---|---|---|---|---|
| **P1** | 16 | 0,015 | parity anchor (y baseline, 0 override) | **2 517** (md5 `650c386f…`) |
| **P2** | 24 | 0,015 | K↑ | ~3 100–3 400 |
| **P3** | 32 | 0,015 | K↑↑ | ~3 900–4 100 |
| **P4** | 24 | 0,010 | K↑ + margin ×0,67 | ~3 100–3 400 (=P2) |
| **P5** | 32 | 0,0075 | K↑↑ + margin ×0,5 | ~3 900–4 100 |
| **P6** | 16 | 0,010 | margin ×0,67 (giữ K) | ~2 517 (±1 %) |

Tag Kaggle: `de-p1` … `de-p6` (kernel `chuyendinh/sim-de-p<N>`).

## 3. CỔNG PARITY (buộc — chạy TRƯỚC khi đọc số arm khác)

- **P1 = baseline G2** phải khớp **`md5(printDone.csv) = 650c386f0d0dfea334af9d55ca2f21d4`** (n **2 517**,
  eq **131 908**; = artifact `g2flat3-val`/`trail2-g2-flat3`). **Lệch ⇒ DỪNG**, báo parity FAIL, không chấm tiếp.
- `[GATE-RATIO]` bật **thật** trong `sim.out` (mode `ratio`, `pct=0.999950829`, `days=90`).
- `[CONC-PC] SUMMARY blocked=0` (cap 15 % = NO-OP trên KEEPLEG0 như đã biết).
- Ghi `PROFILE_HASH`/`jar_sha256` từng arm (parity dùng md5 `printDone.csv`, KHÔNG dùng `PROFILE_HASH` — xem `KAGGLE_SIM.md` §0.3).

## 4. CHẤM 4 TẦNG §9 (as-is — phí base đã nằm trong artifact)

Công cụ: `research/analysis/double_entries_driver.py` (gọi thẳng `research/analysis/reset_rule_score.py`:
`load_legs`/`load_daily`/`core_metrics`/`ci_pair`/`run_mtm` — **KHÔNG viết lại thuật toán**).
Chấm **as-is** (KHÔNG hiệu chỉnh lại phí — artifact đã chạy phí base 0,112 %).

| tầng | ngưỡng |
|---|---|
| **T1** RÀO RỦI RO (MTM phút) | maxDD **MTM phút**/năm ≤ 40 % · `UW ≤ 250` ngày · quý xấu nhất ≥ −20 % · **0 năm âm** · conc 1 coin ≤ 15 % |
| **T2** ĐỘ BỀN | `q* ≥ 15 %` · `%PnL top-1% lệnh ≤ 25 %` |
| **T3** NON-INFERIORITY vs **P1** | `win% ≥ −2,0 pp` · `TSloss% ≤ +2,5 pp` (**CI block-72h**, **2000 rep**, seed **`20260905`**, **`inflate(k)`**) |
| **T4** MỤC TIÊU | `n` **MỤC TIÊU CHÍNH** · `Calmar_MTM ≥ 0,90 × baseline P1` · `conc ≤ baseline P1` |

- **`k` = 5** (số arm ĐỐI CHIẾU vs baseline, P2…P6 — đồng quy ước `PREREG_GDV2_EVEN` `k=2` cho 2 ứng viên)
  ⇒ **`inflate(k=5) = sqrt(2·ln 5) = 1,79407`**.
- `Calmar_MTM = CAGR / |maxDD MTM-phút toàn kỳ|`. Baseline P1 (đo được) là mốc; tham chiếu brief §T4
  `0,90×1,900 = 1,710` (brief nêu P1 Calmar 1,900; bản `g2_flat3`/FLAT3 kỳ vọng ~1,940 — **lấy số ĐO của P1**).
- So sánh `n`: `2× baseline` ⇒ mốc xấp xỉ **5 034** (nếu P1 = 2 517); nêu rõ mức `n` cao nhất đạt được.

## 5. CÂU HỎI PHẢI TRẢ LỜI DỨT KHOÁT

1. Có arm nào đạt `n ≥ 2× G2 (~5000)` không? Không ⇒ nêu RO mức `n` cao nhất đạt được.
2. Có arm nào qua **cả 4 tầng** không? Arm `n` cao nhất mà vẫn PASS?
3. K24 vs K16/K32: `n` và T3 (`win%`/`TSloss%`) thay đổi bao nhiêu — K24 có phải điểm cân bằng?
4. Lever CONFIG đã CẠN chưa (còn dư địa tăng `n`, hay phải sang CẤU TRÚC / OFI V3)?

## 6. OUTPUT

`docs/prereg/PREREG_DOUBLE_ENTRIES.md` (này) + `docs/result/RESULT_DOUBLE_ENTRIES.md` (+ `docs/result/double_entries.json`). Commit + push.
