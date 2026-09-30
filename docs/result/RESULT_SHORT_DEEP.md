# RESULT_SHORT_DEEP — đào sâu model SHORT: 2023/2024 âm vì gì · cơ chế cắt · funding · ngưỡng label

Ngày: **2026-10-01**. Pre-reg: `docs/prereg/PREREG_SHORT_DEEP.md` (**`676263e4`**, commit TRƯỚC đo).
Script: `research/analysis/short_model_deep.py`. Số: `docs/result/RESULT_SHORT_DEEP.json`.
Nền: `RESULT_SHORT_MODEL.md` (`a3b59757`) = `NO-GO/NULL` (A PASS, B FAIL).

**Tuân thủ:** 0-sim · **không** Java/sim trên Oracle · **không** sửa `.java` · **không** chạm
production/242/ONNX/LIVE · **không push file dữ liệu** · DEV ≤ 2025-12-31 (mọi nguồn lọc `< 2026-01-01`).
Train CHỈ trên Kaggle (`sm-train-gpu` cho arm chính `t*=0,015`; `sm-thr-sweep` cho quét ngưỡng).
Funding = Aerospike `test.funding_data` (read-only), quy ước khoá `RESULT_FUNDING_SIGN`: `rate>0` ⇒ short NHẬN.

---

## 0. KẾT LUẬN NGẮN (đọc cái này là đủ)

**`NO-GO/NULL`** theo luật §7. **A PASS** (rank-IC `+0,0519`, 3/3 seed ngoài CI raw & ×1,21).
**B2 FAIL**: không tồn tại `(t,M)` cho net(K8) > 0 **ngoài CI** + **≥3/4 năm dương** + **đã credit funding**.
Điểm chết = **2023** (Q1) **cộng** funding âm trên short (−0,34 %/72h ở 2023).

**Phát hiện mới quan trọng:** **funding của short ở đây là CHI PHÍ, không phải lợi thế.** Model short
nhắm đúng nhóm coin đang giảm ⇒ đó là nhóm **short đông** ⇒ `rate < 0` ⇒ **short TRẢ** tiền funding
(mean `−0,45…−0,58 %/72h`). Credit funding **lật dấu** net: `+0,41 %` → `−0,17 %` (cắt cứng +30 %).

---

## 1. LUẬT §7 — áp cơ học

| # | điều kiện | kết quả |
|---|---|---|
| **A** | rank-IC `t*=0,015` > 0 & ngoài CI (raw & ×1,21), mean-seed | **PASS** — `+0,051874`; SHORT42 `+0,051873`, SHORT7 `+0,050884`, SHORT13 `+0,052866`; cả 3 seed `out_both` |
| **B2** | tồn tại `(t,M)`: net(K8)>0 **ngoài CI** + **≥3/4 năm dương** + **credit funding** | **FAIL** — xem §3/§4 |
| | | **⇒ `NO-GO/NULL`** |

- **Chưa credit funding**: net điểm ước lượng **dương** ở mọi cắt cứng (`none` +0,34 %, `+20 %` +0,42 %,
  `+30 %` +0,41 %) **NHƯNG CI raw chứa 0** và **chỉ 2/4 năm dương** (2022, 2025) ⇒ đã FAIL B2 ở vế "ngoài CI".
- **Đã credit funding**: net **ÂM** ở mọi cơ chế (`hard +30 %` = `−0,17 %`, `none` = `−0,24 %`) ⇒ FAIL nặng hơn.
- **"2023 sửa được?" KHÔNG.** Không `(t,M)` nào làm 2023 ≥ 0 & 2024 ≥ 0. 2023 là **điểm chết của hướng short** ở DEV.

---

## 2. TRẢ LỜI CÂU HỎI 1 — **2023/2024 ÂM VÌ GÌ**

Bóc tách (SHORT13, đại diện; 3 seed nhất quán). Net = per-tick mean − phí 0,112 %/vòng.

| năm | gross (không cắt) | net (không cắt) | phí | **funding** | net `+30 %` | nhận xét |
|---|---|---|---|---|---|---|
| 2023 | **−0,12 %** | −0,23 % | −0,11 % | **−0,34 %** | −0,59 % | tín hiệu âm nhẹ + funding âm nặng |
| 2024 | **−0,14 %** | −0,25 % | −0,11 % | −0,11 % | −0,11 % | tín hiệu âm nhẹ + funding âm nhẹ |

**Theo quý** (net, không cắt): 2023 `Q1 −1,81 % · Q2 +1,21 % · Q3 +0,58 % · Q4 −0,94 %`
2024 `Q1 −1,76 % · Q2 +1,61 % · Q3 +0,14 % · Q4 −1,02 %`. ⇒ **mất gần hết ở Q1 cả hai năm**.

**Theo regime** (proxy = median `retEnd_72h` thị trường theo tick; BTC không có trong nhãn):
2023 regime **tăng** net `−4,53 %/lệnh` (n=144k) vs **giảm** `+4,31 %/lệnh` (n=136k);
2024 **tăng** `−6,53 %` vs **giảm** `+5,74 %`. ⇒ short **chỉ thắng khi thị trường giảm**, thua đậm khi tăng.

**Theo coin** (đóng góp âm, mean %/lệnh): 2023 `IOTA −19,5 %` (217), `CAKE −17,2 %` (21), `USTC −14,4 %`
(167), `INJ −11,1 %` (767), `ETHW −10,7 %` (252). 2024 `PNUT −129,7 %` (151), `AIXBT −24,8 %`,
`1000SHIB −24,3 %` (1341), `VIRTUAL −18,5 %`, `RARE −17,4 %`.

**Theo entry-type** (bucket `maxFav_72h` = mức coin đã TĂNG = bất lợi cho short):
2023 `<5 % −… ` no-cut `+5,37 %` · `5–10 % +0,50 %` · `10–20 % −4,41 %` · `20–30 % −10,92 %` · `≥30 % −23,63 %`.
2024 `<5 % +9,45 %` · `5–10 % +3,65 %` · `10–20 % −2,67 %` · `20–30 % −10,46 %` · `≥30 % −32,16 %`.

**Kết luận câu 1:** âm do **TÍN HIỆU/REGIME** (chọn coin rồi coin vẫn tăng — Q1 năm nào cũng vậy; đuôi
"coin tăng ≥10 %" là nơi lỗ), **KHÔNG do phí** (phí chỉ 0,11 %). Cắt cứng **không cứu được** (2023 vẫn −0,59 %),
vì phần lớn lệnh lỗ **không chạm ngưỡng cắt**. **Funding là áp lực LỚN NHẤT ở 2023** (−0,34 %).

---

## 3. TRẢ LỜI CÂU HỎI 2 — **CƠ CHẾ CẮT NÀO TỐT NHẤT**

Mean-seed, `t*=0,015`, K=8/tick. `outCI` = net ngoài CI raw. `funded` = đã credit funding (§4).

| cơ chế | net (chưa fund) | outCI | by-year (22/23/24/25) | funded (raw / clip) |
|---|---|---|---|---|
| không cắt | **+0,34 %** | ✗ | +1,23 / −0,25 / −0,31 / +0,70 | **−0,24 %** / −0,11 % |
| cắt cứng **+20 %** | **+0,42 %** | ✗ | +1,19 / −0,62 / +0,02 / +1,10 | −0,16 % / −0,03 % |
| cắt cứng **+30 %** | **+0,41 %** | ✗ | +1,17 / −0,59 / −0,11 / +1,18 | −0,17 % / −0,04 % |
| cắt cứng +40 % | +0,36 % | ✗ | +1,12 / −0,53 / −0,20 / +1,06 | −0,22 % / −0,09 % |
| cắt cứng +50 % | +0,34 % | ✗ | +1,13 / −0,54 / −0,22 / +1,01 | −0,24 % / −0,11 % |
| cắt cứng +70 % | +0,29 % | ✗ | +1,12 / −0,47 / −0,27 / +0,81 | −0,28 % / −0,15 % |
| cắt cứng +90 % | +0,27 % | ✗ | +1,11 / −0,40 / −0,31 / +0,67 | −0,32 % / −0,18 % |
| **mềm 2 tầng (0,20→0,40)** | **−1,99 %** | ✓ (âm) | −0,24 / −2,11 / −2,39 / −3,19 | −2,57 % |
| mềm 2 tầng (0,30→0,50) | −1,03 % | ✓ (âm) | +0,42 / −1,32 / −1,44 / −1,76 | −1,61 % |
| time-stop 12 h | +0,03 % | ✗ | +0,04 / −0,08 / −0,14 / +0,30 | −0,13 % |
| time-stop 24 h | +0,08 % | ✗ | +0,21 / −0,12 / −0,20 / +0,44 | −0,20 % |
| time-stop 24 h + cắt +30 % | +0,11 % | ✗ | +0,27 / −0,22 / −0,15 / +0,56 | −0,15 % |
| **UB lookahead** 0,10 (cận trên) | +0,45 % | ✗ | +1,03 / **+0,14** / +0,26 / +0,36 | — |
| **UB lookahead** 0,20 (cận trên) | +0,46 % | ✗ | +1,13 / −0,06 / +0,11 / +0,64 | — |

- **Tốt nhất (net + đuôi trái) = cắt cứng +20…+30 %** (`+0,42 / +0,41 %`): chặn đuôi (`max lỗ` từ
  `−1499 %` → `−30 %`), **nhưng** net vẫn CI chứa 0 & 2023 vẫn âm.
- **Cắt MỀM 2 tầng KHÔNG hơn** — **tệ nhất** (−1,0…−2,0 %, ngoài CI âm): mức thoát trung bình `−(S+C)/2`
  bị áp cho ĐA SỐ lệnh (không chỉ đuôi). **Time-stop 12/24 h cũng KHÔNG hơn** cắt cứng (net +0,03…+0,08 %).
- **UB lookahead** (BỎ-theo-pre-reg, chỉ để định vị tiềm năng, nhãn `UB/lookahead`) cho thấy nếu thoát
  được **đúng lúc coin giảm ≥10 %** thì 2023 mới **≥0** ⇒ tiềm năng nằm ở **exit rule đường giá**, không
  phải ở tín hiệu vào lệnh. Muốn khai thác phải có sim đường giá (ngoài §1.2).

---

## 4. TRẢ LỜI CÂU HỎI 3 — **FUNDING LÀM NET ĐỔI BAO NHIÊU**

Cửa sổ `(t_entry, t_entry+72h]`, đơn vị %/notional; short NHẬN khi `rate>0`.

| đại lượng (SHORT13; 3 seed khớp trong ±0,01 pp) | giá trị |
|---|---|
| % lệnh **NHẬN** / **TRẢ** | **62,6 %** / **36,6 %** |
| mean `f_pp` (raw) | **−0,585 %** ⇒ short **TRẢ** ròng |
| mean `f_pp` (clip trần `|rate|≤0,0075`/kỳ) | **−0,452 %** |
| median `f_pp` | **+0,055 %** (đa số nhận ít) |
| p01 / p99 | **−13,1 %** / +0,90 % (đuôi TRẢ rất nặng) |

- **Đổi net:** `none` `+0,34 %` → `−0,24 %`; `hard +30 %` `+0,41 %` → `−0,17 %` (clip `−0,04 %`).
  Tức funding **đổi dấu** kết luận kinh tế. Theo năm (funded, mean-seed): 2022 `+0,98…+0,99 %`,
  **2023 `−0,94 %`**, **2024 `−0,22 %`**, **2025 `−0,49 %`** ⇒ **3/4 năm âm** sau funding.
- **Có phải LỢI THẾ không? KHÔNG — là CHI PHÍ.** Vì tín hiệu short nhắm đúng nhóm coin đang giảm
  (nhóm **short đông**, `rate<0`). Đây là nghịch lý cấu trúc của "short theo đà giảm".
- **Caveat dữ liệu:** đuôi TRẢ nặng (p01 −13 %) một phần do bản ghi funding lặp/giá trị cũ cho vài coin
  (vd `XEMUSDT` cùng một tổng qua nhiều mốc liền nhau). Đã báo **song song bản CLIP**; kết luận dấu
  (short TRẢ) **không đổi**. Borrow = 0 (PERP). Liquidation KHÔNG mô hình (số short vẫn là cận trên lạc quan).

---

## 5. TRẢ LỜI CÂU HỎI 4 — **QUÉT NGƯỠNG LABEL**

- **Arm huấn luyện (khoá trong pre-reg §3):** kernel `chuyendinh/sm-thr-sweep` đã **push + ĐANG CHẠY**
  (start `2026-09-30 20:06 UTC`), train 9 arm `t ∈ {0,010,0,030,0,050} × seed {42,7,13}` + chấm in-kernel.
  ETA ~6–7 h ⇒ **chưa có kết quả trong vòng này**. Đây là **việc dở dang**, không được thay bằng suy đoán.
- **Proxy offline (KHÔNG phải arm train lại — nhãn rõ):** dùng **NGUYÊN** model `t*=0,015`, đo IC phân
  biệt `y_t = 1[retEnd_72h ≤ −t]` (mean-seed):

| `t` | 0,010 | 0,015 | 0,030 | 0,050 |
|---|---|---|---|---|
| IC (mean-seed) | 0,0469 | 0,0540 | 0,0721 | **0,0881** |
| base rate | 0,476 | 0,449 | 0,371 | 0,282 |

⇒ Cùng một score **xếp hạng cú giảm CÀNG MẠNH càng tốt** (IC tăng đơn điệu theo ngưỡng). NHƯNG net của
K8 short **không phụ thuộc `t`** với cùng score; muốn biết ngưỡng nào cho **net** tốt hơn **phải chờ** 9 arm
train thật. ⇒ Không kết luận ngưỡng nào tốt nhất từ proxy.

---

## 6. ĐỐI CHIẾU LONG (bất đối xứng)

LONG42 (bin có sẵn): rank-IC **−0,0213** (đối xứng kém 2,4×); K8 long net **−0,009 %** (≈0); by-year
`2022 −0,99 % · 2023 +0,72 % · 2024 +0,39 % · 2025 −0,17 %`. ⇒ Hai hướng đều **không có lợi thế ròng**;
short chỉ "trông dương" khi **chưa** tính funding.

---

## 7. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Trailing theo **đường giá** (+ UB lookahead chỉ để định vị) | ⛔ BỎ (đúng pre-reg §4) | aggregate `.pb` không có path; cần sim Java đường giá |
| 2 | Liquidation / margin call | ⛔ BỎ | không mô hình được từ dữ liệu hiện có |
| 3 | Borrow spot cho short | ⛔ BỎ | PERP ⇒ borrow = 0 |
| 4 | Đổi feature/hyperparam/fold/K | ⛔ BỎ | giữ nguyên để so với vòng trước |
| 5 | Gate-33 / S1-9 train riêng | ⛔ BỎ | như vòng trước |
| 6 | Horizon 4h/12h/24h làm arm quyết định | ⛔ BỎ | h=72h khoá; 12/24 h chỉ dùng cho time-stop |
| 7 | **Time-stop 48 h** | ⚠️ KHÔNG ĐO ĐƯỢC | nhãn `.pb` chỉ có `4h/12h/24h/72h`, **không có 48h** ⇒ báo là lỗ hổng, không bịa |
| 8 | 9 arm quét ngưỡng label | ⏳ ĐANG CHẠY (`sm-thr-sweep`) | ETA ~6–7 h; proxy ở §5 là chẩn đoán offline, không thay thế |

---

## 8. SẢN PHẨM

- `research/analysis/short_model_deep.py` — chấm sâu 0-sim (cắt cứng/mềm/time-stop/UB + funding + phân rã).
- `docs/result/RESULT_SHORT_DEEP.md` · `docs/result/RESULT_SHORT_DEEP.json`.
- Kernel: `chuyendinh/sm-train-gpu` (arm chính, đã xong) · `chuyendinh/sm-thr-sweep` (quét ngưỡng, đang chạy).
- Theo pre-reg §7: **`NO-GO/NULL`** ⇒ **KHÔNG** dựng đường SELL; **KHÔNG** build production.
