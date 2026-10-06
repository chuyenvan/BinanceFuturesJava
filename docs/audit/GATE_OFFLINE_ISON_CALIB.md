# GATE_OFFLINE_ISON_CALIB — P0.a: hiệu chuẩn iso-n bằng đếm offline

Ngày 2026-10-06 (GMT+7). Pre-reg `docs/prereg/PREREG_GATE_K_FRONTIER.md` §4 P0.a (MASTER, commit `4e4fc975`); kết quả ở ADDENDUM-1 (commit kèm file này). Brief: `Claude outputs/BRIEF_GATE_K_FRONTIER_20261006.md`.
Thuần offline, 0 PnL, 0 Java/sim/Kaggle. Seed 42 (A1). Driver `research/analysis/gate_k_frontier_driver.py`; JSON `docs/audit/GATE_OFFLINE_ISON_CALIB.json`. `gate_offline.py` mở rộng `--topk --pct`.

## 1. Validate bộ đếm (cổng §4 P0.a, ≤2%) — PASS

| Run | K | pct | pass offline | pass sim | lệch |
|---|---|---|---|---|---|
| n700-a1 | 24 | 0,999950829 | 3233 | 3231 | **+0,062%** |
| n700-a2 | 16 | 0,99985 | 5955 | 5950 | **+0,084%** |
| gqsf-a1 (NỀN s42) | 24 | 0,999950829 | 3226 | 3232 | **−0,186%** |

3/3 ≤2% ⇒ bộ đếm đáng tin. (Lưu ý kỹ thuật: phải truyền đúng printDone của CHÍNH run làm khoá "coin đang giữ"; nếu dùng nhầm run khác, n700-a2 lệch +44%.)

## 2. pct cuối (iso-n) — 8/8 arm Phase 1 đạt ≤1%

`pass_NỀN_s42 = 2653` (symbol-pass 2022–2025, K24 pct base). `pass_target(n_t) = 2653 × n_t / 736`.

| Đường | K | n_t | pct | pass offline (22–25) | phút mở/năm 22/23/24/25 | K hiệu dụng | dev |
|---|---|---|---|---|---|---|---|
| iso-736 | 12 | 736 | 0,999924707 | 2679 | 175/215/172/270 | 12,0 | +0,98% |
| iso-736 | 16 | 736 | 0,999937768 | 2646 | 185/170/146/233 | 16,0 | −0,26% |
| iso-736 | 32 | 736 | 0,999981560 | 2649 | 209/39/200/130 | 32,0 | −0,15% |
| iso-736 | 40 | 736 | 0,999999884 | 2669 | 89/18/93/71 | 40,0 | +0,60% |
| iso-1000 | 16 | 1000 | 0,999922492 | 3609 | 232/228/202/293 | 16,0 | +0,12% |
| iso-1000 | 24 | 1000 | 0,999939977 | 3607 | 226/176/173/242 | 24,0 | +0,07% |
| iso-1000 | 32 | 1000 | 0,999971815 | 3624 | 261/60/259/200 | 32,0 | +0,54% |
| iso-1000 | 40 | 1000 | 0,999993736 | 3572 | 113/25/118/88 | 40,0 | −0,90% |

- **K hiệu dụng = K** ở mọi arm (0% tick thiếu ứng viên). Không có arm nào phải hạ K vì thiếu ứng viên.

## 3. CỜ ĐỎ: K48 không đạt iso-1000 (ảnh hưởng P0.b §4)

- K48: pct `0,999999869` → pass offline **4446** (≈1227 lệnh/năm), **dev +23,34%**, KHÔNG đạt target 3605.
- Cơ chế **sàn pass tăng theo K**: `fac = max(DYN_MIN, sp/0,15·1,2876)` kẹp nhóm `sp` nhỏ về cùng hệ số `DYN_MIN`; vì p15 là market-level (chung cả phút), một phút p15 cực trị mở gate cho **cả nhóm floored-fac** cùng lúc. Nới K ⇒ thêm symbol vào nhóm ⇒ sàn cao hơn. Sweep pct: **K24 → 0, K40 sàn ~737, K48 sàn ~1227 lệnh/năm**.
- Hệ quả: **P0.b "K48 @ pct iso-1000" bất khả thi**. Cần MASTER/owner chọn: (a) chạy P0.b K48 ở sàn (~1227/năm); (b) đổi P0.b sang K40 (đạt ~974); (c) hướng khác.
- Lưu ý chấm: iso-736 K40 & iso-1000 K40 dùng pct cực đoan (0,999999884 / 0,999993736) — gate gần đóng, "đều lệnh" thoái hóa; arm K≤32 dùng pct dải bình thường.

## 4. Bước tiếp (theo §11 pre-reg)

Cổng nền (NỀN s42 md5 `gqsf`) → P0.b (chờ MASTER chốt K48) → Phase 1 (8 kernel, dùng pct ADDENDUM-1) → Phase 2 → Phase 3 (nếu luật cho phép).
