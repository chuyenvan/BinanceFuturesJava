# PARITY_LIVE_VS_SIM_CHECKLIST — kiểm "all in/out" LIVE (shadow_c3 + 242) so với backtest B0

- **Mục đích:** mọi chỉ số ảnh hưởng *vào lệnh / ra lệnh / size* trên LIVE phải khớp B0 (`profiles/g2_flat3.properties`,
  config sinh B0 = `~/kaggle_sim/out/selab-p0/prof_run.properties`) — hoặc được ghi rõ là lệch + lý do + hành động.
- **Tiêu chí chốt TRƯỚC khi chạy (2026-10-03), không nới sau khi thấy số.** Chạy lại bất cứ lúc nào bằng
  `python3 research/parity/parity_check.py live` (kết quả: `docs/audit/PARITY_LIVE_VS_SIM_<ngày>.json`, exit 0 PASS / 2 FAIL / 3 MISSING).
- **Trạng thái:** `PASS` đo được và đạt · `FAIL` đo được và không đạt · `MISSING` không đo được (thiếu dữ liệu/chưa tới hạn/cần code).
  `FAIL` có cờ `known` = lệch đã biết/có chủ ý, vẫn tính FAIL.
- **Phạm vi:** shadow_c3 (Oracle, được sửa env/config/file, KHÔNG sửa .java/build) · 242 (tiền thật, **CHỈ ĐỌC**).
- **Quy ước thời gian:** log GMT+7; `ts` epoch ms (UTC) = mở nến 1m; dòng `[GATE]` phút M ứng với nến M-1.

## Cách đọc nguồn "kỳ vọng từ sim"
B0 = sim chạy bằng jar `ea14071d`/`d944bea5` (cùng `Configs`/`TradeUtils`/`EntryGate` với jar live `8f3ee52c`), md5 printDone `650c386f`,
n=2517 cụm (2223 PREDICT + 248 BIG_DOWN + 46 DCA_LEVEL1 ở leg đầu), equity cuối 131 908.

## A. Config / key (vào-ra-size)
| id | cách đo | kỳ vọng (B0) | tiêu chí PASS | hành động nếu FAIL |
|---|---|---|---|---|
| A1 | `Probe.java` (reflection, jar live `8f3ee52c`) in **giá trị hiệu dụng** `Configs.*` + `LiveProfileC3.*` dưới 3 bộ env: B0 (prof_run), shadow (`conf/env.sh`), 242 (`conf/env.sh` đọc-chỉ) | TOPK 16, F_BASE 0.015, DCA weights 1,1,1,1, scale 6, U_MAX 0.60 (default), CONC 0.15, gate dyn 1.55, MIN_MOM 0.008, arm 0.07, giveback 1.0, gap 0.03/0.03, pNoPump thr 0.29, LOSER 168h, fee 0.000982, slip 0.000067 | mọi field khác nhau B0↔live phải thuộc danh sách "live không đọc / tương đương" có lý do | sửa `conf/env.sh` shadow (backup) + restart + Probe lại |
| A2 | `/proc/<pid>/environ` của JVM đang chạy (lọc SIM_/LIVE_/TS_/…) = `conf/env.sh` | trùng | 0 key lệch | restart (shadow) / báo (242) |
| A3 | gate rolling: `SIM_GATE_ROLLING_*` (B0) ↔ `LIVE_GATE_ROLLING_*` (live) | ratio / 90 / 0.999950829 | shadow: **có** key hoặc ghi lịch bật 10-07 17:15; 242: có | không bật sớm (xem DEPLOY_SHADOW_2A §3: seed WAN 2,2 h) |
| A4 | key B0 mà live không đọc: `SIM_APPLY_FUNDING`, `SIM_FUNDING_MARK`, `DCA_GRID_ENABLED`, `WFO_FUNDING_PRED_DIR`, `SIM_ENTRY_SAMPLE_MIN` | — | ghi từng key + tương đương live | — |
| A5 | key live-only (ghi nhận): `LIVE_PROFILE`, `SHADOW_NO_PUSH`, `PAPER_EQUITY`, `LIVE_ENTRY_GRID_MIN`, `MARKET_SCAN_*`, `OI_LIVE_REFRESH_MODE`, `SELECTOR_TIER1_NET015`, `TRAIL_HINGE_NET015`, `LIVE_FEAT_DUMP*`, `JAVA_TOOL_OPTIONS` | — | `SHADOW_NO_PUSH=true`, `LIVE_PROFILE=c3_shadow` bắt buộc | — |
| A6 | `config.properties` có key chết (`RATE_FEE`, `RATE_PROFIT_STOP_MARKET`…) — Configs in cảnh báo "KHÔNG AI ĐỌC" | không ảnh hưởng | ghi nhận | — |

## B. Gate
| id | cách đo | kỳ vọng | tiêu chí | hành động |
|---|---|---|---|---|
| B1 | `[GATE]` coverage: số phút distinct / số phút trong cửa sổ (từ lần restart gần nhất) | 1/phút | ≥ 95 % | điều tra tick lỡ |
| B2 | từ `sel_dump` (gateValue sp, 16 ứng viên) tính lại `thr_i = base·max(0.26787, sp/0.15·1.2876)·scale` (float32) ↔ `thr=[min..max]` log | khớp công thức `EntryGate` | \|Δ\| ≤ 6e-6 ở ≥ 99 % phút | env `SIM_GATE_DYN_SCALE`/`SIM_MIN_MOMENTUM_15M` |
| B3 | `n_pass` tính lại (`!(p15<thr_i)`) ↔ log `n_pass` | khớp | 100 % phút | — |
| B4 | ORT(model gate deploy `d19fc8cd`) trên `feat_dump` (33 feat) ↔ `p15_out` | khớp | max\|Δ\| ≤ 1e-6 | — |
| B5 | shadow ↔ 242 cùng phút: p15, thr_min, n_cand, top-16 | khớp | \|Δp50 p15\| ≤ 0.02 pp **và** thr_min ±1 % ≥ 90 % phút | điều tra nguồn dữ liệu Oracle↔242 |
| B6 | ngưỡng khi chưa arm: `[GATE-RATIO] q_t=0.008000` (fallback) ↔ `thr = 0.008·factor·1.55` | fallback base | 242: q_t=0.008 tới arm; shadow: ratio tắt ⇒ base 0.008 | — |
| B7 | **sau 10-07**: `gate_arm_check.py` đọc `run/gate_ratio_live.bin` (GRR1) → q(0.99995 trên r, 90 ngày, floor(pct·(m−1))) ↔ `[GATE-RATIO] q_t` log; `firstTs+7d` | q_t log = q tính lại ±1 ULP; n_pass/ngày ∈ [0.34; 3.8] | chạy được phần fallback hôm nay | xem `DEPLOY_SHADOW_2A` §7 |
| B8 | p15 live ↔ `ai_pred_1m` Aerospike 242 cùng phút (chỉ `get`) | khớp (nhiễm 2 writer tới 10-07) | ghi `gen` | cần jar `f282581a` + `LIVE_IS_SHADOW_HOST=true` (10-07) |

## C. Selector
| id | cách đo | kỳ vọng | tiêu chí | hành động |
|---|---|---|---|---|
| C1 | `sel_dump` shadow ↔ 242 cùng tick: \|top-16 ∩\| | 16/16 (cùng model S1 `8b1dcf00` + net015 `41a07109` + map) | trung bình ≥ 15/16 và ≥ 95 % tick ≥ 14/16 | điều tra feature/OI lệch |
| C2 | thứ tự sort: `rank` tăng ⇒ `gateValue` (sp = 1−P(win)) **không giảm**, `selectorScore` không giảm; rank 1 = sp thấp nhất | luật sim: sp nhỏ nhất = tốt nhất | 100 % tick | — |
| C3 | recompute offline top-16 từ model deploy trên **cùng feature vector live** (45 G015 + 9 KEEP9) | 16/16 | cần vector live | dump vector (cần code) ⇒ MISSING nếu không có |
| C4 | `n_cand` = 16 mỗi tick, số coin được chấm điểm (`[S1] score N coin`) | ~universe sim | ghi N, so shadow↔242 | — |

## D. Feature
| id | cách đo | kỳ vọng | tiêu chí | hành động |
|---|---|---|---|---|
| D1 | 33 feature gate: `feat_dump` shadow ↔ 242 cùng phút | giống | cột PASS nếu ≥ 99 % hàng có \|Δ\| ≤ 1e-3·(1+\|x\|) | tìm nguồn lệch (ticker vs kline) |
| D2 | 33 feature live ↔ DEV export cùng phút (`parity_check.py features`) | 27/33 FAIL lần trước | ghi số cột PASS | — |
| D3 | 45 cột G015 + 9 KEEP9 S1 (vector selector) live ↔ offline | khớp | cần vector live | `feat_dump` hiện KHÔNG ghi ⇒ MISSING, đề xuất code (LiveFeatureDump.maybeDumpSelector) |
| D4 | OI feature: `[OI-LIVE] mode inplace`, số coin nạp/universe | `AUDIT_OI_FEAT_PARITY` KHÔNG VÊNH | ghi | — |

## E. Entry / size
| id | cách đo | kỳ vọng (sim) | tiêu chí | hành động |
|---|---|---|---|---|
| E1 | giá vào = `ticker.priceClose` nến tín hiệu (code: `DetectEntrySignal2TradeNormal` → `ShadowBookC3.openPos(order.priceEntry)`) | sim `entry = ticker.priceClose` | cùng giá | — |
| E2 | margin leg đầu: sim = `equity·F_BASE·throttle/ΣW · tier · (w0·DCA_GRID_SCALE)` (FIX_B2); live = `equity·F_BASE·throttle/ΣW · tier` (**không** nhân scale) — đo bằng `TradeUtils.managerBudget` thật + công thức sim trên cùng equity/throttle | 787.5 ở equity 35000, throttle 1 | \|live−sim\|/sim ≤ 1e-6 | `SIM_F_BASE` shadow = F_BASE×SCALE (bù) |
| E3 | cap per-coin `CONC_CAP_PERCOIN` 15 % và trần 4.5 % equity (live-only) có chặn không | không bind ở leg 0 | không bind | — |
| E4 | số lệnh đồng thời / U_MAX throttle: `U = Σmargin/equity` (live: `ShadowBookC3.marginRunning`) | cùng công thức | cùng công thức | — |
| E5 | DCA grid | sim: có (46 DCA_LEVEL1 + leg 1-3) | live **không có** | FAIL-known (cần code) |
| E6 | ledger giấy shadow/242 (archive `ledger.csv`, `ledger_from_log.csv`): số lệnh, size thực | — | ghi | — |

## F. Exit
| id | cách đo | kỳ vọng | tiêu chí | hành động |
|---|---|---|---|---|
| F1 | arm: giấy hardcode `LiveProfileC3.ARM_RATE=0.07`; legacy `Configs.RATE_PROFIT_STOP_MARKET`=env 0.07 | 0.07 | cùng | — |
| F2 | SL sau arm = `trailFromCap(peak)`: `peak − min(peak·1.0, 0.03)` làm tròn bước 0.005 — chạy hàm Java thật (Probe) vs Python float32 trên lưới peak 0.07→0.50 | khớp | 0 sai khác | — |
| F3 | làm tròn 0.5 % | `Math.round(rate/0.005)*0.005` | đúng | — |
| F4 | ratchet: giấy liên tục; legacy dead-zone ×5.21847 (arm·5.22=36.5 %) | sim liên tục | giấy PASS; legacy ghi (có chủ ý) | — |
| F5 | time-stop 168h: sổ mới (cụm chưa arm) đóng sau 168h; legacy không | sim 168h tại min(open,close) | cùng ngưỡng | — |
| F6 | SL cứng ban đầu (`PRE_ARM_SL`, `calRateLossDynamic…`) | B0: không có (PRE_ARM_SL=0) | live không có | — |
| F7 | nguồn đỉnh/giá: sim = HIGH nến 1m, fill SL = min(SL, open) nến sau; giấy = snapshot `price_realtime` 10 s, fill = đúng SL | cùng | **khác** ⇒ FAIL-known (thiết kế) | cần code nếu muốn so tuyệt đối |
| F8 | cùng-nến ưu tiên: sim đặt SL ở nến arm, không khớp cùng nến (`BLOCK_INTRABAR_LOOKAHEAD`); giấy: arm→ratchet→kiểm `px<=SL` cùng tick | cùng | ghi | — |
| F9 | vị thế thật/giấy đang chạy: đối chiếu SL sổ vs công thức | — | MISSING nếu không có lệnh | — |

## G. Phí / funding
| id | cách đo | kỳ vọng | tiêu chí | hành động |
|---|---|---|---|---|
| G1 | `ShadowBookC3.closeAt` pnl = (exit−entry)·qty (không phí, không slip, không funding) | sim trừ 0.000982·2? + slip 0.000067·2 + funding mark | ghi lệch | tính offline từ ledger |
| G2 | 242 fill thật legacy đóng (phí thực tế vs 0.1116 %/vòng) | 0.000982+2·0.000067 ≈ 0.1116 % | MISSING nếu không có fill | — |

## H. Nhịp / độ trễ
| id | cách đo | tiêu chí |
|---|---|---|
| H1 | `[GATE]`/phút coverage (từ lần restart gần nhất), `[PASS-TIMING] selector tick` p50/p90 | ≥95 %; p90 ≪ 60 s |
| H2 | `[OI-LIVE] inplace refresh … evicted=0` hằng giờ, OOM/ERROR mới = 0 | 0 |
| H3 | auto-restart 12 h giữ heap: `JAVA_TOOL_OPTIONS` có trong `/proc/pid/environ` + `jcmd VM.flags` | shadow PASS; 242 chỉ báo cáo |

## I. Dữ liệu vào
| id | cách đo | tiêu chí |
|---|---|---|
| I1 | universe live: `[S1] score N coin` (shadow vs 242), `n_cand`, số coin trong `sel_dump` | cùng bậc; không BTCDOM/USDC/index |
| I2 | coin vol=0 / symbol lạ xuất hiện trong top-16 | không |
| I3 | legacy: 242 `legacy_symbols.csv` n=?; shadow = 0 | ghi |

## Kết quả và chạy lại

- Kết quả lần chạy 2026-10-03: `docs/audit/PARITY_LIVE_VS_SIM_20261003.md` (+ `.json`, có trước/sau sửa).
- Chạy lại: `python3 research/parity/parity_check.py live --fetch --probe --out docs/audit/PARITY_LIVE_VS_SIM_<ngay>.json --md docs/audit/PARITY_LIVE_VS_SIM_<ngay>.md` (exit 0 PASS / 2 FAIL / 3 MISSING). Cần probe: `research/parity/probe/*.txt` (copy thành `.java` rồi chạy source-file mode, không build repo).
- Mốc đo lại bắt buộc: 2026-10-07 17:15 sau khi bật gate rolling shadow + jar `jar_nowrite` f282581a + `LIVE_IS_SHADOW_HOST=true` (B7, B8, E6, F9).
- Điều kiện chỉ mở rộng bằng checker: F_BASE shadow = F_BASE(B0) x DCA_GRID_SCALE được coi là lệch giải thích được (bù E2); ghi trong audit §7.
