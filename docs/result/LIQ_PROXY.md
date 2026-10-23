# LIQ_PROXY — chỉ báo THANH LÝ gián tiếp (OI rơi + giá sập + taker bán) cho entry crash-buy

Ngày đo: 2026-10-23. Pre-reg: `docs/prereg/PREREG_LIQ_PROXY.md`, commit **a468b743**, sha256 **e304fa445af0707f2c0e95068a7552989b48e7aadbd865f1cd28bfb6583e85b2** (chốt TRƯỚC khi dựng proxy/đọc kết quả).
Code: `docs/result/liq_proxy/build_proxies.py` sha256 **5cc285f2…0ea24edf**, `score_liq_proxy.py` **4415e508…e7e08369**, `checks_liq_proxy.py` **4973810a…e75546c224**, `v4_manual.py`. Hash ghi trong `code_sha.txt`; hash code được chốt trước khi chạy `score_liq_proxy.py`.

## 0. KẾT LUẬN (một dòng)

> **NO-GO cả 4 proxy.** Không proxy nào đạt tiêu chí "có cửa" (|IC| ≥ 0,10 cùng dấu ở khám phá VÀ kiểm; CI 95 % kỳ kiểm không chứa 0; IC tăng thêm ≥ 0,07; luật size thô ≥ +5k/seed). Proxy "cạn thanh lý" **không** thêm thông tin ổn định cho entry crash-buy. Chỉ `LM` có tín hiệu thống kê ở kỳ kiểm nhưng **đảo dấu** so với khám phá (+0,093 → −0,104 trên PnL); HO 2026 mô tả cũng âm (−0,105) ⇒ là đảo chiều theo chế độ, không phải edge ổn định. **Không đề xuất luật nào.** Muốn kiểm giả thuyết gốc cho đúng cần mua lịch sử `forceOrder` (liquidation thật) — xem §8.

## 1. Dữ liệu, lag, chống rò rỉ

| mục | giá trị |
|---|---|
| metrics 5m | `/home/ubuntu/vz/out/metrics5m/<year>/<yyyy-mm>.parquet` (Vision UM; `ts` = `create_time` nguyên xi, UTC) |
| kline 1m | `/home/ubuntu/vz_e1/raw/kline1m-<yyyy-mm>.parquet` (Vision UM, UTC) |
| printDone | `~/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}/storage/printDone.csv` |
| **lag OI chọn** | **10 phút tính từ `create_time`**; `g = floor((t−10′)/5′)×5′`, chỉ dùng bản ghi có `avail_ts = create_time + 5′ ≤ g`. Tương đương **≥ 5 phút sau khi kỳ 5m kết thúc** theo CẢ hai quy ước `create_time` (OLD/NEW); bảo thủ hơn NEW 5 phút. |
| giá/khối lượng | chỉ nến 1m đã đóng: `open_time ≤ g−1` |
| múi giờ | printDone `start` +07 → UTC (`−7h`); metrics/kline UTC. V2 xác nhận. |

Không hardcode mốc 2024-03-04, không dò quy ước per-(symbol,ngày); quy tắc lag 10′ an toàn cho cả hai quy ước (đánh đổi: nhóm OLD trễ thêm 5′). Không dùng 2020/2021.

## 2. Mẫu và phủ dữ liệu

Mẫu chính = cụm crash-buy, gộp 8 seed, khử trùng `(sym, anchor minute)`; `PnL cụm` = trung bình PnL các seed khớp. Mẫu phụ = tất cả leg tại các phút gate PASS (định nghĩa "phút gate-mở" của `RESULT_GATE_ABLATION` §4).

| kỳ | cụm | đợt sập | trung vị cụm/đợt | leg | arm +7 %/168h | PnL TB/median | MFE24 median | MAE24 median |
|---|---|---|---|---|---|---|---|---|
| Khám phá 2022–2023 | **2 523** | 30 | 64 | 2 634 | 81,0 % | +22,8 / +32,4 | +8,96 % | −5,04 % |
| Kiểm 2024–2025 | **2 538** | 32 | 56 | 2 660 | 87,3 % | +50,0 / +73,7 | +11,65 % | −7,88 % |

Phủ (cụm): `L1/L3/LM` **100 %** cả hai kỳ; `L2` **98,1 %** (khám phá) / **91,4 %** (kiểm) — thiếu vì symbol mới chưa đủ 7 ngày baseline; outcome `arm168/MFE24/MAE24` **100 %**, `win_complete` **99,94 %** (vài cụm vào cuối 12/2025 chưa đủ 168h). Phủ theo năm ở `liq_proxy_v1v4.json` (`V3`): L2 99,1 / 97,1 / 92,8 / 89,7 % cho 2022/23/24/25.

## 3. IC và IC tăng thêm

IC = Spearman(proxy tại `t`, outcome); IC tăng thêm = partial Spearman sau khi trừ hạng của `p15`, `oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`, `taker_buy15`. Mẫu cụm.

### 3.1 Khám phá 2022–2023

| proxy | IC arm168 | IC PnL | IC MFE24 | IC MAE24 | IC thêm (arm) | IC thêm (PnL) | n |
|---|---|---|---|---|---|---|---|
| L1 | −0,0664 | **+0,0349** | −0,0570 | −0,0063 | −0,0176 | +0,0420 | 2 523 |
| L2 | −0,0812 | +0,0041 | **−0,1094** | +0,0069 | −0,0276 | −0,0558 | 2 474 |
| L3 | −0,0130 | +0,0029 | +0,0093 | +0,0097 | +0,0217 | +0,0235 | 2 523 |
| LM | −0,0504 | **+0,0932** | −0,0173 | +0,0435 | −0,0138 | +0,0306 | 2 523 |

### 3.2 Kiểm 2024–2025

| proxy | IC arm168 | IC PnL | IC MFE24 | IC MAE24 | IC thêm (arm) | IC thêm (PnL) | n |
|---|---|---|---|---|---|---|---|
| L1 | −0,0527 | **−0,0601** | −0,0415 | +0,0048 | −0,0544 | −0,0387 | 2 538 |
| L2 | +0,0345 | +0,0548 | −0,0323 | +0,0270 | −0,0613 | +0,0577 | 2 323 |
| L3 | +0,0015 | +0,0411 | +0,0129 | −0,0101 | −0,0015 | +0,0373 | 2 538 |
| LM | −0,0040 | **−0,1037** | −0,0345 | −0,0184 | +0,0087 | **−0,0849** | 2 538 |

Đọc nhanh: không proxy nào có |IC| ≥ 0,10 **cùng dấu** ở cả hai kỳ. `L2` có IC MFE24 −0,109 ở khám phá nhưng chỉ −0,032 ở kiểm. `LM` đổi dấu ở outcome chính (PnL). Toàn bộ IC đều nhỏ; kể cả ô lớn nhất (LM −0,104) chỉ giải thích ~1 % hạng phương sai.

### 3.3 Bootstrap 95 % theo đợt (kỳ kiểm, cụm)

| proxy | outcome | lo | hi | nrep |
|---|---|---|---|---|
| L1 | arm168 | −0,1166 | +0,0028 | 2 000 |
| L1 | PnL | −0,1415 | +0,0081 | 2 000 |
| L2 | arm168 | −0,0231 | +0,0900 | 2 000 |
| L2 | PnL | −0,0276 | +0,1463 | 2 000 |
| L3 | arm168 | −0,0378 | +0,0421 | 2 000 |
| L3 | PnL | −0,0109 | +0,0962 | 2 000 |
| LM | arm168 | −0,0959 | +0,0827 | 2 000 |
| LM | PnL | **−0,1907** | **−0,0037** | 2 000 |

Chỉ `LM|PnL` có CI không chứa 0 — nhưng dấu **ngược** khám phá (xem §4). Không dùng CI này để tuyên bố edge.

## 4. Tiêu chí "có cửa" (prereg §8)

| proxy | outcome chọn | IC khám phá | IC kiểm | IC thêm kiểm | CI kiểm | C1 | C2 | C3 | direct/seed | C4 | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L1 | PnL | +0,0349 | −0,0601 | −0,0387 | [−0,1415; +0,0081] | ✗ | ✗ | ✗ | −622,8 | ✗ | **NO** |
| L2 | PnL | +0,0041 | +0,0548 | +0,0577 | [−0,0276; +0,1463] | ✗ | ✗ | ✗ | +873,9 | ✗ | **NO** |
| L3 | PnL | +0,0029 | +0,0411 | +0,0373 | [−0,0109; +0,0962] | ✗ | ✗ | ✗ | +536,1 | ✗ | **NO** |
| LM | PnL | +0,0932 | −0,1037 | −0,0849 | [−0,1907; −0,0037] | ✗ | ✓ | ✓ | −554,5 | ✗ | **NO** |

`direct/seed` = `Σ(w−1)×PnL_cụm / 8`, `w=1,5` đuôi thuận / `0,5` đuôi nghịch theo dấu IC **khám phá**, quintile 20 %. Với LM, vì dấu đảo, luật suy ra từ khám phá lỗ −555/seed ở kiểm. Không proxy nào đạt cả 4 điều kiện.

## 5. Bất ổn định — phần quan trọng nhất

### 5.1 IC theo năm (cụm, PnL)

| năm | L1 | L2 | L3 | LM | n |
|---|---|---|---|---|---|
| 2022 | −0,0625 | +0,0403 | −0,0198 | −0,0503 | 1 221 |
| 2023 | +0,0321 | −0,0837 | +0,0093 | **+0,0580** | 1 302 |
| 2024 | +0,0070 | +0,0816 | +0,0065 | −0,0338 | 1 477 |
| 2025 | −0,0736 | +0,1042 | +0,0663 | −0,0192 | 1 061 |

`LM` dương ở khám phá **chỉ nhờ 2023** (+0,058); 2022 và 2024 đã âm; sang 2025 vẫn âm. `L2` đổi dấu 2022→2023 rồi dương 2024/2025. `L1` âm ở 2022/2025, dương 2023/2024. Không proxy nào giữ dấu qua 4 năm.

### 5.2 LM theo episode (cụm, PnL, episode có n ≥ 30)

IC dao động **−0,488 … +0,565** trên 43 episode: âm mạnh ở 2023-08 (−0,49), 2022-06 (−0,37), 2022-07 (−0,35), 2023-11 (−0,29), 2024-04 (−0,27), 2025-10 (−0,25); dương mạnh ở 2022-11 (+0,57), 2022-06-17 (+0,41), 2024-06-07 (+0,35), 2025-11 (+0,29). Đây là nhiễu chế độ, không phải quan hệ ổn định.

### 5.3 HO 2026 (chỉ mô tả, không chấm)

HO dùng `tsx-ho-x14-s*` 8 seed, cùng định nghĩa proxy; 1 159 cụm (2026-01-19 → 2026-09-23), phủ L1/L3/LM 100 %, L2 92,1 %, outcome 100 %, arm 82,5 %, PnL TB +29,6. IC (cụm):

| proxy | arm168 | PnL | MFE24 | MAE24 |
|---|---|---|---|---|
| L1 | +0,0001 | +0,0120 | −0,0031 | +0,0543 |
| L2 | −0,0080 | −0,0262 | −0,0487 | +0,0697 |
| L3 | +0,0004 | −0,0273 | −0,0146 | +0,0095 |
| LM | −0,0242 | **−0,1048** | −0,0234 | −0,0863 |

`LM` PnL âm ở HO (−0,105), gần đúng mức âm của kỳ kiểm (−0,104) và ngược dấu khám phá (+0,093). Đây là mô tả, **không** dùng để chấm hay đề xuất; nó củng cố kết luận "đảo chiều theo chế độ" chứ không tạo edge theo prereg.

### 5.4 LM theo quintile (PnL TB, USD/cụm)

| kỳ | Q0 | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|---|
| Khám phá | 16,5 | 18,2 | 28,5 | 33,1 | 17,9 |
| Kiểm | 69,3 | 48,3 | 29,9 | 45,7 | 56,3 |

Không đơn điệu; ở kiểm Q0 (LM thấp nhất) lại tốt nhất — ngược dấu "LM cao = đã cạn = mua tốt". Đúng như IC −0,104.

## 6. Kiểm vệ sinh

| kiểm | kết quả |
|---|---|
| **V1 không look-ahead** | 3/3 cụm: nhân 3× mọi `oi/oi_value/tbq/qv/close` có ts > `t` ⇒ `L1/L2/L3/LM` tại `t` **không đổi** (Δ = 0). PASS. |
| **V2 múi giờ** | 3 cụm: `start` local +07 → UTC; `r60` tại UTC = −5,39 % / −1,08 % / −1,49 % (đúng bối cảnh sập); nếu hiểu `start` là UTC (lệch +7h) thì `L1` = 0 / 0 / +1,36 % — sai bối cảnh. Dùng UTC. PASS. |
| **V3 phủ** | L1/L3/LM 100 %; L2 98,1/91,4 %; outcome 100 %. PASS (có ghi rõ chỗ thiếu). |
| **V4 tái lập tay** | 3 cụm (2023-12-11, 2023-11-16, 2025-11-21): `L1/L2/L3/LM` khớp pipeline < 1e-6 (thực tế ≤ 4e-8). PASS. |

Chi tiết: `liq_proxy_v1v4.json`, `v4_manual.json`, `v2_tz.json`.

## 7. Bất thường / giới hạn

1. **LM đảo dấu** (+0,093 khám phá → −0,104 kiểm; CI kiểm [−0,191; −0,004]). Đây là bất thường chính. Nếu chỉ nhìn kỳ kiểm sẽ tưởng có edge "LM cao ⇒ PnL xấu", nhưng khám phá ngược lại; không đủ để đề xuất, và đi ngược tiêu chí prereg.
2. **L3 outlier**: HOLOUSDT 2025-09-11 có `L3 = −1,917` do OI 15′ trước gần 0 (symbol mới/thanh khoản mỏng). Không winsorize theo prereg; Spearman chịu được, nhưng là lý do nên xem L3 là proxy nhiễu.
3. **L2 phủ giảm theo năm** (99,1 → 89,7 %) vì symbol mới chưa đủ 7 ngày baseline; kết quả L2 ở 2024/2025 dựa trên mẫu thiên về symbol cũ.
4. **Partial IC n nhỏ hơn**: 1 585/2 523 (khám phá) và 2 418/2 538 (kiểm) do `ls_toptrader` chỉ phủ 63,2 % ở 2022–2023 (100 % ở 2024–2025) và một phần `oi_delta24h`/`ls_global` thiếu ở symbol mới. IC tăng thêm chỉ đọc trên mẫu con này.
5. **Quy ước `create_time`** không đồng nhất theo symbol; lag 10′ bảo thủ cho cả hai. Nhóm OLD bị trễ thêm 5′ so với NEW — làm proxy yếu hơn, không gây leak.
6. **8 seed không độc lập**; đã khử trùng cụm và bootstrap theo đợt, nhưng cụm vẫn có thể trùng lặp theo không gian (nhiều symbol cùng một đợt sập).
7. **HO 2026 chỉ mô tả**: kline 1m 2026 lấy từ Kaggle `chuyendinh/vz-kline1m-2026` (9 file, ~5,4 GB) sau khi verdict đã đóng; không dùng chấm. Kết quả §5.3 xác nhận `LM` âm ở 2026, nhưng không làm thay đổi tiêu chí hay verdict.
8. **Không có liquidation thật**: OI giảm có thể do đóng vị thế chủ động, không chỉ forceOrder. Đây là giới hạn bản chất của proxy, không phải lỗi tính toán.

## 8. Dữ liệu cần mua để kiểm thật

Proxy OI/taker **không** thay được liquidation thật. Để kiểm giả thuyết "thanh lý dây chuyền đã cạn":

- **Binance UM `forceOrder` / liquidation snapshot** (websocket hoặc lịch sử), tối thiểu: `symbol`, `timestamp` (ms), `side` (BUY/SELL), `price`, `avgPrice`, `origQty`, `executedQty`, `timeInForce`, `orderStatus`.
- Phủ **2022-01-01 → 2025-12-31** (và 2026 nếu muốn HO), **toàn bộ symbol USDT-M** đã niêm yết, không chỉ top.
- Tần suất: event-level; nếu chỉ có snapshot 1s/1m thì ghi rõ.
- Cần thêm `forceOrder` theo `symbol` + `ts` để dựng L1' = notional thanh lý bán 60′ / OI, L2' = tỷ lệ thanh lý bán / tổng khối lượng, L3' = gia tốc thanh lý; khi đó mới kiểm đúng "cạn".

Nếu không mua được: giữ kết luận **đóng proxy**, không mở rộng vòng này.

## 9. Đầu ra & tái lập

```
docs/result/liq_proxy/
  build_proxies.py        # samples / aux / proxies / outcomes
  score_liq_proxy.py      # IC, partial IC, bootstrap, criteria
  checks_liq_proxy.py     # V1-V4
  v4_manual.py            # V4 tái lập tay
  samples.csv             # mẫu thô (clusters + legs)
  samples_proxy.csv       # + proxy/control
  samples_outcome.csv     # + arm168/PnL/MFE24/MAE24
  aux_daily.csv, aux_l2.csv
  liq_proxy_ic.json       # bảng IC + bootstrap + criteria
  liq_proxy_tables.md     # bảng IC đầy đủ
  liq_proxy_v1v4.json     # V1/V3/V4
  v2_tz.json, v4_manual.json
  posthoc.json            # IC theo năm/episode, quintile
  ho_descriptive.py       # HO 2026 mô tả (script riêng)
  ho_samples*.csv, ho_aux_*.csv, ho_ic.json
  code_sha.txt
```

Chạy lại (DEV): `python3 build_proxies.py samples && python3 build_proxies.py aux && python3 build_proxies.py proxies && python3 build_proxies.py outcomes && python3 score_liq_proxy.py && python3 checks_liq_proxy.py && python3 v4_manual.py`.
HO mô tả: `python3 ho_descriptive.py samples && python3 ho_descriptive.py aux && python3 ho_descriptive.py proxies && python3 ho_descriptive.py outcomes && python3 ho_descriptive.py score`.

## 10. Đề xuất

**Không đề xuất luật nào.** Không đạt tiêu chí "có cửa"; proxy đóng. Vòng sau chỉ nên mở lại nếu có `forceOrder` thật, với prereg mới đọc trước khi đo. Ghi nhận (không phải đề xuất): `LM` âm ở 2024–2026 và dương ở 2022–2023 — nếu owner muốn theo dõi, phải prereg riêng cho giả thuyết "đảo chiều chế độ", không tái dùng vòng này.
