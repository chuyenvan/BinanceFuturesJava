# RESULT — P6: ARM **A2 KHỚP SIZE** (khử confound size của `RESULT_EXIT_STRUCT.md` §6)

**Ngày:** 2026-09-28 · **Nhánh:** `module` · **Pre-reg:** `docs/prereg/PREREG_EXIT_STRUCT_P6.md` (commit `f6f62a7`, chốt TRƯỚC).
**Runner:** `research/analysis/exit_struct_p6_run.py` · **Scorer:** `research/analysis/exit_struct_p6_score.py`.
**Số:** `docs/result/RESULT_EXIT_STRUCT_P6.json` (9,6 KB).
**Chân Kaggle:** `chuyendinh/sim-xs-a2s6` — **COMPLETE · ok=true · n=900 · symbol_mapper=863 · 1.108,5 s**
· jar sha256 `43888ebd…` (**TÁI DÙNG `sim-jar-cadence` — KHÔNG sửa code, KHÔNG build lại**).
Nền = `sel15` (DEV 2021-07-01..2025-12-31, `d_last=20251121`, `d_last_end=20251231`).
**KHÔNG chạm 2026 / 242 / ONNX / LIVE.** Chi phí Kaggle 0.

---

## 0. TRẢ LỜI NGẮN (4 câu bắt buộc)

1. **Key size + hệ số (đo):** key = **`SIM_F_BASE`** → `Configs.F_BASE` (`Configs.java:864` đọc / `:155` khai báo
   `0,03f`; profile `x1_gs_t170` **không khai**). Hệ số dùng: **`SIM_F_BASE = 0,18 = 0,03 × 6`**.
   **Đo được `margin TB/leg`: A0 1.490,6 (1,00×) · A2 262,5 (0,18×) · A2size 1.225,8 (0,82×)** ⇒ khớp size
   **ĐẠT trong hạn pre-reg 1,25×** (1.490,6/1.225,8 = **1,216×**) nhưng **KHÔNG khớp ở mức portfolio**:
   `gross TB` A0 1,741 % · A2 2,627 % · **A2size 13,648 % (7,8× A0)**; `gross MAX` **58,85 %** (≈ trần `U_MAX=0,60`).
2. **A2size có PASS (a)/(b′) không?** Không gian chủ (USDT): **(a) 18,36 % FAIL · (b′) −24.839 USDT FAIL**.
   Size-neutral (`pnl/margin`): **(a) 13,13 % PASS** · **(b′) −9,09 FAIL**. ⇒ **0/2 ở USDT**, chỉ (a) đổi ở size-neutral.
   **Rào cũ `--appetite latest`: A2size VI PHẠM** (`ALL:conc 24,2 % > 15 %`) — A0 và A2 **PASS**.
3. **Kết luận cũ "A2 kém A0" có giữ không?** **GIỮ phần "FAIL 2 rào", BỎ phần "kém hơn về lãi".**
   `dCAGR` A2 `−10,18 pp` (P>0 0,001) là **ARTIFACT của size** — ở size khớp, A2size `dCAGR +4,51 pp`
   (sd 5,82, ngưỡng +8,63, **P>0 0,797 ⇒ KHÔNG ý nghĩa**). Ngược lại phần **rủi ro/đuôi trở nên TỆ HƠN**, và
   **A2size phá trần conc 1 coin 15 %** — điều A2 gốc "trông có" chỉ vì chạy 1/6 size.
4. **Còn lệch size không?** Có — **còn, ở mức portfolio**: per-leg 0,82× (đạt), nhưng `gross` 7,8× A0 và
   `gross MAX` 58,85 % sát trần 60 % ⇒ **35 lệnh bị chặn** (`n` 935 → 900, −3,7 %) do `managerBudget` trả `null`
   khi `u ≥ U_MAX`. ⇒ So sánh này là **apples-to-apples ở size/lệnh**, **KHÔNG** apples-to-apples ở vốn triển khai.

---

## 1. VIỆC 1 — KEY SIZE (`file:line`) + HỆ SỐ (đo, không đoán)

- **Key:** `SIM_F_BASE` → `Configs.F_BASE` (**`src/main/java/com/binance/chuyennd/tradecore/Configs.java:864`**,
  khai báo **`:155`** `= 0,03f`; profile nền `x1_gs_t170` **KHÔNG khai** ⇒ chạy `0,03`).
- **Công thức** (`TradeUtils.managerBudget`, **`TradeUtils.java:142`**):
  `budget = equity × F_BASE × clamp(1 − U/U_MAX, 0, 1) / dcaGridTotalWeight()`.
  Nhánh grid (**`SimulatorMarketLevelTicker1MStopLoss.java:1435-1442`**) nhân thêm
  `DcaUtils.gridLegWeightRatio = w[leg] × DCA_GRID_SCALE` (**`DcaUtils.java:62`**, `FIX_B2=true` trong profile).
- Với `DCA_GRID_WEIGHTS=1,1,1,1` (ladder = 4), `DCA_GRID_SCALE=6,0`:
  A0 = `equity×F_BASE×throttle/4×6 = equity×0,045×throttle`; A2 (grid OFF) = `equity×0,0075×throttle` ⇒ **6,0×**.
  ⇒ **`SIM_F_BASE = 0,03 × 6 = 0,18`.**
- **ĐO `margin TB/leg` (không đoán): A0 1.490,6 · A2 262,5 (0,18×) · A2size 1.225,8 (0,82×).**
  Lệch còn lại **do `throttle` phi tuyến** (A2 giữ nhiều cụm đồng thời ⇒ `U` cao hơn A0 ⇒ `throttle` nhỏ hơn),
  **không phải do hằng số sai**. `1.490,6/1.225,8 = 1,216× < 1,25×` ⇒ đạt hạn pre-reg §4.1.

## 2. BẢNG 3 CỘT (nền `sel15`, DEV 2021-07-01..2025-12-31)

| arm | tag | cấu hình | n | entry/tháng | **margin TB/leg** | **gross TB%** | **gross MAX%** | CAGR% | maxDD% | UW | qmin% | conc% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A0** | `cd-sel15` | grid + TS168 (chuẩn) | 744 | 13,77 | **1.490,6** | **1,741** | **49,53** | +17,29 | −6,27 | 166 | −3,36 | 6,77 |
| **A2** | `xs-a2` | grid OFF + bỏ TS168 | 935 | 17,31 | **262,5** | **2,627** | **25,54** | +7,10 | −4,76 | 92 | −0,18 | 7,74 |
| **A2size** | `xs-a2s6` | **A2 + `SIM_F_BASE=0,18`** | 900 | 16,66 | **1.225,8** | **13,648** | **58,85** | +21,81 | −11,43 | 181 | −3,28 | **24,24** |

| arm | %top-1 (USDT) | (a) | TF50 (USDT) | (b′) | q*% | asym | sign% | TSloss% | mP\|SM | mP\|SL | mMargin |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 19,13 | **FAIL** | −17.551 | **FAIL** | 21,5 | 2,428 | 88,4 | 9,8 | +7,7 | −16,6 | 1.490,6 |
| A2 | 16,10 | **FAIL** | −4.622 | **FAIL** | 22,0 | 1,786 | 84,7 | 0,0 | +7,1 | — | 262,5 |
| A2size | 18,36 | **FAIL** | **−24.839** | **FAIL** | 18,0 | 1,717 | 88,1 | 0,0 | +8,9 | — | 1.225,8 |

**4 thước chuẩn** (`wl_ratio=asym` · `tf_5` · `loss_mean` · `conc_5`): A0 `2,428 / +0,02532 / +0,18599 / 0,480`
· A2 `1,786 / +0,03416 / +0,18047 / 0,441` · **A2size `1,717 / +0,04797 / +0,19362 / 0,403`**.

**Size-neutral (`pnl/margin`) — (a)/(b′) + q\*:**

| arm | %top-1 | (a) | bỏ-50 % | (b′) | q*% | median | tf_5 | tf_10 |
|---|---|---|---|---|---|---|---|---|
| A0 | 23,01 | FAIL | −6,54 | **FAIL** | 32,0 | 0,0420 | 0,0253 | 0,0189 |
| A2 | 15,27 | FAIL | −14,87 | **FAIL** | 25,0 | 0,0445 | 0,0342 | 0,0228 |
| A2size | **13,13** | **PASS** | −9,09 | **FAIL** | 32,5 | 0,0469 | 0,0480 | 0,0340 |

**CI vs A0** (block-72h, 2000 rep, seed `20260905`, `inflate(3)=1,4823`):
`A2 dCAGR −10,18 pp` (sd 3,35, ngưỡng +4,97, **P>0 0,001**) ·
**`A2size dCAGR +4,51 pp`** (sd 5,82, ngưỡng +8,63, **P>0 0,797 ⇒ không đạt ý nghĩa**).
Rate có CI: `TSloss% −9,81 pp [−14,29; −6,05]*` (A2size, giống A2) · `meanP +3,045 [0,144; 6,245]*` (A2size).

**3 chỉ số martingale:** thứ tự **A0 · A2 · A2size**
- ① lỗ lớn nhất 1 vị thế/1 coin: **2.483 · 975 · 3.318** USDT (đều rơi 2025; theo năm A2size 0/30/8/0/**3.318**).
- ② conc 1 coin: 6,77 % · 7,74 % · **24,24 % ⇒ VƯỢT trần 15 %** (trần của A2size: LTC 24,2 % · BEL 20,0 %).
- ③ coin "chết" hoàn toàn (Σpnl<0): 52/272 (−14.666) · 4/271 (−1.255) · 9/272 (−10.339).

**Rào cũ `--appetite latest`:** A0 **PASS** · A2 **PASS** · **A2size VI PHẠM — `ALL:conc24.2`**.
Theo năm A2size: 2021 +14,3 · 2022 +17,5 · 2023 +19,0 · 2024 +32,8 · 2025 +14,6 (**0 năm âm**), maxDD 2025 −11,43.

## 3. TRẢ LỜI (bắt buộc)

**(1) Sau khi khớp size, A2 còn tệ hơn A0 không?** **Chia hai mặt, và mặt nào cũng khác kết luận cũ.**
- **Lãi:** **KHÔNG còn tệ** — A2size CAGR **+21,81 %** vs A0 **+17,29 %**, `dCAGR +4,51 pp` **không ý nghĩa**
  (P>0 0,797). Số cũ `−10,18 pp (P>0 0,001)` **biến mất**.
- **Đuôi / rủi ro / cấu trúc:** **TỆ HƠN rõ**: (b′) USDT **−24.839** vs A0 **−17.551** (−1,41×);
  size-neutral (b′) **−9,09** vs **−6,54**; `q*` 18,0 % vs 21,5 % (phụ thuộc đuôi **nặng hơn**);
  `maxDD` **−11,43** vs −6,27 (×1,82); lỗ lớn nhất 1 vị thế **3.318** vs 2.483 (×1,34);
  **conc 1 coin 24,24 % vs 6,77 % (VƯỢT trần 15 %)**; `gross MAX` **58,85 %** vs 49,53 % (sát trần `U_MAX` 60 %).
- Mất cân xứng `asym` **1,717** vs A0 **2,428** — vẫn thấp hơn (giống A2 1,786); ở size-neutral
  `tf_5` **0,04797** > A0 **0,02532** và (a) **PASS 13,13 %** < A0 **23,01 % FAIL**.

**(2) A2 có PASS (a)/(b′) không?** **A2size: (a) USDT 18,36 % FAIL** (ngưỡng 15 %) — **gần A0 (19,13 FAIL) hơn
là "PASS"**; size-neutral **13,13 % PASS**. **(b′) −24.839 USDT FAIL** và **−9,09 size-neutral FAIL**.
⇒ **Không PASS cả hai** ở không gian chủ; (a) chỉ đổi dấu ở size-neutral. **A2 gốc (a) 16,10 / (b′) −4.622.**

**(3) Kết luận — GIỮ hay BỎ?** **GIỮ phán quyết "FAIL", BỎ lý do "kém vì cấu trúc" và SỬA con số.**
- **GIỮ:** "bỏ time-stop 168h + DCA tới chết" **không tạo được nguồn lãi không-đuôi** — (b′) **âm ở CẢ HAI
  không gian** sau khi khớp size, và **âm hơn A0**; `q*` **giảm** (18,0 % vs 22,0 % của A2) ⇒ khớp size làm
  **tăng** phụ thuộc đuôi, không giảm. ⇒ **A0 (grid + TS168) vẫn là nền tốt nhất.**
- **BỎ:** (i) *"A2 kém A0 về CAGR −10,18 pp (P>0 0,001)"* — **đó là artifact size, rút lại**;
  (ii) *"A2 giảm mất cân xứng / lỗ lớn nhất 1 vị thế giảm 61 % — tốt hơn"* — phần "tốt" đó chủ yếu là
  **nhỏ đi**: khớp size thì lỗ lớn nhất 975 → **3.318 (vượt cả A0 2.483)**;
  (iii) *"A2 tuân thủ trần conc 1 coin 15 % (7,74 %)"* — khớp size thì **24,24 %, VƯỢT trần**: tuân thủ đó là
  **ảo giác của size 1/6**. *(Đây là kết quả mới, quan trọng nhất về rủi ro.)*
- **Mục bỏ + lý do tổng quát:** mọi so sánh **USDT tuyệt đối** giữa A2/A3 và A0 là **không hợp lệ** khi chưa khớp
  size — P6 đã khớp (0,82×, trong hạn 1,25×) nên các so sánh **USDT** ở đây **hợp lệ**, còn **so sánh cấu trúc
  đuôi phải đọc ở size-neutral** vì **`gross` portfolio còn lệch 7,8×** (không khử được bằng `F_BASE`: A2 giữ
  nhiều cụm đồng thời hơn, nên trần `U_MAX=0,60` chặn **35 lệnh** khi đẩy size lên).

## 4. HẠN CHẾ

- **Còn lệch size ở mức PORTFOLIO:** `gross TB` A2size **13,648 %** vs A0 **1,741 %** (7,8×) và `gross MAX`
  **58,85 %** ≈ trần `U_MAX=0,60`. Không thể khớp cả hai cùng lúc bằng một hằng số: A2 giữ **1,58 cụm đồng thời**
  (A0 0,53). ⇒ Đã khớp **size/lệnh** (đúng định nghĩa confound §6 của `RESULT_EXIT_STRUCT`), **chưa** khớp vốn triển khai.
- **35 lệnh bị chặn** (`n` 935 → 900) khi `u ≥ U_MAX` (`managerBudget` trả `null`, `TradeUtils.java:141`) — hệ quả
  **thật** của việc đẩy size lên, không phải lỗi. Không log-đếm được (`TickDecisionLog` OFF) nên **suy từ `n`**.
- **Rate suy biến vẫn còn:** bỏ TS168 ⇒ `0` leg `STOP_LOSS_DONE` ⇒ `TSloss% = 0,0` và `mP|SL = –` (A2/A3/A2size);
  `mP|SL` **bỏ khỏi bộ thước**. `meanP` (đồng nhất thức) và `win%` (ρ −0,99 với TSloss%) **bỏ** như vòng trước.
- **Trần gross 70 % chưa áp** (như `RESULT_CAP70 §5`): cần mô hình exposure/tick, ngoài dữ liệu leg-level.
  Ở đây `gross MAX` A2size 58,85 % < 70 %, nhưng ≈ `U_MAX` 60 % nên **throttle mới là ràng buộc thật**.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
