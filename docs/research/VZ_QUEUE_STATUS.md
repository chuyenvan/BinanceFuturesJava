# VZ QUEUE STATUS — VZ_QUEUE_1014 (Q1→Q6)

Mỗi Q xong ghi 1 dòng: Q | trạng thái | commit | số chính. Trạng thái: DONE / BLOCKED / WAITING.

| Q | trạng thái | commit | số chính |
|---|---|---|---|
| Q1 | DONE | 997f18f3 | `SIM_RATE_FEE=0.000982` là phí **khứ hồi** (sim trừ 1 lần) ⇒ E1 cũ đếm gấp đôi; `cost_of` sửa cộng 1 lần; T3–T9 tính lại, spread nhóm bất biến max|Δ|=2,8e-17 (≤1e-9), chỉ mức dịch +0,000982. Proof `reports/fee_recompute.json` |
| Q2 | DONE | (see next commit) | 6 709 chân: nhóm tuổi 0-7=616, 8-30=437, 31-90=669, >90=570, unknown=4 417 (2 292 chân có tuổi chính xác/eproxy). net_exit TB: 0-7 +3,99 %, 8-30 +4,03 %, 31-90 +4,72 %, >90 +6,56 %, unknown +3,03 %. net_240 TB giảm dần theo tuổi: 0-7 +4,22 % → >90 +1,31 %. Chân ≤30 ngày = 1 053 (15,7 %) đóng góp **17,2 %** Σ net_exit; ≤7 ngày = 616 (9,2 %) đóng góp 10,0 %. Không GO. `reports/e1_q2_age_legs.json` |
| Q3 | BLOCKED | n/a | File per-leg EXEC đã bị xoá: `~/claude_master/1012/exec/legs.pkl` (script `exec_legs.py`) không còn; chỉ còn `need.json`, log, `docs/result/exec_result.json` (chỉ aggregate). Cache agg/kl đã xoá. Không tải lại aggTrades (Phase 2 chưa mở). ⇒ không dựng được bảng chi phí vào theo phút-trong-giờ. |
