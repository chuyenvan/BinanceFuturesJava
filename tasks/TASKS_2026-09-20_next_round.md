# TASK BRIEFS — vòng tiếp theo sau T170 (soạn 2026-09-20, MASTER = phiên Fable)

Mỗi mục dưới đây là một brief **tự chứa**, copy nguyên khối cho một agent (Sonnet/Opus) là chạy được.
Phần 0 là luật chung — dán kèm vào MỌI brief.

---

## 0. LUẬT CHUNG (dán kèm mọi task)

**Nguồn sự thật & kênh**
- Repo canonical: Oracle `/home/ubuntu/src/BinanceFuturesJava`, branch `module` (HEAD ≥ `99b6580`). Bản Windows
  `E:\educa\source\github\20260415\BinanceFuturesJava` CŨ ~50 commit, có `.git/index.lock` rác + diff CRLF giả —
  chỉ dùng để đọc `docs/runbooks/AGENT_RUNBOOK.md` §1, KHÔNG làm nguồn code/docs, KHÔNG commit bên Windows.
- Tới Oracle CHỈ qua desktop bridge (`docs/runbooks/AGENT_RUNBOOK.md` §1): desktop-commander `write_file` .sh →
  `C:\Users\pc\AppData\Local\Temp\<prefix>_<n>.sh`; `start_process` (timeout_ms 25000)
  `powershell.exe -NoProfile -Command "Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\pc\AppData\Local\Temp\runsh.ps1','-Sh','<sh>','-Out','<log>' -WindowStyle Hidden; 'launched'"`;
  đọc `read_file <log>` (ENOENT = chưa xong). Load 3 tool desktop-commander bằng MỘT ToolSearch. Job > 5 phút:
  `nohup ... > log 2>&1 & disown`, poll log cách quãng, không giữ bridge. Bridge lỗi >3 lần liên tiếp ⇒ dừng, báo PID + bước.
- **Oracle = aarch64 (ARM64), 4 core / 23G / swap 0. CHỈ MỘT job nặng tại một thời điểm** (sim java `-Xmx14g`
  HOẶC train xgboost). Trước mỗi job: `free -g` (available ≥12G) + `pgrep -af "Simulator|ExportWfo|s1_hpo|xgboost"`
  rỗng. Process `BinanceOrderTradingManager` (shadow-c3, -Xmx4g) là paper, không đụng. Vi phạm 09-19 đã gây OOM + sập SSH.
- Kaggle CPU = x86_64 ≠ Oracle ARM64 ⇒ **mọi A/B phải cùng env**; Kaggle-variant chỉ so Kaggle-baseline
  (S1 edge5 15.209%, dataset `chuyendinh/s1-featv2-x1-20260919`), Oracle-variant chỉ so Oracle-baseline. Sàn vênh
  cross-arch +0.197pp edge5 (`docs/result/RESULT_S1_DETERMINISM.md`). GPU CẤM cho rank-IC.
- Đĩa Oracle ~26G trống. Dataset WFO tạm (~4.3G) `rm -rf` ngay sau khi dùng. KHÔNG xoá: `aerospike-data/`,
  `predwf_*`, `claudedata/`, `featv2/`, `ledger/`, `wfo_ds_x1_2021/`, `derivs_store/`, `kaggle_data_hpo/`, `ds_feat*/`,
  `java/fsrun/`, `selector_pred_out/`, `shadow_c3/`, `s1hpo/`.

**Kỷ luật nghiên cứu**
- **Pre-reg TRƯỚC khi chạy**: `docs/PREREG_<TÊN>.md` commit trước bất kỳ run nào; ghi luật thắng, k, dự đoán;
  KHÔNG sửa sau khi thấy số (chỉ thêm phụ lục đính chính). Kết quả → `docs/RESULT_<TÊN>.md` cùng format
  `docs/result/RESULT_K_DENSITY.md`.
- Incumbent = **T170**: `profiles/x1_gs_t170.properties` (`SIM_GATE_DYN_SCALE=1.70`), devrun
  `/home/ubuntu/java/devrun/X1_GS_T170_2021`, md5 printDone `efb793e2`, n=1089, equity 111.070, CAGR 29.27,
  maxDD −11.84, UW 92; dataset `wfo_ds_x1_2021` (18 fold 2021-07→2025-12), bins `predwf_map_s1a2_x1_2021`.
  **Cổng reproduction bắt buộc** trước mỗi vòng sim: chạy lại T170 phải ra md5 `efb793e2` (devrun cần symlink
  `ln -sfn /home/ubuntu/java/simulator/kaggle_data_hpo kaggle_data_hpo`; ~13 phút/run; xem `docs/runbooks/AGENT_RUNBOOK.md` §2,
  `docs/result/RESULT_DEV2021_READJUDICATE.md` §7, `docs/result/RESULT_TRAIL_HINGE.md` ghi chú vận hành).
- **Luật thắng sim**: variant THẮNG ⇔ ≥2 rate chất lượng (win%, TSloss%, meanP, mP|SL) ngoài CI block-72h
  **cùng hướng tốt** với `research/analysis/x1_rates.py ... --k <số variant>` (inflate(k)=sqrt(2 ln k), k=1→1.0;
  `docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md`) VÀ PASS rào cứng theo năm theo **khẩu vị mới** `docs/runbooks/RISK_APPETITE.md`:
  maxDD≤30 · UW≤200 · quý≥−15 · tập trung 1 coin ≤15% (ghi thêm ngưỡng cũ 15/120/−5 để tham khảo). ≥2 rate hướng
  xấu ⇒ THUA; còn lại NULL. Equity/CAGR chỉ báo cáo, không phải tiêu chí. **Cấm mở biến thể quanh winner** (B4/GD92).
- **Luật offline (rank-IC/edge5)**: metric chính edge5 OOS (mean g1lite top-5 trong tick − mean tick); paired
  block-bootstrap 72h, 2000 rep, CI95 × inflate(k). **Nested**: SELECT (OOS 2021Q3→2023Q4) chỉ để ĐỀ CỬ,
  **CONFIRM (2024Q1→2025Q4) là cổng quyết duy nhất**; đối chứng nhiễu chỉ chấm trên CONFIRM
  (bài học `docs/result/RESULT_S1_HPO_BAG_FEATGRP.md` §1, `docs/prereg/PREREG_S1_NOISE_CAL.md`). Score S1: thấp = tốt (bẫy dấu).
- **HOLDOUT 2026 KHÔNG đụng** (`SIM_END_DATE=20251231`; `HoldoutSeal`). Box 242 (tiền thật) KHÔNG ssh, KHÔNG deploy.
  KHÔNG `git push`. Trailer commit: `Co-Authored-By: <model của bạn> <noreply@anthropic.com>` +
  `Claude-Session: <link phiên của bạn>`. Gặp `index.lock` do agent khác: chờ 30s thử lại, không xoá.
- Đã ĐÓNG (không lặp lại): mọi trục exit/time-stop/SL adaptive/trailing STRONG-WEAK, K density, 2x-halfsize, DCA
  signal/gate-widen/more-legs/round-cap/agg-percoin/hold-DCA, BIG_DOWN size/select/threshold, gate scale 48 tháng,
  gate rolling GD92, gate 27-feature, regime gate BTC30d, S1 +OI features, S1 HPO/bagging/nhóm feature còn sót,
  FS 16 feature giá/volume/funding, pump-dump detectors, collapse probes, trend-following, short mirror.
  Danh sách + verdict: `docs/index.md` banner, `docs/RESULT_*.md`.

---

## TASK 1 — BETA_DECOMP_T170 (chạy TRƯỚC, quyết định các task sau) · read-only · ~2-4h · Sonnet

**Câu hỏi**: CAGR 29% của T170 là alpha xếp hạng hay beta BTC được gate bật đúng lúc? Chưa ai đo.

**Dữ liệu (chỉ đọc)**
- Equity ngày: `/home/ubuntu/java/devrun/X1_GS_T170_2021/logs/sim.out` dòng `Update YYYYMMDD 07:00 => b:<B> ... unP:<U>`,
  equity = B+U, bản cuối mỗi ngày — **tái dùng** `research/analysis/c3_rates.py` `C.equity()`, không tự parse khác.
  Baseline đối chiếu `X1_C3_FULL_2021` cùng chỗ. Cửa sổ 2021-07-01→2025-12-31, vốn 35.000.
- Lệnh: `.../X1_GS_T170_2021/storage/printDone.csv` (`pd.read_csv(on_bad_lines="skip")`; cột `sym,side,entry,tp,
  profit,status,start,time_start_format,end,...,margin,pnl,...,symbolPred`; giờ GMT+7 naive; `profit` %/lệnh; `pnl` USDT).
- BTC close 1h: `/home/ubuntu/java/fsrun/CLOSES_1H.bin` — tái dùng loader trong `research/pipeline/feat_v2_build.py`
  hoặc `research/analysis/trend_rank_ic.py`; map symbol qua `/home/ubuntu/selector_pred_out/symbol_map.csv` nếu cần.
  Mốc ngày BTC = close 1h ≤ 07:00 GMT+7 (= 00:00 UTC) để khớp dòng `Update`. **In vài dòng kiểm ghép mốc** (lỗi hay gặp).

**Phép đo (viết luật đọc vào đầu file kết quả TRƯỚC khi chạy, không đổi sau)**
- A. Tầng ngày (T170 và baseline; theo năm + toàn kỳ): r_s = ln-return equity, r_b = ln-return BTC. OLS `r_s = α + β r_b`
  với **HAC Newey-West lag 5**: α (ngày, annualized ×365), β, R², t(α). Phân rã tích luỹ: Σβr_b (phần beta) vs Σ(α+ε)
  → **% tổng lợi nhuận log thuộc beta**. Dual-beta (ngày BTC lên / xuống). Beta chỉ trên ngày có vị thế mở
  (ngày ∈ [start,end] của ≥1 lệnh) vs ngày không vị thế (kỳ vọng ≈0, sanity).
- B. Tầng lệnh: r_btc_hold = ln(BTC(end)/BTC(start)) trên đúng thời gian giữ. OLS `profit = a + b·r_btc_hold`
  (HAC cụm theo ngày vào lệnh): a, b, R², theo năm. Σpnl lệnh có r_btc_hold>0 vs ≤0 + winrate hai nhóm.
  PnL "chỉ nhờ BTC" = Σ(notional × r_btc_hold) so Σpnl thật (notional đúng theo cách `c3_rates.py` tính).
- C. Y hệt cho baseline `X1_C3_FULL_2021` để thấy gate chặt (T170) giảm beta hay chỉ giảm số lệnh.
- D. **Luật đọc pre-declared** (chép nguyên): "(i) phần beta ≥60% tổng lợi nhuận log VÀ |t(α)|<2 ⇒ **CHỦ YẾU BETA**
  (tối ưu selector là tối ưu sai chỗ; sản phẩm thật là BTC beta có timing). (ii) phần beta ≤40% VÀ |t(α)|≥2 ⇒
  **CHỦ YẾU ALPHA**. (iii) còn lại ⇒ **HỖN HỢP**, báo tỉ lệ." Không kết luận gì ngoài 3 nhãn.

**Đầu ra**: `research/analysis/beta_decomp_t170.py`, `/home/ubuntu/s1hpo/beta_decomp.json`,
`docs/analysis/ANALYSIS_BETA_DECOMP_T170.md` (nguồn + múi giờ, luật đọc, bảng A/B/C, nhãn D, giới hạn: BTC là proxy duy nhất,
mẫu theo năm nhỏ). Commit 2 file. Báo: bảng β/α ann./t/R²/%beta/dual-beta/beta lệnh cho T170 & baseline theo năm
+ toàn kỳ, nhãn D, bất thường.

**Rẽ nhánh sau task này**: CHỦ YẾU BETA → ưu tiên TASK 2 (hedged book) và cân nhắc lại toàn bộ chương trình selector.
CHỦ YẾU ALPHA → ưu tiên TASK 3/4 (dữ liệu mới) rồi TASK 2. HỖN HỢP → TASK 2 trước (nó tách hai phần ra đo được).

---

## TASK 2 — HEDGED_BOOK: long top-k + short BTC perp theo beta · code sim + pre-reg · 1-2 ngày · Opus

**Giả thuyết**: ICC(ROI, cohort ngày)=0.247 ⇒ trần ~4 cược độc lập/ngày; hệ long-only alt = một cược chiều BTC. Hedge
yếu tố chung bằng short BTCUSDT perp theo beta ⇒ ICC↓, n_eff↑ 4-5×, CI hẹp ⇒ hiệu ứng selector ~0.5pp đo được.
Đây là hướng DUY NHẤT đánh vào nút thắt power (`power_wall.md`, `ci_reality.md`). KHÁC `RESEARCH_SHORT` (short-only
mirror, đã đóng) và `ENABLE_SHORT` (đảo tín hiệu).

**Bước 1 — Recon code (trước khi thiết kế)**: đọc `SimulatorMarketLevelTicker1MStopLoss`, `BudgetManagerSimple`,
`tradecore/EntryGate`, `Configs.java` (`grep -rn "SHORT\|hedge\|SELL" src/main/java | head -50`), `docs/analysis/RESEARCH_SHORT.md`,
`docs/experiment/C3_BASELINE.md`. Trả lời: sim có mở được vị thế SELL độc lập không (không qua cơ chế đảo tín hiệu)? Funding
được tính cho SELL không? Có chỗ nào ghép "portfolio-level leg" (một lệnh không thuộc coin selector) không?
Ước lượng số dòng code. Nếu >~400 dòng hoặc đụng lõi sizing → viết `docs/design/DESIGN_HEDGED_BOOK.md` trước, dừng chờ Uni duyệt.

**Bước 2 — Thiết kế (ghi vào PREREG, chốt trước)**
- Hedge leg: một vị thế SHORT BTCUSDT perp, notional = β_target × Σ notional long đang mở, rebalance khi Σ notional
  long đổi >20% hoặc mỗi 4h (tham số cố định, không quét). β_target: **cố định 1.0** (dollar-neutral) cho V1;
  V2 = β ước lượng rolling 30 ngày từ TASK 1 (không nhìn tương lai: chỉ dùng dữ liệu ≤ t). k=2. KHÔNG có biến thể thứ 3.
- Chi phí hedge phải mô hình hoá: funding BTC perp 8h (nguồn: `label_15m/funding_label_*.pb` hoặc `claudedata/funding_lf.bin`),
  phí taker 0.05%/rebalance, slippage 1bp. Ghi rõ giả định.
- Cổng byte-identity: `HEDGE_MODE=OFF` phải ra md5 `efb793e2` (T170 không đổi). Đây là điều kiện bắt buộc trước khi tin số.
- **Metric chính KHÔNG phải CAGR** (hedge sẽ cắt CAGR — đó là mục đích): 
  (a) ICC(ROI lệnh, cohort ngày) và n_eff (tái dùng `docs/result/NBETS_RESULT.md`/`PREREG_NBETS.md` cách tính) — kỳ vọng ICC↓;
  (b) Sharpe ngày (annualized) và **CI bootstrap của Sharpe**; (c) β thực nghiệm của book sau hedge (từ TASK 1 script) —
  kỳ vọng |β|<0.2; (d) maxDD/UW theo khẩu vị mới; (e) MDE80 cho hiệu ứng selector: chạy lại cặp T170-vs-T100 (hoặc
  S1-vs-G015) DƯỚI hedge và đo CI của hiệu — **đây là câu hỏi thật: hedge có làm phép so selector phân biệt được không**.
- Luật đọc pre-declared: "THÀNH CÔNG kỹ thuật ⇔ β_after ∈ [−0.2,0.2] VÀ ICC giảm ≥50% VÀ n_eff tăng ≥2×. CÓ ALPHA ⇔
  Sharpe_after CI95 loại 0. Nếu thành công kỹ thuật nhưng Sharpe CI chứa 0 ⇒ kết luận: phần lớn lợi nhuận T170 là beta
  — ghi thẳng, không biện hộ."
- Dự đoán MASTER (ghi trước): hedge đạt về kỹ thuật (β↓, ICC↓), Sharpe sau hedge dương nhưng nhỏ, CI có thể chứa 0.

**Bước 3 — Chạy**: cổng repro T170 → OFF byte-identity → V1 → V2 (tuần tự, 1 job/lần) → chấm → `docs/RESULT_HEDGED_BOOK.md`.

**Rủi ro nói thẳng**: funding BTC perp âm/dương kéo dài ăn vào kết quả; hedge rebalance rời rạc để lọt gap; short
BTC trong bull run cắt phần lớn CAGR lịch sử. Mọi cái đó là ĐÚNG mục đích đo — không phải lý do bỏ.

---

## TASK 3 — MICROSTRUCTURE_DATA: mua lịch sử L2/trades thay vì chờ collector · đề xuất, không mua · 0.5 ngày · Sonnet

**Lý do**: `power_wall.md` + 3 xác nhận (FS 0/16, OI12, HPO/bag/featgrp) ⇒ thông tin mới chỉ có thể ở order book /
trade-by-trade / cross-exchange. Collector `derivs_store/` mới 8 ngày; liquidation collector (`36e3e2c`) CHƯA ghi được
dòng nào (Uni kiểm `derivs_store/$(date +%Y%m%d)/liquidations.csv`). Chờ 6-12 tháng là quá lâu.

**Việc (chỉ nghiên cứu + viết đề xuất, KHÔNG mua, KHÔNG tải dữ liệu lớn về Oracle)**
1. Khảo sát nhà cung cấp: Tardis.dev, Kaiko, CoinAPI, Amberdata, Binance Vision (miễn phí: chỉ aggTrades/klines/metrics,
   KHÔNG có L2 lịch sử — xác nhận lại). Với mỗi nhà: có Binance USDT-M futures **L2 depth snapshots/incremental** +
   **trades** từ 2021-07 không; độ phân giải; universe (bao nhiêu symbol); giá theo tháng/theo GB; format (csv.gz/parquet);
   API/bulk download; giới hạn licence (dùng nội bộ nghiên cứu).
2. Ước lượng dung lượng: ~300 symbol × 4.5 năm; L2 full quá lớn — đề xuất **subset**: (a) trades đầy đủ (aggressor
   flag) cho toàn universe; (b) L2 top-20 level snapshot mỗi 1s hoặc 100ms chỉ cho ~60 symbol có lệnh nhiều nhất trong
   `printDone` của T170 + baseline (liệt kê 60 symbol đó từ printDone). Tính GB nén và chi phí lưu: **Oracle 26G KHÔNG đủ**
   → cần object storage (Oracle OCI bucket / Backblaze) + xử lý streaming ra feature 1m/5m rồi chỉ giữ feature.
3. Danh sách feature định sinh (để justify mua): order-flow imbalance 1m/5m/1h, depth imbalance top-5/top-20,
   spread & spread-vol, trade-size distribution, aggressive buy ratio, book-pressure trước pump, liquidation cluster
   (từ forceOrder nếu có), spot-perp basis (nếu mua thêm spot). Ghi rõ feature nào đã có bản thô lưới giờ (taker_buy,
   amihud) và vì sao bản fine-grained khác.
4. Kế hoạch dùng: sau khi có feature → pre-reg kiểu `PREREG_FS` (k = số feature, ngưỡng inflate(k), noise control chấm
   trên CONFIRM) — đo rank-IC/edge5 trước, sim sau.
**Đầu ra**: `docs/plan/PROPOSAL_MICROSTRUCTURE_DATA.md` (bảng so nhà cung cấp, subset đề xuất, GB, USD, nơi lưu, timeline,
feature list, rủi ro: licence, chất lượng dữ liệu, survivorship symbol đã delist). Commit. Uni quyết mua.

---

## TASK 4 — EVENT_FEATURES: token unlock, listing/delisting, leverage-tier · thu thập + pre-reg FS · 1-2 ngày · Sonnet

**Lý do**: 40 feature hiện có toàn là hình chiếu của giá/volume/funding/OI. Driver cấu trúc của pump/dump alt là SỰ KIỆN:
lịch unlock token (cung tăng ⇒ dump), listing/delisting sàn, thay đổi leverage tier/margin, funding cực trị chéo sàn.
Prior cao hơn feature lưới giờ vì là NGUYÊN NHÂN.

**Việc**
1. Nguồn lịch sử (miễn phí/rẻ trước): token unlock — DefiLlama `/unlocks` (có lịch sử), Cryptorank/TokenUnlocks (kiểm
   API/lịch sử tới 2021?); listing/delisting/leverage — Binance announcement archive (`binance.com/en/support/announcement`,
   crawl theo category, có ngày), `exchangeInfo` snapshot lịch sử nếu có trong `java/exchange_info_pin.json` + git history.
   Với mỗi nguồn: phủ tới năm nào, bao nhiêu symbol trong universe của ta khớp, độ chính xác timestamp (ngày hay giờ).
   **Leak check**: chỉ dùng thông tin công bố TRƯỚC thời điểm t (announcement date, không phải effective date).
2. Sinh feature ở lưới 15m/1h khớp `feat_v2_x1` (ts,sym): `days_to_next_unlock`, `unlock_pct_supply_next30d`,
   `days_since_listing`, `days_to_delisting_if_announced`, `lev_tier_change_7d`, `n_listings_mkt_7d` (mức thị trường).
   Ghi vào parquet riêng `featv2/feat_events_x1.parquet`, KHÔNG sửa `feat_v2_x1.parquet`.
3. Pre-reg `docs/PREREG_FS_EVENTS.md` theo khung `PREREG_FS`: thêm-1 vào KEEP-9, k = số feature, Δedge5 + Δrank-IC,
   block-bootstrap 72h, inflate(k), **đối chứng nhiễu chấm trên CONFIRM** (không SELECT), nested SELECT→CONFIRM. Chạy
   offline CPU Oracle (1 job/lần) hoặc Kaggle (so Kaggle-baseline). Dự đoán ghi trước.
**Đầu ra**: `docs/ops/EVENT_DATA_SURVEY.md`, `research/pipeline/x1/build_feat_events.py`, PREREG + RESULT. Nếu không nguồn nào
phủ trước 2023 ⇒ báo và dừng ở survey (không ép).

---

## TASK 5 — VOL_TARGET sizing: size ∝ 1/σ realized · code nhỏ + pre-reg · 1 ngày · Sonnet

**Lý do**: GS wave-1 (`docs/result/GS_WAVE1_RESULT.md`): trục duy nhất có ảnh hưởng là size/leverage, đổi DD lấy CAGR tuyến tính.
Vol-targeting làm size thích nghi theo σ realized của coin/danh mục — chuẩn ngành, chưa có trong sim. Không phải alpha;
kỳ vọng cải thiện DD/UW/độ đều equity ở cùng CAGR.

**Việc**
1. Recon: `BudgetManagerSimple.equityNow()`, `SIM_F_BASE` (default 0.03, `Configs.java:664`), `DCA_GRID_SCALE`,
   `CAPITAL_START`; xác nhận điểm tính notional lệnh và có knob nào đã là hàm của vol chưa (`grep -rn "vol\|sigma\|atr"`).
2. Thiết kế: `SIZE_VOL_TARGET_MODE=OFF|COIN|PORTFOLIO` default OFF (byte-identical `efb793e2`). COIN: notional ×
   (σ_ref / σ_coin_7d) kẹp [0.5, 2.0]; PORTFOLIO: scale toàn bộ theo σ_equity_20d → target vol năm cố định (tham số cố định
   trước, ví dụ 25%). σ tính từ `CLOSES_1H.bin` chỉ dùng dữ liệu ≤ t. k=2 (COIN, PORTFOLIO). Không quét hằng số.
3. Luật: như luật sim chung; thêm metric phụ: sd(return ngày), Calmar, độ lệch ROI theo quý (CV). Dự đoán MASTER:
   NULL ở rate chất lượng (đúng, vì sizing không đổi lệnh nào vào), cải thiện maxDD/UW/CV — ghi là "cải thiện rủi ro,
   không phải bằng chứng alpha".
**Đầu ra**: code flag + `docs/prereg/PREREG_VOL_TARGET.md` + `docs/result/RESULT_VOL_TARGET.md`. Cổng repro + OFF byte-identity bắt buộc.

---

## TASK 6 — SHADOW_T170 trung thực (quyết định vận hành của Uni, agent chỉ chuẩn bị)

Shadow 242 hiện chạy FLATGRID KEEPLEG0 (`DECISION_SHADOW_FLATGRID_KEEPLEG0.md`), KHÔNG phải T170 ⇒ không tích được
bằng chứng forward cho incumbent nghiên cứu. Cách duy nhất số cược độc lập tăng THẬT là forward.
**Việc agent**: đọc `docs/result/RESULT_SHADOW_T170_FIX.md`, `shadow_c3/app/conf/env.sh`, unit `shadow-c3.service`; soạn
`docs/plan/PLAN_SHADOW_T170_PARALLEL.md`: chạy **instance thứ hai** song song (`shadow_t170/`, redis riêng, port riêng,
`SHADOW_NO_PUSH=true`, env = đúng `profiles/x1_gs_t170.properties` md5 `efb793e2`, systemd riêng, log journald),
RAM/CPU thêm bao nhiêu (box còn ~12G khi rảnh, nhưng phải chừa cho sim -Xmx14g ⇒ có thể phải giảm Xmx sim xuống 10g
hoặc chạy shadow thứ hai trên máy khác), cách đo MTM định kỳ không ssh 242 (đọc sổ giấy trên Oracle). **KHÔNG deploy** —
Uni quyết. Kèm việc kiểm `-2014 API-key format invalid` (Uni cập nhật key).

---

## THỨ TỰ & PHỤ THUỘC
1. TASK 1 (read-only, quyết định hướng) — chạy ngay, không chờ gì.
2. Song song với TASK 1: TASK 3 (đề xuất, không compute) và TASK 4 bước 1 (survey nguồn).
3. Sau TASK 1: TASK 2 nếu nhãn BETA/HỖN HỢP; TASK 4 bước 2-3 nếu nguồn phủ đủ; TASK 5 bất kỳ lúc slot sim rảnh.
4. TASK 6 chờ Uni.
Slot sim Oracle chỉ 1 ⇒ TASK 2 và TASK 5 không chạy cùng lúc; offline (TASK 4) có thể đẩy lên Kaggle (so Kaggle-baseline).

## ĐIỀU KHÔNG LÀM
Không chạm HOLDOUT 2026 cho tới khi TASK 1 trả lời alpha/beta và Uni có pre-reg riêng. Không quét lại bất kỳ trục đã
đóng ở mục 0. Không so số Oracle với Kaggle. Không chạy 2 job nặng trên Oracle.
