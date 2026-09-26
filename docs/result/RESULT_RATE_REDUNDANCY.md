# RESULT_RATE_REDUNDANCY — KIỂM TRÙNG LẶP THANG ĐO (tầng B) + TEST RÀO MỚI (a)/(b)

Thực thi `docs/prereg/PREREG_RATE_REDUNDANCY.md` (commit `330811a`, chốt **TRƯỚC** khi đo).
Thuần **Python offline** trên `printDone.csv` **đã có** — `research/analysis/rate_redundancy.py`
(+ `docs/result/RATE_REDUNDANCY.json`, số thô `/tmp/rr/`). **KHÔNG** train/sim/Java, **KHÔNG** chạm
production/242/ONNX/LIVE, **KHÔNG** push. DEV only: mọi leg `start <= 2025-12-31`, **không đọc 2026**.
**Không** chạy lại vòng `PREREG_TAIL_ROBUST_RULERS.md` (không đụng artifact phiên khác).

## 0. KẾT LUẬN NGAY (verdict)

1. **CÓ 1 cặp TRÙNG THỐNG KÊ mạnh:** **`win%` ↔ `TSloss%`** — Pearson **−0,992** · Spearman **−0,930**
   trên **448 run** (khối chính). ⇒ **2 rate này KHÔNG phải 2 bằng chứng độc lập**. Khối ô `run×năm`
   chỉ **Pearson −0,967** đạt, Spearman **−0,784** không đạt ⇒ theo luật chốt trước
   (§3-ii: phải đạt **cả 2 khối**) **KHÔNG** gọi "trùng thống kê", gọi **"phụ thuộc gần-tuyệt-đối ở cấp run"**.
   **Không** cặp nào đạt `|rho| ≥ 0,99` ở bất kỳ khối nào.
2. **CÓ 1 TRÙNG ĐẠI SỐ:** **`meanP` là HÀM XÁC ĐỊNH của {`TSloss%`, `mP|SM`, `mP|SL`}**
   (đồng nhất thức **H3**, sai số ≤ 1e-15) trên **100 %** run mà `SM ∪ SL` phủ hết leg
   (**408/448 = 91,1 %** run; **100 %** trong 8 đối tượng được đo). ⇒ `meanP` **không mang thông tin mới**.
3. **`n` KHÔNG phải rate chất lượng** (là **quy mô mẫu**, và là **mẫu số chung** của `win%`, `TSloss%`,
   `meanP`, `mMargin`) ⇒ không được tính là 1 trong "≥2 rate" của luật CI.
4. **Rào (a) `≤ 15 %`: 7/8 biến thể FAIL** (20,7 – 40,9 %). **CHỈ `kg0-q998-15m` PASS** (12,91 %).
5. **Rào (b) bỏ top-20 % ⇒ PnL DƯƠNG: 4/8 PASS** — `kg0-q995` (+772) · `kg0-q998` (+4 180) ·
   `kg0-q999` (+2 901) · `kg0-q998-15m` (+5 848). **ÂM:** `KEEPLEG0` (−1 575) · `T100` (−76 850) ·
   `GD92` (−61 183) · `T170` (−1 723).
5b. **RÀO (b′) NÂNG LÊN bỏ top-50 % (owner 26/09 23:17, `RULERS_CURRENT.md` §8) ⇒ PnL DƯƠNG:
   **0/8 PASS** — **TẤT CẢ FAIL rất sâu**: `T100` **−155 919** · `GD92` **−134 390** · `T170` **−35 416** ·
   `KEEPLEG0` **−33 196** · `kg0-q995` **−29 512** · `kg0-q998` **−24 511** · `kg0-q999` **−23 257** ·
   `kg0-q998-15m` **−3 357**. (Đồng nhất thức `TF(50 %) ≡ Σ nửa dưới` — kiểm **ĐÚNG 8/8**, lệch 0 USDT.)
5c. **⚠️ KHẮC RÕ "gần với median leg > 0" — SAI nếu đọc là tương đương.** `median leg PnL` **DƯƠNG ở
   CẢ 8 biến thể** (59,1 – 74,6 USDT; `sign_frac(pnl>0)` = 83,4 – 90,5 %) nhưng `Σ nửa dưới` **ÂM ở cả 8**.
   ⇒ **`median > 0` KHÔNG suy ra được rào (b′)**, và ngược lại. Điều kiện thật là **"lãi TRUNG BÌNH của nửa
   dưới > 0"**, mạnh hơn hẳn "lệnh trung vị có lãi".
6. **KHÔNG cấu hình nào đủ điều kiện go-live.** Với rào (b′)-50 %: **0/8** (mọi biến thể âm sâu).
   Với rào (b)-20 %: biến thể duy nhất PASS cả (a)+(b) là `kg0-q998-15m`, mà cấu hình này (i) **không tái lập
   được nhịp live 1′** (tỷ lệ entry 0,440 < 0,60 → `RESULT_GATE_RECAL.md`), (ii) đã **0/4 arm PASS**,
   (iii) **CAGR 11,08 %/năm vs 27,14 %** của `KEEPLEG0` (−59 % tương đối; PnL cuối kỳ 21 148 vs 68 083 = −69 %).
7. **SỬA SAI SỐ LIỆU ĐANG LƯU HÀNH:** `RULERS_CURRENT.md` §7 và `RESULT_FRAGILITY_N.md` §0.3 viết
   *"hiện bỏ top-5 % đã ÂM (T100/GD92)"* — **SAI**. Số thật: bỏ **top-5 %** vẫn **DƯƠNG**
   (`T170` +32 922 · `KEEPLEG0` +30 416 · `GD92` +14 794 · `T100` +2 771); chỉ **top-10 %** mới ÂM
   (`T100` −31 294 · `GD92` −18 167). Ngưỡng gãy thật `q*` (bỏ-top nhỏ nhất làm tail-free ≤ 0):
   **T100 5,5 % · GD92 7,0 % · KEEPLEG0 19,0 % · T170 19,0 % · kg0-q995 21,0 % · kg0-q999 22,5 % ·
   kg0-q998 23,5 % · kg0-q998-15m 38,0 %**.

---

## 1. VIỆC 1 — ĐỊNH NGHĨA CHÍNH XÁC TỪNG RATE (`file:line`)

Nguồn số: `storage/printDone.csv`. Cột do `TraceOrderDone.printOrderTestDone` ghi
(`src/main/java/com/binance/chuyennd/bigchange/test/TraceOrderDone.java`):
- **`profit`** = `100 · (priceTP − priceEntry)/priceEntry`, **đổi dấu nếu `side = SELL`** — dòng **`:114-115`**
  (`Utils.rateOf2Double(order.priceTP, order.priceEntry)`), ghi ra tại **`:133`** ⇒ **% chênh giá leg**.
- **`pnl`** = `order.calTp()` — **`:149`** ⇒ **PnL USDT ròng của leg** (dùng cho mọi thang TIỀN).
- **`margin`** = `order.calMargin()` — **`:148`**; **`quantity`** — **`:147`**.
- **`status`** = `order.status.toString()` — **`:134`**; enum `OrderTargetStatus`
  (`trading/OrderTargetStatus.java:23-35`), 3 giá trị thực gặp trong dữ liệu: **`STOP_MARKET_DONE` (`:31`)** ·
  **`STOP_LOSS_DONE` (`:29`)** · **`REQUEST` (`:23`)**.

Bảng rate (`research/analysis/c3_rates.py:94-109` `def rates(d)`; nhãn ở `research/analysis/x1_rates.py:22`;
`KEYS` ở `c3_rates.py:159`):

| rate | `file:line` | định nghĩa | mẫu số |
|---|---|---|---|
| `n` | `c3_rates.py:102` | `len(d)` — **số leg** trong bảng trade | — |
| `win%` | `c3_rates.py:103` | `100 · mean(profit > 0)` — **% leg CÓ lãi giá** (bất kể cách thoát) | **`n`** |
| `TSloss%` | `c3_rates.py:104` | `100 · mean(status == STOP_LOSS_DONE)` — **% leg thoát bằng dừng lỗ cứng** | **`n`** |
| `mP\|SM` | `c3_rates.py:105` | `mean(profit)` trên nhóm **SM = `status == STOP_MARKET_DONE`** | **`n_SM`** |
| `mP\|SL` | `c3_rates.py:106` | `mean(profit)` trên nhóm **SL = `status == STOP_LOSS_DONE`** | **`n_SL`** |
| `meanP` | `c3_rates.py:107` | `mean(profit)` — bình quân **toàn bộ** leg | **`n`** |
| `mMargin` | `c3_rates.py:108` | `mean(margin)` — **kích thước vốn/leg (USDT)** | **`n`** |

**SM / SL nghĩa là gì (nhóm lệnh nào):**
- **SM (`STOP_MARKET_DONE`)** = leg đóng bằng lệnh **STOP_MARKET đã kéo (trailing) lên vùng lãi** —
  xem `research/ExitClampTest118.java:28` (*"priceSL > priceEntry → STOP_MARKET_DONE"*) ⇒ nhóm **thoát
  trong lãi** (≈ nhóm WINNER).
- **SL (`STOP_LOSS_DONE`)** = leg đóng bằng **dừng lỗ cứng** dưới giá vào (hoặc huỷ niêm yết/de-list,
  `SimulatorMarketLevelTicker1MStopLoss.java:891`) ⇒ nhóm **thoát trong lỗ** (≈ nhóm LOSER).
- **`REQUEST`** = leg **chưa có kết quả khớp** còn sót lại trong bảng (`Simulator…:1162`, `:1489`) —
  **không** thuộc SM/SL.

## 2. VIỆC 2 — KIỂM ĐẠI SỐ (đồng nhất thức)

Trên **448 run** đủ điều kiện (`n ≥ 30`, DEV-2025):

| # | đồng nhất thức | kết quả | kết luận |
|---|---|---|---|
| **H1** | `status` chỉ có SM + SL ⇒ `n_SM + n_SL = n` | **SAI**: 40/448 run có **`REQUEST`** (tối đa **195 leg**; `X1_HD_E25/E50/E100`) | `SM ∪ SL ≠ all` ở **8,9 %** run |
| **H2** | `win% ≡ 100 − TSloss%` | **SAI**: chỉ **13/448** run đúng (2,9 %). Khe hở trung vị **0,66 pp**, lớn nhất **13,87 pp** | `win%`/`TSloss%` **không** trùng hoàn toàn |
| **H3** | `meanP ≡ (1 − TSloss%/100)·mP\|SM + (TSloss%/100)·mP\|SL` | **ĐÚNG** (sai số ≤ 1e-15) trên **408/408 = 100 %** run có `n_other = 0` | ⇒ **`meanP` = hàm xác định** của `TSloss%`+`mP\|SM`+`mP\|SL` |
| **H4** | `mMargin` có đồng nhất thức với rate khác? | **KHÔNG** | `rho` (nếu cao) là **thống kê**, không phải đại số |
| **H5** | mẫu số: `win%`·`TSloss%`·`meanP`·`mMargin` chung mẫu số `n`; `mP\|SM`→`n_SM`; `mP\|SL`→`n_SL` | **ĐÚNG** (đúng theo định nghĩa `:103-108`) | 4 rate **dùng chung `n`** ⇒ sai số chuẩn **phụ thuộc nhau** |

**Khe hở H2 giải thích được:** `win% − (100 − TSloss%) = 100·(C − B − other_neg)/n`, với
`B = #(SM & profit ≤ 0)`, `C = #(SL & profit > 0)`, `other_neg = #(REQUEST & profit ≤ 0)` ⇒ **lệch chỉ do
"lệch phân loại" (dấu `profit` ≠ nhóm `status`)**, không do lỗi tính. Đại lượng lệch này **KHÔNG** nằm
trong bộ 7 rate ⇒ **`win%` không suy ra được từ `TSloss%`** (H2 sai là kết quả thật, không phải bug).

**Kết luận VIỆC 2 — cặp TRÙNG HOÀN TOÀN (đại số):**
- **`meanP` ∈ span{`TSloss%`, `mP|SM`, `mP|SL`}** — trùng đại số (điều kiện đủ: `n_other = 0`; 91,1 % run,
  và **100 %** 8 đối tượng được đo: khe H3 ≤ 1,8e-15).
- Tổng quát hơn và **luôn đúng**: `meanP = Σ_g (n_g/n)·(mean profit nhóm g)` trên **mọi** nhóm `status`
  ⇒ `meanP` **không bao giờ** mang thông tin độc lập với **phân rã theo `status`**.
- **KHÔNG** tìm thấy đồng nhất thức nào khác (H4 âm).

## 3. VIỆC 3 — KIỂM THỐNG KÊ (bảng số)

**Số run dùng:** **448** (từ `/home/ubuntu/kaggle_sim/out/*` **và** `/home/ubuntu/java/devrun/*`, có
`storage/printDone.csv`, `n ≥ 30` sau lọc DEV; 15 thư mục bị loại vì thiếu CSV/cột). Khối ô `run×năm`
(`n_year ≥ 30`): **1 800 ô**. Danh sách tag đầy đủ: `docs/result/RATE_REDUNDANCY.json` → `tags`
(gồm toàn bộ arm gate-recal `gr-*`, `gr-kg0-q99*`, `t170-x1-2021`, `hn-t100`, `hn-g92`, các `X1_*`,
`CC_*`, `DS_*`, `FG_*`, `NB_*`, `RG_*`, …).

**Bảng cặp `|rho| ≥ 0,9` (và `≥ 0,99`) — mọi khối đo:**

| khối | n | cặp đạt `|rho|≥0,9` | Pearson | Spearman | `≥0,99` |
|---|---|---|---|---|---|
| **A — 448 run (toàn kỳ)** | 448 | **`win%` ↔ `TSloss%`** | **−0,992** | **−0,930** | **không** |
| A′ — 448 run `n≥200` | 448 | `win%` ↔ `TSloss%` | −0,992 | −0,930 | không |
| A″ — 408 run `n_other=0` | 408 | `win%` ↔ `TSloss%` | −0,978 | −0,913 | không |
| **B — 1 800 ô run×năm** | 1 800 | `win%` ↔ `TSloss%` *(chỉ Pearson đạt)* | −0,967 | −0,784 ✗ | không |
| B″ — 1 674 ô `n_other=0` | 1 674 | *(chỉ Pearson đạt)* | −0,908 | −0,745 ✗ | không |
| B‴ — trong-run (đã trừ TB theo run) | 1 800 | **không cặp nào** | −0,628 | −0,637 | không |

**Các cặp mạnh tiếp theo (khối A, đều dưới ngưỡng):** `win%`↔`mP|SM` P=**−0,866** S=+0,048 ·
`TSloss%`↔`mP|SM` P=**+0,841** S=−0,029 · `TSloss%`↔`mP|SL` P=+0,773 S=+0,180 ·
`meanP`↔`mMargin` P=+0,578 S=+0,454 · `mP|SM`↔`mP|SL` P=+0,620 S=+0,388.
**Toàn bộ 15 cặp × 6 khối: KHÔNG cặp nào đạt `|rho| ≥ 0,99`.**

**Kết luận VIỆC 3:**
- **TRÙNG (mạnh nhất, mức "gần-tuyệt-đối"): `win%` ↔ `TSloss%`** — tuyệt đối ở **cấp run** (−0,99);
  suy yếu ở **cấp ô run×năm** (Spearman −0,78) và ở **biến thiên TRONG run** (−0,63). Nghĩa là hai rate
  này **gần như cùng một thông tin giữa các cấu hình**, nhưng **khác nhau chút ít theo thời gian**.
- **TRÙNG ĐẠI SỐ: `meanP`** (mục 2) — không cần `rho`.
- **ĐỘC LẬP THẬT (mọi khối đều `|rho| < 0,9` cả Pearson & Spearman): `mP|SM` · `mP|SL` · `mMargin`.**
  (`mP|SM` vs `mP|SL` chỉ +0,62/+0,39 ⇒ thắng-lớn và thua-lớn là **2 thông tin khác nhau**.)

## 4. VIỆC 4 — TEST RÀO MỚI (a) `≤15 %` VÀ (b) BỎ-TOP-20 % `> 0`

Đo trên cột **`pnl` (USDT)**, `k = ceil(q·n)` leg `pnl` lớn nhất bị bỏ (chốt trước §5).
**Hợp lệ chéo:** `Σ pnl` = `equity_final − equity_start` (khớp **0 USDT** cho `gr-par-kg0`
68 083 = 103 083−35 000; `gr-kg0-q998-15m` 21 149 ≈ 56 148−35 000) ⇒ thang đo tiền tin được.

| biến thể | n | `Σpnl` | **`share top-1 %`** | **(a) ≤15 %** | TF5 | TF10 | **TF20** | **(b) >0** | `q*` | CAGR* |
|---|---|---|---|---|---|---|---|---|---|---|
| `KEEPLEG0` (`gr-par-kg0`) | 1 085 | 68 083 | 23,74 % | **FAIL** | +30 416 | +16 360 | **−1 575** | **FAIL** | 19,0 % | 27,14 % |
| `T100` (`hn-t100`) | 2 559 | 86 770 | 40,85 % | **FAIL** | +2 771 | −31 294 | **−76 850** | **FAIL** | 5,5 % | 31,94 % |
| `GD92` (`hn-g92`) | 2 632 | 98 944 | 37,75 % | **FAIL** | +14 794 | −18 167 | **−61 183** | **FAIL** | 7,0 % | 34,76 % |
| `kg0-q995` (`gr-kg0-q995`) | 1 021 | 64 531 | 21,58 % | **FAIL** | +31 099 | +17 918 | **+772** | **PASS** | 21,0 % | 26,15 % |
| `kg0-q998` (`gr-kg0-q998`) | 954 | 62 674 | 20,70 % | **FAIL** | +32 292 | +19 999 | **+4 180** | **PASS** | 23,5 % | 25,63 % |
| `kg0-q999` (`gr-kg0-q999`) | 868 | 55 699 | 21,04 % | **FAIL** | +28 379 | +17 449 | **+2 901** | **PASS** | 22,5 % | 23,57 % |
| `T170` (`t170-x1-2021`) | 1 089 | 76 070 | 25,90 % | **FAIL** | +32 922 | +17 650 | **−1 723** | **FAIL** | 19,0 % | 29,27 % |
| **`kg0-q998-15m`** | 420 | 21 149 | **12,91 %** | **PASS** | +14 043 | +10 512 | **+5 848** | **PASS** | 38,0 % | **11,08 %** |

\* CAGR từ `result.json` `equity_final` (35 000, 2021-07-01→2025-12-30 = 4,498 năm), **không** từ `pnl`.
**Hợp lệ chéo:** `Σpnl` (cột CSV) = `equity_final − 35 000` cho **cả 8/8** biến thể (khớp 0–1 USDT).

**Trả lời trực tiếp 2 câu hỏi rào:**
- **(a) `%PnL từ top-1 % ≤ 15 %`** ⇒ **1/8 PASS**: `kg0-q998-15m` = **12,91 %**. 7 biến thể còn lại
  **20,70 – 40,85 %** (`T100` 40,85 % tệ nhất; ngay nền tốt nhất `KEEPLEG0` 23,74 % = **vượt rào 1,58 lần**).
- **(b) bỏ top-20 % ⇒ PnL DƯƠNG** ⇒ **4/8 PASS** (`kg0-q995` **+772** · `kg0-q998` **+4 180** ·
  `kg0-q999` **+2 901** · `kg0-q998-15m` **+5 848**). **ÂM cụ thể:** `KEEPLEG0` **−1 575** ·
  `T170` **−1 723** · `GD92` **−61 183** · `T100` **−76 850**.
  ⇒ **Biến thể 1′ nào cũng FAIL (b)** — dự kiến đúng. **NHƯNG** kết luận *"0 biến thể dương ở bỏ-20 %"* là
  **SAI**: 4 biến thể dương (3 trong đó là arm gate-recal siết Q, dương **mỏng** +772…+4 180, `q*` chỉ
  **21,0–23,5 %** ⇒ **vượt rào 20 % chỉ ~1,0–3,5 pp**, rất dễ lật).
- **Theo năm:** rào (b) **không** biến thể 1′ nào dương **cả 5 năm** (đều âm **2025**; `KEEPLEG0` còn âm
  -1 703 ở 2022, `T100` âm 3 năm). **Duy nhất `kg0-q998-15m` DƯƠNG ở CẢ 5 NĂM** khi bỏ-20 %
  (2021 +964 · 2022 +2 032 · 2023 +985 · 2024 +869 · 2025 +1 048). Theo năm, `share top-1%`
  duy nhất `kg0-q998-15m` giữ dưới 20 % mọi năm (8,9–19,3 %).
- **Kiểm độ nhạy (đo trên `profit` % giá thay vì `pnl` USDT):** `share top-1%` giảm ở các nền lớn
  (`T100` 40,85 % → 24,15 %; `GD92` 37,75 % → 22,00 %) nhưng **vẫn FAIL (a)**; TF20 đổi dấu ở biên
  (`T170` −1 723 → **+1 208**, `GD92` −61 183 → −32). ⇒ Kết luận (a)/(b) **ổn định về định tính**;
  riêng `T170`/`GD92` ở (b) là **biên** (đổi dấu theo cách đo) — **phải nói rõ**, không chọn cách đo có lợi.

**Hệ quả go-live:** **KHÔNG cấu hình nào** trong số đo được đủ điều kiện go-live dưới rào mới:
biến thể duy nhất PASS cả (a)+(b) là `kg0-q998-15m`, mà cấu hình này (i) **không tái lập được nhịp live 1′**
(tỷ lệ entry 0,440 < 0,60 → `RESULT_GATE_RECAL.md`), (ii) đã **0/4 arm PASS** ở vòng gate-recal,
(iii) **CAGR 11,08 %/năm vs 27,14 %** của `KEEPLEG0` (−59 % tương đối; PnL cuối kỳ 21 148 vs 68 083 = −69 %). 3 arm `kg0-q99*` PASS (b) nhưng
**FAIL (a)**, và đã **0/5 rate ngoài CI vs cả 2 đối chứng**, `dCAGR −0,99/−1,51/−3,56 pp` (cùng vòng trên).

## 4b. BỔ SUNG — RÀO (b′) **BỎ TOP-50 %** (owner nâng rào 26/09 23:17, `RULERS_CURRENT.md` §8)

| biến thể | n | `Σpnl` | **TF50 (= `Σ nửa dưới`)** | **(b′) >0** | `median leg` | `sign%(pnl>0)` | `TF50` trên `profit` | == nửa dưới? |
|---|---|---|---|---|---|---|---|---|
| `KEEPLEG0` | 1 085 | 68 083 | **−33 196** | **FAIL** | +70,0 | 87,8 % | −971,1 | ✔ |
| `T100` | 2 559 | 86 770 | **−155 919** | **FAIL** | +70,6 | 84,1 % | −5 118,3 | ✔ |
| `GD92` | 2 632 | 98 944 | **−134 390** | **FAIL** | +63,7 | 83,4 % | −4 719,4 | ✔ |
| `kg0-q995` | 1 021 | 64 531 | **−29 512** | **FAIL** | +71,7 | 87,8 % | −764,9 | ✔ |
| `kg0-q998` | 954 | 62 674 | **−24 511** | **FAIL** | +72,5 | 87,8 % | −578,5 | ✔ |
| `kg0-q999` | 868 | 55 699 | **−23 257** | **FAIL** | +74,6 | 87,9 % | −578,1 | ✔ |
| `T170` | 1 089 | 76 070 | **−35 416** | **FAIL** | +74,2 | 88,0 % | −791,5 | ✔ |
| `kg0-q998-15m` | 420 | 21 149 | **−3 357** | **FAIL** | +59,1 | 90,5 % | −5,8 | ✔ |

(Cột cuối cùng = `TF50` đo trên cột `profit` **% giá** thay vì `pnl` **USDT** — **cũng ÂM cả 8** ⇒ kết luận
không phụ thuộc cách đo; `median leg profit` = **+4,5…+5,0 %** dương cả 8, cùng hiện tượng.)

**→ 0/8 PASS. Không biến thể nào (kể cả `kg0-q998-15m`) qua được rào (b′).**

**1) Ý NGHĨA TƯƠNG ĐƯƠNG (đã kiểm bằng số, `tf50_equals_bottom_half = true` 8/8):**
`bỏ top-50 % > 0` ⟺ **`Σ pnl của nửa dưới (floor(n/2) leg nhỏ nhất) > 0`** ⟺ **lãi TRUNG BÌNH/leg của
nửa dưới > 0**. Đây **KHÔNG** phải "median leg > 0" (xem 2).

**2) ⚠️ KHẮC RÕ ĐỂ KHÔNG HIỂU SAI:** `median leg PnL` **> 0 với CẢ 8 biến thể** (+59…+75 USDT,
`sign%(pnl>0)` = 83–91 %) **NHƯNG** `Σ nửa dưới` **< 0 với CẢ 8**. Hai điều kiện **KHÔNG tương đương**.
**Cơ chế (số đo):** luật thoát hiện tại cho **tỷ lệ thắng rất cao** nhưng **mất cân xứng độ lớn**:
`mean pnl/leg | SM` = **+112,5 USDT** vs `mean pnl/leg | SL` = **−369,2 USDT** ⇒ **1 leg lỗ lớn bằng 3,3 leg lãi**
(tỷ số 0,27–0,32 trên cả 8). Vì vậy **nửa dưới (chứa phần lớn leg SL) âm nặng**, dù lệnh **trung vị lãi**.
⇒ **Muốn qua rào (b′), phải sửa MẤT CÂN XỨNG LỚN/THUA (cắt lỗ ngắn hơn hoặc để lãi chạy dài hơn),**
không phải chỉ "có thêm 1 leg lãi nữa".

**3) THEO NĂM (rào b′): DUY NHẤT 3/40 ô dương** — `kg0-q998` 2021 **+325** · `kg0-q999` 2021 **+134** ·
`kg0-q998-15m` 2023 **+214**; **37/40 ô ÂM**. Sâu nhất: `T100` 2025 **−96 186** · `GD92` 2025 **−57 385** ·
`T100` 2024 **−29 579**. **Không** biến thể nào dương **cả 5 năm**. (`median leg` dương ở **mọi** ô.)

**4) KẾT LUẬN BẢN CHẤT (phải ghi rõ):** rào (b′) **đổi bản chất mục tiêu** — từ *"tối ưu hệ thống hiện tại"*
sang *"tìm CẤU TRÚC LÃI không phụ thuộc đuôi"*. Với luật thoát "**arm +7 % → trailing**": lãi đến từ
**% thắng thấp nhưng biên độ lớn trên vài leg** ⇒ **về mặt cấu trúc KHÔNG THỂ thoả** rào (b′) **bất kể
cách tham số hoá** (0/8 ở mọi biến thể, kể cả biến thể siết gate nặng nhất `kg0-q999`). ⇒ **go-live bị CHẶN**
cho tới khi có **nguồn lãi không-đuôi**, đúng như `RULERS_CURRENT.md` §8 đã ghi. Cơ chế thoát đã thoả thuận:
owner **hạ rào** nếu không cấu hình nào ra — **không** tính là thất bại (ghi ở đây để đối chiếu §8).

## 5. VIỆC 5 — ĐỀ XUẤT


**(1) Bộ rate tối thiểu KHÔNG trùng (để *"≥2 rate ngoài CI"* = 2 bằng chứng ĐỘC LẬP):**

| | rate | vai trò | vì sao |
|---|---|---|---|
| 1 | **`TSloss%`** | **tần suất thua** | đại diện nhóm tần suất; giữ nó thay `win%` (kinh tế trực tiếp hơn, `win%` ≈ nó) |
| 2 | **`mP\|SM`** | **độ lớn THẮNG** | độc lập: `|rho|` với `TSloss%` = 0,841/<0,03; với `mP\|SL` = 0,62/0,39 |
| 3 | **`mP\|SL`** | **độ lớn THUA** | độc lập: `|rho|` với `TSloss%` = 0,773/0,180 |
| 4 | **`mMargin`** *(khuyến nghị thêm)* | **quy mô vốn/leg** | không có đồng nhất thức (H4); `|rho|` lớn nhất 0,578/0,454 |

⇒ **Bộ cứng 3 rate = {`TSloss%`, `mP|SM`, `mP|SL`}`** (phủ 3/4 khía cạnh, prereg B4 đạt);
**bộ đủ 4 rate** thêm `mMargin` (phủ 4/4). **Mọi cặp trong bộ có `|rho| < 0,9` ở CẢ Pearson & Spearman
và ở CẢ 6 khối** ⇒ đạt điều kiện B3.
**Luật siết đề xuất:** *"≥2 rate ngoài CI vs cả 2 đối chứng, **trong đó tối đa 1 rate thuộc nhóm tần suất
{`win%`,`TSloss%`}** và **KHÔNG tính `meanP`**"* — nếu không siết, `win%` + `TSloss%` sẽ cho **2 "bằng
chứng"** nhưng thực chất là **1** (`rho = −0,99`).

**(2) Rate bỏ / hạ về BÁO CÁO (không dùng làm cổng):**
- **`meanP`** — **bỏ khỏi cổng** (trùng đại số H3; §7(c) owner đã đồng ý hạ cấp thang mean-based).
- **`win%`** — **hạ về báo cáo** (`rho = −0,99` với `TSloss%`; giữ 1 trong 2).
- **`n`** — **không** là rate chất lượng (quy mô mẫu + mẫu số chung) ⇒ chỉ báo cáo/điều kiện mẫu, không tính vào "≥2 rate".
- **`mP|SM`, `mP|SL`, `mMargin`** — **giữ**, nhưng ghi rõ **mẫu số khác nhau** (`n_SM`, `n_SL`, `n`) ⇒
  khi bootstrap phải resample **theo khối trên cùng bảng leg**, không resample độc lập từng rate.

**(3) Rate TAIL-ROBUST thay thế (tham chiếu `PREREG_TAIL_ROBUST_RULERS.md` §5/§7):**
Thay vai trò *"bằng chứng độ lớn"* (mean-based) bằng họ **không-đuôi**:
- **`median` (R5)** — thay `meanP`/`mP|SM` làm **độ lớn trung tâm** (ưu tiên #1 theo D3 của prereg đó).
- **`sign_frac` (R6)** — thay `win%`/`TSloss%` làm **tần suất** (có **sign test** = CI của tỷ lệ, không bị đuôi chi phối).
- **`loss_mean` (R15)** — thay `mP|SL` làm **độ lớn thua** (downside); **cần thiết nhất** vì nguyên nhân
  FAIL rào (b′) là **mất cân xứng độ lớn thắng/thua** (`|SL|/SM` = **3,3×**), không phải tần suất.
- **`tf_20` (R9)** = rào (b) cũ, **`tf_50` (**mức owner nâng 26/09 23:17**) = rào (b′)**, và
  **`conc_1`/`conc_5` (R10/R11)** = chính **rào (a)** ⇒ cả ba nhóm dùng làm **RÀO**, **KHÔNG** dùng làm bằng chứng.
⚠️ **Chưa kiểm trùng lặp cho họ 17** (`median`/`tmean_1`/`wmean_*` **có thể** gần nhau) — nếu chốt dùng
họ này làm bộ chuẩn thì **phải chạy lại ma trận `rho` y như vòng này** trước khi tin luật "≥2 thước".

## 6. HẠN CHẾ / KHAI BÁO

- **`sel15` / `all15`: KHÔNG có artifact cục bộ** — `/home/ubuntu/kaggle_sim/cd-sel15{,-q998,-q999}` chỉ chứa
  `kernel-metadata.json` + `run.py`, **không có** `storage/printDone.csv` ⇒ **không đo được** (không bịa).
- Khối **B (run×năm)** trộn nhiều nền/cửa sổ khác nhau ⇒ Spearman bị pha loãng; đã báo thêm khối
  **trong-run** (trừ TB theo run) làm thăm dò. **Luật chốt trước giữ nguyên**; phần khối phụ chỉ để giải thích.
- `rho` là **thống kê mô tả trên 448 run không ngẫu nhiên hoá** (các run là biến thể do người chọn) ⇒
  **không** suy ra p-value/nhân quả; chỉ dùng để phát hiện **trùng lặp** như đã chốt trước.
- Đo trên **`pnl` USDT** là chính (đồng nhất `RESULT_FRAGILITY_N`); bản `profit` chỉ là **kiểm độ nhạy**.
- Vòng này **không** đụng `P32`/pool Kaggle của phiên `PREREG_TAIL_ROBUST_RULERS.md`.
