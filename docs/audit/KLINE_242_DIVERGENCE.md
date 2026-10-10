# KLINE_242_DIVERGENCE — kline 1m Aerospike 242 lệch Binance (agent KDIV, 2026-10-10)

Pre-reg `docs/prereg/PREREG_KLINE_242_DIV.md` (**b41bbf81**, commit TRƯỚC khi đo). Script `research/analysis/kline_242_div.py` (stage `syms|d1|d2|dev|gate|gatecmp|report`). JSON `docs/audit/KLINE_242_DIVERGENCE.json`. CHỈ ĐỌC 242 (Aerospike `operate` = read + `expression_read` LUT; log; file jar/config đang chạy): 0 ghi, 0 restart. 0 sim, 0 Kaggle, 0 Java, 0 sửa `.java`. REST công khai: 61 call `fapi/v1/klines`. Thư mục Oracle `~/claude_master/1003/kdiv/` (tiền tố `kdiv_`).

## KẾT LUẬN (rủi ro trước)

1. **242 sai, Binance (REST = Vision) đúng.** Trên 60 (symbol, ngày) = 86 400 phút: REST `fapi/v1/klines` ≡ Vision **100,000%** cả 7 trường (O/H/L/C/Q/V/trades); REST ≡ 242 chỉ **56,2%** (40 ngày tệ nhất 42,4%; 20 ngày ngẫu nhiên 83,9%).
2. **Kiểu sai: nến M được "chốt vĩnh viễn" 2–6 s sau khi đóng, khi sàn chưa gộp đủ trade cuối phút**, và không bao giờ lấy lại. Ô lệch: open đúng 99,8%, H/L nằm trong biên Vision 99,9%, quoteVolume **luôn thấp hơn** (0% cao hơn; 48% thiếu < 1%, 37% thiếu 1–10%, 12% thiếu 10–50%), close lệch 68%. Không phải lệch phút (shift 1,3%), không đổi symbol, không làm tròn.
3. **Điểm gãy: 2026-04-25 09:31 +07** (phút lệch bền đầu tiên; 09:20–09:30 bị pass repair REST ghi đè bằng nến đã đóng). Ingest websocket cũ chết 04-24 13:02; **V8 REST khởi động 04-25 09:20:41, V8.1 11:16:56**; commit **`2cbf27c9`** (04-25 09:25 "fix bug limit ws of binance at production") đổi `BinanceDataIngestor` sang `TickerIngestor2AerospikeNew`. Dòng gây lệch: `TickerIngestor2AerospikeNew.java:164` (cửa sổ giây 2–10) + `:235` (`limit=2`) + `:288-293` (chốt + `remove`).
4. **Quy mô (mẫu 170 symbol, 2026-04-25→10-09 07:00 +07, 37,7 M ô):** 15,71% ô lệch ≥ 1 trường; close 10,71%, H 1,14%, L 1,11%, open 0,03%, quoteVolume 15,71%. T5 22,1%, T6 20,0%, T7 13,2%, T8 12,7%, T9 11,9%, T10 11,3%. Trước gãy (04-01→04-24) 0,008%. Lệch tăng theo biến động phút: 10,6% (H−L < 0,1%) → 45,7% (> 5%); và theo độ sớm của lần ghi cuối: 20,1% (ghi ở giây 2–5) → 12,3% (5–10 s) → 6,9% (10–20 s).
5. **Ảnh hưởng:** DEV (`kaggle_data_hpo` 2025) **khớp Vision 100,000%** (8 ngày × 28–48 symbol, 415 480 ô) ⇒ DEV sạch. Holdout HO26 T5–T6: 21,05% ô lệch (symbol HO26: 18,65%, close 13,91%); chân s42 (k24+b0) T5–T6: 38/124 giá vào rơi vào close lệch, 54/120 nến thoát lệch. Live: xem D4a.

## D1 — Lượng hoá (Aerospike 242 `ticker.kline_1m_opt` vs Vision)

Mẫu 170 symbol = top-50 totalUsdt 242 (03-10..16) ∪ 128 symbol có lệnh HO26 s42 (k24/b0). Khớp trường ⇔ float32 bằng (|Δ| ≤ 1e-8·|b|). 242 chỉ lưu O/H/L/C/totalUsdt (= quoteVolume) ⇒ **volume base / trades: N/A** (không lưu). Vision daily 2026-10-09 chưa phát hành lúc đo ⇒ cửa sổ kết thúc 2026-10-09 07:00 +07.

| Kỳ (+07) | ô | lệch ≥1 trường | open | high | low | close | quoteVol |
|---|---|---|---|---|---|---|---|
| 04-01→04-24 (trước gãy) | 5 460 755 | 0,008% | 0,000% | 0,003% | 0,003% | 0,007% | 0,008% |
| 04-25→10-09 | 37 720 173 | **15,713%** | 0,032% | 1,139% | 1,113% | 10,705% | 15,713% |
| T4 (cả tháng) | 6 757 474 | 3,093% | 0,004% | 0,225% | 0,227% | 2,115% | 3,093% |
| T5 | 6 794 897 | **22,107%** | 0,039% | 1,601% | 1,590% | 15,195% | 22,107% |
| T6 | 6 826 557 | **19,998%** | 0,043% | 1,503% | 1,486% | 14,357% | 19,998% |
| T7 | 7 053 099 | 13,239% | 0,041% | 0,926% | 0,898% | 8,677% | 13,239% |
| T8 | 7 053 087 | 12,719% | 0,024% | 0,871% | 0,820% | 8,323% | 12,718% |
| T9 | 6 825 577 | 11,860% | 0,019% | 0,876% | 0,846% | 7,951% | 11,860% |
| T10 (01→09 07:00) | 1 870 237 | 11,265% | 0,022% | 0,885% | 0,871% | 7,545% | 11,265% |

Ngày tệ nhất: 06-04 28,56%, 06-05 28,32%, 06-03 26,50%, 06-06 25,99%, 05-28 25,08%; 05-22 22,50%; 06-25 14,18%; 04-25 5,47% (từ 09:31), 04-26 8,85%.

**Độ lớn (|a/b − 1| trên ô lệch, p50 / p99, T5 | T9):** close 0,029% / 0,25% | 0,025% / 0,23%; high 0,029% / 0,37%; low 0,030% / 0,41%; open (hiếm) 0,035% / 0,18%; quoteVolume 1,16% / 80% | 1,14% / 82%.

**Theo biến động phút Vision (H−L)/O, 04-25→10-09 — % ô lệch:** < 0,1%: 10,63 · 0,1–0,2%: 14,43 · 0,2–0,5%: 19,51 · 0,5–1%: 29,56 · 1–2%: 38,00 · 2–5%: 42,80 · > 5%: 45,66 (T5–T6: 14,97 → 52,74).

**Theo thời điểm ghi cuối của key phút (LUT − (phút+60 s)), 04-25→10-09:**

| off (s) | phút | ô | % ô lệch |
|---|---|---|---|
| < 0 (không có lần chốt sau khi đóng) | 40 | 6 283 | 98,4% |
| 0–2 | 3 | 468 | 97,0% |
| **2–5** | 41 631 | 6 592 670 | **20,06%** |
| **5–10** | 121 449 | 19 167 236 | **12,31%** |
| 10–20 | 1 707 | 269 705 | 6,93% |
| 20–60 | 67 | 10 568 | 8,23% |
| 60 s–1 ngày (repair/restart ghi lại) | 16 293 | 2 573 657 | 13,92% |
| ≥ 1 ngày (ghi lại hàng loạt, LUT 06-02 19:47→10-07 21:09) | 59 663 | 9 099 586 | 20,44% |

⇒ chốt càng sớm càng lệch; các lần ghi lại muộn (repair khi restart `startDataRepair` chỉ thêm symbol **thiếu**) **không sửa** ô sai. gen điển hình 21 (≈ 20 lần ghi "nặn nến" mỗi 3 s + 1–2 lần chốt); trước gãy 500–4 700 (websocket ghi từng symbol).

**Phân bố trong phút:** 57,0% ô lệch nằm ở phút có 5–20% symbol lệch, 41,3% ở phút 20–50%, chỉ 0,96% ở phút > 50% (565 phút) ⇒ lỗi rải theo symbol trong hầu hết mọi phút, **không phải** mất cả phút.

**Điểm gãy:** % khớp theo giờ 04-24 00:00→04-25 08:59 = 100% (trừ 04-24 01:00 99,92%: phút lệch đầu tiên 01:24, sự cố websocket lẻ); 04-25 09:00 96,5%, 10:00 91,7%, sau đó 89,8–91,9%/giờ. Theo phút (150 ô/phút): 09:20–09:30 0 lệch (gen ~565 = pass repair REST ghi đè bằng nến đã đóng), **09:31 2 lệch, 09:32 7, 09:33 13** … rồi 4–21 lệch/phút; gen rơi 565 → 11 (09:37) → 31 (từ 11:17, V8.1). Quy tắc pre-reg (trung bình 60′ kế tiếp < 99%) cho **08:40** — đây là giả tượng cửa sổ nhìn trước 60′ của quy tắc; phút gãy thật = **2026-04-25 09:31 +07**.

**Ô thiếu:** 242 thiếu 2,70 M ô có trên Vision (04-25→10-09) — do 9 symbol 242 ngừng ingest hoàn toàn (42, DEGO, DENT, DF, GHST, NKN, RVV, TANSSI, YALA), 3 symbol dừng giữa kỳ (COS, D, HIGH) phần còn lại ở symbol niêm yết giữa kỳ (chưa phân rã); không phải lỗi giá trị.

## D2 — Ai đúng (REST `fapi/v1/klines` chính thức)

Mẫu chốt trước: 40 (symbol, ngày UTC) nhiều ô lệch nhất (≤ 2/symbol, ≤ 6/tháng, T4..T10) + 20 ngẫu nhiên (seed 20261010) ⇒ 60 ngày, 39 symbol, 86 400 phút. REST gọi 2026-10-10 (nến đã đóng từ lâu).

| So sánh | ô chung | khớp đủ trường | O | H | L | C | Q | V | trades |
|---|---|---|---|---|---|---|---|---|---|
| REST ↔ Vision | 86 400 | **100,000%** | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| REST ↔ 242 | 86 398 | **56,23%** | 99,96% | 97,22% | 97,31% | 63,70% | 56,23% | N/A | N/A |
| — 40 ngày tệ nhất | 57 598 | 42,42% | | | | | | | |
| — 20 ngày ngẫu nhiên | 28 800 | 83,86% | | | | | | | |

Ô 242≠REST (37 814): Q242/Q_REST ∈ [0,99; 1,01) 43,2%, [0,9; 0,99) 49,9%, [0,5; 0,9) 6,2%, [0,1; 0,5) 0,5%, < 0,1 0,2% (gồm 38 ô Q=0), > 1,01 **0**.
⇒ **Vision/REST đúng, 242 sai.** Kiểu sai = **nến chưa "settle" (thiếu trade cuối phút) bị ghi làm nến đóng**: open đúng, H/L bị cắt bên trong, close = giá trước trade cuối, volume thiếu. Loại trừ: ghi đè sai phút (shift 1,3%), lấy từ websocket thiếu trade (websocket không còn dùng sau 04-25), làm tròn (độ lệch p50 0,03% ≫ ulp float32), đổi symbol (O khớp 99,96%). Phần nhỏ Q < 0,5·REST (0,65%) = nến "nặn" từ `ticker/price` khi fetch klines của symbol đó lỗi.

## D4 (b) — DEV

- Nguồn DEV: `~/java/simulator/kaggle_data_hpo/daily/ticker_*.bin.gz` (Java-serialized), export từ Aerospike Oracle-local `test.kline_1m_opt` bằng job tickexport (`docs/audit/D1_DATA_AUDIT.md:387-388`; tool `ai_ml/hpo/kaggle/ExportTickerDaily.java`).
- Kiểm mẫu 2025 (ngày 01 & 15 của T3/T6/T9/T12, symbol top-50 có mặt): **415 480 / 415 480 ô = 100,000%** khớp Vision cả 5 trường (mỗi ngày 100,000%; 12-15 chỉ 16 600 ô do file ngày thiếu giờ). DEV **không** dính lỗi (lỗi bắt đầu 2026-04-25, sau DEV ≤ 2025-12-31; HO3 K2a: 2026-03 99,997%).

## D4 (c) — Holdout HO26 (2026-05-01→06-30)

- Ticker HO26 (`ticker_2026*.bin.gz`) ≡ Aerospike 242 99,9996% (HO3 K1) ⇒ mang nguyên lỗi: **21,05%** ô lệch (close 14,78%), mẫu symbol HO26 18,65% (close 13,91%), top-50 27,71% (close 17,54%).
- Chân s42 (k24 + b0) có start/end trong T5–T6: **38/124** giá vào (close nến quyết định) lệch, **54/120** nến thoát lệch ≥ 1 trường. AUD26: giá vào sim cao hơn Vision TB +0,049%, tác động bậc 1 ΣPnL k24 Δ +1 [−45..+51] ⇒ hướng lỗi (close/high cắt bên trong, volume thiếu) không tạo lợi thế có hệ thống cho sim; nhưng feature volume (quoteVolume thiếu 1–80%) và gate (D4a) lệch trên toàn bộ T5–T6.
- Đánh giá: kết quả HO26 T5–T6 được tính trên **dữ liệu 242-lệch, cùng nguồn với live** (nhất quán sim≡live) nhưng **không** phải dữ liệu sàn chuẩn. Muốn HO26 "sàn chuẩn" phải export lại ticker từ Vision cho 04-25→06-30 và chạy lại (biến thể mới, pre-reg riêng).

## D4 (a) — Live: gate trên nến 242 vs nến Vision (2026-05-01→06-30)

Cách đo (chốt trong pre-reg): 33 feature gate = port `devexport_202609` (md INLINE cả 2 nhánh, funding 242 chung, `DIED_SYMBOLS` từ `config.properties` repo) tính trên (i) kline 242 nguyên bản, (ii) cùng universe 242 nhưng giá trị thay bằng Vision (T4 thay 27,91 M/27,94 M ô, T5–T6 100%); p15 = ONNX fold_20 (`Model_Regressor_Return15M.onnx`, = model live); ứng viên = top-24 sp bins HO26 (`bins2026Ax`, ffill ≤ 15′); r, q_h (90 ngày, pct 0.999950829, J=256, warm-up 7 ngày), PASS ⇔ !(p15 < q·factor·1,55) như `gate_offline`. Lịch sử r trước 04-01 dùng chung nhánh 242. Chunk tháng (warm-up 48 h) giống nhau ở 2 nhánh.
**Validate:** 04-03→04-24 (trước gãy) hai nhánh cho p15 trùng tuyệt đối **99,84%** phút (31 680), |Δ| max 0,086 pp ⇒ khác biệt sau 04-25 là do dữ liệu, không do pipeline.

| Chỉ số (T5–T6, 87 802 phút, 2 106 936 cặp phút×ứng viên) | 242 | Vision |
|---|---|---|
| PASS | 719 (0,0341%) | 688 (0,0327%) |
| PASS chỉ ở 1 nhánh | 64 | 33 |
| Cặp đổi quyết định | **97 = 0,0046%** cặp; phút có ≥1 đổi: **0,017%** (15 phút) | |
| Jaccard tập PASS | **87,1%** (655 chung / 752) | |
| T5 / T6 | 0 PASS cả 2 nhánh / 97 đổi trên 719 vs 688 PASS | |
| p15 trùng tuyệt đối | 28,1% phút | |
| \|Δp15\| p50 / p90 / p99 / max | 0,0024 / 0,012 / 0,026 / 0,64 pp | (p15 TB 0,899% vs 0,900%) |
| q_h Vision/242 | p1 0,956 · p50 1,000 · p99 1,010; 777/1 464 giờ khác | |

- Feature lệch (rtol 1e-6, % phút): ≥ 90%: momentum1M/15M/Acceleration, volatility15M/1H/24H/TermStructure, advanceDeclineRatio, volumeRatioUpDown, btcDominance, volumeSpike, distMA20, basket×4; marketBreadthStrength 81%, rsi14 82%, percentAboveMA20 74%, trendStrengthETH 59%, volatility1M 53%; momentum5M/1H/4H/24H 40–41%; funding×3 35–44% (rổ basket chọn theo volume ⇒ đổi rổ); trendConsistency 0,9%.
- **Hạng ứng viên: S1 không tính lại** (cần pipeline S1). Proxy: top-24 theo return 60′ (close 242 vs Vision) lưới 15′ — Jaccard TB **0,974** (đáy-24: 0,970); **31,2%** mốc 15′ có top-24 khác ≥ 1 symbol (đáy-24: 35,7%).
- Đọc: lệch nến làm **~13% quyết định PASS khác** (64+33 trên 752 PASS hợp), nhưng trên toàn bộ cặp chỉ 0,0046% vì gate gần như luôn chặn (PASS 0,03%). Hướng: 242 PASS nhiều hơn Vision 4,5% (719 vs 688). Ảnh hưởng tới PnL live không đo (cần sim; ngoài phạm vi).

## D3 — Nguyên nhân (code + git + log 242, chỉ đọc)

**Mốc deploy (log 242 `collectData/logs/full.log`):**
- Ingest cũ = websocket `TickerIngestor2Aerospike` (`[Kline-Ingestor-Loop] … Finalized Minute`): dòng cuối **2026-04-24 13:02 +07** (phút 13:02 chỉ còn 332 symbol, bình thường ~590) ⇒ ws chết/treo.
- 04-24 13:03 → 04-25 09:20: không có ingest. **2026-04-25 09:20:41** khởi động `TickerIngestor2AerospikeNew` **V8 (REST)**; **11:16:56** khởi động lại bản **V8.1 "HYBRID REALTIME"** (= code đang chạy, mọi lần restart sau đều V8.1; jar hiện tại `collectData/target/binance-java-sdk-1.2.4.jar` 2026-08-20 21:25, log `[KLINE V8.1] Chốt nến phút …` tới 10-10).
- Lỗ 04-24 13:03→04-25 09:20 được lấp bởi `startDataRepair(30*60)` (REST lịch sử, nến đã đóng hẳn) ⇒ khớp Vision; vì vậy điểm gãy đo được nằm ở lúc V8/V8.1 bắt đầu ghi realtime chứ không ở 04-24 13:03.
- Commit nguồn: **`2cbf27c9` (2026-04-25 09:25 +07, "fix bug limit ws of binance at production")**: `BinanceDataIngestor.main` bỏ `TickerIngestor2Aerospike`/`FundingIngestor2Aerospike` (websocket) và chuyển sang `TickerIngestor2AerospikeNew` + `FundingIngestor2AerospikeNew` (REST polling). Các commit sau (106baeee, 16971984, 409ab7e9, 89c35850) chỉ thêm ban-guard/pool/watchdog, **không đổi thời điểm chốt nến**.

**Dòng code gây lệch** (`src/main/java/com/binance/chuyennd/websocket/TickerIngestor2AerospikeNew.java`, HEAD = bản chạy):
- L163-164: `Rest-Kline-Loop` chỉ chạy ở **giây 2–10 của phút M+1**; L235: `GET /fapi/v1/klines?symbol=S&interval=1m&limit=2` ⇒ nhận nến M (vừa đóng) + M+1 (vừa mở).
- L262-264: ghi đè vào `timeBuffer[M]`; L288-293 `flushKlinesToDatabase`: ghi M **"chốt lưu vĩnh viễn"** rồi `timeBuffer.remove(lastMin)` ⇒ **nến M không bao giờ được lấy lại**. Log cho thấy lần chốt hoàn tất ở giây ~5–6 (vd `11:28:05.750 Chốt nến phút 11:27`).
- Hệ quả đo được (D1/D2): ô lệch có open đúng, H/L nằm trong biên Vision, quoteVolume **thấp hơn** (không bao giờ cao hơn), close lệch ⇒ **ảnh chụp nến M khi sàn chưa gộp đủ trade cuối phút** (REST trả nến M chưa "settle" trong vài giây đầu sau khi đóng; càng biến động càng thiếu nhiều).
- Phụ: L50-124 `Rest-Price-Loop` "nặn nến" từ `ticker/price` mỗi 3 s và ghi phút hiện tại mỗi 3 s (L121-124, merge `writeMinuteBatch` `DataManagerAerospikeFloatSim.java:192-212`); symbol nào fetch klines lỗi (L268-270 nuốt exception, timeout 3 s L237, ban-guard L233) giữ nến "nặn" (Q = phần đầu phút hoặc 0) — chỉ là phần nhỏ (bậc Q242/QV < 0,1). `Rest-Kline-Loop Error: null` (= `f.get(20s)` timeout L175) làm hỏng cả phút — hiếm (log ~1 440 lần chốt/ngày).
- Pre-04-25 (websocket `kline_1m` chỉ ghi khi `x=true`) khớp Vision ~100% ⇒ lỗi do đổi kiến trúc ingest, không do Binance đổi dữ liệu.

## D5 — Đề xuất sửa (KHÔNG thực hiện)

**1. Sửa chốt nến (chọn một, ưu tiên a):**
- (a) Quay lại websocket `<sym>@kline_1m`, chỉ ghi khi `k.x == true` (nến đóng, là nến cuối của sàn); chia ≤ 200 stream/kết nối (giới hạn đã làm sập ws ngày 04-24), reconnect + heartbeat; REST chỉ dùng lấp lỗ (repair).
- (b) Nếu giữ REST: trong `Rest-Kline-Loop` đổi cửa sổ L164 từ giây 2–10 sang **≥ 20–25** và `limit=3`; chỉ ghi nến có `closeTime < now − 15 s`; ghi lại M−1 (nến đã chốt phút trước) ⇒ mỗi nến được chụp 2 lần, lần sau ≥ 80 s sau khi đóng. Chi phí weight không đổi (~1/symbol/phút, ~750/2400 weight/phút).
- (c) Bỏ `timeBuffer.remove(lastMin)` khi fetch symbol lỗi; đếm và log số symbol fetch OK/lỗi mỗi phút (hiện nuốt câm L268-270).
- Bất kể a/b: job đối soát ngày (sau khi Vision daily phát hành, ~D+1 08:00 +07) ghi đè ngày D từ Vision (quoteVolume → totalUsdt, float32), chỉ cho symbol có Vision.

**2. Backfill/chuẩn hoá Aerospike 242 (`ticker.kline_1m_opt`) 2026-04-25 09:20 → nay:**
- Sao lưu trước (cơ chế `ReplicateSet242To226`, TASK-034) sang 226.
- Ghi lại từng phút từ Vision monthly/daily: merge theo symbol (giữ ô 242 không có trên Vision; giữ đúng proto/snappy, float32), tuyệt đối không ghi phút hiện tại/±5′ (live đang đọc). Chạy bằng tool Java dùng chính `DataManagerAerospikeFloatSim.writeMinuteBatch` (qua `Live242WriteGuard`), giờ thấp điểm.
- Kiểm sau backfill: chạy lại `kline_242_div.py d1` ⇒ cổng ≥ 99,99% ô khớp 5 trường.
- Hệ quả: (i) live: bộ đệm r 90 ngày của gate (q) trong JVM đã nạp từ feature lệch ⇒ restart/khởi tạo lại sau backfill; (ii) research: `ticker_2026*.bin.gz` (HO26) đang là bản 242-lệch cho 04-25→06-30 ⇒ nếu cần HO26 trên dữ liệu chuẩn phải export lại từ nguồn đã backfill (đổi nguồn = biến thể mới, khai pre-reg).

**3. Kiểm liên tục:**
- Healthcheck mỗi giờ (Python chỉ đọc): 20 symbol top volume + 30 ngẫu nhiên, cửa sổ [now−70′, now−10′], REST `fapi/v1/klines` limit 60 (weight 1/symbol, ~50 weight/giờ) so Aerospike; chỉ số = % ô khớp O/H/L/C/Q float32; cảnh báo < 99,9%, ghi kết quả vào set riêng.
- Báo cáo ngày vs Vision daily (cổng 99,99%) + đếm phút thiếu.
- Trong ingest: gauge "symbol chốt OK/phút", cảnh báo khi < 99%.

## Provenance / lệch khỏi pre-reg (khai thật)

- Quy tắc điểm gãy pre-reg (trung bình 60′ kế tiếp < 99%) trả **08:40** do cửa sổ nhìn trước 60′; báo kèm phút gãy thật theo chuỗi phút (**09:31**). Không đổi số nào khác.
- Vision daily 2026-10-09 chưa phát hành ⇒ D1 dừng ở 2026-10-09 07:00 +07 (ô 242 không có Vision đếm `a_only`, không tính khớp/lệch).
- p50/p99 độ lớn theo tháng gom theo ngày UTC (histogram log10, bin 0,01 ⇒ sai số ≤ 2,4%).
- D4a xấp xỉ (đã khai trước): không loại coin đang giữ, không tái lập `isTickerAvailable`, S1 không tính lại (proxy return 60′), feature = port Python (không phải đường Java live; RESULT_DEVEXPORT_202609: 30/33 khớp store DEV).
- Lỗi code sửa trước khi chốt số: `vis_dense` cố định 7 cột (crash nhánh vis khi chạy thử 1 ngày, chưa ra số); bỏ trùng proxy hạng ở ranh chunk; thêm memo parse (chỉ tốc độ). Thêm kiểm `validate_pre_break` (ngoài pre-reg, chỉ để kiểm pipeline).
- Đọc 242: Aerospike (`operate` read + LUT), `collectData/logs/full.log` (grep), danh sách jar/config (ls). Không đọc secret, không ghi.
- Chạy: d1 ~55 phút; gate 7 chunk (242: 01-31→06-30; Vision: 04-01→06-30) ~80 phút, lock `oracle_heavy.lock` khi > 4 G (đã gỡ); REST 61 call; Vision ~7 000 file zip đọc trong RAM (đĩa: JSON/npz/csv tạm trong `~/claude_master/1003/kdiv/`).
