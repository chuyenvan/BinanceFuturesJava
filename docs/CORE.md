# CORE — Luật luôn-nạp (mọi CCD/CDK/headless mang theo, recall bắt buộc)

> Hạt nhân an toàn: luật mà quên = hại KHÔNG đảo ngược (mất data/tiền/máy) hoặc backtest sai ÂM THẦM.
> Chi tiết theo ngữ cảnh: xem `docs/index.md` để nạp đúng pack cho việc đang làm. KHÔNG nhồi chi tiết vào đây.

## Ngôn ngữ
- Trả lời người dùng bằng **tiếng Việt**.

## An toàn vận hành (KHÔNG đảo ngược được)
- ⛔ KHÔNG ghi file/log/output ra **ổ C** (`/tmp`, `~/`, `C:\...\Temp`). Dùng `/d/claudedata` (local) hoặc trên 226. Đã crash MCP 3 lần. → `KAGGLE_RULES.md §0`.
- ⛔ KHÔNG `pkill`/`killall java`. Chỉ kill ĐÚNG PID job mình spawn. TUYỆT ĐỐI không kill: `BinanceDataIngestor`, `BinanceOrderTradingManager` (2 process live), Aerospike, Redis, HPO của user. → luật dọn-job 226.
- 🔒 Deploy code / restart 2 process live = **CHỈ user tay**. CCD chỉ build jar + soạn runbook. (Tác động DỮ LIỆU 242 qua 226 thì CCD làm được — job data, không phải deploy.)
- 🔒 `config/PrivateConfig.java` / `runAider.bat` chứa key live đã lộ trong git — KHÔNG echo secret ra log/commit/chat; nhắc user rotate.
- Tool batch chạy Kaggle/nền: cuối `main()` phải `System.exit(0)` (lỗi `1`). Thiếu → kernel treo tới 12h, MẤT output. KHÔNG áp cho 2 process live (chúng cố ý chạy mãi).

## Toàn vẹn backtest (sai ÂM THẦM nếu quên) — chi tiết tại pack backtest
- KHÔNG look-ahead nội-nến (`Configs.BLOCK_INTRABAR_LOOKAHEAD=true`); đặt SL nến này, khớp nến sau.
- Mọi backtest "thật" đi qua `BacktestIntegrityGuard.assertProductionGrade()` (đã cắm ở `simulatorWithInitEntry`). KHÔNG bỏ; chỉ nới khi CỐ Ý chạy đối chứng.
- Fee + slippage 2 chân LUÔN bật (`RATE_FEE`, `SLIPPAGE_RATE`, `APPLY_SLIPPAGE=true`). Tắt = lãi ảo.
- Bump `CONFIG_VERSION` (`RunHpoMaster_Distributed`) khi đổi thứ ảnh hưởng backtest NGOÀI genome (fee/slippage/trailing/breaker/guard/đổi model/số gene). Quên = cache HPO trả điểm cũ → run vô nghĩa.

## Code an toàn — chi tiết tại pack code
- CẤM `catch` câm/rỗng/comment-suông. Mọi catch phải `LOG.warn/error` kèm exception + ngữ cảnh (symbol/key/ts). KHÔNG `printStackTrace`/`System.out`.
- Logging dùng **SLF4J → Logback**. KHÔNG `System.out`.

## Thống nhất ngôn ngữ — Java là nguồn chân lý (chốt 2026-06-24)
- TOÀN BỘ pipeline **dữ liệu + logic xử lý** PHẢI là **Java** — kể cả **dữ liệu TRAIN** cũng do Java export (vd `ExportFeaturesForPythonTool` sinh ff_*.bin, `ExportFundingOiPerCoin` sinh OI). KHÔNG để Python (hay ngôn ngữ khác) tính/biến đổi feature dùng cho train/inference.
- **DUY NHẤT** được phép là Python: code **train** model (`ml/**/train_*.py`) và code **validate/test/compare** (đối chiếu, đo lệch). Đây là tiêu thụ dữ liệu Java, KHÔNG sinh/biến đổi dữ liệu.
- Lý do: 2 ngôn ngữ cùng tính 1 feature = nguồn lệch ngầm (đã dính nhiều lần: cross-sectional population, basket warmup, OI merge). Một nguồn chân lý (Java) loại trừ lớp lỗi này.
- **Provenance:** model/artifact luôn đi kèm code+data Java đã sinh ra nó. Khi model lệch khỏi Java export hiện tại → **TRAIN LẠI** trên Java export mới (KHÔNG revert code, KHÔNG lệ thuộc artifact cũ mất dấu). Mất code/nguồn của artifact = artifact chỉ còn dùng làm benchmark, không phải chân lý.

## Tròn việc hoặc thành Task — chống job nửa chừng / chờ mù (chi tiết: rules/task-workflow)
- Mọi việc khởi động phải kết ở 1 trong 2: **TRÒN** (chạy xong + VERIFY bằng số NGAY trong phiên) hoặc **THÀNH TASK** (`tasks/<id>.md` có checkpoint + acceptance + theo dõi). KHÔNG có trạng thái thứ 3 "lửng lơ".
- ⛔ KHÔNG spawn job nền nếu thiếu 1 trong 3: (a) cách ĐO tiến độ (queue/done-count/log mốc có timestamp, nơi bền); (b) điều kiện KẾT THÚC + ước lượng thời gian; (c) cách VERIFY khi xong. Thiếu → thành task hoặc không chạy.
- Việc > ~vài phút / distributed / ghi data thật / không chắc xong trong phiên → MẶC ĐỊNH là task (file + queue), KHÔNG ad-hoc nền.
- Đổi hướng: việc đang dở phải DỪNG sạch (kill ĐÚNG PID mình spawn + ghi trạng thái lại) hoặc chốt task resume được. CẤM bỏ process mồ côi chạy nền.
- "Done" = có số ĐO (validate dữ liệu), KHÔNG phải "lệnh đã chạy xong".

## Phản biện & tìm giải pháp tốt hơn (user đề cao — áp cho việc CÓ TẦM ẢNH HƯỞNG)
- User LUÔN đề cao phản biện + câu hỏi "còn giải pháp nào tốt hơn không". **Kể cả khi user ĐÃ CHỐT phương án, hoặc Claude đã chốt** — nếu thấy giải pháp tiềm năng hơn thì PHẢI phân tích sâu hơn (đánh đổi, rủi ro, chi phí đảo ngược) rồi mới quyết, KHÔNG im lặng làm theo.
- **Ngưỡng áp dụng:** chỉ cho việc có tầm ảnh hưởng (kiến trúc, cách scale, hàm mục tiêu, thay đổi lõi PnL, chọn dọc/ngang...). Việc vặt (đặt tên file/biến, format) thì KHÔNG bới — bới việc vặt là tự tạo bottleneck.
- Cách làm đúng: nêu phương án thay thế + phân tích đánh đổi NGẮN GỌN → để user quyết. KHÔNG tự đổi hướng đã chốt mà không nói. Cũng KHÔNG phản biện lấy lệ/dài dòng.

## Khi nhận task
- Đọc `docs/index.md` → nạp pack theo ngữ cảnh việc đang làm (code / backtest / run-226 / kaggle / db / deploy).
- Đọc `docs/AGENT_WORKFLOW.md` + `docs/AGENTS.md` TRƯỚC khi claim task (nhiều CCD không thấy nhau; claim để khỏi đụng).
- Gặp blocker thật → DỪNG, báo user. KHÔNG tự ý planning / refactor hàng loạt (codebase ~250 class, ràng buộc ngầm). Sửa nhỏ, mỗi thay đổi một mục đích.
