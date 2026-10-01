# RESULT_BD_CHAIN — đổi `rateDown15MAvg` theo tỷ lệ universe `f` (G2 + FLAT3)

Chạy 2026-10-01, nhánh `module`. Pre-reg: `docs/prereg/PREREG_BD_CHAIN.md` (chốt **TRƯỚC** khi đo).
Nền: `profiles/g2_flat3.properties` (`G2 + FLAT3`, md5 `c6d4ef57…`; parity `printDone.csv` md5 `650c386f…`).

---

## 0. KẾT QUẢ CHỐT (đọc trước)

> ### ⛔ **DỪNG ở VIỆC 2 vì KAGGLE BẬN.** Không chạy được train/pred/sim ⇒ **KHÔNG có số cho bất kỳ `f` nào**.
> Bằng chứng: `kaggle kernels status chuyendinh/sm-pathexit` = **`running`** (job KHÁC, commit `c4f6f38e`
> SHORT_PATHEXIT, lastRunTime 2026-10-01 05:48). Theo ràng buộc CỨNG #1 ("Kaggle bận ⇒ DỪNG + báo RÕ"),
> toàn bộ VIỆC 2 (parity f=0 + 4 arm) và VIỆC 3 (chấm) **KHÔNG thực hiện**. Không có kết luận GO/NO-GO
> dựa trên số — **giữ nguyên `f=0` (N=100)**.

**VIỆC 0 (hoàn tất) + VIỆC 1 (hoàn tất): xem §1 và §2.**

---

## 1. VIỆC 0 — `rateDown15MAvg` là INPUT MODEL hay RULE? (hoàn tất, có bằng chứng)

**KẾT LUẬN: LÀ INPUT MODEL (và đồng thời là rule) — nằm trong cả GATE(33) lẫn SELECTOR(45).**

| # | khẳng định | file:line |
|---|---|---|
| 1 | **GATE (33 V3FULL)**: feature #3 = `f.momentum15M` nằm trong vector 33 | `ai_ml/onnx/entry/OnnxInferenceManager.java:67` |
| 2 | nguồn: `features.momentum15M = rate.rateDown15MAvg` | `ai_ml/features/export/entry/ComprehensiveMarketFeatureExtractor.java:94` |
| 3 | **SELECTOR (45)**: feature index 5 = `f.rateDown15MAvg` | `ai_ml/onnx/funding/SelectorOnnxInferenceManager.java:62` |
| 4 | nguồn: `f.rateDown15MAvg = rate.rateDown15MAvg` | `ai_ml/features/export/funding/FundingDataCollectionManager.java:285-286` |
| 5 | rule song song (BIG_DOWN/DCA) | `tradecore/MarketBigChangeDetector.java:169-178` (call-site `:86-88`) |
| 6 | rule size-adapt | `tradecore/BdSizeAdapt.java:86-89` |
| 7 | rule weak-block DROP15M | `tradecore/TickWeakBlock.java:135` |

⇒ **Đổi định nghĩa ⇒ PHẢI retrain + pred lại cả dây chuyền**, KHÔNG được "chỉ sim".

---

## 2. VIỆC 1 — CODE (đã thêm, GATED, default byte-identical)

- Key mới **`SIM_BD_FRACTION`** (default `0`). Không khai / `<= 0` ⇒ `BD_FRACTION = 0f` ⇒ **không chạm `period`**
  ⇒ byte-identical với `N=100` cũ.
- `Configs.BD_FRACTION` (+ đọc key trong static-block override) — `Configs.java`.
- `MarketBigChangeDetector.calRateChangeAvg`: `BD_FRACTION > 0` ⇒ `N = clamp(round(f×size),1,size)`; cap `4/5` cũ giữ nguyên.
- **KHÔNG chạm 242 / ONNX / LIVE.** `git add` chỉ 4 file của bài này.

---

## 3. BẢNG `f` × chỉ số — **KHÔNG CÓ SỐ (BLOCKED)**

| `f` | parity md5 | ON-rate BD/DCA | n | T3 (win%/TSloss%) | UW | maxDD | q* | conc | Calmar | 4 tầng |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 (parity) | **NOT-RUN** | — | — | — | — | — | — | — | — | — |
| 0.10 | NOT-RUN | — | — | — | — | — | — | — | — | — |
| 0.30 | NOT-RUN | — | — | — | — | — | — | — | — | — |
| 0.50 | NOT-RUN | — | — | — | — | — | — | — | — | — |
| 1.00 | NOT-RUN | — | — | — | — | — | — | — | — | — |

- **f=0 parity:** chưa chạy (Kaggle bận) ⇒ chưa xác nhận md5 `650c386f…`.
- **f nào qua 4 tầng:** chưa đo được (không có arm nào chạy).
- **Trôi theo năm (ON-rate 2023 vs 2025):** chưa đo trong bài này (chỉ có bằng chứng cũ 0-sim ở `RESULT_BD_DEEP §3.4`).

---

## 4. TRẢ LỜI 5 CÂU (theo thực tế đã làm)

1. **`rateDown15MAvg` là input model hay rule?** → **INPUT MODEL** (GATE 33 idx2=`momentum15M`; SELECTOR 45 idx5)
   **và** rule (BIG_DOWN/DCA/size-adapt/weak-block). File:line ở §1.
2. **Mỗi `f` (ON-rate/n/T3/UW/maxDD/q*/conc/Calmar) so G2?** → **KHÔNG CÓ SỐ** — dừng ở VIỆC 2 vì Kaggle bận.
3. **Có `f` nào qua 4 tầng?** → **Chưa đo được** (không arm nào chạy).
4. **Trôi theo năm hết chưa?** → **Chưa đo được trong bài này.**
5. **Kết luận dứt khoát:** → **NO-GO (tạm thời, do BLOCKED) — giữ `f=0` (N=100)**. KHÔNG phải kết luận khoa học
   "biến thể kém"; đây là **chưa đo được vì hạ tầng bận**. Muốn có kết luận, chạy lại VIỆC 2/3 khi Kaggle rảnh.

---

## 5. MỤC BỎ + LÝ DO

- **Bỏ:** VIỆC 2 (parity + 4 arm Kaggle) và VIỆC 3 (chấm 4 tầng + theo năm + CI).
- **Lý do:** ràng buộc CỨNG #1 — `chuyendinh/sm-pathexit` đang **`running`** (job khác). Không giành slot.
- **KHÔNG bỏ:** VIỆC 0 (kết luận input-vs-rule), VIỆC 1 (pre-reg + code gated), commit+push.
