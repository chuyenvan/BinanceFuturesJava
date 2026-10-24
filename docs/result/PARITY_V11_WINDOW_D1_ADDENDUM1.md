# PARITY v1.1 — lượt D1 (2026-10-21 UTC) — ADDENDUM 1: chấm lại sau audit OC1023

- **Ngày:** 2026-10-24 (+07). **Prereg:** `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (`481701b2`) — **KHÔNG đổi** nguồn, universe, ngưỡng, luật phân loại.
- **Result gốc:** `docs/result/PARITY_V11_WINDOW_D1.md` (`ab5bbe44`). **Harness:** `research/parity_v11/` (`0bd019f7`). **Sửa code chấm:** commit `5f8e7291` (`fix(parity_v11 D1 scorer)`).
- **Ràng buộc:** không đụng 242 / Aerospike 242 / Binance REST. Mọi dữ liệu dùng ở đây đã có sẵn trên Oracle (`~/claude_master/parity_v11w/`), gồm log 10-22 00:00–07:05 (+07) owner kéo ngày 10-24.

## 0. Kết luận (risk-first)

**Verdict D1 theo prereg §5: ĐẠT** (sơ bộ cho phần phụ thuộc funding; phán quyết chính thức P1/P2-funding ở lượt M). Gốc: TRƯỢT P3 + XÁM (K5 = 4) → sửa: P1/P2/P3/TSX/S1-I/GV-I/CTL đạt ngưỡng, K5 = 0.

Điểm rủi ro, xếp theo mức độ:
1. **P2 chưa thật sự được thử.** 33 264 cặp, không có cặp nào ở r/q ≥ 0,9 (max 0,8913; chỉ 6 cặp ≥ 0,8). Ở cả live lẫn offline đều 0 pass. "0 lật nặng" là điều kiện cần nhưng yếu.
2. **K5 = 0 là kết quả cơ học, không phải bằng chứng.** Khi áp đúng nhãn K3, nhãn này phủ **1387/1387 phút** của cửa sổ: trước 16:54 (+07) `nsym` live = 738 ≠ |U_D| = 741, còn từ 16:00–16:10 (+07) có 3 symbol niêm yết, nên mọi phút sau đó đều có "U đổi trong [M−1440′, M]". Vì vậy nhãn K không phân biệt được phút nào trong ngày D1. Ba phút "15′ reference" có một giả thuyết mạnh (§7.1) nhưng **vẫn CHƯA GIẢI THÍCH**.
3. **Log `[GATE]` gây hiểu nhầm (không phải lỗi parity).** Khoảng `thr=[a..b]` được in bằng `EntryGate.threshold()`, tức base tĩnh `MIN_MOMENTUM_15M = 0,008`, chứ không phải ngưỡng ratio q_t. Còn `n_pass` = n_cand − n_rej, trong đó n_rej chỉ đếm REJECT của gate. Ứng viên bị bỏ vì thiếu prediction vì thế vẫn được đếm là "pass" (10-21 07:54:38: `n_pass=24`). `check_242_failopen_1024_0819.txt` xác nhận sự cố này **fail-closed về hiệu quả** (xem §7.4).
4. **Code chấm vẫn hard-code ngày D1** (T0/T1, glob `2026102[12]`, `LOGS`, `DAY_D`). Phải tham số hoá trước lượt D2.
5. Phát hiện thêm ngoài audit (đã sửa, nêu ở §2):
   - 7 file psym 10-22 00:00–00:06 **có sẵn** trên Oracle. Lượt gốc ghi "live thiếu" là **sai**.
   - Dòng `[GATE]` bị map lệch 1 tick.
   - Nguồn phút lệch theo §5 thiếu MD/P1/S1-V. Riêng S1-V có 601 phút lệch chưa từng được gán nhãn.

## 1. Lý do làm lại (audit `docs/audit/OC1023_AUDIT.md`, mục parity_d1)

- **CRIT-1** — map giờ q_t9 sai. `LiveGateRollingRatio.noteCandidate()` gọi `logHour()` khi sang giờ mới, nên dòng `[GATE-RATIO]` in lúc giờ h+1 (+07 log) là q của **giờ UTC h**. Mã nguồn `627e9b34` xác nhận: `noteCandidate` → `logHour()` in `buffer.currentQ()` trước khi reset bộ đếm giờ. Lượt gốc map theo giờ ghi log, gây ra "13:01 lệch 4,33e-3" và lời giải thích "record buffer bị ghi đè" — lời giải thích này **không có bằng chứng** và nay được rút lại.
- **CRIT-2** — `d1_labels.py:82` gán K3 cho phút **trước** mốc đổi U (`t < first741 <= t+1440`), trong khi prereg §5 định nghĩa K3 là U đổi trong [M−1440′, M].
- **MAJ-1** — log chỉ có ngày local 10-21. Hệ quả:
  - P2 âm thầm chỉ chấm 966/1386 phút (dropna).
  - P3 "23/24" gồm 8 dòng trước cửa sổ và thiếu 8 giờ trong cửa sổ.
- **MIN:**
  - Phía offline của P2 dùng q log live (đã lệch giờ) thay vì q replay.
  - Cờ `match6` luôn False (so 9 chữ số với 6 chữ số).
  - FUND/NET có mẫu số 1380.

## 2. Thay đổi code (commit `5f8e7291`, chỉ code chấm, không đụng harness/thước)

| # | file | thay đổi |
|---|---|---|
| 1 | `py/d1_eval.py` `qlog_by_hour()` | Dòng `[GATE-RATIO]` lúc t_log được gán cho giờ UTC `h = floor(t_log/H)·H − H`. |
| 2 | `py/d1_eval.py` `stage_p3` | Chỉ so 24 giờ UTC của cửa sổ (00–23 UTC 10-21) với q replay từ `gate_ratio_live.bin`. Luật replay giữ nguyên `ab5bbe44`: ts ∈ [h−90d, h); giờ có restart dùng record flush trước restart. Tiêu chí `rel ≤ 1e-6`; **bỏ `match6`**. Thêm phép kiểm `m == buffer_log − eval_log`. |
| 3 | `py/d1_eval.py` `stage_gv_p2` | **Offline** dùng q REPLAY (đúng prereg §4 P2). **Live** dùng q log đã map đúng giờ. Trong giờ có restart (12 UTC), tick < phút-restart − 1′ do process cũ quyết định với q đầu giờ (process cũ tắt trước h+1 nên không có dòng log), nên dùng q replay normal và ghi rõ `q_src`. |
| 4 | `py/d1_eval.py` (`[GATE]` log) | Map dòng `[GATE]` về tick = phút ghi log − 1′, kiểm 426/426 bằng `[MAP] tick=` của log 10-22. Lượt gốc map theo phút ghi log (lệch 1 tick). Thêm kiểm khoảng `thr=[..]` với base tĩnh 0,008 (§0 mục 3) để xác nhận fac/gv/tick. |
| 5 | `py/d1_eval.py` `loglines()` | Nối `raw/loglines_1021.gz` với `full_1022_0000_0705.log.gz`. |
| 6 | `py/d1_eval.py` `load_live45()` + `sh/psym_c_build.sh` | Giải mã 7 file `predictionSymbol` 1792602000000…1792602360000 (10-22 00:00–00:06 +07) bằng `Pa1020Feat` (jar v11c, stub Aerospike đứng trước) thành `live/feat45_live_c.csv.gz`. Kiểm: giải mã lại 00:07 → 694/694 dòng **trùng bit** với `feat45_live_b`. |
| 7 | `py/d1_labels.py` (viết lại) | **K3** = (`nsym` live gần nhất ≠ \|U_D\|) **hoặc** có mốc đổi U ∈ [M−1440′, M], với mốc = nến Vision đầu tiên của symbol mới. Nguồn phút lệch đủ theo §5: P1-F, P1 (rel > 1e-3), MD, FUND, NET, GV-O, S1-V. Thêm K2a (lỗ Vision), K2b (`[TS-EXT] day … n_min` < 1440), K2c (bộ đếm `[FEAT-PIPE]` tăng). |
| 8 | `py/d1_add1_report.py` | JSON gốc vs sửa, verdict tính từ số: `docs/result/parity_v11_d1/parity_v11_d1_add1.json`. |

## 3. Dữ liệu bổ sung và độ phủ

| mục | kiểm | kết quả |
|---|---|---|
| `live/full_1022_0000_0705.log.gz` | 11 278 dòng, md5 `3726f353…`, 22/10 00:00:00.246 → 07:05:30.111 (+07) | đủ |
| `[GATE]` (n_pass, thr) | 1 dòng/phút | **426/426 phút** (00:00–07:05) |
| `[MAP] tick=` | 1 dòng/phút, ngay trước `[GATE]` | 426/426; tick = phút log − 1′: **426/426** |
| `[GATE-RATIO]` | 1 dòng/giờ | 8 dòng (00:01 … 07:01) = q các giờ 16…23 UTC 10-21 (+ 23 UTC = dòng 07:01) |
| `[LIVE-KLINE]`, `[FEAT-PIPE]`, `[TS-EXT]` | có | 51 / 7 / 20 dòng; FEAT-PIPE `partial=gap=no_snap=0`, `nsym=741` |
| `MainClass` (restart) 10-22 00:00–07:05 | — | không có restart |
| **P2: r/q từng ứng viên** | log không in p15/thr từng ứng viên | **không cần**: P2 tính lại từ `sel_dump` (p15, gateValue) + q đã map; log chỉ dùng để kiểm `n_pass` và khoảng thr |
| psym 10-22 00:00–00:06 | 7 file trong `live/psym/`, mtime 00:01:06…00:07:06 (+07) đúng nhịp ghi live | **đo được** (đã giải mã, §2 mục 6) |
| feat_dump 10-22 00:00–00:06 | có sẵn từ lượt gốc | đo được |

⇒ Không còn phần nào của D1 ở trạng thái "KHÔNG ĐO ĐƯỢC" do thiếu dữ liệu. Phút 10-21 07:53 vẫn bị loại theo §4 (warm-up restart, không có dòng `feat_dump`).

## 4. Bảng gốc (`ab5bbe44`) → sửa (ADD1)

Dung sai một giá trị: `|a−b| ≤ 1e-6·(1+|b|)`. Cửa sổ: `1792543980000 … 1792627140000` = 10-21 07:53 → 10-22 06:59 (+07).

| mã | ngưỡng | gốc ab5bbe44 | sửa ADD1 | verdict sửa |
|---|---|---|---|---|
| **P1** | median rel ≤ 1e-4 **và** ≥ 98 % phút ≤ 1e-3 | median 6,04e-10; 99,9278 %; n 1386 | **không đổi**: median 6,041e-10; 99,9278 % (1385/1386); max 1,12e-3 (23:59) | **ĐẠT** |
| P1-m | 100 % ≤ 1e-6 | 100 % (max 3,66e-7) | không đổi | ĐẠT |
| P1-F (30 cột) | báo cáo | 1378/1386 | không đổi (8 phút) | — |
| MD | báo cáo | 99,7835 / 99,8557 / 99,4228 % | không đổi | — |
| FUND (#1–40 bỏ funding) | báo cáo | 45 101 dòng, 99,341 %; phút 1371/**1380** | 45 353 dòng, 99,345 %; phút **1378/1387** (99,351 %); 7 phút mới đều khớp | — |
| NET | báo cáo | 99,9357 %; phút 1377/1380 | 99,936 %; phút **1384/1387**; max \|Δ\| 0,00786 | — |
| **S1-I** | 100 % | 1387/1387 | không đổi | **ĐẠT** |
| S1-m | 100 % | 940 226 dòng, max 0 | không đổi | ĐẠT |
| **GV-I** | 100 % | 33 120/33 120 (1380 phút) | **33 288/33 288 (1387 phút)** | **ĐẠT** |
| GV-O | báo cáo | 99,9698 % (10 dòng) | 99,9700 % (10 dòng; 07:53, 23:59) | — |
| **P2** | lật nặng = 0 | 23 184 cặp / **966** phút; q log lệch giờ cho cả 2 phía; 0 lật | **33 264 cặp / 1386 phút** (loại 07:53: không có p15_off); q_off = replay; q_live = log map đúng (1333 phút) + replay-normal trước restart 19:54 (+07) (53 phút 12:00–12:52 UTC); **0 lật, 0 lật nặng**; max r/q live 0,8913 / off 0,8913; **0 cặp ≥ 0,9** (6 cặp ≥ 0,8) | **ĐẠT (yếu)** |
| `[GATE] n_pass` log == tính lại | báo cáo (thuộc P2) | 965/966 (lệch 07:54) | **1386/1386** (map tick); khoảng `thr` log (base 0,008) khớp **1386/1386**; dòng `n_pass=24` thuộc tick 07:53 = phút bị loại | — |
| **P3** | rel ≤ 1e-6 **mọi giờ** | 23/24 (gồm 8 dòng ngoài cửa sổ; 13:01 rel 4,33e-3); thiếu 8 giờ trong cửa sổ | **24/24 giờ UTC (00–23) trong cửa sổ**; max rel 4,14e-10, median 2,71e-10; `m == buffer_log − eval_log` 24/24; 2 giờ restart (00, 12 UTC) khớp; 8 dòng trước cửa sổ cũng khớp (tham khảo) | **ĐẠT** |
| **TSX** | cờ trùng | live OFF vs Vision OFF | không đổi; log 10-22 xác nhận `flagToday=OFF dd=−0,137179` đến 06:00 (+07), 07:00 `PENDING` (ngày 10-22) | **ĐẠT** |
| **CTL** | 100 % | gate bit 100 %; Tool1 dung sai 100 % | không chạy lại (không đổi) | **ĐẠT** |
| Nhãn §5 | K5 = 0 cho ĐẠT | 9 phút lệch: K1 4, K3 2, **K5 4** | **604 phút lệch** (P1-F 8, FUND 9, NET 3, GV-O 2, P1 1, MD 8, **S1-V 601**): K1 69, K2a/b/c 0, **K3 604**, **K5 0**; K3 phủ 1387/1387 phút cửa sổ | — |

## 5. Kiểm độc lập

- **P3 — `audit_oc1023/audA/p3_audit.py`:** chỉ đổi đường dẫn log để nối thêm log 10-22 (bản sao `~/claude_master/pard1fix_wk/p3_audit_2log.py`, diff 1 dòng), logic giữ nguyên. Buffer: 736 464 record, 0 chunk lỗi, đã sắp xếp. Kết quả: **24/24 dòng trong cửa sổ** (log 10-21 08:01 → 10-22 07:01 +07) có `q_log` == replay `ts < giờ-q` tới 9 chữ số, gồm cả 2 giờ restart. Lớp kiểm này của audit dùng luật "normal" cho cả giờ restart mà vẫn khớp.
- **P1 — `audA/p1_audit.py`** (chạy nguyên bản): median rel 6,041e-10, ≤ 1e-3 99,928 %, max 1,120e-3, n 1386; P1-m max 3,657e-7; P1-F 1378/1386, 8 phút lệch giống nhau. **Khớp** `stage_gate`.
- **Tái lập độc lập `rateDown15MAvg`** (`py/inv_rdown15.py`): viết lại theo mã jar (`MarketDataInlineGenerator.update` + `MarketBigChangeDetector.calMarketData`, float32), không import harness, đọc Vision zip trực tiếp. Kết quả: **66/66 phút bit-exact với OFF-BT** trên 16:55–18:00 (warm-up 8 h).

## 6. Nhãn K (§5, cơ học)

| phút (+07) | nguồn lệch | nhãn sửa | nhãn gốc |
|---|---|---|---|
| 10-21 07:53 | FUND, NET, GV-O (phút loại khỏi P1) | K3 | K3 |
| 10-21 11:59 | P1-F, MD, FUND, NET | K1, K3 | K1, K3 |
| 10-21 17:04, 17:16, 17:18 | P1-F, MD, FUND, S1-V | K1, K3 | K1 |
| 10-21 17:37, 17:38, 17:40 | P1-F, MD, FUND (+S1-V 17:38/17:40) | **K3** | K5 |
| 10-21 23:59 | P1-F, P1, MD, FUND, NET, GV-O, S1-V | **K1**, K3 | K5 |
| 595 phút khác | chỉ S1-V (cột rank f2/f5, 2 dòng/phút) | K3 (+K1 ở 64 phút) | (không được gán ở gốc) |

- Mốc đổi U (nến Vision đầu tiên): CEGUSDT 16:00, BACUSDT 16:05, IBKRUSDT 16:10 (+07, 10-21). Không có symbol mới nào trong U_D ở 10-20.
- Lỗ Vision (K2a): 0 trên U_D cho 10-20 và 10-21. `[TS-EXT] day 2026-10-21 n_min=1440` nên K2b = 0. FEAT-PIPE không có khối nào bị cờ, nên K2c = 0.
- 23:59 nay có K1 nhờ log 10-22: cửa sổ `[LIVE-KLINE]` kết thúc 00:01 có `reread_overwritten=215`, cửa sổ 00:11 có `decided_on_unsettled=214`.

## 7. Điều tra (mô tả, không đổi verdict)

### 7.1 Ba phút "15′ reference" 17:37 / 17:38 / 17:40 (+07) — **CHƯA GIẢI THÍCH**, có một giả thuyết mạnh

**Feature lệch.** Chỉ có `momentum15M` và `momentumAcceleration` (cùng `f5` của Tool1 trên mọi dòng):
- `momentum15M = rateDown15MAvg` = trung bình 100 giá trị thấp nhất của `close/max(high trên 15 NẾN KHẢ DỤNG gần nhất)−1` trên toàn universe. "Khả dụng" = `low≠high || quoteVol≠0`. Các key được khử trùng bằng TreeMap\<Float>; N = min(100, size·4/5).
- `momentumAcceleration = momentum5M − momentum15M`.
- Độ lệch: |Δ| ≈ 1,17e-5. Nhân với N = 100 thì tương đương ~1,2e-3 trên **một** symbol.

**Không phải symbol mới.** BAC/CEG/IBKR không đủ để giải thích:
- H1 (bỏ một symbol khỏi snapshot) không tái lập được phút nào.
- Ở các phút này IBKR xếp hạng 63–72 và CEG 199–378 trong tập; BAC không có giá trị r15.

**Giả thuyết H2 — live thiếu một nến khả dụng trong buffer 15 nến.** Tái lập bit-exact giá trị live (`py/inv_rdown15_drop.py`) khi giả định đúng một nến khả dụng bị thiếu:
- **RDWUSDT**, với nến bị thiếu là một trong {17:03, 17:04, 17:13, 17:14, 17:16, 17:18}: sửa đủ cả 17:37/17:38/17:40 và **không làm hỏng phút nào khác** trong 16:55–18:00.
  - 17:17, 17:31, 17:34, 17:35, 17:36 bị loại vì làm hỏng chính phút của chúng; 17:37–17:40 chỉ sửa được một phần.
  - Nến 17:03 trên Vision: o=h=l=c=8,49, quote 18,17 USDT (giá phẳng, khối lượng nhỏ).
  - RDW có nhiều phút 0 giao dịch, nên 15 nến khả dụng trải ~40′. Vì vậy một nến thiếu lúc 17:0x vẫn ảnh hưởng tới 17:40.
- **RAMUSDT**, nến 17:03 hoặc 17:04: sửa 17:16/17:18 và không phá phút nào. Hai phút này vốn đã có nhãn K1.
- Nến 17:03–17:04 nằm trong cửa sổ `[LIVE-KLINE]` kết thúc 17:11 (`reread_overwritten=253`, `decided_on_unsettled=252`). Đây là cơ chế K1: nến chưa settle lúc quyết định đi vào buffer trong RAM và không được sửa lại khi reread.

**Vì sao vẫn ghi CHƯA GIẢI THÍCH:**
- (a) Ứng viên RDW **không duy nhất**: 6 nến. 4 trong số đó nằm trong cửa sổ 17:21, mà cửa sổ này không có cờ.
- (b) Không có nến live ngày 10-21 trên Oracle để xác minh, và luật cấm đọc 242.
- (c) Phút 17:32 có lệch nhỏ hơn dung sai (không tính là lệch) và không giải thích được bằng ứng viên nào.

**Đề xuất cho MASTER (không tự đổi):** khung K1 [M−20′, M+10′] **không phủ** được hiệu ứng trễ của cửa sổ 15 nến đếm theo nến khả dụng.

### 7.2 Bảy phút psym "thiếu" 10-22 00:00–00:06 (+07)

**Không thiếu trên live.** 7 file `predictionSymbol` có trên Oracle (kéo về 10-23) với mtime 00:01:06…00:07:06 (+07), đúng nhịp ghi mỗi phút. Chúng chỉ không được giải mã vào `feat45_live_b.csv.gz` (bắt đầu từ 00:07), và lượt gốc kết luận sai rằng "live thiếu".
- Sau khi giải mã: 4 874 dòng, 683–709 symbol/phút. Phút 17:00 UTC có 705 dòng, khớp `[MAP] n_coins=705`.
- Cả 7 phút đều khớp FUND/NET/GV-I/GV-O.
- Vì sao builder gốc bỏ sót 7 file: **CHƯA GIẢI THÍCH** (script dựng `feat45_live_b` không có trong repo).

### 7.3 S1-V — 601 phút lệch ở cột rank (mô tả)

- Chỉ có `f2 rk_dd_7d` (402 dòng) và `f5 rk_ret_3d` (786 dòng) lệch, khoảng 2 dòng/phút, theo cặp symbol cố định trong từng giờ. Ví dụ: APT/FOGO 14:xx, ALGO 15:xx, ARKM/KGEN 17:xx.
- Ví dụ f5 có bằng chứng: `ret_3d` live (float32) cho APT 0,049499925 > FOGO 0,04949991, còn tính lại bằng double (`d1_s1v.py`) cho APT 0,04949994 < FOGO 0,04950000 ⇒ **hạng của cặp gần hoà bị hoán đổi do khác độ chính xác** float32 (live) và float64 (S1-V offline).
- f2 chưa kiểm cặp. Lời giải thích của lượt gốc ("thiếu lịch sử Vision/universe") **không khớp** với mẫu f5.
- Top-24 vẫn khớp 1387/1387. S1-V là chỉ số báo cáo, không có ngưỡng.

### 7.4 Sự cố 10-21 07:54 (`check_242_failopen_1024_0819.txt`, owner chạy 10-24 08:19)

Diễn biến:
- 07:54:12 `ERROR [FEAT-PIPE] khong co feature snapshot phut nay`.
- 07:54:38 xuất hiện **24 dòng** `No AI prediction data for <SYM> at time 20261021 07:53` (đủ 24 ứng viên), rồi `[GATE] thr=[-..-] n_cand=24 n_rej=0 n_pass=24`.

Lý giải theo mã nguồn `627e9b34`:
- `thr` chỉ được tính khi `predictData != null`, nên in ra `-`.
- `n_pass = n_cand − n_rej`, trong đó n_rej chỉ đếm REJECT của gate.
- Trong khung 07:53–07:59 không có dòng `[SHADOW]` mở vị thế nào ngoài dòng khởi tạo sổ giấy.

⇒ Gate không chặn, nhưng tầng sau (thiếu prediction) chặn 24/24, **không có lệnh**: **fail-closed về hiệu quả**. `n_pass=24` là ngữ nghĩa log, không phải pass thật. Mục 3 của file cho thấy từ 10-21 đến 10-24 08:19 chỉ có 1 lỗi `[FEAT-PIPE]`, tức sự cố không lặp lại. Giới hạn: tôi chỉ thấy output của script kiểm, không thấy chính script.

## 8. Verdict D1 theo prereg (`481701b2` §4–§5)

| tiêu chí | gốc | sửa |
|---|---|---|
| P1 | ĐẠT | **ĐẠT** (sơ bộ phần funding: 3 cột funding tiêm live, chính thức ở lượt M) |
| P2 | ĐẠT (yếu, 966 phút) | **ĐẠT (yếu)**: 1386 phút, 0 lật nặng, 0 cặp r/q ≥ 0,9 |
| P3 | TRƯỢT (1/24) | **ĐẠT** 24/24 |
| TSX | ĐẠT | **ĐẠT** |
| S1-I / GV-I / CTL | ĐẠT | **ĐẠT** |
| K5 | 4 ⇒ XÁM | **0** (cơ học, xem §0 mục 2) |
| **Tổng lượt D1** | TRƯỢT + XÁM | **ĐẠT** (sơ bộ cho phần funding) |
| KHÔNG ĐO ĐƯỢC | (ngầm: 8 giờ P3, 420 phút P2, 7 phút psym) | **không còn** trong D1; funding tháng 10 chờ lượt M (Vision monthly đầu 11) |

## 9. Còn thiếu và đề xuất cho lượt D2 (10-22, 10-23)

1. **Điều kiện chạy:**
   - Vision daily 10-22/10-23 có cho ≥ 99 % U_D.
   - `pull242` đã chạy: dữ liệu ở `~/claude_master/pull242/<YYYY-MM-DD>/`.
   - Kiểm độ phủ **trước** khi chấm, cho từng ngày UTC D:
     - log **không lọc theo ngày local**, phủ [D 06:00, D+1 07:10] (+07), gồm cả `[MAP]`;
     - 1440 dòng `[GATE]`;
     - 24 dòng `[GATE-RATIO]` (dòng của giờ 23 UTC in lúc D+1 07:01 +07);
     - 1440 file psym, tất cả đều được giải mã;
     - feat/sel/s1 dump;
     - `gate_ratio_live.bin` chụp sau D+1 00:01 UTC;
     - `ts_ext_daily.csv`;
     - các dòng `MainClass`.
   - Thiếu ⇒ ghi KHÔNG ĐO ĐƯỢC cho đúng phần đó.
2. **Tham số hoá code** (`d1_eval.py`, `d1_labels.py`, `d1_s1v.py`, `psym_c_build.sh`): ngày D, T0/T1, glob, danh sách log, `DAY_D/DAY_PREV`. Chạy lại D1 sau khi tham số hoá phải ra **bit-identical** JSON của ADDENDUM này (regression test).
3. **Nhãn K cần MASTER quyết định trước D2** (ADDENDUM prereg, không tự đổi):
   - (a) K3 phủ trọn ngày có niêm yết ⇒ K5 mất tác dụng. Có thể thu hẹp K3, ví dụ chỉ khi symbol đổi tham gia vào feature lệch.
   - (b) K1 thiếu hiệu ứng trễ của cửa sổ 15 nến khả dụng (§7.1).
4. **P2:** ghi tích luỹ số cặp r/q ≥ 0,9 qua các ngày. P2 chỉ có ý nghĩa khi có cặp gần ngưỡng.
5. **Gợi ý cho live (không thuộc parity):**
   - In `thr` theo ngưỡng ratio thật (q_t) thay vì base tĩnh.
   - Tách `n_skip_nopred` ra khỏi `n_pass`.
6. **Funding:** lượt M khi Vision monthly `fundingRate` tháng 10 phát hành (đầu tháng 11).

## 10. Artefact

- JSON máy đọc: `docs/result/parity_v11_d1/parity_v11_d1_add1.json` (gốc vs sửa + status).
- Chi tiết: `docs/result/parity_v11_d1/add1/` gồm `gate|fund|net|s1|gv_p2|p3|labels _d1.json`, `p3_q.csv`, `p3_audit_2log.out`, `p1_audit.out`, `inv15_a.out`, `inv15_b2.out`.
- Code: `research/parity_v11/py/{d1_eval,d1_labels,d1_add1_report,inv_rdown15,inv_rdown15_drop}.py`, `research/parity_v11/sh/psym_c_build.sh`.
- Dữ liệu mới trên Oracle: `~/claude_master/parity_v11w/live/feat45_live_c.csv.gz` (md5 `1a062d08…`). JSON gốc được lưu ở `~/claude_master/pard1fix_wk/work_orig_ab5bbe44/`.
- An toàn: không chạm 242 / Aerospike / Binance REST; không sudo; chỉ ghi trong `~/claude_master/{parity_v11w,pard1fix_wk,vz_e1_wt}`.
