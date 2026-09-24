# F4 — Tầng TIMING có phải là nơi chứa alpha không?

Phép đo **OFFLINE thuần**. Không chạy Java sim, không chạy VAL, không GPU.
Pre-reg `docs/prereg/PREREG_F4.md` commit **`1fa042d`** (chốt trước khi đo, không sửa sau).
Script `research/analysis/f4_timing.py`. Log `/home/ubuntu/F4_RUN.out`.

## Trả lời một câu

**NULL trên cuộc thi — nhưng là null KHÔNG CÓ POWER, không phải null loại trừ được hiệu ứng.**
Lưới tick 87,552 quan sát chỉ cho `n_eff ≈ 900` sau khi tính tương quan chuỗi (khối 72h),
`sd_boot ≈ 0.033` chứ không phải 0.0034 ⇒ **MDE80 của HIỆU |rank-IC| ≈ 0.13**. Ứng viên mạnh
nhất (`br_lag3`) hơn incumbent +0.055 — **dưới MDE, không phân biệt được**. `p15` giữ nguyên
vì không ai đánh bại được, **không phải vì `p15` đã được chứng minh là tốt nhất.**

Điều đo được có dấu rõ: tầng timing **có** tín hiệu (`p15` rank-IC `+0.100`, CI loại trừ 0), gate
**có** chọn lọc thật (`mean(Y|MỞ) − mean(Y|ĐÓNG)` = `+0.0224` / `+0.0727` theo hai định nghĩa),
**đồng thời** khối tick trên-trung-vị nằm NGOÀI gate lớn gấp **12.67×** (Gate-A) / **83.98×**
(Gate-B) khối nằm trong. Cả hai đúng cùng lúc — đây là bài toán **đặt ngưỡng**, không phải bài
toán **chọn biến**.

## 0. Pre-reg đã chốt gì (tóm tắt, bản đầy đủ ở `PREREG_F4.md`)

| mục | đã chốt trước |
|---|---|
| đơn vị | tick 15m, lưới lịch DEV `2022-01-01 → 2024-06-30` |
| `Y_tick` PRIMARY | `mean(g1lite)` của top-8 theo `score_g015` tăng dần |
| secondary | `P(maxFav_72h>=0.07)` top-8; `mean(g1lite)` top-3 — **không dùng để chọn** |
| ứng viên | ĐÚNG 5: `p15`, `br_lag3`, `mkt_vol7`, `mkt_dd7`, `p15_ma24h` |
| thống kê | `S_v = |rank-IC|`; CI = moving-block 72h (288 tick), 2000 rep, seed 20260905, ×`f=1.21` |
| ngưỡng | ĐÁNH BẠI ⟺ (a) CI95 của `S_v − S_p15` cận dưới > 0 **VÀ** (b) dấu nhất quán 2022/23/24 |
| model | ĐÚNG MỘT: XGBRegressor CPU, 5 biến, WFO quý, purge 72h, seed 42 |

Pre-reg cũng ghi trước hai cảnh báo — **cả hai đều đúng**:
1. `cand_dev.parquet` chỉ có **4,639/87,552** tick DEV ⇒ phải dựng lại lưới mở rộng.
2. `SE = 0.0034` của đề bài là iid ⇒ quá lạc quan; block bootstrap là trọng tài.

## 1. Lưới tick mở rộng — dựng lại và kiểm chứng

Dựng từ đúng 3 nguồn gốc mà `ledger.py` dùng, không đổi định nghĩa nào:
`wfo_gate_pred.csv` (p15) + `predwf_G015x26` (p_g015) + `label_15m/*.pb` (nhãn, `nBars_72h>=288`),
`dyn_thr` đọc từ `research/analysis/gate_cfg.py` (không hardcode).

| đại lượng | giá trị |
|---|---|
| tick lưới lịch DEV | **87,552** (liên tục, thiếu 0) |
| tick có ≥1 pred G015 | 87,547 (99.994%) |
| **tick có `Y_tick`** | **86,971** (99.34%) |
| tick bị loại vì < 8 coin | **0** (`ncoin` med 166, min 10) |
| coin/tick trung vị theo quý | 129 (2022Q1) → 258 (2024Q2) |
| `Y_tick` | mean `+0.0576`, sd `0.1216`, p50 `+0.0445` |
| Gate-A mở (`p15>=0.008`) | **4,595** |
| Gate-B mở (`npass>=1`) | **469** |

**Kiểm chứng ngược với F3:** F3 đo trên `cand_dev` được **4,595** tick có `score_g015` và
**465** tick có ≥1 `gate_dyn_ok`. Lưới mở rộng cho **4,595** và **469**. Khớp tuyệt đối ở con số
thứ nhất, lệch **4 tick (0.86%)** ở con số thứ hai — nhiều khả năng do khác biệt nhỏ ở bộ lọc
nhãn giữa hai lần dựng. **Ghi lại, không giấu**; không đủ lớn để đổi kết luận nào bên dưới.

## 2. Kết quả PRIMARY — bảng rank-IC 5 ứng viên

`n = 86,615` tick (99.6% panel; mất 356 tick do `br_lag3` NaN đầu chuỗi) ⇒ **300 khối 72h**.

| ứng viên | rank-IC | `|IC|` | CI95(`|IC|`) ×1.21 | `sd_boot` | IC 2022 | IC 2023 | IC 2024 | dấu |
|---|---|---|---|---|---|---|---|---|
| `p15` *(incumbent)* | **+0.1000** | 0.1000 | [+0.0213, +0.1796] | 0.0332 | +0.1622 | +0.0785 | +0.2579 | **OK** |
| `br_lag3` | **+0.1553** | 0.1553 | [+0.0762, +0.2367] | 0.0337 | +0.1357 | +0.1404 | +0.2454 | **OK** |
| `p15_ma24h` | +0.1088 | 0.1088 | [+0.0158, +0.2033] | 0.0390 | +0.1637 | +0.0856 | +0.3417 | **OK** |
| `mkt_vol7` | +0.0901 | 0.0901 | [−0.0033, +0.1853] | 0.0398 | +0.1302 | +0.0741 | +0.2051 | OK |
| `mkt_dd7` | +0.0186 | 0.0186 | [−0.0021, +0.1084] | 0.0256 | **−0.0850** | +0.0308 | +0.0804 | **LỆCH** |

Ba biến (`p15`, `br_lag3`, `p15_ma24h`) có CI loại trừ 0 ⇒ **tầng timing có tín hiệu thật**.
`mkt_vol7` sát 0 ở cận dưới, `mkt_dd7` không loại trừ 0 và **đổi dấu ở 2022**.

### Hiệu so với incumbent — phán quyết theo đúng ngưỡng §4 pre-reg

Cùng 2000 rep, **common random numbers**.

| ứng viên | `d = |IC| − |IC_p15|` | CI95(d) ×1.21 | `P(d>0)` | dấu | **PHÁN QUYẾT** |
|---|---|---|---|---|---|
| `br_lag3` | **+0.0553** | **[−0.0347, +0.1450]** | 0.930 | OK | **KHÔNG** |
| `p15_ma24h` | +0.0088 | [−0.0118, +0.0306] | 0.843 | OK | **KHÔNG** |
| `mkt_vol7` | −0.0098 | [−0.0823, +0.0528] | 0.327 | OK | **KHÔNG** |
| `mkt_dd7` | −0.0813 | [−0.1579, +0.0596] | 0.080 | LỆCH | **KHÔNG** |

> **PHÁN QUYẾT PRIMARY: NULL. Không ứng viên nào đạt đồng thời (a) và (b). `p15` GIỮ NGUYÊN.**

### Vì sao null này KHÔNG mạnh — con số phải đọc trước mọi diễn giải

`sd_boot` của HIỆU (suy từ độ rộng CI, đã ×1.21) ≈ **0.046** cho `br_lag3`
⇒ **MDE80 = 2.802 × 0.046 ≈ 0.128**. Hiệu quan sát `+0.055` **chỉ bằng 43% MDE**.

Nói cách khác: thiết kế này **không thể** phát hiện một ứng viên tốt hơn `p15` một lượng nhỏ hơn
0.13 `|rank-IC|` — và 0.13 lớn hơn chính rank-IC của `p15` (0.100). **Cuộc thi đã được chốt với
một ngưỡng mà gần như không ứng viên thực tế nào vượt nổi.** Đây là lỗi thiết kế của F4, ghi ra
đây để không lặp lại; nó không cho phép sửa ngưỡng sau khi thấy số.

`n_eff` suy từ `sd_boot`: `1/0.0332² ≈ 908`, so với `n = 86,615` ⇒ **hệ số phóng đại 95×**.
Con số `1/sqrt(87,600) = 0.0034` trong giả thuyết ban đầu **sai gấp ~10 lần**.

## 3. Chẩn đoán `br_lag4` — một phần ưu thế của breadth là RÒ RỈ

`br_lag3` (= `br.shift(3)`, cột có sẵn của `GATE_BREADTH_DAILY.csv`) còn rò rỉ tối đa ~1 ngày:
`br` của ngày `D` là nhãn nhìn 72h nên cửa sổ đóng tại `D+4`, mà lag chỉ 3. Pre-reg §3.1 khai báo
trước biến sạch `br_lag4` (`br` của ngày `D'` cuối cùng thoả `D'+4 ngày <= t`) làm **chẩn đoán,
không dự thi**. `n = 86,519`.

| biến | rank-IC | CI95 ×1.21 | 2022 | 2023 | 2024 | `d` so với `p15` |
|---|---|---|---|---|---|---|
| `p15` | +0.1014 | [+0.0231, +0.1829] | +0.1644 | +0.0785 | +0.2579 | — |
| `br_lag3` (dự thi) | **+0.1567** | [+0.0762, +0.2369] | +0.1383 | +0.1404 | +0.2454 | +0.0553 [−0.0405,+0.1419] |
| `br_lag4` (sạch) | **+0.0973** | [+0.0088, +0.1920] | **+0.0305** | +0.1008 | +0.2416 | −0.0041 [−0.0959,+0.0831] |

**38% rank-IC của `br_lag3` biến mất khi bịt rò rỉ** (0.1567 → 0.0973), và 2022 sụt
`+0.1383 → +0.0305` (−78%). Sau khi bịt, breadth **thấp hơn** `p15`.

⇒ Ứng viên duy nhất nhìn có vẻ khá hơn incumbent là ứng viên **duy nhất còn rò rỉ**.
`AUDIT_APPLIED` B8 ("breadth TB 7d lag3, IC +0.30") phải đọc kèm cảnh báo này: con số +0.30 đo
với **target tương lai** `tgt`, không phải `Y_tick`, và trên biến chưa bịt rò rỉ.

## 4. Secondary (báo cáo, KHÔNG dùng để chọn)

`Y2 = P(maxFav_72h >= 0.07)` của top-8:

| biến | rank-IC | 2022 | 2023 | 2024 | `d` so `p15` | CI95(d) ×1.21 |
|---|---|---|---|---|---|---|
| `p15` | +0.1932 | +0.2705 | +0.1729 | +0.2159 | — | — |
| `p15_ma24h` | +0.2089 | +0.2779 | +0.1863 | +0.3021 | +0.0157 | [−0.0040, +0.0349] |
| `mkt_vol7` | +0.2032 | +0.2791 | +0.1767 | +0.2006 | +0.0100 | [−0.0537, +0.0648] |
| `br_lag3` | +0.1775 | +0.1952 | +0.1681 | +0.1506 | −0.0158 | [−0.0948, +0.0649] |
| `mkt_dd7` | −0.0659 | −0.1488 | −0.0252 | −0.0295 | **−0.1274** | **[−0.2138, −0.0444]** |

`Y3 = mean(g1lite)` top-3: `p15` +0.0697, `br_lag3` +0.1323, `p15_ma24h` +0.0709,
`mkt_vol7` +0.0575, `mkt_dd7` +0.0315 (LỆCH). `d(br_lag3)` = +0.0626 [−0.0182, +0.1429].

Hai điểm đáng ghi:
- **`mkt_dd7` là ứng viên DUY NHẤT bị loại dứt khoát**: trên `Y2`, CI của hiệu **nằm trọn dưới 0**
  ⇒ kém `p15` một cách phân biệt được, cộng với dấu lệch trên `Y_tick` và `Y3`. Đóng biến này.
- Trên `Y2`, `p15` mạnh hơn hẳn so với trên `Y_tick` (0.193 vs 0.100). Timing dự báo **xác suất
  CHẠM +7%** tốt hơn dự báo **độ lớn g1lite** — nhất quán với `E0_EXIT_CF`/`F3` (biến động nằm ở
  đuôi, và `maxFav>=0.07` là ngưỡng ARM chứ không phải ngưỡng THẮNG).

## 5. FALSE NEGATIVE — cả hai định nghĩa gate, không chọn một

`F3_SUPPLY` giới hạn 3: `gate_dyn_ok` offline tái lập **61.5%** giờ-entry thật;
`p15>=0.008` tái lập **92.2%**. Vì vậy báo cả hai.

| | **Gate-A** `p15>=0.008` (92.2%) | **Gate-B** `npass>=1` (61.5%) |
|---|---|---|
| tick MỞ | 4,595 (5.28%) | 469 (0.54%) |
| tick ĐÓNG | 82,376 (94.72%) | 86,502 (99.46%) |
| `median(Y|MỞ)` = mốc `m` | +0.07309 | +0.11116 |
| `mean(Y|MỞ)` | +0.07883 | +0.12989 |
| `mean(Y|ĐÓNG)` | +0.05643 | +0.05722 |
| chênh mean | **+0.02240** | **+0.07267** |
| `P(good)` top-8 MỞ / ĐÓNG | 0.6688 / 0.5440 | 0.7820 / 0.5493 |
| `Y3` top-3 MỞ / ĐÓNG | +0.09439 / +0.07485 | +0.14707 / +0.07549 |
| KS `D` | 0.1589 | 0.3014 |
| **`q = P(Y|ĐÓNG > m)`** | **0.3534** | **0.2277** |
| **khối lượng bỏ lỡ = `q × n_ĐÓNG`** | **29,115 tick** | **19,694 tick** |
| mốc so `0.5 × n_MỞ` | 2,298 | 234 |
| **tỷ số** | **12.67×** | **83.98×** |

Phân vị `Y_tick`:

| | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| Gate-A MỞ | −0.0537 | +0.0199 | +0.0731 | +0.1374 | +0.2195 |
| Gate-A ĐÓNG | −0.0541 | −0.0061 | +0.0428 | +0.1021 | +0.1786 |
| Gate-B MỞ | −0.0230 | +0.0523 | +0.1112 | +0.2079 | +0.2919 |
| Gate-B ĐÓNG | −0.0542 | −0.0055 | +0.0442 | +0.1035 | +0.1804 |

### Đọc đúng hai con số này

1. **Gate CÓ chọn lọc, và siết chặt hơn thì chọn tốt hơn.** `q` giảm đơn điệu 0.500 (ngẫu nhiên)
   → 0.353 (A) → 0.228 (B); chênh mean tăng +0.022 → +0.073; `P(good)` tăng 0.669 → 0.782.
   Đây **bác** cách đọc "gate chỉ là bộ lọc ngẫu nhiên".
2. **Đồng thời, khối lượng cơ hội trên-trung-vị nằm ngoài gate lớn hơn trong gate 12.7× / 84×** —
   thuần tuý vì tập ĐÓNG lớn gấp 18× (A) / 184× (B). Gate đánh đổi **độ chính xác lấy độ phủ**,
   và tỷ lệ đánh đổi hiện tại cực kỳ lệch về phía độ chính xác.
3. **Điểm mù ở đuôi trên:** p90 của nhóm ĐÓNG Gate-A (+0.1786) **cao hơn** p75 của nhóm MỞ
   (+0.1374). Không phải mọi thứ ngoài gate đều xấu.

### Ba cảnh báo bắt buộc trước khi ai đó dùng con số 29,115

- **Đếm TICK, không đếm cơ hội độc lập.** Nhãn nhìn 72h ⇒ 288 tick liên tiếp dùng chung cửa sổ.
  Số "đợt" độc lập nhiều nhất chỉ cỡ `29,115/288 ≈ 101`. Con số 29,115 là **thể tích lưới**,
  không phải số lệnh có thể vào.
- **`Y_tick` là danh mục KHÔNG giao dịch được.** Nó giả định lấy top-8 ở MỌI tick (96 tick/ngày,
  chồng lấn hoàn toàn), trong khi hệ thật giữ cap 8 vị thế và time-stop 168h. `F3` đã đo: trong
  giờ-gate-mở hệ đã giữ **6.275** vị thế — gần cap. Mở gate rộng hơn **không** tự động biến các
  tick này thành lệnh.
- **Không có xác nhận P&L.** `g1lite` là proxy đường trailing, không phải lời/lỗ, không trừ phí,
  không mô hình hoá margin. Diễn giải P&L ở mục này bị pre-reg CẤM và ở đây không có.

## 6. Model tổ hợp — đúng một model đã khai báo, và nó THUA

XGBRegressor `device="cpu"`, `tree_method="hist"`, 5 biến, WFO 9 quý test, purge 72h hai phía,
`random_state=42`, `n_estimators=300 max_depth=4 lr=0.05 subsample=0.8 colsample=0.8`.
OOS = **78,331 tick** (90.4%).

| | rank-IC OOS | CI95 ×1.21 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| **model** (5 biến) | **+0.0866** | [+0.0137, +0.1610] | +0.0412 | +0.0738 | +0.0488 |
| `p15` (cùng 78,331 tick) | **+0.1297** | [+0.0549, +0.2075] | +0.1814 | +0.0785 | +0.2579 |

`d = |IC_model| − |IC_p15| = −0.0431`, CI95 ×1.21 `[−0.1503, +0.0610]`, `P(d>0) = 0.160`
⇒ **KHÔNG đánh bại. Model kém hơn chính biến đơn `p15` mà nó chứa.**

Cơ chế: `n_eff ≈ 900` cho 5 feature × 300 cây — tỷ lệ tham số/thông tin quá cao. Điểm số ổn định
hơn theo năm (0.041/0.074/0.049) nhưng thấp hơn ở mọi năm, tức model **trơn hoá mất tín hiệu**
chứ không phải chỉ overfit ồn.

> Hệ quả trực tiếp: **thêm feature vào tầng timing không phải hướng đi.** Với `n_eff ≈ 900`,
> mọi model tổ hợp sẽ gặp đúng bức tường này.

## 7. Bốn dự đoán ghi trước — ĐÚNG 2, SAI 2. Ghi rõ.

| # | dự đoán (pre-reg §8) | thực tế | |
|---|---|---|---|
| 1 | `p15` sẽ có rank-IC **lớn nhất** trong 5 | `br_lag3` +0.1553 và `p15_ma24h` +0.1088 đều **cao hơn** `p15` +0.1000 | **SAI** |
| 1b | *không ứng viên nào đạt cả (a) và (b)* | đúng, không ai đạt | ĐÚNG |
| 2 | `p15_ma24h` **thấp hơn** `p15` (tín hiệu là mức tức thời) | **cao hơn** +0.0088 — nhưng CI [−0.012,+0.031] ⇒ không phân biệt được | **SAI** (yếu) |
| 3 | `q` ở Gate-A sẽ **> 0.40** | `q = 0.3534` | **SAI** |
| 4 | CI sẽ **rộng hơn 0.0034 rất nhiều** | `sd_boot` 0.026–0.040, gấp ~10× | **ĐÚNG** |

Lý do dự đoán 1 và 2 sai, ghi để lần sau không lặp: tôi giả định `p15` — biến mà gate đang bind —
phải là biến dự báo mạnh nhất cho kết quả top-8. Hai chuyện đó khác nhau: `p15` được HPO để chọn
**điểm vào**, không được tối ưu để **xếp hạng chất lượng tick**. Dự đoán 3 sai theo hướng có lợi
cho gate: gate chọn lọc tốt hơn tôi nghĩ.

## 8. Giới hạn của phép đo

1. **Power không đủ cho cuộc thi, và điều này biết được TRƯỚC khi biết kết quả nhưng chỉ định
   lượng được SAU.** MDE80 của hiệu ≈ 0.128 trong khi rank-IC của incumbent chỉ 0.100. Null của
   §2 **không loại trừ** một ứng viên tốt hơn `p15` tới +0.12 `|IC|`. Đây là giới hạn nặng nhất.
2. **`n_eff ≈ 908` chứ không phải 86,615.** Giả thuyết "tick-level phá tường power" của F4 **SAI**.
   Tường power vẫn ở đó, chỉ đổi mặt: từ 970 lệnh sang ~300 khối 72h độc lập.
3. **`Y_tick` không giao dịch được** (§5). Mọi rank-IC ở đây là IC với một **proxy chất lượng
   tick**, không phải với P&L. `g1lite` không trừ phí, không mô hình margin/cap/time-stop.
4. **Rank-IC của 5 biến thô là IN-SAMPLE mô tả**, không phải out-of-sample — chúng không có tham
   số ước lượng nên không overfit theo nghĩa thông thường, nhưng danh sách 5 biến **do người chọn
   sau khi đã nhìn F3**. Chỉ số OOS thật duy nhất trong tài liệu này là của model (§6).
5. **`br_lag3` còn rò rỉ ~1 ngày** (§3), đã định lượng: 38% rank-IC của nó là rò rỉ.
6. **Lệch 4 tick (469 vs 465) so với F3** ở Gate-B chưa truy nguyên (§1).
7. **`gate_dyn_ok` offline vẫn chỉ tái lập 61.5% giờ-entry thật** (`F3` giới hạn 3). Mọi con số
   Gate-B mang sai số hệ thống chưa định lượng được. Đó là lý do bắt buộc báo cả Gate-A.
8. **2021 không dùng được làm hold-out** — `predwf_G015x26` không có bins trước `20220101`
   (pre-reg §1.3 đã ghi trước). F4 **không có hold-out nào**.
9. **`predwf_G015x26` không reproduce được** (`AGENT_RUNBOOK` §5). `score_g015` — thứ định nghĩa
   top-8 và do đó định nghĩa `Y_tick` — là single point of failure không tái lập.
10. **Không chạy sim ⇒ không có xác nhận P&L cho bất kỳ con số nào.**

## 9. HỆ QUẢ — roadmap tiếp theo

### Cái gì ĐÓNG lại

- **Đóng "thay biến gate".** 4 ứng viên đều KHÔNG; ứng viên khá nhất mất 38% ưu thế khi bịt rò rỉ
  và khi đó **thấp hơn** `p15`. Không có cơ sở đổi biến bind của gate.
- **Đóng `mkt_dd7`** — bị loại dứt khoát trên `Y2` (CI của hiệu nằm trọn dưới 0) + dấu lệch.
- **Đóng "thêm feature / model tổ hợp cho tầng timing".** Model 5-biến đã khai báo THUA biến đơn
  `p15` OOS (−0.043). Với `n_eff ≈ 900` đây là tường, không phải vấn đề chọn feature.
- **Đóng luôn giả thuyết "chuyển sang mức tick sẽ có power".** Đây là kết quả có giá trị nhất của
  F4: nó **xoá một lối thoát mà 3 task trước đều mặc định là còn mở**. Mọi thiết kế tương lai ở
  mức tick phải tính `n_eff` bằng block bootstrap **trong pre-reg**, trước khi chốt ngưỡng.

### Cái gì MỞ — theo thứ tự ưu tiên

1. **Sweep ngưỡng `p15` (không phải đổi biến `p15`).** F3 chỉ ra `p15` là trục cung binding duy
   nhất và nói "cần build lại ledger với ngưỡng lỏng hơn — chưa pre-reg, chưa chạy". **Lưới đó
   giờ đã có**: `/home/ubuntu/ledger/f4_ticks.parquet` (86,971 tick, đủ `p15`/`Y`/`npass`/`ncoin`).
   §5 cho thấy đánh đổi precision/coverage hiện cực lệch (`q` 0.353 tại 5.28% độ phủ) ⇒ câu hỏi
   "ngưỡng 0.008 đặt đúng chỗ chưa" giờ **đo được offline, chi phí gần bằng 0**.
   **Cảnh báo cứng:** tiêu chí KHÔNG được là equity (`RUNBOOK` §0.3), và phải chốt trước rằng
   `q < 0.5` ở mọi ngưỡng nghĩa là **mọi** lần nới đều pha loãng — nên tiêu chí phải là một
   đánh đổi được viết thành công thức trước, không phải "chọn ngưỡng đẹp nhất sau khi thấy đường
   cong". Nếu không viết được công thức đó thì **đừng chạy**.
2. **Đóng khe K=8 (sim) vs K=5 (live)** — `Q6.4`. F3 đã định lượng 33.5% nguồn cung good. Đây là
   **fidelity**, không sinh alpha, không cần sim run, và là nợ kỹ thuật duy nhất đang làm 970 lệnh
   của DEV không phải tập lệnh live sẽ vào.
3. **Pin `predwf_G015x26` + pipeline S1 vào git** (`AUDIT_APPLIED` mục ưu tiên 1). F4 vừa thêm một
   lý do: `Y_tick` — nền của toàn bộ tài liệu này — phụ thuộc vào bins không reproduce được.
4. **Nếu vẫn muốn đo tầng timing:** đơn vị phải cho `n_eff` lớn hơn, không phải `n` lớn hơn. Hai
   đường khả dĩ, cả hai đều cần pre-reg riêng: (a) mở rộng cửa sổ thời gian thay vì làm mịn lưới —
   `n_eff` tỷ lệ với **số khối 72h**, tức với **độ dài lịch sử**, không với tần suất lấy mẫu;
   (b) đổi outcome sang đại lượng ít tự tương quan hơn 72h. Làm mịn lưới lên 1 phút sẽ cho
   `n = 1.3M` và **cùng `n_eff ≈ 900`** — bẫy này phải ghi vào `AGENT_RUNBOOK`.

### Một dòng cho `AGENT_RUNBOOK` §4

> **Tick-level KHÔNG phá được tường power.** F4: `n = 86,615` tick ⇒ `n_eff ≈ 908`
> (`sd_boot(rank-IC) = 0.033`, khối 72h). MDE80 của hiệu `|rank-IC|` ≈ 0.13 > chính rank-IC của
> incumbent (0.100). `n_eff` tỷ lệ với **số khối 72h**, tức với độ dài lịch sử — không với tần
> suất lấy mẫu. Mọi pre-reg mức tick phải tính `n_eff` bằng block bootstrap TRƯỚC khi chốt ngưỡng.
