# RESULT — VÒNG CẤU TRÚC LUẬT THOÁT: **BỎ TIME-STOP 168h + "DCA TỚI CHẾT"** (A0/A1/A2/A3)

Pre-reg: `docs/prereg/PREREG_EXIT_STRUCT.md` — **chốt TRƯỚC** khi chạy (commit `969fa7a`).
Runner: `research/analysis/exit_struct_run.py` · Scorer: `research/analysis/exit_struct_score.py`.
Số: `docs/result/RESULT_EXIT_STRUCT.json` (11 KB).
Jar: `sim-jar-cadence` sha256 `43888ebd…` (commit code `3b6c6e9`) — **TÁI DÙNG, KHÔNG sửa code, KHÔNG build lại**.
3 chân Kaggle (`xs-a1/a2/a3`) **COMPLETE · ok=true · symbol_mapper=863**, JVM 1.100–1.362 s.
Nền = **`sel15`** (DEV 2021-07-01..2025-12-31). **KHÔNG chạm 2026 / 242 / ONNX / LIVE. KHÔNG push git.**

---

## 0. VIỆC 1 — CÔNG TẮC TIME-STOP 168h (`file:line`)

- **Time-stop 168h SỐNG duy nhất** = `SIM_LOSER_TIME_STOP_HOURS` → `Configs.LOSER_TIME_STOP_HOURS`
  (**`src/main/java/com/binance/chuyennd/tradecore/Configs.java:433`**; đọc env `:831`), cài đặt tại
  **`src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:1016-1030`**
  (`startUpdateOldOrderTrading`): cụm **CHƯA arm** (`priceSL==null`) quá 168h kể từ `clusterFirstLegTime`
  ⇒ đóng `min(open, close)`. Profile nền `x1_gs_t170` khai `=168` ⇒ **TẮT = override `=0`** (đúng default).
- ⚠️ **ĐÍNH CHÍNH cảnh báo trong task:** key `TIME_STOP_HOURS` (profile nền khai `=0`) là **CƠ CHẾ ĐÃ CHẾT**
  — cơ chế trong `updateStatusNew` (grep được ở `OrderTargetInfoTest`) đã bị **XÓA** ở commit **`5f40a90`**
  (2026-09-03); chính commit đó ghi: *"HARD_SL_PCT (0), HARD_STOP_LOSS_RATE (0), TIME_STOP_HOURS (0) — chỉ còn
  LOSER_TIME_STOP_HOURS=168"*. Hiện **KHÔNG có reader** cho `TIME_STOP_HOURS` ⇒ **168h = LOSER_TIME_STOP_HOURS**.
- **"DCA tới chết"** = `DCA_GRID_ENABLED=false` (`Configs.java:186`) ⇒ DCA phản xạ `DcaUtils.shouldDca`
  (`DcaProcessor.java:46`), **không trần số leg**.
- **⇒ KHÔNG sửa code ⇒ KHÔNG cần parity lại.** (Parity "TẮT = y nguyên" đã PASS với jar này ở
  `RESULT_SIM_CADENCE_MATCH` §0: `99e42b75…`/1085/103083 và `efb793e2…`/1089/111070.)

## 1. BẢNG 4 ARM (nền `sel15`, DEV 2021-07-01..2025-12-31)

| arm | cấu hình | n | entry/tháng | eq | CAGR% | maxDD% | UW | qmin% | conc% |
|---|---|---|---|---|---|---|---|---|---|
| **A0** | grid + **TS168** (đang chạy, `cd-sel15`, tái dùng) | 744 | 13,77 | 71.718 | **+17,29** | −6,27 | 166 | −3,36 | 6,77 |
| **A1** | grid + **BỎ** TS168 | 780 | 14,44 | 51.671 | +9,05 | **−12,38** | **318** | −5,88 | 12,62 |
| **A2** | **DCA tới chết** + **BỎ** TS168 ← owner | 935 | 17,31 | 47.644 | +7,10 | −4,76 | 92 | −0,18 | 7,74 |
| **A3** | DCA phản xạ + giữ TS168 | 877 | 16,24 | 44.918 | +5,70 | −1,59 | **276** | −0,05 | 2,27 |

**Rào cũ** (`--appetite latest`: maxDD≤40 · UW≤250 · qmin≥−20 · 0 năm âm): **A0 PASS · A2 PASS ·
A1 VI PHẠM** (2022 ret≤0 + UW 304, 2023 UW 258, 2025 ret≤0, ALL UW 318) · **A3 VI PHẠM** (ALL UW 276).
CI vs A0 (block-72h, 2000 rep, seed 20260905, inflate(k=3)=1,4823): **dCAGR A1 −8,23 · A2 −10,18 · A3 −11,57 pp**
(P>0 lần lượt 0,090 / **0,001** / **0,000**) ⇒ **cả 3 biến thể ĐỀU KÉM A0** (A2/A3 âm CÓ Ý NGHĨA).

## 2. RÀO OWNER (a)/(b′) — **CẢ 4 ARM FAIL CẢ HAI**

Hai cách áp (task §3.6): **(1) USDT** trên cột `pnl` (sim đã gồm phí `RATE_FEE 0,002/chân + SLIPPAGE 0,003/chân`
≥ mức owner 0,006) và **(2) SIZE-NEUTRAL** trên `pnl/margin`.

| arm | %top-1 (a) USDT | (a) | bỏ-50% USDT | (b′) | %top-1 size-neutral | bỏ-50% size-neutral | (b′) | q*% | median/leg | tf_5 | tf_10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 19,13 | FAIL | −17.551 | FAIL | 23,01 | −6,54 | FAIL | 21,5 | 62,1 | 27,7 | 17,4 |
| A1 | **37,35** | FAIL | −21.073 | FAIL | 28,62 | **−19,32** | FAIL | **6,5** | 33,9 | 2,2 | **−5,4** |
| A2 | 16,10 | FAIL | **−4.622** | FAIL | 15,27 | **−14,87** | FAIL | 22,0 | 12,0 | 7,7 | 4,8 |
| A3 | 16,68 | FAIL | −3.541 | FAIL | 16,87 | −11,99 | FAIL | 24,0 | 11,3 | 6,6 | 4,5 |

- **(a) 0/4 PASS** (16,10–37,35 %, đều > 15 %). A2 **16,10 %** sát ngưỡng nhưng **vẫn FAIL**.
- **(b′) 0/4 PASS.** Trên USDT A2 (−4.622) "đỡ âm" hơn A0 (−17.551) — **NHƯNG đó là ẢO GIÁC DO SIZE**:
  **`DCA_GRID_ENABLED=false` đồng thời TẮT hệ số sizing `DCA_GRID_SCALE=6.0`** (nhánh `budget *= ratio`,
  `Simulator…:1408-1421`) ⇒ A2/A3 chạy **~1/6 size** (margin TB/leg: A0 1.468 vs A2 263). Ở không gian
  **size-neutral (lãi suất/leg)**, **(b′) của A2 (−14,87) và A3 (−11,99) ÂM SÂU HƠN A0 (−6,54)** ⇒ cấu trúc
  **KHÔNG tốt hơn**, chỉ là **nhỏ hơn**.

## 3. MẤT CÂN XỨNG + 5 thước chuẩn + 4 rate

| arm | **mean\|lỗ\|/mean lãi** (ret/leg) | (USDT) | sign%>0 | loss_mean | median | conc_5 | tf_5 | TSloss% | mP\|SM | mP\|SL |
|---|---|---|---|---|---|---|---|---|---|---|
| A0 | **2,43×** | **3,38×** | 88,4 | 0,1860 | 0,0420 | 0,480 | 0,0253 | 9,8 | +7,7 | −16,6 |
| A1 | **4,62×** | **6,68×** | 91,3 | 0,4460 | 0,0431 | 0,717 | 0,0147 | **0,0** | +8,5 | — |
| A2 | 1,79× | 2,05× | 84,7 | 0,1805 | 0,0445 | 0,441 | 0,0342 | **0,0** | +7,1 | — |
| A3 | 1,60× | 1,79× | 82,7 | 0,1398 | 0,0420 | 0,441 | 0,0282 | 7,4 | +7,1 | −14,1 |

- **A1 (chỉ bỏ TS168) LÀM MẤT CÂN XỨNG NẶNG HƠN: 3,38× → 6,68×** (+98 %) — zombie leg bị giữ tới end.
- **A2/A3 giảm mất cân xứng** (USDT 3,38 → 2,05 / 1,79) — **ngược kỳ vọng ghi trước**; nhưng (b′) size-neutral
  vẫn **xấu hơn A0** ⇒ mất cân xứng **trung bình** ≠ **phụ thuộc đuôi**.
- ⚠️ **Rate `TSloss%`/`mP|SL` suy biến ở A1/A2**: bỏ TS168 ⇒ **0 leg `STOP_LOSS_DONE`** (A1/A2); leg thua
  không còn bị đóng phẳng mà **giữ tới cuối kỳ rồi mark-to-market** (status `REQUEST`): A1 31 leg (−17.719),
  A2 12 leg (−1.398). Đối chiếu equity: A2 `35000+Σpnl=47.703` vs eq `47.644` (lệch 0,12 %); **A1 lệch 765 (1,5 %)**.
- **Bỏ khỏi thước:** `mP|SL` (A1/A2 không tính được) · `meanP` (đồng nhất thức đại số) · `win%` (ρ −0,99 với TSloss%).

## 4. 3 CHỈ SỐ MARTINGALE (BẮT BUỘC)

| arm | ① lỗ lớn nhất 1 vị thế/1 coin (USDT, cả kỳ) | ① theo năm (worst sym) | ② conc 1 coin > 15 %? | ③ coin "chết" hoàn toàn (Σpnl<0) |
|---|---|---|---|---|
| A0 | 2.483 (2025) | 321/450/731/913/2.483 | **6,77 % — KHÔNG** | **52/272** (−14.666) |
| A1 | **4.766** (2025) | 0/24/5/76/**4.766** | 12,62 % — KHÔNG | 15/273 (−16.930) |
| A2 | 975 (2025) | 0/37/1/0/975 | 7,74 % — KHÔNG | **4/271** (−1.255) |
| A3 | 441 (2025) | 41/80/98/168/441 | **2,27 % — KHÔNG** | 31/271 (−1.624) |

- ② **Không arm nào vượt trần conc 15 %** (max A1 12,62 %). ① chỉ **A1 tăng** (2.483 → 4.766, ×1,9).
- ③ số coin chết giảm mạnh ở A2 (4) — nhưng lại đi kèm **CAGR −10,18 pp** và (b′) **vẫn âm**: nhồi thêm
  chỉ **kéo dài vị thế**, không tạo lãi không-đuôi.

## 5. TRẢ LỜI (bắt buộc)

**(1) A2 (DCA tới chết + bỏ TS168) có PASS (a) và (b′) không?** **KHÔNG pass cả hai.**
(a) `%PnL top-1% = 16,10 %` > 15 % ⇒ **FAIL**. (b′) `bỏ-50% = −4.622 USDT` ⇒ **FAIL**; size-neutral
`−14,87` (âm **sâu hơn** A0 −6,54). `q* = 22,0 %`, `CAGR +7,10 %` (A0 +17,29), dCAGR **−10,18 pp** (P>0 0,001).

**(2) Mất cân xứng thay đổi thế nào, lỗ lớn nhất 1 coin tăng bao nhiêu?** Ở A2 mất cân xứng **GIẢM**
(3,38× → 2,05× USDT; 2,43× → 1,79× size-neutral) và lỗ lớn nhất 1 vị thế **GIẢM** (2.483 → 975, −61 %) —
**ngược kỳ vọng ghi trước** (pre-reg dự `>3,6×`). Nhưng phần "giảm" này chủ yếu do
**grid-DCA bị tắt kéo theo hệ số size ×6 bị tắt** (A2 chạy ~1/6 size). Bù lại: (b′) size-neutral **xấu hơn**,
`q*` không cải thiện, CAGR mất 10 pp ⇒ **không phải cải thiện cấu trúc**. Còn **A1 (chỉ bỏ TS168) thì
mất cân xứng TĂNG MẠNH 3,38× → 6,68×** và lỗ lớn nhất 1 vị thế 2.483 → **4.766 (×1,9)**.

**(3) A1 vs A0 (chỉ bỏ time-stop) — được/mất gì?** **MẤT nhiều, ĐƯỢC không.** n +36, nhưng
**CAGR 17,29 → 9,05 % (−8,23 pp)**; maxDD −6,27 → **−12,38**; **UW 166 → 318 (vượt trần 250)**;
qmin −3,36 → −5,88; **`q*` 21,5 % → 6,5 %** (lãi phụ thuộc đuôi NẶNG hơn nhiều); **2 năm ÂM (2022, 2025)**;
`(b′) −17.551` xấu hơn A0. ⇒ **Bỏ riêng time-stop 168h là PHÁ hoại** (đúng vai trò "cắt zombie" của nó).

**(4) Kết luận — có giữ biến thể nào?** **KHÔNG giữ biến thể nào. A0 (grid DCA + TS168, `sel15`) vẫn tốt nhất.**
Cả 4 arm **FAIL (a) lẫn (b′)** (0/4). ⇒ Đúng như đã thoả thuận: **hướng đúng là CẮT LỖ NGẮN HƠN / ĐỂ LÃI CHẠY**,
**không phải nhồi thêm** — A2/A3 (DCA tới chết) không tạo được nguồn lãi không-đuôi, chỉ giảm size/kéo dài vị thế.

## 6. HẠN CHẾ + MỤC BỎ

- **Confound size (lớn nhất):** grid OFF tắt luôn `DCA_GRID_SCALE=6,0` ⇒ A2/A3 ~1/6 size, không apples-to-apples
  với A0. Đây là lý do (b′) USDT "đỡ âm" nhưng size-neutral lại xấu hơn. **Nếu owner muốn kiểm chặt**:
  chạy thêm 1 arm "A2 với size khớp" (`F_BASE`×~6) — cần ngân sách (1 chân Kaggle ~19–23 phút, phí 0).
  - ✅ **ĐÃ CHẠY — xem `docs/result/RESULT_EXIT_STRUCT_P6.md`** (2026-09-28, `xs-a2s6`, `SIM_F_BASE=0,18`).
    Kết quả: khớp size/lệnh **0,82×** (1.490,6 → 1.225,8 USDT/leg, trong hạn 1,25×) nhưng `gross` portfolio
    **7,8×** A0 · `gross MAX` 58,85 % (≈ `U_MAX` 60 %) · `n` 935→900 (35 lệnh bị chặn).
    **`dCAGR −10,18 pp (P>0 0,001)` của A2 là ARTIFACT SIZE — RÚT LẠI**: ở size khớp `dCAGR +4,51 pp` (P>0 0,797).
    **Phán quyết FAIL GIỮ** ((b′) âm ở cả hai không gian, `q*` 22,0→18,0 %), **nhưng thêm mới: A2size
    VI PHẠM trần conc 1 coin (24,24 % > 15 %)** — A2 "tuân thủ" chỉ vì chạy 1/6 size.
- **Trần gross 70 % CHƯA áp** (như `RESULT_CAP70 §5` đã khai): cần mô hình exposure/tick, **ngoài** dữ liệu
  leg-level. Phí: sim đã tính `RATE_FEE 0,002/chân + SLIPPAGE 0,003/chân` (≥ 0,006 chuẩn owner).
- A1/A2 có leg `REQUEST` (mở tới cuối kỳ, mark-to-market) ⇒ `TSloss%`/`mP|SL` suy biến; A1 lệch eq−Σpnl 1,5 %.
- **Bỏ khỏi báo cáo quyết định:** `meanP` (đồng nhất thức) · `win%` (ρ−0,99) · `mP|SL` (suy biến A1/A2).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
