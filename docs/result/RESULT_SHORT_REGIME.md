# RESULT_SHORT_REGIME — SHORT + TÍN HIỆU REGIME THẬT (0-sim) ⇒ **NULL**

Ngày: **2026-10-01**, branch `module`. Pre-reg: `docs/prereg/PREREG_SHORT_REGIME.md` (**`0cbc4c2b`**, TRƯỚC đo).
Code: `research/analysis/short_regime_0sim.py`. Số: `docs/result/RESULT_SHORT_REGIME.json`.
Nền: `RESULT_SHORT_PATHEXIT_PSOFT` (`05169026`).

**Tuân thủ:** 0-sim (KHÔNG chạy sim 1m vì cắt đuôi KHÔNG rõ) · không `.java`/ONNX/242/LIVE ·
không push dữ liệu · DEV ≤ 2025-12-31 · chỉ `git add` file của mình.

---

## 0. KẾT LUẬN NGẮN

> **NULL.** Regime "DOWN" tự dựng từ giá **KHÔNG cắt được cái đuôi** (SL-rate baseline **20,6 %** →
> R1 20,7 · R2 21,1 · R3 21,0 · R5 **24,3** %; chỉ R4-drawdown 18,8 %, tức **−1,8 pp** — xa ngưỡng
> `≤0,6×`). Net **âm ở mọi biến thể**, **ngoài CI phía âm**, **0/4 năm dương**; `tail(max_loss)`
> **không đổi** (−10,7 %). ⇒ **không đủ điều kiện chạy sim 1m**; **chốt đóng hướng short**.

## 1. PHƯƠNG PHÁP + ⚠️ CAVEAT PROXY (quan trọng để đọc số)

- Pick = **`PA_t15_E10_S42`** top-8/tick (bins Kaggle `sm-pathexit`; P-soft `sm-pw` không có bản local
  ⇒ dùng P-hard proxy). 1 106 753 pick khớp nhãn.
- Thoát = **LABEL-exit TP −1,5 % / SL +10 %** trên nhãn `.pb` (first-hit **xấp xỉ**).
- ⚠️ **Proxy lệch:** baseline SL-rate của proxy = **20,6 %**, còn **sim 1m thật = 11,4–11,6 %** — vì `.pb`
  chỉ có **cực trị + thời điểm cực trị** (ambig 39,5 %), **không đủ xác định first-hit** (đã ghi ở
  `RESULT_SHORT_PATHEXIT` §1). ⇒ **net tuyệt đối bị lệch âm; chỉ dùng để SO SÁNH TƯƠNG ĐỐI giữa regime.**
- ⚠️ **Funding-aggregate BỎ** ở 0-sim (không có nguồn funding toàn-sàn DEV rẻ local) — ghi rõ theo pre-reg §3.

## 2. KẾT QUẢ (net %/lệnh, sau fee 0,112 % + funding pro-rata; CI95 block-72h)

| biến thể (DOWN) | n | frac | **SL-rate** | net | CI95 | ngoài 0 | win | tail | năm dương |
|---|---|---|---|---|---|---|---|---|---|
| *(baseline, không lọc)* | 1 106 753 | 1,000 | **20,6 %** | −1,30 | [−1,39; −1,21] | CÓ (âm) | 78,5 % | −10,7 % | 0/4 |
| R1 BTC-trend (SMA200&ret30<0) | 347 531 | 0,314 | 20,7 % | −1,31 | [−1,48; −1,15] | CÓ (âm) | 78,2 % | −10,7 % | 0/4 |
| R2 breadth<0,40 | 563 833 | 0,509 | 21,1 % | −1,35 | [−1,48; −1,23] | CÓ (âm) | 78,0 % | −10,7 % | 0/4 |
| R3 trend & breadth<0,50 | 306 613 | 0,277 | 21,0 % | −1,35 | [−1,52; −1,18] | CÓ (âm) | 77,9 % | −10,7 % | 0/4 |
| **R4 drawdown <−20 % (90d)** | 306 982 | 0,277 | **18,8 %** | **−1,13** | [−1,33; −0,96] | CÓ (âm) | 79,7 % | −10,7 % | 0/4 |
| R5 trend & vol>median | 153 716 | 0,139 | **24,3 %** | −1,67 | [−1,90; −1,45] | CÓ (âm) | 75,3 % | −10,7 % | 0/4 |

Theo năm (net %): baseline −0,70 / −1,01 / −1,23 / −2,26 (2022→2025). R4: −0,71 / **−2,01** / −0,96 / −2,46
⇒ 2023 **xấu hơn** baseline ở R4; không biến thể nào lật dấu năm.

## 3. TRẢ LỜI (a–e)

- **(a) Cắt được bao nhiêu % đuôi?** Gần **như không**: SL-rate chỉ giảm ở **R4** (20,6 %→18,8 %, −1,8 pp);
  R1/R2/R3 ~ **không đổi**, **R5 TỆ HƠN** (24,3 %). ⇒ **< ngưỡng** `≤ 0,6×` (cần ≤ 12,4 %).
- **(b) net sau fee+funding?** **Âm mọi biến thể** −1,13 … −1,67 %/lệnh (đã tính fee 0,112 % + funding pro-rata).
- **(c) CI95?** Mọi biến thể **ngoài 0 phía ÂM** (raw); **không** biến thể nào dương.
- **(d) theo năm 2022–2025?** **0/4 năm dương** ở mọi biến thể; 2023 đặc biệt xấu ở R4 (−2,01 %).
- **(e) > 0 & ngoài CI?** **KHÔNG** (ngoài CI nhưng **phía âm**).
- **Overfit?** Không có biến thể nào "đẹp" ⇒ không phải overfit; kết quả **nhất quán NO-GO/NULL**.

## 4. QUYẾT ĐỊNH

**NULL — chốt đóng hướng short** (theo pre-reg §4: cắt đuôi KHÔNG rõ ⇒ KHÔNG chạy sim 1m).
Lý do gốc không đổi: **biên gross của pick quá nhỏ so fee+funding**, và **đuôi SL đến từ đuôi tăng
(idiosyncratic) của từng coin, KHÔNG phải từ regime thị trường** — nên lọc regime (vốn chỉ đổi
*thời điểm*, không đổi *coin*) không chạm được đuôi. Muốn cắt đuôi phải can thiệp **chọn coin / thoát
sớm hơn** (đã đo ở `RESULT_SHORT_PATHEXIT*` — cũng không cứu được).

> Muốn mở lại: cần **DATA MỚI** (liquidation / L2 / fill thật) — không phải thêm biến thể regime.
