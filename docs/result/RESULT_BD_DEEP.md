# RESULT_BD_DEEP — `rateDown15MAvg` ("DownAvg15M"): cách tính · ý nghĩa · NÚT chỉnh

Chạy 2026-10-01. Pre-reg: `docs/prereg/PREREG_BD_DEEP.md` (commit `2536c43c`, **TRƯỚC** khi đo).
**0-SIM THUẦN PYTHON**: KHÔNG chạy Java, KHÔNG build, KHÔNG sim, KHÔNG Kaggle job, KHÔNG chạm 242,
KHÔNG sửa `.java`, KHÔNG đọc/chạm 2026. DEV = `[2021-07-01, 2025-12-31)` giờ `Asia/Saigon` (2 299 826 phút).
Script: `research/analysis/bd_deep.py`, `bd_deep_raw.py`, `bd_deep_defn.py`. JSON kèm: `RESULT_BD_DEEP{,_dist,_sweep,_year,_link,_defn}.json`.

---

## 0. TRẢ LỜI NGẮN (4 câu hỏi owner)

1. **Cách tính hiện tại có hợp lý không?** — **Hợp lý về ý tưởng, nhưng có 2 chỗ "lệ" đo được**:
   (a) `calRateChangeAvg` là **TRUNG BÌNH của N khoá CỰC TRỊ** (order statistic cố định), **KHÔNG** phải
   phân vị ⇒ giá trị **phụ thuộc SỐ COIN** của universe; cùng ngưỡng `-0.03157` cho **tần suất ON lệch 3×**
   giữa các năm (2023 `0,108 %` vs 2025 `0,333 %`). (b) **Hai thống kê KHÁC THANG** (nến 1M vs độ sâu
   dưới đỉnh 15M) **dùng CHUNG một hằng số** `-0.03157` — đây là *trùng số*, không phải *hiệu chỉnh*:
   cùng ngưỡng đó cho BIG_DOWN **124 phút / 4,5 năm** (88 episode) nhưng DCA **5 316 phút** (1 180 episode).
2. **Nút nào CHƯA thử & có tiềm năng?** — **`N` (=100)**, **cửa sổ 15′**, **định nghĩa** (mean-worst-N →
   phân vị/median), **bộ lọc** (`-0.004/-0.15/+0.3`), **ngưỡng DCA tách riêng** (`MS_DOWN_BIG_AVG_DCA`).
   0-sim chứng minh 4 nút đầu **đổi mạnh bộ ngày ON** (Jaccard 0,18–0,84) ⇒ **KHÔNG vô hại**; nhưng
   **không nút nào đã có bằng chứng PnL**.
3. **Chỉnh nó có cải thiện G2 không (số cụ thể)?** — **Chưa có bằng chứng cải thiện, và có bằng chứng NGƯỢC
   ở nút duy nhất đã quét trên sim**: `BD_THRESHOLD_FRAGILITY` cho thấy `-0.03157` là **local max PnL**
   (16 254 USD vs 15 188/12 525/8 323 ở 4 điểm lân cận) ⇒ nới hay siết đều **kém hơn**. Ở tầng leg toàn bộ,
   cả 5 điểm đều overlap CI ⇒ nút ngưỡng **không đổi chất lượng leg**. Về **phạm vi ảnh hưởng**: trong
   baseline `de-p1` (R4/G2, n 2517) `rateDownAvg` chạm **248 leg (9,9 %)**, `rateDown15MAvg` chạm **46 leg (1,8 %)**.
4. **KẾT LUẬN: NO-GO / NULL (0-sim).** Không có biến thể nào được đề xuất tiêu sim dựa trên bằng chứng hiện có:
   nút ngưỡng đã bị chứng minh **mong manh + hiện tại đã là đỉnh**; các nút `N`/cửa sổ/định nghĩa **chưa có
   cơ chế lý thuyết nào nói tốt hơn**, chỉ là *đổi định nghĩa rồi hy vọng*. **Biến thể đáng đi DUY NHẤT (nếu
   owner muốn tiêu 1 vòng Kaggle)**: *chuẩn hoá theo universe* — dùng **phân vị** thay vì mean-worst-100
   (vd. `frac 0,20`), vì đó là nút **sửa đúng khuyết điểm non-stationarity đã ĐO**, không phải quét mù.

---

## 1. CÁCH TÍNH THẬT (file:line + số)

### 1.1 `calRateChangeAvg` — `MarketBigChangeDetector.java:149-166`

```java
TreeMap<Float,String> rateLoss2Symbols  // key = chi so, ASC
if (period > size * 4 / 5) period = size * 4 / 5;      // CAP 4/5
for (entry : map.entrySet()) { counter++; total += key; if (counter >= period) break; }
return total / counter;                                 // TRUNG BINH `period` khoa DAU TIEN (= cuc tri nhat)
```

⇒ **KHÔNG phải phân vị, KHÔNG phải median, KHÔNG percentile**. Đây là **trung bình của `period` giá trị
CỰC TRỊ NHẤT** = **tail-mean theo SỐ LƯỢNG CỐ ĐỊNH**. Cap `4/5` chỉ chặn việc lấy hết rổ.

### 1.2 `calMarketData` — `MarketBigChangeDetector.java:48-92`

| field | công thức | bộ lọc | N |
|---|---|---|---|
| `rateDownAvg` | `mean(100 × (close/open − 1)` **âm nhất**) | bỏ `diedSymbol`; bỏ nếu `rateChangeBtc > −0,004 && rateChange < −0,15`; bỏ nếu `rateChange > +0,3` | 100 |
| `rateUpAvg` | `−mean(100 × (open/close − 1) … )` | như trên | 100 |
| **`rateDown15MAvg`** | `mean(100 × (close/maxPrice − 1)` **âm nhất**) | như trên; **luôn ≤ 0** | 100 |
| `rateMin2Symbols` | `−(close/minPrice − 1)` | — | (không dùng để gate) |

`maxPrice` = **max(`maxPrice`) của 15 nến 1M gần nhất, KỂ CẢ nến đang chạy** — `Configs.NUMBER_TICKER_CAL_RATE_CHANGE = 15`
(`Configs.java:107`); dựng buffer trượt ở `MarketDataInlineGenerator.java:35/57-85` và `ExportMarketData2File.java:111`.
`minPrice` tương tự (min). ⇒ **15 phút**, không phải 15 nến giờ/ngày.

### 1.3 Ngưỡng & nơi dùng

- `Configs.java:466` `MS_DOWN_BIG_AVG = -0.03157f` (comment: *"HPO (đã revert về cũ): -0.05514f"*) → `getMarketStatus1M` ⇒ **BIG_DOWN**.
- `Configs.java:470` `MS_DOWN_BIG_AVG_DCA = -0.03157f` → `isDcaAlt` (`rateDown15MAvg < THR_DCA || rateDownAvg < THR_DCA/3`) ⇒ **DCA_LEVEL1**.
- Override: `SIM_MS_DOWN_BIG_AVG` / `SIM_MS_DOWN_BIG_AVG_DCA` (`Configs.java:900/902`).
- **4 nơi dùng**: `MarketBigChangeDetector` (BIG_DOWN + DCA) · `TickWeakBlock.java:135` (MODE `DROP15M`) ·
  `BdSizeAdapt.java:86-89` (dùng `rateDownAvg` + `MS_DOWN_BIG_AVG`) · `DetectEntrySignal2TradeNormal.java:263-265` (live).

### 1.4 KIỂM CHỨNG nguồn (bắt buộc, đã PASS)

- `market.bin` (`/home/ubuntu/wfo_ds_x1_2021/market.bin`, 2 554 812 phút) khớp **100 % chính xác** cột
  `dow/up/dow15m` tại 2 517 entry của `de-p1` (max |Δ| = 4,9e-9 — sai số float32). ⇒ **market.bin = đúng
  tín hiệu sim đọc**, dùng được cho mọi phép đo tần suất/ngưỡng.
- Tái lập `calMarketData` từ `ticker_YYYYMMDD.bin.gz` (ngày 20241026): `max|Δ|` = **5,0e-4** (down/up) ·
  **5,0e-3** (down15); 100 % phút lệch < 1e-3 ⇒ đủ tốt để quét `N`/cửa sổ/định nghĩa.

---

## 2. Ý NGHĨA + PHÂN BỐ + TẦN SUẤT VƯỢT NGƯỠNG (DEV, `market.bin`)

**Một câu:** `rateDown15MAvg` = *"độ sâu TRUNG BÌNH dưới đỉnh 15 phút của 100 coin TỆ NHẤT"* —
một thước **chiều sâu đuôi** của thị trường trong 15 phút, **luôn ≤ 0**.

| thống kê | `rateDownAvg` (nến) | `rateUpAvg` | **`rateDown15MAvg`** |
|---|---|---|---|
| p1 | −0,00460 | −0,00223 | **−0,02184** |
| p5 | −0,00284 | −0,00091 | **−0,01443** |
| p50 | −0,00065 | +0,00067 | **−0,00531** |
| p95 | +0,00087 | +0,00281 | **−0,00190** |
| p99 | +0,00212 | +0,00454 | **−0,00135** |
| min / max | −0,3542 / +0,0383 | −0,0717 / +0,1630 | **−0,7183 / 0,0000** |

**Tần suất vượt ngưỡng (cùng hằng số −0,03157):**

| tín hiệu | điều kiện | % phút | số phút | episode (0→1) | độ dài run |
|---|---|---|---|---|---|
| **BIG_DOWN** | `rateDownAvg < −0,03157` | 0,0054 % | **124** | **88** | mean 1,41′ · max 13′ |
| **DCA** | `rateDown15MAvg < −0,03157` **hoặc** `rateDownAvg < −0,01052` | 0,2497 % | **5 742** | 1 520 | — |
| └ DCA nhánh 15M | `rateDown15MAvg < −0,03157` | 0,2311 % | 5 316 | 1 180 | mean 4,51′ · max 224′ |
| └ DCA nhánh nến | `rateDownAvg < −0,01052` | 0,0587 % | 1 349 | 1 028 | — |

⇒ **BIG_DOWN ⊂ DCA** (124/124 phút BIG_DOWN đều DCA). BIG_DOWN nằm ở **p≈0,005 %** (cách p1 **7×**) —
**sự kiện vô cùng thưa: 124 phút · 54 ngày trên 4,5 năm**. Theo năm: 16/10/25/35/38 phút (2021→2025).
Trong `de-p1`: **BIG_DOWN 248 leg** (124 phút × 2 coin) · **DCA_LEVEL1 46 leg** · PREDICT 2 223.

**Quan hệ với BTC / regime** (`CLOSES_1H.bin`, MA200 causal):

| tập | n | BTC ret 1h (mean) | BTC ret 1h p1 | BTC fwd 1h (mean) | % phút BTC trên MA200 |
|---|---|---|---|---|---|
| ALL | 2 299 826 | +0,0039 % | −1,73 % | +0,0023 % | 50,7 % |
| BIG_DOWN | 124 | **−0,4510 %** | −2,12 % | **−1,3305 %** | **30,6 %** |
| DCA15 | 5 316 | −0,2414 % | −5,04 % | −0,6599 % | 29,0 % |

⇒ Tín hiệu bắt đúng **cú sập đồng loạt**: BTC đã giảm trong giờ đó và **GIẢM TIẾP 1 giờ sau** (fwd −1,33 %),
và xảy ra **lệch về regime gấu** (30,6 % vs 50,7 % thời gian ở trên MA200). **`corr(rateDownAvg, rateDown15MAvg) = 0,508`**.

**NON-STATIONARITY theo năm** (khuyết điểm cấu trúc — xem §3.4):

| năm | `rateDownAvg` p1 | `rateDown15MAvg` p1 | `rateDown15MAvg` p0,2 | BIG_DOWN %phút | DCA %phút |
|---|---|---|---|---|---|
| 2021 | −0,00418 | −0,02055 | −0,03239 | 0,0062 | 0,2216 |
| 2022 | −0,00438 | −0,02202 | −0,03548 | 0,0020 | 0,2954 |
| 2023 | −0,00324 | −0,01552 | −0,02558 | 0,0049 | **0,1077** |
| 2024 | −0,00463 | −0,02135 | −0,03133 | 0,0068 | 0,1932 |
| 2025 | −0,00538 | −0,02487 | −0,03594 | 0,0075 | **0,3334** |

---

## 3. `rateDownAvg` (nến) vs `rateDown15MAvg` (đỉnh 15′) — KHÁC GÌ, ĐIỀU KHIỂN GÌ

| | `rateDownAvg` | `rateDown15MAvg` |
|---|---|---|
| đo gì | dump **1 nến 1 phút** của 100 coin tệ nhất | **khoảng cách dưới ĐỈNH 15′** của 100 coin tệ nhất |
| thang đo | p1 = −0,46 % · min −35 % | p1 = −2,18 % · min −71,8 % |
| **điều khiển** | `getMarketStatus1M` ⇒ **BIG_DOWN** (mở leg 2 coin) + `BdSizeAdapt` | `isDcaAlt` ⇒ **DCA_LEVEL1** + `TickWeakBlock DROP15M` |
| tần suất @−0,03157 | 124 phút (0,0054 %) | 5 316 phút (0,231 %) — **gấp 43×** |
| bản chất | **cú sốc tức thời** (spike 1,4 phút) | **trạng thái suy yếu tích luỹ** (run 4,5 phút) |
| dùng chung hằng số? | **CÓ — cả hai = −0,03157** (trùng số, không hiệu chỉnh) | 〃 |

**Điểm "lệ" #2 phát biểu rõ:** hai biến **khác đơn vị và khác phân bố ~1 bậc** (p1 −0,46 % vs −2,18 %) nhưng
**dùng CHUNG một hằng số**. Hệ quả: trong thực tế `rateDown15MAvg` "rộng" hơn nhiều, nên DCA bắt **toàn bộ**
BIG_DOWN cộng thêm 5 192 phút khác — hai ngưỡng *trông như* độc lập nhưng **không độc lập**.

---

## 4. BẢNG NÚT — ĐÃ THỬ / CHƯA THỬ (số + commit)

| # | Nút | Trạng thái | Kết quả đo (số) | Nguồn |
|---|---|---|---|---|
| 1 | **Ngưỡng BIG_DOWN** `MS_DOWN_BIG_AVG` | **ĐÃ THỬ (sim)** | PnL BIG_DOWN **2×** qua 5 điểm (−0,025→16 254→−0,045: 11 413/15 188/**16 254**/12 525/8 323). `−0,03157` = **local max**. Hard-constraint cả 5 điểm PASS; 5 rate toàn-bộ-leg đều **overlap CI**. | `RESULT_BD_THRESHOLD_FRAGILITY` (prereg `61cf533`, code `720afe0`); `Configs.java:466` ghi HPO −0,05514 đã revert |
| 2 | **Ngưỡng DCA tách riêng** `MS_DOWN_BIG_AVG_DCA` | **ĐÃ TẠO, CHƯA QUÉT sim** | Default = giá trị cũ ⇒ parity byte-identical; chưa có điểm quét riêng | `BD_THRESHOLD_FRAGILITY §1` |
| 3 | **`N` (đang 100)** | **CHƯA THỬ** | 0-sim: `N=20` ⇒ BIG_DOWN 125→**254** phút (Jaccard **0,49**); `N=200` ⇒ **94** (Jac 0,75); `N=400` ⇒ 84 (Jac 0,67 — **cap 4/5 BẮT ĐẦU BIND**, universe mean 268) | §5 |
| 4 | **Cửa sổ (đang 15′)** | **CHƯA THỬ** | 0-sim: `win5` ⇒ DCA 1 895→**628** (Jac **0,33**); `win30` ⇒ 4 306 (Jac 0,44); `win60` ⇒ 10 751 (**Jac 0,18**) | §5 |
| 5 | **Định nghĩa** (mean-worst-N → phân vị/median) | **CHƯA THỬ** | 0-sim: `frac0,50` (≈"median độ sâu dưới đỉnh") ⇒ lệch ít (Jac **0,82**, corr 0,976); `frac0,33` Jac 0,79; `frac0,10` Jac 0,45 | §5 |
| 6 | **Bộ lọc** (`rateChangeBtc>−0,004&&rc<−0,15` / `rc>+0,3`) | **CHƯA THỬ** | — (chưa có đo) | — |
| 7 | **Breadth/rolling-quantile khác** (DEPTH/BREADTH/DROP15M) | **ĐÃ THỬ** | **NULL/NO-GO cả 3**; `DROP15M` (dùng chính `rateDown15MAvg`) chặn 23,80 % lượt nhưng **net mất 0 lệnh** | `RESULT_TICK_BLOCK` (prereg `b98c9ff`) |
| 8 | **Selection 2 coin BIG_DOWN** | **ĐÃ THỬ** | **NULL** — 0/3 rate ngoài CI; DROP point-estimate +82 % PnL/leg nhưng CI quá rộng | `RESULT_SEL_BIGDOWN` (prereg `4de6b6e`) |
| 9 | **Size/severity theo BIG_DOWN** | **ĐÃ THỬ** | **NULL** — 248 leg giữ nguyên; chỉ rescale pnl/leg, không đổi chất lượng/rủi ro | `RESULT_BD_SIZE_ADAPT` (prereg `a55f913`) |
| 10 | **Bỏ HẲN BIG_DOWN + DCA** | **ĐÃ THỬ** | **XẤU đi rõ**: T170 mất **−18,7 % equity** (111 070→90 247), CAGR **−5,83 pp**, UW FAIL 2022 (131) | `RESULT_NOBD_READJUDICATE` |
| 11 | **DCA leg-2 theo tín hiệu / nới gate** | **ĐÃ THỬ** | **NULL** cả V1 (`bd45a50`), V2 (`130ad24`), V3 (`1063dd1`) — UW là ràng buộc binding | `RESULT_DCA_SIGNAL_GATE{,_V2}`, `RESULT_DCA_GATEWIDEN_V3` |
| 12 | **Pacing BIG_DOWN** | **ĐÃ THỬ** | **NULL** (fail t2 ∧ t3) | `RESULT_PACING_BIGDOWN` (prereg `aa3c4aa`) |

---

## 5. QUÉT `N` / CỬA SỔ / ĐỊNH NGHĨA (0-sim, mẫu 100 ngày: **tất cả 56 ngày BIG_DOWN** + 46 ngày thường, seed 20261001)

Thước đo: `n_on` = số phút `< −0,03157`; `ep` = episode; `jac` = Jaccard tập phút ON vs baseline; `corr` = tương quan chuỗi.
Universe: **mean 268,5 coin/phút** (min 112, max 578).

| biến thể | `n_on` | `ep` | `jac` | `corr` | mean |
|---|---|---|---|---|---|
| **BASE down (N=100)** | **125** | 88 | 1,00 | 1,00 | −0,001017 |
| down gr N=20 | 254 | 116 | **0,49** | 0,947 | −0,002602 |
| down gr N=50 | 188 | 94 | 0,66 | 0,987 | −0,001638 |
| down gr N=200 | 94 | 68 | 0,75 | 0,983 | −0,000591 |
| down gr N=400 | 84 | 62 | 0,67 | 0,932 | −0,000440 |
| down frac 0,10 | 228 | 117 | 0,55 | 0,949 | −0,002255 |
| down frac 0,50 | 113 | 80 | 0,76 | 0,960 | −0,000844 |
| **BASE d15 (N=100, win 15)** | **1 895** | 260 | 1,00 | 1,00 | −0,007857 |
| d15 N=20 | 6 746 | 977 | **0,28** | 0,967 | −0,014245 |
| d15 N=50 | 2 771 | 390 | 0,68 | 0,995 | −0,010237 |
| d15 N=200 | 1 586 | 225 | 0,84 | 0,993 | −0,006327 |
| d15 N=400 | 1 485 | 215 | 0,78 | 0,970 | −0,005790 |
| d15 win 5 | 628 | 138 | **0,33** | 0,894 | −0,004492 |
| d15 win 30 | 4 306 | 437 | 0,44 | 0,930 | −0,011221 |
| d15 win 60 | 10 751 | 736 | **0,18** | 0,832 | −0,016080 |
| d15 frac 0,10 | 4 218 | 570 | 0,45 | 0,974 | −0,012665 |
| d15 frac 0,33 | 2 205 | 315 | 0,79 | 0,981 | −0,008265 |
| d15 frac 0,50 | 1 850 | 250 | 0,82 | 0,976 | −0,007060 |

**Đọc bảng:** `N` và **cửa sổ** là 2 nút **mạnh nhất** (`N=20` ⇒ 2× số phút BD; `win60` ⇒ 5,7× số phút DCA;
Jaccard 0,18–0,33 ⇒ **bộ ngày ON đổi gần hết**). **Định nghĩa** (mean-worst-N vs mean-worst-p%) **yếu hơn**
(`frac0,50` chỉ lệch Jac 0,82) — vì `N=100` trên universe ~268 **đã là** "worst ~37 %", gần `frac0,33`.
Baseline `down` trong mẫu = 125 phút, khớp toàn DEV = 124 ⇒ **bộ ngày BIG_DOWN đã bao đủ** (sanity PASS).

---

## 6. KẾT LUẬN — **NO-GO / NULL** (0-sim)

1. **Cách tính hiện tại:** hợp lý về ý tưởng (bắt được đúng cú sập đồng loạt — BTC fwd 1h −1,33 %; regime gấu 2×),
   nhưng có **2 chỗ lệ đo được**: (i) là **order statistic cố định** (mean-worst-100) ⇒ **phụ thuộc universe**,
   tần suất ON **lệch 3× giữa 2023 và 2025** với cùng ngưỡng; (ii) **hai thang khác nhau dùng chung hằng số**
   `−0,03157` ⇒ BIG_DOWN là tập con của DCA, hai ngưỡng không độc lập.
2. **Nút chưa thử:** `N`, cửa sổ, định nghĩa, bộ lọc, ngưỡng DCA tách riêng — đều **đổi mạnh bộ ngày ON**
   (không vô hại) nhưng **chưa nút nào có bằng chứng PnL**.
3. **Cải thiện `G2`?** **Không có bằng chứng nào.** Nút ngưỡng (nút duy nhất có số sim) đã cho thấy hiện tại
   là **đỉnh PnL local** ⇒ nới/siết đều kém. Các vòng liên quan (#7–#12) **toàn NULL**.
4. **KẾT LUẬN: NO-GO.** Không đề xuất tiêu sim cho biến thể nào dựa trên bằng chứng hiện có. **Biến thể
   đáng đi duy nhất nếu owner muốn tiêu 1 vòng Kaggle:** **chuẩn hoá `rateDown15MAvg` theo phân vị universe**
   (thay mean-worst-100) — vì nó **sửa đúng khuyết điểm non-stationarity đã ĐO (§2/§3)**, không phải quét mù;
   và với `rateDown15MAvg` chỉ chạm **46/2517 leg (1,8 %)** của G2 nên **kỳ vọng lợi ích trần rất thấp**.

## 7. KHÔNG làm / giới hạn

- **KHÔNG** kết luận PnL từ số 0-sim (đúng pre-reg §3). Mọi con số §5 là **tần suất tín hiệu**, không phải PnL.
- Tái lập từ ticker bin lệch tối đa 5e-3 (do `diedSymbol` + cửa sổ ấm đầu ngày) ⇒ §5 là **so sánh tương đối**.
- **KHÔNG** chạm 2026 (holdout nguyên vẹn). **KHÔNG** sửa `.java`. **KHÔNG** chạm 242.
