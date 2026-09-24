# DIAG_GATE_LIVE_VS_OFFLINE — Đo lại biên cổng (B0) + so p15 LIVE vs OFFLINE (B5)

- **Ngày**: 2026-09-24 (giờ VN). Branch `module`. Task **READ-ONLY**.
- **Phạm vi**: không start/stop/restart service · không sửa `config.properties`/`env.sh` · **không ghi**
  vào `/home/ubuntu/shadow_c3/` · không chạm 242 · không đọc/in key · **không `pgrep -af`** · không Claude
  Code · **không chạy Java/sim** · không push. Chỉ đọc log + file artifact + source; phân tích bằng Python
  chỉ-đọc (script tạm ở `/tmp`, không vào repo).
- **Nguồn**: `shadow_c3/app/logs/full.log` (466 tick), `claudedata/wfo_gate_pred.csv` (n=2,500,260,
  2021-03-31→2025-12-31), `claudedata/wfo_gate_pred_2026_H1.csv` (n=260,183, 2026-01-01→2026-06-30),
  `wfo_ds_x1_2021/{pred.bin,manifest.txt}`, `predwf_map_s1a2_x1_2021/predict_wf_2025*.bin`,
  `claudedata/wfo_models/fold_20/`, source `EntryGate.java` / `DetectEntrySignal2TradeNormal.java` /
  `OnnxInferenceManager.java` / `AIRejectFilter.java` / `SimulatorMarketLevelTicker1MStopLoss.java`.
- **Tiền đề của task đã cập nhật**: `docs/DIAG_FORWARD_PIPELINE.md` (commit `b35b231`) giả thuyết "cổng đóng
  sát biên vì p15 live lệch ⇒ bug-class". **Kết luận của tài liệu này: KHÔNG tìm được lệch định nghĩa
  p15 live-vs-offline.** Cổng đóng **đúng cơ chế**, và **0 lệnh trong 4.3 ngày là kết quả ĐƯỢC DỰ ĐOÁN**
  (kỳ vọng 0.04–0.26 PASS trong cửa sổ 325 tick). Có **2 khoảng trống cấu trúc** đáng ghi (mục 6).

---

## 1. TL;DR

1. **B0 (biên cổng)**: 325/325 chu kỳ `n_pass=0`; `gap = max(pred15M) − min(thr)` **luôn âm**
   (min −2.92pp, p50 −2.13pp, **sát nhất −0.021pp**). `thr_min` per tick ∈ [2.311%..3.724%],
   p50 = **3.129%**; p15 live ∈ [0.534%..2.302%], p50 = **0.986%**. Đổi jar 20/09 22:06 **không đổi p15**
   (p50 pre 1.000% vs post 0.986%) — nó chỉ đổi **cơ chế cổng** (phẳng 0.008 → động ×1.70).
2. **B5 (p15 live vs offline)**: **không so được cùng mốc thời gian** — artifact offline **kết thúc
   2026-06-30**, live bắt đầu 2026-09-20 (không có cửa sổ giao nhau, đúng như `docs/L1_SHADOW_C3.md` §(d)
   đã ghi là blocker). So theo **phân bố** trên cửa sổ gần nhất:
   | | n | p50 | p90 | p99 | max |
   |---|---|---|---|---|---|
   | LIVE 20/09→24/09 (2026) | 325 | **0.986** | **1.196** | 1.424 | **2.302** |
   | OFFLINE 2026H1 (01→06/2026) | 260,183 | 0.859 | 1.078 | 1.319 | 37.773 |
   | OFFLINE 2021-2025 (`pred.bin`) | 2,500,260 | 0.545 | 0.837 | 1.308 | 12.261 |
   p50 live **+15%** so với offline-2026H1, **+2.5%** so với riêng tháng 2026-04 (0.962).
   **max live 2.302% = phân vị 99.97 của 2026H1 và 99.84 của 2021-25** ⇒ **đuôi live KHÔNG mỏng hơn
   offline; nếu khác thì là DÀY hơn.** Không có hệ số scale/offset nào.
3. **Chuỗi model đã kiểm**: ONNX p15 live (md5 `8ec99757…`, 144,774 B) **trùng byte-for-byte** với
   `claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx` — tức **đúng họ model WFO fold** đã
   sinh `wfo_gate_pred.csv`; `pred.bin` khớp từng giá trị với csv đó (verify 5/5 mốc). Feature class
   `ComprehensiveMarketFeatureExtractor` dùng chung 2 phía. → **live ≡ offline về định nghĩa p15**.
4. **Ngưỡng cũng khớp**: `thr_min`/tick offline (tính lại từ `predict_wf` bins, top-8 score thấp nhất,
   2025Q3, n=8,831 tick) = min 1.77%, **p50 3.334%**, p90 3.714%, max 4.561% vs LIVE min 2.311%,
   **p50 3.129%**, max 3.724%. `symbolPred` rank-1 offline: min 0.152 / p50 0.286 / max 0.391 vs live
   top-8 0.304–0.321 → **cùng thang**.
5. **Kỳ vọng PASS (counterfactual, số quyết định)**: dùng đúng 325 mốc/tick và `thr_min` thật của live,
   áp CDF offline ⇒ kỳ vọng **0.04 PASS** (CDF 2026H1) / **0.26 PASS** (CDF 2021-25) trong 4.3 ngày.
   `P(0 PASS) = 96% / 77%`. ⇒ **`n_pass=0` không phải bằng chứng lỗi**; "sát biên −0.021pp" là nhiễu
   mẫu nhỏ (bài học: 1 lần gần-đạt không có thông tin).
6. **Hai khoảng trống cấu trúc phát hiện thêm** (không phải bug p15): (a) p15 offline cho chính khối OOS
   của model đang chạy (≈2026-07-01→2026-10-01, **trùm đúng cửa sổ live**) **chưa từng được sinh** ⇒
   không có phép đo đồng-mốc và hiệu chuẩn `scale=1.70` vẫn dựa trên đuôi 2021-25 **dày gấp ~5 lần 2026**;
   (b) `ENTRY_GRID_MIN = 15L` (hardcode, `DetectEntrySignal2TradeNormal:988`) ⇒ live chỉ đánh giá cổng
   **mỗi 15 phút**, còn sim đánh giá **~1 phút** (`n_cand=17,925,650` ÷ 1645 ngày ≈ 10,898 signal/ngày
   ≈ 1440 tick/ngày) ⇒ live có **~1/15 số cơ hội** so với backtest.

---

## 2. B0 — ĐO LẠI BIÊN CỦA CỔNG (log thật)

### 2.1 Số chu kỳ và khoảng cách
- `[GATE]` tổng **325 dòng**; **`n_pass=0`: 325/325 (100%)**; không một dòng `n_pass>0`.
- Cửa sổ: `20/09/2026 22:19:00` → `24/09/2026 13:04:26` (3.615 ngày, cadence ~15 phút).
- Nhịp tick: 376/466 delta ≈ 15 phút, 36 delta ≈ 16 phút, 30 delta ≈ 14 phút (khớp `ENTRY_GRID_MIN=15`).

| đại lượng (per tick) | min | p50 | p90 | max |
|---|---|---|---|---|
| `thr` cận dưới (dễ nhất) | **2.311%** | **3.129%** | 3.393% | **3.724%** |
| `thr` cận trên | 2.580% | 3.587% | 3.845% | **4.107%** |
| `pred15M` live (p15) | 0.534% | 0.986% | 1.196% | **2.302%** |
| `gap = max(pred15M) − min(thr)` | **−2.924pp** | **−2.133pp** | −1.782pp | **−0.021pp** |

⇒ **`gap < 0` ở 325/325 tick** (không lần nào ≥ 0). Tick sát nhất: `20/09/2026 22:19:00`
(p15 1.1905% vs thr 2.9770%, hụt 0.0179pp). `thr_min` trung vị 3.129% **cao hơn mọi p15 quan sát được**.

### 2.2 Đối chiếu cửa sổ trước/sau khi đổi jar (20/09 22:19 = dòng `[GATE]` đầu tiên)
Jar đổi mtime `20/09 22:06` (kèm `.bak_20260920_stubkey`) ⇒ ranh giới `[GATE]` đầu tiên 22:19:00.
Dòng `🔕 [PREDICT fail]` + `Predict: {"return15M":…}` có **trước cả** ranh giới (từ 18/09 19:34).

| cửa sổ | n tick | p15 p50 | p15 max | cổng |
|---|---|---|---|---|
| TRƯỚC (18/09 18:34 → 20/09 22:19, jar cũ) | 141 | **1.000%** | 1.567% | **PHẲNG** 0.008 (không có dòng `[GATE]`) |
| SAU (20/09 22:19 → 24/09 13:04, jar mới) | 325 | **0.986%** | 2.302% | động ×1.700 (`[GATE]` mỗi tick) |

- **p15 không đổi** giữa hai cửa sổ (p50 1.000% → 0.986%, Δ = −1.4%) ⇒ việc thay jar **không đổi model/
  feature của p15**, chỉ đổi **đường quyết định cổng**. Đây là bằng chứng trực tiếp rằng "dừng lệnh 20/09"
  là **do cổng**, không do drift dữ liệu/model.
- Kiểm chứng chéo cơ chế cổng phẳng: tỉ lệ `p15 ≥ 0.80%` trên toàn bộ 466 tick = **87.1%** ⇒ cổng phẳng
  0.008 phải cho qua ~87% số tick ⇒ nhịp ~13–20 lệnh/ngày quan sát 18–20/09 **khớp hoàn toàn**.
  Với cổng động ×1.70, tỉ lệ đó rơi xuống **0%**.
- Công thức khớp code (`EntryGate.threshold`): `thr = 0.008 × max(0.26787, (sp/0.15)×1.2876) × 1.70`;
  với `sp` top-8 = 0.304–0.321 ⇒ `thr` = **3.55%–3.74%** ✔ khớp log (`thr=[0.03102..0.03396]` …).

### 2.3 Vì sao `n_pass=0` là *hệ quả cơ học* chứ không phải bất thường
Cổng yêu cầu `p15 ≥ thr`, mà `thr ≥ 2.311%`. Trên nền offline 2026H1, chỉ **0.0315% số phút** có
`p15 ≥ 2.31%` (82/260,183) và **0.0069%** có `p15 ≥ 4.0%` (18/260,183). Dùng đúng 325 mốc tick và
`thr_min` thật của live:

| CDF dùng để đối chiếu | Σ P(p15 ≥ thr_min) trên 325 tick | P(0 PASS) |
|---|---|---|
| LIVE tự thân (p15 p50 0.986, max 2.302) | 0.00 (theo định nghĩa) | 100% |
| OFFLINE 2021-2025 (`pred.bin`) | **0.26** | 77% |
| OFFLINE 2026H1 | **0.04** | 96% |

---

## 3. B5 — p15 LIVE vs OFFLINE CÙNG KỲ

### 3.1 Ràng buộc: KHÔNG có cửa sổ giao nhau (không thể "cùng mốc thời gian")
- `wfo_gate_pred.csv` / `pred.bin` bao **2021-03-31 → 2025-12-31** 23:59 (`manifest.txt`,
  `marketRange=1609459200000..1767225540000`, `predCount=2,500,260`).
- `wfo_gate_pred_2026_H1.csv` bao **2026-01-01 → 2026-06-30** (260,183 mốc, lưới **1 phút**:
  ts cách nhau 60,000 ms).
- Live (log còn lại) bao **2026-09-20 22:19 → nay**.
⇒ **Không mốc nào trùng** ⇒ chỉ so được **phân bố** (và so **phân vị**), không so được **tương quan
theo mốc**. Đây chính là blocker đã ghi ở `docs/L1_SHADOW_C3.md` §(d) ("chưa chứng minh được đồng nhất")
— tài liệu này **không phá được blocker đó**, nhưng **đã đo được** phần đo được (lệch phân bố).

### 3.2 Phân bố

| tập | n | min | p50 | p90 | p95 | p99 | p99.5 | p99.9 | max | mean |
|---|---|---|---|---|---|---|---|---|---|---|
| LIVE 20→24/09/2026 | 325 | 0.534 | **0.986** | **1.196** | 1.266 | 1.424 | – | – | **2.302** | 0.991 |
| OFFLINE 2026H1 | 260,183 | 0.396 | 0.859 | 1.078 | 1.155 | 1.319 | 1.394 | 1.762 | 37.773 | 0.846 |
| OFFLINE 2021-2025 | 2,500,260 | 0.202 | 0.545 | 0.837 | 0.960 | 1.308 | 1.585 | 2.818 | 12.261 | 0.585 |

**Theo tháng (offline 2026H1)** — cho thấy biên độ tháng lớn, nên "p50 lệch 15%" nằm gọn trong dao động:

| tháng | n | p50 | mean | #(p15≥2.31%) | #(p15≥3.13%) |
|---|---|---|---|---|---|
| 2026-01 | 44,640 | 0.846 | 0.851 | 12 | 6 |
| 2026-02 | 40,320 | 0.917 | 0.933 | 58 | 24 |
| 2026-03 | 44,640 | 0.871 | 0.870 | **0** | **0** |
| 2026-04 | 43,200 | **0.962** | 0.968 | 2 | 1 |
| 2026-05 | 44,640 | 0.833 | 0.829 | **0** | **0** |
| 2026-06 | 42,743 | **0.536** | 0.628 | 10 | 3 |

- p50 live 0.986 nằm **trong dải tháng** offline 2026 (0.536–0.962), thậm chí **trên đỉnh dải**.
- p90 live 1.196 vs offline-2026H1 p90 1.078 → live **+11%** (rộng hơn).
- **Đuôi**: `max` live 2.302% = phân vị **99.968** của 2026H1 (83/260,183 quan sát ≥ 2.302%).
  Kỳ vọng max của mẫu n=325 theo CDF 2026H1 ≈ p99.7 = 1.478% ⇒ **max live 2.302% CAO HƠN kỳ vọng**.
  Theo CDF 2021-25 (p99.7 = 1.838%) thì live cũng cao hơn. ⇒ **không có thiếu hụt đuôi**.

### 3.3 Kiểm từng nghi vấn lệch (checklist của task)
| Nghi vấn | Kết quả | Bằng chứng |
|---|---|---|
| Hệ số scale/offset | **KHÔNG** | p50 live/off-2026H1 = 1.15; /off-2026-04 = 1.025. Không có bội số hằng nào |
| Model khác (S1 vs net015 vs gate_model_v2) | **KHÔNG (đã loại)** | live ONNX md5 `8ec9975726270782692bfe00b39bd37f` = `claudedata/wfo_models/fold_20/…` (byte-identical). `wfo_models` là nguồn của `wfo_gate_pred*.csv` (`WFOGateRunner:61,142`) |
| Feature window khác (15m vs 1m) | **KHÔNG ở tầng feature** | Live dùng `ComprehensiveMarketFeatureExtractor` (Detect…:1017) = đúng class offline dùng (`GenerateGate15mV2Predictions:83`). Khác duy nhất: **nhịp gọi cổng** 15m vs 1m (mục 6b) |
| Đơn vị (% vs số thực) | **KHÔNG** | live log in `predictData.return15M*100`; `Predict: {"return15M":0.009933}` ↔ `market[15M:0.99%]` nhất quán |
| Đơn vị thời gian (ms/s) | **KHÔNG** | `time`, `tick=1790225946014` (ms) khớp bins/`wfo_gate_pred` (ms) |
| Clamp / NaN | **KHÔNG thấy** | live p15 ∈ [0.534..2.302] liên tục, không dồn ở biên; model regressor không bị chặn (offline max 12–37%) |
| p15 ≠ p15 (tên artifact) | **CẢNH BÁO** | `pred.bin` **không** phải từ `~/claudedata/gate_model_v2/Model_Regressor_Return15M.onnx` (md5 `51bfee1a…`, 136,713 B, `train_meta: label_oldbasket, cutoff 20250601`). `pred.bin` verify **khớp từng giá trị** với `wfo_gate_pred.csv` (5/5 mốc đầu) ⇒ nguồn là `wfo_models/fold_*`. `gate_model_v2` là artifact TASK-043 (`ai_pred_market_gate_v2`) — **dễ bị nhầm khi audit sau này** |

### 3.4 Ngưỡng (`symbolPred`) — đo lại từ bins để đối chiếu
Tính lại `thr_min`/tick offline bằng dữ liệu selector offline (`predwf_map_s1a2_x1_2021/predict_wf_20250701.bin`,
26B: `ts(long), sym(short), p4h,p12h,p24h,p72h(float)`, `score = 1 − P(win)`, horizon idx 0 = 4h;
chọn 8 score nhỏ nhất/tick = top-8):

| | n tick | min | p50 | p90 | max |
|---|---|---|---|---|---|
| OFFLINE `thr_min` (2025Q3) | 8,831 | **1.769%** | **3.334%** | 3.714% | **4.561%** |
| LIVE `thr_min` (20→24/09) | 325 | **2.311%** | **3.129%** | 3.393% | **3.724%** |

`symbolPred` rank-1 offline: min 0.1515 / p50 0.2856 / max 0.3907; live top-8 = 0.304–0.321 (giữa dải).
⇒ **thang giá trị của cổng (thr) khớp giữa live và offline (lệch p50 ≈ 6%)**. Không có
"symbolPred live bị đẩy lên ~2 lần" như một giả thuyết có thể có (ghi chú `docs/G4_RECIPE_C4.md` §6.2
về "net015 lệch hiệu chuẩn 2 lần" là chuyện của **nhánh giá trị khác**, không áp cho cặp này).

---

## 4. KẾT LUẬN (trả lời trực tiếp)

**(1) Cổng đóng THẬT không?** — **Đóng thật, đúng cơ chế.** 325/325 `n_pass=0`; `gap(max p15 − min thr)`
luôn âm (sát nhất −0.021pp); `thr_min` p50 = **3.129%** trong khi p15 live p50 = **0.986%**, max 2.302%.
Nhưng **cách diễn giải "sát biên ⇒ cổng không thể mở" là SAI thống kê**: với `thr` đó, kỳ vọng PASS
trong 4.3 ngày chỉ **0.04–0.26** ⇒ `n_pass=0` là **kết quả kỳ vọng (P=77–96%)**.

**(2) p15 live lệch offline bao nhiêu & vì sao?** — **Lệch rất ít và cùng chiều CAO, không có bội số
hay offset**: p50 0.986% vs 0.859% (off-2026H1, **+15%**) / 0.962% (off-2026-04, **+2.5%**);
p90 +11%; **max live 2.302% nằm ở phân vị 99.97 của offline 2026H1** (đuôi không hụt mà hơi dày).
Nguyên nhân duy nhất tìm được là **khác kỳ/khác tháng** (offline 2026 có dao động p50 0.536–0.962 theo
tháng), **không phải** scale/offset, không phải model khác (ONNX live **trùng byte** với
`wfo_models/fold_20` = họ model sinh chính `wfo_gate_pred*`), không phải feature class khác, không phải
lệch đơn vị, không clamp. **Tương quan theo mốc: KHÔNG tính được** (offline dừng 2026-06-30, live từ
2026-09-20; không cửa sổ giao nhau).

**(3) Nếu là bug ⇒ fix?** — **Không tìm thấy bug ở tầng định nghĩa p15 / thang cổng.** Do đó **không có
fix** cho giả thuyết "p15 live lệch". Hai khoảng trống cấu trúc (đề xuất cho owner quyết, **không tự sửa**):
- **(a) Thiếu tham chiếu đồng-mốc**: p15 offline cho OOS block của chính model đang chạy
  (`wfo_models/fold_20`, OOS ≈ 2026-07-01→2026-10-01, **trùm đúng cửa sổ live**) **chưa từng được sinh**;
  muốn có phép đo "dut diem re nhat" (như L1 §(d) đề xuất) phải regenerate p15 cho 2026-07→09 **bằng
  đúng fold_20** trên feature store gate. Hiện **feature store chưa có** phần này ⇒ vẫn là blocker.
- **(b) Lệch nhịp đánh giá cổng live-vs-sim**: `ENTRY_GRID_MIN = 15L` **hardcode** trong
  `src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java:988`, dùng ở
  `isTimeProcessData()` (:991-1004) ⇒ **live chỉ xét cổng tại :00/:15/:30/:45** (~96 tick/ngày), trong khi
  sim xét **~1 phút/tick** (`SimulatorMarketLevelTicker1MStopLoss`, `n_cand=17,925,650` ÷ 1645 ngày
  ≈ 10,898 signal/ngày ≈ 1440 tick/ngày). ⇒ **live có ~1/15 số cơ hội vào lệnh so với mốc backtest**
  (0.51 PASS/ngày của T170 là ở nhịp 1 phút). Đây là **khác biệt live↔sim thật**, độc lập với p15, và nó
  làm nhịp lệnh forward thấp hơn nữa so với con số backtest. (Tài liệu archive
  `v1_live_deploy_15m_grid_2026-08-17.md` ghi `LIVE_ENTRY_GRID_MIN` đọc từ env, **nhưng code hiện tại là
  hằng số hardcode** ⇒ muốn đổi phải rebuild jar, không phải đổi config.)

**(4) Nếu p15 live ĐÚNG ⇒ nói rõ + ý nghĩa thị trường?** — **p15 live ĐÚNG (theo phân bố, mức bằng chứng
cao nhất hiện có)**. Ý nghĩa:
- **"Thị trường duyên hải" theo đúng nghĩa ĐUÔI MỎNG, không phải "im lặng"**: p50/p90 live nằm *trên* mức
  offline 2026 ⇒ phần thân phân bố **không** thấp. Nhưng **đuôi để mở cổng thì cực hiếm**: offline 2026
  chỉ **82/260,183 phút (0.0315%)** có `p15 ≥ 2.31%`, và **có tháng = 0** (2026-03, 2026-05: 0 tick);
  `p15 ≥ 3.13%` (mức `thr_min` trung vị của live) chỉ **34 phút trong 181 ngày** (0.013%).
- **Cổng `scale=1.70` đang được hiệu chuẩn trên một phân bố KHÁC**: `0.64 lệnh/ngày` của T170 đo trên
  2021-25, nơi `P(p15 ≥ 2.31%) = 0.158%` — **đuôi dày hơn 2026 khoảng 5 lần**. Trên nền 2026, nhịp lệnh
  kỳ vọng của cổng này ≈ **0.02–0.05 lệnh/ngày ở nhịp 15 phút** (⇒ ~1 lệnh mỗi 20–50 ngày). Forward
  evidence ở cấu hình hiện tại **gần như đứng yên vì thiết kế cổng + chế độ thị trường, không vì lỗi.**
- Đây **là quyết định của owner**, không phải việc agent: (i) hạ `SIM_GATE_DYN_SCALE` (đổi live, cần
  pre-reg + holdout), hoặc (ii) chấp nhận nhịp ~1 lệnh/20–50 ngày (⇒ forward gần như vô dụng cho quyết
  định), hoặc (iii) re-threshold theo phân bố p15 2026 (đang 2026 thật, không tune trên holdout).
  **Không tự sửa trong task này.**

---

## 5. MỤC NÀO BỎ + LÝ DO

| Hạng mục task | Trạng thái | Lý do |
|---|---|---|
| B0: đo `thr`, `pred15M`, đếm `n_pass>0`/`=0`, khoảng cách max−min, đối chiếu trước/sau 20/09 22:19 | **LÀM ĐỦ** | §2 (325 tick, gap luôn âm, pre/post p50 1.000 vs 0.986) |
| B5: trích p15/pred15M live 20/09→nay | **LÀM ĐỦ** | §3.2 (325 mẫu, min/p50/p90/p99/max/mean) |
| B5: tính lại offline **cho cùng symbol + cùng mốc thời gian** | **BỎ — bất khả thi** | artifact offline kết thúc **2026-06-30**; live bắt đầu 2026-09-20; không cửa sổ giao nhau (khớp ghi chú L1 §(d)). Muốn có phải **regenerate p15 bằng `wfo_models/fold_20` trên feature store 2026-07→09** — cần chạy Java/sim (bị cấm trong task) và feature store hiện **chưa có** phần đó |
| B5: **tương quan** live↔offline | **BỎ** | Hệ quả của mục trên: không có cặp (ts, p15) nào chung. Đã thay bằng: phân bố + phân vị + counterfactual kỳ vọng PASS |
| B5: đối chiếu `ai_predictions.data_v3_FULL` | **BỎ — thay nguồn** | `FILE_AI_PREDICTIONS=../storage/ai_ml/ai_predictions.data_v3_FULL` là **cache file của DEV sim**, không tồn tại trên host này (`find /` = 0 hit) và **không phủ 2026-09**. Thay bằng `wfo_gate_pred_2026_H1.csv` (offline 2026, gần live nhất) + `pred.bin`/`wfo_gate_pred.csv` (2021-25) |
| B5: `wfo_ds_x1_2021/pred.bin` cho "cùng mốc" | **LÀM MỘT PHẦN** | Dùng để (i) lấy phân bố 2021-25, (ii) **verify chuỗi provenance** (khớp 5/5 giá trị với `wfo_gate_pred.csv`) — nhưng chỉ phủ ≤ 2025-12-31 |
| Đọc/in key, chạm 242, ghi `shadow_c3/`, restart service, `pgrep -af`, chạy Java/sim, push | **KHÔNG LÀM (đúng ràng buộc)** | — |

**Ghi chú phương pháp (để người sau kiểm lại được)**: phân tích chỉ-đọc bằng Python script tạm ở `/tmp`
(`b05.py`, `b05b.py`); KHÔNG ghi gì vào `/home/ubuntu/shadow_c3/`; output tool giữ nhỏ (grep/tail/sed/head).
Phép tính `thr_min` offline ở §3.4 dùng `predict_wf_20250701.bin` (1 file = 1 fold OOS 2025Q3,
8,831 tick, 461 symbol/tick trung vị) làm mẫu — chưa quét toàn bộ 18 file; đủ để so **thang** (p50 lệch 6%).

---

## 6. VIỆC ĐỀ XUẤT (KHÔNG TỰ CHẠY)

- **B-W1 (đo, rẻ)**: regenerate p15 offline cho **2026-07-01 → 2026-10-01 bằng đúng `wfo_models/fold_20`**
  (model trùng byte với live) ⇒ có phép đo **đồng-mốc** thật cho p15 live vs offline, và có CDF 2026 mùa
  hè/thu để tính kỳ vọng PASS chuẩn. Cần feature store gate kéo dài qua 2026-07 ⇒ **blocker riêng** (như L1 §(d)).
- **B-W2 (mở rộng cửa sổ đo)**: để kết luận được "cổng có bao giờ mở", cần **≥ 1,250 tick ≈ 14 ngày**
  (nền CDF 2021-25) hoặc **≈ 8,000 tick ≈ 90 ngày** (nền CDF 2026) mới có kỳ vọng ≥ 1 PASS. Ghi vào
  watchdog thay vì kết luận sớm từ 3.6 ngày.
- **B-W3 (báo cáo cho owner, KHÔNG tự sửa)**: (i) lệch nhịp cổng live 15m vs sim 1m (`ENTRY_GRID_MIN`);
  (ii) `scale=1.70` hiệu chuẩn trên đuôi 2021-25 (dày ~5× so với 2026) ⇒ nhịp forward kỳ vọng
  ~0.02–0.05 lệnh/ngày ở nhịp 15m; (iii) cảnh báo audit: `pred.bin` **không** từ `gate_model_v2`
  (md5 `51bfee1a…`) mà từ `wfo_models/fold_*` (md5 fold_20 `8ec99757…` = model live).
