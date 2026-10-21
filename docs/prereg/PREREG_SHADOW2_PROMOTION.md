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

**C+ (sổ vận hành, tiếp).**
- 17:21–17:22: owner swap buffer, thời gian dừng khoảng 3 s + warm-up.
  - Dry-run và merge đều cho q = 0,007228.
  - Load lại: n = 505.776, firstTs 20261001 13:00, trạng thái armed.
  - Backup: `run/gate_ratio_live.bin.bak_oracle_20261016_1721`.
- 18:01: log `[GATE-RATIO] q_t=0.007228 buffer=506688 eval=912 pass=0`, đúng giá trị dự kiến.
  - Tick: p50 0,61 s, p95 1,19 s. Riêng tick đầu sau restart mất 23,2 s.
  - RSS 2,68G, legacy 44, 0 ERROR, 0 lệnh thật.
- ⇒ **Cửa sổ đánh giá (B) bắt đầu lúc 2026-10-16 18:01 (+07).**
- Đã đề xuất cho owner (chưa thực hiện):
  - restart có chủ đích để bật `-Xlog:gc`;
  - tắt shadow c3b trên Oracle.
- Classifier chặn tôi chạy hai việc trên, nên owner sẽ tự chạy; khi xong cần ghi vào sổ này.
- 10-16 ~19:5x: owner tắt shadow c3b và c3b-redis trên Oracle (stop + disable). Trạng thái `failed` là do app thoát với mã khác 0 khi nhận SIGTERM. Shadow c3 vẫn chạy để tham khảo.
- 10-16 20:00:01 → 20:00:05: restart có chủ đích để bật `-Xlog:gc` trên 242 (backup `bin/start.sh.bak_gclog_20261016_2000`).
  - Sau restart: buffer 509.544 bản ghi, armed; tick đầu 22,6 s (warm-up), sau đó 0,8 s; legacy 44.
  - Lần chạy lặp lại của owner dừng ở bước kiểm (grep = 0), không thực hiện restart thứ hai.
  - Tính vào cửa sổ đánh giá như một restart có chủ đích, đã ghi sổ.
- 10-17 14:51:18: restart có chủ đích (owner) để khôi phục `JAVA_TOOL_OPTIONS` (`-Xms1g -Xmx3g` + `-Xlog:gc`). Lý do: lần restart
  theo lịch 10-17 08:00:32 chạy với heap mặc định 1956M và không có gc log (SHADOW_AUDIT_1020). Ghi bổ sung 10-20 (trước đây thiếu trong sổ).
- 10-20 20:33:04 (+07): deploy v11b do owner chạy. Process cũ log tick cuối 20:32:06 (phút 20:31), phút 20:32 không có tick.
  Process mới PID 6547 start 20:33:04, tick đầu 20:34:07 (phút 20:33, 28,5 s warm-up).
  - Jar `dc839568` → `d7824f6d` (nhánh `v1.1/collector-settle` `66cb6196`). Backup: `target/binance-java-sdk-1.2.4.jar.bak_v10_dc839568_20261020`
    (md5 dc839568 đã kiểm) và `conf/env.sh.bak_v10_20261020`.
  - env.sh thêm đúng 6 dòng: `LIVE_FEAT_INPUT=snapshot`, `LIVE_FEAT_MD=inline`, `LIVE_MD_DIED_SYMBOLS=BTCDOM,USDC`, `LIVE_MD_SOURCE=inline`,
    `LIVE_RANK_TIEBREAK=symbol`, `LIVE_FUNDING_REFRESH_HOURLY=1`. `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true` và `JAVA_TOOL_OPTIONS`
    (MaxHeap 3G, gc.log) không đổi. LEGACY 44, sổ giấy open=5 realized 112,18 không đổi.
  - Lý do: PARITY_1020 P1 TRƯỢT; v1.1 sửa đường input feature live = backtest (docs/plan/V11_COLLECTOR_SETTLE.md §1–§6).
  - **Cửa sổ đánh giá (B) cũ, bắt đầu 10-16 18:01, KẾT THÚC tại 10-20 20:33:04.**
  - Từ thời điểm này là giai đoạn kiểm parity v1.1. Thời điểm bắt đầu cửa sổ chính thức chờ owner chốt gói v1.1 (có/không TS_MKT_EXT).
  - Tự-restart 12h kế tiếp dự kiến khoảng 10-21 08:33–08:35 (ngoài 00:50–01:20 / 12:50–13:20).
- 10-21 05:55:29 (+07, PID 26221, log `MainClass` 05:55:31.018): owner restart v_t_m với env +`export LIVE_TS_MKT_EXT=1`
  (backup `target/…jar.bak_v11b_d7824f6d_20261021` md5 d7824f6d, `conf/env.sh.bak_v11b_20261021`). **Jar KHÔNG đổi**: vẫn d7824f6d
  (không có `target/*v11c*` trên 242, bước scp chưa chạy) ⇒ hành vi = v11b, TS_MKT_EXT chưa chạy. LEGACY 44, sổ giấy open=4 realized 88,09
  (10-20 22:21 time-stop SUSDT −24,09), 0 ERROR. Restart có chủ đích, ghi sổ; **KHÔNG mở cửa sổ chính thức** (gói v1.1 chưa deploy).
  Tự-restart kế ~10-21 17:56; lần sau ~10-22 05:57 sẽ rơi khung ±3' nếu không deploy lại. Chi tiết `docs/result/V11C_DEPLOY_1021.md`.
- **10-21 07:53:59 (+07, PID 7535, log `MainClass` 07:54:01.267): owner deploy v11c** — jar d7824f6d → **eea5adec** (md5 kiểm qua
  `/proc/7535/fd`), env giữ đúng 1 dòng `LIVE_TS_MKT_EXT=1` + 6 key v11b, heap 3G + gc.log, c3_shadow, SHADOW_NO_PUSH=true, LEGACY 44,
  sổ giấy open=4 realized 88,09 (không đổi). `[TS-EXT] BAT`; seed 30 ngày 07:54:19→07:57:09; `flag day=2026-10-21 flag=OFF dd=-0.137179`
  (max30Day 09-27, minN 1436 do 10-10 thiếu 4'); cache 31 dòng; tick không chậm khi seed. 1 ERROR warm-up `[FEAT-PIPE] khong co feature
  snapshot phut nay` ở tick đầu (07:54:12, không lặp). **CỬA SỔ PROMOTION CHÍNH THỨC gói v1.1 BẮT ĐẦU 2026-10-21 07:53:59 (+07).**
  Tự-restart kế ~19:54:3x; ~chu kỳ 7 (~10-24 19:57) trôi vào khung ±3'. Chi tiết `docs/result/V11C_DEPLOY_1021.md`.

---

## ADDENDUM 2026-10-20 (c) — gói v1.1 = v11b + TS_MKT_EXT X14; cửa sổ chính thức (khai TRƯỚC khi deploy gói)

**A. Quyết định.** Owner 10-20: X14 (`docs/prereg/PREREG_TS_MKT_EXT.md` + addendum 1, HO 2026 CONFIRM `docs/result/TS_MKT_EXT_HO.md`) vào gói v1.1,
chạy shadow trên 242. **Gói v1.1** = jar nhánh `v1.1/ts-mkt-ext` (trên `66cb6196` = v11b d7824f6d; jar `eea5adec…`, khác v11b đúng
`ShadowBookC3` + lớp mới `AltEwIndex`/`TsMktExt`) + env v11b (6 dòng §6.4 `V11_COLLECTOR_SETTLE.md`) + `export LIVE_TS_MKT_EXT=1`.
Spec live: `docs/plan/V11_TS_MKT_EXT_LIVE.md`; runbook `docs/runbooks/DEPLOY_V11_TS_MKT_EXT_242.md`.
TS_MKT_EXT chỉ tác động sổ GIẤY c3_shadow (không vị thế THẬT/LEGACY).

**B. Backtest đối chiếu (thước sim của (ii'), (iii), (iv) và PnL báo cáo) — chạy CÙNG cờ với live:**
- `SIM_LOSER_TS_EXT_HOURS=336` và `SIM_LOSER_TS_EXT_DAYS=<khoảng ngày UTC>` tính bằng luật cờ đóng băng (ALT_EW cuối ngày d ≤ −30 % so max
  EOD d−30..d ⇒ cờ d+1; `tsx_ho.py:flags()`) trên kline **Vision** của đúng kỳ chấm (cập nhật chuỗi trước mỗi lần chấm; ghi sha256 chuỗi).
- `SIM_RANK_TIEBREAK_SYMBOL=1`; nguồn MarketDataObject chuẩn (Java `calMarketData`, died {BTCDOM,USDC} — `V11_COLLECTOR_SETTLE.md` §6);
  jar sim chứa a8690d46 (`sim-jar-tsx` cc0f9d11 hoặc kế thừa có P0 byte-identical).
- Không đổi ngưỡng/giờ/luật TS_MKT_EXT sau khi thấy số forward.

**C. Tiêu chí bổ sung (vi) TS_MKT_EXT (CHẶN CỨNG phần an toàn, phần còn lại parity):**
- (vi-a) 0 dòng `[TS-EXT] defer-START` cho symbol LEGACY, 0 thay đổi vị thế LEGACY do code TS-EXT (như (i')).
- (vi-b) Cờ live mỗi ngày (`[TS-EXT] flag day=…`) = cờ tính lại offline từ Vision cùng luật cho ngày đó. Ngày `NA` (thiếu dữ liệu,
  đã WARN) ghi sổ, không tính trượt; ngày ON/OFF lệch ⇒ TRƯỢT phần parity + điều tra (dữ liệu kline_1m_opt 242 vs Vision).
  Đối chiếu thêm `[TS-EXT] day … sum_ew` với tổng EW Vision cùng ngày (báo cáo |Δ|).
- (vi-c) Mọi cụm giấy chưa arm qua 168h: quyết định cắt/hoãn trong log khớp `decide()` với cờ của ngày (cắt ở nhịp đầu ngày OFF hoặc
  khi > 504h; trễ tối đa ~22' khi PENDING sau 00:00 UTC — đã khai ở spec §3).
- Kỳ vọng thường gặp: 0 ngày cờ trong cửa sổ ⇒ (vi-b/c) = "chưa quan sát", **không chặn** (i')–(v); ghi rõ cơ chế chưa được kiểm forward.

**D. Cửa sổ chính thức.** Cửa sổ đánh giá (B) của gói v1.1 bắt đầu **tại giờ restart deploy gói này trên 242**:
**`2026-10-21 07:53:59 (+07)`** (điền sau khi owner deploy và kiểm 15' của runbook ĐẠT).
  **ĐIỀN 10-21 08:0x: CỬA SỔ PROMOTION CHÍNH THỨC gói v1.1 BẮT ĐẦU tại 2026-10-21 07:53:59 (+07)** (v11c eea5adec, owner deploy,
  PID 7535; kiểm 15' ĐẠT — `docs/result/V11C_DEPLOY_1021.md` phần "DEPLOY LẦN 2").
  (Lịch sử: 10-21 06:0x ghi "CHƯA BẮT ĐẦU" — restart 05:55:29 chạy jar v11b d7824f6d, v11c chưa lên 242, không phải gói v1.1.)
  Khi owner chạy bước 1+4 runbook và kiểm 15' ĐẠT (md5 eea5adec, `[TS-EXT] BAT`, cờ 10-21), điền giờ start thật ở đây; đoạn
  10-20 20:33:04 → giờ đó (kể cả 05:55:29 v11b + env thừa) = giai đoạn kiểm parity v11b, không tính. Tối thiểu 4 tuần như (B). Giai đoạn
10-20 20:33:04 → giờ đó (v11b không TS_MKT_EXT) chỉ là giai đoạn kiểm parity v1.1, không tính vào cửa sổ.
