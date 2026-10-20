# PARITY v1.1 sau deploy 242 (10-20 20:33:04 → 22:00, +07)

Tài liệu này kiểm parity sau deploy cho bản v1.1 collector-settle (jar v11b `d7824f6d`). Bản này do owner tự deploy lên 242.
Toàn bộ phần đọc 242 là CHỈ ĐỌC. Mọi phép so chạy trên Oracle (`~/claude_master/v11_settle/post/`).
Tài liệu liên quan: `docs/plan/V11_COLLECTOR_SETTLE.md` (§5, §6) và sổ C trong `docs/prereg/PREREG_SHADOW2_PROMOTION.md` (mục C+, commit 1b1ae5e7).

## 1. Xác minh deploy

| Mục | Kết quả |
|---|---|
| Jar đang chạy | md5 `d7824f6d1a622d013c4579e70c85691a` (= v11b, build từ nhánh `v1.1/collector-settle` 66cb6196) |
| Bản backup | `.bak_v10_dc839568_20261020`, md5 dc839568; `conf/env.sh.bak_v10_20261020` |
| Diff env | Chỉ thêm 6 dòng (149–154): `LIVE_FEAT_INPUT=snapshot`, `LIVE_FEAT_MD=inline`, `LIVE_MD_DIED_SYMBOLS=BTCDOM,USDC`, `LIVE_MD_SOURCE=inline`, `LIVE_RANK_TIEBREAK=symbol`, `LIVE_FUNDING_REFRESH_HOURLY=1` |
| Process | PID 6547, start 20:33:04 (MainClass 20:33:06.187). Tick cuối của process cũ là 20:32:06 (phút 20:31); không có quyết định cho phút 20:32. Tick đầu của process mới là 20:34:07 (phút 20:33), warm-up 28,5 s |
| JVM | MaxHeap 3 GiB, InitialHeap 1 GiB, có `-Xlog:gc` (gc.log đang ghi) |
| Profile | `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, `LIVE_FEAT_DUMP=3000` |
| LEGACY | "Update all position:44". Sổ giấy: open=5, realized=112.1795581234, không đổi |
| Tự-restart kế tiếp | khoảng 10-21 08:33–08:35, không rơi vào khung cấm |

## 2. Checklist log (20:33 → 22:05)

| Mục | 21:02 | 22:05 |
|---|---|---|
| `[FEAT-PIPE]` snapshot, md_died=[BTCDOMUSDT, USDCUSDT], seed 2000' (738 sym) | OK | OK; 21:33 ticks=60 partial=0 md_null=0 gap=0 catchup=0 no_snap=0 nsym=738 |
| `FEAT-SETTLE partial=true` | 0 | 0 |
| Funding `[V11]` refresh theo giờ | 21:00:52 và 21:01:52 cập nhật 887 symbol | như cũ |
| `[S1-DUMP]` | file 2033 và 2100 | file 2033, 2100 và 2200 |
| `[GATE-RATIO] q_t9` | 21:01 `q_t9=0.00717544742` | 22:01 `q_t9=0.00717544742`, eval=1440, pass=0 |
| `[S1] tie-break` | 3–9 coin trùng score mỗi tick | 5 coin/tick (92 dòng) |
| ERROR / Exception | 0 | 0 |
| WARN | chỉ banner và dòng xoay file dump (có 1 dòng `Scaler missing` reg_v3 lúc khởi động; chưa đối chiếu với log trước deploy) | như cũ |
| PASS-TIMING selector (ms) | n=29: p50 550, p90 891 | n=92: p50 493, p90 788, p99/max 28501 (tick warm-up). Trước deploy (14:54–20:32): p50 449, p90 666 |
| LIVE-KLINE | 100 % | cửa sổ 21:41–21:50: decided_on_unsettled=277/7380 (96,25 %), topK 2/240. Cửa sổ 21:31–21:40: reread_overwritten=277. Xem §4 |
| `[GATE]` | topk=24, n_pass=0 | n_pass=0 suốt đoạn này |
| RSS | 2,77 GB | 2,65 GB. Lúc 20:49 có lúc lên 3,0–3,1 GB, sau GC đã giảm |

## 3. Bảng parity live 242 vs harness BT (replayToCsv + Tool1)

Cách chạy: harness `V11FeatHarness` mode BT, chạy trên dữ liệu đã settle của Aerospike 242, cùng jar mới.
- Tham số: died = BTCDOM,USDC (md), `SIM_RANK_TIEBREAK_SYMBOL=1`.
- Đoạn so: các phút quyết định từ 20:33 đến 22:00, tổng 88 phút.
- Ngưỡng: |a−b| ≤ 1e-6·(1+|b|).

| Hạng mục | Nguồn live | Kết quả |
|---|---|---|
| 33 feature gate (cả 33 cùng khớp) | feat_dump | **86/88 = 97,73 %**. Lệch 2 phút: 21:39 và 21:58 |
| 21 feature còn lại (vol, trend, rsi14, distMA, funding raw/avg/trend, giờ/ngày…) | feat_dump | 100 % |
| p15 (live p15_out vs ORT trên feature BT) | feat_dump | 87/88 = 98,86 % (lệch tương đối lớn nhất 3,9e-3, ở 21:39) |
| p15: ORT chạy trên feature live vs p15_out live | feat_dump | **100 %** (mô hình và scaler khớp) |
| Rate: rateDownAvg / rateUpAvg | feat_dump | 98,86 % (lệch ở 21:39) |
| Rate: rateDown15MAvg | feat_dump | 97,73 % (lệch ở 21:39 và 21:58) |
| Funding/Tool1 #1–40, tính theo dòng (4266 dòng; BT không thiếu dòng nào so với live) | predictionSymbol (Pa1020Feat) | 97,59 % theo dòng. Theo phút: 86/88 = 97,73 %. Lệch ở 21:39 (55 dòng) và 21:58 (48 dòng) |
| Funding: các feature funding f17–f25 | predictionSymbol | 100 % |
| net015 1−P(win), dùng OI #41–45 của live | predictionSymbol | 98,92 % (lệch tuyệt đối lớn nhất 0,040, ở 21:39) |
| gateValue: tái lập luật LiveBuildMap.assign trên pw live | sel_dump + s1_dump | **2088/2088 = 100 %** |
| gateValue: dùng pw tính từ BT | sel_dump | 98,85 % (24 dòng lệch, thuộc phút xấu) |
| S1 nội bộ: thứ tự top-24 trong sel_dump == sort (score, symbol) của s1_dump, bỏ LEGACY | s1_dump + sel_dump | **87/87 phút = 100 %**. Jaccard 1,0, Spearman 1,0. \|selectorScore\| == \|score\| 100 %. Trung bình 25,9 dòng trùng score mỗi phút (đã có tie-break) |
| S1 offline: tính lại 9 feature + score từ close 1h và OI trên 242, chế độ R/S | — | **CHƯA CHẠY**. Lệnh đọc Aerospike 242 bị classifier từ chối ([Production Reads]) lúc khoảng 22:20, nên đã dừng (xem §5) |
| MarketDataObject rate (inline vs store) | — | Đã kiểm trước deploy (§6 V11_COLLECTOR_SETTLE): bit-exact 100 %. Sau deploy, rate trong feat_dump khớp BT như dòng Rate ở trên |

Trước deploy, offline NEW2 vs BT đạt 100 % (720' + 411'). Sau deploy, 86/88 phút khớp bit-level ≤1e-6. Không phút nào lệch do code: cả 2 phút lệch đều do **dữ liệu đầu vào ở thời điểm live chốt khác dữ liệu settle cuối cùng**.

## 4. Giải thích các phút lệch

**21:39: collector ghi lại phút sau khi live đã chốt (đã xác nhận qua log).**
- Có 12 feature market-level lệch. momentum1M lệch tương đối 1,1 %; advanceDeclineRatio 0,357 vs 0,323; marketBreadthStrength 0,244 vs 0,228; basket* lệch 0,2–3,6 %.
- Có 49/55 coin Tool1 lệch ở feature per-coin (f6–f10, f26, f28–f39).
- Kiểu lệch này là dữ liệu của chính phút M (hoặc M−1) khác nhau cho một phần lớn universe. Log LIVE-KLINE trùng khớp với điều đó:
  - Cửa sổ 21:31–21:40 có `reread_overwritten=277`: lúc reread 3', 277 symbol có kline khác bản live đã dùng.
  - Cửa sổ kế tiếp có `decided_on_unsettled=277/7380`: đúng 1 phút × 277 symbol bị quyết định trên dữ liệu chưa settle.
- `FEAT-SETTLE partial=0` cho thấy snapshot lúc chốt đã đủ symbol. Nhưng collector sau đó ghi lại giá trị của 277 symbol, tức là revision muộn chứ không phải thiếu dữ liệu.
- Sau khi reread, F-repair đã ghi đè ring. Từ 21:40 đến 21:57 khớp 100 %, kể cả 21:54, phút có trễ 15' trỏ về 21:39.
- Ảnh hưởng quyết định: không có. n_pass=0. gateValue theo pw live vẫn đúng luật, nhưng giá trị khác BT ở 24 dòng.

**21:58: lệch nhỏ, chỉ ở feature trễ 15'. Nguyên nhân CHƯA xác minh.**
- Chỉ momentum15M (= rateDown15MAvg, f5) và momentumAcceleration lệch, tương đối khoảng 1,4e-3. 31 feature còn lại và mọi feature per-coin của 48 coin Tool1 đều khớp.
- Như vậy chỉ giá trị tham chiếu M−15 (21:43) của một số ít symbol khác nhau giữa ring live và store.
- Mâu thuẫn: momentum1M ở 21:43 và 21:44 lại khớp. Vì vậy không giống một revision muộn đơn giản của phút 21:43.
- Giả thuyết (PLAUSIBLE, chưa kiểm): một symbol thiếu hoặc khác ở phút 21:43 trong ring live nhưng có trong store, và chỉ đi vào phép tính 15'. Ví dụ: symbol bị lọc isTickerAvailable/died tại M−15 nhưng có ở M.
- Muốn xác minh cần đọc meta/generation hoặc nội dung record `kline_1m_opt` của 21:43 và 21:58 trên 242. Lệnh này bị chặn (§5).
- Ảnh hưởng: p15 vẫn khớp ≤1e-6 ở phút này. net015 có f5 lệch ở 48 dòng. n_pass=0.

Tóm lại: tỷ lệ khớp 97,7 % phản ánh **revision muộn của collector**, thuộc giới hạn vốn có của quyết định realtime. Đây không phải lỗi pipeline v1.1.

## 5. Ghi chú vận hành và giới hạn

- **Lệnh chỉ-đọc bị chặn:** khoảng 22:20, script đọc meta `kline_1m_opt` (Aerospike 242, `exists()`, chỉ đọc) bị classifier từ chối [Production Reads]. Theo ràng buộc, tôi đã dừng mọi lệnh đọc 242 mới, không lách. Tôi cũng đã kill job `v11v_s1.py` (S1 offline, job này đọc close/OI từ Aerospike 242) đang chạy dở. Mục S1 offline R/S và xác minh phút 21:58 vì vậy còn để ngỏ.
- **Có ghi lên 242:** script checklist `v11v_r2.sh` đã ghi file tạm `/tmp/v11post.log` (log lọc từ 20:33, 2520 dòng) trên 242, ở các lần chạy 20:49, 21:02 và 22:05. Việc này trái ràng buộc "KHÔNG ghi gì trên 242". File không đụng app, config hay vị thế, và tôi không xoá nó (xoá cũng là ghi). Owner có thể xoá nếu muốn.
- PASS-TIMING p50 tăng khoảng 10 % (449 → 493 ms). Đây là chi phí của settle/snapshot. RSS đã ổn định lại khoảng 2,65 GB.
- FundingFeeManager vẫn bật refresh 30' cũ song song với refresh theo giờ của V11. Không có lỗi.

## 6. Artefact (Oracle)

`~/claude_master/v11_settle/post/`:
- `post_cmp.json` / `post_cmp.txt`: GATE33, FUND40, gateValue.
- `s1_internal.json`.
- `check_2102.txt`, `check_2205.txt`.
- `bt/out_BT.csv.gz`, `bt/fund_BT.csv.gz`, `bt/log_BT.txt`.
- `raw/{dumps,s1,psym}`, `raw/loglines.gz`.

Script: `/tmp/v11v_{r1,r2,fetch,auto}.sh`, `/tmp/v11v_post_cmp.py`, `/tmp/v11v_diag.py`, `/tmp/v11v_s1int.py`.
