# PARITY v1.1 — lượt D, ngày đầu cửa sổ promotion (2026-10-21 UTC)

Thước: `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (commit `481701b2`), áp nguyên văn; không đổi nguồn/universe/ngưỡng/luật phân loại sau khi thấy số.
Đối tượng live: 242, jar `eea5adec…` (v11c) từ `2026-10-21 07:53:59 (+07)` (nến quyết định đầu tiên `1792543980000`).
Toàn bộ đọc 242 là **chỉ đọc** qua `ssh … ls/cat/tar/grep/awk/du/find`; **không ghi file nào lên 242**, **không đọc Aerospike 242**.
Harness: `research/parity_v11` (commit `0bd019f7`), `HARNESS_OFFLINE=1`, stub Aerospike halt 97 + SecurityManager halt 98.

## 1. Dữ liệu và phạm vi đo

| Mục | Kết quả |
|---|---|
| Vision UM 1m daily 2026-10-21 | **có**, 741/741 symbol của U_D (100 %) |
| Vision 2026-10-22 | **chưa có** (HTTP 404 lúc 2026-10-23 11:16 +07) → **không đo ngày này** |
| Vision 2026-10-23 | chưa có (404) |
| Vision 2026-10-18..20 (warm-up BT 48h + seed NEW2 2000′) | có; 10-18..20: 738/741 (3 symbol `BACUSDT,CEGUSDT,IBKRUSDT` niêm yết trong 10-21 nên 404 các ngày trước) |
| Cửa sổ đo | `1792543980000 … 1792627140000` = 10-21 00:53 UTC → 10-21 23:59 UTC = **10-21 07:53 → 10-22 06:59 (+07)** |
| Phút live có dòng `feat_dump` | **1386**; thiếu `10-21 07:53` (phút warm-up, live log có `[FEAT-PIPE] khong co feature`) → loại khỏi chấm theo §4 |
| Phút BT | 1387 (= 1386 + 07:53) |
| Universe U_D | **741** = hợp(u_cache1017 ∪ symbol trong `sel_dump`/`s1_dump`/`predictionSymbol` ngày D) bỏ symbol không có file Vision; khớp `nsym=741` cuối ngày của log |
| Universe thay đổi trong ngày | nsym live 738 → 739 (16:00 UTC) → 740 (16:05) → 741 (16:10); 3 symbol mới |
| `predictionSymbol` live | 1440 file ngày 10-21 + 413 file đầu ngày 10-22; **thiếu 7 phút 10-22 00:00–00:06 (+07)** |
| Dump kéo về | 530 file feat/sel (10-21+10-22), 53 file s1, 1860 file psym, `gate_ratio_live.bin`, `ts_ext_daily.csv`, `legacy_symbols.csv`, log lọc 6147 dòng |

## 2. R0 và CTL (điều kiện trước khi chấm)

| Mục | Kết quả |
|---|---|
| **R0** (chạy lại 2026-10-23 11:19 +07) | **11/11 ca ĐẠT**: client242/clientOracle/readClient/mapperLoad/fundingScan/tickerRead → exit 97; socket242/dnsVision → exit 98; thiếu stub → 96; config thật → 96 |
| strace BT & NEW2 | 4 `connect()` toàn bộ là `AF_UNIX /var/run/nscd/socket`; **0 connect tới 103.157.218.242, 0 AF_INET** |
| **CTL** OFF-NEW2 vs OFF-BT | gate 33: 1386/1386 phút **bit-identical** (1 phút 07:53 chỉ có ở BT do warm-up); Tool1 #1–40: **100 % trong dung sai 1e-6**, bit 94,25 % (chỉ cột `f3`, 2605 dòng lệch bit cuối), 31 dòng chỉ có ở BT (7 phút psym thiếu) |

## 3. Bảng khớp chính (live 242 vs OFF-BT, lượt D)

Dung sai 1 giá trị: `|a−b| ≤ 1e-6·(1+|b|)` (NaN=NaN). 1386 phút chấm.

| mã | chỉ số | Kết quả | Ngưỡng | Verdict |
|---|---|---|---|---|
| **P1-F** | 30 feature gate không-funding, ALL cùng khớp | **1378/1386 = 99,4228 %**; 8 phút lệch | báo cáo | ĐẠT (kèm 8 phút có nhãn) |
| | từng feature | 18/30 feature 100 %; 9 feature 99,7835 % (3 phút); `momentum15M`, `momentumAcceleration` 99,4228 % (8 phút) | | |
| **P1** | p15 ONNX trên vector OFF (3 cột funding thay bằng live) vs `p15_out` live | median rel **6,04e-10**; ≤1e-3: **99,9278 %**; ≤1e-4: 99,9278 %; max rel 1,12e-3 (1 phút: 10-21 23:59) | median ≤1e-4 **và** ≥98 % ≤1e-3 | **ĐẠT** |
| P1-m | p15 ONNX trên vector live vs `p15_out` | **100 %** ≤1e-6 (max rel 3,66e-7) | 100 % | **ĐẠT** |
| **MD** | rateDownAvg / rateUpAvg / rateDown15MAvg | **99,7835 % / 99,8557 % / 99,4228 %** | báo cáo | — |
| **FUND** | Tool1 #1–40 (bỏ f17–f25, f32), 45.101 dòng khớp khoá | **99,341 % dòng**; **1371/1380 phút = 99,348 %** phút ALL-khớp | báo cáo | ĐẠT (phần funding chờ lượt M) |
| **NET** | net015 trên vector OFF (f17–f25,f32,f40–44 tiêm live) vs vector live | **99,9357 %** dòng ≤1e-6; 1377/1380 phút ALL (99,783 %); max |Δ| 0,00786 | báo cáo | — |
| **S1-I** | thứ tự top-24 `sel_dump` == sort(score↑, symbol↑) của `s1_dump` bỏ LEGACY | **1387/1387 phút = 100 %** (Jaccard 1,0; không cần loại coin đang giữ); \|selectorScore\| vs \|score\| max 7,5e-8 | 100 % | **ĐẠT** |
| S1-m | ONNX S1 trên f0..f8 live vs score live | **940.226 dòng, 100 %** ≤1e-6, max abs **0,0** (score live = −output ONNX) | 100 % | **ĐẠT** |
| **S1-V** | f0..f6 tính lại từ close 1h Vision + f7/f8 live → score → top-24 | f0/f1/f3/f4/f6 100 %, f2 99,957 %, f5 99,916 %, score 99,991 % ≤1e-6, **top-24 Jaccard 1,0 & trùng thứ tự 1387/1387** | báo cáo | ĐẠT (không ngưỡng) |
| **GV-I** | `gateValue` sel_dump == luật `LiveBuildMap.assign` trên pw live + thứ tự S1 live | **33.120/33.120 = 100 %** | 100 % | **ĐẠT** |
| GV-O | `gateValue` với pw OFF (NET, fallback live khi ngoài Tool1) | **99,9698 %** (10 dòng lệch: 07:53 và 23:59) | báo cáo | — |
| **P2** | cặp (phút, ứng viên): 23.184 cặp | pass live **0**, pass off **0**, lật **0**, lật nặng **0** | lật nặng = 0 | **ĐẠT (yếu)** — max r/q 0,891 < 0,9 ⇒ **chưa có cặp nào thật sự gần ngưỡng**, P2 chưa được thử đúng nghĩa |
| | `[GATE] n_pass` log vs tính lại | 965/966 phút khớp; lệch duy nhất 10-21 07:54: log 24, tính lại 0 (q_t=0 lúc warm-up sau restart, xem §6) | | |
| **P3** | q_t9 log mỗi giờ vs replay causal từ buffer | **23/24 giờ ≤1e-6** (max rel 2,7e-10); **13:01 lệch 4,33e-3** | rel ≤1e-6 **mọi giờ** | **KHÔNG ĐẠT** (xem §6) |
| **TSX** | cờ `[TS-EXT] flag day=2026-10-21` | live **OFF** (dd −0,137179, minN 1436) vs Vision **OFF** (dd −0,139532, minN 1439) | cờ trùng | **ĐẠT** |
| | ΔS_j | 10-21: Δ **3,45e-9** (n=1440/1440); 10-20: Δ 1,81e-4 (Vision n=1439) | báo cáo | — |

## 4. Feature lệch theo từng cột (P1-F)

| Feature | % khớp | Số phút lệch |
|---|---|---|
| 18 feature còn lại (momentum5M/1H/4H/24H, trendStrengthETH, trendConsistency, volatility*, volatilityTermStructure, rsi14, volumeSpike, distMA20, hourOfDay, dayOfWeek, weekOfMonth, monthOfYear) | 100,0000 | 0 |
| momentum1M, advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance, basketMomentum15M, basketMomentum1H, basketRsi14, basketVolSpike | 99,7835 | 3 (11:59, 17:04, 23:59) |
| momentum15M, momentumAcceleration | 99,4228 | 8 |

3 cột funding của gate (`fundingRateRaw`, `fundingRateAvg24H`, `fundingRateTrend`) lệch gần như toàn bộ — **kỳ vọng ở lượt D** vì file funding Vision chỉ có tới 2026-09-30; P1 đã tiêm funding live đúng prereg, phán quyết funding để lượt M.

## 5. Phân loại phút lệch (§5, cơ học)

10 phút lệch (hợp của gate/FUND/NET): 07:53, 11:59, 17:04, 17:16, 17:18, 17:37, 17:38, 17:40, 23:59 (+07).

| Phút (+07) | Nhãn | Bằng chứng |
|---|---|---|
| 10-21 07:53 | **K3** + loại khỏi chấm | không có dòng `feat_dump` (warm-up restart 07:53:59); U_D 741 vs nsym live 738 |
| 10-21 11:59 | **K1, K3** | `[LIVE-KLINE]` cửa sổ kết thúc 12:01 `reread_overwritten=199`, 12:11 `decided_on_unsettled=199`; 12 feature market-level lệch 0,3–5 %; nsym 738 |
| 10-21 17:04 | **K1** | cửa sổ 17:11 `reread_overwritten=253`, `decided_on_unsettled=252`; 12 feature market-level lệch (advanceDeclineRatio 3,434 vs 3,278) |
| 10-21 17:16, 17:18 | **K1** | cùng cửa sổ 17:11; chỉ `momentum15M`+`momentumAcceleration` lệch ~0,1 % |
| 10-21 17:37, 17:38, 17:40 | **K5 — CHƯA GIẢI THÍCH** | cùng dấu hiệu “chỉ 15′ reference lệch ~0,1 %” như phút 21:58 của PARITY_V11_1020; không có cửa sổ LIVE-KLINE nào có cờ trong [M−20′, M+10′]; nsym 741 |
| 10-21 23:59 | **K5 — CHƯA GIẢI THÍCH** | 12 feature market-level lệch 1–2,5 %; không cờ LIVE-KLINE; quanh 23:50–23:55 log `Market level change … symbols:` dao động 659–684; psym live **thiếu 7 phút kế tiếp** 10-22 00:00–00:06 (dấu hiệu sự cố dữ liệu live tại mốc nửa đêm local) — chưa đủ để gán K1/K2 |
| 10-21 07:54 | không lệch feature, chỉ lệch `[GATE] n_pass` | q_t=0 lúc warm-up sau restart 07:53:59 (log GATE-RATIO đầu tiên 08:01 mới có q) ⇒ 24/24 ứng viên “pass”; replay dùng q của giờ ⇒ 0 |

Tổng: **K1 = 4 phút, K3 = 2, K5 = 4**. K2a = 0 (Vision `holes=0` trên toàn cache 5267 phút). K2b: `[TS-EXT] day=2026-10-21` in `minN=1436` (thiếu 4 phút của **10-20**), nhưng `ts_ext_daily.csv` của chính 10-20/10-21 đều `n_min=1440` ⇒ không áp nhãn K2b cho phút nào.

## 6. Bất thường P3 (13:01 +07) và GATE 07:54

- Log `21/10/2026 13:01:14` (+07) = **06:01 UTC**, giờ q = 06:00 UTC. `q_t9` log = `0,00715446286`; replay từ `gate_ratio_live.bin` với `ts ∈ [h−90d, h)` cho `0,00712359743` (rel **4,33e-3**). 23 giờ còn lại khớp ≤2,7e-10, **gồm cả 2 giờ có restart** (05:00 và 19:00 +07 = 22:00 UTC 10-20 và 12:00 UTC).
- Số record khớp nhau: replay dùng **672.216** record, đúng bằng `buffer=672216` trong log ⇒ không phải lệch biên window.
- Hai giá trị là **hai order-statistic kề nhau**: sort buffer tại mốc này có `a[k]=0,007123597`, `a[k+1]=0,007154463` (đúng **1** record mang giá trị sau), gap `3,086e-5`. Chênh lệch q log vs replay = đúng 1 bậc order-statistic ⇒ **một record trong buffer đã bị ghi đè/đổi giá trị sau 06:01** (cùng loại K1 — collector ghi đè sau quyết định), không phải lỗi code/định nghĩa q.
- Hệ quả: P3 chỉ “trượt” ở đúng giờ mà bậc 99,995 % rơi vào cặp giá trị bị dịch; không thể tái lập giá trị **trước** khi ghi đè từ file cuối (giới hạn vốn có của buffer chỉ-đọc).
- Theo đúng chữ prereg: **P3 KHÔNG ĐẠT** (yêu cầu ≤1e-6 **mọi** giờ). Không đổi ngưỡng; ghi để điều tra/ADDENDUM trước lượt kế.
- `[GATE] n_pass=24` tại 07:54 (+07): q_t = 0 trong giờ warm-up đầu sau restart, `thr=0` ⇒ mọi ứng viên pass; không phải lỗi parity.

## 7. S1-V (f0..f6 từ close 1h Vision, f7/f8 tiêm live)

Cài lại đúng công thức `S1FeatureLive` (decompile từ jar `eea5adec`: `vol7d` population? → **sample std (n−1)**, `dd7d` = c/max(c[i−167..i])−1 với min 84 mốc, `hrsSinceHigh7d` = (167−argmax)/168, `ret` = c[i]/c[i−k]−1, `rankPct` = average-rank/n), lấy close giờ từ Vision 1m daily 10-06..10-21 (hour close = nến 1m cuối giờ), chấm `s1a2x1_cut20251231`, so với `s1_dump` live.

| Mục | Kết quả |
|---|---|
| Số dòng / số phút | 940.226 dòng / **1387 phút** |
| f0 `vol_7d` | **100 %** |
| f1 `dd_7d` | **100 %** |
| f2 `rk_dd_7d` | 99,9572 % |
| f3 `hrs_since_high_7d` | **100 %** |
| f4 `ret_3d` | **100 %** |
| f5 `rk_ret_3d` | 99,9164 % |
| f6 `ret_14d` | **100 %** |
| score (ONNX, score live = −output) | **99,9911 %** ≤1e-6; max |Δ| 0,01399; Spearman 0,99999998 |
| top-24 (sort score↑, symbol↑) | **Jaccard trung bình 1,0 (min 1,0); trùng thứ tự 1387/1387 = 100 %** |

Hai cột rank lệch ≤0,09 % dòng: chênh lệch mẫu số xếp hạng ở các phút mà một số symbol không có đủ lịch sử Vision (404 ở 10-06..10-11 hoặc niêm yết mới), trong khi live xếp hạng trên universe đầy đủ; không ảnh hưởng top-24 (100 % mọi phút). Đây là chỉ số **báo cáo, không ngưỡng** theo prereg (OI + close 1h live nạp lúc chưa settle).

## 8. Funding — phần chưa đo được ở lượt D

- Vision **không có** fundingRate daily (404) và monthly tháng 10 chỉ phát hành đầu tháng 11 ⇒ lượt D **không có** funding của tháng hiện tại.
- Theo prereg: mọi chỉ số phụ thuộc funding (gate 3 cột; Tool1 f17–f25, f32) được **tiêm từ live** cho P1/NET; FUND chỉ chấm #1–40 bỏ các cột đó. Kết quả khớp của các cột funding khi so trực tiếp (0–37 %) là **kỳ vọng**, không dùng để phán quyết.
- OI f40–f44 khớp 37,1 % khi so trực tiếp — OI nằm ngoài phạm vi tái lập (đã tiêm live), đúng prereg §2.4.
- **Phán quyết chính thức P1/P2 phần funding: chờ lượt M** (khi Vision monthly `fundingRate` tháng 10 có ≥99 % symbol).

## 9. Kết luận theo §5 prereg

| Tiêu chí | Verdict |
|---|---|
| P1 | **ĐẠT** |
| P1-m | ĐẠT |
| P2 | **ĐẠT nhưng yếu** (0 lật nặng; 0 cặp r/q ≥ 0,9 ⇒ chưa thực sự thử) |
| P3 | **KHÔNG ĐẠT** (23/24 giờ; 1 giờ lệch 4,33e-3) |
| TSX | **ĐẠT** (cờ trùng OFF) |
| S1-I, S1-m, GV-I | **ĐẠT** (100 %) |
| GV-O, MD, NET, FUND | báo cáo, không ngưỡng |
| CTL | ĐẠT (gate bit 100 %, Tool1 dung sai 100 %) |
| K5 | **4 phút** (17:37, 17:38, 17:40, 23:59 +07) |

⇒ Trạng thái lượt D: **KHÔNG ĐẠT** — TRƯỢT ở P3 (1/24 giờ) và XÁM do K5 = 4. Các tiêu chí còn lại đều đạt. Không sửa ngưỡng; đề xuất điều tra P3 13:01 và 3 phút “15′ reference” trước lượt D2.

## 10. Artefact & an toàn

- Code: `research/parity_v11/` (harness commit `0bd019f7`) + `py/d1_eval.py`, `py/d1_labels.py`, `py/d1_s1v.py`, `py/d1_tsx_build.py`, `py/d1_report.py`.
- Dữ liệu/đầu ra Oracle: `~/claude_master/parity_v11w/{live,runs/d21,work,vision}`. JSON máy đọc: `docs/result/parity_v11_d1/parity_v11_d1.json`.
- 242: chỉ đọc; **không ghi file nào**; **không đọc Aerospike**; không Binance REST.
