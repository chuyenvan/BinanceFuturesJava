# PRE-REG — GATE × K FRONTIER (GKF)

- Ngày: 2026-10-06. Thiết kế: MASTER (owner duyệt hướng 10-06). Thực thi: claw.
- Trạng thái: **PRE-REG PHẦN 1 (thiết kế + luật)**. Phần 2 (bảng pct sau P0.a) phải commit dưới dạng ADDENDUM-1 **trước kernel Kaggle đầu tiên**. Mọi thay đổi khác sau commit này phải ghi ADDENDUM có giờ và lý do. Mọi thứ ngoài pre-reg = "chỉ báo cáo".
- Hash commit này ghi vào RESULT. Không tune sau khi thấy số.

---

## 0. Câu hỏi

Owner nhận xét: với gate rolling hiện tại, K24 vẫn giữ chất lượng.

- **H1 (đánh đổi tĩnh, cùng số lệnh):**
  - (a) nới gate (pct thấp hơn ⇒ nhiều phút mở hơn) + siết K;
  - (b) siết gate + nới K.

  Cách nào cho Calmar22/CAGR22 tốt hơn nền K24 pct base ở **cùng n**?
- **H1n (tăng n):** ở n ≈ 1 000/năm, có điểm (K, pct) nào qua luật GO §9 A.4 so với nền (~736/năm) không?
- **H2 (K theo độ mạnh gate):** tách K_entry khỏi K_buffer. q_t vẫn tính trên top-24; hạng 25..K_entry chỉ vào khi tự vượt q_t (phút rất mạnh). Có qua GO không?

## 1. Cơ chế (sự thật đã kiểm — nguồn trong ngoặc)

- **Pass:** `r = p15 / (max(0,26787, sp/0,15·1,2876)·1,55) ≥ q_t`.
  - q_t = phân vị `SIM_GATE_ROLLING_PCT` (nền 0,999950829) của r trên **symbol-phút top-K** 90 ngày (`SIM_GATE_ROLLING_DAYS=90`), tính lại mỗi giờ, warm-up 7 ngày.
  - Coin đang giữ bị loại sau khi cap K.
  - Nguồn: `EntryGate.java`, `GateRollingRatio.java:105-108`, `GateRatioBuffer.java`, `profiles/g2_flat3.properties:104-105`.
- **p15 là market-level;** trong một phút r chỉ khác nhau qua dyn(sp). Với C3, `sp_k = 1 − pwin_(k)` tăng theo hạng ⇒ hạng thấp khó qua hơn. Pass rate theo decile sp 43,7 → 0 ×1e-5 (GATE_QUOTA_DIAG §D3, 15d3e2d5). ⇒ K là **trần**, chạm ở phút mạnh.
- **Quota:** pass ≈ ρ × luồng ứng viên, ρ không đổi qua K16/24/32 (AUDIT_CHAIN_AND_N, c733467c). Nâng K trộn 2 tác dụng:
  - (i) hạng sâu vào ở phút mạnh;
  - (ii) buffer thêm r ⇒ q_t hạ ⇒ thêm phút.

  H2 tách hai tác dụng này.
- **Sizing:** U = margin/equity, throttle = 1 − U/U_MAX (0,60), F_BASE 0,015; U ≥ U_MAX ⇒ chặn. `GATE_QUOTA_SKIP_WHEN_FULL=true` (merge 95d32a56) ở **mọi arm**.
- **Ứng viên có thể < K:** top-16 replay cho cand_per_min = 15,33 (chain_n_audit). Với K32–48, P0.a phải báo K hiệu dụng.

## 2. Bằng chứng nền (không đo lại)

| Nguồn | Số | Hàm ý |
|---|---|---|
| N700 (9a62e1a0) | A1 K24: n 732, Calmar22 1,650. A2 pct 0,99985 @K16: n 1 242, Calmar 1,339 (0,71×), UW 284, 2022 âm, % ΣPnL lệnh 0h 55% | nới gate mạnh ⇒ chất lượng sụt |
| RANKBAND_K24 (96da8f82) | ROI/lệnh hạng 1–8 / 9–16 / 17–24 = 3,42 / 3,43 / 3,47% | trong top-24, xếp hạng không phân biệt ROI |
| R50 (b7fedef4) | random 16 trong top-50: Calmar 1,05 vs 3,43 | chất lượng rơi đâu đó sau hạng 24 (chưa biết) |
| BD anatomy (7b17140a) | lệnh thứ >20 trong episode = 42% ΣPnL; lúc >30 lệnh mở = 23%, lãi nhất | đợt mạnh chịu được nhiều lệnh |
| SEEDBAND/SKIPFULL (7bd71b41, f089f37d) | K24 ON 8 seed: CAGR22 36,98 ± 1,37 | bắt buộc đa seed, ghép cặp theo seed |
| COST_TRUTH (d059cc3) | chân vào nến 1m ≤ −1%: +1,675%/chân | bắt buộc stress cost |

## 3. Nền so sánh (cost 0, đã có)

- **NỀN** = K24, pct 0,999950829, skipFull ON, profile g2_flat3 + override như vòng GATE_QUOTA_SKIPFULL. Seed gate 42/7/21 = run `gqsf-*` (`docs/result/gate_skipfull.json`). Seed 42: n 736/năm, CAGR22 36,90, Calmar22 1,662, maxDD −22,21.
- pred.bin:
  - seed 42: `/home/ubuntu/wfo_ds_x1_2021/pred.bin` (md5 5dd6bb4c);
  - seed 7: `~/claude_master/1004/gabl/ds_SEED7/pred.bin` (dataset `gate-abl-*`);
  - seed 21: `~/claude_master/1004/gsb/pred_S21/pred.bin` (dataset `gate-sb-s21`).
- Jar: dataset `sim-jar-shadow2` (code module 3a80ba91; P0 B0@K16 OFF md5 ff3ce513). Kernel: `tools/kaggle_sim.py` HEAD (NOWRITE242) + khối `pred_ds`.
- **Cổng nền:** chạy lại NỀN seed 42 qua driver mới ⇒ md5 printDone phải trùng run `gqsf` seed 42. Trượt ⇒ dừng.

## 4. Phase 0 — chuẩn bị (không chọn arm bằng PnL)

**P0.a — hiệu chuẩn iso-n bằng ĐẾM offline**
- Mở rộng `research/analysis/gate_offline.py` thêm `--topk K --pct P` (seed 42). Xuất:
  - số symbol-pass/năm, phút mở/năm;
  - K hiệu dụng = TB số ứng viên/tick sau cap;
  - % tick có < K ứng viên.
- **Cổng validate** (trước khi dùng). Pass offline lệch ≤ 2% so với log `[GATE-RATIO]`/pass của sim ở cả 3:
  - n700-a1 (K24 pct base);
  - n700-a2 (K16 pct 0,99985);
  - NỀN seed 42 (K24 ON).

  Trượt ⇒ dừng, báo MASTER.
- **Quy tắc chọn pct (cố định, chỉ ĐẾM):**
  - `pass_target(n_t) = pass_NỀN_s42 × n_t / 736`, với n_t ∈ {736, 1000}.
  - Với mỗi (K, n_t), tìm pct sao cho pass offline 2022–2025 lệch ≤ 1% pass_target (bisection trên `1 − pct`, khởi tạo `ρ0 = 4,9171e-5 × 24/K × n_t/736`).
  - Làm tròn pct tới 9 chữ số.
- **ADDENDUM-1** (commit TRƯỚC kernel đầu tiên): bảng (K, n_t, pct, pass offline, phút mở/năm, K hiệu dụng) + kết quả validate.
- Nếu K hiệu dụng < 0,9K ở K40/K48 thì vẫn chạy, nhưng ghi K hiệu dụng cạnh K danh nghĩa.

**P0.b — RANKBAND sâu (1 kernel, chỉ báo cáo)**
- Cấu hình: K48, pct iso-1000 của K48, skipFull ON, seed 42.
- Báo ROI%/lệnh, SL%, ΣPnL, size TB, n theo dải hạng S1 tại lúc vào: 1–8, 9–16, 17–24, 25–32, 33–40, 41–48 (join như RANKBAND_K24/R50). Thêm theo năm và theo tercile độ mạnh `s = r/q_t` lúc vào (chia theo ĐẾM).
- **Luật Phase 3 (cố định):** gọi R = ROI/lệnh dải 1–24.
  - ROI dải 25–32 ≥ 0,8R **và** ROI dải 33–48 ≥ 0,8R ⇒ Phase 3 chạy K_entry ∈ {32, 48}.
  - Chỉ dải 25–32 đạt ⇒ chỉ K_entry 32.
  - Dải 25–32 < 0,8R ⇒ **không chạy Phase 3**.
- P0.b **không** ảnh hưởng arm Phase 1/2.

## 5. Phase 1 — sàng lọc 1 seed (seed 42, 8 kernel)

| Đường | Arm (K, pct theo ADDENDUM-1) |
|---|---|
| iso-736 | K12, K16, K32, K40 (nền K24 có sẵn) |
| iso-1000 | K16, K24, K32, K40 |

- Mọi arm: skipFull ON; chỉ đổi `SELECTOR_RANK_TOPK` và `SIM_GATE_ROLLING_PCT`.
- **Sàng lọc (cố định):** mỗi đường xếp theo Calmar22 MTM giảm dần (hoà ⇒ CAGR22), lấy **top-2** sang Phase 2.
- **Cổng quota:** n/năm sim lệch > 15% so với n_t ⇒ ghi "lệch quota" cạnh arm, vẫn xếp hạng.

## 6. Phase 2 — xác nhận (≤ 8 kernel)

- 4 arm được chọn × seed 7 và 21.
- So ghép cặp theo seed với NỀN cùng seed (42/7/21).

## 7. Phase 3 — H2 (chỉ khi luật P0.b cho phép)

- **Code** (branch `feat/gate-buffer-topk`, KHÔNG merge trong vòng này): key `GATE_BUFFER_TOPK` (default −1 ⇒ = SELECTOR_RANK_TOPK ⇒ byte-identical).
  - Khi = 24 và `SELECTOR_RANK_TOPK = K_entry > 24`: chỉ r hạng 1–24 nạp buffer/tính quota.
  - Hạng 25..K_entry được kiểm `r ≥ q_t`, qua thì vào lệnh, không nạp buffer.
  - Áp sim + live qua cùng `EntryGate`/`GateRatioBuffer`.
  - JUnit ON/OFF, `tools/check_cfg_gateway.sh`, SLF4J.
  - P0 B0@K16 OFF md5 ff3ce513 + NỀN seed 42 OFF key trùng md5 gqsf.
- **Arm:** K_entry ∈ {32, 48} (theo luật P0.b), pct NỀN, × seed 42/7/21. ≤ 6 kernel + 1 P0.

## 8. Thước (cố định)

- **MTM ngày ghép cặp** arm vs NỀN **cùng seed gate**: block-10d, NREP 2000, seed 20260905.
- **Báo:** CAGR22, ΣPnL/ΔPnL, maxDD MTM phút, Calmar22, UW22, n/năm, phút vào/năm (riêng 2022), skipFull count, U TB/p95, K hiệu dụng.
  - Theo năm 2022–25 và quý; bản ex-2022 (CAGR23).
  - % ΣPnL top-10 ngày; % ΣPnL lệnh 0h (định nghĩa N700).
- **Stress:** chấm lại với +1,675%/chân cho mọi chân vào trong nến 1m có close/open−1 ≤ −1% (COST_TRUTH). Báo base và stress song song.
- **Inflate:** half-width × √(2 ln k), k = 8 (Phase 1) + số arm Phase 3 thực chạy (P0.b không tính vì không chấm GO).
- **Đa seed:** mean ± sd qua 3 seed, CI paired t df 2 (ghi rõ yếu), số seed Δ > 0.

## 9. Luật GO (cố định; §9 A-20261003 A.4/A.5)

- **iso-736:** GO nếu tất cả:
  - Calmar22 > NỀN ở **3/3 seed**;
  - mean ΔCAGR22 ≥ 0;
  - maxDD ≤ 40% mọi seed;
  - mean ΔCAGR23 (ex-2022) ≥ −1,0pp;
  - đạt ở **cả base lẫn stress**.
- **iso-1000 và Phase 3:** GO nếu tất cả:
  - mean ΔPnL > 0 với CI MTM inflate (gộp 3 seed) loại 0;
  - maxDD ≤ 40% mọi seed;
  - Calmar22 ≥ 0,90 × NỀN ở mọi seed;
  - ≥ 3/4 năm mean ΔROI ≥ 0;
  - đạt cả base lẫn stress.
- Không arm nào GO ⇒ **giữ NỀN** (K24 pct base — cấu hình shadow #2). Không chọn điểm tốt nhất khi nằm trong nhiễu. Nhiều arm GO ⇒ báo cả, MASTER/owner chọn.
- Win%/SL% chỉ báo cáo.

## 10. Kỳ vọng khai trước (điểm ước lượng vs NỀN, mean 3 seed)

| Arm | ΔCAGR22 (pp) | Calmar22 (×NỀN) | P(GO) |
|---|---|---|---|
| iso-736 K12 | −3 … −1 | 0,85–0,95 | < 5% |
| iso-736 K16 | −2 … 0 | 0,90–1,00 | ~5% |
| iso-736 K32 | −1 … +1 | 0,95–1,05 | ~10% |
| iso-736 K40 | −2 … +1 | 0,90–1,05 | ~10% |
| iso-1000 K16 | −2 … +1 | 0,75–0,90 | < 5% |
| iso-1000 K24 | −1 … +2 | 0,80–0,95 | ~10% |
| iso-1000 K32 | 0 … +2 | 0,85–0,95 | ~10–15% |
| iso-1000 K40 | 0 … +3 | 0,85–1,00 | ~10–15% |
| Phase 3 K_entry32 | +0,5 … +2 | 0,95–1,05 | ~15–20% |
| Phase 3 K_entry48 | 0 … +2 | 0,90–1,05 | ~10–15% |

- Kết cục khả dĩ nhất: **không arm nào GO** (MDE sau inflate ~4–5pp CAGR22).
- **Điều gì sẽ bác giả thuyết** (xét seed 42 với arm chỉ chạy Phase 1, ≥ 2/3 seed với arm Phase 2):
  - H1(a) chết nếu mọi arm iso-736 K < 24 có Calmar22 ≤ NỀN.
  - H1(b) chết nếu ROI dải 25–32 < 0,8R **hoặc** K32/K40 iso-736 có Calmar22 ≤ NỀN.
  - H2 chết nếu Phase 3 không chạy hoặc không GO.
  - Cả ba chết ⇒ "trục K × gate trên DEV đóng".

## 11. Thực thi

- **Thứ tự:**
  1. Commit pre-reg này.
  2. P0.a, validate.
  3. ADDENDUM-1 (commit).
  4. Cổng nền.
  5. P0.b.
  6. Phase 1.
  7. Sàng lọc (ghi vào RESULT nháp, commit).
  8. Phase 2.
  9. Phase 3 (nếu luật cho phép).
  10. RESULT.
- **Parity mỗi run:** jar sha; log override (`SELECTOR_RANK_TOPK`, `SIM_GATE_ROLLING_PCT`, `GATE_QUOTA_SKIP_WHEN_FULL=true`, `GATE_BUFFER_TOPK` nếu có); "md5 verified" pred; n, eq, md5 printDone. Tối đa 2 kernel song song.
- **KHÔNG:**
  - chạm 242 hay shadow;
  - Java sim trên Oracle;
  - sửa Java ngoài Phase 3;
  - dùng dữ liệu 2026 (niêm phong).
- Python logging, Java SLF4J. RAM ≤ 8G + lock `~/claude_master/1002/oracle_heavy.lock`. `df` trước mỗi bước ghi; < 500 MB ⇒ dừng.
- **Git:** fetch + kiểm fast-forward; không `pull --rebase` khi có merge commit; chỉ add file của mình.

## 12. Sản phẩm

- `research/analysis/gate_offline.py` (thêm `--topk --pct`)
- `research/analysis/gate_k_frontier_driver.py`
- `docs/audit/GATE_OFFLINE_ISON_CALIB.md`
- `docs/audit/RANKBAND_K48.md`
- `docs/result/RESULT_GATE_K_FRONTIER.md` + `gate_k_frontier.json`
- branch `feat/gate-buffer-topk` (nếu Phase 3)

**Bảng bắt buộc trong RESULT:**
1. Frontier mỗi đường (mean ± sd seed).
2. Δ vs NỀN, CI raw/inflate, base/stress.
3. Năm/quý.
4. RANKBAND sâu.
5. Verdict từng arm theo §9.
6. Lệch pre-reg.

**Chi phí:** ≤ 24 kernel, ~10–14h wall, đĩa ≤ 1 GB.

---

## ADDENDUM-1 — bảng pct sau P0.a (2026-10-06 20:34 GMT+7)

Thực thi: claw. Pre-reg gốc: commit `4e4fc975`. Driver `research/analysis/gate_k_frontier_driver.py` (commit mới); JSON `docs/audit/GATE_OFFLINE_ISON_CALIB.json`. Đếm offline seed 42 (A1). `pass_NỀN_s42 = 2653` (symbol-pass 2022–2025, K24 pct base).

### Validate bộ đếm (cổng §4 P0.a, ≤2%) — PASS

| Run | K | pct | pass offline | pass sim | lệch |
|---|---|---|---|---|---|
| n700-a1 | 24 | 0,999950829 | 3233 | 3231 | +0,062% |
| n700-a2 | 16 | 0,99985 | 5955 | 5950 | +0,084% |
| gqsf-a1 (NỀN s42) | 24 | 0,999950829 | 3226 | 3232 | −0,186% |

### pct cuối (iso-n) — 8/8 arm Phase 1 đạt ≤1%

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

- **K hiệu dụng = K** ở mọi arm (0% tick thiếu ứng viên) ⇒ K danh nghĩa luôn đủ ứng viên; không cần hạ K vì thiếu ứng viên.
- pct làm tròn 9 chữ số, dùng nguyên trong sim Phase 1.

### CỜ ĐỎ: K48 KHÔNG đạt iso-1000 (P0.b §4) — báo MASTER

- K48: pct `0,999999869` → pass offline 4446 (≈1227 lệnh/năm), **dev +23,34%**, KHÔNG đạt target 3605.
- Nguyên nhân: **sàn pass tăng theo K** — `fac = max(DYN_MIN, sp/0,15·1,2876)` kẹp nhóm `sp` nhỏ về cùng hệ số; vì p15 chung cả phút, 1 phút p15 cực trị mở gate cho **cả nhóm** cùng lúc. Nới K = thêm symbol vào nhóm = sàn cao. (Sweep pct: K24→0, K40 sàn ~737, K48 sàn ~1227 lệnh/năm.)
- ⇒ **P0.b "K48 @ pct iso-1000" bất khả thi như §4 viết.** Cần MASTER chọn: (a) chạy P0.b K48 ở sàn (~1227/năm); (b) đổi P0.b sang K40 (đạt ~974); (c) hướng khác.
- Lưu ý chấm: iso-736 K40 và iso-1000 K40 dùng pct cực đoan (0,999999884 / 0,999993736) — gate gần đóng, "đều lệnh" thoái hóa ở pct→1; các arm K≤32 dùng pct dải bình thường (0,99992–0,99998).
