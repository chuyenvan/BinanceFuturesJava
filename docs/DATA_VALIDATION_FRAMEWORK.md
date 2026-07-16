# DATA VALIDATION FRAMEWORK — Preflight Gate trước HPO/WFO

> **Mục đích:** Chặn LỖI IM LẶNG (dữ liệu sai/thiếu mà không ai báo) TRƯỚC khi tốn hàng giờ HPO/WFO trên
> data hỏng. Mọi kết luận sai lớn nhất của dự án đều đến từ lỗi im lặng (xem §5). Tài liệu này là canonical
> — session mới ĐỌC ĐẦU TIÊN khi đụng tới data/train/validate.
>
> Trạng thái: SPEC đã duyệt sơ bộ với Uni 2026-07-11. Cơ chế + ngưỡng "block vs warn" còn chờ Uni chốt tiếp.

---

## 1. NGUYÊN LÝ

1. **Đo không đoán:** không tin "data đã sạch" từ trí nhớ — re-scan trước mỗi lần dùng.
2. **Fail-fast:** phát hiện lỗi nghiêm trọng → DỪNG, không cho HPO/WFO chạy trên data hỏng.
3. **Full-scan cho check rẻ, random-sample-đủ-phủ cho check đắt** (phân tầng theo tháng × tier coin,
   không sample mù → tránh "may không trúng chỗ lỗi").
4. **Pre-register expected ranges:** mỗi nguồn khai báo trước (range thời gian, records/tháng, min/max
   mỗi feature); validate so khai báo, lệch = fail.
5. **Provenance bắt buộc:** mỗi model/dataset đi kèm manifest (commit + data hash + cutoffs). Không có
   provenance = không dùng.

---

## 2. DANH MỤC KIỂM (19 loại lỗi, 6 nhóm)

### A. COVERAGE (thiếu/lệch dữ liệu)
| # | Lỗi | Cơ chế phát hiện | Mức |
|---|---|---|---|
| A1 | Pred thiếu cả giai đoạn (gate trống 2021-2022) | Đếm records/tháng mỗi nguồn; cảnh báo tháng < X% median | **BLOCK** |
| A2 | Lệch range giữa các nguồn (market tới 2026-05, pred tới 2025-10) | Giao thời gian market∩gate∩selector∩funding phủ mọi cửa sổ | **BLOCK** |
| A3 | Coin trong pred không có ticker (ghost USDCUSDT) | Mọi symId trong pred phải có ticker | **BLOCK** |
| A4 | Fold WFO thiếu (16 vs 17) | Số fold = số cửa sổ mong đợi | **BLOCK** |

### B. LEAKAGE (rò rỉ tương lai) — đảo ngược verdict
| # | Lỗi | Cơ chế | Mức |
|---|---|---|---|
| B1 | Label tính từ giá vùng OOS | Mỗi predict_wf: max(ts_train) < min(ts_oos) − embargo | **BLOCK** |
| B2 | Feature dùng dữ liệu tương lai | Shuffle-test (xáo nhãn → edge phải biến mất); so precision train vs OOS | WARN |
| B3 | Purge buffer < max holding | Embargo ≥ max holding thực đo | **BLOCK** |

### C. GIÁ TRỊ (data bẩn)
| # | Lỗi | Cơ chế | Mức |
|---|---|---|---|
| C1 | NaN/Inf trong feature/pred | Đếm NaN/Inf mỗi cột = 0 | **BLOCK** |
| C2 | Giá phi lý (0, âm, nhảy x1000 — bug USDC-margin) | giá>0; \|Δ1phút\|<50%; OHLC hợp lệ (high≥low≥0, high≥close≥low) | **BLOCK** |
| C3 | Trùng lặp (ts, symbol) | Không cặp (ts,symId) lặp mỗi nguồn | **BLOCK** |
| C4 | Scale sai (0.03 vs 3%) | min/max/median mỗi feature trong khoảng pre-register | WARN |

### D. THỜI GIAN
| # | Lỗi | Cơ chế | Mức |
|---|---|---|---|
| D1 | Timezone lệch (GMT+7 vs UTC) | Settlement funding đúng 00/08/16h UTC | WARN |
| D2 | Gap thời gian (ngày <1440 phút SKIP lặng) | Đếm phút/ngày = 1440, log ngày thiếu | WARN |
| D3 | Off-by-one nến (dùng close chưa chốt) | Verify BLOCK_INTRABAR_LOOKAHEAD bật | **BLOCK** |

### E. PROVENANCE (nguồn gốc — gốc của "config đặc biệt")
| # | Lỗi | Cơ chế | Mức |
|---|---|---|---|
| E1 | Model không khớp code/data (ONNX 262MB mất source) | Manifest ghi commit + data hash + cutoffs | **BLOCK** |
| E2 | md5 mismatch (copy pred.bin quên sửa manifest) | md5 mọi file khớp manifest trước load | **BLOCK** |
| E3 | Cutoff config im lặng (gate train cutoff 2023 không khai báo) | Manifest ghi train range; validate khớp mong đợi | **BLOCK** |

### F. CẤU HÌNH
| # | Lỗi | Cơ chế | Mức |
|---|---|---|---|
| F1 | Env thiếu → fallback im lặng (WFO_SMART_CACHE, pred dir rỗng) | Fail-fast nếu env bắt buộc thiếu, KHÔNG fallback lặng | **BLOCK** |
| F2 | Config version drift | Enforce CONFIG_VERSION khớp | WARN |

*(Mức BLOCK/WARN là ĐỀ XUẤT — chờ Uni chốt cuối.)*

---

## 3. QUY TRÌNH (Data Preflight Gate)

```
[TRƯỚC MỌI HPO/WFO]
   │
   ├─ 1. Load manifest mỗi nguồn (market, gate pred, selector pred, funding, ticker)
   │      → thiếu manifest = BLOCK ngay (E1)
   │
   ├─ 2. FULL-SCAN (rẻ): A1-A4, C1-C3, E2-E3, F1
   │      → bất kỳ BLOCK nào fail = DỪNG, in report, KHÔNG chạy HPO/WFO
   │
   ├─ 3. RANDOM-SAMPLE phân tầng (đắt): B1-B3, C4, D1-D3
   │      → mỗi (tháng × tier coin) ≥ N mẫu (đề xuất N≥100)
   │      → BLOCK fail = DỪNG; WARN = ghi report, cho chạy
   │
   ├─ 4. Ghi report PASS/FAIL rõ ràng (bảng từng check + số liệu)
   │
   └─ 5. CHỈ nếu PASS toàn bộ BLOCK → cho phép HPO/WFO khởi động
```

**Điểm gắn:** gọi Preflight trong `WfoCoordinator.reset()` (trước khi buildJobs) và đầu mỗi HPO run.
Fail → throw, log SLF4J, exit. KHÔNG cho chạy tiếp.

---

## 4. CÂU HỎI CHỜ UNI CHỐT (trước khi implement)
1. Ngưỡng BLOCK vs WARN từng loại — bảng §2 là đề xuất, Uni duyệt/sửa.
2. Sample size check đắt: N ≥ 100/(tháng×tier)? Hay khác?
3. Loại lỗi Uni từng gặp mà CHƯA có trong 19 loại?
4. Ưu tiên implement trước: nhóm A (coverage) + E (provenance) là gốc 2 bug lớn nhất → làm trước?

---

## 4b. CHỐT (Uni ủy quyền Claude quyết, 2026-07-11) — đảo ngược được

**Q1 — Ngưỡng BLOCK vs WARN:** giữ bảng §2, CHỈ sửa **F2 WARN→BLOCK** (config drift → cache HPO trả điểm cũ = run vô nghĩa, CORE đã cấm). BLOCK = {A1-A5, B1, B3, B4, C1-C3, D3, E1-E3, F1-F2}. WARN = {B2 shuffle-test (chẩn đoán, cần người nhìn), C4 scale, D1 timezone, D2 gap}. **Escalate có điều kiện:** D2 gap → BLOCK nếu ảnh hưởng BTC/ETH majors HOẶC làm 1 cửa sổ WFO tụt dưới ngưỡng coverage A1.

**Q2 — Sample check đắt:** N = **100 / (tháng × tier)**, tier = {majors BTC/ETH, top, mid, tail} (4 tier). Cell < N record → lấy TẤT CẢ (không fail vì thưa, chỉ cờ coverage). Riêng B1/B4 (leak biên fold): thêm 100 mẫu trong ±embargo quanh MỖI biên fold (leak sống ở đó).

**Q3 — Loại lỗi bổ sung (đọc từ §5 + task 001/005/132):** thêm **A5 Survivorship** (coin delist/dead phải CÓ trong universe lịch sử trước ngày chết — nếu chỉ thấy survivor → backtest tâng bốc; BLOCK) và **B4 Cross-sectional/population leak** (basket warmup, z-score toàn kỳ, OI merge tương lai — nguồn lệch ngầm CORE nêu; BLOCK). ⇒ **21 loại**. Lỗi ĐO-LƯỜNG (maeLow không reset §5.3, maxDD/trueUnrealizedMin §5.4) KHÔNG phải data-check → thuộc **unit-test framework (WS2)**, không nằm trong preflight.

**Q4 — Ưu tiên:** implement **cả 21 loại song song** (chia task nhỏ 201-205). Thứ tự **REVIEW** khi task xong: A+E trước (2 gốc bug lớn) → C → B → D/F.

### Nguồn gốc + nơi chạy (Uni chốt 2026-07-11)
- **Oracle = gốc dataset.** WFO/HPO/train đều tiêu thụ dataset ĐI TỪ Oracle. Validate chạy **TẠI** Oracle (bin) — không kéo về dev.
- **Kaggle** chạy WFO/master-worker trên **bản sao** dataset sync từ Oracle → phải **re-validate trên Kaggle theo baseline (fingerprint) đó** trước khi tin.
- Tầng SOURCE (Aerospike raw: kline/funding/OI/lifecycle ở 242/226) validate riêng nơi Aerospike đó; là upstream của export bin.
- Máy dev **không** validate data (thiếu dữ liệu) — chỉ build jar + `mvn test` framework.

### Cơ chế chạy (Uni chốt: "nhanh gắn vào, lâu chạy ngoài") — 2 TẦNG + STAMP
- **Tầng FAST** (check rẻ, `expensive=false`): GẮN INLINE đầu `WfoCoordinator.init()/reset()` + đầu HPO. Luôn chạy, chặn tại chỗ.
- **Tầng SLOW** (check đắt, `expensive=true`): chạy NGOÀI theo TRIGGER, KHÔNG mỗi lần WFO. PASS → ghi `ValidationStamp` (fingerprint md5 dataset + env + gateVersion).
- **WFO khởi động** (`assertReadyForWfo`): chạy FAST + đòi stamp SLOW hợp lệ cho (fingerprint, env) hiện tại. Không có/không khớp → THROW, bắt chạy full ngoài.
- **TRIGGER chạy SLOW (bắt buộc re-validate):** (1) run WFO đầu tiên trên dataset; (2) data mới / dataset regen (md5 đổi); (3) đổi môi trường (Oracle→Kaggle master-worker: dataset copy sang env mới phải validate lại); (4) gen model/pred mới; (5) bump `PreflightGate.GATE_VERSION`.
- Code: `Tier`, `ValidationStamp`, `PreflightGate.assertReadyForWfo/runFullAndStamp` (đã dựng skeleton 2026-07-11).

---

## 5. LỖI ĐÃ XẢY RA (bài học — session mới đọc để hiểu vì sao cần framework này)

Mọi lỗi dưới đây là LỖI IM LẶNG đã ĐẢO NGƯỢC hoặc SUÝT đảo ngược kết luận:

1. **Gate coverage thiếu 2021-2022 (2026-07-11):** gate model pred chỉ phủ 2023-01→2026-05. Entry đòi
   `predict != null` → 2021-2022 chặn cứng mọi lệnh → 8/17 cửa sổ WFO ZERO_TRADES → verdict FAIL GIẢ.
   Suýt kết luận sai "trần kiến trúc long-only". Uni chỉ hướng "2021 bull mạnh nhất mà 0 lệnh = phải có
   lỗi" → tìm ra. → loại A1/E3. **Task 156 đang sửa.**

2. **Leakage nhãn OOS (nhiều lần):** label tính từ giá trong vùng OOS gần biên fold → precision ảo cao
   → "×2.4 lần" hóa ra là số leaky. → loại B1/B3.

3. **MAE metric sai (`maeLow` không reset):** đo sai → đảo ngược verdict circuit-breaker. → loại C (đo lường).

4. **maxDD sai (không track trueUnrealizedMin/tick):** đảo verdict MARGIN mode. → loại C.

5. **Ghost USDCUSDT (38 symbol):** coin margin-USDC tạo ticker ảo, symId không có ticker thật → vào lệnh
   "mù". Bug nguồn `DataManagerAerospikeFloatSim:940` (endsWith USDT). → loại A3/C2.

6. **Backtest-lite compound bug:** CAGR_lite nổ mũ (11 triệu %) → số tuyệt đối vô nghĩa, chỉ dùng được
   thứ hạng tương đối. Candidate 0.01|72h|pump thắng lite nhưng Java thật PST −1421. → bài học: lite rank
   ≠ PnL thật, luôn Java-confirm.

7. **pred.bin rỗng 4 byte khi export v6:** gate set không scan được → sim chạy không gate. Phát hiện nhờ
   ls -la size. → copy từ v5 + sửa md5 manifest. → loại E2.

8. **Env thiếu fallback lặng:** WFO_SMART_CACHE thiếu → route sang file cache 18 tháng → zero-trade windows
   câm; WFO_FUNDING_PRED_DIR rỗng → fallback set leaky. → loại F1.

9. **Model provenance mất (ONNX 262MB):** không có source code sinh ra → dead end. → loại E1. Nguyên tắc:
   model ship kèm code+data Java sinh ra nó.

10. **Fold WFO thiếu (16 vs 17):** selector/candidate chỉ có 16 fold, thiếu 2026Q1. → loại A4.

**MẪU CHUNG:** lỗi không crash, không báo — chỉ cho ra SỐ SAI trông hợp lý. Chỉ lộ khi đo trực tiếp
data (đếm records, scan range, check md5). Đây là lý do Preflight Gate phải chạy TRƯỚC, tự động, fail-fast.
