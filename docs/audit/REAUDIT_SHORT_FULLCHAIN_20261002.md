# REAUDIT SHORT_FULLCHAIN (S1 decile-0 → SHORT, trailing/SL/time-stop, gate predRisk4H) — 2026-10-02

Đối tượng: `b61ae757 result(SHORT_FULLCHAIN) AMENDMENT A1 … NO-GO` (`docs/result/RESULT_SHORT_FULLCHAIN.{json,md}`,
`research/analysis/short_fullchain_sim.py`, prereg `docs/prereg/PREREG_SHORT_FULLCHAIN.md`). Hai agent audit trước
bị chặn SSH → chỉ có báo cáo text + script `research/analysis/audit_short_fullchain_repro.py` (viết nhưng chưa
chạy). Doc này = (1) báo cáo text vòng trước + (2) bổ sung tái lập thô do auditor vòng 3 chạy trên Oracle
(chỉ đọc, DEV ≤ 2025, không Java/Kaggle/242).

## 0. Trạng thái nguồn — ĐỌC TRƯỚC

- **Báo cáo text FULLCHAIN của vòng trước KHÔNG có trong brief giao việc cho auditor vòng 3** (brief bị cắt ngay
  sau dòng `=== BÁO CÁO TEXT CẦN GHI THÀNH DOC ===`). Auditor vòng 3 không tự dựng lại văn bản. Mục 1 để trống.
- Claim vòng trước biết được (chỉ qua brief): **F1** pool `cand_dev_x1` 100% `p15 ≥ 0,008`, tick/năm
  2926/510/2258/11653; **F4** "SL không bao giờ kích trước trailing"; net hằng số lát 2024 A `T3_SL100_TS24h`
  −0,294%, D −0,013%; cần kiểm funding EXACT và causality entry `close m0+14`.

## 1. Báo cáo audit vòng trước (nguyên văn)

> **(Báo cáo nguyên văn của auditor vòng 1 — bị chặn SSH, MASTER dán lại)

Verdict NO-GO đứng (vẫn NO-GO khi funding=0/đảo dấu, bỏ D, sửa artifact SL) NHƯNG giải thích/phạm vi sai 4 chỗ lớn:

F1 (CAO): "nhánh A không gate" thực chất = tick GATE LONG MỞ: pred_s1a2x1 chấm trên pool cand_dev_x1 = 17 349 tick, 100% dòng đã lọc p15 ≥ 0,008 (G5_VALUE_LABELS.md:123, BRIEF_GATE_SELECTOR_20260911.md:96, X1_EXTEND.md:287). Tick gate mở theo năm 2022=2926, 2023=510, 2024=2258, 2025=11653 ⇒ 83% pick ở 2025. Kết luận đúng phạm vi: "short S1-d0 TRONG tick gate long mở là âm"; short khi gate đóng CHƯA test.

F2 (CAO): đọc ngược dấu IC bước 1: IC(s1,ret)<0 với s1=−score ⇒ decile 0 (ứng viên short) có hạng lợi nhuận CAO hơn ⇒ selector đi NGƯỢC short, không phải "đúng chiều & bền". Bảng decile khớp (d0 ≈ trung bình, thấp nhất d7/d8). trend_rank_ic.add_s1 ghép asof không giới hạn độ cũ ⇒ 35 047 snapshot 1h dùng điểm S1 cũ hàng tuần (panel chỉ 17 349 tick thật).

F3 (TRUNG–CAO): FUND72 hằng số 0,585%·held/72 dao động 0,055% (D T3) → 0,46% (C T8_TS72h), lớn hơn |net| nhiều ô. Tính lại 144 ô từ mean_held_h: funding=0 → 30/144 ô net>0 (tốt nhất D T8_TS72h +0,085%); đảo dấu → 72/144 (A T8_SL100_TS72h +0,448%, CI≈[−0,16;…]); vẫn 0 ô GO (CI chứa 0, ≤2/4 năm, 2023 âm). "A âm có ý nghĩa" cũng phụ thuộc funding (f=0: A T3_TS72h −0,115 CI [−0,284;+0,070]). --raw-out không lưu sym ⇒ không tính funding exact từ npz.

F4 (TRUNG): thoát lệnh: trailing kích hoạt NGAY từ lúc vào, không arm (runmin=fmin.accumulate(low), level=runmin·(1+T)) ⇒ trailing = stop ≈ P·(1+T), T≤8% ⇒ SL ∈{10…100%} gần như không kích trước (agent 2 tái lập: SL10 có kích ≤0,36% lệnh, ảnh hưởng net ≤0,03pp); "ưu tiên SL cùng nến" sai vật lý (2 stop cùng phía, giá chạm level thấp hơn trước) ⇒ lệnh thoát SL là artifact (tail −50,2% ở SL50; "+0,003…0,014% khi bỏ SL" của A1). "SL=100 no-stop" KHÔNG phải no-stop ⇒ giả thuyết owner "cắt cứng mất lãi" CHƯA HỀ được test. Lưới thực chất 6 cấu hình thoát (3 trailing × 2 TS) × 4 nhánh lồng nhau (A=B∪D, C⊂B). Thiên lệch lạc quan nhỏ: trailing dùng low nến kích hoạt, fill đúng level bỏ gap, slippage 0,67bp/chân.

F5 (TRUNG): vũ trụ pick bước 2 (944k, lưới 1h, điểm cũ) ≠ bước 3 (654k, tick 15m pool); C 9,8%→0,55% (3 607 lệnh), D 9,2%→28,8% (q10/q90 tính trên toàn chuỗi phút 2021–2025 trong khi pick dồn 2025). "Kiểm chứng kênh gross −0,042 ≈ ret24 −0,041" là trùng hợp (giữ 10,9h vs 24h, khác tập, khác trọng số).

F6 (THẤP): phí bước 3 trừ 1 lần 0,112% khớp Java; bước 1 dùng 0,2098% (đếm 2 lần) — không đổi kết luận.

F7 (THẤP): amendment 444377a (23:29:22) tạo 29s SAU commit kết quả gốc 5784f0e (23:28:53) ⇒ post-hoc theo yêu cầu owner; sửa code (SLS, lọc NaN agg) commit cùng lúc kết quả; A1 tái lập 18 ô gốc ≤3e-6, n 654 326→654 256 (70 pick NaN); không đổi verdict.

F8 (THẤP): RESULT ghi "18 cấu hình" (thực 36); §4 dùng số cũ; §5 "0/72"; net headline trung bình theo tick, by_year theo pick (luật A và B đo 2 đại lượng khác); by_year theo TZ+7, bước 1 UTC.

Trả lời 9 điểm: (1) tái lập — agent 2 đã làm lát 2024, khớp 4 chữ số; (3) m0+14 đọc code đúng (ts = open nến 15m, entry close 1m m0+14 = m0+15; lọc p15 tại ctime=ts có thể nhìn trước 15' — chưa xác minh); (4) MDE80 ≈ 0,25–0,5%/lệnh; 2023 chỉ vài chục cụm; (8) bỏ D: A/B/C ≤ −0,23…−1,17, 0/4 năm ⇒ NO-GO đứng (với funding gốc); (9) "0 ô ⇒ không overfit/thiếu edge hệ thống" sai một phần: power thấp, lưới dư, D CI chứa 0 = chưa kết luận được.

> được viết vào mục này.

## 2. Bổ sung tái lập trên dữ liệu thô (auditor vòng 3)

Chạy trên Oracle, lock `oracle_heavy.lock`, watchdog RSS ≤ 6 GiB:
- `research/analysis/audit_short_fullchain_repro.py --slice 2024 --fund-cache /tmp/fund_cache.npz` (script vòng
  trước, **không sửa**; dùng nguyên `build_picks/sim/exits/agg` của `short_fullchain_sim.py`). 590 s, peak RSS
  3,16 GB, 62 924 tick-pick lát 2024, gate q10 −0,02386 / q90 −0,01056 (khớp RESULT), funding phủ 100%.
  → `docs/audit/REAUDIT_SHORT_FULLCHAIN_2024_20261002.json`.
- `research/analysis/reaudit_short_fullchain_f1.py` (mới, chỉ đọc) → `docs/audit/REAUDIT_SHORT_FULLCHAIN_F1_20261002.json`.
- `/tmp/fund_cache.npz` còn nguyên (1 814 663 settle, 831 sym, ts_max 2025-12-31 23:00, 0 ts không đơn điệu/0 trùng
  trong từng sym → `searchsorted` của repro hợp lệ). Không cần tái tạo; không có đầu vào nào bị CHẶN.

### (i) Net hằng số lát 2024 vs `by_year['2024']` của `RESULT_SHORT_FULLCHAIN.json`

| nhánh | combo | n | net const (repro, pick-weighted) | RESULT by_year['2024'] | khớp |
|---|---|---|---|---|---|
| A_all | T3_SL100_TS24h | 62 924 | −0,2944% | −0,2944% | ✓ |
| A_all | T3_SL10_TS24h | 62 924 | −0,2969% | −0,2969% | ✓ |
| D_NGHICH_q10 | T3_SL100_TS24h | 28 710 | −0,0126% | −0,0126% | ✓ |
| D_NGHICH_q10 | T3_SL10_TS24h | 28 710 | −0,0140% | −0,0140% | ✓ |

→ **Tái lập khớp tới 4 chữ số** (claim A −0,294%, D −0,013%). Pipeline sim của b61ae757 cho lát 2024 là xác định
và tái lập được từ Aerospike thô.

### (ii) Funding EXACT (Σ rate settle trong (entry, entry+held], rate>0 ⇒ SHORT NHẬN) thay hằng số

Hằng số `FUND72 = 0,585%/72h` giả định SHORT **trả** ≈0,065%/settle; thực tế lát 2024 SHORT **nhận** ròng.

| nhánh · combo | fund const TB | fund exact TB | net const | net exact | Δ | exact tick-weighted (CI raw block-72h) |
|---|---|---|---|---|---|---|
| A · T3_SL100_TS24h | −0,0374% | +0,0119% | −0,2944% | **−0,2451%** | +0,049 pp | −0,251% [−0,419; −0,093] |
| D · T3_SL100_TS24h | −0,0264% | +0,0084% | −0,0126% | **+0,0222%** | +0,035 pp | +0,009% [−0,244; +0,258] |
| A · T8_SL10_TS72h (Δ lớn nhất A) | −0,2294% | +0,0666% | −1,4255% | −1,1295% | +0,296 pp | −1,092% [−1,931; −0,128] |
| B · T3_SL100_TS24h | −0,0467% | +0,0148% | −0,5309% | −0,4694% | +0,062 pp | −0,474% [−0,650; −0,312] |
| C · T8_SL100_TS72h (n 163) | −0,3215% | +0,0994% | −0,1235% | +0,2974% | +0,421 pp | +0,325% [−3,33; +3,92] |

→ Hằng số funding **bi quan có hệ thống** (+0,035…+0,42 pp/lệnh, tăng theo thời gian giữ). Ở T3 (giữ TB ≈4,6 h)
Δ chỉ ~0,04–0,05 pp: A vẫn âm, CI không chứa 0; D lát 2024 lật dấu sang +0,02% nhưng CI [−0,24; +0,26] chứa 0
(chỉ 1 năm; 2023 của D theo RESULT là −0,30%, Δ cỡ này không cứu). C n=163 quá nhỏ, CI ±3,6 pp — không đọc.

### (iii) Số lệnh thoát bằng SL thực tế (kiểm claim F4 "SL không bao giờ kích trước trailing")

Đếm `pnl == −SL` trên toàn 62 924 tick-pick lát 2024 (gồm cả ca SL và trailing cùng nến → `exits()` ưu tiên SL):

| combo | TS24h | TS72h |
|---|---|---|
| T3_SL10 | 20 (0,032%) | 20 |
| T5_SL10 | 56 (0,089%) | 60 |
| T8_SL10 | 183 (0,29%) | 228 (0,36%) |
| T*_SL100 | 0 | 0 |

→ **F4 SAI về chữ, ĐÚNG về độ lớn**: SL 10% có kích (20–228 lệnh), không phải "không bao giờ"; nhưng tỉ lệ
≤0,36% và ảnh hưởng net ≤0,03 pp (vd A T3_TS24h SL10 −0,2969% vs SL100 −0,2944%). Cơ chế: mức trailing
`runmin·(1+T)` ≤ `low₀·(1+T)` nên SL `P·(1+SL)` chỉ đến trước khi giá **nhảy** > ~(SL−T) trên entry mà không
quay đầu — hiếm với T=3%, thường hơn với T=8%. Ghi chú phụ (không định lượng): `exits()` tính `runmin` gồm
cả `low` của chính nến kích trailing → giả định low xảy ra trước high trong cùng nến 1m (thứ tự thuận lợi cho SHORT).

### (iv) 20 lệnh mẫu — causality entry (rng seed 20261002, T3_SL10_TS24h)

Key Aerospike theo UTC+7. Ví dụ dòng 1: `ts`=1710855900000 = 2024-03-19 13:45 UTC (open nến 15m) → key m0+14 =
`20240319-2059` (+7) = nến 1m mở 13:59 UTC, **đóng 14:00 UTC = đúng giờ đóng nến 15m**; entry = close nến này
(33,13); đường giá cho exit bắt đầu từ nến m0+15 (`i0 = m0+1`). 20/20 mẫu có đủ 3 nến m0+13/14/15 (0 lỗi đọc).

| ts (UTC) | sym | m0+13 close | **m0+14 close = entry** | m0+15 H/L/C | pnl | giữ (phút) |
|---|---|---|---|---|---|---|
| 2024-03-19 13:45 | DASH | 33,09 | 33,13 | 33,14/32,98/32,99 | −0,89% | 84 |
| 2024-09-06 21:00 | HIGH | 1,1778 | 1,1793 | 1,1793/1,1765/1,1781 | −2,81% | 473 |
| 2024-12-21 16:45 | BNT | 0,67025 | 0,67027 | 0,67058/0,66816/0,66978 | −0,87% | 451 |
| 2024-04-03 00:45 | RLC | 3,2389 | 3,2440 | 3,2457/3,2355/3,2378 | −1,56% | 41 |
| 2024-03-05 15:30 | STG | 0,6984 | 0,6963 | 0,6993/0,6954/0,6993 | +1,76% | 39 |
| 2024-11-24 09:30 | 1MBABYDOGE | 0,0024272 | 0,0024266 | 0,0024298/0,0024248/0,0024293 | +7,39% | 188 |
| 2024-04-18 13:45 | DOGE | 0,14746 | 0,14786 | 0,14800/0,14749/0,14754 | −2,29% | 15 |
| 2024-12-21 16:45 | KAS | 0,12037 | 0,12029 | 0,12041/0,12000/0,12028 | +1,39% | 909 |
| 2024-03-12 16:45 | C98 | 0,4130 | 0,4124 | 0,4137/0,4123/0,4134 | +2,62% | 25 |
| 2024-03-17 07:15 | MATIC | 1,0221 | 1,0215 | 1,0247/1,0209/1,0246 | −2,26% | 62 |
| 2024-03-14 15:00 | OP | 4,1715 | 4,1627 | 4,1636/4,1534/4,1545 | +0,78% | 292 |
| 2024-01-05 17:00 | DASH | 28,51 | 28,52 | 28,60/28,52/28,59 | −2,82% | 141 |
| 2024-12-10 05:30 | DOGE | 0,40338 | 0,40309 | 0,40315/0,40209/0,40263 | −2,74% | 208 |
| 2024-11-13 15:00 | BOND | 1,4750 | 1,4760 | 1,4770/1,4720/1,4720 | −2,72% | 99 |
| 2024-08-05 20:15 | NEO | 8,523 | 8,531 | 8,534/8,509/8,513 | −2,30% | 228 |
| 2024-03-03 08:30 | MKR | 2067,5 | 2069,2 | 2071,2/2068,7/2071,2 | −2,04% | 824 |
| 2024-11-13 04:30 | USTC | 0,021539 | 0,021532 | 0,021573/0,021484/0,021552 | −0,79% | 12 |
| 2024-12-11 13:30 | SFP | 0,6878 | 0,6884 | 0,6882/0,6854/0,6871 | −2,04% | 137 |
| 2024-01-19 16:30 | ROSE | 0,09741 | 0,09709 | 0,09787/0,09700/0,09735 | −2,40% | 52 |
| 2024-03-01 01:00 | ARB | 1,9722 | 1,9712 | 1,9717/1,9691/1,9708 | −1,41% | 1398 |

→ Về phía **giá**, entry = close nến 1m đóng đúng lúc nến 15m `[ts, ts+15m)` đóng; không dùng giá sau entry để
vào lệnh; exit chỉ dùng nến từ m0+15. Causality phía **tín hiệu** (score S1 tại `ts` có dùng dữ liệu tới
`ts+15m` hay không; gate `predRisk4H` đọc ở phút m0+14) **không kiểm được ở đây** — prereg đã ghi `predRisk4H`
là set CŨ, không leak-free (in-sample lạc quan).

### (v) F1 — pool `ledger/cand_dev_x1.parquet`

| kiểm | kết quả |
|---|---|
| số dòng / tick | 7 020 129 / 21 396 (ts_max 2025-12-31 16:45 UTC) |
| tỉ lệ dòng `p15 ≥ 0,008` | **100,000%** (min 0,00800002; 0 NaN); mọi tick có min p15 ≥ 0,008 |
| tick theo năm (UTC) | 2021 **4 049** · 2022 **2 926** · 2023 **510** · 2024 **2 258** · 2025 **11 653** |
| tick theo năm (UTC+7) | 4 047 · 2 928 · 507 · 2 260 · 11 654 |

→ **F1 khớp chính xác** (2926/510/2258/11653 theo năm UTC, trùng `docs/experiment/X1_EXTEND.md` §10.1). Lưu ý
pool còn 4 049 tick năm 2021 nằm ngoài 4 năm được đếm.

### Kết luận tái lập thô (auditor vòng 3)

- Verdict SHORT_FULLCHAIN **NO-GO giữ nguyên**. Sim tái lập khớp 4 chữ số (lát 2024); funding EXACT làm net tốt
  lên +0,03…+0,42 pp/lệnh (hằng số 0,585%/72h bi quan có hệ thống) nhưng không lật kết luận: A vẫn âm, CI ngoài 0;
  D lát 2024 ≈ 0 (+0,02%, CI chứa 0), 1 năm không đủ cho G năm-dương.
- **Nên sửa trong mọi sim SHORT sau**: thay `FUND72` hằng số bằng funding exact (đã có `/tmp/fund_cache.npz`).
- F1 ✓; F4 sai về chữ (SL10 kích 20–228/62 924), không đáng kể về net; giá entry causal (close m0+14 = đóng nến 15m).
- Chưa kiểm: các lát 2022/2023/2025 với funding exact; causality của score S1 và `predRisk4H`.
