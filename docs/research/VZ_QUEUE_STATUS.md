# VZ QUEUE STATUS — VZ_QUEUE_1014 (Q1→Q6)

Mỗi Q xong ghi 1 dòng: Q | trạng thái | commit | số chính. Trạng thái: DONE / BLOCKED / WAITING.

| Q | trạng thái | commit | số chính |
|---|---|---|---|
| Q1 | DONE | 997f18f3 | `SIM_RATE_FEE=0.000982` là phí **khứ hồi** (sim trừ 1 lần) ⇒ E1 cũ đếm gấp đôi; `cost_of` sửa cộng 1 lần; T3–T9 tính lại, spread nhóm bất biến max|Δ|=2,8e-17 (≤1e-9), chỉ mức dịch +0,000982. Proof `reports/fee_recompute.json` |
| Q2 | DONE | (see next commit) | 6 709 chân: nhóm tuổi 0-7=616, 8-30=437, 31-90=669, >90=570, unknown=4 417 (2 292 chân có tuổi chính xác/eproxy). net_exit TB: 0-7 +3,99 %, 8-30 +4,03 %, 31-90 +4,72 %, >90 +6,56 %, unknown +3,03 %. net_240 TB giảm dần theo tuổi: 0-7 +4,22 % → >90 +1,31 %. Chân ≤30 ngày = 1 053 (15,7 %) đóng góp **17,2 %** Σ net_exit; ≤7 ngày = 616 (9,2 %) đóng góp 10,0 %. Không GO. `reports/e1_q2_age_legs.json` |
| Q3 | BLOCKED | n/a | File per-leg EXEC đã bị xoá: `~/claude_master/1012/exec/legs.pkl` (script `exec_legs.py`) không còn; chỉ còn `need.json`, log, `docs/result/exec_result.json` (chỉ aggregate). Cache agg/kl đã xoá. Không tải lại aggTrades (Phase 2 chưa mở). ⇒ không dựng được bảng chi phí vào theo phút-trong-giờ. |
| Q4 | DONE | (see next commit) | H-F imbalance 15′→4h/12h, 8 biến thể: IC nhóm M15 âm tách 0 (−0,0033…−0,0064) nhưng spread quintile chỉ −2…−2,6 bps < chi phí khứ hồi ~10 bps ⇒ không đáng kể kinh tế. Nhóm M00 IC ≈ 0. Không GO. `reports/e1_q4_imbalance.json` |
| Q5 | DONE | (see next commit) | Đã thêm §6c vào `docs/result/VZ_EXPLORE_2024.md` (Q1 phí + bảng kịch bản, Q2 tuổi symbol, Q3 BLOCKED, Q4 H-F); tổng phép thử mới 12 ⇒ sổ 38→50; ≤2 ứng viên (tuổi symbol; H-F loại) — không GO. Ledger cập nhật (dòng 39–50 + note Q1). |
| Q6 | WAITING | n/a | Chưa đủ lake 2022/2023/2025 (+lookback). Guard đã kiểm: `e1_confirm.py --years 2022,2023,2025` REFUSE (28 tháng kline1m thiếu). Addendum 1 (Q1.4) đã commit. Kiểm lại mỗi khi một năm Phase 1 xong. |

## Ghi chú thứ tự lake (MASTER 10-15 07:02)
- Phase 1 sẽ build **`2021-12` TRƯỚC** (sau khi xong 2022), rồi 2021-01→11 → 2026 → 2020s.
- **Gate Q6 (B4) = 2022 + 2023 + 2025 + `2021-12`** (2021-12 là lookback ≤30 ngày cho 2022). 2022-12, 2024-12 đã có.
- Khi đủ gate ⇒ chạy `e1_confirm.py --prereg docs/prereg/PREREG_VZ_B4.md --years 2022,2023,2025` **đúng 1 lần**.

## QUEUE_1015 — P1..P5 (MASTER 10-15)
| P | trạng thái | commit | số chính |
|---|---|---|---|
| P2 | RUNNING | (commit này) | Collector liquidations forward đã chạy nền trên Oracle (pid 3750693, `setsid nohup`) + cron watchdog 5′. **Root cause file cũ 0 dòng thực chất đã chạy nhưng không ghi dòng nào từ 2026-09-12**: endpoint raw `wss://fstream.binance.com/ws/!forceOrder@arr` bị host Oracle nhận HTTP-101 nhưng **0 frame** (cả `/ws/<sym>@aggTrade` cũng 0); chỉ endpoint **combined** `wss://fstream.binance.com/market/stream?streams=!forceOrder@arr` mới stream. File mới ghi `~/collect/liq/YYYY-MM-DD.csv.gz` (UTC), heartbeat 5′, reconnect backoff, watchdog stale 300s. Số event 1h: đang chờ. |
| P1-RESIDUAL | DONE | (commit này) | 3 hạng mục treo đã xác minh: (1) `b7c89f09`=`sim-jar-nsel`, `0944841c`=`sim-jar-gqsf` ⇒ **ĐÃ BỊ XOÁ trên Kaggle** nhưng jar **đúng sha còn nguyên trên đĩa** (`~/src_wt_nsel/target/…` từ `df021437`, `~/src_wt_gqsf/target/…` từ `128290af`) ⇒ **khôi phục được, KHÔNG BLOCKED**; `246087fb`(`sim-jar-ecost`) còn ✓. (2) "bundle Vision A/B" = `sim-ho26-bundle` + `sim-ho26a-bundle` ⇒ **CÒN ĐỦ** (funding.bin 5 GB…). (3) template `ho4p1-c2` khai dataset_sources = `sim-ho26a-bundle` + 7×`wfo-ticker-*` + `sim-jar-nsel`; thiếu **`sim-jar-nsel`** ⇒ template chưa chạy được tới khi đẩy lại. Output `docs/data/KAGGLE_REQUIRED.md` |
| P1 | DONE (lõi) + 3 mục xác minh tiếp | 1b8455c0 | Mọi `vz-*` (10) + `bcast-2020-2021h1-p1` + `sim-ho26(-a)-bundle` + `ho4p1-code`/`ho4p1-jar-exp` + `sim-jar-ecost` + `wfo-ticker-2021..2025` **đều CÒN ĐỦ** trên Kaggle (đã xác minh). Chưa map 2 jar nền (b7c89f09/0944841c) + "bundle Vision A/B" + dataset template sim ⇒ chuyển bước xác minh. Output `docs/data/KAGGLE_REQUIRED.md` |
