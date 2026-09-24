# F3 — Hệ bị giới hạn bởi NGUỒN CUNG hay bởi TẦNG QUYẾT ĐỊNH?

Phép đo **OFFLINE thuần** trên `ledger/cand_dev.parquet` (1,220,490 dòng) +
`devrun/C2b/storage/printDone.csv` (970 lệnh). Không chạy Java, không train, không sửa
code sim. Script: `research/analysis/f3_supply.py`.

## Trả lời một câu

**Bị giới hạn bởi CUNG — nhưng trục cung khan hiếm là THỜI GIAN gate thị trường mở
(biến mức-tick `p15`), KHÔNG phải universe.** Universe không đo được là đòn bẩy (mục A
không khử được confound; mục A7 null trên kết quả thực), và về **cơ chế** universe không
thể tạo thêm tick gate mở vì `p15` là scalar toàn thị trường. Trong ~200 giờ thực sự có
cơ hội thì cap `SELECTOR_RANK_TOPK=8` mới là ràng buộc binding — nhưng F1 đã chứng minh
nới cap đó làm Sharpe giảm 34%.

## 0. Ngữ cảnh nguồn dữ liệu (bắt buộc đọc trước khi dùng số)

`ledger.py:28` — pool CHỈ tồn tại ở tick 15m mà **gate thị trường mở** (`p15 >= 0.008`).
`ledger.py:42` — `gate_dyn_ok = p15 >= dyn_thr(score_g015)`.

| đại lượng | giá trị |
|---|---|
| dòng / tick 15m / coin unique | 1,220,490 / 8,642 / 289 |
| giờ có gate mở / giờ lịch | 3,847 / 28,346 = **13.57%** |
| `P(maxFav_72h >= 0.07)` toàn pool | **0.6054** |
| `gate_dyn_ok` toàn pool | 0.0252 |
| có `score_g015` (2021 không có G015) | 0.6344 |

⚠️ **"good" = `maxFav_72h >= 0.07` là ngưỡng ARM, không phải ngưỡng THẮNG.** 60.5% ứng
viên chạm +7% — đây không phải biến cố hiếm. `E0_EXIT_CF`: nhóm chết là nhóm **không bao
giờ chạy**. Mọi con số "cơ hội tốt" dưới đây phải đọc với ràng buộc này.

## A. Đường cung theo universe — **KHÔNG KẾT LUẬN ĐƯỢC**

Đơn vị = **giờ có gate mở**; `U`/`N_good` đếm **coin distinct** trong giờ (không đếm lại
coin xuất hiện ở nhiều tick). `N_good` = coin có `maxFav_72h >= 0.07`.

Mốc theo năm (bảng tháng đầy đủ trong log của script):

| năm | giờ | U | N_good/giờ | N_pass/giờ | N_good&gate/giờ | % giờ có good&gate |
|---|---|---|---|---|---|---|
| 2021 | 1,695 | 111.2 | 73.5 | — (không có G015) | — | — |
| 2022 | 1,272 | 133.3 | 75.6 | 7.20 | 5.63 | 10.1% |
| 2023 | 328 | 178.9 | 90.4 | 5.05 | 3.40 | 7.6% |
| 2024 | 552 | 252.4 | 149.7 | 7.81 | 5.25 | 8.0% |

### Hồi quy `log(N_good/giờ) ~ log(U)`

| spec | dốc | CI95 | R² | n | MDE80 |
|---|---|---|---|---|---|
| A1 thô, 2021-04..2024-06 | **+0.679** | [+0.244, +1.114] | 0.208 | 40 | 0.60 |
| A1 thô, DEV 2022-01..2024-06 | **+1.117** | [+0.501, +1.732] | 0.330 | 30 | 0.84 |
| A4 **+ year FE**, full | +0.334 | [−0.941, +1.608] | 0.397 | 40 | **1.76** |
| A4 **+ year FE**, 2022+ | +0.435 | [−1.210, +2.079] | 0.401 | 30 | **2.24** |
| A6 ô (năm × decile U theo giờ) | +0.545 | [−0.248, +1.338] | 0.667 | 40 | **1.09** |
| A6b `log P(good) ~ log U` + yearFE | −0.455 | [−1.248, +0.338] | 0.228 | 40 | 1.09 |
| A5 within-year 2021 | −0.115 | [−0.901, +0.670] | 0.014 | 10 | 0.95 |
| A5 within-year 2022 | −5.087 | [−11.97, +1.80] | 0.213 | 12 | 8.66 |
| A5 within-year 2023 | +0.749 | [−1.529, +3.027] | 0.051 | 12 | 2.86 |
| A5 within-year 2024 | −0.508 | [−8.190, +7.175] | 0.008 | 6 | 7.75 |

### Confound KHÔNG khử được

`spearman(U, thứ tự tháng) = +0.995` (p=1.7e-40). U gần như là một hàm đơn điệu của thời
gian: 2021 U∈[101,127], 2022 [128,142], 2023 [141,229], 2024 [235,259] — bốn khối gần
như rời nhau, biến thiên trong-năm rất nhỏ (2022 spread/median = 0.10; 2024 = 0.09).

⇒ Dốc thô +0.68/+1.12 **là tác động của NĂM đội lốt universe**. Mọi spec có khử confound
đều có **MDE80 ≥ 1.09**, tức không phân biệt nổi dốc 0 với dốc 1. **Kết luận A: không
kết luận được** — dữ liệu DEV không đủ để trả lời câu hỏi này bằng hồi quy tổng lượng.

## A7. Thống kê thứ tự — test thay thế cho A, có kết luận

Câu hỏi mà A định trả lời viết lại ở dạng đo được: *universe to hơn có làm **top-8 tốt
lên** không?* Đo ở mức TICK (không cần chuẩn hoá thời gian), ô (năm × decile U), year FE,
n = 30 ô, 4,595 tick.

| đại lượng của top-8 | elasticity theo `log(U)` | CI95 | t | MDE80 |
|---|---|---|---|---|
| `mean(score_g015)` (thấp = tốt) | **−0.325** | [−0.461, −0.189] | −4.92 | 0.19 |
| `score` của rank-1 | **−0.324** | [−0.452, −0.195] | −5.18 | 0.18 |
| `mean(g1lite)` | +0.032 | [−0.156, +0.221] | +0.35 | 0.26 |
| `P(maxFav >= 0.07)` | −0.066 | [−0.498, +0.366] | −0.31 | 0.59 |

**Universe to hơn cải thiện ĐIỂM DỰ BÁO của top-8 đúng như thống kê thứ tự dự đoán
(t ≈ −5), nhưng KHÔNG cải thiện KẾT QUẢ THỰC của top-8 (null trên cả `g1lite` lẫn
`P(good)`).** Hai hồi quy dùng chung một thiết kế và chung một confound; một cái động
mạnh, một cái đứng yên ⇒ so sánh nội bộ này bền hơn từng hồi quy riêng lẻ.

Cơ chế: điểm mỏng dần ở đuôi trên không đủ thông tin để lợi thế thứ tự chuyển thành lợi
thế kết quả. Đây là **bằng chứng chống** giả thuyết "mở universe cho thêm lệnh rank-nông
tốt". Cảnh báo: nhận dạng chủ yếu đến từ trong-2023 (U 141→229, 510 tick); MDE80 trên
`g1lite` = 0.26 nên hiệu ứng dương nhỏ vẫn có thể bị bỏ sót.

## G. Chặn động thời gian — gate thị trường là biến MỨC TICK

`sd(p15)` trong tick = **0** ⇒ `p15` là scalar toàn thị trường, **universe không thể đổi
được nó**. Chỉ **465 / 4,595 tick có score (10.12%)** có ≥1 coin qua `gate_dyn_ok`.

| decile `p15` | p15 | U TB | pass/tick | % tick có ≥1 pass | pass_rate |
|---|---|---|---|---|---|
| 0 | 0.0081 | 180.7 | 0.02 | 0.2% | 0.0001 |
| 4 | 0.0090 | 173.6 | 0.31 | 0.9% | 0.0018 |
| 7 | 0.0111 | 158.4 | 2.09 | 7.4% | 0.0132 |
| 8 | 0.0128 | 151.2 | 7.71 | 20.9% | 0.0510 |
| 9 | 0.0196 | 153.9 | **54.76** | **63.5%** | **0.3558** |

`spearman(npass, p15) = +0.454` vs `spearman(npass, U) = +0.021`. Số cơ hội được nhận vào
do **regime** quyết định, không do universe. U thậm chí **giảm** ở decile p15 cao.

## B. Chất lượng theo độ sâu rank (POOL, n = 774,268 dòng / 4,595 tick, 2022+)

Rank trong từng tick theo `score_g015` tăng dần (thấp = tốt, `ledger.py:55`).

### B1 — toàn pool

| bin rank | n | P(good) | mean g1lite | mean g1lite\|good | med g1lite\|good | mean maxFav\|good | gate_ok |
|---|---|---|---|---|---|---|---|
| 1-2 | 9,190 | **0.6985** | 0.0975 | **0.1778** | 0.0939 | 0.2469 | 0.0955 |
| 3-5 | 13,785 | 0.6730 | 0.0785 | 0.1566 | 0.0831 | 0.2247 | 0.0818 |
| 6-8 | 13,785 | 0.6449 | 0.0667 | 0.1445 | 0.0801 | 0.2122 | 0.0743 |
| 9-16 | 36,760 | 0.6316 | 0.0588 | 0.1344 | 0.0769 | 0.2013 | 0.0676 |
| 17-32 | 73,520 | 0.6134 | 0.0511 | 0.1246 | 0.0750 | 0.1911 | 0.0593 |
| >32 | 627,228 | **0.5646** | 0.0396 | **0.1070** | 0.0682 | 0.1713 | 0.0333 |

### B2 — chỉ dòng QUA `gate_dyn_ok` (tập sim thực sự có thể vào)

| bin rank | n | P(good) | mean g1lite | mean g1lite\|good | med g1lite\|good |
|---|---|---|---|---|---|
| 1-2 | 878 | 0.7973 | 0.1494 | 0.2101 | 0.1259 |
| 3-5 | 1,128 | 0.7952 | 0.1291 | 0.1820 | 0.1125 |
| 6-8 | 1,024 | 0.7871 | 0.1273 | 0.1809 | 0.1188 |
| 9-16 | 2,485 | 0.7899 | 0.1154 | 0.1645 | 0.1073 |
| 17-32 | 4,359 | 0.7839 | 0.1102 | 0.1576 | 0.1052 |
| >32 | 20,874 | 0.7456 | 0.1011 | 0.1534 | 0.1009 |

### Trả lời câu hỏi của B

**KHÔNG. Chất lượng khi thắng KHÔNG phải hằng số theo độ sâu — cả hai kênh cùng suy
giảm đơn điệu.** Welch t-test (bin 1-2 làm mốc):

- `mean(g1lite | good)`: 0.1778 → 0.1566 (t=5.5) → 0.1445 (t=9.2) → 0.1344 (t=14.3) →
  0.1246 (t=18.2) → 0.1070 (t=24.8, p=1e-129).
- `P(good)`: 0.6985 → 0.6730 → 0.6449 → 0.6316 → 0.6134 → 0.5646 (t=27.7, p=9e-163).

Đối chiếu F1: `medP` = 5.50 bất biến ở cả 4 run. Trên pool, **median** khi thắng đúng là
đại lượng ít nhạy nhất — chỉ giảm 0.1259 → 0.1009 (−20%) trên dải sâu gấp 30 lần, và trên
tập qua-gate thì bin 6-8 (0.1188) còn cao hơn bin 3-5 (0.1125). Vậy `medP` bất biến của
F1 là **tính trơ của median**, không phải bằng chứng chất lượng-khi-thắng bất biến. Mean
và `P(good)` đều nói ngược lại.

## C. Trần cung — bao nhiêu cơ hội tốt bị bỏ lỡ mỗi giờ

Tính trên 3,847 **giờ có gate mở** (86.4% giờ lịch không có một ứng viên nào).

| | mean | p50 | p90 | max | % giờ > 0 |
|---|---|---|---|---|---|
| `N_good`/giờ (coin distinct) | **86.56** | 87 | 141 | 258 | 99.97% |
| `N_good & gate_dyn_ok`/giờ | **2.90** | **0** | **0** | 257 | **5.15%** |
| entries thật (C2b)/giờ | 0.231 | 0 | 0 | — | 5.22% |

**Cơ hội tốt bỏ lỡ / giờ-gate-mở = 86.33** theo định nghĩa "chạm +7%", **= 2.67** nếu bắt
buộc qua `gate_dyn_ok`. Con số thứ hai mới là upside khả thi, và nó **cực lệch**: 94.85%
giờ-gate-mở có **0** cơ hội qua gate; trong 198 giờ có cơ hội thì trung bình **56.4**
coin/giờ. Toàn DEV: 888 entry / 11,175 coin-giờ good&gate = **chiếm dụng 7.95%**.

Vị thế đang giữ (từ 970 lệnh thật):

| phạm vi | vị thế TB | % giờ rỗng |
|---|---|---|
| mọi giờ trong cửa sổ lệnh (n=21,630) | **1.894** | 61.8% |
| chỉ giờ-gate-mở (n=2,146) | **6.275** | 33.5% |

⇒ **"Trung bình 1.83 vị thế / 62.5% giờ rỗng" là hiện tượng của giờ GATE ĐÓNG.** Khi gate
mở, hệ đã giữ 6.3 vị thế — gần cap. Vốn không nằm không lúc có cơ hội.

Ràng buộc binding trong giờ có cơ hội là **cap K=8/tick**: tick có ≥1 pass trung bình có
**66.1** coin qua gate (p50 = 47, `P(>8) = 0.710`), tức ~58 coin/tick mà cap không bao giờ
nhìn tới. Nhưng F1 đã kiểm đúng việc nới cap này (K=8→16/24/32): `sd(daily)` giảm đúng dự
đoán, `mean(daily)` giảm gấp 3 lần thế, Sharpe 1.491→0.980, cả 3 biến thể LOẠI ở ràng buộc
cứng. **Cap binding nhưng nới nó là lỗ** — nhất quán với mục B (chất lượng giảm theo độ sâu).

Theo bin universe (không thấy quan hệ đơn điệu giữa U và `% giờ có good&gate`):

| U bin | giờ | U | N_good/h | N_good&gate/h | % giờ có good&gate |
|---|---|---|---|---|---|
| (100,125] | 1,519 | 109.4 | 73.8 | 0.00 | 0.0% |
| (125,150] | 1,513 | 133.0 | 75.7 | 4.79 | 8.7% |
| (150,175] | 107 | 161.3 | 80.6 | 1.30 | 4.7% |
| (175,200] | 61 | 184.5 | 61.0 | 5.85 | 14.8% |
| (200,250] | 225 | 231.6 | 137.2 | 4.81 | 5.8% |
| >250 | 422 | 256.1 | 149.6 | 5.57 | 9.5% |

## D. Khe K=8 (sim) vs K=5 (live) — định lượng

| | toàn pool | chỉ dòng qua `gate_dyn_ok` |
|---|---|---|
| slot top-5 / top-8 | 22,975 / 36,760 | 2,006 / 3,030 |
| slot rank 6-8 (% của top-8) | 37.5% | 33.8% |
| `N_good` top-5 / top-8 | 15,696 / 24,586 | 1,597 / 2,403 |
| **good mất khi hạ về K=5** | **8,890 = 36.16%** | **806 = 33.54%** |
| `P(good)`: top-5 / rank 6-8 | 0.6832 / 0.6449 | 0.7961 / 0.7871 |
| tổng `g1lite` rank 6-8 (% của top-8) | 31.7% | **32.0%** |
| `mean(g1lite)`: top-5 / rank 6-8 | 0.0861 / 0.0667 (**−22.5%**) | 0.1380 / 0.1273 (**−7.7%**) |

**Live K=5 nhìn thấy ít hơn sim K=8 khoảng một phần ba nguồn cung good qua gate (33.5%) và
32.0% khối lượng `g1lite`.** Slot 6-8 kém hơn slot 1-5 theo mọi thước đo, nhưng chỉ kém
7.7% trên `mean(g1lite)` ở tập qua-gate.

⚠️ **Đây là độ LỚN của khe, KHÔNG phải dấu P&L.** F1 cho thấy đi sâu hơn K=8 làm Sharpe
giảm; ngoại suy ngược (K=5 nông hơn ⇒ tốt hơn) là hợp lý về hướng nhưng **chưa được kiểm**.
Điều chắc chắn: **970 lệnh của sim KHÔNG phải tập lệnh live sẽ vào** — 1/3 nguồn cung good
mà sim tính đến thì live không bao giờ nhìn tới. Đây là **lỗ hổng FIDELITY**, và nó vẫn
đang mở (`AGENT_RUNBOOK §5`, `QUEUE Q6.4`).

## Giới hạn của phép đo

1. **`good = maxFav_72h >= 0.07` là ngưỡng ARM, không phải ngưỡng THẮNG.** P = 60.5% toàn
   pool ⇒ không hiếm. `E0_EXIT_CF`: nhóm chết là nhóm không bao giờ chạy, và hạ ngưỡng arm
   KHÔNG cứu được. Con số "86.33 cơ hội bỏ lỡ/giờ" **không dịch thẳng thành tiền**.
2. **Mục A không khử được confound.** `spearman(U, tháng) = +0.995`; mọi spec khử confound
   có MDE80 ≥ 1.09 ⇒ không phân biệt được dốc 0 với dốc 1. Báo cáo là **không kết luận
   được**, không phải "dốc ≈ 0.5". Mục A7 là đường vòng, không phải thay thế tương đương.
3. **`gate_dyn_ok` offline không tái lập được gate của sim.** 92.2% giờ-entry thật nằm
   trong giờ gate-mở của ledger (`p15 >= 0.008` — tốt), nhưng chỉ **61.5%** nằm trong giờ
   có `gate_dyn_ok` pass. Mọi số điều kiện trên `gate_dyn_ok` (C, D cột phải) là **chỉ báo,
   không phải tái lập**. Con số 2.67 và 33.54% mang sai số hệ thống chưa định lượng được.
4. `cand_dev` chỉ chứa tick gate mở ⇒ **không đo được gì về giờ gate đóng** ngoài việc
   chúng không có ứng viên. Không kiểm được giả thuyết "nới `p15 >= 0.008` thì sao".
5. 2021 không có `predwf_G015x26` ⇒ B, A7, D chỉ trên 2022+ (774,268 dòng / 4,595 tick).
6. `U` = số coin **có label** tại tick, không phải universe niêm yết. Pool DEV có 289 coin
   unique, U tối đa 260 — trong khi VAL là 563 coin/giờ. **Ngoại suy A/A7 sang VAL là ngoài
   miền dữ liệu.**
7. **`n_eff` nhỏ hơn `n` rất nhiều.** Các tick trong cùng giờ/ngày tương quan mạnh; t-test
   mục B coi mỗi dòng độc lập ⇒ p-value bị phóng đại. Tin **hướng và tính đơn điệu**, không
   tin độ lớn của t.
8. Không chạy sim ⇒ **không có xác nhận P&L cho bất kỳ con số nào ở đây.** Mọi phát biểu về
   lời/lỗ đều dựa vào F1/F2/E1 đã chạy trước.

## Hệ quả cho hàng đợi

- **Đóng hướng "mở universe".** A không kết luận được; A7 null trên kết quả thực trong khi
  điểm dự báo cải thiện rõ; G cho thấy universe không đụng được tới `p15` — biến quyết
  định số cơ hội được nhận vào. Ba mảnh này không đủ để **loại** giả thuyết, nhưng đủ để
  nói **không có bằng chứng nào ủng hộ nó**, và chi phí kiểm (sửa selector + universe
  probe) không được biện minh. Ghi vào B9/A4 (`AUDIT_APPLIED`, `PHASE1_DECISION_SURFACE`).
- **Không làm thêm can thiệp tầng quyết định exit/flow.** E1, F1, F2 đều null; F3 giải
  thích tại sao: trong 94.85% giờ-gate-mở không có gì để tái triển khai vốn vào, nên mọi
  cơ chế "giải phóng margin sớm để quay vòng" đều không có đích đến (F2: tổng lệnh 970 →
  1,003, +3.4%).
- **Khe K=8/K=5 đáng đóng vì FIDELITY, không phải vì alpha.** 33.5% nguồn cung good của sim
  không tồn tại với live. Đây là nợ kỹ thuật `Q6.4`, chi phí thấp, không cần sim run mới.
- **Câu hỏi còn mở, chưa ai kiểm:** nới `p15 >= 0.008` (số giờ gate mở) là trục cung DUY
  NHẤT mà phép đo này chỉ ra là binding. `cand_dev` không chứa dữ liệu để trả lời — cần
  build lại ledger với ngưỡng lỏng hơn. **Chưa pre-reg, chưa chạy.**
