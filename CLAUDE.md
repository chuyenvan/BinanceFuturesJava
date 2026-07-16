# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⛔ ĐỌC NGAY — TRƯỚC KHI LÀM BẤT CỨ GÌ
1. **`docs/CORE.md`** — luật an toàn + toàn vẹn backtest (LUÔN áp, recall bắt buộc).
2. **`docs/index.md`** — router tri thức: từ đây nạp đúng pack cho loại việc đang làm.

> Trả lời người dùng bằng **tiếng Việt**.
> File này CỐ TÌNH MỎNG (chống phình + chống drift) — luật thật nằm ở `CORE.md` và các pack; KHÔNG chép luật vào đây.

## Nạp pack theo việc (đường dẫn + 1 dòng mô tả ở `docs/index.md`)
- Sửa code Java / HPO → `docs/rules/code.md`
- Chạy/sửa backtest · sim · golden → `docs/rules/backtest.md`
- Chạy job java trên 226 → `docs/rules/run-226.md`
- Chạy/giám sát job dài · pipeline · nút bấm CE → `docs/rules/ce-buttons.md` (⛔ cấm bash driver ad-hoc khi nút/pipeline có sẵn)
- Build Maven / môi trường dev → `docs/rules/build-env.md`
- Đụng secret / key → `docs/rules/security.md`
- Chạy Kaggle → `docs/KAGGLE_RULES.md`
- Đọc/ghi/chọn-nơi-chạy theo data → `docs/db/` (242 source · 226 compute · redis)
- Điều phối / nhận & chạy task nhiều CCD → `docs/rules/task-workflow.md` + `docs/AGENT_WORKFLOW.md` + `docs/AGENTS.md`
- Bức tranh lớn codebase → `docs/architecture.md`
- Lộ trình & mô hình → `docs/ROADMAP.md` · `docs/REBUILD_ROADMAP.md` · `docs/FINDINGS.md`

> 2 process live: `websocket/BinanceDataIngestor.main()` + `trading/BinanceOrderTradingManager.main()`. ⛔ Deploy/restart = NGƯỜI tay (xem `docs/CORE.md`).
> Thứ tự ưu tiên công việc kiểm chứng: `docs/ROADMAP.md`.
