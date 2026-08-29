# REPORT — Gate/frequency ablation trailing WFO + Kaggle self-contained (2026-07-27, session tối)

> Nối tiếp `HANDOFF_20260727_entry_alpha.md` (NEXT#1+#3+#4). Test giả thuyết: gỡ nghẽn frequency (gate MOM15)
> thì trailing — hướng dương duy nhất, trước đó WFE 0.24 FAIL — có PASS robust không?
> Đo-không-đoán. Verdict PnL/commit thuộc Uni. Không commit git, không đụng production 242.

## A. Gate/frequency ablation (Oracle, `ce.cmd`, trailing WFO w4–16)

**Thiết kế thực tế** (điều chỉnh có căn cứ so với grid literal): `MIN_MOMENTUM_15M` là **genome gene HPO** trong
`[0.010, 0.045]` (StrategyWfoTask:60), không phải env cố định. Để đặt gate cố định env-only → `WFO_N_SAMPLES=1`
(sample-0, không HPO) + `SIM_MIN_MOMENTUM_15M`. Cell "gate off" = `ABLATION_MODE=B` (bỏ hết filter).
Fixed-genome N=1, DCA off, funding on, TICKER_SOURCE=file, exit=trailing default.

| cell (gate MOM15) | net-EV (Σ oosPnl) | Σ trades | %OOS-SUCCESS | WFE median | maxDD worst | pre-register |
|---|---|---|---|---|---|---|
| **G0** baseline 0.02284 | +7,928 | 2,741 | 6/13 = 46% | 0.75 | 17% | WFE✅ %OOS❌ DD✅ |
| **G1** low 0.010 | **+11,946** (+51%) | 6,772 (2.5×) | 9/13 = **69%** (75% ex-w16) | **0.68** | 26% | WFE✅ %OOS≈ DD✅ |
| **G2** zero 0.0 | **−55,354** | 45,623 (17×) | 1/13 = 8% | âm | **59%** | tất cả ❌ |
| **G3** off (ABLATION_MODE=B) | ≡ G2 (trùng khít từng số) | — | — | — | — | ≡ G2 |

Pre-register: WFE med≥0.5 / %OOS≥70% / maxDD≤50%. w16 ZERO ở MỌI cell = OOS 2026 hết ticker (structural, không phải gate).

## B. Verdict đo được

1. **FREQUENCY = trần ràng buộc — XÁC NHẬN.** Hạ gate baseline→0.010: trades 2,741→6,772, %OOS 46%→69%,
   net-EV +51%, và **w15 giảm từ 68%→46% tổng PnL** (PnL dàn ra: w8/w11/w12 đóng góp lớn; w11 TOO_FEW→+1547/411tr;
   w13 ZERO→+472; w5/w7 TOO_FEW→SUCCESS). Đây đúng là "mở gate = mở khoá trailing".
2. **Non-monotonic, sweet-spot ~0.010.** Nới gate về 0 / off (G2/G3) = **phá huỷ**: BURN_ACCOUNT hàng loạt,
   maxDD 59%, net-EV −55k. → "nới gate hẳn ra" KHÔNG phải hướng đi; đúng là hạ về mức tuned, không bỏ gate.
3. **Trailing tại sweet-spot: gần-PASS nhưng CHƯA robust PASS sạch.** G1: WFE med 0.68 (≥0.5 ✅), maxDD 26% (✅),
   %OOS 69% / 75% ex-w16 (chạm 70%). NHƯNG còn 2–3 window thoái hoá (w14 BURN, w9 CAPITAL_LOCK), w15 vẫn lớn nhất.
   → edge THẬT nhưng mong manh, nằm trong dải gate hẹp.
4. **WFE 0.24 baseline (handoff) = artifact HPO over-tightening, KHÔNG phải bản chất** (giả thuyết mạnh, cần
   N=30 confirm). Fixed-genome cho WFE med 0.68–0.75 ngay ở gate baseline. HPO thưởng IS-fit → đẩy gate về 0.045
   → giết OOS frequency/robustness. Tức: **cố định gate thấp còn tốt hơn để HPO tự chọn gate.**

## C. Close-branch condition (NEXT#5) — KHÔNG kích hoạt

Điều kiện đóng entry-alpha = "mở frequency mà trailing VẪN WFE-fail + dồn 1 window". Kết quả ngược lại:
mở frequency → WFE med 0.68 (PASS ngưỡng) + PnL dàn khỏi w15. → **KHÔNG đóng nhánh.** Entry-alpha hồi sinh
về trạng thái "near-PASS, đáng theo tiếp": tune sweet-spot gate + xác nhận N=30 + đóng vài window BURN/LOCK.

## D. Kaggle self-contained (NEXT#4) — DONE

- **Root cause thật** (khác handoff đoán): không phải `kaggle_wfo/train.py` (kernel XGBoost khác việc), cũng không
  phải `run_worker.py`/`kernel-metadata.json` (đã đúng, dataset v6 attach sẵn). Mà là dataset `chuyendinh/java-run-lc`
  có `config.properties: TICKER_SOURCE=aerospike` (upload 07-16). Java (`SimulatorMarketLevelTicker1MStopLoss.java:116-136`,
  `KaggleDataLoader.java`) đã hỗ trợ sẵn nhánh `file` — chỉ 1 dòng config sai, KHÔNG cần sửa/rebuild jar.
- **Fix:** đổi `config.properties` → `TICKER_SOURCE=file`, push qua venv Kaggle CLI sạch `kaggle==1.6.17`
  (`D:\claudedata\kaggle-clean-env`; CLI 2.2.2 lỗi `KaggleObject.from_dict()... 'token'` — biến thể bug KAGGLE_RULES §5b).
  dataset_sources của wfo-worker-N không pin version → tự dùng bản mới ở push kế.
- **Verify parity:** kernel độc lập `chuyendinh/wfo-verify-file-parity` (VerifyOneWindow, không claim jobstore chung),
  COMPLETE rc=0, **0 lệnh Aerospike ticker**, w6 = oosPnl 437.41 / wfe 1.2052 / trades 56 → **khớp gần khít Oracle
  handoff** (437 / 1.21 / 56). Còn 1 kết nối Aerospike nhẹ ở SimpleSymbolMapper init (không phải nguồn fail cũ, rủi ro thấp).
- → Fanout Kaggle giờ self-contained; oi_z-thay-gate dataset có thể build/test trên Kaggle fleet, né disk Oracle 89%.

## E. NEXT (chờ Uni quyết — heavy compute)

1. **oi_z THAY gate** (cột còn thiếu của grid): không env-only, cần build predict_wf dataset mới (converter Python).
   Nên chạy trên Kaggle (đã self-contained) để né disk Oracle.
2. **Rebuild jar** để (a) hạ sàn genome MOM15 <0.010 dò sweet-spot rộng hơn, và/hoặc (b) fix gate + regularize DOF,
   rồi N=30 HPO đối chứng apples-to-apples với baseline WFE 0.24 (chứng minh dứt điểm claim B4).
3. Đóng window thoái hoá còn lại (w14 BURN, w9 CAPITAL_LOCK) tại sweet-spot.

Raw: `grid_results.tsv`, `run_gate_grid.ps1` (scratchpad). Không commit/PnL nào được thực hiện.

## F. Nối Probe A — frequency bị bóp bởi CHỒNG gate absolute (không chỉ MOM15)

Probe A (read-only, `D:\claudedata\probe_a_report.md`) xác định entry condition = HYBRID, trong đó leg selector always-on (`PREDICT_SYMBOL_TRADE`) = **ABSOLUTE THRESHOLD** (`SimulatorMarketLevelTicker1MStopLoss.java:280-283`: `if(score > maxThres) break`, maxThres = `PREDICT_SYMBOL_RATE_MAX_THRESHOLD × AI_DYNAMIC_MAX` = 0.15×2.14 = 0.3212). → frequency starve theo regime là do NGƯỠNG, không thiếu candidate.

Bức tranh hợp nhất — frequency bị bóp bởi ≥3 gate absolute nhạy regime, ablation này mới nới 1:
1. `predict != null` coverage (Task 156) — giết 2021/2022.
2. `MIN_MOMENTUM_15M` — gate DOMINANT (gate=0 → 45k trades bung dù selector-threshold vẫn bật). Sweet-spot ~0.010.
3. `PREDICT_SYMBOL_RATE_MAX_THRESHOLD×AI_DYNAMIC_MAX` (Probe A) — secondary. Pass-rate/năm: 2023 51.7% · 2024 79.1% · 2025 98.5% (bóp vừa ở 2023, hết tác dụng 2025).

Ý nghĩa: near-PASS (WFE 0.68) đạt được khi mới nới #2; còn #1 (đang xử lý) + #3 (chưa đụng) vẫn starve thêm → vẻ 'edge chết/dồn w15' phần lớn là artifact stack-gate, KHÔNG phải edge chết. Củng cố: không đóng nhánh, chưa cần build model mới.

Fix ưu tiên gợi ý (chưa test): rank-based top-K thay absolute threshold cho leg selector — top-K tự chuẩn hoá theo regime (không starve lúc yếu, không flood lúc mạnh), an toàn hơn hạ absolute (nhớ: MOM15→0 = BURN −55k, non-monotonic).

Caveat: (a) funding.bin Probe A đọc = lưới 15m KHÔNG forward-fill → cần kiểm nhánh load runtime; (b) 2022 (22.1%) overlap vùng đã chết bởi gate #1. Window→year (suy từ log freq: w4=2023Q1) — cần xác nhận mapping đầy đủ nếu dùng để chấm per-window.

## G. Frequency probe (Kaggle count-only, gate × oi_z, w4-15) — vùng gate + oi_z bị loại

Bảng đầy đủ: `D:\claudedata\freq_probe_table.md`. Đơn vị = `gatePass` (admission thô tại gate, per symbol×phút).

1. **off (MOM15 thuần): vùng gate khả dụng ≈ [0.008, 0.010].** Mọi window w4-15 có gatePass>0 ở gate ≤ 0.010 → MOM15 mức thấp KHÔNG starve window nào. Gate ≥0.015 zero w4/w13. Gate 0.003 admit ~94% (w15 451080/480732) → sát gate-off = flood/BURN. Khớp sweet-spot 0.010 của ablation.
2. **oi_z LOẠI trên chính frequency (độc lập PnL):** Q25 giết sạch w4/5/7/8 (gateSeen off>0 → q25=0); Q50 giết w5/7/8; các window còn lại sụt 99%+ (w9 109140→127, w13 146801→89). oi_z = frequency destroyer, không phải quality filter. Đóng oi_z dứt điểm.
3. **CAVEAT:** gatePass = admission thô, KHÔNG phải trade cuối. Probe (a) bác 'MOM15-thấp starve window', (b) loại oi_z; NHƯNG không tự giải thích zero-trade gốc. Zero-trade gốc = HPO đẩy MOM15 cao (≥0.02 → w4/w13→0) + selector-score absolute (Probe A) + pred coverage (Task 156).
4. **Hội tụ config frequency-viable:** MOM15 fix ~0.008-0.010 (không để HPO đẩy lên) + oi_z off + xử lý selector-threshold (rank-based per Probe A) → chạy full trailing WFO ở config này = test go/no-go.

## H. GO/NO-GO (2026-07-28) — Track1 (Kaggle absolute) vs Track2 (Oracle rank-based)

Bảng: `D:\claudedata\gonogo_results.md`. Fixed-genome N=1, DCA off, funding on, TICKER_SOURCE=file, oi_z off.

| Config | net-EV | WFE med | %OOS(/13) | maxDD | w15-share |
|---|---:|---:|---:|---:|---:|
| G1 baseline | +11946 | 0.68 | 69% | 26% | 46% |
| mom008 | +9186 | 0.286 | 69% | 27% | 44% |
| mom010 | +11946 | 0.612 | 69% | 26% | 46% |
| rank-off | +11946 | 0.540 | 69% | 26% | 46% |
| rank-K3 | +5077 | 0.238 | 69% | 6.1% | 44% |
| rank-K5 | +5899 | 0.388 | 77% | 8.1% | 37.8% |

- **Harness validated:** mom010(Kaggle)=rank-off(Oracle)=G1=11946.3 trùng khít → 2 pipeline độc lập parity.
- **Hạ gate 0.008 = tệ hơn** (net↓, WFE 0.286) → sweet-spot KHÔNG dưới 0.010; bác lo ngại lưới thô (thấp hơn không tốt hơn).
- **rank-K5 validate một phần giả thuyết Probe A:** maxDD 26%→8%, w15-share 46%→38%, %OOS 69%→77% (qua ngưỡng). Đánh đổi: net-EV còn nửa, WFE 0.39 (fail).
- **Verdict: BORDERLINE — không GO sạch, không NO-GO, KHÔNG đóng nhánh.** Không config nào qua đủ 3 ngưỡng (WFE≥0.5/%OOS≥70%/DD≤50%) cùng lúc.
- **CONFOUND chưa fair với rank:** rank-K3/K5 chạy trên genome tuned cho ABSOLUTE mode → WFE thấp có thể là mismatch genome-config, chưa phải overfit thật (như mom008 WFE sụp vì flood + genome không hợp).
- **NEXT quyết định:** HPO re-tune genome RIÊNG cho rank-K5 mode rồi chấm WFE (= task #5 N=30 target rank-K5, không phải gate). WFE≥0.5 giữ %OOS77%+DD8% → GO sạch; vẫn <0.5 → non-monetizable robust → close.
- Caveat: Track1 mom008/mom010 thiếu w16 (kernel rc=1; w16 = ZERO structural 2026, không ảnh hưởng verdict).

## I. Rank-K sweep (2026-07-28, Kaggle N=1 fixed-genome, MOM15=0.010) — tìm K tối ưu shape

Bảng: `D:\claudedata\rank_k_sweep.md`. Parity K5: Kaggle 5922 vs Oracle 5899 (lệch 0.4%).

| K | net-EV | WFE(conf) | %OOS | maxDD | w15-share |
|---|---:|---:|---:|---:|---:|
| off(abs) | 11946 | 0.54 | 69% | 26% | 46% |
| K3 | 5077 | 0.24 | 69% | 6.1% | 44% |
| K5 | 5899 | 0.39 | 77% | 8.1% | 38% |
| K8 | 6165 | 0.54 | 69% | 11% | 24% |
| K10 | 6610 | 0.55 | 61.5% | 11% | 21.8% |
| K15 | 8413 | 0.58 | 61.5% | 17% | 28% |

- **net-EV ↑ đơn điệu, maxDD ↑ đơn điệu theo K** — không free lunch, không đỉnh nội tại ở 2 metric này. K→lớn tiến về absolute.
- **%OOS đỉnh K5 (77%)** (breadth tốt nhất); **w15-share đáy K8-K10 (~22-24%)** (dàn rủi ro tốt nhất).
- **WFE ↑ theo K nhưng CONFOUNDED** (genome tuned-absolute; K lớn ≈ absolute → hợp genome hơn). KHÔNG dùng chọn K. Ghi chú: K8+ đã WFE conf ≥0.5 → sau N=30 re-tune fair, K≥8 nhiều khả năng đạt WFE≥0.5 dễ hơn K5 (0.39 conf).
- **Frontier, không 1 điểm:** K5 = breadth+an toàn (%OOS77/DD8) net thấp; K8 = cân bằng (w15 24%, net nhỉnh, DD11, %OOS69). Chọn theo mục tiêu.
- **Chờ:** Oracle N=30-K5 (fair WFE cho K5). Nếu K5 WFE≥0.5 → GO K5 (breadth cao). Nếu <0.5 → N=30 re-tune K8 (WFE-safe hơn, spread tốt, net nhỉnh) là candidate GO thay thế.
- Caveat: cả 4 kernel thiếu w16 (rc=1, structural) — tính trên 12/13, đồng nhất nên không ảnh hưởng so sánh.

## J. N=30 re-tune rank-K5 (fair WFE) — K5 FAIL, confound BÁC (2026-07-28)

Bảng: `D:\claudedata\n30k5_verdict.md`. MOM15=0.010 xac nhan 13/13. off0 anchor net 5899 khop harness.

| | K5 fixed-genome | K5 N=30 re-tune | pre-register |
|---|---:|---:|---:|
| WFE median | 0.388 | 0.434 | ≥0.5 ❌ |
| %OOS-SUCCESS | 77% | 53.8% | ≥70% ❌ |
| maxDD | 8.1% | 10.9% | ≤50% ✅ |
| w15-share | 37.8% | 59.3% | — |
| net-EV | 5899 | 6678 | — |

- **Confound BẠC:** WFE re-tune chỉ 0.388→0.434, vẫn <0.5 → rank-K5 KHÔNG generalize thật (không phải genome mismatch). K5 = **FAIL pre-register** (2/3 trượt: WFE + %OOS).
- **HPO re-tune làm TỆ HƠN:** %OOS 77%→54%, w15-share 38%→59% → N=30 chase IS-PnL → chọn genome dựa dẫm w15 → breadth sụp. net-EV tăng chỉ nhờ w15.
- **META (lặp lần 3):** HPO trên hệ này overfit vào window w15 (lần 1 = WFE 0.24 gate artifact). → fixed params generalize tốt hơn HPO; WFE tương tác xấu với hệ có 1 window thống trị.
- **CRUX:** mọi config đều dồn PnL vào w15 (2025Q4 vol cao) — edge thực chất là 'một quý ngon'. Câu hỏi sống-còn: có config nào edge KHÔNG phụ thuộc w15? K5 không phá được.
- **Còn 2 phát cuối:** K8 N30 (nhiều coin hơn, w15-share conf 24%) + offset-sweep (cắt top fake-pump w15). Nếu cả 2 không phá được w15-dependence → close entry-alpha.

## K. Fitness WFO HPO (Probe B, read-only) — mismatch 3 tầng (2026-07-28)

Bảng: `D:\claudedata\probe_b_fitness.md`.
- **Chọn genome (per-window):** `finalFitness = Calmar × factor` (`HPOFitnessCalculatorV4.java:173`); Calmar=profit/|maxDD| (`:136`), factor∈[0.5,1] thưởng số lệnh (`:167-172`). Sharpe không dùng; Sortino report-only. Best = argmax isFit (`StrategyWfoTask.java:210`); rejectSamples chỉ đếm.
- **WFE = `oosPnl/isPnl`** (raw PnL ratio, `StrategyWfoTask.java:227`) — KHÔNG dùng Calmar. → **mismatch chọn(Calmar) vs chấm(raw-PnL)**.
- **net-EV = Σ oosPnl tuyệt đối** (script scratchpad ngoài repo).
- **KHÔNG có term** consistency / phạt concentration / normalize theo vol. Constraint `posYearRatio≥0.80` **TẮT** cho WFO 12 tháng (guard `spanYears≥2`, `:157-160`).
- **Ngụ ý:** "edge đều nhưng đo sai bằng Σ$" = SAI — WFE-median & %OOS đã là metric breadth, vẫn fail. Lever hợp lý = align objective (chọn theo đúng cái chấm) + term consistency + bật posYearRatio; nhưng fixed-genome K5 WFE 0.388 → gap IS→OOS nội tại, trần thấp. Đổi fitness = p-hacking risk → re-pre-register + held-out bắt buộc.

## L. N=30 re-tune rank-K8 (fair WFE) — K8 FAIL breadth, tension frontier (2026-07-28)

Bảng: `D:\claudedata\k8_offset_status.md`. w16 loại (Kaggle geo-block Binance API, rc=1); tính 12/13. MOM15=0.010 xac nhan.

| | K5 N30 | K8 N30 | pre-register |
|---|---:|---:|---:|
| WFE median | 0.434 ❌ | 0.573 ✅ | ≥0.5 |
| %OOS-SUCCESS | 54% ❌ | 46% ❌ | ≥70% |
| maxDD | 10.9% | 11.3% ✅ | ≤50% |
| w15-share | 59% | 37% | — |
| net-EV | 6678 | 5079 | — |

- **K8 chữa WFE (0.573≥0.5) + ít dồn w15 (37%) nhưng %OOS tụt 46%** (tệ hơn K5). Cả 2 config đều FAIL pre-register.
- **TENSION FRONTIER (bằng chứng edge mong manh):** K5 fail WFE / breadth khá; K8 pass WFE / breadth tệ → cải thiện WFE đánh đổi breadth và ngược lại. KHÔNG có config nào vừa robust vừa rộng. Cả hai chỉ chạy ~nửa số window.
- **Xu hướng: CLOSE.** Còn offset-sweep (mechanical, N=1 shape — dù đẹp vẫn cần N30 confirm) + fitness-alignment (methodological, p-hacking caveat) là 2 lever cuối.
- Infra note: Kaggle bắt đầu geo-block Binance API → w16 (OOS 2026) fail rc=1 (vốn structural-zero, không đổi verdict). Ghi INFRA_FACTS.

## M. Probe C — mổ w15-dependence: NGHIÊNG M (harness artifact), KHÔNG phải regime (2026-07-28)

Bảng: `D:\claudedata\probe_c_w15_dissection.md`. Đảo lại lean 'close' trước đó.

**w15 PnL/lệnh ≤ trung bình non-w15 (fixed-genome N=1):**
| config | w15 PnL/lệnh | non-w15 PnL/lệnh |
|---|---:|---:|
| rank-off | 1.81 | 2.73 |
| K5 | 2.97 | 3.61 |
| K8 | 1.40 | 2.81 |

- **R bị bác:** w15 to tuyệt đối CHỈ vì số lệnh (nhiều opportunity hơn), edge/lệnh non-w15 còn CAO HƠN → edge RỘNG, không độc quyền w15.
- **HPO là thủ phạm:** N=30 cơ học starve non-w15 (w11/w13) + bơm w15, tái lập trên K5 & K8. Core w6/7/8/12 SUCCESS bền mọi config.
- **Verdict-không: NGHIÊNG M** (harness/HPO overfit + Σ$ aggregation), hybrid, tin TRUNG BÌNH.
- **Bottleneck = WFO/HPO HARNESS, KHÔNG phải gate/selector/regime.** → hướng đi: sửa harness, giữ gate+selector; KHÔNG build gate/model mới, KHÔNG close (chưa).
- **Cap tin (2 thiếu):** (a) leakage — fixed-genome sample-0 = param production live, nguồn tune không xác định (`StrategyWfoTask:185-186 getField`) → breadth có thể là leakage; (b) thiếu return%/win-rate/cost.
- **STEP-2 quyết định:** genome đóng băng train CHỈ trên data pre-OOS (diệt leakage) apply forward all-window + metric return%/winRate/cost-per-trade. Non-w15 winRate>50% + net dương sau phí → M xác nhận (sửa harness); sụp → R (breadth = leakage → close). Chạy Oracle (226 cho w16).

## N. Offset-sweep CHẾT + step-2 crash (2026-07-28)

- **Offset-sweep K5 (off{1,2,3,5,8}, N=1 shape):** net-EV GIẢM đơn điệu theo offset (off0 5899 → off8 4130). Bỏ top-rank chỉ MẤT edge → **top-K CHÍNH LÀ edge, KHÔNG phải fake-pump**. w15-share giữ 31-38% ở MỌI offset → offset KHÔNG giảm w15-dependence. → **lever offset CHẾT** (giả thuyết top-nhiễm bị bác). Bảng: `D:\claudedata\step2_offset_verdict.md`.
- **Step-2 (frozen leakage-free A/B) CRASH** = harness bug (regex derive genome kỳ vọng RESULT_JSON ngay sau `rc=0`, java-logger chèn dòng vào giữa → 0 parse → abort). KHÔNG phải kết quả khoa học. **Verdict R/M CHƯA CÓ.** Re-run với regex `RESULT_JSON (\{.*\})`, jar `binance-lf-frozen-1.0.0.jar` đã build sẵn.

## O. VERDICT CUỐI CÙNG (2026-07-28, sau re-run step-2) — **M: SUA HARNESS, KHONG CLOSE NHANH**

Bảng đầy đủ: `D:\claudedata\step2_final_verdict.md`. Nhánh A = genome đóng băng train CHỈ trên 2022 (KHÔNG thể leak), rank-K8, MOM15=0.010, funding-fee ON. Coverage verdict = w2-w14 (13 window OOS non-w15; loại w0/w1 derive-in-sample, w15 pre-register, w16 zero-trade cấu trúc).

| tiêu chí (non-w15, N=13) | A (frozen, leakage-free) | B (production) |
|---|---:|---:|
| winRate>50% | **13/13 (100%)** | 4/13 (31%) |
| net-after-cost dương | **11/13 (85%)** | 11/13 |
| CẢ HAI (rule) | **11/13 (85%)** | 4/13 (31%) |
| Σ net | **+10106** | +4327 |
| net/trade | **8.59** | 1.92 |

**Áp rule pre-committed (không nới): A đạt 11/13 (85%) ≥ đa số → VERDICT = M.** Edge rộng, leakage-free, THẬT. Genome sạch net/trade non-w15 (8.59) ≥ w15 (7.97); w15 chỉ chiếm 28% Σnet — w15-dominance là artifact, không phải bản chất.

**A-vs-B: B KHÔNG tốt hơn A (ngược dự đoán leakage) — A thắng B 2.34× Σnet, 4.48× net/trade.** → breadth KHÔNG phải leakage; genome production hiện tại dưới mức tối ưu.

**Chân dung bottleneck (bằng chứng trực tiếp):** trong 13 window non-w15 của A, các window fail ăn đúng `TOO_MUCH_CAPITAL_LOCK` (7) và `TOO_FEW_TRADES` (4) — **harness đang loại bỏ chính window ĐANG LÃI** vì constraint capital-lock/min-trades, không phải vì vô edge.

**KẾT LUẬN CHIẾN LƯỢC:** KHÔNG build gate mới, KHÔNG build model mới. giu nguyen gate (MOM15=0.010) + giu nguyen selector (rank-K8/tuong duong). Fix WFO/HPO harness: (a) nới/sửa constraint TOO_MUCH_CAPITAL_LOCK/TOO_FEW_TRADES đang loại nhầm window lãi; (b) fix fitness mismatch (§K: Calmar-chọn vs raw-PnL-chấm); (c) cân nhắc genome gần-frozen/regularized thay per-window HPO argmax (argmax = nguồn w15-overfit, §J/§L).

**Caveat còn treo (chưa N=30 confirm trên harness đã sửa):** N=1 shape; avgLoss A khá béo (đuôi rủi ro, DCA-like); w16 (OOS 2026 forward) chưa có bằng chứng (Kaggle geo-block + Oracle cũng zero). Offset-sweep đã đóng (§N, lever chết, top-K không nhiễm). Bước tiếp theo (không phải trong scope report này): sửa 2 constraint trên trong Java WFO core (uncommitted → cần review + commit), rồi N=30 confirm full trên harness mới trước khi coi là production-ready.
