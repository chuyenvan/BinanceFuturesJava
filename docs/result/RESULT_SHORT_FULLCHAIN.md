# RESULT_SHORT_FULLCHAIN — SHORT: GHÉP 3 TẦNG THEO BƯỚC (S1 selector → GATE → SIM 1m)

Ngày: **2026-10-01**, branch `module`, repo `/home/ubuntu/src/BinanceFuturesJava`.
Pre-reg: `docs/prereg/PREREG_SHORT_FULLCHAIN.md` (**`9ac83699`**, commit **TRƯỚC** đo).
Code: bước 1 **`f4d3cc55`** · bước 2 **`1b4b96c1`** · bước 3 sim **`ffb7703f`**.
Số: `docs/result/RESULT_SHORT_FULLCHAIN.json`. Nền: `RESULT_SHORT_FEASIBILITY` (`9c570e6f`) ·
`RESULT_SHORT_PATHEXIT` (`c4d56074`) · `RESULT_SHORT_PATHEXIT_PSOFT` (`05169026`).

**Tuân thủ:** KHÔNG Java/engine-sim/ONNX/242/LIVE trên Oracle; **KHÔNG sửa `.java`**;
không push dữ liệu; DEV ≤ 2025-12-31 (không chạm 2026); **train CHỈ trên Kaggle** — vòng này
**0 kernel** vì tái dùng selector S1 đã có (`pred_s1a2x1.parquet`); phần đường giá = Python offline
stream Aerospike `kline_1m_opt` (1 lượt, buffer trượt 72h, **không ghi đĩa**); chỉ `git add` file của mình.

---

## 0. KẾT LUẬN NGẮN

**`NO-GO`** theo luật §4.6 pre-reg. Ghép đủ 3 tầng rồi **vẫn âm**: **0/72 tổ hợp** (18 cấu hình thoát
× 4 nhánh gate) đạt net > 0. **Gate KHÔNG cứu được short** — đúng **2 hướng owner chỉ định** (CHẶN /
THUẬN) đều **làm XẤU**; chỉ hướng **NGHỊCH** (vào khi risk CAO) kéo net **về sát 0** (tốt nhất
`−0,042 %`, CI **chứa 0**, chỉ 1/4 năm dương) nhưng **vẫn ≤ 0** và **bị nhiễu do `predRisk4H`
không leak-free**. **2023 vẫn âm** ở mọi nhánh. **Không có "vùng đẹp"** (0 tổ hợp dương).

---

## 1. BƯỚC 1 — SELECTOR S1 (`f4d3cc55`, 0-sim)

Ứng viên SHORT = **decile 0 của `s1 = −score`** (= `score` CAO nhất ≈ 10 % "tệ nhất" theo S1).
`Spearman(s1, ret_h)` cross-section, CI block-72h (2000 rep, seed 20260905, ×1,21):

| h | IC(s1,ret) | CI95 | ngoài 0? | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|
| 1h | **−0,0247** | [−0,0264; −0,0229] | CÓ | −0,0240 | −0,0215 | −0,0265 | −0,0267 |
| 4h | **−0,0407** | [−0,0440; −0,0370] | CÓ | −0,0405 | −0,0347 | −0,0394 | −0,0481 |
| 24h | **−0,0693** | [−0,0770; −0,0613] | CÓ | −0,0691 | −0,0608 | −0,0648 | −0,0828 |

⇒ **Selector xếp hạng ĐÚNG CHIỀU và BỀN**: IC < 0 **mọi năm 2022–2025**, **ngoài CI** ở cả 3 horizon,
|IC| tăng theo horizon (quán tính). **NHƯNG biên của decile-0 quá nhỏ so chi phí**:
`d0 ret24 = −0,033 %` (dấu mean theo năm **lật: 2/4 âm** — 2022 −0,30 %, 2023 **+0,26 %**,
2024 +0,08 %, 2025 −0,18 %) ≪ ngưỡng cost `0,2098 %`; mốc **K=8** cũng chỉ `−0,070 %`.
⇒ "Selector OK" **về RANK**, **KHÔNG OK về BIÊN** so cost. (Khớp `RESULT_SHORT_FEASIBILITY` §3.)

## 2. BƯỚC 2 — GHÉP GATE `predRisk4H` (`1b4b96c1`, 0-sim)

Gate = `predRisk4H` (market-level/phút, `p15_dev.csv`), ngưỡng `q10 = −0,02386`, `q90 = −0,01056`.
`risk CAO ⇔ predRisk4H thấp` (âm hơn). n(decile 0) = **944 428**.

| nhánh | n | giữ | `mean ret24` (d0) | theo năm (ret24) |
|---|---|---|---|---|
| **A** không gate | 944 428 | 100 % | **−0,041 %** | 2022 −0,30 · 2023 **+0,26** · 2024 +0,09 · 2025 −0,17 (%) |
| **B** gate **CHẶN** (bỏ `g ≤ q10`) | 857 582 | 90,8 % | **+0,017 %** | −0,18 · +0,31 · +0,13 · −0,13 (%) |
| **C** gate **THUẬN** (giữ `g ≥ q90`) | 92 714 | 9,8 % | **+0,461 %** | +0,19 · +0,72 · +0,38 · +0,15 (%) |
| **D** gate **NGHỊCH** (giữ `g ≤ q10`) | 86 846 | 9,2 % | **−0,616 %** | −1,48 · −1,31 · −0,38 · −0,46 (%) |

**Đọc:** (a) **CHẶN** và (b) **THUẬN** — đúng 2 hướng owner chỉ định — **đều SAI hướng cho short**:
CHẶN làm ret24 từ −0,041 % → +0,017 % (bớt cơ hội giảm), THUẬN giữ đúng nhóm **tăng** (+0,46 %).
Chỉ **NGHỊCH** (vào khi risk CAO) cho ret24 **−0,616 %, âm CẢ 4 NĂM** ⇒ gate chỉ giúp short theo
hướng **ngược** với công dụng long-gate. ⚠️ **Caveat (giữ nguyên):** `predRisk4H` lấy từ **set CŨ**,
`RESULT_PREDBIN_REPRO` ghi **KHÔNG leak-free** (train tới ~2025-12) ⇒ vùng < 2025-12 **in-sample lạc
quan** ⇒ D **không đủ tin để tin live**.

## 3. BƯỚC 3 — SIM 1m (first-hit THẬT) + TRAILING + SL CỨNG (`ffb7703f`)

Pick = decile 0 S1, **n = 654 326** (2022 40 473 · 2023 9 236 · 2024 62 924 · 2025 541 693).
Entry = close nến 1m tại `m0+14` (offset đã kiểm `mae=0` khớp `.pb`); path nến `m0+15..m0+14+TS`;
exit **ưu tiên SL** khi cùng nến. Phi base 0,112 %; funding pro-rata `−0,585 %·(h/72)`.

**Lưới 18 cấu hình × 4 nhánh (net %/lệnh; CI95 block-72h; `ypos` = số năm net>0):**

| nhánh | net (min..max trên 18 ô) | ô ngoài CI `out_both` | ô net>0 | năm dương tốt nhất |
|---|---|---|---|---|
| **A** không gate | **−0,24 % … −0,37 %** | 9/18 | **0/18** | 0/4 |
| **B** CHẶN q10 | −0,34 % … −0,46 % | 9/18 | **0/18** | 0/4 |
| **C** THUẬN q90 | −0,59 % … −1,17 % | 12/18 | **0/18** | 0/4 |
| **D** NGHỊCH q10 (exploratory) | **−0,04 % … −0,23 %** | **0/18** | **0/18** | **1/4** (2022) |

Ô tốt nhất mỗi nhánh (%, net / CI95 / winrate / giữ / theo năm):

| nhánh (ô) | net | CI95 | win | giữ | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| A `T3_SL20_TS72h` | −0,237 | [−0,406; −0,052] | 34,7 % | 14,7 h | −0,19 | −0,81 | −0,29 | −0,22 |
| B `T3_SL10_TS72h` | −0,337 | [−0,552; −0,095] | 33,7 % | 17,2 h | −0,74 | −1,01 | −0,52 | −0,22 |
| C `T3_SL10_TS72h` | −0,591 | [−1,016; −0,105] | 31,6 % | 19,6 h | −1,12 | −0,96 | −1,06 | −0,02 |
| **D `T3_SL20_TS24h`** | **−0,042** | **[−0,228; +0,132]** | 37,9 % | 6,8 h | **+0,15** | **−0,30** | **−0,02** | **−0,20** |

- **TRAILING/SL gần như KHÔNG đổi kết quả** theo SL (10/15/20 %) — vì trailing chạm rất sớm; T lớn
  (8 %) thì **xấu hơn** (giữ lâu ⇒ trả funding & dính đuôi tăng). Time-stop 24h vs 72h chênh nhỏ.
- **Kiểm chứng kênh:** A `T3_SL20_TS24h` net `−0,243 %` → **gross trước phí/funding ≈ −0,043 %**
  (cộng lại 0,112 % fee + 0,089 % funding) ≈ đúng `d0 ret24 = −0,041 %` của bước 2 ⇒ sim 1m **khớp**
  kênh 0-sim. (Parser/offset **copy nguyên** sim đã kiểm `mae=0` — `RESULT_SHORT_PATHEXIT` §1.)
- **§9** (`RISK_APPETITE.md` §9): **T1 FAIL** — điều kiện cứng "**0 năm âm**" bị vi phạm (net < 0 ở
  mọi cấu hình, không nhánh nào ≥3/4 năm dương). **T2/T3/T4 = N/A**: cần artifact **equity/MTM phút**
  (maxDD/UW/quý/Calmar/conc) mà **nghiên cứu per-trade short lẻ không dựng được**; ghi rõ, không bịa.

## 4. TRẢ LỜI 4 CÂU (bắt buộc)

1. **Gate có làm short > 0 & ngoài CI không?** — **KHÔNG.** 0/72 tổ hợp net>0. Đúng 2 hướng chỉ định
   (**CHẶN/THUẬN**) **làm xấu**; hướng **NGHỊCH** kéo net về sát 0 (`−0,042 %`) nhưng **CI chứa 0**
   (`[−0,228; +0,132]`) và chỉ 1/4 năm dương ⇒ **không ngoài CI**.
2. **2023 còn âm không?** — **CÒN.** 2023 âm ở **mọi** nhánh (A −0,81 %, B −1,01 %, C −0,96 %,
   D −0,30 % ở ô tốt nhất) ⇒ đúng "hard year" như các vòng trước.
3. **Có > 1 "vùng đẹp" (overfit) không?** — **KHÔNG có vùng đẹp nào** (0 tổ hợp dương) ⇒ vấn đề
   **không phải overfit cục bộ** mà là **thiếu edge ròng** một cách hệ thống. (Ngược lại: nếu có 1 ô
   dương lẻ thì mới lo overfit.)
4. **Nguyên nhân THẬT (NO-GO):** (i) **biên gross của decile-0 S1 quá nhỏ** (≈ −0,04 %/lệnh, đúng
   bằng bước 2) ≪ **cost 0,112 % + funding**; (ii) **gate long-purpose không áp được cho short** —
   chỉ hướng NGHỊCH mới "thuận", nhưng nguồn `predRisk4H` **không leak-free** nên số NGHỊCH **lạc quan**;
   (iii) **thoát TRAILING/SL không tạo edge mới**, chỉ co giãn nhỏ. Không phải "apply chưa khớp".

## 5. GO/NO-GO

**`NO-GO`** (0/72 cấu hình đạt A&B; §9-T1 FAIL). Không đủ cơ sở dựng đường SELL.

## 6. VIỆC BỎ + LÝ DO

| # | việc | lý do |
|---|---|---|
| 1 | Train kernel Kaggle mới | tái dùng S1 panel đã có ⇒ **0 kernel**; không cần GPU/không chờ slot |
| 2 | Horizon 48h | ngoài lưới khoá §4.3 (24/72h) |
| 3 | Java engine-sim / ONNX / 242 / LIVE | ràng buộc cứng §1.2 |
| 4 | Push panel/bins/1m | §1.3 |
| 5 | Sửa `.java` | §1.2 |
| 6 | Intrabar/liquidation | chỉ có OHLC 1m ⇒ quy ước ưu tiên SL (bảo thủ) |
| 7 | Short toàn universe (không xếp hạng) | câu hỏi là selector S1 decile 0 |

## 7. SẢN PHẨM

`docs/prereg/PREREG_SHORT_FULLCHAIN.md` (`9ac83699`) ·
`research/analysis/short_fullchain_s1.py` ·
`research/analysis/short_fullchain_gate.py` ·
`research/analysis/short_fullchain_sim.py` + `short_fullchain_merge.py` ·
`docs/result/RESULT_SHORT_FULLCHAIN.md` (this) + `.json`.
