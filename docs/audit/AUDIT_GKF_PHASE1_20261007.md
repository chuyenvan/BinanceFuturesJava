# AUDIT — Chấm lại GATE × K FRONTIER Phase 1 (seed 42) theo đúng thước pre-reg

- Ngày: 2026-10-07. Người chấm: agent re-score (MASTER giao). Không sim mới, không sửa Java, không sửa file của claw.
- Pre-reg: `docs/prereg/PREREG_GATE_K_FRONTIER.md` (4e4fc975 + ADDENDUM-1 36b5d136). Kết quả claw: `docs/result/GATE_K_FRONTIER_RESULT.md` + `gate_k_frontier.json` (0a3f10d0) — claw chấm Calmar **daily**, chưa MTM phút, chưa stress, chưa CI.
- Script: `research/analysis/gkf_rescore.py`. JSON: `docs/audit/AUDIT_GKF_PHASE1_20261007.json`. Cache (không push): `~/claude_master/1007/gkfscore/{mtm,bar}.json`.
- Mọi số là **1 seed (42)** ⇒ chỉ là **sàng lọc proxy**, không phải GO (§9 cần 3 seed).

## Tóm tắt

1. **Parity 15/15 PASS; cổng nền PASS**: md5 printDone `gkf-nen` = `gqsf-a1` = `ad26fd55` (n 3541, eq 146 078). Tự kiểm NỀN vs `gate_skipfull.json` ON_A1: 0 lệch (CAGR22 36,90; Calmar22 MTM 1,662; maxDD22 MTM −22,21; UW22 117).
2. **Calmar daily của claw thổi 1,2–2,3×** so với Calmar MTM phút, và **đảo thứ hạng**: `736-k40` daily 2,600 (> nền 2,363) → MTM 1,148 (0,69× nền); `1k-k16` daily 2,381 (≥ nền) → MTM 1,652 (0,994×).
3. **Luật §9 (proxy 1 seed): 0/13 arm đạt, ở cả base lẫn stress.** Không arm nào có ΔPnL > 0 ngoài CI inflate; không arm nào có ≥ 3/4 năm ΔROI ≥ 0 ở stress. ⇒ theo §9: **giữ NỀN** (K24 pct base).
4. Kết luận claw "**1k-k16 = tăng n miễn phí**" **không đứng**: ΔCAGR22 −1,11 pp [−8,36; +6,49], ΔPnL −11 799, ΔROI 2025 −9,24 pp, ΔCAGR23 −3,65 pp, chỉ 2/4 năm ΔROI ≥ 0 (stress 1/4).
5. **Sàng lọc đúng luật §5 (Calmar22 MTM)**: iso-736 → **K12, K16**; iso-1000 → **K16, K32** (claw daily sẽ chọn iso-736 K12, K40). Nhưng **lệch quota > 15%** ở 6/8 arm ⇒ so sánh không iso-n.
6. **Iso-n hỏng do bộ đếm offline đếm thừa pass ở tầng gate**, không phải float32 và không phải cap: pass sim/offline = 0,81 / 0,90 / 0,61 / 0,30 (iso-736 K12/16/32/40), 0,82 / 0,94 / 0,65 / 0,35 (iso-1000); lệnh PREDICT/pass sim = 1,000 ở mọi arm; skipFull = 0 ở mọi arm trừ 1k-k24 (975). Chi tiết §5–§6.

## Phương pháp (giữ nguyên thước các vòng trước)

- **MTM phút**: `reset_rule_score.run_mtm` (phí legacy as-is, cửa sổ 2022+ qua `feat_add_v1_score`), maxDD22/UW22 MTM phút. CAGR22 từ equity ngày (b+unP), Calmar22 = CAGR22/|maxDD22 MTM|. Chỉ số khác = `n700_driver.arm_metrics` (ΣPnL 0h = định nghĩa N700; U = Σmargin/equity, time-weighted lưới phút, 2022+).
- **Δ vs NỀN**: ΔCAGR22 = MTM ngày paired block-10d NREP 2000 seed 20260905 (`selector_ablation_driver.daily_boot`); ΔPnL = paired theo ngày đóng (`n700_driver.pnl_boot`, cùng lưới khối). Inflate √(2 ln 13) = 2,265 (8 arm Phase 1 + p0b + 4 l2 đã nhìn). Năm: ΔROI equity ngày; ex-2022 = ΔCAGR23.
- **Stress (COST_TRUTH d059cc3) — post-hoc, không có script sẵn** (vòng FLAT3_CRASHPEN phạt trong sim bằng `SIM_CRASH_ENTRY_PENALTY`): với **mọi chân** trong printDone (PREDICT/BIG_DOWN/DCA), nến quyết định = nến 1m có close = giá vào (khớp 100% ở phút start, 0,7% ở phút start−1 ⇒ dùng phút start); nếu close/open−1 ≤ −1% ⇒ giá vào ×1,01675 (unP MTM giảm từ lúc vào) và PnL −1,675%×notional; equity ngày trừ cộng dồn phạt các chân có ts < mốc Update. Nguồn 1m = `/home/ubuntu/kaggle_data_hpo` (nguồn MTM phút các vòng trước); tuple jbin = (startTime, max, min, close, open, vol) ⇒ open = tup[4] (thứ tự field Java serialization; kiểm min ≤ open, close ≤ max mọi nến). Đối chiếu: NỀN có 41,3% chân là chân sập (1 461/3 541), khớp B0 FLAT3_CRASHPEN (1 096/2 517 = 43,5%, log sim).
- Giới hạn stress: bậc 1 — không mô phỏng lại qty/TP/SL/sizing/lịch vào sau khi phạt.
- Luật áp: arm n/năm > NỀN ⇒ luật iso-1000 (c1 ΔPnL>0 ngoài CI inflate; c2 maxDD MTM ≤ 40% (toàn kỳ và 2022+); c3 Calmar22 MTM ≥ 0,90×NỀN; c4 ≥ 3/4 năm ΔROI ≥ 0); arm n ≤ NỀN ⇒ luật iso-736 (c1 Calmar22 > NỀN; c2 ΔCAGR22 ≥ 0; c3 maxDD ≤ 40%; c4 ΔCAGR23 ≥ −1,0 pp) — 1 seed nên kể cả đạt cũng chỉ là "chưa đủ seed". Đạt = đạt cả base và stress.
- `†` = ngoài Phase 1: `p0b-k48` (P0.b, chỉ báo cáo), `l2-*` (claw thêm sau khi thấy số, **ngoài pre-reg — chỉ báo cáo**).


## 0. Parity / hợp lệ

| run | md5 printDone | jar | n | eq | pct log (f32) | pass gate | skipFull | parity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gqsf-a1 | ad26fd55 | 0944841c | 3541 | 146078 | 0.99995083 | 3232 | 14 | PASS |
| nen | ad26fd55 | 20d412e8 | 3541 | 146078 | 0.99995083 | 3232 | 14 | PASS |
| 736-k12 | d0fe6e4d | 20d412e8 | 2897 | 117291 | 0.99992472 | 2604 | 0 | PASS |
| 736-k16 | 1b32fbbe | 20d412e8 | 3186 | 117609 | 0.99993777 | 2881 | 0 | PASS |
| 736-k32 | b56c628c | 20d412e8 | 2383 | 108153 | 0.99998158 | 2093 | 0 | PASS |
| 736-k40 | 4e4b0ae2 | 20d412e8 | 1250 | 73566 | 0.99999988 | 1001 | 0 | PASS |
| 1k-k16 | e62e8199 | 20d412e8 | 3819 | 131313 | 0.99992251 | 3510 | 0 | PASS |
| 1k-k24 | 359bd5e2 | 20d412e8 | 4396 | 129135 | 0.99993998 | 4083 | 975 | PASS |
| 1k-k32 | 7e8a8942 | 20d412e8 | 3197 | 121843 | 0.99997181 | 2891 | 0 | PASS |
| 1k-k40 | 912b25c2 | 20d412e8 | 1709 | 73868 | 0.99999374 | 1456 | 0 | PASS |
| p0b-k48† | b5f506db | 20d412e8 | 1435 | 74937 | 0.99999988 | 1184 | 0 | PASS |
| l2-k16† | 9219d669 | 20d412e8 | 5304 | 130310 | 0.99988002 | 4975 | 177 | PASS |
| l2-k24† | c44bc6a5 | 20d412e8 | 6707 | 140945 | 0.99989498 | 6376 | 2092 | PASS |
| l2-k24b† | a9e1559f | 20d412e8 | 7967 | 147386 | 0.99987000 | 7626 | 1626 | PASS |
| l2-k32† | f2a4503f | 20d412e8 | 7489 | 156807 | 0.99991500 | 7154 | 5341 | PASS |

## 1. Bảng chính (base, phí legacy as-is; MTM phút)

| arm | K | pct | n/năm | phút vào/năm (2022) | CAGR22 | maxDD22 MTM | Calmar22 MTM | Calmar daily (claw) | UW22 ng | ΣPnL 0h % | ΣPnL top10 ngày % | skipFull | U TB/p95 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nen | 24 | 0.999950829 | 736 | 146 (170) | 36,90 | -22,21 | 1,662 | 2,363 | 117 | 43,6 | 44,4 | 14 | 4,3/23,0 |
| 736-k12 | 12 | 0.999924707 | 607 | 167 (187) | 32,44 | -17,09 | 1,898 | 3,027 | 90 | 46,0 | 39,9 | 0 | 4,6/21,7 |
| 736-k16 | 16 | 0.999937768 | 662 | 157 (173) | 31,28 | -21,71 | 1,441 | 2,008 | 117 | 44,0 | 43,0 | 0 | 4,7/23,9 |
| 736-k32 | 32 | 0.999981560 | 466 | 73 (101) | 25,41 | -18,95 | 1,340 | 2,338 | 219 | 51,6 | 58,5 | 0 | 2,2/14,1 |
| 736-k40 | 40 | 0.999999884 | 256 | 24 (32) | 18,19 | -15,84 | 1,148 | 2,600 | 181 | 50,9 | 67,8 | 0 | 1,0/6,3 |
| 1k-k16 | 16 | 0.999922492 | 805 | 190 (211) | 35,79 | -21,66 | 1,652 | 2,381 | 113 | 43,3 | 39,8 | 0 | 5,9/26,7 |
| 1k-k24 | 24 | 0.999939977 | 921 | 181 (198) | 35,05 | -24,59 | 1,425 | 1,918 | 138 | 43,3 | 43,6 | 975 | 6,0/30,2 |
| 1k-k32 | 32 | 0.999971815 | 654 | 96 (134) | 30,27 | -19,10 | 1,585 | 2,055 | 129 | 42,0 | 51,4 | 0 | 3,4/22,4 |
| 1k-k40 | 40 | 0.999993736 | 364 | 40 (70) | 19,02 | -18,96 | 1,003 | 1,967 | 175 | 56,1 | 69,5 | 0 | 1,4/9,2 |
| p0b-k48† | 48 | 0.999999869 | 293 | 27 (33) | 18,71 | -16,97 | 1,102 | 2,408 | 181 | 51,8 | 69,9 | 0 | 1,0/6,3 |
| l2-k16† | 16 | 0.999880000 | 1133 | 292 (250) | 35,65 | -25,76 | 1,384 | 1,768 | 154 | 52,1 | 44,2 | 177 | 8,7/31,3 |
| l2-k24† | 24 | 0.999895000 | 1432 | 295 (252) | 37,83 | -26,90 | 1,407 | 1,768 | 242 | 47,1 | 44,6 | 2092 | 10,0/37,5 |
| l2-k24b† | 24 | 0.999870000 | 1706 | 368 (279) | 38,79 | -27,42 | 1,415 | 1,763 | 244 | 51,2 | 44,5 | 1626 | 11,8/39,9 |
| l2-k32† | 32 | 0.999915000 | 1602 | 270 (265) | 41,05 | -26,34 | 1,558 | 2,041 | 244 | 43,5 | 43,9 | 5341 | 10,1/40,0 |

### 1b. Stress (+1,675%/chân vào nến 1m ≤ −1%, post-hoc)

| arm | chân sập 22–25 (% mọi chân) | Σphạt 22–25 | CAGR22 S | Δ vs base | maxDD22 S | Calmar22 S | UW22 S | ΣPnL 0h % S | top10 % S |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nen | 1226 (41,3%) | 21427 | 32,53 | -4,37 | -23,77 | 1,369 | 146 | 47,9 | 50,8 |
| 736-k12 | 980 (39,6%) | 18078 | 27,78 | -4,65 | -18,69 | 1,487 | 127 | 52,3 | 47,5 |
| 736-k16 | 1076 (39,9%) | 18454 | 26,62 | -4,66 | -23,23 | 1,146 | 137 | 50,0 | 51,6 |
| 736-k32 | 873 (45,9%) | 12380 | 22,27 | -3,14 | -23,09 | 0,964 | 220 | 55,5 | 66,2 |
| 736-k40 | 497 (45,1%) | 5889 | 15,86 | -2,33 | -17,62 | 0,900 | 328 | 52,8 | 72,7 |
| 1k-k16 | 1286 (38,9%) | 23334 | 30,22 | -5,57 | -23,44 | 1,289 | 144 | 50,6 | 48,8 |
| 1k-k24 | 1468 (39,3%) | 22914 | 29,64 | -5,41 | -26,26 | 1,129 | 214 | 50,3 | 53,7 |
| 1k-k32 | 1078 (41,0%) | 14841 | 26,82 | -3,45 | -22,38 | 1,198 | 156 | 45,0 | 57,0 |
| 1k-k40 | 703 (49,0%) | 7551 | 16,11 | -2,91 | -21,74 | 0,741 | 328 | 60,7 | 80,8 |
| p0b-k48† | 558 (44,5%) | 6095 | 16,34 | -2,37 | -18,90 | 0,865 | 328 | 53,7 | 75,2 |
| l2-k16† | 1487 (32,3%) | 25741 | 29,31 | -6,34 | -27,70 | 1,058 | 223 | 64,6 | 57,2 |
| l2-k24† | 1886 (32,6%) | 29175 | 31,17 | -6,66 | -30,06 | 1,037 | 391 | 58,8 | 58,5 |
| l2-k24b† | 2094 (30,1%) | 31497 | 31,75 | -7,03 | -29,65 | 1,071 | 280 | 65,1 | 59,6 |
| l2-k32† | 2297 (35,5%) | 34273 | 33,88 | -7,17 | -29,34 | 1,155 | 252 | 53,9 | 57,5 |

## 2. Δ vs NỀN — điểm [CI95 raw] {CI inflate k=13, ×2.265}

| arm | ΔCAGR22 base (pp) | ΔPnL base | ΔCAGR22 stress | ΔPnL stress |
| --- | --- | --- | --- | --- |
| 736-k12 | -4,47 [-12,71; +3,20] {-23,14; +12,90} | -25324 [-47102; -4596] {-74649; +21623} | -4,75 [-13,66; +3,09] {-24,92; +13,01} | -21975 [-42322; -2660] {-68060; +21772} |
| 736-k16 | -5,62 [-12,05; +0,01] {-20,17; +7,14} | -26475 [-45511; -9594] {-69591; +11758} | -5,91 [-12,80; -0,01] {-21,53; +7,45} | -23501 [-41497; -7602] {-64260; +12509} |
| 736-k32 | -11,50 [-26,47; +3,24] {-45,41; +21,89} | -40061 [-73980; -9676] {-116884; +28760} | -10,27 [-25,46; +4,69] {-44,67; +23,61} | -31014 [-62220; -3074] {-101694; +32269} |
| 736-k40 | -18,71 [-37,63; -0,95] {-61,55; +21,52} | -68612 [-118242; -27363] {-181020; +24813} | -16,67 [-36,33; +1,44] {-61,20; +24,35} | -53073 [-99173; -13882] {-157487; +35693} |
| 1k-k16 | -1,11 [-8,36; +6,49] {-17,52; +16,12} | -11799 [-32832; +8984] {-59436; +35273} | -2,31 [-10,03; +5,58] {-19,80; +15,57} | -13706 [-33585; +5996] {-58732; +30917} |
| 1k-k24 | -1,86 [-7,49; +4,26] {-14,61; +12,00} | -14181 [-30692; +1173] {-51577; +20594} | -2,89 [-8,90; +3,57] {-16,50; +11,76} | -15668 [-31216; -1190] {-50882; +17124} |
| 1k-k32 | -6,64 [-15,27; +1,06] {-26,19; +10,81} | -24961 [-45856; -6528] {-72287; +16789} | -5,72 [-14,61; +2,33] {-25,86; +12,50} | -18375 [-37649; -579] {-62030; +21932} |
| 1k-k40 | -17,88 [-37,30; +1,92] {-61,87; +26,98} | -67420 [-117462; -25859] {-180761; +26713} | -16,42 [-36,28; +2,89] {-61,40; +27,33} | -53544 [-98969; -14804] {-156428; +34198} |
| p0b-k48† | -18,19 [-37,19; -0,20] {-61,23; +22,56} | -67276 [-116266; -25979] {-178236; +26258} | -16,20 [-35,62; +2,07] {-60,19; +25,19} | -51943 [-96940; -12899] {-153858; +36489} |
| l2-k16† | -1,25 [-11,92; +10,41] {-25,42; +25,17} | -13056 [-51584; +23668] {-100319; +70121} | -3,22 [-15,08; +9,82] {-30,09; +26,31} | -17369 [-55065; +18109] {-102748; +62985} |
| l2-k24† | +0,93 [-12,07; +16,23] {-28,50; +35,59} | -2857 [-42175; +36626] {-91909; +86569} | -1,36 [-15,63; +15,04] {-33,67; +35,80} | -10604 [-49102; +26566] {-97798; +73584} |
| l2-k24b† | +1,88 [-12,97; +19,67] {-31,77; +42,18} | +2348 [-42717; +48273] {-99721; +106364} | -0,78 [-16,99; +18,49] {-37,50; +42,85} | -7721 [-51403; +36124] {-106658; +91585} |
| l2-k32† | +4,14 [-8,83; +20,32] {-25,23; +40,78} | +12689 [-31283; +56261] {-86905; +111376} | +1,35 [-13,05; +19,07] {-31,26; +41,49} | -157 [-42781; +41685] {-96697; +94611} |

### 2b. ΔROI năm (pp, equity ngày) và ΔCAGR23 (ex-2022) — base / stress

| arm | ΔROI 2022 | ΔROI 2023 | ΔROI 2024 | ΔROI 2025 | ΔCAGR23 | #năm ΔROI≥0 |
| --- | --- | --- | --- | --- | --- | --- |
| 736-k12 | +7,42 / +8,19 | -12,01 / -13,44 | -10,94 / -12,17 | -6,35 / -6,06 | -9,60 / -10,36 | 1 / 1 |
| 736-k16 | +0,53 / +1,50 | -10,66 / -11,70 | -8,46 / -10,14 | -6,25 / -6,16 | -8,33 / -9,19 | 1 / 1 |
| 736-k32 | +6,85 / +8,24 | -30,21 / -28,84 | -18,80 / -18,20 | -10,14 / -8,66 | -19,16 / -18,05 | 1 / 1 |
| 736-k40 | +2,41 / +5,44 | -46,36 / -43,54 | -16,93 / -16,44 | -20,36 / -18,80 | -27,40 / -25,79 | 1 / 1 |
| 1k-k16 | +4,54 / +4,24 | +2,01 / -0,54 | -2,00 / -3,67 | -9,24 / -10,14 | -3,65 / -5,25 | 2 / 1 |
| 1k-k24 | -0,87 / -0,84 | +5,77 / +3,65 | -9,59 / -12,63 | -1,69 / -1,21 | -2,29 / -3,81 | 1 / 1 |
| 1k-k32 | -3,56 / -3,31 | -13,96 / -11,98 | -10,20 / -9,06 | -0,91 / -0,21 | -7,96 / -6,75 | 0 / 0 |
| 1k-k40 | +5,91 / +7,22 | -43,51 / -40,35 | -19,34 / -18,96 | -21,26 / -20,33 | -27,55 / -26,10 | 1 / 1 |
| p0b-k48† | +2,29 / +5,31 | -45,66 / -42,89 | -15,07 / -14,74 | -20,50 / -18,93 | -26,64 / -25,09 | 1 / 1 |
| l2-k16† | -3,16 / -4,01 | +9,47 / +6,45 | +1,53 / +0,26 | -9,10 / -12,18 | -0,33 / -2,78 | 2 / 2 |
| l2-k24† | -7,40 / -8,70 | +21,94 / +17,64 | +1,26 / -1,26 | -4,10 / -5,82 | +5,00 / +2,31 | 2 / 1 |
| l2-k24b† | -8,21 / -10,28 | +22,56 / +17,30 | -0,36 / -2,90 | +1,57 / +0,29 | +6,84 / +4,03 | 2 / 2 |
| l2-k32† | -2,98 / -5,13 | +25,82 / +20,90 | +0,81 / -2,59 | -0,03 / -1,30 | +7,50 / +4,50 | 2 / 1 |

## 3. Luật §9 (proxy 1 seed) — base | stress

| arm | luật | n/năm | Cal×NỀN base | Cal×NỀN stress | base | stress | verdict | phạm vi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 736-k12 | iso-736 | 607 | 1,142 | 1,086 | c1✓ c2✗ c3✓ c4✗ | c1✓ c2✗ c3✓ c4✗ | TRUOT proxy | Phase 1 |
| 736-k16 | iso-736 | 662 | 0,867 | 0,837 | c1✗ c2✗ c3✓ c4✗ | c1✗ c2✗ c3✓ c4✗ | TRUOT proxy | Phase 1 |
| 736-k32 | iso-736 | 466 | 0,807 | 0,705 | c1✗ c2✗ c3✓ c4✗ | c1✗ c2✗ c3✓ c4✗ | TRUOT proxy | Phase 1 |
| 736-k40 | iso-736 | 256 | 0,691 | 0,658 | c1✗ c2✗ c3✓ c4✗ | c1✗ c2✗ c3✓ c4✗ | TRUOT proxy | Phase 1 |
| 1k-k16 | iso-1000 | 805 | 0,994 | 0,942 | c1✗ c2✓ c3✓ c4✗ | c1✗ c2✓ c3✓ c4✗ | TRUOT | Phase 1 |
| 1k-k24 | iso-1000 | 921 | 0,858 | 0,825 | c1✗ c2✓ c3✗ c4✗ | c1✗ c2✓ c3✗ c4✗ | TRUOT | Phase 1 |
| 1k-k32 | iso-736 | 654 | 0,954 | 0,875 | c1✗ c2✗ c3✓ c4✗ | c1✗ c2✗ c3✓ c4✗ | TRUOT proxy | Phase 1 |
| 1k-k40 | iso-736 | 364 | 0,604 | 0,541 | c1✗ c2✗ c3✓ c4✗ | c1✗ c2✗ c3✓ c4✗ | TRUOT proxy | Phase 1 |
| p0b-k48† | iso-736 | 293 | 0,663 | 0,632 | c1✗ c2✗ c3✓ c4✗ | c1✗ c2✗ c3✓ c4✗ | TRUOT proxy | P0.b - chi bao cao (khong cham GO) |
| l2-k16† | iso-1000 | 1133 | 0,833 | 0,773 | c1✗ c2✓ c3✗ c4✗ | c1✗ c2✓ c3✗ c4✗ | TRUOT | ngoai pre-reg - chi bao cao |
| l2-k24† | iso-1000 | 1432 | 0,846 | 0,758 | c1✗ c2✓ c3✗ c4✗ | c1✗ c2✓ c3✗ c4✗ | TRUOT | ngoai pre-reg - chi bao cao |
| l2-k24b† | iso-1000 | 1706 | 0,851 | 0,783 | c1✗ c2✓ c3✗ c4✗ | c1✗ c2✓ c3✗ c4✗ | TRUOT | ngoai pre-reg - chi bao cao |
| l2-k32† | iso-1000 | 1602 | 0,938 | 0,844 | c1✗ c2✓ c3✓ c4✗ | c1✗ c2✓ c3✗ c4✗ | TRUOT | ngoai pre-reg - chi bao cao |

## 4. Sàng lọc Phase 1 (top-2 mỗi đường theo Calmar22 MTM, hoà ⇒ CAGR22)

| đường | xếp hạng base | top-2 base (luật) | top-2 stress (tham khảo) | lệch quota >15% |
| --- | --- | --- | --- | --- |
| iso-736 | 736-k12(1,898) > 736-k16(1,441) > 736-k32(1,340) > 736-k40(1,148) | 736-k12, 736-k16 | 736-k12, 736-k16 | 736-k12 -17%, 736-k32 -37%, 736-k40 -65% |
| iso-1000 | 1k-k16(1,652) > 1k-k32(1,585) > 1k-k24(1,425) > 1k-k40(1,003) | 1k-k16, 1k-k32 | 1k-k16, 1k-k32 | 1k-k16 -20%, 1k-k32 -35%, 1k-k40 -64% |

## 5. Chẩn đoán iso-n (2022–25)

| arm | pct | pct f32 | 1−pct / 1−pct_f32 (lệch) | ứng viên/tick | hạng từ đỉnh q: liên tục / f64 / f32 | pass offline | pass sim | sim/off | skipFull | lệnh PREDICT | PREDICT/pass | phút mở off | phút vào sim | pass/phút off | PREDICT/phút sim |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nen | 0.999950829 | 0.9999508262 | 4.917e-05 / 4.917e-05 (+0,01%) | 22,2 | 141,55 / 142 / 142 | 2653 | 2667 | 1,005 | 14 | 2667 | 1,000 | None | 586 | — | 4,55 |
| 736-k12 | 0.999924707 | 0.9999247193 | 7.529e-05 / 7.528e-05 (-0,02%) | 11,0 | 106,96 / 107 / 107 | 2679 | 2168 | 0,809 | 0 | 2168 | 1,000 | 832 | 668 | 3,22 | 3,25 |
| 736-k16 | 0.999937768 | 0.9999377728 | 6.223e-05 / 6.223e-05 (-0,01%) | 14,7 | 118,32 / 119 / 119 | 2646 | 2373 | 0,897 | 0 | 2373 | 1,000 | 734 | 628 | 3,60 | 3,78 |
| 736-k32 | 0.999981560 | 0.9999815822 | 1.844e-05 / 1.842e-05 (-0,12%) | 30,3 | 72,49 / 73 / 73 | 2649 | 1605 | 0,606 | 0 | 1605 | 1,000 | 578 | 293 | 4,58 | 5,48 |
| 736-k40 | 0.999999884 | 0.9999998808 | 1.160e-07 / 1.192e-07 (+2,77%) | 38,4 | 0,58 / 1 / 1 | 2669 | 809 | 0,303 | 0 | 809 | 1,000 | 271 | 96 | 9,85 | 8,43 |
| 1k-k16 | 0.999922492 | 0.9999225140 | 7.751e-05 / 7.749e-05 (-0,03%) | 14,5 | 145,26 / 146 / 146 | 3609 | 2942 | 0,815 | 0 | 2942 | 1,000 | 955 | 761 | 3,78 | 3,87 |
| 1k-k24 | 0.999939977 | 0.9999399781 | 6.002e-05 / 6.002e-05 (-0,00%) | 21,8 | 169,69 / 170 / 170 | 3607 | 3403 | 0,943 | 975 | 3403 | 1,000 | 817 | 723 | 4,41 | 4,71 |
| 1k-k32 | 0.999971815 | 0.9999718070 | 2.819e-05 / 2.819e-05 (+0,03%) | 30,0 | 109,42 / 110 / 110 | 3624 | 2342 | 0,646 | 0 | 2342 | 1,000 | 780 | 383 | 4,65 | 6,11 |
| 1k-k40 | 0.999993736 | 0.9999937415 | 6.264e-06 / 6.258e-06 (-0,09%) | 38,2 | 31,01 / 32 / 31 | 3572 | 1236 | 0,346 | 0 | 1236 | 1,000 | 344 | 160 | 10,38 | 7,72 |
| p0b-k48† | 0.999999869 | 0.9999998808 | 1.310e-07 / 1.192e-07 (-9,00%) | 46,1 | 0,78 / 1 / 1 | None | 954 | — | 0 | 954 | 1,000 | None | 107 | — | 8,92 |
| l2-k16† | 0.999880000 | 0.9998800159 | 1.200e-04 / 1.200e-04 (-0,01%) | 13,9 | 216,78 / 217 / 217 | None | 4232 | — | 177 | 4232 | 1,000 | None | 1169 | — | 3,62 |
| l2-k24† | 0.999895000 | 0.9998949766 | 1.050e-04 / 1.050e-04 (+0,02%) | 20,8 | 282,72 / 283 / 283 | None | 5427 | — | 2092 | 5427 | 1,000 | None | 1179 | — | 4,60 |
| l2-k24b† | 0.999870000 | 0.9998700023 | 1.300e-04 / 1.300e-04 (-0,00%) | 20,3 | 341,69 / 342 / 342 | None | 6502 | — | 1626 | 6502 | 1,000 | None | 1472 | — | 4,42 |
| l2-k32† | 0.999915000 | 0.9999150038 | 8.500e-05 / 8.500e-05 (-0,00%) | 27,8 | 306,42 / 307 / 307 | None | 6106 | — | 5341 | 6106 | 1,000 | None | 1081 | — | 5,65 |

## 6. Nguyên nhân iso-n hỏng (đọc bảng §5)

- **Không phải cap/U_MAX sau gate:** lệnh PREDICT 2022–25 / pass sim 2022–25 = **1,000** ở cả 14 run (mọi pass thành lệnh). Book đầy bị chặn **trước** gate và đếm ở skipFull: = 0 ở 8/13 arm (gồm mọi arm thiếu quota nặng), 975 ở 1k-k24, 177–5 341 ở l2.
- **Không phải float32 (a):** `GateRollingRatio` dùng `Float.parseFloat`, `k = floor((double)pct_f32·(m−1))`. 1−pct_f32 lệch 1−pct ≤ 0,12% ở mọi arm K ≤ 32 và 1k-k40; hạng-từ-đỉnh của q (m ≈ ứng viên/tick × 129 600) **trùng nhau f32 vs f64** ở 12/13 arm (1k-k40: 31 vs 32). Riêng pct → 1: 736-k40 (0,999999884) và p0b-k48 (0,999999869) **cùng một float32** 0,99999988 (1−pct_f32 = 1,19e-7, lệch +2,8% / −9,0%) và cùng hạng nguyên = 1 (q = r lớn thứ 2 trong 90 ngày) — ở vùng này pct không còn là núm liên tục (bước = 1 hạng ≈ 1/m ≈ 1,9e-7), nên bisection pct ở ADDENDUM-1 vô nghĩa với K40/K48; nhưng đây vẫn là hệ quả chung của offline lẫn sim (offline cũng dùng `np.float32(pct)`), không giải thích chênh offline↔sim.
- **Nguyên nhân chính = bộ đếm offline đếm THỪA pass ở tầng gate**, tăng theo K và độ chặt pct: pass sim/offline 0,81 (K12) · 0,90 (K16) · 0,61 (K32) · 0,30 (K40) ở iso-736; 0,82 · 0,94 · 0,65 · 0,35 ở iso-1000; p0b-k48 954 vs 4 446 offline (0,21). Bộ đếm chỉ được validate ở 3 điểm (K24 pct base, K16 pct 0,99985) — ngoài đó lệch 6–79%.
- **Tập trung phút (b):** phút vào sim / phút mở offline = 668/832 (K12), 628/734 (K16), 293/578 (K32), 96/271 (K40); 1k: 761/955, 723/817, 383/780, 160/344. Pass/phút offline 9,9–10,4 ở K40 (pass dồn vào ít phút cực trị — đúng cờ đỏ ADDENDUM-1).
- **[SUY LUẬN, chưa kiểm]** cơ chế chênh: sim loại coin đang giữ **sau** cap K (ứng viên/tick sim = 11,0 / 14,7 / 22,2 / 30,3 / 38,4 / 46,1 cho K12/16/24/32/40/48, tức thiếu ~1–2 so với K; ADDENDUM-1 báo K hiệu dụng = K). Trong một đợt cực trị kéo dài nhiều phút, offline đếm lại cùng symbol mỗi phút còn sim chỉ vào phút đầu (coin đã giữ bị loại) ⇒ phần đếm lặp lớn dần khi pass càng dồn (K lớn, pct chặt). 1k-k24 còn thêm skipFull 975 ứng viên không nạp r/không pass. Kiểm được bằng cách cho bộ đếm offline mặt nạ "coin đang giữ" từ printDone của chính run — chưa làm (ngoài phạm vi, không sim).

## 7. Đối chiếu "điều gì bác giả thuyết" (§10, seed 42, iso-n KHÔNG đạt nên chỉ tham khảo)

- H1(a) (nới gate + siết K, iso-736 K < 24 có Calmar22 > NỀN?): K12 1,898 > 1,662 (stress 1,487 > 1,369) ⇒ **chưa chết theo tiêu chí §10**, nhưng K12 thiếu quota −17%, ΔCAGR22 −4,47 pp, ΔCAGR23 −9,60 pp, 3/4 năm ΔROI < 0 ⇒ Calmar cao do ít lệnh/ít DD, không phải lợi nhuận.
- H1(b) (siết gate + nới K): K32 1,340 và K40 1,148 ≤ NỀN 1,662 ⇒ **chết theo §10** (vế RANKBAND P0.b không thuộc phạm vi chấm này).
- H1n (~1000/năm): arm Phase 1 gần nhất là 1k-k24 (921/năm) — Calmar 0,858× (base) / 0,825× (stress) ⇒ trượt c3; không arm Phase 1 nào đạt ≥ 1000/năm.

## 8. Rủi ro / giới hạn

- 1 seed; SEEDBAND K24 ON có sd CAGR22 ≈ 1,4 pp giữa seed — mọi Δ < ~3 pp ở đây là nhiễu seed.
- CI inflate k = 13 rất rộng (ΔCAGR22 half-width ≈ 13–45 pp, ΔPnL ≈ ±35–110k): phép thử gần như không có power; "trượt c1" phần lớn do điểm Δ âm, không chỉ do CI.
- Stress post-hoc bậc 1 (không đổi lịch vào/sizing); FLAT3_CRASHPEN cho thấy phạt trong sim làm đổi tập lệnh — số stress ở đây là xấp xỉ, nghiêng lạc quan nhẹ (không có hiệu ứng lãi kép âm của phạt).
- Iso-n hỏng (n Phase 1 lệch n_t từ −65% đến −8%): so sánh Phase 1 thực chất là so khác số lệnh, không phải đánh đổi gate×K ở cùng n như H1 đặt ra. Muốn trả lời H1 đúng cần hiệu chuẩn lại pct bằng chính sim (hoặc bộ đếm offline có mặt nạ coin đang giữ + skipFull), không phải chọn arm theo số Phase 1 này.
- `java_rc = 1` ở mọi run (kể cả gqsf-a1 đã dùng làm nền) với `ok = true`, date_last 20251230 — coi là mã thoát bình thường của harness, không phải lỗi.
- `l2-*` được thêm sau khi thấy số ⇒ bất kỳ lựa chọn nào từ l2 đều là post-hoc; l2-k32 tốt nhất trong nhóm (ΔCAGR22 +4,14 base / +1,35 stress, Calmar 0,938× / 0,844×, maxDD22 −26,3, UW22 244 ng vs 117) vẫn trượt c1/c4 (và c3 ở stress).

## 9. Lệch pre-reg ghi nhận

- k inflate = 13 theo brief chấm lại (pre-reg §8 ghi k = 8 + Phase 3); dùng 13 vì đã nhìn 13 biến thể.
- Stress áp post-hoc thay vì chạy sim có phạt (brief: không sim mới).
- Luật §9 áp proxy 1 seed (pre-reg yêu cầu 3 seed ghép cặp) — chỉ sàng lọc.
- Phân luật theo n thực (n > NỀN ⇒ iso-1000, ngược lại iso-736) theo brief; vì vậy 1k-k32 (654/năm) và 1k-k40 (364/năm) bị chấm luật iso-736.

## 10. Đối chiếu claw Phase 2a (0f8753d3, push trong lúc chấm lại)

- Claw Phase 2a dùng **maxDD MTM toàn kỳ (2021-07..2025-12)** và Calmar = CAGR/|ddMTM toàn kỳ| — vẫn **không phải Calmar22** của pre-reg §8 (CAGR22/|maxDD MTM phút 2022+|). Ví dụ NỀN claw 1,684 vs thước validate 1,662 (= `gate_skipfull.json` ON_A1); 1k-k16 claw 1,443 (0,86×) vs Calmar22 1,652 (0,994×); 736-k32 claw 1,504 vs 1,340; 1k-k24 claw 1,320 vs 1,425.
- Hệ quả: claw loại 1k-k16 vì c3 (Calmar) — theo thước đúng 1k-k16 **qua c3** nhưng **trượt c1 (ΔPnL −11 799) và c4 (2/4 năm; stress 1/4)**. Verdict cuối giống nhau (không arm nào đạt), lý do khác. Claw 2a vẫn thiếu CI, stress và luật §9 đầy đủ.
- Tôi không sửa file của claw; số trong audit này thay thế §7 của RESULT claw cho mục đích quyết định.
