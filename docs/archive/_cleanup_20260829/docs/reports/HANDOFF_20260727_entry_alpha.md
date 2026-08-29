# HANDOFF 2026-07-27 — Entry-alpha: trailing là hướng dương duy nhất nhưng WEAK; FREQUENCY là trần

> Đọc kèm: `docs/STRATEGY_ENTRY_ALPHA.md` (§9 lịch sử), `reports/trailing_oiz_wfo_20260727.md`,
> `reports/reprobe_dedup_short_20260726.md`. Nguyên tắc: đo-không-đoán, pre-register, validate-nhỏ, Uni quyết PnL/commit.

## TL;DR
- Selector (label `maxFav_H≥6%`): **selectability THẬT** (xsecIC 18/18 quý, dedup xác nhận KHÔNG phải overlap artifact) nhưng **KHÔNG monetize ở endpoint** (WEAK, alpha~0/âm sau cost).
- **Đã loại dứt khoát:** hard-SL/TP first-touch (âm hết), short bottom-decile (NOT_VIABLE), oi_z-veto-CHỒNG (frequency wall), hướng long-dài, relabel-cho-SL-cứng.
- **Trailing (DCA off, funding on) = hướng DƯƠNG duy nhất** trên path 1m thật: 9/10 window có-lệnh dương. **NHƯNG chưa PASS**: WFE median ≈0.24 (<0.5 → overfit), PnL dồn 1 window (w15 +7469), 7/13 window ZERO/TOO_FEW (frequency nghẽn).
- **Trần thật = FREQUENCY/gate**, KHÔNG phải exit. Đây là đòn bẩy kế tiếp (khớp memory "binding constraint = opportunity frequency").

## Kết quả đã đo (session 2026-07-26→27)

### Kaggle probes (kernel chuyendinh/ | code repo ml/funding_selector/kaggle_*/)
- `reprobe-unfiltered-wf-dedup`: overlap thổi #event ~9–19× nhưng xsecIC≈pooledIC (0.19–0.22), **18/18 quý dương giữ nguyên** → selectability thật. Endpoint alpha~0/âm-sau-cost. Spread top−bottom ≈0.
- `short-probe-bottom-decile`: **NOT_VIABLE** (pnl sau SL −0.16%, 0–1/18 fold dương). Coin điểm thấp underperform tương đối nhưng vẫn tăng tuyệt đối → short lỗ.
- `track-a-lite-firsttouch`: hard-SL/TP first-touch **mọi policy NO** (best −0.32%/−0.43%, 0–1/18 dương). SL bị quét bởi cú thọt-trước-bơm; endpoint (SL→∞) là cận trên vẫn âm.
- `oiz-gate-probe`: veto_q50 12h endpoint alpha **+0.055%, 12/18 quý dương, frequency sống** (2971 ev); soft_weight < off. → oi_z veto cải thiện chất lượng NHƯNG chỉ khi THAY selection, chưa net sau cost.

### Oracle WFO trailing (VerifyOneWindow, DCA off, funding on, TICKER_SOURCE=file) — `/home/ubuntu/claudedata/.run/trailfull/w*.log`
| win | oosPnl | wfe | ddPct | trades | note |
|---|---|---|---|---|---|
| 6 | +437 | 1.21 | 0.8% | 56 | SUCCESS |
| 8 | +797 | 1.36 | ~2% | 169 | SUCCESS |
| 10 | +411 | 0.29 | 3.7% | 240 | SUCCESS |
| 12 | +771 | 0.44 | 6.0% | 146 | SUCCESS |
| 15 | +7469 | 4.95 | 21% | 895 | SUCCESS (outlier, thống trị tổng) |
| 5/7/11 | +140/+133/+61 | 0.10/0.18/0.04 | thấp | 4–10 | TOO_FEW |
| 9 | +371 | 0.15 | 6.8% | 249 | CAPITAL_LOCK |
| 14 | −348 | −0.13 | 1.2% | 11 | TOO_FEW (âm) |
| 4/13/16 | 0 | — | — | 0 | ZERO_TRADES |

**Verdict trailing vs pre-register (WFE med≥0.5 / %OOS≥70% / maxDD≤50%):** WFE med 0.24 **FAIL**; maxDD 21% PASS; %OOS 90% (traded) / 69% (gồm zero). PnL dồn w15. → **PROMISING nhưng WEAK, KHÔNG deploy.**

## Hạ tầng / tooling (để session mới khỏi dò lại)
- **Chạm Oracle:** `orchestrator/ce.cmd` (Git-ssh `C:\Program Files\Git\usr\bin\ssh.exe`, key `C:\Users\pc\.ssh\id_rsa_chuyennd`, ubuntu@161.118.212.3). **Windows-OpenSSH raw ssh FAIL (exit 255)** — chỉ dùng Git-ssh / ce.cmd.
- **ce menu chính:** `sys_health`, `bg_run/bg_status/bg_report`, `wfo_verify <ds> <win> "<env phẩy>"`, `wfo_fanout <ds> [jar] [n] [seed] [oracle_workers] [kaggle] [tag] [env]`, `wfo_status`, `wfo_report <tag>`, `kaggle_slots/push/status/output`.
- **Gotchas (đã cắn):** (1) interact cap ~180s → job dài phải `bg_run`/`setsid ... </dev/null >log 2>&1 &` detached; (2) dataset PHẢI symlink vào cwd jar `~/java/simulator/<ds>`; (3) extra_env **PHẨY-phân tách** (space → chỉ nhận key đầu); (4) remote grep KHÔNG dùng `|` alternation (PowerShell tách) — dùng `grep -e` / pattern đơn; (5) `TICKER_SOURCE=file` (dataset có market.bin) nhanh + né hard-timeout 1800s của wrapper (đã giết w12 lần chạy aerospike).
- **Kaggle:** CLI local có creds. Dataset ticker `hpo-ticker-daily` = **ticker 1-PHÚT intraday shard-ngày** (1826 file `ticker_YYYYMMDD.bin`, ~662 sym×1440', **v6 2026-07-13 post ghost-clean**; KHÔNG dùng bản 07-04 stale). `wfo-ds-ret2-4h-ff` = sync từ Oracle `wfo_ds_ret2wf_4h_ff` (cùng preds). `java-run-lc` = jar.
- **CẢNH BÁO fanout:** kernel Kaggle hiện đọc ticker từ **Aerospike 226 (network)**, KHÔNG đọc `hpo-ticker-daily` file → fanout `trailfan` FAILED 9/16 (network). Kaggle CHƯA self-contained; muốn dùng phải wire `TICKER_SOURCE=file` trong `run_worker.py`/kernel.
- Disk Oracle **89%** (~17GB trống) — để ý output.
- Datasets Oracle: `wfo_ds_ret2wf_4h_ff` (selector, symlink đã tạo), `wfo_ds_oiz75`/`wfo_ds_oiz2022_75` (oi_z veto CHỒNG). Jar: `preflight-v42.jar` (verify), `binance-futures-wfo-lf.jar` (leak-free).

## Trạng thái job lúc handoff
- Oracle sweep trailing: **DONE** (summary ALL_DONE). w4–16 kết quả ở `~/claudedata/.run/trailfull/`.
- Fanout `trailfan`: DONE 7 / **FAILED 9** (aerospike network) — KHÔNG trust cho verdict; nên `ce wfo_stop` + `sys_zombies kill=true` dọn nếu còn sót.
- Specs CHƯA vào repo (đang ở scratchpad outputs): `SPEC_TRACK_A_LITE.md`, `SPEC_EVAL_FRAMEWORK.md` — copy vào `docs/` nếu muốn giữ.

## NEXT (đề xuất, thứ tự ưu tiên)
1. **FREQUENCY / gate = đòn bẩy cao nhất.** 7/13 window trailing bị ZERO/TOO_FEW. Nguồn: (a) Task 156 coverage 2022; (b) gate MOM15 cùn (`AIRejectFilter` + `MIN_MOMENTUM_15M`, 1 giá trị/phút toàn thị trường, ngưỡng cao → khóa cả window). Mở gate = mở khoá trailing. Test gate-ablation: `{oiz thay gate}×{MIN_MOMENTUM_15M baseline/thấp/~0}`, chấm joint net-EV × frequency-floor.
2. **Chống overfit HPO trailing** (WFE 0.24): giảm DOF genome / regularize; KHÔNG tin outlier w15.
3. **oi_z dạng THAY gate** (bỏ MIN_MOMENTUM_15M), KHÔNG chồng thêm veto — screen Kaggle gợi ý giữ frequency + tăng chất lượng.
4. (hạ tầng) wire kernel Kaggle `TICKER_SOURCE=file` đọc `hpo-ticker-daily` → self-contained + mới cross-check ticker Kaggle vs Oracle được (parity kernel: cùng VerifyOneWindow/window/genome/config, chỉ khác nguồn ticker).
5. **Điều kiện đóng nhánh:** nếu mở frequency mà trailing vẫn WFE-fail + dồn 1 window → kết luận edge maxFav **non-monetizable cho retail long-only**, đóng entry-alpha.

## Việc PnL/quyết định thuộc Uni
Chưa commit gì (mọi thay đổi repo là doc + code Kaggle probe, không đụng production 242). Chọn hướng (1) gate/frequency vs (3) oi_z-thay-gate là quyết định của Uni.
