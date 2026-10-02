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

> **CHƯA CÓ — chờ MASTER dán nguyên văn báo cáo text FULLCHAIN.** Không có kết luận nào của auditor vòng 3
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
