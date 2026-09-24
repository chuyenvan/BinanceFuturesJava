# PREREG_TAIL_LEVER — ĐÒN BẨY ĐÚNG: CHẶN `gross exposure` / TRAP ALT cắt được bao nhiêu đuôi rủi ro, giá bao nhiêu lãi

Chốt **TRƯỚC khi đo** (2026-09-24). Thuần **Python offline trên Oracle**, **KHÔNG** Java/sim,
**KHÔNG** claude-run, **KHÔNG push**, DEV only (mọi mốc `<= 2025-12-30`, **không đọc 2026**).
Script: `research/analysis/tail_lever.py`. Kết quả: `docs/result/RESULT_TAIL_LEVER.md`.

## 0. Động cơ (số đã đo — KHÔNG diễn giải lại)

`docs/result/RESULT_INTRADAY_DD.md` (commit `ea6bf11`) + `docs/runbooks/RISK_APPETITE.md` §7.3:

- `maxDD` THẬT (MTM mốc phút) = **T170 −19.96% · KEEPLEG0 −19.96% · T100 −26.26% · GD92 −24.30%**
  (chuỗi ngày −11.84 / −11.21 / −16.13 / −16.55).
- Cửa sổ **2025-10-09..13**: MTM **−19.57…−20.70%**, chuỗi ngày **0.00%**; trough cả 4 nền =
  `2025-10-10 21:20Z`.
- **8/10 cú giảm intraday sâu nhất là HỆ THỐNG** (coin xấu nhất chỉ 9–18% độ sâu, 13–30 coin mở
  cùng lúc) ⇒ nghi vấn: rủi ro đuôi đến từ **exposure tổng**, không từ 1 coin.
- `margin/(quantity*entry) = 1.0000` trên **toàn bộ leg** của 4 nền ⇒ **1x isolated**, `margin`
  CHÍNH LÀ **notional** ⇒ `Σ margin` leg đang mở = **gross exposure** đo được từ artifact.
- Max concurrent margin (đo lại lượt này, tie-break theo thứ tự leg): **T170 52,151 · KEEPLEG0
  48,070 · T100 66,748 · GD92 62,981 USDT** ⇒ **~47–57% equity** lúc đó.
  ⇒ Trần `G = 20/30/40/50%` **binding thật**, không phải trần danh nghĩa.

⇒ Câu hỏi trung tâm: **chặn `gross exposure` / trap khi ALT sập cắt được bao nhiêu độ sâu, và giá
phải trả bao nhiêu lãi**. Đây là đòn bẩy **đúng** — **KHÔNG** phải số lệnh, **KHÔNG** phải exit.

## 1. Câu hỏi chốt trước + NGƯỠNG QUYẾT ĐỊNH chốt trước

**(A)** Trong cửa sổ `2025-10-09..13` và 10 cú giảm intraday sâu nhất (toàn kỳ, mỗi nền), độ sâu
chia thế nào giữa **(i) 1 coin · (ii) top-3 coin · (iii) phần còn lại (= thị trường)**?

**(B)** Trần `Σ margin mở <= G% equity`, `G ∈ {20, 30, 40, 50}%`, so với **KHÔNG trần**: cắt được
bao nhiêu độ sâu (intraday maxDD, worst-window drop 11/10), mất bao nhiêu lãi (PnL, CAGR), và `n`,
`UW`, `#leg bị chặn` đổi thế nào — **cho cả 4 nền**.

**(C)** Luật trap ALT (2 luật, chốt trước) chặn vào lệnh mới: cắt được bao nhiêu % độ sâu của 11/10,
mất bao nhiêu PnL, **kích hoạt bao nhiêu lần trên toàn kỳ (2021-07..2025-12)** ⇒ có đáng không, hay
chỉ cắt đúng lúc tốt nhất?

### 1.1 Ngưỡng quyết định (chốt TRƯỚC, không sửa sau khi thấy số)

Đọc bằng **THUỐC ĐUÔI** (`intraday maxDD` mốc phút, `worst-window drop` của 2025-10-09..13) —
**KHÔNG** dùng rate trung bình / Sharpe / số lệnh ngon.

| mục | gọi là | ngưỡng chốt trước |
|---|---|---|
| A | **rủi ro HỆ THỐNG** | top-1 coin `< 25%` độ sâu **VÀ** top-3 `< 50%` (phần còn lại `>= 50%`), trên `>= 7/10` cú của `>= 3/4` nền |
| A | **1 coin** (idiosyncratic) | top-1 `> 50%` độ sâu |
| B | **G đáng** | giảm `>= 25%` độ sâu 11/10 so với không trần **VÀ** giữ `>= 70%` tổng PnL **VÀ** giữ `>= 70%` CAGR **VÀ** intraday maxDD toàn kỳ không xấu hơn baseline |
| B | **G quá đắt** | giữ `< 50%` PnL hoặc CAGR `< 50%` |
| C | **trap đáng** | `<= 40` lần kích hoạt toàn kỳ **VÀ** giữ `>= 90%` PnL **VÀ** cắt `>= 15%` độ sâu 11/10 |
| C | **trap vô dụng** | cắt `< 5%` độ sâu 11/10, hoặc kích hoạt `> 120` lần toàn kỳ |

**Chốt trước thêm**: nếu trap chỉ cắt được ở 11/10 mà ở các cú giảm sâu khác (top-10) không cắt
được gì (`< 5%` độ sâu trung bình) ⇒ kết luận là **"chỉ cắt đúng lúc tốt nhất"**, không phải cơ chế.

## 2. Dữ liệu — đọc THẬT, tái dùng cái đã có

- Leg + margin: `kaggle_sim/out/{t170-x1-2021,hn-t100,hn-g92}` + `java/devrun/FG_KEEPLEG0`
  (`storage/printDone.csv`; giờ GMT+7 → UTC `-7h`, như `RESULT_INTRADAY_DD`).
- Dữ liệu 1m: `/home/ubuntu/kaggle_data_hpo/ticker_YYYYMMDD.bin.gz`, đọc bằng `research/analysis/jbin.py`.
  Contract tuple đã kiểm ở `PREREG_INTRADAY_DD` §2.2 (`tup[1]=HIGH, tup[2]=LOW, tup[3]=CLOSE,
  tup[4]=OPEN`) — **tái dùng nguyên**, không kiểm lại.
- **Chuỗi equity mốc phút baseline: TÁI DÙNG cache** `/home/ubuntu/intradaydd/series.npz`
  (`c_/l_/r_` cho 4 nền, 2,367,360 mốc) — **không tính lại từ đầu**.
- Trục chung `DAY0=20210701 00:00Z`, `DAY1=20251230 23:59Z` ⇒ `T = 1,644*1440 = 2,367,360` mốc.
- Lượt này (chỉ để cho B/C) đọc **1 lượt** dữ liệu 1m để dựng: (a) đóng góp `qty*P` theo **từng leg**
  (mọi mốc leg mở), (b) `ret1h` cross-section toàn universe theo phút + `ret1h` BTC ⇒ cache riêng ở
  `/home/ubuntu/taillever/`.

### 2.1 Công nghiệm thu (chốt trước — phải PASS mới báo cáo)

| # | nội dung | ngưỡng |
|---|---|---|
| **W1** | dựng lại chuỗi baseline (không trần) từ **đóng góp từng leg** == `series.npz` (`c_`) | max\|Δ\| `<= 1e-3` USDT |
| **W2** | maxDD/UW baseline dựng lại == số `RESULT_INTRADAY_DD` §3.1 (−19.96/−19.96/−26.26/−24.30; UW 144.4/147.2/248.2/277.8) | lệch `<= 0.05 pp` / `<= 0.1 ngày` |
| **W3** | phân rã A: `\|Σ contribution − depth\| / depth < 2%` trên mọi cú × nền | `<= 2%` |
| **W4** | trần G: `#leg chặn` tăng đơn điệu khi G giảm (20 ≥ 30 ≥ 40 ≥ 50 ≥ 0) | đơn điệu |

## 3. VIỆC A — phân rã độ sâu theo coin (chốt trước)

Với mỗi `(nền, cú giảm)`: `peak` `i` (đỉnh chạy trước trough), `trough` `j`, `depth_USD = eq(i) − eq(j)`
trên chuỗi **mốc phút** baseline. Tập leg dùng để phân rã:

- `L_trough` = leg **đang mở tại `j`** (và có giá hợp lệ tại `j`);
- đóng góp của leg `l ∈ L_trough`: `qty_l * (P_l(j) − P_ref)` với `P_ref = P_l(i)` nếu leg cũng mở
  (và hợp lệ) ở `i`, ngược lại `P_ref = entry_l`;
- cộng thêm: `pnl_l` của leg **đóng trong `(i, j]`** (realized trong cú giảm);
- nhóm theo `sym` ⇒ `contrib_coin`; `share_coin = contrib_coin / depth_USD` (dấu âm = kéo equity xuống).

Báo cáo: **top-1 / top-3 / phần còn lại** (% độ sâu), số coin mở; cho **cửa sổ 2025-10-09..13**
(`i` = đỉnh chạy từ neo `2025-10-09 00:00Z`, `j` = đáy cửa sổ) **và** cho top-10 cú toàn kỳ.
Top-10 cú **tính lại** bằng `episodes()` trên cache (đúng phương pháp `RESULT_INTRADAY_DD` §4), không
chép tay.

## 4. VIỆC B — trần `gross exposure` (XẤP XỈ offline — GHI RÕ KHÔNG PHẢI SIM)

Luật chốt trước: duyệt leg theo **`m0` tăng dần** (tie: thứ tự gốc trong `printDone.csv`);
`gross(t)` = `Σ margin` các leg **đang mở**; leg mới bị **CHẶN** nếu
`gross(m0) + margin_leg > G% * equity(m0)`.

- `equity` tham chiếu = **chuỗi equity của chính kịch bản** (fixed-point: vòng 1 dùng baseline,
  lặp 3 vòng; báo cáo số leg đổi trạng thái giữa vòng).
- Leg bị chặn: **bỏ hẳn** (không vào, không tính pnl, không chiếm exposure). **KHÔNG tái phân bổ vốn**,
  **KHÔNG tái hiện lại đường quyết định của sim** (sim có thể vào lệnh khác thay thế).
  ⇒ **ĐÂY LÀ XẤP XỈ XẾP HẠNG PHƯƠNG ÁN, KHÔNG PHẢI SIM.**
- Đo cho mỗi `G ∈ {20, 30, 40, 50}` và baseline `G=∞`: **intraday maxDD** (toàn kỳ, mốc phút, `P=close`),
  **worst-window drop 2025-10-09..13** (neo `2025-10-09 00:00Z`, đỉnh chạy trong cửa sổ),
  **tổng PnL** (`Σ pnl` leg nhận), **CAGR** (`(eq_final/CAP0)^(1/4.5) − 1`, 4.5 năm = 2021-07-01→2025-12-30),
  **n** (số leg nhận), **UW** (ngày), **#leg bị chặn**. Cho **cả 4 nền**.
- Bảng so sánh: `Δ độ sâu 11/10 (pp)` vs `Δ PnL (%)` vs `Δ CAGR (pp)` ⇒ chọn G theo **điểm Pareto**.

## 5. VIỆC C — kịch bản trap ALT (chốt trước)

Tín hiệu tại phút `t` (cross-section = **toàn universe trong file 1m**, giá close, đã ffill/bfill
trong ngày; `ret1h(t) = P(t)/P(t−60) − 1`):

- **L1**: `|p10(ret1h cross-section)| > 20%` (đuôi yếu sập > 20% trong 1h);
- **L2**: `|ret1h(BTC)| < 1%` **VÀ** `p10(ret1h) < −10%` (BTC không giảm mà ALT sập).

**Luật chính (primary)**: leg mới bị **CHẶN** nếu `L1 ∪ L2` đúng **tại đúng phút mở lệnh**.
**Biến thể (sensitivity)**: (a) lookback **15 phút** (trap đúng trong `[m0−15, m0]`); (b) chỉ **L1**;
(c) chỉ **L2**.

Đo: **số lần kích hoạt** (đoạn liên tục, và số phút), **#leg bị chặn**, **Δ PnL toàn kỳ**, **Δ độ sâu
11/10**, **Δ intraday maxDD toàn kỳ**, **Δ độ sâu trung bình của top-10 cú** (kiểm "chỉ cắt đúng lúc
tốt nhất"), **phân bố theo năm**.

## 6. Kết luận phải trả lời

1. Rủi ro hệ thống chiếm bao nhiêu % độ sâu của các cú giảm lớn?
2. Trần G nào cắt được nhiều nhất với chi phí lãi thấp nhất (có bảng)?
3. Trap ALT có đáng không (bao nhiêu lần, cắt được gì, mất gì)?
4. Đề xuất **2–3 cấu hình đáng đưa vào SIM THẬT** (không tự chạy) — kèm **tiêu chí chấm đúng
   THUỐC ĐUÔI** (intraday maxDD / worst-window drop), **KHÔNG** phải rate trung bình.

## 7. Mục BỎ / giới hạn (chốt trước + cái đã biết)

1. **KHÔNG chạy Java/sim**, **KHÔNG** chạy lại profile/fitness, **KHÔNG** đổi code nghiên cứu khác.
2. **KHÔNG mô hình thanh lý/margin call** (sim cũng không) ⇒ mọi số là **cận dưới** của rủi ro thực.
3. **KHÔNG tái phân bổ vốn** khi chặn leg ⇒ VIỆC B/C là **thứ tự xếp hạng**, không phải kết quả sim.
4. **KHÔNG có CI** cho metric cực trị (1 quan sát lịch sử, episode không độc lập: ~9 đợt thị trường).
5. Bỏ qua đường đi **trong nến 1m** (chỉ dùng close ở VIỆC B/C; biến thể `bar.low` chỉ để đối chiếu).
6. Chặn theo **phút mở lệnh**, không mô hình trễ/huỷ lệnh trong sim. Leg cùng phút: xử lý tuần tự
   (sim xử lý theo lô) ⇒ xấp xỉ.
7. `p10`/BTC tính trên **universe trong file 1m** (112→598 sym), không phải đúng universe sim từng
   ngày; không loại stablecoin.
8. Không tái dùng bất kỳ verdict nào; kết quả này **không đổi** `RESULT_INTRADAY_DD` (chỉ thêm lựa chọn).
9. Giữ output tool nhỏ (head/grep), kết quả trung gian ở `/home/ubuntu/taillever/`; đĩa chỉ còn ~8GB
   nên cache viết nén, không nhân bản.
