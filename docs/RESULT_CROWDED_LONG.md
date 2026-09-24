# RESULT_CROWDED_LONG — crowded-long bằng **QUANTILE TRƯỢT**: tín hiệu **RỦI RO/SIZE** (không phải alpha)

Ngày đo: 2026-09-24. Pre-reg: `docs/PREREG_CROWDED_LONG.md` (**commit `0acf68c`**, chốt **TRƯỚC** khi đo;
sau đó **không sửa thiết kế**). Script: `research/analysis/crowded_long_build.py` (dựng panel),
`research/analysis/crowded_long.py` (đo), `crowded_long_supp.py` + `crowded_long_supp2.py` (bổ trợ post-hoc,
**có ghi rõ**, xem AMENDMENT-1).

Ràng buộc đã tuân: **thuần Python offline** · **KHÔNG** Java/sim trên Oracle · **KHÔNG** `claude-run`
· **KHÔNG push** · **DEV only** (mọi cửa sổ `< 2026-01-01`). Trung gian `/tmp/crowded/`
(`report_crowded.txt`, `report_crowded_supp*.txt`, `results_crowded.json`).

---

## 0. KẾT LUẬN (một dòng mỗi câu hỏi)

> **(1) Crowded-long (quantile trượt) có phải tín hiệu RỦI RO thật không? → KHÔNG (dưới MDE).**
> EW 24h `ON−OFF = −0,2246%/−0,2816%` (N=30/90) với `CI72h_x1.21` **chứa 0** và **dưới MDE `0,53%/0,55%`**.
> Neo MOM15 (ô mạnh nhất) `−2,4248%/−2,5597%`, p một phía `0,022/0,037`, OOS cùng dấu `−3,72%/−7,12%`
> — **NHƯNG** `CI72h_x1.21` vẫn **chứa 0**, `CI_adj(√2)` càng chứa 0, và **đó là hiệu ứng TRUNG BÌNH,
> không phải ĐUÔI** (đuôi khi ON **nông hơn** khi OFF). Kiểm chéo: **không** là proxy biến động cao hay
> downtrend BTC — nó là **regime "bull êm"** (BTC>MA30 **0,56×**, Jaccard ≤ 0,25) ⇒ cái đo được là
> *"thị trường yên ả"*, không phải *"đám đông long"*.
>
> **(2) "Giảm size khi crowded-long" có làm giảm ĐUÔI > chi phí không? → KHÔNG.**
> Trên sách thật (KEEPLEG0, ô đăng ký chính) `drop24 ON−OFF = −0,0058% (N=30) / +0,0197% (N=90)`,
> CI chứa 0, IS/OOS **ngược dấu**. **Đuôi KHÔNG tập trung vào cửa sổ ON**: `0/10` (N=30) và `2/10`
> (N=90) trong **10 cửa sổ drop24 tệ nhất** là ON; tỷ trọng đóng góp vào tổng drop âm chỉ
> **22,9–26,3%** ≈ tần suất ON nền **25,0–25,8%**. Cú giảm lớn nhất cả mẫu (**2025-10-10, `−19,32%`**)
> xảy ra khi tín hiệu **TẮT** (`0,0%` giờ ON ở N=30 trong `[25/09..11/10/2025]`).
> Tỷ lệ "lợi ích/chi phí = 21×" ở proxy là **giả tạo** (cắt size trong ~25% giờ *bất kỳ* cũng cắt CVaR5
> ~25%) ⇒ **không phải hedge đuôi, mà là một bet timing trung bình dưới MDE**.
>
> **(3) Có đề xuất cấu hình nào cho SIM thật không? → KHÔNG. ĐÓNG NỐT trục crowded-long/positioning.**
> Cùng với `RESULT_TAIL_LEVER` (trần tĩnh không đáng), nay **bản có điều kiện cũng không có cơ sở**:
> đuôi của sách là **hệ thống** và đến lúc tín hiệu **TẮT**.

---

## 1. Cổng tự-kiểm (chạy TRƯỚC khi đọc số)

| Cổng | Kỳ vọng | Vòng này | Đạt |
|---|---|---|---|
| **G1 neo MOM15** (pre-reg §2) | `net@0,10% = +1,6690%`, n = **7 128** | `+1,6690%`, n = **7 128** | ✔ |
| **G2** x_t causal | ngưỡng chỉ dùng `[t−N·24, t−1]`, **không** gồm `t` | `shift(1)` trên rolling p80, ≥90% mốc hợp lệ | ✔ |
| **G3** coverage `ls_global` | 100% từ 2023 | 2023 **100,0%**, 2024 **99,9%**, 2025 **99,9%**, 2022 94,9% | ✔ |
| **G4** không đọc 2026 | 0 mốc ≥ 2026-01-01 | 0 (ma trận dừng `2025-12-31 23:00`) | ✔ |
| **G5** chuỗi MTM tái dùng | V1–V5 đã PASS | đọc lại `/home/ubuntu/intradaydd/series.npz` (không chạy lại sim) | ✔ |
| **G6** đối chứng EW mọi bảng | có | có (hàng `OFF`/`EW` mọi bảng) | ✔ |

Panel: NH = 35 088 mốc giờ, `ncol = 627`, `x_t` có **34 599** mốc hợp lệ, universe TB **255,9 sym/mốc**.
W1 = 2023-01-01 → 2025-12-31 23:00 (**26 304** mốc giờ); IS = 2023-2024; OOS = 2025.

---

## 2. Tín hiệu & trạng thái ON — **% thời gian BẬT + số lần kích hoạt**

`x_t = median(log ls_global)` cross-section; `thr_t(N) = p80(x)` trên `[t−N·24, t−1]`; `ON_t = x_t > thr_t`.

| N (ngày) | n_undef (W1) | **% thời gian BẬT** | **số đoạn ON** | chuyển OFF→ON | độ dài trung vị | TB | dài nhất | ≤2h | ≤6h |
|---|---|---|---|---|---|---|---|---|---|
| **30** | 19 | **25,8%** | **571** | 571 | **2,0 h** | 11,9 h | 349 h (15 ngày) | 52% | 72% |
| **90** | 19 | **25,0%** | **364** | 364 | **3,0 h** | 18,1 h | 656 h (27 ngày) | 48% | 72% |

- % giờ ON theo năm — **N=30**: 2023 **32,5%** · 2024 **28,2%** · 2025 **16,8%**; **N=90**: 30,4% · 30,2% · **14,4%**.
  (Tức tín hiệu **thưa dần** về cuối mẫu — chính là năm có cú giảm 2025-10-10.)
- ⚠ **Tính vận hành:** median một đoạn ON chỉ **2–3 giờ** ⇒ **571/364 lần bật trong 3 năm** (~190/năm,
  ~0,5 lần/ngày) — **tín hiệu rung (chattering)**, không phải "thời kỳ" dài. Một luật giảm size theo nó
  sẽ **bật/tắt liên tục**; đây là vấn đề vận hành độc lập với việc có edge hay không.

---

## 3. (A) Lợi nhuận khi ON vs OFF — chi phí của luật

`net(t,H) = mean_u[c5(t+H)/c5(t)−1] − 0,0010 − 0,5·rg(t)/c5(t) − [f5(t+H)−f5(t)]`.

### 3.1 EW (universe) — 6 ô đăng ký

| ô | ON mean | OFF mean | **ON−OFF** | CI72h_x1.21 | CI_adj(√2) | p(>0) | OOS | MDE(p80) ON |
|---|---|---|---|---|---|---|---|---|
| N=30 H=1h | −0,2242% | −0,2172% | **−0,0070%** | [−0,0373, +0,0233] | [−0,0499, +0,0359] | 0,283 | −0,0251% | — |
| N=30 H=4h | −0,2431% | −0,2007% | **−0,0424%** | [−0,1503, +0,0655] | [−0,1950, +0,1101] | 0,168 | −0,1011% | — |
| **N=30 H=24h** | −0,3374% | −0,1129% | **−0,2246%** | **[−0,8021, +0,3529]** | [−1,0413, +0,5922] | 0,174 | −0,4374% | **0,5279%** |
| N=90 H=1h | −0,2317% | −0,2147% | **−0,0169%** | [−0,0464, +0,0126] | [−0,0587, +0,0248] | 0,081 | −0,0072% | — |
| N=90 H=4h | −0,2540% | −0,1975% | **−0,0565%** | [−0,1668, +0,0539] | [−0,2125, +0,0996] | 0,108 | −0,0801% | — |
| **N=90 H=24h** | −0,3818% | −0,1002% | **−0,2816%** | **[−0,8999, +0,3366]** | [−1,1560, +0,5927] | 0,136 | −0,6272% | **0,5493%** |

- **Dấu nhất quán** ("crowded-long ⇒ forward EW xấu hơn" ở 24h) nhưng **|hiệu ứng| < MDE ~2,0×** và
  CI (kể cả chưa hiệu chỉnh) **chứa 0** ⇒ *không phân biệt được với 0*.
- **Đuôi khi ON không tệ hơn**: N=30 24h — `CVaR5` ON **−10,10%** vs OFF **−9,90%**; `p01` ON **−11,31%**
  vs OFF **−11,22%**; N=90 — `CVaR5` ON **−10,39%** vs OFF −9,78%. Chênh lệch đuôi ~0,2–0,6 pp so với
  mức ±25–45% của chính đuôi ⇒ **không ích cho giảm rủi ro**.
- Độ lệch "EW trung bình" so với vòng trước (`−0,2237%`) là do **trọng số**: vòng này lấy **TB theo giờ**
  (mỗi giờ 1 phiếu), vòng `RESULT_LS_TAKER` lấy **TB theo symbol-giờ** (universe lớn dần về cuối mẫu nên
  nặng hơn về 2025 vốn xấu hơn). Ghi rõ để không ai đọc chéo hai bảng thấy "lệch".

### 3.2 Neo MOM15 (ô mạnh nhất của cả vòng)

| ô | ON mean | OFF mean | **ON−OFF** | CI72h_x1.21 | CI_adj(√2) | p(>0) | IS | **OOS** | MDE(p80) ON |
|---|---|---|---|---|---|---|---|---|---|
| N=30 H=4h | +0,4970% | +0,9105% | −0,4135% | [−2,5535, +1,7265] | [−3,4400, +2,6129] | 0,405 | −0,5608% | −0,5187% | — |
| **N=30 H=24h** | **+0,4725%** | **+2,8974%** | **−2,4248%** | **[−5,2886, +0,4389]** | **[−6,4748, +1,6251]** | **0,022** | −2,0980% | **−3,7248%** | **1,9057%** (adj 2,6950%) |
| N=90 H=4h | +0,5227% | +0,8818% | −0,3591% | [−2,4523, +1,7341] | [−3,3193, +2,6011] | 0,406 | +0,0251% | −2,0515% | — |
| **N=90 H=24h** | **+0,2906%** | **+2,8503%** | **−2,5597%** | **[−5,7583, +0,6389]** | **[−7,0832, +1,9638]** | **0,037** | −1,9540% | **−7,1189%** | **2,4129%** (adj 3,4124%) |

- Đây là **ô hấp dẫn nhất**: cực ổn định giữa 2 giá trị N (−2,42% / −2,56%), p một phía 0,022/0,037,
  OOS **cùng dấu** và **lớn hơn** IS ⇒ "edge MOM15 (+1,67%/event) tệ hơn hẳn khi crowded-long".
- **NHƯNG theo đúng tiêu chí đã đăng ký thì KHÔNG đạt:** `CI72h_x1.21` **chứa 0** (cận trên +0,44%/+0,64%),
  `CI_adj(√2)` càng chứa 0, và |2,42%| **< nửa-độ-rộng CI (2,86%)**; MDE(p80) nhánh ON = 1,91% /
  2,41% (đã ×√2 = 2,70%/3,41%) ⇒ **dưới ngưỡng phán quyết**.
- **Và quan trọng hơn cho câu hỏi RỦI RO:** đây là **hiệu ứng TRUNG BÌNH**, không phải ĐUÔI —
  `CVaR5` **ON −25,00%** vs **OFF −29,14%** (N=30); `p01` ON **−29,37%** vs OFF **−35,25%**.
  ⇒ Khi ON, chiến lược **lãi ít hơn NHƯNG cũng ít đuôi hơn**. Muốn "giảm đuôi" thì phải cắt khi **OFF**.

---

## 4. (C) Đối chứng định nghĩa — tercile THEO THỜI GIAN (không tính vào k)

| regime | n (giờ) | net 24h | p05 | CVaR5 |
|---|---|---|---|---|
| tercile-TH 0 | 8 738 | **+0,0563%** | −6,2815% | −8,8658% |
| tercile-TH 1 | 8 762 | +0,0368% | −5,8566% | −8,5304% |
| **tercile-TH 2** | 8 761 | **−0,6046%** | −8,2348% | −11,8989% |

`ter2−ter0 = **−0,6609%**`, `CI72h_x1.21 [−1,3160, −0,0058]` (p(diff>0)=0,005, **k=1**), OOS **−1,5534%**.

- Số ter2 **trùng khít** vòng trước (−0,6046% vs −0,6044%) ⇒ **định nghĩa cũ tái lập được**.
- **Nhưng:** (i) tercile đặt bằng **phân bố TOÀN MẪU W1** ⇒ có **look-ahead** trong phân loại
  (top-tercile chỉ biết được *sau khi* biết cả 3 năm); (ii) khi thay bằng **ngưỡng trượt causal**
  (đăng ký chính), hiệu ứng **co lại ~2,5–3×** (từ −0,66% xuống **−0,22%/−0,28%**) và **tụt xuống dưới MDE**
  với CI chứa 0. ⇒ Kết luận đúng đắn: phần "ấn tượng" của ter2 đến từ **việc chọn ex-post thời kỳ**,
  không phải từ một trạng thái nhận biết được tại thời điểm giao dịch.

---

## 5. (D) Đuôi intraday trên SÁCH THẬT — `drop24` (ô đăng ký của câu hỏi (2))

`drop24(t) = min_{m∈(t,t+24h]} E(m)/E(t) − 1` trên chuỗi equity mốc phút **đã nghiệm thu**
(`series.npz`, mark = `close`; nền chính **KEEPLEG0**). 26 256 mốc giờ (bỏ 48 giờ cuối W1 vì thiếu 24h
forward trong cache). `dd24` = maxDD trong cửa sổ (cummax) — **không có CI**.

| nền / N | ON mean | OFF mean | **ON−OFF** | CI72h_x1.21 | p(>0) | IS | OOS | lift 10 tệ nhất | tỷ trọng drop âm |
|---|---|---|---|---|---|---|---|---|---|
| **KEEPLEG0 N=30** | −0,1755% | −0,1697% | **−0,0058%** | [−0,1288, +0,1173] | 0,448 | −0,0250% | **+0,0292%** | **0,00×** (50 tệ: 0,00×) | **26,3%** |
| **KEEPLEG0 N=90** | −0,1564% | −0,1761% | **+0,0197%** | [−0,0930, +0,1324] | 0,648 | −0,0233% | **+0,1400%** | 0,80× (50 tệ: 0,16×) | **22,9%** |
| T100 N=30 | −0,4717% | −0,4189% | −0,0528% | [−0,2309, +0,1253] | 0,253 | −0,0992% | −0,0906% | 0,00× (50: 0,47×) | 28,0% |
| GD92 N=30 | −0,5315% | −0,4222% | −0,1092% | [−0,2968, +0,0783] | 0,079 | −0,1676% | **+0,0538%** | 0,00× (50: 0,70×) | 30,3% |
| GD92 N=90 | −0,5629% | −0,4126% | −0,1503% | [−0,3237, +0,0231] | 0,018 | −0,2572% | **+0,1875%** | 0,80× (50: 0,16×) | 31,3% |

- **Nền đăng ký chính (KEEPLEG0) = ZERO** (−0,006% / +0,020%), CI chứa 0, **IS âm nhưng OOS dương**.
- **Đuôi KHÔNG tập trung ở ON.** Ô duy nhất "trông có" là `GD92 N=90` (−0,150%, p=0,018) nhưng
  **OOS +0,19% ngược dấu**, 50 cửa sổ tệ nhất lại chỉ **0,16×** tần suất nền, và GD92 chỉ là nền **phụ**
  ⇒ **không dùng được** (ghi rõ, không lén nâng lên).
- **10 cửa sổ `drop24` tệ nhất của KEEPLEG0 = 10/10 đều thuộc 2025-10-10**, và trạng thái ON:
  `N=30: 0/10` · `N=90: 2/10` (2 giờ đó là 16:00 & 17:00 ngày 10/10).
- **% giờ ON quanh cú giảm toàn kỳ** `[2025-09-25 .. 2025-10-11]`: **N=30 = 0,0%** (n=385) ·
  **N=90 = 5,5%** — so với tần suất nền **25,8%/25,0%**. ⇒ **Sự kiện rủi ro lớn nhất của mẫu xảy ra khi
  tín hiệu TẮT.** Một luật "giảm size khi crowded-long" **không chạm tới** cú giảm đó (drop `−19,32%`).
- `dd24` p01: ON **−4,33%** vs OFF −3,23% (N=30) và ON −4,19% vs OFF −3,23% (N=90) — hơi sâu hơn khi ON,
  nhưng **không có CI** và **nhỏ hơn nhiều bậc** so với cú −19,3% nằm ở OFF.

---

## 6. (E) KIỂM CHÉO bắt buộc — tín hiệu có phải chỉ là proxy?

| đo | N=30 | N=90 | đọc ra |
|---|---|---|---|
| Spearman(`x_t`, `vol_t`) | **−0,236** | — | crowded-long đi với **biến động THẤP** |
| P(vol-ter2 \| ON) / P(vol-ter2) | 37,7% / 33,3% = **1,13×** | 39,7% / 33,3% = **1,19×** | gần như **không** trùng (Jaccard 0,197 / 0,205) |
| P(BTC 24h<0 \| ON) / P | 55,7% / 47,3% = 1,18× | 52,7% / 47,3% = 1,12× | trùng **yếu** (Jaccard 0,245 / 0,223) |
| P(BTC<MA30 \| ON) / P | 24,2% / 43,4% = **0,56×** | 20,6% / 43,4% = **0,47×** | **NGƯỢC** với downtrend (Jaccard 0,099 / 0,081) |

Tương phản `ON−OFF` (EW 24h) **trong từng lát**:

| lát | N=30 | N=90 |
|---|---|---|
| vol-ter0 (biến động thấp) | **−0,6020%** CI[−1,3556, +0,1516] p=0,021 | **−0,6649%** CI[−1,4253, +0,0956] p=0,021 |
| vol-ter1 | −0,1882% | −0,2806% |
| vol-ter2 (biến động cao) | **+0,0587%** | −0,0132% |
| BTC 24h > 0 (BTC tăng) | −0,3403% | −0,5685% p=0,026 |
| BTC 24h < 0 | −0,1808% | −0,0440% |
| BTC > MA30 | −0,0770% | −0,4267% |
| BTC < MA30 | −0,5376% (n_ON=1 642) | **+0,1144%** (n_ON=1 352) |

**Đọc ra:** crowded-long **không** là proxy của biến động cao (1,13–1,19×) và **càng không** là proxy của
downtrend BTC (0,56× — nó xảy ra khi BTC **trên** MA30). Hiệu ứng (yếu) **tập trung ở vol THẤP** và
BTC-**tăng** (nhưng ở N=90 lát "BTC<MA30" lại **đổi dấu +0,11%**, n=1 352 ⇒ không ổn định). ⇒ Không thể "thay bằng cái đơn giản hơn" (vol/trend) — vì bản thân
crowded-long **chính là một biến thể của "bull êm"**, và tiêu chí (1) đã trượt ở ngưỡng MDE.
(Ghi nhận: Jaccard in trong `report_crowded.txt` §(E) là công thức viết vội — **số đúng** ở
`report_crowded_supp2.txt` §S8.)

---

## 7. (F) Tác động lên SỐ LỆNH

| | N=30 | N=90 |
|---|---|---|
| **% thời gian phải giảm size** | **25,8%** | **25,0%** |
| **% event MOM15 trong W1 rơi vào giờ ON** | **30,1%** (n=5 433) | **26,6%** |
| % event MOM15 toàn DEV 2022-2025 trong ON | 28,1% (n=6 876) | 24,5% (n=6 722) |
| số lần can thiệp (đoạn ON / 3 năm) | **571** | **364** |

⇒ Nếu dùng như **filter cứng (`s=0`)**: mất **~27–30% số lệnh MOM15**; nếu dùng **giảm nửa size**: cắt
25% exposure trong ~26% thời gian, **bật/tắt ~190 lần/năm** (median đoạn 2–3h) ⇒ chi phí **vận hành**
lớn, trong khi lợi ích rủi ro (mục 5) = **0**.

---

## 8. (G) Kinh tế luật + **AMENDMENT-1** (metric đăng ký bị suy biến)

Luật đăng ký: `s=0,5` khi ON, `s=1` khi OFF, trên proxy EW:

| N / H | baseline mean | rule mean | Δmean | ΔCVaR5 | "tỷ lệ" ΔCVaR5/Δmean |
|---|---|---|---|---|---|
| 30 / 24h | −0,1707% | −0,1273% | **+0,0434%** | +0,9377% | 21,6× |
| 90 / 24h | −0,1707% | −0,1229% | **+0,0478%** | +0,9973% | 20,9× |
| 30 / 1h | −0,2190% | −0,1900% | +0,0289% | +0,2647% | 9,2× |

⚠ **Tỷ lệ này KHÔNG dùng được làm bằng chứng "lợi > chi phí":**
1. **Δmean > 0 (có "lãi") chỉ vì nhánh ON có mean xấu hơn** — tức đây là *bet timing trung bình*,
   không phải hedge đuôi; và hiệu ứng mean đó **đã bị phán quyết dưới MDE** ở mục 3.
2. **ΔCVaR5 dương ~25% là CƠ HỌC**: cắt size ở ~25% giờ *bất kỳ* cũng giảm CVaR5 ~25%. Kiểm chứng
   trực tiếp (supp2 §S4): trong **5% giờ EW 24h xấu nhất**, tỷ lệ ON chỉ **30,9%/31,8%** (lift
   **1,20×/1,27×** so nền 25%) — và với **MOM15** thì **22,8%/23,9%** (**0,76×/0,90×**), còn 4h là
   **12,9% (0,43×)** ⇒ đuôi **KHÔNG** tập trung vào ON, với chính chiến lược thì đuôi **nằm ở OFF**.

### AMENDMENT-1 (bổ sung SAU khi đo; ghi rõ vì pre-reg §4 yêu cầu `maxDD` của chuỗi luỹ kế)

Metric đăng ký "`maxDD` của chuỗi luỹ kế 24h-step" trả về **−100,00%** cho **cả baseline lẫn rule** ⇒
**SUY BIẾN, không dùng được**. Đã **đo lại nguyên nhân** (không suy diễn):
- **Lý do cấu trúc:** net 1h của proxy EW có **mean −0,22%/giờ** = **cost drag** (phí 0,10% + slip +
  funding). Cộng dồn 26 000 bước ⇒ `(1+r)` về ~0 ⇒ `maxDD = −100%` **bất kể** luật. Metric này vô nghĩa
  cho proxy re-balance mỗi giờ.
- **Nhiễu thêm (đã QC):** 28/7 829 596 ô symbol-giờ (H=1h) có net < −50% (H=24h: 941 ô, 3 ô < −90%),
  ô xấu nhất **−88,85% CUDISUSDT 2025-11-04 22:00** mà giá **gần như không đổi** (`0,19630 → 0,19660`)
  ⇒ thủ phạm là **hạng tử slip `0,5·rg/c5`** trên nến có range dị thường (không phải giá "chết").
  Bản **WINSOR** (clip cross-section [p1,p99] mỗi giờ, supp §S2) cho **cùng kết luận**:
  `ON−OFF (24h) = −0,2234% (N=30) / −0,2830% (N=90)`, CI vẫn chứa 0; `maxDD(path)` **vẫn −100%**
  (đúng như lý do cấu trúc ở trên).
- **Thay thế đã dùng:** các metric đuôi **có nghĩa** = `CVaR5`/`p01` của chuỗi per-giờ **và** (quan trọng
  nhất) `drop24`/`dd24` **trên sách thật** (mục 5) — vốn **không** bị ảnh hưởng bởi lỗi này.
  ⇒ **Không đổi bất kỳ tiêu chí phán quyết nào** của pre-reg; bổ sung này chỉ **thay thế một metric
  bị suy biến**, và cả hai đường (raw/winsor) đều cho cùng phán quyết.

---

## 9. TRẢ LỜI TRỰC TIẾP (1)(2)(3)

**(1) Crowded-long có phải tín hiệu RỦI RO thật (ngoài MDE, có OOS) không? → KHÔNG.**
- **EW 24h**: `−0,2246% (N=30) / −0,2816% (N=90)`, `CI72h_x1.21` chứa 0, `CI_adj(√2)` chứa 0,
  **dưới MDE 0,5279%/0,5493%** ⇒ không phân biệt được với 0.
- **Neo MOM15 24h** (ô mạnh nhất): `−2,4248% / −2,5597%`, p 0,022/0,037, IS −2,10/−1,95%, **OOS −3,72/−7,12%**
  (cùng dấu, lớn hơn IS) — **nhưng** `CI72h_x1.21` **chứa 0** (`[−5,29, +0,44]`/`[−5,76, +0,64]`),
  `CI_adj(√2)` càng chứa 0 ⇒ **dưới ngưỡng phán quyết đã đăng ký**. Và nó là hiệu ứng **mean**, không
  phải đuôi (đuôi ON **nông hơn** OFF).
- **Kiểm chéo**: không phải proxy vol cao (1,13–1,19×) cũng không phải downtrend BTC (**0,56×**) ⇒
  bản chất là **"bull êm"**; do đó dù có hiệu ứng thì **cái đơn giản hơn** (chính "bull êm" = low-vol
  + BTC>MA30) đã bao trùm, và bản thân nó cũng không có cơ sở.

**(2) "Giảm size khi crowded" có giảm đuôi > chi phí không? → KHÔNG (số cụ thể):**
- Sách thật KEEPLEG0: `drop24 ON−OFF = −0,0058% (N=30) / +0,0197% (N=90)`; CI chứa 0; IS/OOS ngược dấu.
- **Đuôi không tập trung ở ON**: 10 cửa sổ drop24 tệ nhất = **10/10 là 2025-10-10**, trong đó
  **0/10 (N=30)** và **2/10 (N=90)** là ON; 50 tệ nhất: lift **0,00×/0,16×**; tỷ trọng đóng góp drop âm
  **22,9–26,3%** ≈ nền **25%**. Cú giảm toàn kỳ **−19,32% (10/10/2025)** có **0,0% (N=30) / 5,5% (N=90)**
  giờ ON trong 17 ngày trước đó.
- "Tỷ lệ 21×" của luật trên proxy là **cơ học** (cắt 25% size ⇒ cắt ~25% CVaR5) và phần dương của
  Δmean đã **dưới MDE** ⇒ **không phải giảm đuôi > chi phí**.
- So sánh trực tiếp với `RESULT_TAIL_LEVER` (trần tĩnh không đáng): luật **có điều kiện** này cũng
  **không đáng** — và lý do sâu hơn: **nó nhắm sai chỗ** (đuôi nằm ở OFF).

**(3) Nếu có ⇒ đề xuất cấu hình cho SIM thật? → KHÔNG có. ĐÓNG NỐT.**
- Không đưa ra cấu hình nào; **không** dùng crowded-long cho cổng AI, cho size, cho filter coin, hay cho
  bất kỳ throttle nào. Trục **crowded-long/positioning (đặc trưng "vị thế/đám đông")** ⇒ **đóng**
  (nối tiếp việc đóng trục OI 5/5 cột ở `RESULT_LS_TAKER`).
- **Việc còn lại nên làm** (không thuộc vòng này, không tự chạy): giảm đuôi phải nhắm vào **thứ tự hiện
  diện ở OFF** — tức **cơ chế hệ thống** (portfolio-level stop / gross-exposure theo tổn thất của CHÍNH
  sách, không theo trạng thái đám đông). Đây là **cấp sách**, không phải cấp đám đông.

---

## 10. Mục nào BỎ / hạn chế (theo pre-reg §9 + điều thấy thật)

1. **BỎ metric `maxDD` của chuỗi luỹ kế proxy** (bị suy biến do cost drag; xem AMENDMENT-1). Thay bằng
   `CVaR5`/`p01` + `drop24`/`dd24` sách thật.
2. **BỎ horizon 1h** khỏi mọi kết luận: |hiệu ứng| 0,007–0,017% ≪ MDE, và net 1h bị **cost drag**
   (−0,22%/giờ) chi phối ⇒ vô dụng làm tín hiệu.
3. **BỎ các nền phụ T100/GD92 như bằng chứng**: `GD92 N=90` có p=0,018 nhưng **OOS ngược dấu** và lift
   50-tệ-nhất = 0,16× ⇒ **không dùng** (ghi rõ thay vì lờ đi).
4. **KHÔNG** đọc tercile-theo-thời-gian (§4) như bằng chứng dương: nó **có look-ahead** ở khâu phân loại
   và **co 2,5–3×** khi chuyển sang ngưỡng trượt causal.
5. Giới hạn: (a) proxy EW/neo MOM15 **không phải** sách thật; (b) sách thật chỉ **đọc lại** chuỗi equity cũ —
   **luật có size thay đổi CHƯA được mô phỏng trên sách thật** (không chạy sim), nên (2) chỉ là
   *"đuôi có tập trung vào ON không"* + *"chi phí trên proxy"*, **không** phải PnL của luật;
   (c) `drop24` bỏ 48 giờ cuối W1 (thiếu 24h forward trong cache); (d) `dd24` (cummax) **không có CI**;
   (e) 2022 có lỗ hổng `ls_global` 5,1% mốc giờ — chỉ ảnh hưởng warm-up, W1 sạch ≥99,9%.
