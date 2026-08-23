# Phase 3 — Matrix 5m×15m × threshold × moveSL — HOÀN TẤT (2026-08-14)

## ✅ 18 ô xong: 5m (12 ô = 4 thr × 3 moveSL) + 15m (6 ô = 2 thr × 3 moveSL). 16 window sạch 2022Q1..2025Q4.
- **Lưới 5m** = train15→pred5 (B-series), `selector-15mtr-pred5-net*`.
- **Lưới 15m** = train15→pred15 (G-series, TRACKC), kernel `selector-15mtr-pred15-net{008,015}-gpu` (predict-only tại grid train, features 15m).
- 2 fold 2026 FAIL mọi ô (run_worker hardcode `WFO_MAX_OOS_DATE=20260101`, Kaggle không inject env → harness nit, gỡ Phase 4). Không ảnh hưởng so sánh (mọi ô cùng 16 window apples-to-apples).

### Bảng LƯỚI 5m (full-16)
| tag | thr | moveSL | total | t | %pos | **maxDD** | PF |
|-----|-----|--------|------:|--:|----:|--------:|---:|
| B008 | 0.008 | 0.03 | 15,139 | 2.98 | 69 | 796 | 11.4 |
| B015 | 0.015 | 0.03 | 17,596 | 2.70 | 81 | 1,985 | 8.5 |
| B02 | 0.02 | 0.03 | 18,342 | 2.86 | 88 | 2,217 | 7.4 |
| B03 | 0.03 | 0.03 | 4,672 | 0.59 | 62 | 7,848 | 1.5 |
| B008sl05 | 0.008 | 0.05 | 17,987 | 2.50 | 69 | 1,805 | 5.7 |
| B015sl05 | 0.015 | 0.05 | 23,526 | 2.57 | 88 | 3,365 | 7.2 |
| B02sl05 | 0.02 | 0.05 | 21,866 | 2.67 | 75 | 3,643 | 5.7 |
| B03sl05 | 0.03 | 0.05 | 10,829 | 1.03 | 69 | 7,584 | 2.1 |
| B008sl08 | 0.008 | 0.08 | 15,899 | 1.34 | 62 | 4,731 | 2.7 |
| B015sl08 | 0.015 | 0.08 | 23,158 | 1.91 | 81 | 5,792 | 4.1 |
| B02sl08 | 0.02 | 0.08 | 17,002 | 1.52 | 62 | 5,693 | 2.7 |
| B03sl08 | 0.03 | 0.08 | 20,694 | 1.64 | 75 | 4,761 | 2.9 |

### Bảng LƯỚI 15m (full-16)
| tag | thr | moveSL | total | t | %pos | **maxDD** | PF |
|-----|-----|--------|------:|--:|----:|--------:|---:|
| **G008** | 0.008 | 0.03 | 14,233 | 2.50 | 88 | **358** | **32.9** |
| G015 | 0.015 | 0.03 | 15,527 | 2.24 | 88 | 1,611 | 8.3 |
| **G008sl05** | 0.008 | 0.05 | 16,574 | 2.52 | 81 | **589** | **14.0** |
| G015sl05 | 0.015 | 0.05 | 20,736 | 2.63 | 81 | 2,348 | 8.6 |
| G008sl08 | 0.008 | 0.08 | 19,749 | 2.02 | 75 | 2,210 | 4.7 |
| G015sl08 | 0.015 | 0.08 | 21,600 | 2.03 | 69 | 3,287 | 5.3 |

## SO SÁNH 5m vs 15m (cùng thr×moveSL) — total / maxDD / PF
| config | 5m | 15m | Nhận xét |
|--------|----|----|----|
| 008 sl03 | 15,139 / 796 / 11.4 | 14,233 / **358** / **32.9** | 15m maxDD nửa, PF gấp 3, total ~ -6% |
| 015 sl03 | 17,596 / 1,985 / 8.5 | 15,527 / 1,611 / 8.3 | 15m DD thấp hơn, total -12% |
| 008 sl05 | 17,987 / 1,805 / 5.7 | 16,574 / **589** / **14.0** | 15m DD 1/3, PF gấp 2.5, total -8% |
| 015 sl05 | 23,526 / 3,365 / 7.2 | 20,736 / 2,348 / 8.6 | 15m DD -30%, PF cao hơn, total -12% |
| 008 sl08 | 15,899 / 4,731 / 2.7 | 19,749 / 2,210 / 4.7 | 15m HƠN cả total lẫn DD |
| 015 sl08 | 23,158 / 5,792 / 4.1 | 21,600 / 3,287 / 5.3 | 15m DD -43%, total -7% |

**Kết luận đối chiếu (rất rõ):**
1. **Lưới 15m có maxDD THẤP HƠN 5m ở CẢ 6 cặp config** — thường 30–60% nhỏ hơn. Lưới thực thi 5m mịn hơn KHÔNG cắt đuôi, mà LÀM ĐUÔI TO HƠN (nhiều điểm vào hơn → nhiều lệnh dính whipsaw pump-rồi-dump).
2. **Total: 5m nhỉnh hơn ~6–12% ở moveSL 0.03/0.05; ở moveSL 0.08 thì 15m HƠN.** Chênh total nhỏ so với chênh maxDD.
3. **Risk-adjusted (t, PF, maxDD): 15m thắng ở threshold 0.008.** G008: maxDD **358**, PF **32.9**, t 2.50, %pos 88 — Calmar-like ~40, gấp đôi B008 (5m) về cả maxDD lẫn PF.
4. Trả lời trực tiếp mối lo project (đuôi/maxDD lớn): **nguồn đuôi lớn một phần đến từ chính lưới 5m** — chuyển execution về 15m cắt đuôi đáng kể mà chỉ mất ít total.

## ⭐ BEST CONFIG (cập nhật sau khi có 15m)
- **Risk-adjusted tốt nhất tuyệt đối: G008 (15m, thr 0.008, moveSL 0.03).** maxDD 358, PF 32.9, t 2.50, total 14,233, %pos 88. Đuôi cực gọn — khớp nhất mối lo maxDD của project.
- **Cân bằng total-vs-đuôi: G008sl05 (15m, 0.008, 0.05).** total 16,574, maxDD 589, PF 14.0, t 2.52. Thêm ~16% total mà DD vẫn cực nhỏ.
- **Ưu tiên total tuyệt đối (chấp nhận đuôi): B015sl05 (5m, 0.015, 0.05)** total 23,526 nhưng maxDD 3,365 (gấp ~9× G008). Hoặc B02 sl03 (5m) total 18,342 maxDD 2,217.
- **Loại:** thr 0.03 (edge vỡ ở 5m); moveSL 0.08 nói chung (t tụt <2, đuôi to) trừ khi cần total.

→ **Phase 4:** khuyến nghị chốt **G008 (15m/0.008/sl03)** làm anchor robust; G008sl05 nếu muốn thêm total. Sign-test, holdout 2024H2+, STEP3 rank-K {5,8,12}. Lưu ý B03sl08 (5m) total cao (20,694) nhưng t 1.64/maxDD 4,761 → không robust, đừng bị total đánh lừa.

## Xu hướng tổng (2 lưới)
- **Threshold:** 0.008–0.02 có edge thật (t 2.2–3.0); **0.03 vỡ ở 5m** (t<1.1) nhưng ở 15m chỉ chạy 0.008/0.015 (user chọn 2 thr mạnh).
- **moveSL:** đỉnh total quanh 0.05; lên 0.08 total phần lớn giảm hoặc phẳng, t tụt mạnh, maxDD phình → nới stop quá 0.05 chỉ phình đuôi.
- **Grid:** 15m = ít đuôi hơn, total hơi thấp hơn; 5m = total nhỉnh, đuôi to hơn.

## Sự cố lần chạy này (đừng lặp)
- **Disk-full 194G (100%)** giữa build B02sl05 → funding.bin cụt → worker A6 BLOCK → DONE=0. Gỡ: xóa `wfo_ds_*` (rebuildable). Chain mới auto rm wfo_ds sau mỗi tag.
- **Manifest-version race:** worker push quá sớm bám version dataset cũ (thiếu manifest) → ERROR `MISSING glob /kaggle/input/**/manifest.txt`. Gỡ: re-push 5 worker sau khi `datasets files` xác nhận manifest. (Chỉ dính B02sl05 do slug có version cũ; các slug mới không dính.)

## Cấu hình / con trỏ
- SSH Oracle: key `id_rsa_chuyennd_openssh` (handoff cũ nhầm mất key). `ssh -i ~/.ssh/id_rsa_chuyennd_openssh -o PubkeyAcceptedAlgorithms=+ssh-rsa -o IdentitiesOnly=yes ubuntu@161.118.212.3`.
- Kernel 5m: `selector-15mtr-pred5-net{008,015,02,03}-gpu`. Kernel 15m: `selector-15mtr-pred15-net{008,015}-gpu` (kB15/, TRACKC).
- Fanout `drive_exp18.sh <TAG> 0`. moveSL = `SIM_RATE_PROFIT_STOP_MARKET` trong run_worker.py (đã REVERT sl03 baseline, md5 8173d86a71ba).
- DONE files: `/home/ubuntu/claudedata/sweep/DONE_<tag>.txt` (5m: B*, 15m: G*). Stats: `/tmp/matrix2.py` (18 ô).
