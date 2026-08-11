# Index — Bản đồ tri thức (router)

> Mỗi mục = pointer + 1 dòng. KHÔNG nhồi nội dung. Phình → tách file, để lại pointer.
> **Luôn đọc [CORE](CORE.md)** (luật an toàn + toàn vẹn backtest) + (các) pack liên quan việc đang làm.

## Pack theo việc (nạp đúng cái đang chạm)
- [CORE](CORE.md) — hạt nhân an toàn, mọi agent mang theo.
- [rules/code](rules/code.md) — quy ước + luật code Java/HPO (một-bộ-não, taskId, no-random-split, Float, runtime-config).
- [rules/backtest](rules/backtest.md) — toàn vẹn & tái lập backtest/sim/golden + cạm bẫy đọc kết quả.
- [rules/run-226](rules/run-226.md) — chạy job java trên 226: dọn job cũ, kill đúng PID, SSH.
- [rules/build-env](rules/build-env.md) — Maven + mvn wrapper Windows + protobuf.
- [rules/security](rules/security.md) — secret/key live đã lộ → rotate, không echo.
- [KAGGLE_RULES](KAGGLE_RULES.md) — bắt buộc trước mọi Kaggle job: slot=5, 12h-kill, System.exit, ổ-C, network.
- [db/](db/index.md) — data nào ở đâu, ghi/đọc/chạy đâu (242 source · 226 compute · redis).
- [**REDESIGN_INFRA_20260804**](REDESIGN_INFRA_20260804.md) — 🔴 **TOPOLOGY MỚI (chốt 2026-08-04)**: retire 226 · Oracle hub public 3222 · Kaggle file-fleet · 242 SoT. THẮNG `SESSION_START §1`+`db/index` khi mâu thuẫn.
- [**SESSION_START**](SESSION_START.md) — 🔴 **ĐỌC ĐẦU TIÊN mỗi session mới**: mục tiêu, topology, trạng thái 4 tầng dữ liệu, việc kế tiếp, quyết định đã chốt. (2026-07-07)
- [DATA_STATE](DATA_STATE.md) — **TRẠNG THÁI dữ liệu THẬT (đo)**: 4 tầng (ticker file/aerospike, lifecycle, dataset), 2 đường đọc ticker, survivorship 38 coin. Nguồn sự thật "dữ liệu đủ chưa, ở đâu". (rà 2026-07-07)
- [**DATA_VALIDATION_FRAMEWORK**](DATA_VALIDATION_FRAMEWORK.md) — 🔴 **ĐỌC TRƯỚC MỌI HPO/WFO**: Preflight Gate chặn lỗi im lặng (19 loại, 6 nhóm), quy trình fail-fast, + danh mục 10 lỗi đã xảy ra làm đảo verdict (gate coverage 2021-2022, leakage, MAE, ghost USDC...). (2026-07-11)
- [runbooks/BACKFILL_SURVIVORSHIP](runbooks/BACKFILL_SURVIVORSHIP.md) — quy trình 7 bước backfill/re-export coin delist + checkpoint.
- [architecture](architecture.md) — bức tranh lớn codebase + bản đồ package + 2 process live.
- [rules/task-workflow](rules/task-workflow.md) — luật khi nhận & chạy task (claim theo cách chạy, bàn-giao job nền, checkpoint, dọn, RESULT). · [AGENT_WORKFLOW](AGENT_WORKFLOW.md) — cơ chế điều phối đầy đủ. · [AGENTS](AGENTS.md) — bản đồ CCD đang làm gì. ⚠️ có thể lệch — đối chiếu trạng thái thật ở ROADMAP (con trỏ 2-track).
- [**CE V3 — Cognitive Execution Framework**](../orchestrator/cognitive-execution-framework-v3.md) — canonical: máy chạy trọn chuỗi chân tay, LLM chỉ ở `llm_gate` (nút + pipeline; xem `rules/ce-buttons.md`).

## Mô hình & lộ trình (sống)
- [ROADMAP](ROADMAP.md) — lộ trình kiểm chứng 6 bước (**cha**).
- [REBUILD_ROADMAP](REBUILD_ROADMAP.md) — **con của ROADMAP (bước-1 model)**: rebuild data + 2 model (gate 0010 / funding 0011).
- [PIPELINE](PIPELINE.md) — vận hành cadence 3 tháng (2 pha, 9 bước, 2 cổng gác).
- [PIPELINE_PROVENANCE](PIPELINE_PROVENANCE.md) — **vết truy nguyên**: artifact nào từ code/data/model nào + registry + phát hiện leakage funding (in-sample) + quy ước version. (rà 2026-07-01)
- [WFO_DATA_PIPELINE_MASTER](WFO_DATA_PIPELINE_MASTER.md) — **nguồn sự thật SỐNG** toàn trình dữ liệu WFO (ticker→market→OI→label→Tool1→selector→gate→export→validate), có version + env var + runbook + bug đã biết. Cập nhật mỗi khi đổi hành vi dữ liệu.
- [FINDINGS](FINDINGS.md) — **NGUỒN SỰ THẬT**: mọi kết luận đã ĐO kèm số + lý do.

## Chiến lược (campaign 2026-07-10/11 — tìm cấu hình 20%/năm)
- [SOLUTION_FRAMEWORK_20260711](SOLUTION_FRAMEWORK_20260711.md) — **mới nhất**: cây nhánh chiến lược +
  test rẻ + điểm dừng pre-register. Vị trí hiện tại: CHƯA đạt 20%/năm (~5%/năm).
- [STRATEGY_ROADMAP_3PART](STRATEGY_ROADMAP_3PART.md) — phân rã Entry/Success/Fail, mỗi phần 1 bộ WFO
  riêng (bổ sung `REBUILD_ROADMAP.md`, đi SÂU trong 1 kiến trúc — không mâu thuẫn framework trên).
- [STRATEGY_CONSOLIDATED](STRATEGY_CONSOLIDATED.md) — hợp nhất phiên nghiên cứu 2026-07-10 (bằng chứng đo
  được: giveback/ret2/DCA) + spec chiến dịch điều phối task 140–144.

## Insights (kiến thức nền)
- [insights/DATA_CADENCE](insights/DATA_CADENCE.md) · [insights/INGEST_FORMAT](insights/INGEST_FORMAT.md) · [insights/TRAINING_NOTES](insights/TRAINING_NOTES.md)
- [insights/GATE_REDESIGN_IDEAS](insights/GATE_REDESIGN_IDEAS.md) — ⏸ PARKED (gate chốt-nhanh-không-DCA, sau 039).
- **WFO — hub = [WFO_ROADMAP](insights/WFO_ROADMAP.md)** (sub-roadmap Bước 4 + TRẠNG THÁI LIVE + pointer). Chi tiết: [WFO_FRAMEWORK_DESIGN](insights/WFO_FRAMEWORK_DESIGN.md) (kiến trúc + 5 quyết định chốt 2026-06-29) · [WFO_LEAKS_TODO](insights/WFO_LEAKS_TODO.md) (5 leak L0–L5 chưa xử) · [WFO_OBJECTIVE_RESEARCH](insights/WFO_OBJECTIVE_RESEARCH.md) (hàm mục tiêu).

## Quyết định (ADR — chốt, chống sửa-ngược)
- [decisions/](decisions/) — 0001..0012. `0003` (genome 13) **đã thay bởi 0012** (genome 18 + OFF cứng cụm C). `0007` = `backfill` (hiện hành); `material` đã đánh dấu SUPERSEDED. Kết luận-chốt còn rải ở FINDINGS/TRACE nên tách thêm ADR (SLIPPAGE=0.003, filter mode C, dd4h ở RISK, AI-filter-không-chặn-sập, funding pred[0]=P(fail)).

## Nợ kỹ thuật
- [DEFERRED](DEFERRED.md) — hoãn tới khi có CI/CD. · [LIB_BINANCE_OLD](LIB_BINANCE_OLD.md) — dual-connector, migration dở, chưa quyết.

## Deploy
- [DEPLOY_242 đợt 1](archive/deploy/DEPLOY_242-dot1.md) — 📸 ĐÃ deploy → archive. · Đợt 2 (027-031, **CHỜ user duyệt**) đã archive → [archive/DEPLOY_242_dot2.md](archive/DEPLOY_242_dot2.md).

## Reference — 📸 SNAPSHOT @thời-điểm-viết, KHÔNG phải nguồn sự thật (số/Configs có thể cũ)
- [AUDIT_filter_ablation](reference/AUDIT_filter_ablation.md) · [BO_CODE_DIGEST](reference/BO_CODE_DIGEST.md) · [TRACE_backtest_drift](reference/TRACE_backtest_drift.md)
- [PRODUCTION_AUDIT](reference/PRODUCTION_AUDIT.md) · [STATUS_RECON](reference/STATUS_RECON.md) · [_reconcile-report](reference/_reconcile-report.md)
- [aerospike_242_inventory](reference/aerospike_242_inventory.md) · [basis_verify](reference/basis_verify.md) · [RUNBOOK_kaggle_multi_cpu](reference/RUNBOOK_kaggle_multi_cpu.md) (đã hấp thụ vào KAGGLE_RULES §1)
- [GENE_AUDIT_TASK111](reference/GENE_AUDIT_TASK111.md) — bản đồ gene 6 tầng (tham số→tầng→vai-trò). Genome chốt = [ADR-0012](decisions/0012-genome-18-gene-off-cung-cum-C.md).
- [ARCHITECTURE_STATE_SNAPSHOT_20260707](reference/ARCHITECTURE_STATE_SNAPSHOT_20260707.md) — bản tổng
  hợp kiến trúc+trạng thái viết lại, trùng nội dung `architecture.md`+`DATA_STATE.md`+`SESSION_START.md`
  (nguồn sống hơn). Giữ vì có sơ đồ ASCII gọn.

## Khác
- [../tasks/](../tasks/) — task theo thứ tự LOGIC. · [reports/](reports/) — log worker. · [golden/](golden/) — baseline JSON. · [archive/](archive/) — stale, truy vết.
