# PARITY 1020 — 242 live vs backtest, cửa sổ shadow 2026-10-16 18:01 → 2026-10-20 15:36 (+07)

> **Trạng thái (2026-10-20): MASTER chấp nhận kết luận (P1 TRƯỢT / P2 ĐẠT-chưa-thử / P3 ĐẠT-độ-phân-giải-log); quyết định sửa (v1.1: chờ nến M settle đủ / sửa TreeMap trùng score + reset cửa sổ parity) chờ owner.**
>
> Bản lưu repo của `~/claude_master/parity_1020/summary.md` (nội dung giữ nguyên bên dưới). Script + JSON kết quả nhỏ copy tại `docs/result/parity_1020/`; raw242/, csv.gz lớn, jcls/ KHÔNG đưa vào repo (vẫn ở `~/claude_master/parity_1020/` trên Oracle).


Audit chỉ đọc (242 không bị ghi/restart). Agent thực thi, 2026-10-20.
Nguồn live: `feat_dump`/`sel_dump` 242 (tar đọc), `run/gate_ratio_live.bin` (cat đọc, chụp lúc 15:39, record cuối 14:52), log 242 đã lọc, `predictionSymbol/<ts>.features` (470 phút mẫu), model đọc từ 242 (md5 p15 8ec99757, net015 e65e683b, S1 511add62), jar live dc839568 = `~/src_wt_pxcache` (98e5b919).
Nguồn backtest: `devexport_1020.py --cluster 242 --md-inline --died-config raw242/died_242.properties` (bản 1016, thêm 3 cột rate offline), ONNX; S1/net015: `s1_off.py` tính lại từ dữ liệu settle Aerospike 242.
Cửa sổ: nến 10-16 18:00 → 10-20 15:36 = 5 616 phút feat_dump (offline có thêm 1 phút 10-16 19:59 mà live thiếu), sel_dump 134 760 cặp (24/phút).

## Bảng khớp từng chỉ số

| Chỉ số | n | khớp ≤1e-6·(1+|x|) | |Δ| median | |Δ| p99 | |Δ| max | rel median / p99 | corr |
|---|---|---|---|---|---|---|---|
| rateDownAvg | 5 616 | 99,16 % | 1,7e-10 | 2,1e-9 | 2,8e-5 | 1,3e-7 / 1,3e-6 | 0,9999994 |
| rateUpAvg | 5 616 | 99,31 % | 1,9e-10 | 1,5e-9 | 6,9e-5 | 1,3e-7 / 8,1e-7 | 0,9999976 |
| rateDown15MAvg | 5 616 | **45,5 %** | 3,7e-6 | 1,5e-4 | 5,0e-4 | 4,2e-4 / 2,0e-2 | 0,99995 |
| p15: model trên vector live vs p15_out live | 5 616 | 100 % | 3,8e-12 | 2,8e-9 | 5,6e-9 | — | 1,0 |
| **p15 live vs offline** | 5 616 | 34,2 % | 2,6e-5 | 2,3e-4 | 1,6e-3 | **3,3e-3 / 3,0e-2** | 0,99867 (Spearman 0,9982) |
| r = p15/(f·gs), gateValue live | 134 760 | 34,9 % | 5,6e-6 | 5,2e-5 | 3,9e-4 | 3,3e-3 / 3,0e-2 | 0,99913 |
| q_t log vs replay buffer (giờ) | 91 giờ có log / 94 | 91/91 khớp 6 chữ số | — | — | rel 6,7e-5 (= làm tròn %.6f) | — | — |
| S1 selectorScore (mode T = định nghĩa backtest feat_v2) | 11 256 (469 phút) | 41,7 % (bằng float32) | 2,4e-3 | 0,26 | 0,74 | 7,7e-3 / 2,2 | 0,987 |
| S1 (mode E35 = giả lập OI có trễ 35') | 11 256 | 59,2 % | 4,5e-10 | 0,25 | 0,74 | 1,8e-9 / 1,4 | 0,991 |
| Hạng top-24: Jaccard (T / E35) | 469 phút | =1 ở 56,5 % / 70,9 % | mean 0,960 / 0,972 | min 0,778 | | | |
| Hạng: Spearman rank live vs offline (T / E35) | 469 | | mean 0,978 / 0,983 | min 0,68 / 0,69 | | hạng đúng y: 58,4 % / 67,2 % | |
| net015 gateValue: live ∈ {1−P(win) tính lại trên float[45] live} | 11 256 | **99,98 %** (2 dòng không thấy) | | | | | |
| net015 gateValue với thứ tự S1 offline (T / E35) | 11 256 | 56,7 % / 66,1 % | 0 | 0,030 / 0,028 | 0,073 | 0 / 9,2 % | 0,984 / 0,988 |

Feature gate (33): BTC-only (momentum1M..24H trừ 15M, volatility*, rsi14, volumeSpike, distMA20, lịch, trendStrengthETH) khớp ≥ 99 %. Lệch gần như MỌI phút: họ breadth (advanceDeclineRatio rel median 2,3 %, percentAboveMA20 1,1 %, marketBreadthStrength 1,7 %, volumeRatioUpDown 0,14 %, btcDominance 0,15 %; khớp 0,02–0,3 %), basket (basketMomentum15M/1H, basketRsi14, basketVolSpike; khớp 0–1,8 %), funding×3 (khớp 11–21 %), momentum15M/momentumAcceleration (= rateDown15MAvg; 45,5 %). Lệch không phải lệch phút: dịch ±1/±2 phút làm khớp tệ hơn nhiều.

## Kết luận theo prereg (ii')

- **P1 (p15) — TRƯỢT.** rel median 3,31e-3 (ngưỡng ≤ 1e-4); ≤ 1e-3 ở 36,7 % phút (ngưỡng ≥ 98 %). Theo ngày: 10-16 (18–24h) median 1,7e-7 / 60 % · 10-17 4,1e-3 / 33 % · 10-18 4,9e-3 / 28 % · 10-19 2,4e-3 / 42 % · 10-20 3,1e-3 / 39 %. Tới 10-17 02h gần như khớp; từ 10-17 03h lệch liên tục.
- **P2 (lật gate nặng = 0) — ĐẠT, nhưng chỉ vì thị trường xa ngưỡng.** 0 PASS live, 0 PASS offline, 0 cặp lật (134 760 cặp; cả biến thể "backtest đầy đủ" 11 256 cặp: p15 offline + gateValue map theo S1 offline: 0 lật). max r/q live 0,819, offline 0,813 (10-18 04:39); biến thể đầy đủ 0,716. Log `[GATE]` 5 620 dòng: n_cand=24, n_pass=0, n_skipfull=0, u max 0,0355. Với sai số p15 p99 3 % và ngưỡng thực lệch tới 25 % (gateValue lệch), P2 chưa được thử ở phút gần ngưỡng.
- **P3 (q_t) — ĐẠT ở độ phân giải log; tiêu chí 1e-6 không kiểm được từ log.** Replay causal (`GateRatioBuffer`: q tính 1 lần đầu mỗi giờ trên record ts ∈ [h−90d, h); giờ có restart: gồm cả record trong giờ trước restart) khớp 91/91 giờ có log ở 6 chữ số (q 0,007228 → 0,007175). Log in `%.6f` ⇒ sai số làm tròn tương đối tới ~7e-5 nên không thể kiểm 1e-6. r của sel_dump (κ·p15/gateValue, float32) có mặt BIT-EXACT trong buffer ở 100 % cặp trước thời điểm chụp file (1 032 cặp sau 14:52 chưa flush, đúng kỳ vọng). ⇒ Buffer/quantile/công thức r live = replay.

## Phút lệch nặng (p15 rel lớn nhất) + nguyên nhân

| phút | p15 live | p15 offline | rel | advDecl l/o | pctMA20 l/o | mbs l/o |
|---|---|---|---|---|---|---|
| 10-16 20:30 | 1,6641 % | 1,5045 % | 10,6 % | 0,832/0,802 | 0,409/0,398 | 0,417/0,407 |
| 10-16 20:51 | 1,6264 % | 1,5193 % | 7,1 % | 0,430/0,424 | 0,133/0,127 | 0,278/0,274 |
| 10-19 04:01 | 0,6426 % | 0,6887 % | 6,7 % | 13,30/14,57 | 0,870/0,881 | 0,903/0,908 |
| 10-20 05:56 | 0,4725 % | 0,5024 % | 5,9 % | 1,486/1,575 | 0,361/0,377 | 0,495/0,482 |
| 10-17 05:51 | 0,5116 % | 0,5415 % | 5,5 % | 0,341/0,347 | 0,551/0,569 | 0,211/0,206 |
| 10-17 04:15 | 0,6961 % | 0,7350 % | 5,3 % | 3,86/3,91 | 0,750/0,756 | 0,697/0,699 |
| 10-18 04:06 | 0,6525 % | 0,6853 % | 4,8 % | 0,638/0,659 | 0,710/0,732 | 0,299/0,304 |
| 10-17 14:27 | 0,9060 % | 0,8670 % | 4,5 % | 0,570/0,510 | 0,278/0,257 | 0,300/0,276 |
3 556/5 616 phút có rel > 1e-3, rải đều mọi phút-trong-giờ (50–68 phút mỗi giá trị). 60 phút xấu nhất: `par_a.json` → `P1_bad_minutes`.

Nguyên nhân (đo được):
1. Hoán đổi nhóm feature (thay nhóm offline vào vector live): mỗi nhóm một mình đã gây rel > 1e-3 ở breadth 35,9 %, basket 31,0 %, momentum15M 15,0 %, funding 7,5 % số phút; momentum1M ≈ 0. Nhóm lệch đều là feature **chéo nhiều coin** (rổ top-50 % theo volume 720', MA20 từng coin, high 15' mọi coin, funding giỏ). Feature chỉ dựa trên BTC thì khớp.
2. Dữ liệu phút live chưa đủ lúc tính: collector chốt nến ở giây ~4 với chỉ ~290–340/738 symbol (thiếu ~410–450) ở 22 % phút ngày 10-16 rồi 53–67 % phút từ 10-17 — trùng với lúc P1 bắt đầu lệch (10-17 03h). p15 rel median: phút đủ 2,4e-3 / phút thiếu 4,2e-3. Phần lệch ở cả phút đủ là do lịch sử live (ring HistoryManager, MA20, hạng CoinRankManager tính lại mỗi giờ trên **snapshot phút hiện tại** — `getAllSymbols()` = khoá snapshot cuối) đã được nạp từ các phút thiếu. Offline đọc bản đã settle (738 symbol mọi phút; kiểm lại trực tiếp ở 5 phút thiếu: Aerospike nay có 738). Suy ra kích thước rổ breadth live dao động ~330–365 so với 369 offline (suy từ mẫu số mbs/pma, nhiễu).
3. Không do restart (rel theo giờ-kể-từ-restart 0–1h 3,2e-3 … 9–12h 4,3e-3), không do lệch phút, không do model/thứ tự feature (model trên vector live khớp 5,6e-9).
Cùng cơ chế với §6 SHADOW_PARITY_FEAT_1016 (dữ liệu chưa settle lúc tick), nhưng lần này nằm trên chính 242.

## S1 / net015 — chi tiết

- Universe từng phút mẫu = khoá `predictionSymbol/<ts>.features` (aiCandidates, median 676). 470 phút mẫu (:00/:15/:30/:45 và :02); bỏ 10-20 15:45 vì sel_dump kết thúc 15:36.
- Tỷ lệ khớp S1 giảm theo phút-trong-giờ (E35: :00 63 % → :45 54 %; S (OI settle) 44 % → 28 %). Đây là dấu vết OI: live nạp OI 1 lần/giờ lúc đầu giờ, điểm OI 5' về Aerospike trễ ~25–35'. Giả lập trễ nâng khớp 38 % → 59 %. Nhưng thử mọi điểm OI trong [now−2h, now] cho từng (phút, coin) lệch chỉ cứu được 41/561 (7 %). Phần còn lại không tái lập được offline, có thể do: giá trị OI bị ghi lại sau (writer merge-tích-luỹ), hạng chéo `rk_*` kéo theo khi nhiều coin lệch, close 1h nạp lúc chưa settle. Live không dump 9 feature S1 nên chưa khoanh được.
- Coin lệch hạng lặp lại: live có mà offline không (STBLUSDT, DUSKUSDT, NXPCUSDT, MAGICUSDT, EDUUSDT); offline có mà live không (BTWUSDT, AVAUSDT, SNXXUSDT, BSPUSDT).
- **Phát hiện code:** `buildS1Pool` dùng `TreeMap<Float,String>` khoá theo score ⇒ coin trùng score bị mất. Mất median 9, max 22 coin/phút; 452–454/470 phút có ít nhất một coin bị mất. `selectorRankPool` khoá theo tier1Score cũng có rủi ro tương tự. Coin nào được giữ phụ thuộc thứ tự HashMap ⇒ không tất định, backtest không tái lập được. Chưa kiểm coin bị mất có nằm ở vùng top-24 hay không.
- **net015:** P(win) tính lại bằng Python ORT trên chính mảng float[45] live. gateValue live trùng đúng một phần tử {1−P(win)} ở 99,98 % dòng ⇒ model net015, thứ tự 45 feature và quantile-map live = offline. Lệch gateValue (34–43 % dòng) hoàn toàn do thứ tự S1. **CHƯA ĐO:** 45 feature funding so với backtest. Muốn đo cần một harness Java tính lại FundingFeatureExtractor (40 Tool1 + 5 OI) trên dữ liệu settle 242 cho cửa sổ, hoặc tool export train `ExportFeaturesForPythonTool`.

## Hàm ý / việc đề xuất cho MASTER
1. P1 TRƯỢT ⇒ theo prereg, đường promote phải dừng ở (ii') cho tới khi sửa. Hướng sửa: live chờ nến M settle đủ (ví dụ Total = universe hoặc +X s), hoặc tính feature chéo trên bản đọc lại. Cũng cần quyết backtest có nên mô phỏng đúng trễ dữ liệu live hay không.
2. P2 hiện ĐẠT nhưng chưa có phút gần ngưỡng. Nên giữ đo tiếp tới khi có đợt sập; khi đó dùng tập phút có r/q ≥ 0,9.
3. P3: đề nghị log q_t với `%.9g` (hoặc dump q mỗi giờ) để kiểm được 1e-6. Không đổi logic.
4. S1: thêm dump 9 feature S1 + thời điểm nạp OI (sau cờ) để khoanh 41 % dòng lệch. Sửa TreeMap trùng score (v1.1), vì đây là lệch tất định-vs-không-tất định với backtest.

## File (tất cả trong ~/claude_master/parity_1020/)
- Script: `devexport_1020.py`, `par_a.py` (rates/p15/gate/P3), `s1_off.py` + `Pa1020Feat.java`/`jcls` (S1/net015), `par_c.py` (gate backtest đầy đủ), `diag1.py` (hoán nhóm/lag), `diag2.py` (cỡ rổ), `diag3.py` (collector thiếu), `diag4.py` (restart), `diag5.py` (OI ref), `fetch_psym.py`.
- JSON: `par_a.json`, `par_b.json`, `par_c_fullbt_gate.json`, `diag1.json`, `diag4.json`, `diag5.json`. Theo phút: `out_minute_p15_rates.csv.gz`, `out_minute_collector.csv.gz`, `out_sel_gate.csv.gz`, `out_s1_{S,E25,E35,T}.csv.gz`, `out_s1min_*.json`, `feat45_live.csv.gz`.
- Raw (chỉ đọc từ 242): `raw242/` (dumps, gate_ratio_live.bin, loglines.gz, collector_settle.gz, psym/, models/, legacy_symbols.csv, died_242.properties chỉ dòng DIED_SYMBOLS).
