# RESULT V3 — PARITY HARNESS (`research/parity/parity_check.py`)

> V3 = V2 (`aa9ecb92`) + **sửa/đo bug writer GZ** + **marketparams 4/4 field** + **selector/gate-p15 đo được** + **phân nhóm 26 feature lệch**.
> Harness: `research/parity/parity_check.py`. Report tự sinh: `docs/result/parity_report.{json,md}`. Pre-reg gốc: `docs/prereg/PREREG_PARITY_HARNESS.md` (không sửa). Ngày 2026-10-01 (GMT+7).

> ⛔ **2026 = HOLDOUT**: mọi số 2026 (nhất là LIVE 2026-09) **chỉ audit/đối chiếu**, KHÔNG chọn/tune tham số.
> Ràng buộc giữ đủ: **Python thuần · 0 Java/sim trên Oracle · 242 READ-ONLY · 0 ONNX · không push data · không in secret.**

## 0. KẾT QUẢ TỔNG: `FAIL` (exit_code=2)

| tầng | V2 | V3 | ghi chú |
|---|---|---|---|
| config | FAIL (4 LECH + 18 MISSING) | **PASS** | 242 đổi ngoài (snapshot 71 key, fetch 11:04) ⇒ MATCH 27/27 |
| features | FAIL 27/33 | FAIL 27/33 | nay **đã phân nhóm** (i=20 · ii=1 · iii=6) |
| gate | FAIL (mode=fixed) | **MISSING** | mode nay = `ratio` (PASS); **có p15 DEV dump**; cung-phút vẫn MISSING |
| **marketparams** | MISSING (2/4) | **MISSING (4/4 đo được)** | 3 field khớp mức nhiễu; `rateUp15MAvg`=0 hai phía |
| selector | MISSING | **MISSING** | nay **đo được phía LIVE** (249 tick/163.520 dòng), thiếu đối ứng cung-tick |
| entry | FAIL | FAIL | không đổi (0 vs ≥1) |
| exit | MISSING | MISSING | không đổi |

Selftest **4/4 PASS** (thêm `gz_writer_finalize`). Ghi chú: `config` PASS là do **tiến trình khác đã cập nhật config 242** trước phiên này (snapshot md5 `c977f4b9…`) — KHÔNG do harness/ta sửa.

---

## 1. VIỆC 1 — BUG WRITER GZ (đã xác định file:line; **ĐỀ XUẤT, không sửa**)

**Writer = `LiveFeatureDump`** (`src/main/java/com/binance/chuyennd/ai_ml/features/export/entry/LiveFeatureDump.java`), gọi từ **đường LIVE** `DetectEntrySignal2TradeNormal.java:299`.
⇒ Theo ràng buộc "(đụng LIVE cần owner duyệt / nếu là đường LIVE ⇒ chỉ đề xuất)": **KHÔNG sửa code Java**; chỉ nêu bằng chứng + patch đề xuất.

**Bằng chứng (6/6 file, đo trên đúng artifact harness dùng):**

| file | bytes | gz trailer | tail 4 byte | giải nén full |
|---|---|---|---|---|
| `live_242/feat_dump_20260928_084506.csv.gz` | 45.627 | ✗ | `0000ffff` | ✗ |
| `live_242/feat_dump_20260928_124506.csv.gz` | 24.179 | ✗ | `0000ffff` | ✗ |
| `shadow_c3/…_084006` / `_124006` / `_164106` / `_204206` | 11–12 KB | ✗ | `0000ffff` | ✗ |

**Cơ chế (khớp code):** `open()` tạo `new GZIPOutputStream(counter, 16384, true)` (**syncFlush=true**) — dòng 133-136; `maybeDump()` gọi `writer.flush()` **mỗi dòng** — dòng 98. Vì vậy file luôn kết thúc bằng **DEFLATE sync-flush block rỗng `00 00 FF FF`**, nhưng **trailer GZIP (CRC32+ISIZE) chỉ được ghi khi `close()`** — dòng 148-155. `close()` **chỉ** được gọi khi `rowsWritten >= REMAINING` (242 đặt `LIVE_FEAT_DUMP=3000`) hoặc chạm trần 200 MB ⇒ **JVM restart/stop giữa chừng ⇒ không bao giờ finalize ⇒ thiếu trailer.** KHÔNG có `Runtime.addShutdownHook` cho dump (so sánh: `LiveGateRollingRatio.java:313` CÓ hook ⇒ pattern đã có sẵn trong repo).

**Tái lập cơ chế (deterministic, Python — selftest `gz_writer_finalize`):** mô phỏng `zlib.compressobj(wbits=31)` + `flush(Z_SYNC_FLUSH)` mỗi dòng, **không close** ⇒ `gzip.decompress` **FAIL**, tail `0000ffff` (khớp file thật); thêm `flush()` (finish = tương đương `close()`) ⇒ **OK**. ⇒ Bug tái lập được, và **dữ liệu không mất** (harness đọc dòng hoàn chỉnh bằng partial-inflate) — cái mất chỉ là **trailer + lần restart cắt file**.

**PATCH ĐỀ XUẤT (chỉ thêm finalize, 0 đổi logic giao dịch):** thêm shutdown hook 1 lần (giống `LiveGateRollingRatio`), ví dụ chèn vào `LiveFeatureDump`:

```java
private static boolean hookInstalled = false;
private static synchronized void installShutdownHook() {
    if (hookInstalled || REMAINING <= 0) return;
    hookInstalled = true;
    try {
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try { close(); } catch (Exception ignore) {}
        }, "LiveFeatureDumpFinalize"));
    } catch (Exception e) { LOG.warn("khong dang ky shutdown hook: {}", e.getMessage()); }
}
// goi installShutdownHook() trong static{} khi REMAINING>0 (hoac lan open() dau tien)
```

(Tùy chọn mạnh hơn: **xoay file** theo giờ/tick để mỗi file luôn được `close()`.) ⇒ Sau khi deploy, harness sẽ báo `thieu-trailer=0`. **Việc còn lại của VIỆC 1 = owner duyệt patch LIVE** (không tự sửa).

---

## 2. VIỆC 2 — MARKETPARAMS ĐỦ **4/4** FIELD

Nguồn: `--md-inline` **tương đương** = xuất CSV 4 field từ port `calMarketData` (`dump_marketparams_csv` → `research/parity/data/marketparams_inline.csv`, 1.426 phút). So cùng phút với (a) LIVE feat_dump, (b) DEV store `market.bin` (đã xác minh `WfoDataset`: `count × [ts][3 float: down,up,down15m]` ⇒ có `rateUpAvg`).

| field | so sánh | n | max\|Δ\| | corr | kết |
|---|---|---|---|---|---|
| `rateDownAvg` | LIVE↔inline | 502 | **7,49e-4** | 0,99485 | PASS (≤1e-3) |
| `rateDown15MAvg` | LIVE↔inline | 502 | **7,40e-4** | 0,99958 | PASS |
| `rateDownAvg` | DEV store↔inline | 1376 | 9,79e-4 | 0,9970 | PASS |
| **`rateUpAvg`** | DEV store↔inline | 1376 | **6,20e-4** | 0,9973 | **PASS (mới đo)** |
| `rateDown15MAvg` | DEV store↔inline | 1376 | 2,03e-3 | 0,9977 | PASS (mức nhiễu ngày crash) |
| **`rateUp15MAvg`** | hai phía | 1376 | **0** | 1,0 | PASS = **0 cả hai phía** (`calMarketData` ctor 3 field; market.bin 3 float) |

⇒ **4/4 field đo được**, tất cả ở **mức nhiễu ticker-vs-kline** (không phải lỗi logic). Ngưỡng `MS_DOWN_BIG_AVG/_DCA/MS_UP_BIG_THRES`: 242 & baseline đều UNSET ⇒ **MATCH-DEFAULT** (-0,03157/-0,03157/0,02046). Flip quyết định: **LIVE BIG_DOWN 0 / DCA 0** (502 phút); **DEV stress 2025-10-10 DCA 1** (1376 phút).
**Còn chặn PASS tầng:** LIVE↔store **cùng phút** = MISSING (không overlap 2026-09 ↔ ≤2025-12-31) — đúng luật pre-reg (thiếu nguồn đối ứng ⇒ MISSING). LIVE-side trực tiếp chỉ 2/4 vì **feat_dump thiếu cột `rateUpAvg`/`rateUp15MAvg`**.

---

## 3. VIỆC 3 — SELECTOR + GATE-p15

### 3.1 gate-p15 DEV (nguồn KHÔNG-ONNX = `pred.bin`)
- **Đã dump CSV**: `research/parity/data/p15_dev.csv` (n=**2.500.260**, `ts,predReturn15M,predRisk4H`) — gitignored.
- **Đo phía DEV**: p15 min=0,0020 · q0,5=0,00545 · q0,99=0,0131 · q0,999=0,0282 · max=0,1226; ts 1617210000000..1767225540000.
- **Cùng-phút LIVE vs DEV**: giao **0 phút** (pred.bin hết 2025-12-31; LIVE 2026-09-28) ⇒ **MISSING + lý do** (2026=holdout). LIVE-side: `p15_max=0,01501 < thr_min=0,03388` ⇒ `n_pass=0` tái lập đúng log 242.

### 3.2 selector (đã ĐO được — sửa nhận định V2)
- **V2 nói "artifact chết từ 2026-08-20" là SAI/đã cũ.** Thực tế `~/shadow_c3/app/storage/data/predictionSymbol/` phủ liên tục tới **20261001**, gồm đúng ngày cửa sổ parity **20260928**.
- **Đọc RAW không-ONNX**: Java-serialized `HashMap<String,Float>` bọc Snappy (`StorageSnappy`) → decode bằng `javaobj` + `cramjam` (`read_selector_tick`). Kết quả LIVE `20260928`: **249 tick · 163.520 dòng · 533..719 symbol/tick** → dump `research/parity/data/selector_live.csv` (`ts,symbol,selectorScore,rank`).
- **Đối ứng cung-tick DEV**: `funding.bin` (n=2.301.065, ts 1625072400000..1767200400000) — **KHÔNG phủ 2026-09** ⇒ **MISSING cung-tick + lý do**. Đề xuất: thêm cột `selectorScore`+`rank` vào `feat_dump` (cả live lẫn export) ⇒ có cửa sổ chung để đo rank-overlap/top-K không cần ONNX.

---

## 4. VIỆC 4 — 26 FEATURE LỆCH THẬT: PHÂN NHÓM

Cơ sở: export DEV là **port 1-1** của `ComprehensiveMarketFeatureExtractor` (đã đọc 2 file) ⇒ **công thức giống**; khác nhau còn lại là **NGUỒN** (LIVE = ticker live + history-ring nuôi bằng tick live) vs (BACKTEST = kline lưu). Phân nhóm (27 FAIL = 26 + `momentumAcceleration`):

| nhóm | số | feature |
|---|---|---|
| **(i) nhiễu ticker-vs-kline / tập hợp** | **20** | 15 "thường" (rsi14 40,3 · basketRsi14 30,0 · trendConsistency 2 · percentAboveMA20 0,65 · marketBreadthStrength 0,26 · basketMomentum1H/15M · distMA20 · momentum5M · trendStrengthETH · momentum1H/4H/24H · fundingRateRaw/Trend · volatility24H) + 5 **"tỉ số nhạy"** (volumeRatioUpDown 236 · volumeSpike 123 · basketVolSpike 80 · advanceDeclineRatio 6,6 · btcDominance 0,65 — mẫu số up/down nhỏ ⇒ khuếch đại) |
| **(ii) export thiếu nguồn (=0)** | **0** (trong 26) | nhóm market: `momentum1M`/`momentum15M` **đã hồi phục inline** (PASS); `momentumAcceleration` = 1 dòng dư lượng (dư 2,2e-3 đến từ `momentum5M`, không phải market) |
| **(iii) corr<0,7 "nghi logic/tập hợp"** | **6** | `volatilityTermStructure` 1,30 · `volatility1M`/`15M`/`1H` · `basketMomentum15M` · `fundingRateAvg24H` (corr 0,039) |

**Kết luận:** **20/26 = (i)** (nhiễu nguồn, kể cả nhóm tỉ số khuếch đại); **(ii) = 0/26** (các field "chết=0" đã xử lý bằng inline); **6/26 = (iii) "chưa rõ"** — *không* có bằng chứng lỗi công thức (export là port 1-1); khả năng cao vẫn là **khác nguồn/tập hợp + warmup rolling** (vol dùng history-ring live vs kline; fundingAvg dùng feed khác). Muốn chốt (iii) cần **control cùng-nguồn** (nạp CÙNG kline lưu vào cả 2 nhánh) — nằm ngoài phạm vi Python (cần chạy Java ⇒ Kaggle).

---

## 5. TRẢ LỜI CÂU HỎI

1. **writer đã hết cắt cụt chưa?** → **CHƯA sửa** (đường LIVE ⇒ chỉ đề xuất). Bằng chứng: **6/6 file thiếu trailer, tail `0000ffff`**; selftest tái lập buggy(no-close)=FAIL / fixed(close)=OK. Patch shutdown hook **đề xuất sẵn** (§1).
2. **marketparams 4/4 + lệch?** → **4/4 đo được**: rateDownAvg 7,5e-4/corr 0,995 · rateUpAvg 6,2e-4/0,997 · rateDown15MAvg 7,4e-4–2,0e-3/0,998–0,9996 · rateUp15MAvg **0 hai phía** ⇒ nhiễu, không lỗi logic; ngưỡng MATCH-default.
3. **selector/gate-p15 đo được chưa?** → **gate-p15**: dump p15 DEV (2,5M) + đo phía DEV, **cùng-phút MISSING** (không overlap). **selector**: **đo được phía LIVE** (249 tick/163.520 dòng → CSV), **cùng-tick MISSING** (funding.bin không phủ 2026-09). Đã loại ONNX đúng ràng buộc.
4. **26 feature lệch: phân nhóm?** → **(i) 20 · (ii) 0 · (iii) 6** (nhóm market đã hồi phục inline; xem §4).
5. **V2→V3 + đề xuất còn lại** → xem §0, §6.

---

## 6. ĐỀ XUẤT TỐI THIỂU CÒN LẠI ĐỂ KHỚP 100 %

- **(D) writer** [LIVE, cần owner]: thêm shutdown hook (+ xoay file) ⇒ hết cắt cụt (VIỆC 1).
- **(B) marketparams**: thêm cột `rateUpAvg`/`rateUp15MAvg` vào `feat_dump` ⇒ LIVE-side 4/4 trực tiếp (hiện đo được 4/4 nhưng 2 field qua nhánh DEV).
- **(C) selector/gate-p15 cùng-tick**: thêm `selectorScore`+`rank`+`p15` vào `feat_dump` **và** regenerated export ĐỔI cửa sổ parity sang DEV (≤2025-12-31) để có **cùng tick** — khi đó harness so được không cần ONNX.
- **(E) 26 feature**: chốt (iii) bằng **control cùng-nguồn** trên Kaggle (nạp cùng kline lưu vào cả nhánh live-port và export-port), hoặc thống nhất ngưỡng cho nhóm tỉ số liên-thị-trường (hiện 1e-8 quá chặt cho feature phụ thuộc universe).

## 7. MỤC BỎ / LÝ DO (khai rõ)

- **Bỏ** patch Java LIVE (`LiveFeatureDump`) — ràng buộc "đụng LIVE cần owner duyệt" ⇒ chỉ đề xuất.
- **Bỏ** chạy Java/sim/WFO trên Oracle; **bỏ** ONNX ⇒ gate/selector **cùng-tick = MISSING** (đúng luật pre-reg).
- **Bỏ** bịa PASS cho tầng thiếu đối ứng; giữ MISSING + lý do + đề xuất.
- **KHÔNG** sửa/ghi gì trên 242 (READ-ONLY); **KHÔNG** push file dữ liệu (mọi CSV đều gitignored); **KHÔNG** dùng 2026 để chọn/tune.
