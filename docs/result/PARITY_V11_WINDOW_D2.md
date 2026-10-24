# PARITY v1.1 — lượt D2 (ngày UTC 2026-10-22 và 2026-10-23)

- **Thước:** `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (`481701b2`) + **ADDENDUM1** `docs/prereg/PREREG_PARITY_V11_WINDOW_ADDENDUM1.md` (`fea9fb97`, sha256 `ec94009c…5177`).
  - ADDENDUM1 được commit **trước** mọi phép đo D2.
  - Trước commit đó chỉ đọc cấu trúc log/dump để biết định dạng; không tính chỉ số nào.
- **Đối tượng:** 242 shadow.
  - jar v11c `eea5adec` cho tới 10-23 09:37:29 (+07).
  - Sau đó là jar `dcae2e2b`. Theo ADDENDUM d, đây là thay đổi ops-only, không reset cửa sổ.
- **Dữ liệu live:** `~/claude_master/pull242/<D>/`, cả ba ngày 10-21/22/23 đều `COMPLETE`. Đây là bản kéo chỉ-đọc.
  - **Không** chạm 242, Aerospike 242 hay Binance REST.
  - Vision lấy từ `data.binance.vision` (file tĩnh).
- **Code:** `research/parity_v11/` (commit của lượt này, xem §10).
  - Harness OFFLINE `0bd019f7` giữ nguyên.
  - Cấu hình `HARNESS_OFFLINE=1`; stub Aerospike halt 97; SecurityManager halt 98; chạy dưới strace.
- **Ký hiệu thời gian:** phút ghi dạng `MM-DD HH:MM` là giờ **+07**; giờ UTC ghi rõ "UTC". Ngày UTC D tương ứng D 07:00 → D+1 06:59 (+07).

## 0. Kết luận (risk-first)

| ngày UTC | verdict theo prereg §5 + ADDENDUM1 | lý do |
|---|---|---|
| **2026-10-22** | **XÁM** | P1/P2/P3/TSX/S1-I/GV-I/CTL **đều đạt ngưỡng**. Tuy vậy K5 (luật K′) = **416 phút**, nên phải điều tra trước lượt kế. Không có tiêu chí nào TRƯỢT. |
| **2026-10-23** | **KHÔNG ĐO ĐƯỢC (một phần)** | Vision daily 10-23 **chưa phát hành**: HTTP 404, kiểm lần cuối 10-24 ~10:05 (+07). Phần đo được đều ĐẠT: P3 24/24, S1-I, S1-m, GV-I, P1-m, `[GATE] n_pass` 1440/1440, cờ TSX. Phần cần Vision (P1, P2, CTL, FUND/NET/MD, S1-V, nhãn K′) chưa chấm. |
| tích luỹ cửa sổ (10-21 → 10-23) | 10-21 **ĐẠT** (D1 ADDENDUM1, giữ nguyên); 10-22 **XÁM**; 10-23 **chưa đủ** | Chưa ngày nào TRƯỢT. Chưa ngày nào P2 được thử ở cả hai phía. |

Rủi ro, xếp theo mức độ:

1. **P2 vẫn chưa được thử. Ngày duy nhất thử được (10-23) lại là ngày KHÔNG ĐO ĐƯỢC phía offline.**
   - 10-22: 34 560 cặp, max r/q 0,695, **0 cặp ≥ 0,8**.
   - Tích luỹ hai ngày đo đủ hai phía (10-21 + 10-22): 67 824 cặp, **0 cặp ≥ 0,9** (6 cặp ≥ 0,8, đều ở 10-21).
   - 10-23 là ngày đầu có **PASS live: 25 cặp pass; 28 cặp r/q ≥ 0,9; max r/q 1,657**. Log `[GATE] n_pass` khớp tính lại 1440/1440 (tổng 25 = 25).
   - ⇒ **Việc cần làm ngay khi Vision 10-23 có:** chạy lại 10-23 (lệnh ở §9). Đây là lần đầu P2 bị thử thật.
2. **K5 = 416 ở 10-22 là kết quả cơ học của ADDENDUM1, không phải phát hiện lỗi code.** Lệch thuộc ba loại:
   - **(a) K1′ = 0 do cách đặt luật.** Log 242 chỉ in bộ đếm (`[LIVE-KLINE] … reread_overwritten=N`, `S1 doc lai close …: N coin, sua K`), **không có dòng nào nêu tên symbol bị ghi đè**. Quét toàn log trong cửa sổ cho 0 dòng bằng chứng. Vì vậy 9 phút lệch mức thị trường (P1-F/MD/FUND…) đều là K5. Theo luật cũ, 8/9 phút này là K1, vì có cửa sổ `[LIVE-KLINE]` kết thúc 08:21 và 05:21 với `reread_overwritten` 258 và 287.
   - **(b) S1-V (409 phút).** Đây là các cơ chế độ chính xác float32/float64 **nằm ngoài định nghĩa K6 đã chốt**:
     - *tie-split*: hạng lệch đúng 0,5/n, tức một phía hoà hạng còn phía kia tách;
     - *score-only*: mọi feature khớp dung sai nhưng score ONNX lệch.

     K6 (hoán đổi đúng 1/n) phủ 156 phút. Top-24 trùng tập và trùng thứ tự **1440/1440** phút. Agent **không** mở rộng K6 sau khi thấy số; việc này để MASTER quyết (§6.3).
   - **(c) K3′: 0 phút được chứng minh.** Phép drop BAC/CEG/IBKR đã chạy thật (3 nhóm, OFF-BT chạy lại) nhưng không làm lệch nào biến mất. Lệch **không** do khác universe.
3. **D1 áp lại nhãn K′ (chỉ nhãn): K5 = 375.** Gồm 9 phút mức thị trường và 366 phút chỉ S1-V. Nếu áp luật K′ thì D1 cũng là XÁM. Theo chỉ đạo, verdict D1 **giữ ĐẠT** (ADDENDUM1).
4. **Phát hiện ở D1 (không đổi số D1):** tập LEGACY dùng cho S1-I của D1 là **rỗng**.
   - Nguyên nhân: file `live/raw/ts_ext_legacy.txt` thực chất là `ts_ext_daily.csv`; mọi dòng có dấu phẩy nên bị lọc hết.
   - D2 đọc `[LEGACY] managed 44: …` từ log. S1-I vẫn 1440/1440 ở cả hai ngày.
   - Kiểm mẫu: 44 symbol legacy **có** trong `s1_dump`, nhưng 0 lần lọt top-24 thô ở giờ 12 UTC 10-22. Kết quả D1 vì vậy nhiều khả năng không đổi, nhưng **chưa kiểm lại** trên D1.
5. **Sự cố vận hành trong lượt (đã xử lý; không có số đã báo cáo nào dựa trên dữ liệu sai):**
   - **R0 lần 1 thiếu env mapper.** 9/11 ca exit 96: guard từ chối khởi động, tức fail-closed, không phải hở. Đã sửa `day_harness.py r0` và chạy lại: **11/11 ĐẠT**. Các lượt harness thật có env đầy đủ (log `[HARNESS-OFFLINE] BAT`, strace 0 connect ra ngoài).
   - **`PV_WORK` của regression D1 rò vào chuỗi chạy 10-22.**
     - Hậu quả: 4 file JSON phụ của 10-22 (`coverage`, `universe`, `segs`, `restarts`) bị ghi vào `regr_d1/work`.
     - Đã dừng chuỗi **trước** bước `gate`, tức trước khi bất kỳ file trung gian dùng chung tên nào bị ghi. Đã kiểm timestamp: mọi CSV/JSON D1 trong `regr_d1/work` có giờ ghi ≤ 09:33, trước chuỗi.
     - Đã chuyển 4 file về đúng chỗ; `restarts.json` trùng byte với bản do `prep` chạy riêng. Harness 10-22 đọc `segs.json` của chính 10-22.
     - `run_day.sh` nay luôn `unset PV_WORK`.
   - **Lỗi code K6.** Dung sai |Δhạng| = 1e-6/n quá chặt so với hạng live in float32. Phát hiện khi xem nhãn D1, **trước** khi chạy K′ cho 10-22. Đã sửa thành `1e-6·(1+|hạng|)`, cùng dung sai với mọi phép so khác. D1 chạy lại sau sửa. Đây là lỗi cài đặt, không phải đổi tiêu chí.

## 1. Dữ liệu và độ phủ (`coverage_<D>.json`, `universe_<D>.json`)

| mục | 2026-10-22 | 2026-10-23 |
|---|---|---|
| pull242 `<D>` / `<D+1>` | COMPLETE / COMPLETE | COMPLETE / (10-24 chưa kéo) |
| log dùng | 2 snapshot `full.log@…` (10-22, 10-23); gộp bằng "prefix-extend" (snapshot sau chứa trọn snapshot trước) | 1 snapshot (10-23) |
| log phủ D 06:00 → D+1 07:10 (+07) | có (06:00:00 → 07:10:00) | có |
| `[GATE]` (map tick) trong cửa sổ | **1440/1440** tick; `[MAP] tick=` khớp 1510/1510 dòng | **1440/1440**; 1510/1510 |
| `[GATE-RATIO]` (giờ UTC) | **24/24** | **24/24** |
| psym giải mã (`Pa1020Feat`) | **1440/1440** file, 989 857 dòng, ≥ 627 dòng/phút | **1440/1440**, 983 748 dòng, ≥ 621 dòng/phút |
| feat / sel / s1 dump | 1440 / 1440 / 1440 phút | 1440 / 1440 / 1440 phút |
| buffer `gate_ratio_live.bin` | snapshot 10-24 08:2x (+07), 769 232 record, 0 chunk lỗi, đầu 10-01 13:00 | như trái |
| replay q | chỉ record ts < đầu giờ | như trái |
| `ts_ext_daily.csv` | **không có trong pull242**. Thay bằng dòng log `[TS-EXT] day D sum_ew n_min`: n_min = 1440 cho 10-21, 10-22, 10-23. | như trái |
| restart (`MainClass`) | trước D: 10-21 19:54:32. Trong ngày: 10-22 07:54:43 và 19:55:32. | trước D: 10-22 19:55:32. Trong ngày: 10-23 07:55:42 và **09:37:31 (deploy `dcae2e2b`)**. |
| phút warm-up thiếu `feat_dump` | 0. Hai restart đều vào sau giây :06 nên process cũ đã quyết định tick trước đó. | 0 |
| Universe | U_D = 741: `u_cache1017` ∪ symbol live của ngày, có file Vision ngày D. Symbol live 739/739 có Vision (100 %). | Vision 10-23: **0/739** (404) ⇒ **KHÔNG ĐO ĐƯỢC** phần cần Vision |
| Vision các ngày phụ | 10-07..10-22 tải đủ (idempotent). 10-18..10-20 thiếu 3 file: BAC/CEG/IBKR chưa niêm yết. | — |

## 2. Regression test (bước 2): code tham số hoá chạy lại D1 ⇒ **bit-identical**

- **Code tham số hoá:**
  - `d1_eval.py` → `day_eval.py`; `d1_labels.py` → `day_labels.py`; `d1_s1v.py` → `day_s1v.py` (đều `git mv`).
  - `d1_tsx_build.py` → `day_tsx.py`.
  - Mới: `pv_cfg.py` (cấu hình theo `PV_DAY`), `day_prep.py`, `day_harness.py`, `day_kprime.py`, `day_report.py`, `regress_d1.py`, `indep_check.py`, `sh/run_day.sh`.
- **Cách chạy D1 trong regression:** bố cục dữ liệu cũ, ghi kết quả ra `regr_d1/work`.
- **`regress_d1.json`:**
  - 7 JSON `gate/fund/net/s1/gv_p2/p3/labels` = **identical** với `docs/result/parity_v11_d1/add1/*_d1.json` (a7e2764f), so sánh sau `json.load`, 0 khác biệt.
  - `s1v_d1.json` identical.
  - 7 file trung gian (giải nén) identical: `join_gate`, `join_fund`, `net_pw`, `net_live_all`, `p2_pairs`, `s1v_rows`, `p3_q`.
  - Engine TSX (bin 10-20..21, `u_d21`): `days64` và `days32` **identical** với D1.
- **Thay đổi hành vi có chủ đích (chỉ áp cho ngày ≠ D1):**
  - log gộp từ pull242;
  - LEGACY lấy từ log;
  - `S_j` của TSX tính từ bin (j−1, j). D1 dùng bin bắt đầu đúng 10-20 00:00, nên S_10-20 của D1 chỉ có 1439 phút (tạo tác biên); nay mỗi S_j đủ 1440 phút.
  - NEW2 chạy theo **từng đoạn restart thật**. D1 chỉ seed 1 restart; D2 có 3 đoạn mỗi ngày.

## 3. An toàn harness (R0, strace) và CTL

| mục | 10-22 | ghi chú |
|---|---|---|
| R0 self-test | **11/11 ĐẠT** (lần chạy lại; lần 1 thiếu env ⇒ exit 96, xem §0 mục 5) | 97 cho client242/clientOracle/readClient/mapperLoad/fundingScan/tickerRead; 98 cho socket242/dnsVision; 96 cho thiếu stub / config thật |
| strace 7 lượt JVM (BT, 3×NEW2, 3×drop) | mỗi lượt 4 `connect()`, đều AF_UNIX nscd. **0 tới 103.157.218.242, 0 AF_INET** | `harness_20261022.json`, `drop_runs.json` |
| **CTL** OFF-NEW2 vs OFF-BT | gate 33: **1440/1440 phút bit-identical**. Tool1 #1–40: **100 % trong dung sai**; bit 94,43 %, chỉ cột `f3` lệch bit cuối (2714 dòng), giống D1. | **ĐẠT** |
| 10-23 | không chạy (cần Vision) | KHÔNG ĐO ĐƯỢC |

## 4. Bảng chính

Dung sai một giá trị: `|a−b| ≤ 1e-6·(1+|b|)`. Funding tháng 10 tiêm từ live, theo lượt D của prereg.

| mã | ngưỡng | **2026-10-22** | **2026-10-23** |
|---|---|---|---|
| **P1** | median rel ≤ 1e-4 **và** ≥ 98 % phút ≤ 1e-3 | median **5,33e-10**; ≤ 1e-3 **99,861 %** (1438/1440); max 3,54e-2 (10-23 05:14) ⇒ **ĐẠT** | KHÔNG ĐO ĐƯỢC |
| P1-m | 100 % ≤ 1e-6 | 100 % (max 4,09e-7) ⇒ ĐẠT | 100 % (max 5,21e-7) ⇒ ĐẠT |
| P1-F (30 cột) | báo cáo | 1431/1440 = 99,375 % (9 phút, §5) | — |
| MD | báo cáo | rDown / rUp / rDown15 = 99,861 / 99,861 / 99,375 % | — |
| FUND (#1–40 bỏ funding) | báo cáo | 48 684 dòng, 99,486 %; phút 1431/1440 | — |
| NET | báo cáo | 99,920 % dòng; phút 1438/1440; max \|Δ\| 0,00988 | — |
| **S1-I** | 100 % | **1440/1440** (LEGACY từ log); \|selectorScore\| vs \|score\| max 7,5e-8 | **1440/1440** |
| S1-m | 100 % ≤ 1e-6 | 989 857 dòng, max \|Δ\| **0** | 983 748 dòng, max 0 |
| S1-V | báo cáo | f0/f1/f3/f4/f6 100 %; f2 99,931 %; f5 99,931 %; score 99,981 %; **top-24 Jaccard 1,0, trùng thứ tự 1440/1440** | — |
| **GV-I** | 100 % | **34 560/34 560** | **34 560/34 560** |
| GV-O | báo cáo | 99,951 % (17 dòng; 08:10, 05:14) | — |
| **P2** | lật nặng = 0 | 34 560 cặp / 1440 phút; q_live: log (1333 phút) + replay trước restart (107 phút); pass live 0 / off 0; **lật 0, lật nặng 0**; max r/q 0,6947 / 0,6947 ⇒ **ĐẠT (yếu)** | phía live: 25 pass, 28 cặp r/q ≥ 0,9, 41 cặp ≥ 0,8, max 1,657. **Phía offline KHÔNG ĐO ĐƯỢC** |
| `[GATE] n_pass` log == tính lại | báo cáo | **1440/1440** (Σ 0 = 0); khoảng `thr` (base 0,008) 1440/1440 | **1440/1440** (Σ 25 = 25); thr 1440/1440 |
| **P3** | rel ≤ 1e-6 **mọi giờ** | **24/24**; max 4,14e-10; `m == buffer−eval` 24/24; giờ restart 00, 12 UTC khớp ⇒ **ĐẠT** | **24/24**; max 6,35e-10; giờ restart 00, 02 UTC khớp ⇒ **ĐẠT** |
| **TSX** cờ | cờ trùng | flag day 10-22: live **OFF** (dd −0,130332, minN 1436) vs Vision **OFF** (dd −0,132860, minN 1439) ⇒ **ĐẠT** | flag day 10-23 (cần S tới 10-22): live **OFF** (−0,173328) vs Vision **OFF** (−0,175731) ⇒ **ĐẠT** |
| TSX ΔS_D | báo cáo | S_10-22: \|Δ\| **4,36e-10** (days64) / **6,2e-17** (days32); n_min 1440/1440 | S_10-23: KHÔNG ĐO ĐƯỢC |
| **CTL** | 100 % | ĐẠT (§3) | KHÔNG ĐO ĐƯỢC |

**Kiểm độc lập** (`py/indep_check.py`, không import pipeline): giải mã buffer GRR1 trực tiếp (struct + crc32 + snappy), đọc log raw của pull242, P1 viết theo audit OC1023 audA.

| ngày | P3 | P1 / P1-m | P1-F |
|---|---|---|---|
| 10-22 | 24/24 ≤ 1e-6 (max 4,14e-10) | median 5,327e-10; 99,861 %; max 3,54e-2; P1-m 4,09e-7 | 1431/1440, **đúng 9 phút như §5** |
| 10-23 | 24/24 (max 6,35e-10) | — | — |

Mọi số trùng pipeline.

## 5. Phút lệch mức thị trường 10-22 (P1-F/MD/FUND/NET/GV-O/P1)

| phút (+07) | feature lệch | rel p15 | `[LIVE-KLINE]` gần (bộ đếm, không theo symbol) | K3′ (drop) | nhãn K′ |
|---|---|---|---|---|---|
| 10-22 08:10 | 12 feature mức thị trường (momentum1M −0,001562/−0,001548 …) | 8,1e-3 | cửa sổ kết thúc 08:21: `reread_overwritten=258`, `decided_on_unsettled=257` | drop {BAC,CEG,IBKR}: không hết lệch | **K5** |
| 10-22 08:16, 08:28 | chỉ `momentum15M` + `momentumAcceleration` (~0,1 %) | 0 | như trên | không hết lệch | **K5** |
| 10-23 05:14 | 12 feature mức thị trường | **3,54e-2** | cửa sổ 05:21: `reread_overwritten=287`, `decided_on_unsettled=286` | (S_M rỗng) | **K5** |
| 10-23 05:26, 05:28, 05:29, 05:30, 05:32 | chỉ `momentum15M` + `momentumAcceleration` | 0 | như trên | (S_M rỗng) | **K5** |

**Mẫu hình giống hệt D1** (11:59 / 17:04 / 17:16–17:40 / 23:59): một phút lệch 12 feature ngay trong cửa sổ có ghi đè lớn, rồi một chuỗi phút chỉ lệch tham chiếu 15′ trong vài chục phút sau.

Mẫu này **khớp giả thuyết H2** của D1 ADDENDUM1 §7.1: nến chưa settle lúc quyết định nằm lại trong bộ đệm 15 nến khả dụng của symbol ít giao dịch.

Không có bằng chứng theo symbol nên theo ADDENDUM1, mẫu này **CHƯA GIẢI THÍCH** (K5). **Đề xuất cho MASTER (không tự làm):** cho live log danh sách symbol bị `reread_overwritten` theo cửa sổ. Khi đó K1′ mới kiểm được.

## 6. Nhãn K′ (ADDENDUM1)

Đơn vị gán nhãn là (phút, nguồn). Phút là K5 nếu có ≥ 1 nguồn không mang nhãn (`kprime_<D>.json`).

### 6.1 Tổng hợp

| | D1 10-21 (áp lại, chỉ nhãn) | **10-22** |
|---|---|---|
| phút lệch (hợp mọi nguồn) | 604 | **572** |
| cặp (phút, nguồn) | 632 | 598 |
| K1′ (bằng chứng theo symbol) | 0 (0 dòng log bằng chứng) | **0** (0 dòng) |
| K2a / K2b / K2c | 0 / 0 / 0 | 0 / 0 / 0 |
| K3′ | 0. Drop {BAC,CEG,IBKR} trên 482 phút: không phút nào hết lệch | **0**. Ba nhóm drop {BAC,CEG,IBKR} (155 phút), {BAC,IBKR} (5), {IBKR} (5): không phút nào hết lệch |
| K6 (mô tả) | 229 phút | **156 phút** (ví dụ NET/SHOP f2: dd_7d −0,03857116 vs −0,03857119) |
| **K5** | **375** = 9 phút mức thị trường + 366 phút chỉ S1-V | **416** = 9 phút mức thị trường (§5) + 407 phút chỉ S1-V |
| K5 theo nguồn | P1F 8, P1 1, MD 8, FUND 9, NET 3, GV-O 2, S1-V 372 | P1F 9, P1 2, MD 9, FUND 9, NET 2, GV-O 2, S1-V 409 |
| để so: nhãn cũ (prereg gốc) | K1 69, K3 604, K5 0 | K1 34, K3 165, **K5 401** |

### 6.2 S1-V K5: phân loại mô tả, không phải nhãn

| lớp | D1 | 10-22 | cơ chế |
|---|---|---|---|
| tie-split | 259 phút | 177 phút | Cột rank lệch đúng 0,5/n: một phía hai ứng viên kề bằng nhau và chia hạng trung bình, phía kia tách. \|Δv\| ≤ 1e-6·max. Ví dụ D1 17:00: ARKM/KGEN `ret_3d` = 0,081356 cả hai phía; live hạng 0,865782/0,867257, offline 0,866519 × 2. |
| score-only | 60 phút | 64 phút | Mọi feature khớp dung sai, nhưng score ONNX lệch > 1e-6. Ví dụ ALGO 15:xx D1. Cơ chế khả dĩ: ngưỡng chia của cây. Không làm đổi top-24. |
| other | 53 phút | 0 phút | D1 21:xx: CGPT/COST hoán đổi kề đúng 1/n, nhưng \|Δv\|/max\|v\| = 2,3e-6 (offline) / 6,1e-6 (live), vì \|ret_3d\| ≈ 0,006. Sai số tuyệt đối do float32 khoảng 4e-8, nên tiêu chí tương đối 1e-6 không đạt. |
| nhiều lớp trong cùng phút | 0 | 168 | — |

Mọi phút ở trên đều có **top-24 trùng tập và trùng thứ tự với live**.

### 6.3 Đề xuất cho MASTER (agent không tự đổi)

Nếu MASTER coi tie-split, score-only và hoán đổi có |Δv| nhỏ tuyệt đối là cùng loại K6, cần một ADDENDUM2 chốt **trước** lượt kế. Ví dụ:
- K6 gồm cả tie-split;
- dung sai |Δv| ≤ max(1e-6·|v|, 1e-7);
- score-only được nhận khi top-24 không đổi.

Với 9 phút mức thị trường, chỉ có thể giải quyết bằng cách thêm log per-symbol ở live (§5).

## 7. KHÔNG ĐO ĐƯỢC (lượt này)

| phần | lý do | khi nào đo |
|---|---|---|
| **10-23**: P1, P1-F, MD, FUND, NET, GV-O, **P2 phía offline**, CTL, S1-V, ΔS_10-23, nhãn K′ | Vision daily 10-23 chưa phát hành (0/739 symbol, 404) | ngay khi Vision 10-23 có (§9) |
| cờ TSX ngày 10-24 | cần S_10-23 từ Vision | cùng lúc trên |
| phần phụ thuộc funding tháng 10 (gate 3 cột; Tool1 f17–f25, f32) | Vision monthly `fundingRate` tháng 10 phát hành đầu tháng 11 | lượt M |
| K1′ | log 242 không có bằng chứng theo symbol | khi live có log per-symbol |

## 8. Tích luỹ cửa sổ (từ 10-21 07:53 +07)

| | 10-21 | 10-22 | 10-23 | tổng |
|---|---|---|---|---|
| verdict | ĐẠT (D1 ADD1) | **XÁM** | **KHÔNG ĐO ĐƯỢC (một phần)** | 0 ngày TRƯỢT |
| P2 cặp (đủ hai phía) | 33 264 | 34 560 | — | **67 824** |
| P2 cặp r/q ≥ 0,9 (live / off) | 0 / 0 | 0 / 0 | live 28 / off — | đủ hai phía: **0 / 0** |
| P2 cặp r/q ≥ 0,8 (live / off) | 6 / 6 | 0 / 0 | live 41 / off — | đủ hai phía: **6 / 6** |
| max r/q (live / off) | 0,8913 / 0,8913 | 0,6947 / 0,6947 | 1,657 / — | |
| P3 giờ ĐẠT | 24/24 | 24/24 | 24/24 | **72/72** |
| TSX cờ | OFF = OFF | OFF = OFF | OFF = OFF | 3/3 |
| K5 (luật K′) | 375 (áp lại, chỉ nhãn) | 416 | — | |

## 9. Lặp cho các ngày sau

Một lệnh, chạy trên Oracle. Điều kiện: `pull242/<X>/COMPLETE` (nên có `<X+1>`) và Vision daily ngày X đã có.

```
bash ~/claude_master/vz_e1_wt/research/parity_v11/sh/run_day.sh X && python3 ~/claude_master/vz_e1_wt/research/parity_v11/py/day_report.py d<n> X
```

Từ Windows, chạy nền khoảng 25 phút, rồi đọc `~/claude_master/parity_v11w/d/X/run_day.log`:

```
ssh -o BatchMode=yes -i %USERPROFILE%\.ssh\id_rsa_chuyennd_openssh ubuntu@161.118.212.3 "nohup bash ~/claude_master/vz_e1_wt/research/parity_v11/sh/run_day.sh X > /dev/null 2>&1 &"
```

- **Mã thoát:**
  - 0 = chấm đủ;
  - 3 = Vision X < 99 % symbol live: tự chấm phần không cần Vision (P3, S1-I/m, `live_only`: P1-m, GV-I, P2 phía live, `[GATE]` n_pass; cờ TSX);
  - 1 = lỗi (xem log).
- **Chấm lại 10-23 khi Vision có:**

  ```
  bash …/run_day.sh 2026-10-23 && python3 …/day_report.py d2b 2026-10-23
  ```

- **Chạy tiếp từ một bước:** thêm tham số thứ 2 là tên bước (`prep vision universe r0 harness eval s1v tsx labels kprime`).
- **Regression** sau mỗi lần sửa code chấm:

  ```
  bash ~/claude_master/vz_e1_wt/research/parity_v11/sh/regress_d1.sh && python3 ~/claude_master/vz_e1_wt/research/parity_v11/py/regress_d1.py
  ```

  Kết quả phải là `ALL_JSON_IDENTICAL=true`.

## 10. Artefact, an toàn, dung lượng

- **Commit:** prereg ADDENDUM1 `fea9fb97`; code + result của lượt này: xem commit `result(PARITY_V11_WINDOW D2)`.
- **Artefact** trong `docs/result/parity_v11_d2/`:
  - `parity_v11_d2.json`: verdict tính từ số + tích luỹ.
  - `<ngày>/`: `coverage`, `universe`, `gate`, `fund`, `net`, `s1`, `gv_p2`, `p3`, `p3_q.csv`, `s1v`, `tsx`, `labels`, `kprime`, `kprime_groups`, `live_only`, `cmp_ctl_*`, `harness_*`, `drop_runs`, `r0`, `restarts`, `segs`, `indep_*`.
  - `2026-10-21_relabel/`: `kprime_d1.json`, `regress_d1.json`, `drop_runs.json`.
- **An toàn:**
  - Không chạm 242 dưới mọi hình thức. Chỉ đọc `~/claude_master/pull242` đã có.
  - Không đọc Aerospike; strace: 0 connect tới 242, 0 AF_INET.
  - Không gọi Binance REST; chỉ dùng file tĩnh `data.binance.vision`. Không sudo.
- **Dọn dẹp và dung lượng:** đã xoá cache Vision `.ser.gz`, psym giải mã (`feat45_live.csv.gz` 140 MB × 2), `s1v_rows` (~85 MB × 2) và `closes_cache`. Số đĩa còn trống: xem báo cáo cuối.
