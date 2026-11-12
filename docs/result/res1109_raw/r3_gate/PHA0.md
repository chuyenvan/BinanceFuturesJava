# R3 — Gate "lưới / công thức" thay cho so ngưỡng đơn điệu từng phút — PHA 0 (khảo sát + thiết kế, CHƯA chạy thí nghiệm)

Ngày 2026-11-09. Agent Opus (R3). Trạng thái: ĐỀ XUẤT cho MASTER, CHƯA pre-register, CHƯA đổi code/live. Ứng viên v1.3 (sau D ~11-26), không chạm v1.2.
Nguồn kiểm: code `~/claude_master/v12/c3live` HEAD a48cc56c; `vz_e1_wt` (prereg 6d92cdba, result c9d7deb0, 2fa10cc3); `~/claude_master/gsmart/*`;
log `~/kaggle_sim/out/nt-x14-s42`; probe nhẹ `r3_probe.py` → `r3_probe.json` (RSS 0,32 GB, 1,7 s, flock oracle_heavy, chỉ đọc artefact có sẵn, KHÔNG PnL mới).

## 1. Gate hiện tại (B0) — định nghĩa chính xác

**Ô ứng viên (cell)** = (phút t, coin c) với c thuộc top-K=24 theo `sp` TĂNG (selector S1, `selectCands`, `SimulatorMarketLevelTicker1MStopLoss.java:433-437`), coin đang giữ bị loại TRƯỚC gate (`isSymbolRunning`, :457-460), có p15 ở phút đó. p15 = dự báo XGB MARKET-LEVEL (1 số/phút, chung mọi coin).

**r** (`GateRollingRatio.java:115-118` sim; `LiveGateRollingRatio.java:368-371` live; công thức y hệt):
`fac = max(DYN_MIN, sp/SCORE_BASE·DYN_MULT)`, DYN_MIN=0,26787, SCORE_BASE=0,15, DYN_MULT=1,2876 (`EntryGate.java:44-48`), `gs = GATE_DYN_SCALE = 1,55` (profile); `r = p15/(fac·gs)` float32.
Kiểm A1 (2 631 ô pass DEV): fac ∈ [0,425; 4,60], **0 % ô pass chạm sàn DYN_MIN** ⇒ thực tế r ∝ p15/sp.

**Buffer + quantile** (`GateRatioBuffer.java` — DÙNG CHUNG sim/live):
- `addAndQuery` :42-51: đổi giờ ⇒ tính q MỘT lần ở truy vấn đầu giờ, rồi mới nạp (ts, r) ⇒ q_h CAUSAL (chỉ r có ts < h).
- `computeQ` :72-82: cửa sổ [h−90d, h); m = số bản ghi; warm-up (<7d hoặc m=0) ⇒ fallback 0,008; `k = min(m−1, max(0, floor((double)pct·(m−1))))`, q = phần tử nhỏ thứ k (quickselect :85-115).
- pct đọc bằng `Float.parseFloat` (sim `GateRollingRatio.java:75`, live `LiveGateRollingRatio.java:93`) ⇒ pct_f32 = 0,99995082617 (1−pct = 4,91738e-5 thay vì 4,91710e-5).
- m ≈ 2,9 triệu ô/90 ngày (sim A1 seen ~2,9 M/quý) ⇒ q_h ≈ ô lớn thứ ~143 trong 90 ngày (gate_offline jmax 148–149). **Gate B0 đã là một quota theo SỐ ô (~143 ô/90d)**, đánh giá theo giờ.

**So ngưỡng** (`AIRejectFilter.java:114-121`, `EntryGate.java:184-198`): thr = q·fac·gs (float32), PASS ⇔ `!(p15 < thr)` (`AIRejectFilter.evaluate` :187+, live fail-closed NaN). skipFull (`AIRejectFilter.java:105-108`): sổ đầy (U ≥ U_MAX) ⇒ REJECT, KHÔNG nạp r, không notePass.

**Đếm**: sim `noteCandidate/notePass` → log `GATE-RATIO on … seen/pass` theo quý (`GateRollingRatio.java:93-109,187-196`). Live dòng `[GATE] … n_cand n_rej n_pass n_skipfull u` (`DetectEntrySignal2TradeNormal.java:628-645`, `LiveBookU.java:25-27,63-73`):
`n_cand` = số ứng viên PREDICT tới gate trong tick (sau loại giữ/LEGACY/A1); `n_rej` = REJECT do gate (gồm skipFull); `n_pass = n_cand − n_rej`; `n_skipfull` = REJECT vì sổ đầy; `u` = margin/equity sổ c3 ở lần gọi liveBookFull cuối tick ("-" nếu không tính được).
Offline: `gate_offline.py` `build` :191-210 (valid = ô hợp lệ), `run_g2` :283-308 (P = pass, r, qm), docstring :1-20 khai xấp xỉ (held từ printDone, không ticker stale, tie sp).

**Cấu hình B0 xác nhận** (`nt-x14-s42` overrides): ratio, DAYS 90, PCT 0,999950829, K24, GATE_QUOTA_SKIP_WHEN_FULL=true. Pass sim theo quý DEV 2022–25: 36 (2025Q2) … 297 (2025Q4); tổng 2 667.

### Cấu trúc pass (r3_probe.json, đo từ artefact GATE_SMART p0a_legs, 8 seed, chỉ đếm)
- A1: 2 631 ô pass trên 576 phút ⇒ 4,6 ô/phút (p90 14); 121 đợt; trung vị 22 ô/đợt. 8 seed tương tự (513–590 phút).
- Khoảng cách giữa 2 phút pass liên tiếp: ≤1′ 17 %, ≤5′ 37 %, ≤15′ 52 %, ≤60′ 66 % ⇒ pass dồn cụm mạnh.
- r/q của ô pass: trung vị 1,15; ≥1,25 34 %; ≥1,5 19 %; ≥2 8,9 %.
- p15 A1 DEV: autocorr lag1 0,955 / 5′ 0,909 / 15′ 0,837; top-0,1 % phút: độ dài chuỗi trung vị 2′, p90 8′; Jaccard(top-0,1 % p15, top-0,1 % mean5) 0,63, (…mean15) 0,49 ⇒ đổi khung THAY ĐỔI THẬT tập phút cực trị (không tầm thường).

## 2. GATE_SMART (6d92cdba) — đã làm gì, khác R3 ở đâu
- Pha 0a (c9d7deb0; 20 603 leg, 149 cụm): S1 FALSE (r/q [1;1,1) 26,5 CI[15;38]; top−low +10 CI[−22;44]); S2 FALSE (ALT_EW cao−thấp −34 CI[−89;38]); S3 FALSE (60–90d − <7d −11 CI[−26;1,1]); S5 FALSE (GATE_STAB).
  PnL/leg theo r/q KHÔNG đơn điệu: 26,5 / 34,4 / 40,0 / 29,6 / 36,6 (đã thấy ⇒ khai HARKing).
- S4 (near-miss 0,8 ≤ r/q < 1 vs pass [1;1,1), fwd return 24/72h ròng 0,2 %): ô đã xuất (`gsmart/s4_cells.parquet`: near 18 981 / pass_low 3 273), kernel `s4k.py` + `s4push.py` viết xong, **CHƯA push** (không thấy output Kaggle) ⇒ treo.
- Biến thể Pha 1 GATE_SMART (EWQ, VOLN, SEP, BX24) đều đổi **ước lượng ngưỡng q**; không cái nào chạy (không signature).
- Liên quan khác đã đóng/treo: QUOTA_DIAG D4 (quota theo phút p15 / phút r_max / 365d — không đạt, chỉ đếm); GATE_STAB V1 BX24 / V2 CAP5 (trần bước q 1,05/giờ) / V3 W180 — prereg 29beac99, chưa chạy; ENTRY_CONFIRM FAIL (mọi độ trễ xác nhận giá mất ~28k/seed: edge nằm ở ĐÚNG phút cực trị); BURST_COOLDOWN R1 Calmar 1,30 < 1,65; GATE_VZ NO-GO; GKF/K32/N_DEEP: thêm lệnh ⇒ lệnh mới kém + chen chỗ.
- **R3 khác ở chỗ**: không đổi q mà đổi (i) THỐNG KÊ quyết định (gộp p15 nhiều khung), (ii) TRẠNG THÁI quyết định trong một đợt (hysteresis trên phút, không phải trên q như CAP5), (iii) ÁNH XẠ hành động theo mức (size theo tầng) — chỉ khi S4 đạt.

## 3. Họ biến thể đề xuất (≤4 arm + đối chứng; tham số CỐ ĐỊNH, không lưới tham số)
Chung: mọi buffer nạp đúng tập ô B0 nạp (hợp lệ, không giữ, không skipFull); q mỗi giờ causal như `computeQ`; pct float32; khung trượt dùng p15 của các phút ≤ t (đã có lúc quyết định) ⇒ không lookahead.
Khung w: `s_w(t) = mean(p15[t−w+1..t])` cộng float32 theo thứ tự thời gian; thiếu BẤT KỲ phút nào ⇒ khung w KHÔNG khả dụng ở t (không nạp, không pass theo khung đó) — fail-closed, giống nhau sim/live. `r_w = s_w/(fac·gs)`; mỗi w một buffer riêng, `q_w` với `pct_w = 1 − c·(1 − pct_f32)`.
Cân bằng: **iso-count** (luật GATE_SMART §3: c hoặc pct hiệu chỉnh THEO TỪNG SEED bằng tìm nhị phân trên SỐ ô pass offline DEV 2022–25 = số pass B0 cùng seed ±1 %, cấm mở pnl/MTM; ghi `iso_r3.json` + commit trước push; sau sim lệch >3 % ⇒ ghi, không hiệu chỉnh lại).

| Arm | Định nghĩa | Tham số cố định (lý do) | Cân bằng |
|---|---|---|---|
| R3-0 | B0 (nt-x14-s*, tái dùng, không chạy lại) | — | — |
| R3-A MTF-OR | pass ⇔ ∃w∈{1,15}: !(s_w < q_w·fac·gs) | w=15 = chân trời nhãn p15; Jaccard top mean15 vs p15 0,49 ⇒ khác biệt đủ lớn | iso-count trên c (c<1) |
| R3-B MTF-AND | pass ⇔ r_1 ≥ q_1 VÀ r_5 ≥ q_5 | w=5 (trễ ít hơn 15; ENTRY_CONFIRM ⇒ prior ÂM, giữ để kiểm "lọc nhiễu spike 1 phút") | iso-count trên c (c>1) |
| R3-C LATCH | trạng thái mở thị trường khi có ô pass theo B0; trong T=15′ sau phút pass gần nhất, ô pass nếu r ≥ (1−h)·q; h=0,10 | T=15 (chân trời p15; 52 % khoảng cách pass ≤15′); h=0,10 (= bề rộng bucket [1;1,1)) | iso-count trên pct (tăng) |
| R3-D TIER-DOWN (CÓ ĐIỀU KIỆN) | tầng 0: r ≥ q size ×1; tầng −1: 0,85·q ≤ r < q size ×0,5 | chỉ chạy nếu GATE_SMART S4 = TRUE; 0,85 nằm trong vùng near-miss S4 | **iso-risk**: Σ(size·ô) = số pass B0 ±1 % (tăng pct) |

Loại (lý do đã kiểm): (b↑) size tăng theo độ sâu — S1 FALSE, PnL/leg không đơn điệu, ISO_RISK/B15: size là đòn bẩy tuyến tính, HO không confirm. (d) ngưỡng theo regime vol/BTC — S2 FALSE, GATE_VZ NO-GO, V-b không kích hoạt; 2022 là 1 regime (N_eff≈1). (e) quota theo số pass — B0 đã là quota số ô; QUOTA_DIAG D4 không đạt; BURST_COOLDOWN thua; nếu owner muốn hướng này ⇒ chạy GATE_STAB V2 CAP5 đã prereg thay vì arm mới.

## 4. Thiết kế đánh giá
**Pha 0c — sàng lọc (pre-register TRƯỚC, rẻ, không sim):**
- P1 Oracle (đếm): hiệu chỉnh iso-count/iso-risk từng seed; báo Jaccard ô pass arm vs B0, |thêm|, |bớt|, phân bổ năm. Jaccard ≥ 0,90 ⇒ DỪNG arm (hiệu ứng < MDE — suy đoán dựa §5 GATE_SMART). Lệch số pass năm > ±25 % ⇒ ghi cờ.
- P2 Kaggle 1 kernel (mở rộng `s4k.py`): fwd return 24h/72h ròng 0,2 % từ close phút sau, cho ô THÊM (arm\B0) và BỚT (B0\arm), + S4 GATE_SMART cùng kernel. Bootstrap cụm theo ngày-đợt, 2 000 lần, gộp 8 seed. Arm qua sàng ⇔ mean(THÊM) − mean(BỚT) có CI90 > 0 ở 72h. (Fwd return ≠ PnL leg: không exit/DCA — chỉ là sàng.)
**Pha 1 — sim (chỉ arm qua sàng):** 8 seed gate 42/7/13/21/99/123/777/2024, cấu hình B0 (K24+skipFull+X14, trailing B0), một run phủ DEV + HO.
- DEV = 2022-01-01..2025-12-31 (+07), 2021H2 warm-up; HO = 2026 W9 như B15_V11 (6cf67a58), niêm phong cho tới khi DEV xong.
- Metric: CAGR22, maxDD MTM (`gvz_mtm.py`, missing = 0), Calmar, UW dài nhất, lệnh/năm, lệnh 2022, số pass sim vs offline, crowd-out.
- **Chỉ tiêu chính**: ΔCalmar MTM DEV ghép cặp. Cổng GO (giống GATE_SMART §4 để so được): Holm trên arm THỰC chạy (≤4, α=0,05); CI t ghép cặp ở mức Holm không chứa 0 VÀ ≥7/8 seed cùng dấu; maxDD median không sâu hơn >2 pp, seed tệ nhất >3 pp ⇒ trượt; HO: mean ΔROI cùng dấu, không seed nào DD sâu hơn >2 pp, ΔCalmar ≥0 ≥5/8; crowd-out ΣPnL leg chung ≥0,98×B0; parity khả thi (§5).
- MDE: sd Δ ghép cặp 1–2,4 pp CAGR22 ⇒ với Holm m=3, df=7: MDE80 ≈ 1,4·sd ≈ 1,4–3,4 pp. Calmar: sd seed 0,25 (SEEDBAND); sd Δ ghép cặp Calmar chưa đo (suy đoán 0,1–0,2 ⇒ MDE ≈ 0,15–0,3).
- DSR: báo (phụ, không làm cổng) Sharpe ngày deflated với N_trials = mọi biến thể gate đã sim từ 2026-09 (ước tính ≥25 — đếm chính xác khi prereg).
**Compute (ước):** P1 Oracle: build+run_g2 RSS ~3,2 GB (vượt trần 2 GB Pha 0 ⇒ thuộc Pha 0c, flock), ~10–30 s/lần × ≤40 vòng × 3 arm × 8 seed, tái dùng cây khi chỉ đổi pct ⇒ <1–2 h. P2: 1 kernel 2–4 h. Pha 1: ≤3 arm × 8 run × ~42′ (nt-x14-s42 2 505 s) = 16,8 slot-h ⇒ ~8,5 h wall 2 kernel; MTM 1 kernel ~2 h. Code Java: tổng quát hoá `GateRatioBuffer` đa buffer + key OFF byte-identical + test (1–2 phiên Opus); jar ~100 MB (đĩa Oracle ~24 GB trống 11-09). Ưu tiên Kaggle sau seed gate / NUP4, không đặt cờ kaggle_priority.

## 5. Rủi ro
- **Overfit lưới**: owner hỏi "lưới" — KHÔNG quét w/h/T/tầng; mỗi arm 1 bộ tham số ghi trước; đổi ⇒ addendum có hash trước khi chạy. 4 arm + nhiều hướng gate trước ⇒ thiên lệch chọn lọc; Holm + HO + DSR. Bảng PnL theo r/q, burst, hạng ĐÃ THẤY (GATE_SMART p0a) ⇒ khai §0 HARKing.
- **Thiếu sức thống kê**: ~121 đợt/seed/4 năm; arm iso-count đổi ít ô ⇒ khả năng cao ĐÓNG (prior như GATE_SMART).
- **Iso-count lệch**: offline đếm thừa pass so sim (GKF: tỉ lệ 0,21–0,94; G2off 2022 204 phút vs sim 141) vì U_MAX/skipFull không mô hình ⇒ arm đổi phân bố thời gian sẽ lệch số lệnh thật; kiểm sau sim (>3 % ghi).
- **Lệch live/sim**: (1) pct float32 (ADD17: harness phải `np.float32` — k lệch 1 bậc ~1 lần/200 h); MỖI pct_w mới phải float32 ở sim, live, harness, gate_offline. (2) khung trượt cần p15 liên tục: sim A1 DEV liên tục 100 %, live có restart/hở phút ⇒ luật fail-closed phải giống hệt, nếu không lệch hệ thống. (3) LATCH có trạng thái qua phút ⇒ phải persist qua restart. (4) live đang có lệch buffer (LEGACY đếm hạng + nạp r, TF/INDEX, coin giấy) — mỗi buffer mới nhân bản các luật loại đó.
- **Parity/vận hành**: mỗi buffer ~2,9 M bản ghi × 12 B ≈ 35 MB + scratch ~12 MB; MTF-OR/AND thêm 1 buffer ≈ +47 MB (sát trần +50 MB của GATE_SMART), 242 MemAvail ~2,1 GB. Seed buffer (gst1030) phải dựng lại cho từng khung, nếu không warm-up 90 ngày. Đổi gate = đổi logic ⇒ reset cửa sổ shadow/parity (prereg parity dry ADD4 V-OVL phải mở rộng cho q_w). Không đụng v1.2 trước D.

## 6. Đề nghị cho MASTER
1. Push kernel S4 GATE_SMART (đã viết) — rẻ, đóng S4 và quyết R3-D.
2. Nếu duyệt R3: viết PREREG_R3_GATE (§3–§5 trên) → Pha 0c P1 (Oracle) → P2 (gộp với S4 nếu chưa chạy) → chỉ arm qua sàng mới sang sim.
3. Kỳ vọng thẳng: prior ĐÓNG cao; giá trị chính của R3 là trả lời owner bằng bằng chứng rẻ ở Pha 0c trước khi tốn ~10 h Kaggle.

## Ph? l?c ? S4 GATE_SMART ?? push (MASTER duy?t 11-09, ??ng prereg 6d92cdba ?2.3, kh?ng arm R3)
Kernel `chuyendinh/gsm-s4-fwd` push 2026-11-09T15:20:01Z; code = `research/gate_smart/s4k.py` commit 2fa10cc3 (blob ebbd5b99, sha256 3081a3be); input dataset `chuyendinh/gsm-s4-cells` (s4_cells.parquet sha256 efe56688, near 18 981 / pass_low 3 273) + vz-kline1m-2022..2026; output `s4_fwd.parquet`, `s4_meta.json`; kh?ng jar, kh?ng internet. Fetch: `python3 ~/claude_master/gsmart/s4push.py fetch`. Ph? 0,2 % v? bootstrap (2 000, c?m ng?y-??t, seed RNG c? ??nh) ?p ? b??c ch?m, ch?a trong kernel.
- 2026-11-10: version đầu kẹt `queued` ~12 h (không kernel nào khác chạy, không failureMessage, chưa có output). MASTER duyệt phương án 2: push lại version mới (lần push thứ 2) lúc 2026-11-10T03:32:28Z, CÙNG code s4k.py (blob ebbd5b99) và CÙNG input; prereg không đổi; version đầu chưa từng chạy nên chưa ai thấy kết quả. Trạng thái 30 s sau push: `running` ⇒ KHÔNG cần phương án 3 (thu nhỏ input).
- 2026-11-10 12:15 +07: S4 chấm xong = FALSE (near − pass_low 72h −1,00 pp CI90 [−2,75; +0,70]) ⇒ GATE_SMART ĐÓNG; R3-D/G5 loại. Nháp prereg họ R3: `vz_e1_wt/docs/prereg/PREREG_R3_GATE_FAMILY.md` (chưa commit).
- 2026-11-10: prereg R3 commit b901016e; P1 (commit kết quả xem git log): G1/G2/G4 LOẠI (quota 1,70/1,64/1,37), G3 QUA (quota 1,05, Jaccard 0,34) ⇒ Pha 1 chỉ G3, chờ MASTER.
- 2026-11-10 13:42 +07: Pha 1 G3 bắt đầu. Code r3_wt 12f3b1b6 (nhánh feat/r3-gate-mtf từ 3a855460 = code n4f-b0; 277 test, 0 fail), jar STUB sha256 9f240109 (sec check ×2 OK), dataset sim-jar-r3g3. Kernel đầu: sim-r3g0-a1 (G0 = B0 trên jar R3, kiểm byte-identical n4f-b0-a1). Thứ tự tiếp: G3 s42/7/21/99 → futility → 13/123/777/2024 → MTM; 1 slot. Orchestrator: orch/r3_orch.py + r3_push.py.
- 2026-11-11 16:00 +07: G3 MTF-OR DỪNG (futility 2/4), R3b B2 MEAN60 DỪNG (4/4), B1 LOẠI quota. Jar AS-FILE d10bdbae/26581b54 PASS byte-identical (không cần cổng 3222). Commit kết quả xem R3_FUTILITY.md.
