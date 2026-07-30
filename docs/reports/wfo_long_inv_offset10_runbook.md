# RUNBOOK — WFO pre-reg: SELECTOR_OFFSET=10 (Worst-N inverted selector)

**Ngày fire:** 2026-07-24 · **tag:** `long_inv_offset10` · **trạng thái:** RUNNING (16 window, 4 Oracle worker)

## Giả thuyết pre-registered
Audit tĩnh Kaggle (HORIZON=4h) báo Worst-N + cắt 10 coin bét bảng (offset=10) + lấy N=3 coin tiếp theo cho PnL thô cao nhất (+679% vs +531% ở offset=5, và lật dấu −679% ở offset=15). Câu hỏi pre-reg: **edge tĩnh này có sống sót OOS qua WFO + engine DCA/hard-SL của Java không, và drawdown về đâu?**

Ngưỡng chấp nhận = ngưỡng pre-reg chuẩn như baseline: **WFE median ≥ 0.5 và %OOS-dương ≥ 70%**. Không nới post-hoc.

## Cấu hình chạy
- **dataset:** `/home/ubuntu/claudedata/wfo_ds_oiz2022_75` (full 16-window, cùng dataset baseline sl15 — KHÔNG dùng `wfo_ds_inv_smoke` vì smoke không đánh giá được theo ngưỡng pre-reg).
- **jar:** `/home/ubuntu/java/simulator/preflight-v43.jar` (build mới, md5 `b1aacbda5ae39d38bc0fcef5483708d5`; KHÔNG đè v42 để giữ provenance baseline).
- **env:** `WFO_DISABLE_DCA=0,TIME_STOP_HOURS=24,SELECTOR_INVERT=1,SELECTOR_SCORE_MAX=0.5,SELECTOR_TOPN=3,SELECTOR_OFFSET=10`
  - `SELECTOR_INVERT=1` (KHÔNG phải `true` — Configs check `"1".equals(...)`).
  - `SELECTOR_TOPN=3` khớp audit N=3 (baseline sl15 dùng N=5 → hai config KHÁC nhau, đây là test giả thuyết audit, không phải add offset lên baseline).
- **worker:** 4 Oracle, kaggle=0.

## Thay đổi code (đã build vào v43)
- `Configs.java`: thêm `public static final int SELECTOR_OFFSET` (env, default 0 = byte-identical).
- `SimulatorMarketLevelTicker1MStopLoss.java` (~dòng 290): áp offset vào cả WORST-N và BEST-N, clamp chống IndexOutOfBounds. offset=0 → byte-identical.
- `SimulatorMarketLevelInvertedSelector.java`: **KHÔNG đụng** (không nằm trong WFO path — WFO chạy Ticker1MStopLoss).

## Theo dõi & verify (làm tay hoặc phiên sau)
```
ce wfo_status                       # DONE/RUNNING/FAILED/total
ce wfo_report long_inv_offset10     # khi DONE=16 & RUNNING=0
sed -n '1,22p' /home/ubuntu/claudedata/.run/mcp_ce/wfo_report_long_inv_offset10.md
```
Lấy: %OOS-dương, WFE median, worst maxDD, đếm SUCCESS/BURN/CAPITAL_LOCK/TOO_FEW/ZERO. FAILED>0 → cảnh báo, không kết luận.

Scheduler `wfo-worstn-sweep-advance` KHÔNG tự pick tag này (state của nó là SL-sweep, current_running_tag=null, auto_advance=false). Theo dõi thủ công.

## ⚠ Cảnh báo diễn giải (leakage đã biết)
offset=10 được chọn trên TOÀN dataset (gồm cả window OOS) → WFO này KHÔNG phải OOS sạch tuyệt đối cho offset. Kết quả tốt vẫn có thể do selection bias. WORST lật dấu +679%→−679% giữa offset 10 và 15 là dấu hiệu nhạy tham số cao (nghi overfit). Nếu qua ngưỡng: cần re-test với offset chọn TRONG train-window từng fold trước khi tin. Nếu không qua: xác nhận offset=10 chỉ là artifact tĩnh, quay lại hướng regime filter.
