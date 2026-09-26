# PREREG_SIZE_COUNT_HARNESS — Harness trục "GIẢM MARGIN / TĂNG SỐ LỆNH" dưới trần gross 70%

**Ngày chốt:** 2026-09-27 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC khi chạy sim · **KHÔNG push**
**Yêu cầu owner (27/09 05:25):** *"Giảm margin tăng lệnh.... mục tiêu có rồi bạn tạo harness triển khai đi"*.
⇒ Rào đã có (`docs/analysis/RULERS_CURRENT.md` §7/§8/§10). Việc của vòng này: **tạo HARNESS tái sử dụng** cho
trục này rồi **chạy**.

Nền cố định (đã chốt, KHÔNG đo lại): `KEEPLEG0` + **nhịp THIẾT KẾ** (`sel15`: selector 15′ + BIG_DOWN/DCA 1′;
code `3b6c6e9` / `8aedde8`). Baseline `cd-sel15` = 744 lệnh · 0,453 entry/ngày · 13,77 entry/tháng ·
CAGR **+17,29 %** · maxDD −6,27 % · UW 166 · qmin −3,36 % · conc 6,77 % · `%PnL top-1%` 19,13 ·
`bỏ-50%` **−17.551** (USDT). md5 `printDone.csv` = `1317191624d316d955223311ae693228`, equity cuối 71.718.

---

## 0. TRỤC ĐO — định nghĩa + 2 knob (KHÔNG sửa Java, KHÔNG rebuild)

Trục = **giảm margin/lệnh × tăng số lệnh**, **GROSS GIỮ ≤ 70 % CỨNG**.
⚠️ **KHÁC HẲN vòng cũ** (`gate-scale 1,70→1,00`: n 1.085→2.559 ⇒ UW 92→248 · conc 9,77→27,23 %) — vòng cũ
tăng `n` với **size giữ nguyên** ⇒ **gross TĂNG**. Vòng này giảm size khi tăng `n` ⇒ phải **đo lại**, không
được viện số cũ.

Hai knob đã có sẵn trong code (đọc qua `Cfg`, **KHÔNG sửa dòng nào** ⇒ parity `TẮT = y nguyên`):

| knob | key | default | cơ chế (`file:line`) |
|---|---|---|---|
| **size/lệnh** | `SIM_F_BASE` = `F_BASE` | 0,03 | `Configs.java:155` + `:824`; `budget = equity·F_BASE·throttle/ladder` (`TradeUtils.java:142`) |
| **rank-topk** | `SELECTOR_RANK_TOPK` = `K` | file = 8 | `Configs.java:362` (chọn K coin score thấp nhất mỗi timestamp) |

`SIM_F_BASE` là **đúng nghĩa "% equity mỗi lệnh gốc"** ⇒ chọn nó làm knob "giảm margin".
Lưu ý cơ học (trung thực): `F_BASE` áp **TRƯỚC throttle** ⇒ giảm `F_BASE` không phải scale tuyệt đối thuần —
nó **hạ `u = marginRunning/equity`** ⇒ **throttle CAO hơn** ⇒ cho phép **nhiều leg đồng thời hơn**. Đây chính là
kênh "giảm margin ⇒ tăng số lệnh" muốn đo (và cũng là lý do `n` có thể đổi ngay ở B1 dù giữ `K`).

Nền mỗi arm (KHÔNG đổi): profile `x1_gs_t170` + `{DCA_GRID_WEIGHTS=1,1,1,1, DCA_GRID_SCALE=6.0}` (= `KEEPLEG0`)
+ `{SIM_ENTRY_SAMPLE_MIN=15}` (= nhịp thiết kế) + knob arm. Bundle `sim-x1-2021-bundle`, jar `sim-jar-cadence`,
`SIM_END_DATE=20251231`, `ticker_min_days=1826`.

## 1. CÁC ARM (CHỐT TRƯỚC — không đổi sau khi thấy số)

| arm | size/lệnh | `SIM_F_BASE` | `SELECTOR_RANK_TOPK` | tag Kaggle |
|---|---|---|---|---|
| **B0** | ×1 | (default 0,03) | 8 | `cd-sel15` (**dùng lại**, KHÔNG chạy mới) |
| **B1** | **×0,5** | 0,015 | 8 | `sc-b1` |
| **B2** | **×0,5** | 0,015 | **16** | `sc-b2` |
| **B3** | **×0,25** | 0,0075 | **32** | `sc-b3` |
| **B4** | ×0,5 | 0,015 | **32** | `sc-b4` |
| **PAR** (cổng knob, KHÔNG phải arm) | ×1 | **0,03** (khai tường minh) | **8** (khai tường minh) | `sc-par` |

**PAR** = chứng minh 2 knob ở giá trị default **VÔ HẠI**: `sc-par` phải **byte-identical** `cd-sel15`
(md5 `1317191624d316d955223311ae693228`, n=744, eq=71.718). Nếu lệch ⇒ **DỪNG, báo master** (knob plumbing sai).

Ngân sách: Kaggle CPU **chi phí 0**, trần **5 slot** account ⇒ chạy **5 chặn song song** (`sc-par`,`sc-b1`..`sc-b4`),
~12–22′/chặn. **Không cần cắt** B4/B3 (đúng thứ tự cắt đã định nếu thiếu slot: cắt B4 trước, rồi B3).

## 2. ⚠️ HAI SỰ THẬT TOÁN HỌC GHI TRƯỚC (bắt buộc có trong báo cáo)

1. **Scale đều KHÔNG đổi dấu (b′).** Mọi leg ×s (s>0) ⇒ `TF50 → s·TF50` ⇒ **dấu KHÔNG đổi**.
   ⇒ "giảm margin" (scale đều) **KHÔNG THỂ** đưa (b′) từ âm sang dương. B1 (chỉ đổi size) **dự kiến** vẫn ÂM.
2. **Tăng `n` chỉ giúp nếu `mean(nửa dưới) ≥ 0`.** Hiện `TF50 ≈ (n/2)·mean(nửa dưới)` với
   `mean(nửa dưới) < 0` ⇒ **tăng `n` làm `TF50` ÂM THÊM**. B2/B3/B4 (tăng `n` bằng tăng `K`) **dự kiến**
   `TF50` âm sâu hơn B0.

**KỲ VỌNG GHI TRƯỚC:** trục này có thể cải thiện **`maxDD` · `UW` · `conc` · rủi ro CẤP DANH MỤC**,
nhưng **KHÔNG** cải thiện rào (a)/(b′); **2 rào mới vẫn FAIL** ở **mọi** arm. Nếu đo ra khác ⇒ **báo cáo đúng số**.

Chẩn đoán nền (đã có, `RESULT_TAIL_ROBUST_RULERS.md`): mắt xích = **MẤT CÂN XỨNG** `mean|lỗ|/mean lãi = 2,9–3,6×`,
`sign% > 0` 83–91 % ⇒ trung vị leg ÂM ⇒ (b′) là bài toán **CẤU TRÚC LÃI**, không phải bài toán size.

## 3. TRẦN GROSS 70 % — cách áp + cách KHAI

Sim **KHÔNG enforce** trần gross theo từng tick (nó enforce `U_MAX` = trần margin/equity **tổng**, mặc định 0,60 —
xem `Configs.java:156`; đó **KHÔNG** phải trần gross 70 %). Vì vậy vòng này **áp trần hậu kiểm** như
`RESULT_CAP70_FEE06.md` và **KHAI RÕ là hậu kiểm**, đo **cả 2 cách**:

- **(A) theo TB:** `gross_TB = mean_tick( Σ margin mở / equity )`.
- **(B) theo TỪNG TICK (chặt):** `gross_max = max_tick( Σ margin mở / equity )`.

Dựng từ ledger (`printDone.csv`: `margin`, `start`, `end`) + chuỗi equity ngày (`sim.out`): mỗi leg là 1 khoảng
`[start,end]`, `margin/equity_tại entry`; tổng theo biên sự kiện để lấy chuỗi "gross mở" rồi mean/max.
Hệ quả cần nói rõ: nếu `gross_max > 70 %` thì "trần 70 % bind theo từng tick" ⇒ size thực phải **×0,70/gross_max**.

## 4. CHỈ SỐ (scorer độc lập với trục — đọc `printDone.csv` + `sim.out`)

**Rào mới:** (a) `%PnL từ top-1% leg ≤ 15 %` · (b′) `bỏ top-50% leg` ⇒ PnL **> 0**.
**Phá vỡ `q*`:** bỏ bao nhiêu % leg (theo PnL giảm dần) thì PnL còn lại = 0.
**Bộ 4 thước chuẩn (chốt `RULERS_CURRENT` §10.1):** `wl_ratio` (mean lãi / mean|lỗ|) · `tf_5` (PnL/leg sau khi bỏ
top-5 % leg) · `loss_mean` (lỗ trung bình) · `conc_5` (tỷ phần PnL ở top-5 % leg) + dự bị `median/leg`.
Thêm: `tf_10`, `TF50`, `TF50/(n/2)`, `mean|lỗ|/mean lãi`, `sign%` (= win%).
**Rào cũ (`--appetite latest`):** maxDD ≤ 40 %/năm · UW ≤ 250 ngày · qmin ≥ −20 % · **0 năm âm (CỨNG)** ·
**conc 1 coin ≤ 15 % (CỨNG)** · gross ≤ 70 % · phí 0,6 %/vòng (đã nằm trong sim).
**5 rate + CI** (block-72h · 2000 rep · seed `20260905` · `inflate(k)`), luật siết §10.2:
`{TSloss% · mP|SM · mP|SL · mMargin}`; báo thêm `win%`/`meanP` để đối chiếu nhưng **KHÔNG tính** `meanP`,
**tối đa 1 rate** thuộc nhóm tần suất `{win%, TSloss%}`.
**`k` (multiplicity):** `k = số arm mới đối đầu baseline = 4` (`sc-b1`..`sc-b4`; `sc-par` không tính) ⇒
`inflate(4) = sqrt(2·ln 4) = 1,6651`. Báo **cả raw95 và inflate(k)**.

## 5. THỨ TỰ ƯU TIÊN + LUẬT QUYẾT ĐỊNH

Ưu tiên đọc: (1) `gross` thực tế có giữ ≤ 70 % không (cả 2 cách) → (2) `conc 1 coin` + số coin đồng thời →
(3) `maxDD`/`UW`/quý xấu nhất → (4) rào (a)/(b′) + `TF50` → (5) `TF50/(n/2)` → (6) 5 rate + CI.

**GIỮ một arm** chỉ khi **tất cả**: (i) rào CŨ `appetite latest` PASS (0 năm âm + conc ≤ 15 % + gross ≤ 70 % +
maxDD ≤ 40 + UW ≤ 250 + qmin ≥ −20); **và** (ii) **≥ 2 rate** ngoài CI **cùng hướng TỐT** vs B0 theo luật siết §10.2;
**và** (iii) không làm (a)/(b′) xấu hơn B0 theo bất kỳ nghĩa **ngoài CI**.
Rào (a)/(b′) là **điều kiện go-live**, KHÔNG phải điều kiện "giữ arm": arm có thể "đỡ risk hơn" nhưng vẫn FAIL (a)/(b′)
⇒ ghi rõ **"chưa go-live được"**. Cơ chế thoát đã thoả thuận (`RULERS_CURRENT` §8): không cấu hình nào ra ⇒ owner hạ rào.

## 6. RÀNG BUỘC (CỨNG)

1. **KHÔNG chạy Java/sim trên Oracle** (shadow LIVE) ⇒ **Kaggle**. Chi phí 0.
2. **KHÔNG chạm** production/242/ONNX/`NUM_FEATURES`/`extractFeatures45`/đường LIVE.
3. **KHÔNG push git**; commit sớm.
4. **DEV only ≤ 2025-12-31**; **KHÔNG chạm 2026** (holdout nguyên vẹn).
5. `df -h /` ~93 % ⇒ file NHỎ, dọn ngay; output tool THẬT NHỎ.
6. **KHÔNG sửa code Java.** Nếu buộc phải sửa ⇒ giữ hành vi cũ mặc định + **parity CẢ HAI** md5
   `99e42b75cf1a2142f9cd14dc72e371ba` (KEEPLEG0) và `efb793e2468ca3a7318da0f0ad23d4fc` (T170); lệch ⇒ DỪNG, báo.

## 7. OUTPUT

`docs/prereg/PREREG_SIZE_COUNT_HARNESS.md` (file này) + `research/analysis/size_count_run.py` (runner tham số hoá
`--size-mult/--rank-topk/--arm`) + `research/analysis/size_count_score.py` (scorer độc lập) +
`docs/result/RESULT_SIZE_COUNT.md` (+ JSON). Commit, **KHÔNG push**.
