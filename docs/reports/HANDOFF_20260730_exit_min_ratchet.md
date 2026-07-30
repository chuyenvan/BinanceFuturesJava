# HANDOFF 2026-07-30 (tối) — Exit min-rate 0.03 + ratchet decoupling — ĐỌC TRƯỚC KHI LÀM TIẾP

> Nối mạch từ §0.0 SESSION_START (audit harness WFO, sáng 2026-07-30). Phiên này CHUYỂN HƯỚNG sang
> exit-formula theo yêu cầu Uni, KHÔNG còn ở bước "P0-P6 sửa harness" nữa. Đọc file này trước, đọc
> `EXIT_MACHINE_20260730_stop_schedule.md` (PHẦN 1-3) để có full algebra + số liệu.

## Bối cảnh 1 câu

Uni quan sát: crypto giật mạnh, SL đặt ở min-rate cũ (0.01032 ≈ 1%) bị trượt giá/phí ăn hết lãi →
muốn min-rate ≥0.03 (3%) + tìm công thức di chuyển SL tối ưu. Yêu cầu: KHÔNG tune entry+exit cùng
lúc (tránh overfit) — entry đã đóng băng, phiên này CHỈ động vào exit.

## Đã làm (3 việc, 4 commit, tất cả đã push local — CHƯA push remote nếu có remote)

1. **`3e66898`** — `RATE_PROFIT_STOP_MARKET` default 0.01032→0.03 trong `Configs.java` (đường
   production, không qua HPO) + sàn gene `StrategyWfoTask.java:77` 0.020→0.03 (trần giữ 0.050).
   Lý do: (a) chi phí round-trip 0.008 (fee 2 chân 0.002 + slippage 2 chân 0.003) ăn hết SL đóng
   băng ở +0.5% cũ; (b) **phát hiện quan trọng**: câu hỏi này ĐÃ được đo từ 2026-07-07, xem
   `docs/reports/trailing_stop_sweep_139.md` (script `TrailingStopSweepProbe.java`, commit
   `73f8c77`) — sweep 0.01032→0.05032 cho PnL 2.4×, calmar 2.3×, maxDD không đổi, holdMed
   7ph→52ph tại 0.03032. Khuyến nghị đó 3 tuần nay CHƯA từng được áp vào Configs.java, chỉ nằm
   trong report — đây là lý do việc này lẽ ra nên làm sớm hơn.
2. **`ccc05dc`** — đồng bộ 2 gene range cũ còn kẹt vùng "cắt non" TASK-139 đã xác nhận xấu:
   `WFORunner.java:74` (0.012-0.025) và `SensitivityTool.java:82` (0.005-0.025) → cả hai sang
   0.03-0.05. Cả 2 file này KHÔNG nằm trên đường production (chỉ `StrategyWfoTask` được
   `orchestrator/pipelines/*.json` gọi — xác nhận qua grep) — sửa cho hết là ví dụ sai, không đổi
   hành vi thật.
3. **`b203a78`** — thêm `Configs.TS_RATCHET_DECOUPLED` (env, **mặc định false = hành vi cũ y
   nguyên, byte-identical**). Root cause "dead zone": sau khi arm (`updateStatusNew`, dùng
   `predReturn15M`), SL đóng băng tới khi lãi vượt ratchet threshold = `TS_PROFIT_MULTIPLIER ×
   threshold(rateChangeMax90M)` trong `updateTPSL` — mặc định nhân 5.21847× nghĩa là giá phải chạy
   thêm ~4x đoạn đã lãi mà SL không nhúc nhích. Bật flag = bỏ hệ số nhân, ratchet kích hoạt ngay.
   Code tại `OrderTargetInfoTest.java` (arm dòng ~190, ratchet/`updateTPSL` dòng ~248).
   **CHƯA bật thử nghiệm — vẫn OFF, chưa có run nào đo tác động thật của flag này.**

Tài liệu: toàn bộ 3 việc trên đã ghi chi tiết ở `docs/reports/EXIT_MACHINE_20260730_stop_schedule.md`
PHẦN 3 (bảng số sweep cũ, lý do, giới hạn).

## Việc CHƯA xong — bị chặn, cần xử lý đầu tiên ở session mới

**N=13 window confirm** (đo tác động thật của thay đổi #1 trên verdict M, qua constraint harness V4
đầy đủ — khác sweep cũ TASK-139 vốn không qua harness này):

- Jar đã build (local `target/binance-java-sdk-1.2.4.jar`, md5 `f89c5a449de96a4f377e95dae2de936f`)
  và deploy lên Oracle tại `/home/ubuntu/java/simulator/binance-exit003-20260730.jar` (md5 verify
  OK, KHÔNG đè lên `binance-lf-frozen-1.0.0.jar` cũ của verdict M).
- **CHƯA bắn job.** Lý do dừng: `ce wfo_status` cho thấy job store "strategy_window" hiện tại có
  `DONE=7 FAILED=9 / total=16`, tất cả FAILED đều là
  `readDataFromAerospike1M ... EOFException` tới `STATE_HOST 103.157.218.226:3222` (server jobstore
  Aerospike dùng bởi hệ fanout `ce`/`mcp_tools-v3.py` — **KHÁC** với Aerospike Oracle local mà
  `asd --foreground` chạy trên box 161.118.212.3). Đã test: host 103.157.218.226:3222 TCP
  **reachable** (không sập cứng), nhưng:
  1. Chưa rõ 9 window FAILED này từ đâu (job cũ để lại, hay đang lỗi thật lúc này).
  2. Job store của `strategy_window` **dùng CHUNG cho mọi lần chạy, không cô lập theo `tag` ở tầng
     Aerospike** (chỉ cô lập id tiến trình phía orchestrator Python) — bắn job mới CÓ THỂ đụng lại
     đúng 9 window đang FAILED, chưa chắc coordinator retry sạch.
- **Đã hỏi Uni, CHƯA có câu trả lời** (câu hỏi cuối phiên trước): (a) cứ bắn fanout luôn xem sao,
  (b) điều tra thêm nguồn gốc 9 window FAILED trước, hay (c) Uni tự check/restart node Aerospike đó.

**Việc kế tiếp của session mới, THEO THỨ TỰ:**
1. Đọc câu trả lời của Uni cho câu hỏi trên (nếu có ghi ở đâu đó); nếu chưa, hỏi lại — ĐỪNG tự bắn
   fanout 6-node (2 Oracle + 5 Kaggle) khi chưa rõ trạng thái backend, tốn quota thật.
2. Cách an toàn hơn để thăm dò trước khi fanout full: dùng `wfo_run` (Oracle-only, 1 window, đúng
   mục đích "debug/verify" theo mô tả `orchestrator/profiles/wfo-fanout.json`) với jar
   `binance-exit003-20260730.jar`, xem 1 window chạy sạch chưa rồi mới quyết fanout thật.
   Cú pháp (qua `ce`, xem `mcp_tools-v3.py` dòng ~1309 `cmd_wfo_run`):
   `wfo_run <ds> [jar] [n] [seed] [workers] [tag]` — ds mặc định dùng
   `/home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff` hoặc dataset verdict M đã dùng, N nên = 30 (KHÔNG
   phải 1 — xem mục "Nhắc lại" bên dưới).
3. Sau khi N=30/13-window confirm chạy xong: so PnL/calmar/%OOS-dương với verdict M gốc (đã ghi ở
   `AUDIT_20260730_wfo_constraint_harness.md`), viết vào `EXIT_MACHINE...md` PHẦN 4, rồi mới tính
   tới việc bật thử `TS_RATCHET_DECOUPLED=true` làm 1 confirm RIÊNG (đừng gộp 2 biến 1 lần đo).

## ⚠️ Nhắc lại — tránh lặp lỗi N=1

Handoff gốc đầu phiên đã cảnh báo: "current numbers are N=1, not production-ready. After each step:
N=30 full 13-window confirm." `VerifyOneWindow`/`stage2_frozen_ab.sh` mẫu cũ dùng `WFO_N_SAMPLES=1`
— đúng cho so sánh nhanh nhưng KHÔNG phải confirm chuẩn. Confirm thật cho thay đổi #1 (và sau này
#3) phải chạy N=30 mẫu/cửa sổ như verdict M gốc, không phải N=1.

## Housekeeping CHƯA đụng (vẫn còn treo từ các phiên trước, không phải việc phiên này)

`notebooklm_ready/` (9 file staged-deleted + nhiều file mới tên khác), `clamp_analyze.py` và
`NEXT_SESSION_TODO_entry_alpha.md` (sai vị trí, ở root thay vì `docs/reports/`), vài file rác
`orchestrator/_*`, 4 thư mục `orchestrator/kernels_sl4h/*`, 4 thư mục
`ml/funding_selector/kaggle_*`. Không tự dọn — chờ Uni quyết.

## Việc lớn hơn vẫn treo từ đầu phiên (chưa quay lại)

Từ handoff gốc: (2) fix fitness mismatch (HPO chọn theo Calmar nhưng chấm theo raw-PnL-WFE), (3) bỏ
HPO argmax → genome regularized (nếu 1+2 chưa đủ). Cả hai CHƯA bắt đầu — phiên này rẽ sang exit
theo yêu cầu Uni giữa chừng, chưa quay lại harness.
