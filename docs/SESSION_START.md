# SESSION_START — Điểm bắt đầu session mới (chốt 2026-07-07 chiều)

## 0.-1 MỚI NHẤT (2026-07-30 tối) — ĐỌC FILE NÀY TRƯỚC, TRƯỚC CẢ §0.0
> **Rẽ nhánh sang exit-formula theo yêu cầu Uni (min-rate SL 0.01032→0.03 + ratchet).** Đọc
> `reports/HANDOFF_20260730_exit_min_ratchet.md` — 3 việc đã làm (commit `3e66898`/`ccc05dc`/
> `b203a78`), và **1 việc đang bị chặn**: N=13 confirm chưa bắn được vì job store Aerospike fanout
> (103.157.218.226:3222) đang có 9/16 window FAILED, chưa rõ nguồn gốc — đã hỏi Uni cách xử lý,
> **CHƯA có câu trả lời khi phiên trước kết thúc**. ĐỌC câu trả lời đó trước (nếu có) rồi mới bắn
> job. Đừng tự ý fanout 6-node khi chưa rõ trạng thái backend.
> Việc lớn từ §0.0 (fix fitness mismatch, bỏ HPO argmax) **vẫn treo, chưa quay lại** — phiên tối
> 07-30 rẽ hẳn sang exit, không đụng harness nữa.

## 0.0 (2026-07-30 sáng) — ĐỌC TRƯỚC §0.1
> **Bước 1 của verdict M ĐÃ XONG (read-only audit).** Hai doc mới, đọc trước khi làm gì:
> `reports/AUDIT_20260730_wfo_constraint_harness.md` — 6 lỗ hổng harness (L1–L6) + 7 đề xuất (P0–P6).
> `reports/EXIT_MACHINE_20260730_stop_schedule.md` — algebra exit + kế hoạch E0–E4.
>
> **3 phát hiện chốt:**
> 1. **L1 ordering inversion (BUG):** ramp `TOO_FEW_TRADES` ∈ (−100000, 0) **cao hơn** mọi reject khác
>    (CAPITAL_LOCK ≈ −100002) → genome 1 lệnh thắng genome đang lãi. HPO ưu tiên không-trade.
> 2. **L2:** khi CAPITAL_LOCK bind hết sample, argmax = min pctHeldOver7d → Calmar bị loại khỏi bài
>    toán → **harness CHỦ ĐỘNG chọn genome đánh lướt** (6/17 gene là exit param). "Pump nhưng lướt"
>    không chỉ do label 6% — bị fitness cưỡng chế. ⇒ KHÔNG tune exit trước khi sửa harness.
> 3. **Exit machine vỡ 2 chỗ:** dead zone 1.03%→5.39% (SL đóng băng ở +0.5%, ratchet lệch arm 5.2×,
>    có **bước nhảy siết chặt 41% NGAY tại 5.39%**); và `gap = min(p×g, TS_MAX_GAP)` **đảo dấu** →
>    tỉ lệ nhả teo dần `maxGap/p` (27% ở p=30%, 8% ở p=100%) → cắt mất đuôi x2/x3.
>    Cần `max(p×g, minGap)` thay vì `min(..., maxGap)`.
>
> **Định lượng:** 8/13 window non-w15 bị CAPITAL_LOCK loại, Σ net **+9 176.68 DƯƠNG TOÀN BỘ**.
> Pre-register: sửa CAPITAL_LOCK một mình → 9/13 = 69.2% (**thiếu đúng 1 window**); + hạ sàn
> min-trade → 10/13 = **76.9%**. WFE_median và worstDdPct chưa biết ⇒ CHƯA được nói PASS.
>
> **Sample cho nghiên cứu exit — KHÔNG hạ gate.** Đã đo (`freq_probe_table.md`): gate 0.010 cho
> **26 394 gate-pass** w4–w14 vs 996 trade thật = **26.5×** nếu bỏ filter vốn (C1), cùng phân phối
> momentum, bias 0. Gate 0.008 chỉ thêm 1.64× và kèm sample-selection bias. C1 thắng tuyệt đối.
> ⚠️ Phải dedup (gatePass đếm signal-minute) và giao với rank-K8 trước khi tin số 26k → đó là E0.
>
> **Chưa làm gì cả** — mới audit. Uni chốt: P0+P5+P6 trước, hay gộp P1+P3; E0 riêng hay E0+E1.

## 0.1 (2026-07-29) — verdict M
> **VERDICT M (2026-07-29): entry-alpha KHÔNG đóng. Edge selector THẬT + TRẢI RỘNG (không chỉ w15). Bottleneck = WFO/HPO HARNESS, KHÔNG phải gate/selector/regime.**
> ĐỌC ĐẦU TIÊN: `reports/ENTRY_ALPHA_STATE_AND_PLAYBOOK.md` (hành trình lý luận §2 + mental models §5 + đang-ở-đâu §3 + làm-gì §6 — hiểu MẠCH, không chỉ facts). Bản ngắn: `reports/HANDOFF_20260729_entry_alpha_harness.md`.
> Bằng chứng: step-2 frozen leakage-free → 11/13 window OOS non-w15 winRate>50% + net dương sau phí; net/trade non-w15 8.59 ≥ w15 7.97; A(frozen) thắng B(production) 2.34× → breadth KHÔNG leakage. Window fail = TOO_MUCH_CAPITAL_LOCK/TOO_FEW_TRADES → harness loại nhầm window đang lãi.
> **NEXT (KHÔNG build gate/model mới):** (1) audit+nới constraint TOO_MUCH_CAPITAL_LOCK/TOO_FEW_TRADES [đọc code trước]; (2) fix fitness mismatch (Calmar-chọn vs raw-PnL-chấm); (3) bỏ HPO argmax → genome regularized (nếu 1+2 chưa đủ); (4) N=30 confirm sau mỗi bước (số M hiện tại là N=1). Đã GIẾT: oi_z, offset, hard-SL, short, gate<0.010, HPO-argmax(overfit w15). Config tốt nhất: MOM15=0.010 + rank-K8 + trailing + funding-fee ON.
> Code rank-K/offset/frozen + jar `binance-lf-frozen-1.0.0.jar` = **UNCOMMITTED** (cần review+commit). Chuỗi đầy đủ: `reports/gate_freq_ablation_20260727.md §A–§O`.
> ---
> **CẬP NHẬT gate/frequency ablation — entry-alpha KHÔNG đóng nhánh, hồi sinh về near-PASS.** Nguồn: `reports/gate_freq_ablation_20260727.md` (+ `HANDOFF_20260727_entry_alpha.md`).
> **Đã-đo (07-27 tối):** FREQUENCY = trần ràng buộc (XÁC NHẬN). Hạ gate `MIN_MOMENTUM_15M` baseline(0.02284)→0.010: %OOS-SUCCESS 46%→69% (75% ex-w16), net-EV +51%, PnL dàn khỏi w15 (68%→46%), **WFE median 0.68 (≥0.5 PASS), maxDD 26%**. Non-monotonic: nới gate về 0/off = PHÁ HUỶ (BURN, maxDD 59%, −55k) → KHÔNG bỏ gate, chỉ hạ về sweet-spot. **WFE 0.24 cũ = artifact HPO over-tightening** (fixed-genome cho 0.68–0.75), cần N=30 confirm. Kaggle fanout đã self-contained (`java-run-lc` config `TICKER_SOURCE=file`, parity w6 khớp 437/1.21/56). Close-branch condition NEXT#5 KHÔNG kích hoạt.
> **NEXT (chờ Uni quyết, heavy):** (1) oi_z THAY gate — build predict_wf dataset (nên chạy Kaggle, né disk Oracle 89%); (2) rebuild jar hạ sàn genome MOM15 <0.010 + fix-gate/regularize DOF → N=30 HPO đối chứng baseline 0.24; (3) đóng window thoái hoá w14 BURN / w9 CAPITAL_LOCK tại sweet-spot.
> ---
> **Đã VERIFY edge entry-alpha — ĐỪNG hỏi lại "verify edge trước".** Nguồn đầy đủ: `reports/HANDOFF_20260727_entry_alpha.md`.
>
> **Đã-đo:** selectability THẬT (xsecIC 18/18 quý, dedup) nhưng KHÔNG monetize. Hard-SL/TP first-touch = âm hết; short bottom-decile NOT_VIABLE; oi_z-veto CHỒNG = frequency wall. **Trailing (DCA off, funding on) = hướng DƯƠNG duy nhất nhưng WEAK**: WFE median ≈0.24 (<0.5 overfit), PnL dồn 1 window (w15 +7469), 7/13 window ZERO/TOO_FEW.
> → Theo rule "edge không robust nếu WFE med ≤0 hoặc dương nhờ 1–2 window": **edge NỖ/borderline, trần thật = FREQUENCY/gate** (không phải exit).
> **NEXT (KHÔNG lặp lại verify):** (1) gate/frequency — Task156 coverage + MOM15 cùn (7/13 window bị bóp); (2) chống overfit HPO (giảm DOF genome, đừng tin outlier w15); (3) **tách 2 chiến lược** — label 6% bản chất là scalp; "nuôi lãi / SL chặn" cần label+exit KHÁC, đừng nhồi 1 model; (4) wire Kaggle `TICKER_SOURCE=file` (hpo-ticker-daily 1m) — kernel hiện đọc aerospike226, fanout FAILED 9/16.
> **ĐỒNG BỘ:** verify trên ghi ở **repo docs/** (STRATEGY_ENTRY_ALPHA §9, reports/*), KHÔNG tự vào `memory.md` → session chỉ nạp memory (không đọc repo) sẽ lệch → phải đọc handoff này hoặc chạy consolidate-memory.

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

**TO-DO NÓNG (cập nhật mới nhất):**
1. **Kiểm chứng `SELECTOR_INVERT=1`** — nghịch đảo dấu selector cho Long: mua worst-N "ít pump nhất" để tránh bẫy pump-and-dump. In-sample biến 2025Q2 từ lỗ thảm → lãi ròng. → **cần chạy WFO OOS xác nhận** (chưa OOS = chưa kết luận).
2. **Chạy WFO kịch bản Soft-Gating dồn vốn (`CONF_SIZE_MODE=1`)** để khắc phục vốn idle 14/16 quý.
3. **Vận hành qua CE pipeline tự động (`wfo_from_preds.json`)**, KHÔNG gõ lệnh cơm.

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
