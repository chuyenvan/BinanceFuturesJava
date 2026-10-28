# HO2026_TRADFI_AUDIT — TradFi perps và INDEX trong backtest HOLDOUT 2026 (2026-10-28)

Phạm vi: CHỈ ĐỌC/ĐO. Không chạy lại sim, không tune, không gọi Binance API, không ssh 242. Dữ liệu dùng: printDone đã có trên Oracle (`~/kaggle_sim/out/{ho4-*,tsx-ho-*,ecm-h-*}`), code kernel dựng dữ liệu HO4-P1 (`~/claude_master/1011/ho4p1/kaggle/ho4p1-x26-q*/run.py`), exchangeInfo dump `v12/fixtures/exchangeInfo_20261027_1140.json.gz` (936 symbol), manifest Vision `~/vz/manifest/kline1m.csv.gz`, Binance Vision monthly kline 1m (data.binance.vision, tải trong bộ nhớ, không lưu zip), log pull242 10-18..10-27.
Script/artefact (ngoài repo): `~/claude_master/ho_tradfi_wk/{a1.py,a1b.py,a2.py,a3.py,a4.py}` → `classes.json, a1.json, a1b.json, a2/*.npz, a2/day_*.json, a3.json, a4.json, legs_tf_*.csv`.
Giờ: printDone `start` = UTC+7; mọi phép theo phút/ngày dưới đây = UTC (đã trừ 7h). Cửa sổ HO: W9 = start ∈ [2026-01-01, 2026-10-01) +07; H1 < 2026-07-01 +07; Q3 phần còn lại.

## 0. TL;DR (rủi ro trước)

| # | Phát hiện | Số chính | Độ tin |
|---|---|---|---|
| T1 | **Mọi run HO 2026 (HO4 32 run, ECMEAS-H 8, TS_MKT_EXT X14 HO 8+P0, GOLIVE_QUARTERLY 2026) đều CÓ TradFi** trong universe giao dịch VÀ trong mọi feature thị trường. Không có bộ lọc TradFi/INDEX nào ở dữ liệu, sim, hay chỉ số ALT_EW | TF trong data sim theo tháng: 6 (T1) → 13 → 20 → 32 → 60 → 111 (T6) → 150–151 (T7–T9); giao dịch được: tới 134–135 (T7–T9) | XÁC MINH |
| T2 | **Leg TradFi trực tiếp ăn lỗ ở H1, lãi nhỏ ở Q3** | k24-s W9: 238/3 635 leg (6,5 %), PnL TF −6 084 (−760/seed; −8,2 % ΣPnL realized). H1 −941/seed. Q3: 17 leg (1,3 %), +181/seed. X14: W9 −796/seed, Q3 +261/seed | XÁC MINH (realized theo start) |
| T3 | Tập trung: **69 % leg TF rơi vào 2026-06-02..05** (163/238, −7,9k); ASTSUSDT riêng −2,65k (44 % net TF). Win-rate leg TF 50–52 % vs crypto 84–86 % | 34 symbol TF có leg | XÁC MINH |
| T4 | **Gián tiếp — cờ X14 đổi:** bỏ TF (và TF+INDEX) khỏi ALT_EW ⇒ **thêm 3 ngày cờ tháng 6 (06-06, 06-07, 06-10)**; 14 ngày cờ tháng 2 KHÔNG đổi (lệch dd −0,1..−0,28 pp) | 15 → 18 ngày cờ 2026; ALT_EW tái dựng khớp `ew_2026.npz` max\|Δ\| 4,9e-17 trên 437 750 phút | XÁC MINH (dữ liệu); tác động PnL CHƯA XÁC MINH |
| T5 | Gián tiếp — market level sim (proxy `calMarketData`): `rateChangeUpAvg` lệch trung vị 3,5 bp (≈19 % tương đối) ở phút vào lệnh; `rateChangeDownAvg` lệch 0,08 bp (0,1 %). Nến TF phẳng ngoài giờ (qv=0) có trong ticker sim: trung vị 35–73 nến phẳng/phút ở T6–T9 | lệch tăng dần theo số TF: T1–T4 ≤0,03 bp trung vị; T6–T9 0,4–0,9 bp | CHƯA XÁC MINH (proxy, chưa đối chiếu market.bin; chưa đo gate store breadth) |
| T6 | **Live shadow v1.1 (242, jar dcae2e2b = `v1.1/exec-probe` 16de49a6) CÓ TradFi** ở universe, S1, market feature, ALT_EW; đã mở UNITREEUSDT + IBKRUSDT (10-24), đóng SNPSUSDT (10-22) | S1 dump: 206–227 TF / 722–742 symbol (~30 %) | XÁC MINH (code + log); config override trên 242 CHƯA XÁC MINH |
| T7 | **Lệch backtest↔go-live:** gói go-live c3_live (v1.2) loại TF + INDEX khỏi universe VÀ feature (universe 513); toàn bộ bằng chứng HO 2026 tính trên universe có TF. Ngoài ra backtest chỉ thấy TF nằm trong mapper 863 (151/228), live v1.1 thấy ~223 TF ⇒ v1.1 shadow cũng ≠ backtest | — | XÁC MINH |

Kết luận: **verdict HO 2026 không đổi dấu chỉ vì leg TF** (W9/H1 E0 PASS vẫn dư nhiều; Q3 FAIL còn tệ hơn chút khi bỏ TF). Nhưng các con số go-live (ROI W9, Q3, ΔX14) là của universe khác universe sẽ chạy. Ước lượng thô (bỏ leg TF, không thay thế slot): W9 ROI k24-s +0,7 pp, X14 +0,6 pp; Q3 tệ thêm ~0,2 pp. Tác động gián tiếp (3 ngày cờ X14 tháng 6, market feature, gate p15, slot/vốn được giải phóng) **chưa đo được nếu không chạy lại** ⇒ đề xuất PREREG §7.

## 1. Universe mà sim dùng cho 2026 (Task 1)

| Run | Dữ liệu 2026 | Lọc universe | Lọc TradFi/INDEX |
|---|---|---|---|
| `ho4-{b0,k24}-{b,s}-s*` (32 run, HO4_RESULT_A/B: W9/H1 E0 PASS 8/8, Q3 E0 FAIL) | ticker ngày UTC dựng trong kernel `ho4p1-x26-q{1,2,3}` từ Vision monthly 1m (`run.py:74-96`), dataset `ho4p1-tk26` (273 ngày, md5 `docs/result/ho4/ho4p1_arts26.json`) | `run.py:69-73` `in_uni`: Vision listing ∩ đuôi `USDT` ∩ `^[A-Z0-9]+$` ∩ ∉ {BTCDOMUSDT, USDCUSDT} ∩ mapper 863 (PREREG_HOLDOUT2026H1 ADDENDUM-6 §6.2-1, dòng 280). Bỏ đuôi settle qv=0 ≥1 440 phút (`run.py:115-127`) | **Không có.** Chỉ 16 symbol id mapper trùng (843–850, **cả 16 là TF**) bị loại khỏi giao dịch nhưng vẫn ở market/gate (ADDENDUM-6, dòng 324-326) |
| `ecm-h-s*` (ECMEAS H, merge 5fab95af) | y artefact HO4-P1 (`RESULT_ENTRYCOST_MEASURE.md:17-22`) | như trên | Không |
| `tsx-ho-x14-s*` + `tsx-ho-p0-s42` (TS_MKT_EXT HO W9 CONFIRM, 46ebc1ee) | bundle HO4 (P0 md5 = `ho4-k24-b-s42` 7cc8864c, TS_MKT_EXT_HO V2); cờ 2026 từ ALT_EW `ew_out/ew_2026.npz` | ALT_EW: `edge_attr_build.py:111-121` `build_index`: MỌI symbol trong parquet `vz-kline1m-2026` (= toàn bộ Vision USDT: 629 → 869 symbol, khớp manifest từng tháng), chỉ bỏ BTC/ETH, qv>0 cả hai nến, clip ±0,5 | **Không** (ALT_EW còn gồm cả TF ngoài mapper, BTCDOM/ALL/DEFI, USDC, tên non-ASCII) |
| GOLIVE_QUARTERLY 2026 (61ac2b87) | printDone `tsx-ho-x14-s*` (`research/golive_quarterly/quarterly.py:258,262`) | như X14 | Không |

Sim (jar b7c89f09 / cc0f9d11): universe tại phút t = mọi symbol có record trong ticker (SYMLIFE_AUDIT §3, `SimulatorMarketLevelTicker1MStopLoss.java:216-233`); `DIED_SYMBOLS=BTCDOM,USDC`. `MarketBigChangeDetector.calMarketData` chỉ bỏ `died`, rc>0,3 và rc<−0,15 khi BTC>−0,4 % — **không lọc qv=0**, nên nến TF phẳng ngoài giờ (rc=0) vào snapshot (TreeMap khoá = rc nên các số 0 gộp thành 1 khoá).

## 2. Phân loại và số lượng (Task 2)

Luật phân loại = `TradFiClassifier` (`v12/c3live/.../universe/TradFiClassifier.java:66-77`): TF ⇔ `contractType` chứa TRADIFI/TRADFI hoặc `underlyingType` ∉ {COIN, INDEX, PREMARKET}; INDEX ⇔ `underlyingType=INDEX`. Dump 10-27: 229 `TRADIFI_PERPETUAL` (228 USDT: EQUITY 190, HK_EQUITY 15, COMMODITY 8, KR_EQUITY 8, PREMARKET 4, CN_EQUITY 2, FX 1); INDEX = ALLUSDT, BTCDOMUSDT, DEFIUSDT (SETTLING). PREDICTUSDT (PREMARKET, PERPETUAL) = crypto. Đầy đủ 2026: mọi symbol niêm yết từ 2025-12 trong lifecycle SYMLIFE đều có trong dump (0 thiếu) ⇒ không có TF đã delist bị sót (XÁC MINH). onboardDate TF: 2025-12: 1, T1 4, T2 7, T3 7, T4 12, T5 28, T6 51, T7 39, T8 30, T9 33, T10 16.

| Tháng | Vision USDT | TF trên Vision | TF trong data sim (∩ mapper) | TF giao dịch được (−16 id trùng) | INDEX trong data sim | TF có ≥1 phút trade/ngày (trung vị / max) | TF % thành viên ALT_EW (TB / max phút) | TF nến phẳng (qv=0) % dòng |
|---|---|---|---|---|---|---|---|---|
| 2026-01 | 629 | 6 | 6 | 6 | 2 (ALL, DEFI) | 2 / 5 | 0,4 % / 1,0 % | 33 % |
| 2026-02 | 641 | 13 | 13 | 13 | 2 | 12 / 12 | 1,6 % / 2,5 % | 16 % |
| 2026-03 | 656 | 20 | 20 | 20 | 2 | 14 / 19 | 2,3 % / 3,9 % | 10 % |
| 2026-04 | 672 | 32 | 32 | 32 | 2 | 28 / 31 | 4,2 % / 6,0 % | 12 % |
| 2026-05 | 704 | 60 | 60 | 60 | 2 | 42 / 59 | 6,6 % / 10,5 % | 11 % |
| 2026-06 | 761 | 111 | 111 | 111 | 2 | 100 / 110 | 11,5 % / 17,4 % | 21 % |
| 2026-07 | 801 | 150 | 150 | 134 | 2 | 133 / 149 | 13,9 % / 23,0 % | 26 % |
| 2026-08 | 833 | 180 | 151 | 135 | 2 | 150 / 150 | 15,6 % / 25,2 % | 27 % |
| 2026-09 | 869 | 213 | 151 | 135 | 2 | 150 / 150 | 17,0 % / 27,8 % | 26 % |
| W9 / H1 / Q3 | | | | | | 42 / 22 / 150 (trung vị) | 8,2 / 4,4 / 15,5 % | |

- 62 TF bị loại vì thiếu mapper (`ho4p1_excl26.json` excluded_no_mapper 68 = 62 TF + 6 crypto). Mapper 863 chứa 151 TF + ALL/BTCDOM/DEFI (BTCDOM bị DIED).
- "Lọc tradeable" của sim chỉ là có ticker + có điểm predict (bins/pool S1); L24 = rank TOPK 24 trong `getTopSymbolArray`, không có ngưỡng thanh khoản riêng loại TF. Pool S1/bins 2026 không có trên Oracle ⇒ số TF có điểm predict mỗi ngày: CHƯA XÁC MINH; cột "≥1 phút trade" là cận trên.
- Vào feature thị trường: (a) ALT_EW/X14: mọi TF trên Vision (6 → 213) + 3 INDEX; (b) `calMarketData`/market.bin + gate store breadth/basket (p15): TF trong data sim (6 → 151, gồm 16 id trùng) + ALL/DEFI; (c) Tool1/net015/bins: TF trong data trừ 16 id trùng.

## 3. Leg và PnL realized trên TF/INDEX (Task 3)

Nguồn `a1.json`, `a1b.json`. PnL = cột `pnl` printDone, gán cửa sổ theo `start` (+07). Đây KHÔNG phải ΣPnL MTM của scorer A (scorer tính equity MTM trong cửa sổ) — dùng để đo tỉ trọng, không thay số verdict. **0 leg INDEX** ở mọi run.

| Run (8 seed gộp) | Cửa sổ | Leg TF / tổng (%) | notional % | PnL TF | PnL TF / seed | ΣPnL realized tổng |
|---|---|---|---|---|---|---|
| ho4-k24-s (HO4 bản chính) | W9 | 238 / 3 635 (6,5 %) | 5,3 % | −6 084 | −760 | 74 096 |
| | H1 | 221 / 2 333 (9,5 %) | 8,1 % | −7 530 | −941 | 76 743 |
| | **Q3** | **17 / 1 302 (1,3 %)** | 1,0 % | **+1 446** | **+181** | −2 647 |
| ho4-k24-b | W9 / H1 / Q3 | 236 / 220 / 16 | 5,3 / 8,2 / 0,9 % | −8 183 / −10 229 / +2 046 | −1 023 / −1 279 / +256 | 118 060 / 110 754 / 7 306 |
| ho4-b0-s | W9 / H1 / Q3 | 103 / 100 / 3 | 3,4 / 5,2 / 0,3 % | −4 920 / −4 991 / +72 | −615 / −624 / +9 | 54 357 / 59 558 / −5 201 |
| ho4-b0-b | W9 / H1 / Q3 | 102 / 99 / 3 | 3,4 / 5,3 / 0,3 % | −6 211 / −6 305 / +94 | −776 / −788 / +12 | 85 600 / 87 057 / −1 457 |
| ecm-h (ECMEAS H) | W9 / H1 / Q3 | 236 / 220 / 16 | — | −8 468 / −10 258 / +1 790 | −1 058 / −1 282 / +224 | 108 687 / 109 156 / −469 |
| **tsx-ho-x14 (TS_MKT_EXT, GOLIVE)** | W9 / H1 / **Q3** | 236 / 220 / **16** (6,5 / 9,5 / 1,2 %) | 5,3 / 8,3 / 0,9 % | −6 367 / −8 458 / **+2 091** | −796 / −1 057 / **+261** | 144 844 / 137 427 / 7 417 |

Theo tháng (k24-s; leg TF / PnL TF): T1 6 / −437; T2 27 / +2 580; T4 5 / −181; T5 6 / −1 162; **T6 177 / −8 330**; T7 13 / +1 394; T8 4 / +52; T9 0. X14 tương tự (T6 177 / −10 296; T2 27 / +3 604; T7 12 / +2 016).
- Ngày dày nhất (cả 3 cấu hình k24/X14/ECM): 06-02 64 leg (8 symbol), 06-04 46, 06-03 29, 06-05 24 ⇒ **163/238 = 69 % leg TF trong 4 ngày**, PnL −7,9k (k24-s) / −9,7k (X14). Symbol lớn nhất: ASTSUSDT −2 652 (k24-s), −3 764 (X14) ≈ 44–59 % net TF; còn lại phân tán trên 34 symbol (NOK, SAMSUNG, FLNC, HYUNDAI, EWT, ONDS, CBRS lỗ; HOOD, BBX, LLY, XPD, AAOI lãi).
- Q3: chỉ 16–17 leg TF (cụm 2026-07-31 20:46 +07: AAOI, AXTI, FLNC…), win 87,5 %, gần như toàn lãi (+1,4..+2,1k gộp). Bỏ TF trực tiếp làm Q3 tệ hơn ~180–260/seed; **Q3 E0 FAIL không đổi** (k24-s scorer A mean −2 420, 1/8 seed > 0).
- Theo seed (k24-s, PnL TF W9): −252 … −1 400, cả 8 seed âm; X14: 7/8 âm (s777 +62).
- ΔX14 (x14 − k24-b) phần đến từ leg TF: (−6 367) − (−8 183) = +1 816 gộp = +227/seed ≈ 7 % của ΔX14 W9 (+3 348/seed).
- Ước lượng thô "bỏ leg TF, không thay slot" (CHƯA XÁC MINH — bỏ qua slot/vốn được giải phóng, path dependence lãi kép): W9 k24-s +760/seed ≈ +0,7 pp ROI (E0 ≈ 104k); X14/GOLIVE +796/seed ≈ +0,6 pp (E0 ≈ 143k); Q3 −0,2 pp.

## 4. Tác động gián tiếp (Task 4)

### 4.1 ALT_EW và cờ X14 (XÁC MINH phần dữ liệu)
- Tái dựng ALT_EW từ Vision (cùng luật `logret/build_index`) cho 2025-12..2026-09: **khớp `ew_2026.npz` 437 750/437 750 phút, max\|Δ\| 4,9e-17** (V). 2025-10..11 giữ nguyên từ `ew_2026.npz` (TF ≈ 0).
- Biến thể: noTF (bỏ 228 TF), noTFIDX (bỏ thêm ALL/BTCDOM/DEFI). Luật cờ y nguyên (EOD ≤ −30 % so max EOD 31 ngày ⇒ cờ ngày d+1).

| Biến thể | Số ngày cờ 2026 | Khác so với baseline | dd min 2026 |
|---|---|---|---|
| ALL (= ho_flags.json, 15 ngày) | 15 | — | −40,16 % (02-05) |
| noTF | 18 | **+06-06, 06-07, 06-10**; 0 ngày mất | −40,32 % |
| noTFIDX | 18 | như noTF | −40,40 % |

- Tháng 2 (đợt sập duy nhất tạo CONFIRM): TF chỉ 1,6 % thành viên, lệch dd trên ngày cờ −0,09..−0,28 pp ⇒ **14 ngày cờ tháng 2 vững**.
- Tháng 6: TF ~11,5 % thành viên, cổ phiếu ít biến động làm ALT_EW đỡ giảm; dd 06-05..06-10 lệch −1,6..−1,9 pp, đẩy 3 ngày qua ngưỡng −30 %. Log-level EOD lệch tích luỹ: T6 −4,0 %, T9 +2,5 % (TF làm ALT_EW "cao" hơn trong T5–T7, "thấp" hơn T9).
- Hệ quả: nếu go-live loại TF khỏi ALT_EW (c3_live `MarketIndexFilter`), X14 sẽ hoãn time-stop thêm ở đầu tháng 6 — đúng tuần có cụm leg TF lỗ và nhiều leg crypto (T6 1 149 leg). Dấu tác động PnL: CHƯA XÁC MINH (cần rerun §7).
- Nến phẳng ngoài giờ: ALT_EW đã tự loại (qv>0 cả hai nến), nên méo ALT_EW chỉ đến từ TF trong giờ giao dịch (beta thấp với crypto), không từ nến phẳng.

### 4.2 Market level của sim (`calMarketData` → market.bin / gate) — proxy, CHƯA XÁC MINH
Tái hiện `rateChangeDownAvg`/`rateChangeUpAvg` (TreeMap khoá=rc, 100 khoá đầu, period ≤ size·4/5, bỏ rc>0,3 và rc<−0,15 khi BTC>−0,4 %) trên universe sim (in_uni), so ALL với noTF:
- Trung vị \|Δ\| theo tháng: T1–T4 ≤ 0,03 bp; T5 0,17 bp; T6 0,58; T7 0,87; T8 0,58; T9 0,38 bp; p99 tới 9–13 bp ở T6–T9; max 73–178 bp.
- Ở 193 phút vào lệnh (ho4-k24-s): down100 lệch trung vị 0,08 bp (0,1 % tương đối); **up100 lệch trung vị 3,5 bp (19 % tương đối), p90 17 bp** (H1 3,3 bp, Q3 4,4 bp). Lý do: trong phút sập, ít symbol tăng ⇒ TF (đứng yên/không theo crypto) chiếm chỗ trong top-100 tăng.
- Nến TF phẳng (rc=0, qv=0) trong snapshot sim: trung vị 1–3/phút (T1–T3), 35 (T6), 60–73 (T7–T9). TreeMap gộp chúng thành 1 khoá nên ảnh hưởng `calMarketData` nhỏ; nhưng các feature ĐẾM symbol (gate store 33 V3FULL: advanceDecline, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, basket) sẽ đếm từng nến phẳng — chưa đo (cần code ExportGateDataset + dữ liệu), CHƯA XÁC MINH.
- Không đo `rateDown15MAvg` (cần max giá 15′) và p15 (cần chạy lại predict) — CHƯA XÁC MINH.

Đánh giá cỡ: tháng 1–4 (gồm đợt sập T2) gần như không bị TF chạm ở market level; méo tăng mạnh từ T5, lớn nhất Q3 (TF 15–17 % thành viên, 26 % dòng phẳng). Q3 là quý FAIL và cũng là quý feature bị TF làm méo nhiều nhất ⇒ không loại được giả thuyết TF góp phần vào Q3 xấu qua gate/feature (chỉ rerun mới trả lời).

## 5. Live parity (Task 5)

- Jar đang chạy 242: `dcae2e2bbb1a357bc15703b416d4dccb` (`deploy/deploy_dcae2e2b.sh:16`; V11C_DEPLOY_1021 dòng 406) = v11d 7767a560 + exec-probe (`exec_probe/verify/jarcmp.json`: khác 3 class ShadowBookC3/DES + ExecProbe*). Nguồn: worktree `~/claude_master/exec_probe/wt`, branch `v1.1/exec-probe` @16de49a6.
- Code nhánh đó: universe = `/fapi/v1/ticker/price` + `endsWith USDT && ^[A-Z0-9]+$ && !diedSymbol` (`TickerIngestor2AerospikeNew.java:134,517`); market feature `LIVE_MD_DIED_SYMBOLS` mặc định `BTCDOM,USDC` (`LiveFeaturePipeline.java:37-39,171`); ALT_EW live `AltEwIndex.java:108,139-142` chỉ bỏ BTC/ETH. **Không có lớp TradFiClassifier/MarketIndexFilter** (grep 0; chỉ có cảnh báo lỗi −4411 TradFi agreement ở `OrderHelper.java:66-68`).
- Log pull242 (không ssh 242): S1 dump 10-21..10-27: 206–227 TF / 722–742 symbol (~30 %), có ALLUSDT (INDEX). `[PREDICT]` top-24: TF chiếm 5–19 % tên theo ngày (10-18 19 %, 10-25 5 %). `[SHADOW] open` 10-24: 25 lệnh, 2 TF (UNITREEUSDT, IBKRUSDT); `[SHADOW] closed` SNPSUSDT (TF) 10-22 −5,5 (TIME_STOP_168H), UNITREEUSDT 10-26 +8,9 (TRAILING_STOP).
- ⇒ **v1.1 shadow hiện có TF ở universe, S1, market feature và ALT_EW** — cùng "loại" với backtest HO 2026, nhưng tập TF rộng hơn (≈223 so với ≤151 trong mapper 863) và không loại 16 id trùng. Gói go-live c3_live (`v1.2/c3-live` a5946799: `SymbolUniverseLive.java:23,194-196` loại TRADFI và INDEX; `C3LiveHook.excludeTradFiFeatures`, `DetectEntrySignal2TradeNormal.java:880,1571-1572`, `C3LiveRuntime.java:287` MarketIndexFilter) loại TF + INDEX khỏi cả universe lẫn feature. Ba thế giới: backtest HO (TF ≤151, có trong feature) ≠ shadow v1.1 (TF ~223) ≠ go-live c3_live (0 TF, 0 INDEX).
- CHƯA XÁC MINH: giá trị thật của `LIVE_MD_DIED_SYMBOLS`/`DIED_SYMBOLS` trên 242 (không đọc config 242; luật cứng).

## 6. Giới hạn
1. PnL theo leg là realized gán theo `start`; scorer A tính MTM trong cửa sổ ⇒ tỉ trọng chỉ là mô tả, không thay verdict.
2. "Bỏ leg TF" bỏ qua thay thế slot (TOPK 24, quota gate), vốn giải phóng, lãi kép ⇒ ước lượng ROI chỉ là bậc độ lớn, sai số chưa biết (CHƯA XÁC MINH).
3. Proxy `calMarketData` chưa đối chiếu market.bin HO4 (không có trên Oracle); chưa đo gate store/p15/Tool1/bins.
4. exchangeInfo 10-27 là ảnh chụp sau cửa sổ; luật phân loại không phụ thuộc thời điểm (contractType cố định) — rủi ro thấp.
5. HO 2026 đã nhìn nhiều lần; mọi rerun chỉ là sensitivity, không phải holdout mới.

## 7. PREREG đề xuất — HO2026_NOTF sensitivity (CHƯA CHẠY; chốt trước khi có số)

**Mục tiêu:** đo verdict HO 2026 trên universe đúng như go-live c3_live (không TF, không INDEX) — cả trực tiếp (leg) và gián tiếp (market feature, gate, ALT_EW/X14).
**Trạng thái nhìn số (khai thật):** đã nhìn số HO4/X14/ECM/GOLIVE 2026 và các số trong tài liệu này (leg TF, ước lượng thô, 18 ngày cờ noTFIDX). Rerun KHÔNG phải holdout mới.

1. **Universe A1 (thay đổi DUY NHẤT):** universe HO4-P1 (`run.py:69-73`) trừ tập X = {contractType chứa TRADIFI/TRADFI hoặc underlyingType ∉ {COIN, PREMARKET}} theo `exchangeInfo_20261027_1140.json.gz` (228 TF USDT + ALLUSDT, BTCDOMUSDT, DEFIUSDT). Danh sách X ghi md5 vào prereg trước khi dựng.
2. **Áp ở mọi tầng:** ticker 2026 (⇒ market.bin, gate store, Tool1, nhãn, CLOSES_1H, feat_v2, pool S1, net015, bins, funding.bin dựng lại bằng đúng chuỗi HO4-P1, cùng jar/model/seed) VÀ ALT_EW cờ X14 = biến thể noTFIDX (18 ngày: 02-05..02-14, 02-16, 02-17, 02-24, 02-25, 06-06, 06-07, 06-10, 06-11). Đoạn ≤ 2025-12-31 giữ NGUYÊN byte.
3. **Cấu hình:** k24-s (bản chính HO4), k24-b (nền X14), x14 (fee b, jar cc0f9d11, `SIM_LOSER_TS_EXT_HOURS=336`) × 8 seed {42,7,13,21,99,123,777,2024}; `SIM_END_DATE=20261001`; override y hệt run gốc. 24 kernel A1.
4. **Cổng tất định (trước khi chấm):** dựng lại A0' (cùng pipeline, KHÔNG loại X) cho seed 42 ở 3 cấu hình; printDone md5 phải = run gốc (`ho4-k24-s-s42`, `ho4-k24-b-s42`, `tsx-ho-x14-s42`). FAIL ⇒ dựng A0' đủ 24 kernel và dùng A0' làm nền (không dùng run gốc).
5. **Validate trước khi báo:** V1 ticker A1 có 0 symbol ∈ X; mọi symbol ∉ X trùng byte với ticker gốc (md5 từng ngày trên tập con). V2 ALT_EW A1 = `a2` noTFIDX (max\|Δ\| ≤ 1e-12), cờ = 18 ngày trên. V3 0 leg ∈ X trong printDone A1. V4 self-check scorer như HO4 (E MTM vs equity_final ≤ 0,01 %, miss giá = 0). V5 parity jar/override/pred md5/penalty.
6. **Thước (scorer A HO4 `ho4_score_a.py` y nguyên, giá Vision, bản CHÍNH = stress):** cho W9/H1/Q3: mean ΣPnL_S, số seed > 0, ROI MTM, maxDD MTM; Δ paired A1 − A0 theo seed (ΔROI pp, ΔmaxDD pp); ΔX14 = x14 − k24-b trong từng universe.
7. **Luật quyết (chốt trước):**
   - D1 HO4 E0 (k24-s): E0 = mean ΣPnL_S > 0 VÀ ≥ 6/8 seed > 0, tính lại trên A1 cho W9/H1/Q3. Nếu verdict W9/H1 giữ PASS ⇒ "HO4 vững với TF"; nếu đổi ⇒ báo MASTER, số go-live phải lấy A1.
   - D2 X14 (luật §7 TS_MKT_EXT addendum 1, y nguyên): trên A1, mean ΔPnL(x14 − k24-b) > 0 VÀ 8/8 seed ≥ 0 VÀ mean ΔmaxDD ≥ −1 pp ⇒ CONFIRM giữ; ngược lại ⇒ X14 "chưa xác nhận trên universe go-live", MASTER quyết trước go-live.
   - D3 Vật chất: \|mean ΔROI_W9(A1 − A0)\| ≤ 1,0 pp VÀ \|mean ΔmaxDD_W9\| ≤ 1,0 pp (cả k24-s và x14) ⇒ "không vật chất", giữ số hiện tại kèm chú thích; ngược lại ⇒ phải phát hành lại GOLIVE_QUARTERLY 2026 và ECMEAS H theo A1.
   - D4 Q3: chỉ mô tả (đã nhìn). Q3 PASS trên A1 KHÔNG được dùng làm bằng chứng nâng hạng chiến lược.
8. **Không tune:** không đổi ngưỡng, cửa sổ, seed, model, TOPK, quota, giờ X14. Chấm 1 lần; chạy lại chỉ khi lỗi hạ tầng (rc≠ok, mapper < 800, timeout) với cfg y hệt.
9. **Ngoài phạm vi:** universe "đúng như shadow v1.1" (TF ~223, không mapper) — không mô phỏng được với mapper 863 khoá; ghi là khoảng trống đã biết.
