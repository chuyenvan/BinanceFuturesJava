# PREREG_SHADOW2_PROMOTION — tiêu chí đưa K24 + GATE_QUOTA_SKIP_WHEN_FULL từ shadow #2 lên 242

- **Ngày:** 2026-10-05. **Trạng thái:** ĐỀ XUẤT — **chờ MASTER duyệt**. Commit TRƯỚC khi shadow #2 chạy; không sửa ngưỡng sau khi thấy số forward.
- **Đối tượng:** shadow #2 (`~/shadow_c3b`, K24 + skipFull, paper) so với shadow #1 (`~/shadow_c3`, B0 K16, paper) — cùng jar-logic (skipFull OFF ≙ byte-identical), cùng env trừ 2 key (`docs/runbooks/SHADOW2_K24_SKIPFULL_PLAN.md` §3).
- **Nguyên tắc:** forward 4–12 tuần **không đủ power** cho PnL (sim K24 vs K16: ΔCAGR22 ≈ +4 pp/năm ⇒ ~0,3 pp/4 tuần, nhỏ hơn nhiều so với nhiễu tuần). ⇒ tiêu chí là **VẬN HÀNH + PARITY CƠ CHẾ**, không có ngưỡng PnL. PnL (MTM ngày, theo tuần) chỉ báo cáo.
- **Số sim tham chiếu:** `docs/prereg/shadow2_weekly_ratio.json` (script `research/analysis/shadow2_weekly_ratio.py`, 0 sim, chỉ đọc printDone Kaggle có sẵn). Cặp cùng seed model: `gqsf-{a1,s21,s7}` (K24 ON) vs `gqsf16-{a1,s21,s7}` (K16, = OFF byte-identical); kỳ 2022-01-03…2025-12-28, 208 tuần × 3 cặp. Tự kiểm: tổng A1 K24 2944 lệnh = 736/năm, K16 2083 = 521/năm — khớp bảng C2/C0 `GATE_SKIPFULL_DETAIL_20261005.md` §4.

## Cửa sổ đánh giá

Bắt đầu khi #2 qua kiểm 60' **và** buffer gate armed ở cả hai shadow. Tối thiểu **4 tuần (28 ngày)**. Nếu tới 4 tuần mà shadow #1 có < 10 leg0 PREDICT trong cửa sổ ⇒ gia hạn từng khối 4 tuần, tối đa 12 tuần (sim: 41/156 khối 4 tuần có K16 < 10 leg0; 28/156 khối = 0 lệnh; trung vị tuần = 0 lệnh, 389/624 tuần K16 không có leg0). Quá 12 tuần vẫn < 10 ⇒ (ii) = KHÔNG KẾT LUẬN ⇒ báo MASTER, không promote.

## Tiêu chí (tất cả phải ĐẠT)

**(i) Vận hành.** Suốt cửa sổ: 0 crash (systemd `NRestarts` không tăng do lỗi; restart có chủ đích phải ghi log vận hành), 0 `OutOfMemoryError`, RSS java ≤ 4,3G; 0 ghi Aerospike 242 (banner `[NO-WRITE-242] … BI TAT` mỗi lần khởi động, và không có dòng ghi 242 nào ngoài thông báo "bo qua ghi"); shadow #1 không bị ảnh hưởng (không file chung, NRestarts #1 không tăng do #2); `[GATE] topk=24` có mặt ≥ 95% số phút #2 chạy.

**(ii) Tần suất lệnh #2/#1 trong dải sim.** Tỉ lệ cộng dồn cả cửa sổ R = (số leg0 PREDICT_SYMBOL_TRADE #2) / (số leg0 PREDICT #1). Sim, khối 4 tuần không chồng có K16 ≥ 10 leg0 (n = 115, 3 cặp):
| phân vị | p5 | p10 | p50 | p90 | p95 | min/max (mọi khối K16>0) |
| --- | --- | --- | --- | --- | --- | --- |
| R leg0 | 1,307 | 1,335 | 1,500 | 1,608 | 1,667 | 1,0 / 2,0 |
| R mọi leg (tham khảo) | 1,279 | 1,311 | 1,450 | 1,561 | 1,623 | 1,0 / 2,0 |
Tổng 4 năm theo cặp (leg0): 1,465 / 1,467 / 1,480. Theo năm (p10–p90 khối 4 tuần, leg0, mọi khối K16>0): 2022 1,31–1,67; 2023 1,39–1,60; 2024 1,31–1,57; 2025 1,30–1,67.
- **ĐẠT:** R ∈ [1,31; 1,67] (p5–p95). **XÁM:** R ∈ [1,00; 1,31) ∪ (1,67; 2,00] ⇒ gia hạn 4 tuần + điều tra (buffer gate G1 kéo R xuống — plan §4; sổ giấy #2 phân kỳ U). **TRƯỢT:** R < 1,00 hoặc R > 2,00 (ngoài mọi khối sim) ⇒ dừng, điều tra code/config.
- Dải là dung sai khai trước từ một thước duy nhất (không chọn biến thể sau khi nhìn) ⇒ không nhân inflate √(2 ln k) (k = 1).

**(iii) Sizing đúng công thức (E2/E5 PASS) trên #2.** Theo `docs/audit/LIVE_SIZING_DCA_C3LIVE_20261003.md`: E2 — budget leg = `managerBudget(equity, U) × gridLegWeightRatio(legIdx)` (leg0 @ equity 35000, U=0: **787,5**, không phải 131,25); E5 — DCA leg 1–3 tại −50/−75/−90% giá leg0, `leg_idx` ghi đúng trong `legs.csv`. Đo bằng `live_vs_sim_check.py --probe` (probe L) + đối chiếu từng leg trong cửa sổ: **100% leg** sai lệch tương đối ≤ 1e-3 so với công thức tính lại từ equity/U tại thời điểm vào. Bất kỳ leg sai ⇒ TRƯỢT.

**(iv) skipFull nhất quán điều kiện U ≥ U_MAX.** Mọi sự kiện skipFull phải xảy ra khi U = margin/equity sổ giấy #2 ≥ 0,60 (`U_MAX`), và không có tick nào U ≥ 0,60 mà ứng viên PREDICT lại vào `threshold`/PASS. Sim: skipFull/run 4 năm = 0–942 (trung bình 214, 8 seed; S777 = 0, A1/S99 = 14), dồn ở 2022 (sổ đầy mùa giảm) ⇒ kỳ vọng **0 trong phần lớn cửa sổ 4 tuần**; tiêu chí là **nhất quán**, không phải số đếm. Đếm cần log: live hiện **không có log skipFull riêng** (plan §1b, C2) ⇒ hoặc MASTER cho thêm log Java (pre-reg byte-identical OFF) trước khi chạy, hoặc đo proxy: U theo phút từ ledger/state #2 vs dòng `[GATE]` (`n_rej = n_cand` khi U ≥ 0,60; có ≥1 PASS khi U ≥ 0,60 ⇒ TRƯỢT; proxy theo phút nên loại các phút |U − 0,60| < 0,01 do giá trôi trong phút). Nếu U < 0,60 suốt cửa sổ ⇒ (iv) = "chưa quan sát", **không chặn** (i)–(iii) nhưng ghi rõ: cơ chế skipFull chưa được kiểm forward.

**(v) Real-book adapter (CHẶN CỨNG).** Trên 242, `liveBookFull()` (`DetectEntrySignal2TradeNormal.java:920-933`) và sizing đi nhánh **BudgetManager** (tài khoản thật), không phải ShadowBookC3. Chưa được promote cho tới khi adapter sổ thật hoàn tất và có kiểm chứng riêng rằng `marginRunning/balanceBasic` của BudgetManager trên 242 cùng ngữ nghĩa (margin đang mở / equity MTM) với sổ giấy + sim, kèm test. Shadow #2 đạt (i)–(iv) **không** thay thế điều kiện này.

## PnL — chỉ báo cáo, không ngưỡng
Báo theo tuần + theo ngày (MTM ngày, ghép cặp #2 − #1): ΣPnL, equity MTM, maxDD, số lệnh, win%, SL%, U trung bình/max, số phút U ≥ 0,60. Tham chiếu sim K24+ON (8 seed): CAGR22 37,0 (35,6–39,3), Calmar 1,65, maxDD −22,6, UW 116, ~740 lệnh/năm; K16: 32,8 / 1,74 / −18,9 / 94 / ~520. Lệch xấu bao nhiêu cũng **không** tự thành TRƯỢT; MASTER/owner xem xét riêng (rủi ro theo `docs/RISK_APPETITE.md` §9: maxDD K24 sâu hơn ~3,7 pp, UW dài hơn ~22 ngày; owner duyệt K24+skipFull 10-05 trên cơ sở các số này).

## Quy trình ra quyết định
1. Hết cửa sổ: agent chạy đo (i)–(iv), ghi `docs/result/RESULT_SHADOW2_PROMOTION_<ngày>.md` + json, không đổi ngưỡng.
2. Tất cả ĐẠT + (v) xong ⇒ đề xuất MASTER/owner; triển khai 242 theo runbook riêng (không thuộc prereg này).
3. Bất kỳ TRƯỢT ⇒ dừng đường promote; XÁM ⇒ gia hạn đúng 1 lần/khối 4 tuần, tối đa 12 tuần.

**Chờ MASTER duyệt.**

---

## ADDENDUM 2026-10-16 — đổi đối tượng sang 242, bỏ thước #2/#1, sửa buffer gate (khai TRƯỚC khi có số forward)

**A. Lý do.**
- Owner đã chuyển 242 sang K24 + skipFull ngày 10-16 14:57. 242 vẫn chạy shadow: `c3_shadow`, `SHADOW_NO_PUSH=true`, `SIM_F_BASE=0.015`; jar f6313f59 (pxcache).
- Cặp Oracle #2/#1 không còn dùng làm thước được, vì hai lý do:
  1. **Dữ liệu đầu vào phía Oracle lệch.** Ở 10-08 22:20, p15 trên Oracle là 3,045%, trên 242 và backtest là 1,722% (`SHADOW_PARITY_FEAT_1016.md` §6).
  2. **Buffer gate trên Oracle bị nhiễm.**
     - So K16 của c3 với buffer native của 242 theo từng phút: 10-01…10-07 khớp 100%. Từ 10-08 chỉ khớp 0–71% mỗi ngày.
     - Phút lệch nhiều nhất có r phía Oracle gấp khoảng 2 lần (10-08 22:20 và 10-10 12:04).
     - Đuôi trên của buffer (q là giá trị lớn thứ ~14) gần như toàn record lỗi. Kết quả: q của K24 c3b (đã copy sang 242 lúc 14:57) là **0,01871**, trong khi native tương đương là **0,00723**, gấp **2,59 lần**.
     - Hệ quả: ngưỡng gate thực trên 242 từ 14:57 cao gấp khoảng 2,6 lần mức sim dùng. Bằng chứng: log `[GATE-RATIO] q_t=0.018713` từ 15:01, trước switch là `q_t=0.007370`.
    - **Lưu ý đọc log:** `thr=[..]` trong dòng `[GATE]` là ngưỡng tính trên BASE (`EntryGate.threshold(MIN_MOMENTUM_15M, sp)`), KHÔNG phải ngưỡng thực q_t·f·gs, nên không dùng làm thước. `gateValue` trong `sel_dump` là sp (giá trị đưa vào factor), không phải ngưỡng.
- Tiêu chí (ii) (R #2/#1) **bị bỏ**. Kết quả vận hành của shadow Oracle chỉ còn để tham khảo.

**B. Đối tượng mới.** 242 với K24 + skipFull. Cửa sổ đánh giá bắt đầu khi đủ cả ba điều kiện:
- đã swap buffer theo mục D;
- kiểm 60 phút đạt;
- buffer armed.

Cửa sổ tối thiểu 4 tuần. Các tiêu chí (iii), (iv), (v) giữ nguyên, áp lên 242.

**(i') Vận hành 242.** Suốt cửa sổ phải đạt tất cả:
- 0 `OutOfMemoryError`; RSS java ≤ 3,6G (Xmx3g).
- Restart chỉ có hai loại: theo lịch `ThreadAutoRestartProgram`, hoặc có chủ đích và đã ghi sổ ở mục C. systemd không theo dõi PID nên không dùng `NRestarts`.
- `[GATE] topk=24` có mặt ở ≥ 95% số phút chạy.
- `selector tick total` p95 ≤ 3000 ms.
- `Update all position:44` (hoặc đúng số legacy hiện hành) có ở ≥ 99% số phút chạy.
- 0 lệnh thật.
- 0 thay đổi vị thế LEGACY do code shadow.

**(ii') Parity theo tick với sim, trên cùng dữ liệu 242.** Tính offline bằng `devexport` (`--cluster 242`, mapper ns `ticker`), ONNX `Model_Regressor_Return15M`, replay buffer causal (`GateRatioBuffer`), và `sel_dump` (selectorScore, rank, gateValue).
- P1 (p15): `|p15_live − p15_off| / |p15_off|` có median ≤ 1e-4, và ≤ 1e-3 ở ≥ 98% số phút. Phút vượt ngưỡng được liệt kê kèm breadth.
- P2 (lật gate):
  - Ca lật nặng: một cặp (phút, ứng viên) mà live và offline quyết khác nhau, đồng thời `|p15 − thr| / thr > 1%`. **Phải bằng 0.** Có bất kỳ ca nào ⇒ TRƯỢT, điều tra.
  - Ca lật biên (≤ 1%): chỉ báo cáo.
- P3 (q_t): `q_t` theo giờ lấy từ log live `[GATE-RATIO] q_t=`, so với q replay causal (`GateRatioBuffer`) từ file buffer: sai lệch tương đối ≤ 1e-6 ở mọi giờ. Ngưỡng thực của từng ứng viên = q_t·max(DYN_MIN, sp/0,15·1,2876)·gs, với sp = `gateValue` trong sel_dump và gs = 1,55. P2 dùng ngưỡng thực này.
- PnL vẫn chỉ báo cáo, không có ngưỡng. Thước so là sim K24 + ON (mục "PnL" ở trên).

**C. Sổ vận hành 242 (10-16).**
- Khoảng 14:57: đổi env sang `SELECTOR_RANK_TOPK=24` và `GATE_QUOTA_SKIP_WHEN_FULL=true`. Buffer copy từ c3b; buffer K16 sao lưu thành `run/gate_ratio_live.bin.bak_k16_20261016_1457`.
- 15:36:02 → 16:03:25: **downtime 27 phút** khi swap jar 0c2f4d72 → f6313f59. Nguyên nhân: alias `cp -i` chặn ghi đè sau khi đã stop. Luật mới: dùng `\cp -f`, và chạy kiểm tra trước khi stop.
- 16:18:50 → 16:18:53: restart để đổi heap `-Xms5g -Xmx5g` → `-Xms1g -Xmx3g`. Lý do: RAM available chỉ còn 81 MB. Tick đầu sau restart mất 22,6 s.
- Chờ thực hiện: swap buffer (mục D).

**D. Dựng lại buffer K24 native cho 242.** Phương pháp khai trước khi có số forward, không xét PnL.
- Nguồn dùng: K16 native 242 (`bak_k16`, 10-01 13:00 → 10-16 13:23, 333.856 record).
- Lấp gap 13:23 → 14:56 từ `sel_dump` hạng 1..16: r = κ·p15/gateValue, κ = 0,075159. κ khớp đúng hằng số trên 121 phút chồng (p5 = p95), đúng bằng SCORE_BASE/(DYN_MULT·gs) = 0,15/(1,2876·1,55), nên khớp công thức r = p15/(f·gs) với gateValue = sp.
- Mỗi phút thêm 8 record tổng hợp cho hạng 17..24: r = r₁₆·ρₖ.
  - ρ đo trên 51 phút K24 native sau 14:57: ρ₁₇..₂₄ = 0,995 0,988 0,982 0,975 0,971 0,962 0,958 0,953.
  - Trong mỗi phút, r giảm dần theo hạng: `max r(17..24)/r₁₆` = 1,000 trên 51 phút.
  - Vì vậy record tổng hợp không vào được đuôi trên. Chúng chỉ đổi số lượng m, đúng như hạng 17..24 thật.
- Ghép thêm K24 native từ 14:57 (record index ≥ 258.696 của file live).
- Bỏ toàn bộ record có gốc Oracle.
- Mốc bắt đầu chọn **10-01**, tức toàn bộ phần native hiện có, gần với cửa sổ 90 ngày của sim. Phương án đối chứng bắt đầu 10-08 cho q 0,00745; phương án này không được chọn và chỉ ghi lại để tham khảo.
- Kết quả: q = 0,007228, n = 504.264 (`hyb_base.bin` md5 a11af646…).
- Công cụ `GrrFix` (md5 6bbacdb4…, chỉ dùng một lần, không thuộc app) ghi file bằng chính `GateRatioPersist.writeFresh`. Đã tự kiểm: Java và Python đọc ra cùng q; skip sai ⇒ tool ném lỗi.
- Script nằm ở `research/parity_1016/grr/`.
- Sai khác so với sim cần khai rõ:
  1. Tập held-symbol của live (gồm 44 LEGACY) bị loại khỏi top-K. Sim không có LEGACY.
  2. Hạng 17..24 trước 14:57 là record tổng hợp.
  3. Gap 94 phút được lấp qua κ.
