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
- [db/](db/index.md) — data nào ở đâu, ghi/đọc/chạy đâu (242 source · 226 compute · redis). (`DATA_ARCHITECTURE.md` = pointer cũ.)
- [architecture](architecture.md) — bức tranh lớn codebase + bản đồ package + 2 process live.
- [rules/task-workflow](rules/task-workflow.md) — luật khi nhận & chạy task (claim theo cách chạy, bàn-giao job nền, checkpoint, dọn, RESULT). · [AGENT_WORKFLOW](AGENT_WORKFLOW.md) — cơ chế điều phối đầy đủ. · [AGENTS](AGENTS.md) — bản đồ CCD đang làm gì. ⚠️ có thể lệch — đối chiếu WORK_MINDMAP.

## Mô hình & lộ trình (sống)
- [ROADMAP](ROADMAP.md) — lộ trình kiểm chứng 6 bước (**cha**).
- [REBUILD_ROADMAP](REBUILD_ROADMAP.md) — **con của ROADMAP (bước-1 model)**: rebuild data + 2 model (gate 0010 / funding 0011).
- [PIPELINE](PIPELINE.md) — vận hành cadence 3 tháng (2 pha, 9 bước, 2 cổng gác).
- [FINDINGS](FINDINGS.md) — **NGUỒN SỰ THẬT**: mọi kết luận đã ĐO kèm số + lý do.
- [H1_GATE_SPEC](H1_GATE_SPEC.md) — spec export gate (label+feature) đang thực thi (012/015/017/018/025/026).

## Insights (kiến thức nền)
- [insights/DATA_CADENCE](insights/DATA_CADENCE.md) · [insights/INGEST_FORMAT](insights/INGEST_FORMAT.md) · [insights/TRAINING_NOTES](insights/TRAINING_NOTES.md)
- [insights/GATE_REDESIGN_IDEAS](insights/GATE_REDESIGN_IDEAS.md) — ⏸ PARKED (gate chốt-nhanh-không-DCA, sau 039). · [insights/WORK_MINDMAP](insights/WORK_MINDMAP.md) — 📸 ảnh chụp trạng thái (dễ cũ).

## Quyết định (ADR — chốt, chống sửa-ngược)
- [decisions/](decisions/) — 0001..0011. `0007` = `backfill` (hiện hành); `material` đã đánh dấu SUPERSEDED. Kết luận-chốt còn rải ở FINDINGS/TRACE nên tách thêm ADR (SLIPPAGE=0.003, filter mode C, dd4h ở RISK, AI-filter-không-chặn-sập, funding pred[0]=P(fail)).

## Nợ kỹ thuật
- [DEFERRED](DEFERRED.md) — hoãn tới khi có CI/CD. · [LIB_BINANCE_OLD](LIB_BINANCE_OLD.md) — dual-connector, migration dở, chưa quyết.

## Deploy
- [DEPLOY_242_dot2](DEPLOY_242_dot2.md) — runbook đợt 2 (027-031), **CHỜ user duyệt**. · [DEPLOY_242 đợt 1](archive/deploy/DEPLOY_242-dot1.md) — 📸 ĐÃ deploy → archive.

## Reference — 📸 SNAPSHOT @thời-điểm-viết, KHÔNG phải nguồn sự thật (số/Configs có thể cũ)
- [AUDIT_filter_ablation](reference/AUDIT_filter_ablation.md) · [BO_CODE_DIGEST](reference/BO_CODE_DIGEST.md) · [TRACE_backtest_drift](reference/TRACE_backtest_drift.md)
- [PRODUCTION_AUDIT](reference/PRODUCTION_AUDIT.md) · [STATUS_RECON](reference/STATUS_RECON.md) · [_reconcile-report](reference/_reconcile-report.md)
- [aerospike_242_inventory](reference/aerospike_242_inventory.md) · [basis_verify](reference/basis_verify.md) · [RUNBOOK_kaggle_multi_cpu](reference/RUNBOOK_kaggle_multi_cpu.md) (đã hấp thụ vào KAGGLE_RULES §1)

## Khác
- [../tasks/](../tasks/) — task theo thứ tự LOGIC. · [reports/](reports/) — log worker. · [golden/](golden/) — baseline JSON. · [archive/](archive/) — stale, truy vết.
