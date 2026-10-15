# VZ_MASTER_1015_SUMMARY — tổng hợp kết quả cho MASTER

Lập lúc **2026-10-15 16:45 (+07)**. Branch `research/vz-e1` (worktree `~/claude_master/vz_e1_wt`) + `data/vz-lake`.

## 1. ✅ Q6 — xác nhận B4 = **NO-GO** (chạy ĐÚNG 1 lần, 14:28→14:43)
| điều kiện GO | yêu cầu | kết quả | đạt |
|---|---|---|---|
| (1) gộp 3 năm | spread net_1440 < 0 **và** mean+2,70·se < 0 | **+0,00144** · CI95 [−0,00181, +0,00464] · cận nở **+0,00583** | ❌ |
| (2) mỗi năm | spread net_1440 < 0 | 2022 **+0,00107** · 2023 **−0,00235** · 2025 **+0,00320** | ❌ |
| (3) stress gộp | < 0 | **+0,00148** | ❌ |

- n(đủ 24h): 38 049 / 36 626 / 153 973 → gộp **228 648**; mono gộp **+0,40** (2024 khám phá **−1,00**) ⇒ **không tái lập hướng** (2022 & 2025 dương).
- **md5 output `e9b6560cc292dc1bcb52425deccfc1ff`** (tự tính lại → khớp) · pre-reg `997f18f3` (có Addendum 1) · `ci_widen 2,697` (√(2 ln 38)) · commit `465eadb7` · báo cáo `docs/result/VZ_B4_CONFIRM.md`.
- ⇒ theo pre-reg: **ĐÓNG giả thuyết**; không thử chân trời/biên khác.

## 2. ✅ Queue Q1–Q6 (E1)
`Q1 DONE (997f18f3)` · `Q2 DONE` · `Q3 BLOCKED (file per-leg EXEC đã xoá)` · `Q4 DONE` · `Q5 DONE (84aa5f22)` · `Q6 DONE (NO-GO)`.

## 3. ✅ QUEUE_1015 P1–P5
| P | trạng thái | commit | số chính |
|---|---|---|---|
| P1 | DONE | `1b8455c0`, `b594c5fb` | `docs/data/KAGGLE_REQUIRED.md` — mọi `vz-*` + `bcast-2020-2021h1-p1` + `sim-ho26(-a)-bundle` + `ho4p1-code/jar-exp` + `sim-jar-ecost` + `wfo-ticker-2021..2025` **còn đủ** |
| P2 | RUNNING | `3e85f1fc`, `4ff7da1b`, `35c12e89` | root cause: endpoint raw `!forceOrder@arr` trả **0 frame** từ host Oracle ⇒ dùng endpoint **combined**; ~1h = **3 395 event**; `[low,high]` **100%** (dùng `avg_price`) |
| P3 | DONE | `47f0cbda` | cụm 17 lệnh 08/10 22:20 **KHÔNG phải lỗi khởi động** (gate **ARMED**, `q_t=0,006205`, cùng tick, không restart) |
| P4 | DONE | `7a51ae6f`, `4a9de3a1` | kernel `sim-vz-cand-2024` COMPLETE → `chuyendinh/vz-cand-2024` = `cands_2024.csv.gz` **188,8 MB / 12 247 316 dòng** |
| P5 | DONE (không deploy) | `e3168077` | KillSwitch WARN/PAUSE/STOP + UW, `8/8` + `mvn -o test` **329 test 0 fail**, parity byte-identical |

## 4. ✅ Jar + Kaggle khôi phục
`sim-jar-nsel` (b7c89f09) + `sim-jar-gqsf` (0944841c) đẩy lại từ đĩa ⇒ **ready**; jar mới `sim-jar-cand` (68057d25) cho P4 (không ghi đè `sim-jar-nsel`).

## 5. 🔄 ĐANG CHẠY (chưa xong) — đây là lý do "chưa done hết"
- **Audit A→B→C→D** (`docs/plan/VZ_AUDIT_B4_NEXT.md` @`65a540f6`): chưa ra `docs/result/VZ_AUDIT_B4.md`. ⚠️ có **2 subagent audit chạy song song** (cần chốt 1).
- **Phase 1** `vz_phase1.py 2026 2020` PID **3349** — đang `2026-03`; df **52 GB** (sàn 30 GB OK).
- **P2** collector liquidation (`liq_ws.py`).
- **Sau audit**: soạn `docs/prereg/PREREG_VZ_C1_AGE.md` → commit → **DỪNG chờ MASTER duyệt** → rồi **E2** (H-G..H-K, chỉ 2024, ≤8 biến thể/họ, H-J ≤4).

## 6. Luật MASTER 10-15 đã áp
V3 glitch-tính-trần (`e1ef9440`) · thứ tự 2021-12-trước (`bfdb5a41`) · V4=N/A ngoài vùng `CLOSES_1H` (`d4a8ac4f`) · Kaggle ≤2 kernel · không đọc 2026/2020s cho khám phá · sàn đĩa 30 GB · không deploy 242.
