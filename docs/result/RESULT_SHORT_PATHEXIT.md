# RESULT_SHORT_PATHEXIT — SHORT: THOÁT THEO ĐƯỜNG GIÁ (khớp nhãn) vs CẮT CỨNG

Ngày: **2026-10-01**. Pre-reg: `docs/prereg/PREREG_SHORT_PATHEXIT.md` (**`2ac65831`**, commit TRƯỚC đo).
Code: kernel-maker **`c4f6f38e`** · sim **`d095f508`** (fix entry/offset+dấu pnl **`25cc85f8`**),
grid **`4b5e510c`**. Số: `RESULT_SHORT_PATHEXIT.json` (+`RESULT_SHORT_PATHEXIT_grid.json`).
Nền: `RESULT_SHORT_LABEL2` (**`f6a5cba2`**) · `RESULT_SHORT_DEEP` (`90c9480e`).

**Tuân thủ:** 0-sim/0 Java trên Oracle · KHÔNG sửa `.java` · không chạm production/242/ONNX/LIVE ·
không push dữ liệu · DEV ≤ 2025-12-31 (không chạm 2026) · train CHỈ trên Kaggle (`sm-pathexit`).

---

## 0. KẾT LUẬN NGẮN

**`NO-GO`** theo luật §6 pre-reg. **Thoát KHỚP NHÃN (ii) ĐÃ sửa được MISMATCH** (net từ `−0,32 %`
→ `≈ −0,03 %`, tức **+0,29 %/lệnh** so với cắt cứng) **NHƯNG KHÔNG tạo ra edge**: net ≈ 0,
**CI chứa 0**, ≤2/4 năm dương, 2023 vẫn âm. **Nguyên nhân THẬT không phải "apply chưa khớp"** —
đã đo khớp (thoát theo đường giá 1m) mà net vẫn ≈0: **bản thân top-K của model không có edge
ròng sau phí+funding**; mismatch chỉ là phần nhỏ của khoản lỗ khi cắt cứng.

---

## 1. DỮ LIỆU + KIỂM CHỨNG ĐƯỜNG GIÁ (bắt buộc)

- **Pick**: 3 arm retrain trên Kaggle (`sm-pathexit`): `PA_t15_E10_S42` (33,1'), `PA_t15_E10_S7`
  (27,4'), `OLD_ndown_S42` (38,7') — 45 feature selector, 16 fold, NEST=400, **K=8/tick**,
  **1.111.944 pick/arm**. Bin giữ lại và tải về (không push dữ liệu).
- **Đường giá 1m**: Aerospike `test.kline_1m_opt` (key `YYYYMMDD-HHMM` TZ+7), **stream 1 lượt**,
  buffer trượt 72h, **không ghi đĩa** (thay `raw/<sym>.f32` đã bị dọn). DEV 2022-01..2025-12-31.
- **Kiểm chứng đường giá (đo thật, `mae = 0`):** với offset entry = **nến mở 15m + 14 phút**
  (tức `close(t)` = phút cuối nến, `close(t+72h)` = `m0+4334`), đường 1m tái tạo **khớp tuyệt đối**
  `retEnd_72h` của `.pb` (768/768 pick, `mae=0`); `maxFav_72h` khớp (vd AUCTION 0,3520 vs 0,3521).
  ⇒ **sim 1m ≡ nhãn `.pb` về giá trị**, khác biệt duy nhất là **THỨ TỰ chạm ngưỡng** (proxy `.pb`
  chỉ có cực trị + thời điểm cực trị, không đủ xác định first-hit).

---

## 2. BẢNG 3 KIỂU THOÁT (net sau phí base 0,112 % + funding pro-rata 0,585 %/72h, mean pick/tick)

**(a) `PA_t15_E10_S42`** (nhãn path-aware, thr=1,5 %, E=+10 %):

| kiểu thoát | net% | CI95 (block-72h) | ngoài 0? | 2022 | 2023 | 2024 | 2025 | winrate | giữ (h) | đuôi (max loss) |
|---|---|---|---|---|---|---|---|---|---|---|
| **(i) CẮT CỨNG +20 %** | **−0,32** | [−0,84 ; +0,22] | KHÔNG | +0,78 | −1,33 | −0,76 | +0,07 | 52,5 % | 60,9 | −20,7 % |
| **(ii) LABEL-EXIT (TP −1,5 %/SL +10 %)** | **−0,03** | [−0,08 ; +0,02] | KHÔNG | +0,09 | −0,16 | −0,02 | −0,02 | 87,6 % | 5,4 | −10,7 % |
| (iv) TRAIL 5 % | −0,09 | [−0,20 ; +0,01] | KHÔNG | +0,19 | −0,31 | −0,10 | −0,15 | 38,1 % | 11,3 | −15,5 % |
| (iii) KHÔNG stop | −0,61 | [−1,39 ; +0,19] | KHÔNG | +0,81 | −1,11 | −1,18 | −0,95 | 57,2 % | 72,0 | −1636 % |

- Cắt cứng +30/+50/+90 %: net −0,35 / −0,47 / −0,63 % (xấu dần). Arm `PA_t15_E10_S7` gần như trùng
  (CUT −0,29 · LABEL −0,03 · TRAIL −0,08 · NOSTOP −0,57).
- **`OLD_ndown_S42`** (nhãn cũ): CUT −0,14 · **LABEL −0,00** · TRAIL −0,01 · NOSTOP −0,25.
  ⇒ **Thoát khớp nhãn cải thiện ~+0,29 %/lệnh (PA)** và **+0,14 % (OLD)** so với cắt cứng, nhưng
  chỉ đưa net **về ≈ 0**, KHÔNG dương, CI chứa 0 ở mọi cấu hình.

**Cơ chế**: TP −1,5 % chạm rất nhanh (giữ 5,4 h, winrate 87,6 %) nhưng **11,6 % lệnh dính SL −10 %**
⇒ `0,876×(+1,5 %) + 0,116×(−10 %) ≈ +0,16 %` gross, bị phí + funding ăn hết → net ≈ 0.

---

## 3. SO VỚI `RESULT_SHORT_LABEL2` (nhãn path-aware, đo bằng CẮT CỨNG)

| | LABEL2 (cắt cứng @+30, chưa funding) | PATHEXIT (đo lại, cùng pick, đúng cơ chế) |
|---|---|---|
| net | +0,17 % (CI chứa 0) | CUT −0,32 % · **LABEL −0,03 %** (đã trừ funding pro-rata) |
| cut/stop | cut-rate @+30 = 14,9 % | SL-rate (E=10 %) = 11,6 % |
| 2023 / 2024 | −0,89 / −0,32 (đã funding) | −0,16 / −0,02 (LABEL, đã funding) |

⇒ Đo đúng cơ chế làm **2024 gần hết âm** (đúng như owner nghi "apply chưa khớp"), nhưng
**2023 vẫn âm** và **net vẫn ≤ 0** ⇒ **không thành GO**.

---

## 4. QUÉT h/thr/E — "LOGIC CŨ CÓ OVERFIT KHÔNG?"

- **Proxy `.pb`** (dùng cực trị + heuristic thứ tự `tHitAdv<tHitFav`): 81 tổ hợp × 3 arm,
  **28 tổ hợp net>0, 24 tổ hợp "đạt GO"** — tập trung ở `thr=7 %` + `E=+3 %/+5 %`.
  **NHƯNG đây là ARTIFACT**: ở `thr=7 %,E=+3 %`, **46,8 % pick chạm CẢ HAI** ngưỡng ⇒ dấu net do
  **giả định thứ tự** quyết định (cons −1,1 % ↔ opt +3,6 %). Proxy không đo được first-hit.
- **Lưới CHÍNH XÁC trên đường 1m** (first-hit thật, thay proxy) — `RESULT_SHORT_PATHEXIT_grid.json`,
  arm `PA_t15_E10_S42`, 27 tổ hợp `(h{12,24,72}h × thr{1,5;3;7}% × E{3;5;10}%)`:
  **chỉ 4/27 tổ hợp net > 0, TẤT CẢ ≈ 0** (cao nhất `72h_t70_E10` = **+0,09 %**, CI chứa 0);
  **0/27 tổ hợp đạt GO** (không cái nào net>0 **ngoài CI** — 0/27; tốt nhất chỉ 3/4 năm dương nhưng
  CI chứa 0). Đặc biệt `72h_t70_E3`: proxy nói **+2,0 %**, đường 1m thật chỉ **+0,01 %** ⇒ chênh ~200×.
  ⇒ **Không có "vùng" tổ hợp dương**: mọi (h,thr,E) đều ≤0 hoặc ≈0. Kết quả "24 tổ hợp GO" của
  proxy là **giả** ⇒ tin proxy sẽ **overfit đúng vào 1 artifact xếp hạng**, không phải edge thật.

---

## 5. FUNDING

Theo `RESULT_SHORT_DEEP`: short **TRẢ** funding `−0,585 %/72h`. Trừ **pro-rata theo thời gian giữ**
(đúng hơn flat vì LABEL thoát sớm ~5,4 h ⇒ funding ~−0,04 %). Sau funding: CUT −0,32 %,
LABEL −0,03 %, TRAIL −0,09 % (PA_S42). Funding **không đổi dấu** kết luận.

---

## 6. TRẢ LỜI 4 CÂU

1. **Thoát khớp nhãn có làm net DƯƠNG không (so cắt cứng cũ)?** **KHÔNG.** Có **cải thiện rõ**
   (`−0,32 % → −0,03 %`, **+0,29 %/lệnh**; 2024 từ −0,76 % → −0,02 %) nhưng **vẫn ≤0**, **CI chứa 0**.
2. **2023/2024 còn âm không?** **2024 gần hết âm** (−0,02 %, ≈0); **2023 vẫn âm** (−0,16 %).
3. **Logic cũ có overfit không?** **Có — và proxy ` .pb` sẽ khiến overfit vào artifact.** Proxy
   cho "24/81 tổ hợp GO" (tập trung `thr=7 %`), nhưng **lưới 1m chính xác: 0/27 tổ hợp GO**
   (4/27 net>0 nhưng đều ≈0 & CI chứa 0). "Vùng đẹp" của proxy là **artifact thứ tự first-hit**
   (nhóm 23–47 % pick "chạm cả hai"), không phải edge thật.
4. **Kết luận dứt khoát:** **`NO-GO`** — **KHÔNG** dựng đường SELL. **Nguyên nhân THẬT:** (a) lỗ chính
   là **cấu trúc** — 11,6 % lệnh ăn stop −10 % đủ để triệt tiêu lãi TP nhỏ (base rate của top-K
   không đủ tốt); (b) **funding short là chi phí cấu trúc**; (c) **2023 (regime up) âm**. Mismatch
   cơ chế thoát **chỉ là phần nhỏ** — sửa xong net vẫn ≈0 ⇒ vấn đề nằm ở **CHẤT LƯỢNG PICK/REGIME**,
   không phải ở cách đo.

---

## 7. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Horizon 48h | ⛔ BỎ | `.pb` chỉ có 4/12/24/72h (không nội suy) |
| 2 | Gate-33/S1-9, Java/sim, ONNX, sửa `.java`, push dữ liệu | ⛔ BỎ | §1 pre-reg |
| 3 | Sweep bằng proxy `.pb` làm SỐ CHÍNH | ⛔ BỎ | chứng minh là artifact (§4); dùng lưới 1m |
| 4 | Dựng đường SELL / production | ⛔ BỎ | verdict NO-GO |
