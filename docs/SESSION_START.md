# SESSION_START — Điểm bắt đầu session mới (chốt 2026-07-07 chiều)

> **ĐỌC FILE NÀY ĐẦU TIÊN khi mở session mới.** Nó tóm tắt CHÍNH XÁC những gì đã chốt + trạng thái thật +
> việc kế tiếp, để không miss/lệch. Chi tiết dữ liệu → [DATA_STATE.md](DATA_STATE.md). Topology → [db/index.md](db/index.md).
> Quy trình backfill → [runbooks/BACKFILL_SURVIVORSHIP.md](runbooks/BACKFILL_SURVIVORSHIP.md).

## 0.5 TRẠNG THÁI CHIẾN DỊCH (cập nhật 2026-07-11 tối — đọc trước)
**Đang ở:** tìm cấu hình ≥20%/năm. Entry maxFav3%@4h là hướng sáng nhất (thắng ret2 ở sim full: quý-trade
9→11, PST dương). Chi tiết: reports/155.md, STRATEGY_ROADMAP_3PART.md, SOLUTION_FRAMEWORK_20260711.md.

**PHÁT HIỆN GỐC RỄ (2026-07-11):** WFO luôn FAIL (~29% OOS-dương) cả ret2 lẫn maxFav3 KHÔNG phải do chiến
lược — mà do **gate model pred chỉ phủ 2023-2025** (2021=0, 2022=420 rec). Entry đòi `predict!=null` →
2021-2022 chặn cứng → 8/17 cửa sổ ZERO_TRADES → FAIL giả. Feature 2021-2022 CÓ (chỉ thiếu vì cutoff train
bắt đầu 2023). → task 156 sinh gate 2021-2022 → WFO lại (đang TODO). maxFav3 CHƯA bị bác.

**ĐANG CHẠY (nền, độc lập session):** supervisor detached (orchestrator/supervisor.py, model=sonnet) →
task 156 (gate coverage). Task khác: 146(REVIEW dọn doc), 150/151/152(team Entry/Success/Fail),
153(precision), 154(path-truth fail-recovery), 155(baseline model). Xem orchestrator/STATUS.md.

**QUYẾT ĐỊNH UNI CHỐT:** (1) short = ưu tiên SAU, BẮT BUỘC có SL (crypto x100). (2) cần Data Preflight
Gate chặn lỗi im lặng trước HPO/WFO — spec ở DATA_VALIDATION_FRAMEWORK.md, chờ Uni chốt ngưỡng BLOCK/WARN
+ N sample trước khi implement.

**CƠ CHẾ hiện tại (đọc code xác nhận):** nuôi lãi = trailing động (arm ~5.4% hoặc ~1%, gap=min(đỉnh×
giveback,8%), giveback=1.0 tối ưu). DCA = BIG_DOWN + độ sâu lỗ (phanh theo margin ratio −15..−99%). Cơ chế
+3%→SL cứng+1% của Uni là THIẾT KẾ MỚI cho tầng 2, chưa implement (nuôi lãi hiện vẫn cơ chế cũ).

## 0. MỤC TIÊU ĐANG THEO (Uni chốt)
Xây bộ dữ liệu CHUẨN đi theo pipeline CHUẨN cho hệ WFO tốt nhất — **ưu tiên chất lượng, không vội**.
Chuỗi: **ticker gốc → market object trên Aerospike Oracle → export .bin cho master-worker mọi tài nguyên.**
Nguyên tắc: tìm artifact có sẵn trước, validate đủ+đúng thì DÙNG LẠI, không thì export lại. Đương nhiên validate lại với market object mới.

## 1. TOPOLOGY (KHÔNG đổi)
- **Oracle VPS** `ubuntu@161.118.212.3` (key `/c/Users/pc/.ssh/id_rsa_chuyennd`, 23GB/4-core) = COMPUTE chính + Aerospike LOCAL (127.0.0.1:3222 **ns=test**) = kho DATA-TEST. Mọi việc dữ liệu làm ở ĐÂY.
- **242** `root@103.157.218.242 -p 2222` = SOURCE market production. **OFF-LIMITS — KHÔNG động vào** (Uni chốt). ⚠️ Oracle TỚI ĐƯỢC 242:3222 → tool ghi PHẢI trỏ 127.0.0.1 tường minh, KHÔNG dùng getClient242.
- **226** = jobstore/benchmark. Uni chốt KHÔNG dùng tiếp cho backfill (đã chuyển hết sang Oracle).
- **Kaggle** CLI `chuyendinh`, 5 kernel CPU. Build local: `JAVA_HOME=/c/Users/pc/.jdks/corretto-17.0.9 /c/Users/pc/bin/mvn -q -DskipTests package`. Repo `E:\educa\source\github\20260415\BinanceFuturesJava` branch `module`. Jar deploy Oracle: `binance-futures-backfill.jar`.

## 2. TRẠNG THÁI DỮ LIỆU — 4 TẦNG (đo 2026-07-07, KHÔNG đoán)
| Tầng | Trạng thái | Chi tiết |
|---|---|---|
| Ticker FILE | ✅ | 1886 file `.bin.gz` (2021-01-01→2026-03-01), có 38 coin delist + đuôi sập |
| **Ticker Aerospike** ns=test set kline_1m_opt | ✅ | 2,703,650 record, nạp từ file (IngestTickerFileToAerospike). LUNA đuôi $0.008 đúng |
| **symbol_lifecycle** ns=test | ✅ | 698 sym (636 LIVE/62 DEAD). LUNA/ANC DEAD đúng. Suy từ data (không exchangeInfo) |
| **symbol_mapper** ns=test | ✅ | 781 sym gồm coin delist (LUNA→760, FTT→782). Sống sót reset. ⚠️ có 38 ghost USDCUSDT vô hại |
| **market_data_object** ns=test | ✅ | Gen xong (ExportMarketData2File). Verify LUNA sập: rateDown15MAvg=-0.029 ngày 12/5 đúng |
| **OI feature** | ✅ DÙNG LẠI | `features_oi_percoin_v1/oi_percoin_20210101_to_20260624.bin.gz` 3.1GB, validate coin delist đủ |
| Gate feature ff_*.bin | ❌ | Chỉ ff_202401 (1 tháng) → EXPORT LẠI |
| Funding/selector pred | ⏳ | Chưa kiểm. Model selector v2 (train 06-25) có sẵn |
| wfo_dataset .bin | ❌ | Chờ export lại từ market mới |

## 3. VIỆC KẾ TIẾP (đúng thứ tự — bắt đầu session mới từ đây)
1. **Gate feature**: export lại TOÀN BỘ từ market_data_object mới (ExportGateFeaturesGroupA/B). Validate: có coin delist, 0 NaN/leak.
2. **Funding feature + selector pred**: kiểm bản có sẵn validate đủ/đúng với ticker mới → dùng; không thì gen lại (+ generate selector pred nếu feature đổi).
3. **Export wfo_dataset .bin**: market_data_object + gate pred + funding/selector pred + OI → ExportWfoDataset, ghi manifest provenance (code SHA + nguồn + ngày).
4. **Validate lại** toàn bộ với market object mới.
5. **WFO baseline mới** — ngưỡng pre-reg: WFE≥0.5, %OOS+≥70%, maxDD≤50% (cả 3 required PASS). Kết quả WFO CŨ chỉ THAM KHẢO (baseline cũ trên data bẩn = vô nghĩa).

## 4. NGUYÊN TẮC/CẠM BẪY PHẢI NHỚ
- **Tool batch/nền: cuối main() PHẢI `System.exit(0)`** (executor non-daemon trong DataManager làm JVM treo → zombie giữ RAM). Đã fix ExportMarketData2File. Rule gốc: CORE.md dòng 14.
- **Foreground cap 4 phút** → detach `setsid nohup ... </dev/null >log 2>&1 &` + poll. Lệnh chờ dài làm timeout MCP.
- **Tool ghi Aerospike PHẢI tự tạo `AerospikeClient("127.0.0.1",3222)`** — KHÔNG dùng getClient242 (hardcode 242 trong DataManager). Tool đã có: BackfillDelistCoin, IngestTickerFileToAerospike, SymbolLifecycleBuilderLocal.
- **Vision-per-coin CHẬM** (6-10 phút/coin, tải toàn lịch sử S3) — chỉ dùng cho vài coin lẻ, KHÔNG cho full universe. OI full universe: dùng bản 226 đã có.
- **Kill zombie trước khi chạy job nặng**: `pgrep -f <Class>` + kill đúng PID (KHÔNG pkill java bừa — có process live 242).
- **market_data_object đọc/ghi qua getClient226()** = 127.0.0.1 local Oracle (an toàn, không đụng 242).
- **diedSymbol=BTCDOM,USDC** (chỉ index+stable) — KHÔNG loại coin delist khỏi market. Market gen đủ survivorship.
- SLF4J/Log4j, không System.out. Git trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## 5. QUYẾT ĐỊNH ĐÃ CHỐT (không xét lại trừ khi Uni đổi)
- Backfill vào **Oracle Aerospike local**, KHÔNG 226/242 (né rủi ro ADR-0007).
- OI feature: **dùng lại bản 226** (validate đủ coin delist), không export vision (quá chậm).
- Kết quả WFO cũ = **tham khảo**, không phải baseline (data cũ không sạch).
- Ghost 38 USDCUSDT: vô hại (không data), xử khi tiện, ưu tiên thấp.
- P1 backfill survivorship vốn ĐÃ ĐÓNG (TASK-005) — việc 2026-07-07 là KHÔI PHỤC ticker Aerospike bị reset + đi tiếp P2/H1.

## 6. TOOL/COMMIT SESSION 2026-07-07 (branch module)
Tool mới: `BackfillDelistCoin`, `IngestTickerFileToAerospike`, `SymbolLifecycleBuilderLocal`, `Gate0BackfillFeasibility` (đều trong `ai_ml/validation/data/`).
Commit gần nhất: 8c74e0c (OI) · 631d06a (fix zombie) · e7c9694 (gen market) · c7b8cc6 (nạp ticker+lifecycle) · 856b2bf (runbook+gate0).
Tài liệu: DATA_STATE.md (trạng thái dữ liệu), db/index.md (+ Oracle), runbooks/BACKFILL_SURVIVORSHIP.md.
