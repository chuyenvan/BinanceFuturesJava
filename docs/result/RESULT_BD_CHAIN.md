# RESULT_BD_CHAIN — đổi `rateDown15MAvg` theo tỷ lệ universe `f` (G2 + FLAT3)

Chạy 2026-10-01 (vòng 3 · subagent "BD-CHAIN BUILD"), nhánh `module`. Pre-reg:
`docs/prereg/PREREG_BD_CHAIN.md` (chốt **TRƯỚC** khi đo). Nền: `profiles/g2_flat3.properties`
(md5 FILE `c6d4ef57…`; parity `printDone.csv` md5 `650c386f0d0dfea334af9d55ca2f21d4`, equity
131908, n 2517). DEV ≤ 2025-12-31; 2026 = HOLDOUT (không đọc).

---

## 0. KẾT QUẢ CHỐT (đọc trước)

> ### ✅ HARNESS ĐÃ XÂY + CHẠY ĐƯỢC cho **bước 1-2** (trước đây thiếu hoàn toàn).
> ### ⛔ NHƯNG **CỔNG PARITY `f=0` KHÔNG KHỚP** khi dùng `market.bin` SINH LẠI ⇒ **DỪNG**, không chấm arm.

| hạng mục | kết quả |
|---|---|
| **Kernel A** — sinh `market.bin` từ ticker file Kaggle (+ `SIM_BD_FRACTION`) | ✅ chạy 5/5 arm (f=0/0.1/0.3/0.5/1.0), ~18–38 phút/arm |
| **Kernel B** — patch cột rate-derived của gate store từ `market.bin` (Python thuần) | ✅ chạy 5/5 (f=0/0.1/0.3/0.5/1.0) |
| **Parity JAR HEAD** (`bdjar-par`: jar HEAD + `market.bin` GỐC) | ✅ **md5 `650c386f0d0dfea334af9d55ca2f21d4` — khớp byte-identical** |
| **Parity `f=0` toàn phần** (`bdf000-par`: jar HEAD + `market.bin` SINH LẠI) | ⛔ **md5 `6617c809…` ≠ target** (n 2517, equity 131878 vs 131908) |
| **Kernel C** (gate retrain → `pred.bin`) | code viết xong, **CHƯA chạy** |
| **Kernel D** (S1 + bins) | **CHƯA viết** |
| **4 arm đăng ký (cả dây chuyền)** | **NOT-RUN** — chặn ở cổng parity ⇒ theo pre-reg §4/§6 **DỪNG** |

⇒ **NO-GO (BLOCKED tại cổng parity) — giữ `f=0` (N=100).** Đây **không** phải kết luận khoa học
"biến thể kém": harness đã gỡ được blocker hạ tầng, nhưng **`market.bin` tái tạo từ ticker KHÔNG
tái lập được set `live`** mà sim nền đọc (xem §2) nên không qua được cổng parity.

**Phụ lục (KHÔNG đăng ký):** một biến thể *align* (giữ đúng tập phút của `market.bin` gốc, chỉ thay
GIÁ TRỊ rate — loại nhiễu "data availability") cho **bảng f × chỉ số** ở §3. Bảng này đo **CHỈ
đường RULE** (BIG_DOWN/DCA/size-adapt); gate+selector **KHÔNG retrain** ⇒ **KHÔNG phải** kết luận
4 tầng của pre-reg, chỉ để định hướng vòng sau.

---

## 1. HARNESS XÂY ĐƯỢC GÌ (kernel nào / bước nào)

Code: `tools/kaggle_bd_chain.py` (điều phối A/B/C + stage dataset) · `tools/kaggle_sim.py`
(thêm `market_ds` + `market_align`) · `src/main/java/.../wfo/framework/ExportMarketBinFromTicker.java`.

| bước (§2 pre-reg) | kernel / tool | trạng thái | ghi chú |
|---|---|---|---|
| 1. `market.bin` (rule path) | **Kernel A** `ExportMarketBinFromTicker` | ✅ chạy được trên Kaggle | ticker `wfo-ticker-*` → `MarketDataInlineGenerator` (buffer LIÊN TỤC), ghi format `[count][ts][down,up,down15m]`; `f` qua `SIM_BD_FRACTION` |
| 2. gate store (33 feat) | **Kernel B** (Python, `patch_gate_store`) | ✅ chạy được | chỉ 3 cột phụ thuộc market-rate: `momentum1M=rateDownAvg`, `momentum15M=rateDown15MAvg`, `momentumAcceleration=momentum5M−momentum15M` (`ComprehensiveMarketFeatureExtractor.java:93-100`); các cột khác là hàm giá-từng-coin/lịch ⇒ KHÔNG đổi theo `f` |
| 3. gate retrain → `pred.bin` | **Kernel C** | ⚠ code xong, CHƯA chạy | dùng đúng hyperparam/fold `gate_feat_study/run_cycle.py`; giữ `predRisk4H` cũ (AIRejectFilter bỏ nhánh RISK 2026-08-08) |
| 3b. S1 + bins | **Kernel D** | ⚠ CHƯA viết | cần `s1_rank.py`+`build_map.py` port lên Kaggle |
| 4. sim | `tools/kaggle_sim.py` | ✅ | thêm `market_ds` (thay `market.bin`, giữ pred/funding) + `market_align` |

**Không còn phụ thuộc Aerospike để sinh dữ liệu upstream** (chỉ sim còn cần Aerospike cho
`SimpleSymbolMapper` như mọi run Kaggle trước). Đây là phần **thực sự mới** so với vòng 2
(vòng 2 kết luận "phải xây mới"; vòng này đã xây + chạy bước 1-2).

### 1.1 Kernel A — kết quả 5 arm

Bằng chứng `SIM_BD_FRACTION` có hiệu lực: so `market.bin` giữa các f (cùng 2.627.810 dòng, cùng
tập mốc thời gian):

| so | max\|Δ\| (down/up/down15m) | mean\|Δ\| (down15m) | % phút khác |
|---|---|---|---|
| f=0.30 vs f=0 | 0.057 / 0.079 / 0.092 | 0.00175 | 99,5 % |
| f=1.00 vs f=0 | 0.150 / 0.116 / 0.178 | 0.00140 | 79,3 % (65 % vs `up`) |

⇒ `f` **thật sự** làm đổi market-rate (không phải no-op). (f=1.0 khác f=0 ở ~65-79 % phút vì khi
universe ≤ ~125 thì `min(size, size·4/5) = min(100, size·4/5)` ⇒ trùng — nhất quán với §3 pre-reg.)

---

## 2. PARITY `f=0` — **KHÔNG KHỚP** (và vì sao)

### 2.1 Tách nguyên nhân (2 run đối chứng, cùng jar HEAD `a212e79b`)

| run | `market.bin` | equity | n | md5 `printDone.csv` | kết |
|---|---|---|---|---|---|
| nền `sim-g2flat3-val` | gốc (bundle) | 131908 | 2517 | `650c386f0d0dfea334af9d55ca2f21d4` | — |
| `bdjar-par` | **gốc (bundle)** | 131908 | 2517 | **`650c386f0d0dfea334af9d55ca2f21d4`** | ✅ **PASS** |
| `bdf000-par` | **sinh lại (Kernel A, f=0)** | 131878 | 2517 | `6617c809f443affe58053b0b0e3c34e0` | ⛔ FAIL |

⇒ **JAR HEAD (có `SIM_BD_FRACTION` default 0) BYTE-IDENTICAL với `sim-jar-gdv2`** — khớp đúng kỳ
vọng của pre-reg §1 và trả nợ "chưa re-run JAR HEAD" của vòng 2. **Sai số 100 % đến từ `market.bin`
sinh lại.**

### 2.2 Vì sao `market.bin` sinh lại ≠ `market.bin` gốc

Đối chiếu `bdf000` (sinh lại) vs `market.bin` gốc trên **2.553.236 phút chung**:

| đại lượng | giá trị |
|---|---|
| % phút khớp ≤ 1e-6 (down / up / down15m) | 99,83 % / 99,83 % / 99,88 % |
| % phút khớp ≤ 1e-3 | 99,9999 % |
| max\|Δ\| down15m | 0,0060 |
| mốc THIẾU so gốc (ref-only) | **1.576** (chủ yếu 15 phút cold-start đầu 2021-01-01; 1.332 ở 2025) |
| mốc THỪA so gốc (new-only) | **74.574** (~41 phút/ngày, rải đều 2021..2025, mọi giờ) |

**Nguyên nhân:** `market.bin` gốc = dump set Aerospike `market_data` do tiến trình **LIVE** ghi —
set này **thiếu ~2,8 % số phút** (gaps của live), còn Kernel A sinh từ **ticker file** (đầy đủ hơn).
Ngoài ra ~0,17 % phút lệch giá trị nhỏ do ticker file vs feed live. Vì sim tra `market.bin` **theo
đúng phút**, tập phút khác nhau + giá trị lệch ⇒ đường rule (BIG_DOWN/DCA) đổi ⇒ parity FAIL.
**Đây là giới hạn CỐ HỮU nếu không có Aerospike** (không bịa được set live từ ticker).

### 2.3 Biến thể `align` (loại nhiễu data-availability) — chẩn đoán thêm

`market_align=1` giữ **đúng tập phút của `market.bin` gốc**, chỉ thay **giá trị rate** bằng giá trị
sinh lại. Kết quả `bdal-000` (f=0, align): **equity 131908, n 2517 — TRÙNG khớp nền**, nhưng md5
`a41d8846…` vẫn ≠ target: `diff` chỉ **104 dòng (52 lệnh)**, khác biệt **chỉ ở các cột rate ghi
kèm** (`dow/up/dow15m`), KHÔNG đổi đường lệnh. ⇒ sai số md5 còn lại là do ~0,17 % phút lệch giá trị.
Theo **đúng chữ** pre-reg §4 ("lệch ⇒ DỪNG"), đây vẫn là **FAIL cổng parity** dù kinh tế trùng khớp.

---

## 3. PHỤ LỤC (KHÔNG ĐĂNG KÝ) — bảng `f` × chỉ số, **CHỈ đường RULE**, có `align`

Điều kiện: jar HEAD, `g2_flat3`, `SIM_END_DATE=20251231`, bundle `sim-x1-2021-bundle`,
`market_align=1`. **KHÔNG** retrain gate/selector (dùng nguyên `pred.bin`/bins nền) ⇒ chỉ đo phản
ứng của rule BIG_DOWN/DCA/size-adapt với rate đổi. maxDD/Calmar tính từ **equity NGÀY** (xấp xỉ;
§9 dùng maxDD PHÚT nên số tuyệt đối khác).

| `f` | kernel | n | win% | TSloss% | equity cuối | maxDD% (ngày) | Calmar | CAGR% |
|---|---|---|---|---|---|---|---|---|
| 0.00 (=nền) | `bdal-000` | 2517 | 85,86 | 14,30 | 131908 | 10,02 | 3,42 | 34,25 |
| 0.10 | `bdal-010` | 2782 | 85,62 | 14,59 | 134174 | 11,60 | 3,00 | 34,76 |
| 0.30 | `bdal-030` | 2564 | 85,96 | 14,35 | 134799 | 10,97 | 3,18 | 34,90 |
| 0.50 | `bdal-050` | 2482 | 85,94 | 14,38 | 131663 | 10,93 | 3,13 | 34,20 |
| 1.00 | `bdal-100` | 2392 | 85,95 | 14,30 | 129958 | 10,08 | 3,36 | 33,81 |

**Đọc sơ:** đổi `f` **chỉ ở đường rule** làm `n` đổi ±10 %, equity đổi **+2 % (f=0,1/0,3)** tới
**−1,5 % (f=1,0)**; win%/TSloss% gần như phẳng; **maxDD TĂNG** (10,0 → 11,6 % ở f=0,1) ⇒ **Calmar
của MỌI f đều THẤP HƠN nền** (3,42; gần nhất f=1,0 = 3,36). Số này **không dùng để kết luận 4 tầng**
(thiếu retrain model).

**Trôi theo năm:** f=0,1 tăng pnl ở 2021/2022/2023/2025; f=1,0 **giảm** ở 2024 (2539 vs 2794) và
2025 (2644 vs 2887); f=0,5 giảm ở 2024/2025. ⇒ **không có f «tốt dần theo năm»**; xu hướng ngược
ở f lớn về cuối kỳ (non-stationarity như `RESULT_BD_DEEP §3.4`).

_Lưu ý nhỏ: `PROFILE_HASH` của `bdal-100` = `61e1c515…` khác 4 run còn lại (`c47b73f3…`) — nên đọc
bảng như xấp xỉ; đây là phụ lục định hướng, không phải kết luận._

---

## 4. TRẢ LỜI (theo thực tế đã làm)

1. **Harness xây được chưa?** → **Có, bước 1-2**: Kernel A (market.bin từ ticker, 5 f) + Kernel B
   (patch gate store) đã **chạy thành công** trên Kaggle. Bước 3 (retrain gate) **code xong chưa
   chạy**; bước 3b (S1+bins) **chưa viết**; bước 4 (sim) đã có + mở rộng.
2. **Parity `f=0` khớp?** → **KHÔNG** khi dùng `market.bin` sinh lại (md5 `6617c809…` vs
   `650c386f…`). **NHƯNG jar HEAD khớp byte-identical** khi giữ `market.bin` gốc (`bdjar-par` PASS).
   ⇒ lỗi ở tầng dữ liệu (set live vs ticker), không ở code.
3. **Bảng `f` × chỉ số + f nào qua 4 tầng?** → Có **bảng phụ lục** (rule-path, §3); **không f nào
   qua T4** (Calmar đều < nền). **4 arm ĐĂNG KÝ: NOT-RUN** (chặn ở cổng parity).
4. **Trôi theo năm hết chưa?** → Trong phụ lục: **không thấy** f cải thiện dần theo năm; chưa đo
   được theo dây chuyền đăng ký.
5. **Kết luận dứt khoát?** → **NO-GO / BLOCKED tại cổng parity — giữ `f=0` (N=100).** Không phải
   "biến thể kém"; là **chưa qua được cổng parity của dây chuyền đăng ký**.

---

## 5. MỤC BỎ + LÝ DO

- **Bỏ VIỆC 2/3 (4 arm đăng ký + chấm 4 tầng + CI)**: pre-reg §4 chốt "parity lệch ⇒ DỪNG, không
  chấm tiếp"; `f=0` sinh lại lệch md5 ⇒ DỪNG. Không bịa số.
- **Giữ**: Kernel A/B (harness mới, đã chạy) + `kaggle_sim` override + phụ lục align (nhãn rõ
  KHÔNG đăng ký) + commit/push.
- **Còn nợ (vòng sau):** (i) nguồn `market.bin` khớp set live — cần **dump Aerospike read-only
  trên Oracle → dataset Kaggle** (đề xuất duy nhất trung thực); (ii) Kernel C chạy + Kernel D viết;
  (iii) chấm §9 PHÚT đầy đủ (T1-T4, CI block-72h ×1,21).
