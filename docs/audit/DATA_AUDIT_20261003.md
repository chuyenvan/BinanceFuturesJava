# DATA_AUDIT_20261003 — `CLOSES_1H.bin`: đuôi ffill/stale, lineage symbol, bản sạch v2, ảnh hưởng benchmark ALL

Ngày: 2026-10-03. Kích hoạt bởi `docs/audit/REAUDIT_SHORT_V3_R2B_20261002.md` (701b45f6/eeb55cb9) — phát hiện đuôi giá đứng yên FTM/KLAY/ALPACA/MKR.
Script: `research/analysis/data_audit_v2.py` (stage `vision scan aero lineage build audit impact`, ~12 phút tổng, RSS ≤ 1,8 GB, lock `oracle_heavy.lock` ở stage impact).
0-sim, không sửa `.java`, không ghi đè/xoá dữ liệu cũ, DEV ≤ 2025-12-31 (ts close ≤ 2026-01-01 00:00 UTC).

## 0. Kết luận (đọc trước)

1. **Lỗi có hệ thống, không phải 4 symbol**: **80/627 symbol** có giờ "giả" (không giao dịch) trong v1 — **79 đuôi stale** (76 ≥ 24h, **58 kéo tới hết DEV** 2026-01-01 00:00) + **1 gap giữa chuỗi** (LIT, 7 719h, ticker bị tái dùng). Tổng **320 568 symbol-giờ giả = 3,1 % record v1**, dồn vào 2025 (253 189 giờ = 6,2 % record 2025).
2. **Cơ chế**: Binance Vision (và cả Aerospike `kline_1m_opt`) **tiếp tục phát kline volume = 0, O=H=L=C = giá settle** sau khi hợp đồng ngừng giao dịch (đo trực tiếp: FTMUSDT-1h-2025-06 = 720/720 dòng vol=0, close duy nhất 0.7702). Builder (`research/pipeline/closes1h_build.py`, tái lập generator gốc) **chỉ đọc cột open_time + close, bỏ volume/trades** → không phân biệt được giờ thật với giờ settle. Không có `ffill` nào trong code — "ffill" nằm sẵn trong nguồn.
3. **v2** `/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin` (md5 `58f56069e8e1a7c739011ddfa13e9636`, 10 009 513 rec) + mask `CLOSES_1H_v2_mask.bin` (md5 `ad4a2dc04ebfe2a30663f13b72a7ba73`). Đối chiếu Aerospike 1m: v1 có 0,41 / 1,56 / 1,49 / **5,98 %** symbol-giờ "không có giao dịch thật" (2022/23/24/25) → **v2: 0 %** ở cả 4 năm; close v2 khớp close phút :59 Aerospike **tuyệt đối** (318 086 cặp, max |rel| = 0).
4. **Ảnh hưởng benchmark cũ: KHÔNG verdict nào đổi.** P0A FAIL, R3 NO-GO, R2 GO(1h, ảo theo audit trước), R2b NO-GO đều giữ. Lý do: P0A/R3 đã gate theo quoteVol > 0 (Aerospike cũng có vol = 0 ở đoạn stale) nên coin stale gần như không vào quan sát; R2 `all_ret7` (không gate) chỉ lệch −0,013 pp trung bình (max 2,35 pp/lệnh).
5. **Vấn đề lớn hơn đuôi stale là tập "listing"**: 26/490 listing của R2 không phải listing thật (16 của auditor trước + **10 mới**: BNX, BTCDOM, PUMP, TLM, ICP, BNT, OG, RIF, MAVIA, D). Trong đó **v1 bị cắt đầu đời** ở BNX/BTCDOM/ICP/TLM/PUMP/USDC (Vision hiện có giờ thật sớm hơn first_ts v1) → `listing_day` từ `first finite` của v1 sai. R2b D0 1m sau loại 26: **+2,00 % CI raw [−0,15; +4,51], infl lo −0,54, bỏ top10 % −3,04** → G1, G5 vẫn trượt → NO-GO giữ.
6. **Funding cache cũng nhiễm**: 50 092 kỳ funding (54 symbol, rate ≠ 0, ~+0,005…0,01 %) **sau** giờ giao dịch thật cuối cùng — funding "giả" trong đoạn settle. Không đổi verdict nào (coin stale không vào quan sát), nhưng phải lọc nếu dùng funding cho coin đã chết.

## 1. Cơ chế lỗi (builder + loader)

| tầng | hành vi | hệ quả |
|---|---|---|
| Nguồn Vision `futures/um/monthly/klines/{SYM}/1h` | hợp đồng delist/settle vẫn có kline mỗi giờ, `volume=0, trades=0`, O=H=L=C=giá settle, kéo dài tới 2026 (FTM, KLAY, MKR… đo trực tiếp) | chuỗi close "sống" tiếp với giá hằng |
| Aerospike `test.kline_1m_opt` | cũng có phút vol=0 cho mã đã chết (FTM/KLAY có mặt ở phút 2025-12-31 23:59 với v=0) | qv cache: 13 164 symbol-ngày `qv=0` sau giờ thật cuối |
| `closes1h_build.py` (`one_month`) | `return ot, c` — bỏ cột 5 (volume) và 8 (trades) | không lọc được giờ settle; ghi thẳng vào bin |
| loader dạng ma trận (`load_hourly` của P0A/R2/R3) | ô hữu hạn cuối = `last_day` | `last_day` của 58 mã bị đẩy tới 2025-12-31; `rename_like`/ghép "chết ↔ niêm yết" không bắt được S/KAIA/SKY… |
| `all_ret7` (R2/R2b), `excess` | trung bình ret mọi coin có close tại t0 — không gate volume | coin chết đóng góp ret = 0 vào benchmark ALL |
| P0A / R3 | state/entry đòi `tsh_z` hoặc `qv>0` (từ Aerospike) | coin stale tự bị loại khỏi entry → miễn nhiễm gần hoàn toàn |

Ghi chú phụ: v1 cũng **thiếu** dữ liệu thật ở vài mã (Vision hiện có 112 516 giờ vol>0 không có trong v1): BTCDOM (39 211 giờ, v1 chỉ có 2023-04→2024-11 rời rạc), USDC (v1 có 1 record), BNX (thiếu 2022-04→2023-02 và 2024-11→2025-03), ICP (thiếu 2021-05→2022-06), TLM (thiếu 2021-07→2022-06), EOS (thiếu 2024-11-22→2025-05-21), PUMP (thiếu 2025-04→07), AERGO/MAVIA (lỗ 3 491/2 993 giờ), ~60 mã thiếu 1 ngày (24–32 giờ) mà Vision đã backfill sau. **v2 KHÔNG bổ sung** (v2 = tập con v1 + NaN) để giữ so sánh sạch; xem §7.
`trend_rank_ic.load_closes` cộng thêm `+H` vào ts (coi ts là open time) trong khi ts đã là close time → trễ thêm 1h (bảo thủ, không leak) — ghi nhận, không thuộc phạm vi sửa.

## 2. Quét stale / ffill toàn bộ 627 symbol (v1)

Định nghĩa: giờ "thật" = record v1 có Vision volume > 0 (khớp 99,947 % record v1 theo (ts,sym); 5 450 record v1 không còn trong Vision — tháng 2022-02 Vision đã xoá — xử lý bằng close-đứng-yên, không record nào rơi vào đuôi/gap). Đuôi stale = mọi record sau giờ thật cuối; gap giữa = run giờ không giao dịch ≥ 24h kẹp giữa 2 giờ thật. Cột "close-only" = cách đo của auditor trước (close bằng hệt giá cuối) để đối chiếu.

| chỉ số | giá trị |
|---|---|
| symbol có đuôi stale | **79** (≥24h: 76; ≥7 ngày: 75; ≥30 ngày: 59) |
| … chạm hết DEV (ts 2026-01-01 00:00) | **58** |
| … dừng trước DEV end (v1 ngừng ở 2024-04-11 / 2024-05-28 …) | 21 (SC, BTS, SRM, FTT, RAY, HNT, TOMO, FOOTBALL, BLUEBIRD, ANT, GAL, FRONT, RNDR, BTT, AUDIO, DGB, MATIC, STRAX, LUNA, AKRO, ANC) |
| gap giữa ≥ 24h | 1 (LITUSDT 2025-01-31 → 2025-12-19, 7 719h: Litentry delist, ticker LIT tái dùng 12/2025) |
| head stale (vol=0 trước giờ thật đầu) | 0 |
| giờ vol=0 lẻ (<24h) giữa chuỗi | 303 (giữ) |
| run ≥24h close đứng yên mà CÓ volume | 7 mã, đều là 1 giờ volume lẻ trong đuôi settle (REEF, OMG, VIDT, TROY, AI16Z, QUICK, SKATE) |
| \|ret 1h\| > 50 % | 147 (v1 = v2), **147/147 khớp Aerospike** (biến động thật) |
| close v1 ≠ Vision | 24 record (Vision sửa sau, đã biết từ RESULT_F0) |
| symbol-giờ giả theo năm | 2022: 4 689 · 2023: 25 539 · 2024: 37 093 · 2025: 253 189 · (2026-01-01 00:00: 58) |

Top 30 theo mức nghiêm trọng (giờ giả = đuôi + gap; đầy đủ 80 dòng ở `data/meta/stale_scan_v1.csv`):

| sym | first_ts v1 | giờ thật cuối (close ts) | giờ giả | chạm DEV end? | status lineage | đuôi close-only |
|---|---|---|---|---|---|---|
| SC | 2021-04-12 | 2022-06-17 09:00 | 15939 (664 d) | không (dừng 2024-04-11) | delisted | 15939 |
| BTS | 2021-02-01 | 2022-08-18 09:00 | 15574 (649 d) | không (dừng 2024-05-28) | delisted | 15574 |
| SRM | 2021-01-01 | 2022-11-15 05:00 | 13442 (560 d) | không (dừng 2024-05-28) | delisted | 13442 |
| OCEAN | 2021-01-01 | 2024-06-25 10:00 | 13310 (555 d) | có | renamed_to:FET | 13310 |
| AGIX | 2023-02-16 | 2024-06-25 10:00 | 13310 (555 d) | có | renamed_to:FET | 13310 |
| FTT | 2022-04-15 | 2022-11-14 04:00 | 12344 (514 d) | không (dừng 2024-04-11) | delisted | 973 |
| RAY | 2021-08-20 | 2022-11-15 04:00 | 12320 (513 d) | không (dừng 2024-04-11) | delisted | 973 |
| KLAY | 2021-10-12 | 2024-10-22 09:00 | 10455 (436 d) | có | renamed_to:KAIA | 10455 |
| HNT | 2021-01-01 | 2023-03-20 10:00 | 10437 (435 d) | không (dừng 2024-05-28) | delisted | 10437 |
| UNFI | 2021-02-19 | 2024-10-30 10:00 | 10262 (428 d) | có | delisted | 10262 |
| KEY | 2023-05-24 | 2024-12-03 09:00 | 9447 (394 d) | có | delisted | 9447 |
| REN | 2021-01-01 | 2024-12-03 10:00 | 9446 (394 d) | có | delisted | 9446 |
| LOOM | 2023-10-11 | 2024-12-09 09:00 | 9303 (388 d) | có | delisted | 9303 |
| ORBS | 2023-10-17 | 2024-12-09 09:00 | 9303 (388 d) | có | delisted | 9303 |
| XEM | 2021-03-03 | 2024-12-09 10:00 | 9302 (388 d) | có | delisted | 9302 |
| BOND | 2023-10-15 | 2024-12-16 09:00 | 9135 (381 d) | có | delisted | 9135 |
| BLZ | 2021-01-01 | 2024-12-23 09:00 | 8967 (374 d) | có | delisted | 8967 |
| DAR | 2022-04-29 | 2024-12-26 10:00 | 8894 (371 d) | có | renamed_to:D | 8894 |
| FTM | 2021-01-01 | 2025-01-06 10:00 | 8630 (360 d) | có | renamed_to:S | 8630 |
| REEF | 2021-02-22 | 2025-01-22 10:00 | 8246 (344 d) | có | delisted | 8247 |
| OMG | 2021-01-01 | 2025-01-31 10:00 | 8030 (335 d) | có | delisted | 8031 |
| LIT | 2021-02-18 | (gap giữa) | 7719 (322 d) | gap giữa | relist | 0 |
| AMB | 2023-03-30 | 2025-02-21 09:00 | 7527 (314 d) | có | delisted | 7527 |
| STMX | 2021-03-22 | 2025-02-21 10:00 | 7526 (314 d) | có | delisted | 7526 |
| LINA | 2021-03-19 | 2025-03-27 10:00 | 6710 (280 d) | có | delisted | 6710 |
| COMBO | 2023-06-02 | 2025-03-27 10:00 | 6710 (280 d) | có | delisted | 6710 |
| VIDT | 2024-08-23 | 2025-04-14 10:00 | 6278 (262 d) | có | delisted | 6279 |
| TROY | 2024-10-31 | 2025-04-14 10:00 | 6278 (262 d) | có | delisted | 6279 |
| BAL | 2021-01-01 | 2025-04-14 10:00 | 6278 (262 d) | có | delisted | 6278 |
| BADGER | 2023-11-09 | 2025-04-14 10:00 | 6278 (262 d) | có | delisted | 6278 |

Còn lại (đuôi, giờ): NULS 6278, ALPACA 5894, TOMO 4702, LOKA 3927, DEFI 3423, MEMEFI 3422, LEVER 2871, MKR 2751, BSW 2583, OMNI 2414, ALPHA 2390, NEIROETH 2318, UXLINK 2318, BAKE 2151, HIFI 2150, SLERF 1742, FOOTBALL 1510, BLUEBIRD 1510, ANT 1366, AI16Z 1334, KDA 1334, MYRO 1143, 1000X 1143, FLM 975, XCN 975, PERP 974, PORT3 929, PONKE 807, SWELL 807, QUICK 806, STRAX 651, MILK 639, OBOL 638, SXP 638, TOKEN 638, FIS 519, VOXEL 519, REI 518, SKATE 518, AIA 491, GAL 452, FRONT 447, RNDR 333, BTT 296, AUDIO 285, DGB 243, MATIC 159, LUNA 14, AKRO 2, ANC 1.

Đối chiếu claim auditor trước (9 mã): FTM 8 630h, KLAY 10 455h, ALPACA 5 894h, MKR 2 751h, GAL 452h, RNDR 333h, MATIC 159h — **khớp đúng từng giờ**; EOS, BNX không stale (đúng) nhưng **v1 cắt cụt** (Vision có giờ thật tới 2025-05-21 / 2025-03-17). FTT/RAY: cách đo close-only chỉ thấy 973h vì v1 có lỗ 11 346–11 370h giữa đuôi.

## 3. Lineage — `data/meta/symbol_lineage_v2.csv` (627 dòng)

Cột: `first_real_ts`/`last_real_ts` = phút 1m thật đầu/cuối (open, UTC; Aerospike phút có v>0 trong cửa sổ quanh giờ thật của Vision — 543/611 mã refine được tới phút; 78 mã left-censored ≤ 2021-01-01; còn lại mức giờ Vision), `first/last_real_h_v1` (theo v1), `status`, `listing_flag`, `uncertain`, `notes`, `symId_old_map` (map cũ `_ev2out/symbol_map.csv`: **0 khác biệt symId** với map hiện hành trên 627 mã). "Đời thật" = hợp v1 (giờ vol>0) với Vision hiện tại (bắt cả phần v1 bị cắt).

| status | n | danh sách |
|---|---|---|
| active | 511 | — |
| delisted | 75 | (66 có đuôi stale trong v1) |
| renamed_to:X | 14 | AGIX→FET, OCEAN→FET (merge ASI), BNX→FORM, DAR→D, EOS→A, FTM→S, GAL→G, KLAY→KAIA, MATIC→POL, MKR→SKY, RNDR→RENDER, TOMO→VIC, NU→T, KEEP→T |
| renamed_from:Y | 9 | A, D, FORM, G, KAIA, POL, RENDER, SKY, S (mã mới niêm yết −7…+60 ngày sau khi mã cũ dừng) |
| relist | 11 | 1000LUNC, USTC, RAYSOL, BSV (đã biết); LIT (ticker tái dùng, gap 7 719h); ICP, TLM, MAVIA (gap ≥30 ngày trong Vision); BNT, OG, RIF (funding cache có kỳ từ 165–951 ngày trước giờ thật đầu → hợp đồng cũ cùng ticker) |
| index | 6 | BTCDOM, DEFI, FOOTBALL, BLUEBIRD, XAU (TradFi), PAXG (gold-backed) |
| stable/fiat-like | 1 | USDC |

Heuristic rename (mã mới niêm yết trong [−3d, +14d] quanh giờ thật cuối của mã chết, tỉ giá ≈ 1:1 ±5 % hoặc 10^k / 60 / 24 000): **yếu**. Với tỉ giá bội 10^k bắt ~40 cặp ngẫu nhiên (lịch niêm yết/delist dày); với 1:1 ±5 % chỉ đúng RNDR→RENDER (+10d, 1,041), FTM→S (+10d, 1,023), EOS→A (+7d, 1,018), BNX→FORM (+2d, 0,91 — không 1:1), MKR→SKY (+1d, 1/21 470 ≈ 1/24 000 −11 %). KLAY→KAIA cách 43 ngày (tỉ 2,93 — giá chạy), GAL→G 35 ngày, MATIC→POL 9 ngày (1,105). ⇒ **dùng danh sách tường minh** (`RENAME` trong script), heuristic chỉ để báo dấu hiệu. R2 `rename_like` (±3 ngày, 1/1000/0,001 ±5 %) trên v2 bắt 4 cặp — **cả 4 sai** (LINA→NIL, TROY→PROMPT, LEVER→ARIA ~1000×, UXLINK→HANA ~1×), và vẫn **0/8** rename thật ⇒ giả thuyết "ffill chặn rename_like" chỉ đúng một nửa: sau khi sửa ffill, quy tắc ±3 ngày vẫn hỏng vì rename thật cách 7–43 ngày.

**Ca không chắc (32 mã có cột `uncertain`)** — chính:
- LUNA2 (Terra 2.0, giữ listing), T (Threshold, futures niêm yết ~1 năm sau merge NU/KEEP → giữ listing), VIC (Viction, ~16 tháng sau TOMO dừng → giữ listing): xếp ngược lại cũng hợp lý.
- DAR→D (+14d, tỉ 1,26 lệch), GAL→G, KLAY→KAIA (ngoài cửa sổ ±14d): giữ rename vì có thông báo migration; số liệu không tự xác nhận.
- BSV: auditor trước xếp relist (Binance bỏ BSV 2019); dữ liệu 2021+ không thấy đời trước → dựa thuần vào hiểu biết ngoài.
- UXLINK→HANA (niêm yết 2h sau, ~1:1): trùng hợp (UXLINK bị hack/delist), không phải rename.
- ALPACA→ALPINE, BOND→FARTCOIN, XEM→PENGU, MATIC→UXLINK: dấu hiệu heuristic 1:1 ngẫu nhiên, bỏ qua.
- v1 cắt đầu/cuối đời: BNX, BTCDOM, ICP, TLM, PUMP, USDC (đầu); EOS, BNX, BTCDOM, USDC, 币安人生 (cuối).
- BNT/OG/RIF (relist theo funding cache): Vision không còn dữ liệu đời cũ — chỉ 1 nguồn chứng cứ.

### Tập listing sạch — `data/meta/listing_clean_v2.csv`

Ứng viên = mã có giờ thật đầu trong [2022-01-01, 2025-12-24] hoặc có trong tập `find_listings` của R2 (v1). `keep` = listing thật (status ∉ {renamed_from, index, stable, relist}, universe USDT, và **first_ts v1 không muộn hơn giờ thật đầu > 1 ngày**). R2 (v1) có 490 listing → **giữ 464, loại 26**:
- 16 của auditor trước (khớp đủ 16/16): RENDER, POL, KAIA, S, A, SKY, G, FORM · FOOTBALL, BLUEBIRD, PAXG, XAU · 1000LUNC, USTC, BSV, RAYSOL.
- **10 mới**: D (rename DAR), BTCDOM (index, v1 cắt đầu), BNX (v1 cắt đầu: thật từ 2022-04-01, R2 lấy 2023-02-22), PUMP (thật từ 2025-04-12, R2 lấy 2025-07-10), ICP/TLM/MAVIA (relist sau gap 100–295 ngày), BNT/OG/RIF (relist theo funding cache).
- 0 listing thật bị R2 bỏ sót. `listing_day` (D0) của R2 cho **464/464** mã giữ lại trùng ngày với phút 1m thật đầu (Aerospike) — mở rộng kết luận 20/20 của auditor vòng 3 ra toàn tập.

## 4. CLOSES_1H_v2 + mask + manifest

| file | đường dẫn | md5 | record |
|---|---|---|---|
| v1 (không đổi) | `/home/ubuntu/java/fsrun/CLOSES_1H.bin` | `6c7548801136655065edfd8e6cd7c0af` | 10 322 386 |
| **v2** | `/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin` | `58f56069e8e1a7c739011ddfa13e9636` | 10 009 513 (7 695 NaN) |
| **mask** | `/home/ubuntu/java/fsrun/CLOSES_1H_v2_mask.bin` | `ad4a2dc04ebfe2a30663f13b72a7ba73` | 326 321 |
| manifest | `data/meta/DATA_MANIFEST_v2.json` | — | quy tắc, flag, md5, kiểm loader |

Quy tắc (chọn **NaN + mask**): (a) đuôi sau giờ thật cuối → **bỏ record** (chuỗi kết thúc sạch như EOS); (b) run không giao dịch ≥ 24h giữa chuỗi → **giữ record, close = NaN** (loader dạng dài thấy NaN, không âm thầm nối 2 đoạn); (c) giờ vol=0 lẻ < 24h → giữ, chỉ đánh dấu. Format v2 y hệt v1 (14 B big-endian `[ts close][symId][close f32]`, sort (ts, tên)); mask 11 B `[ts][symId][flag u8]`, flag bit: 1 tail-bỏ, 2 gap-NaN, 4 vol=0 lẻ-giữ, 8 record v1 không còn trong Vision (chưa kiểm volume, giữ), 16 head-bỏ (0 ca), 32 suy từ close-đứng-yên (0 ca). Phần còn lại của v2 **trùng byte giá trị** với v1 (`subset_identical=True`), ts tăng dần, 0 trùng khoá, max ts 2026-01-01 00:00.

Kiểm loader cũ (đọc v2 bằng đúng hàm cũ, chỉ đổi đường dẫn):
- `short_v2_p0a_statemap.load_hourly`: OK (lọc `isfinite`) — C (38 017 × 626).
- `short_v3_r2_listing.load_hourly`: OK, assert lưới 1h PASS, `n_rows_bad = 7 695` = số NaN bị loại.
- `trend_rank_ic.load_closes`: đọc được nhưng **không lọc NaN** → 7 695 NaN đi vào rolling (ồn, không âm thầm). Nếu dùng v2: thêm `np.isfinite(c)` vào mask.
- Reader Java (`VolTargetSizing`, `PacingSizing`…): **chưa kiểm** (cấm Java sim). Float NaN sẽ đi thẳng vào Java — không trỏ Java sang v2 trước khi thêm xử lý NaN.

## 5. Audit dữ liệu toàn diện (0-sim)

**Coverage symbol-giờ** (record hữu hạn):

| năm | v1 | v2 hữu hạn | v2 NaN | bỏ |
|---|---|---|---|---|
| 2021 | 960 768 | 960 768 | 0 | 0 |
| 2022 | 1 204 325 | 1 199 636 | 0 | 4 689 |
| 2023 | 1 647 281 | 1 621 742 | 0 | 25 539 |
| 2024 | 2 427 790 | 2 390 697 | 0 | 37 093 |
| 2025 | 4 081 632 | 3 828 443 | 7 695 | 245 494 |

**Số symbol active theo tháng** (≥1 record hữu hạn; v1 → v2): 2021-01 84→84 · 2022-07 135→135 · 2023-01 148→146 · 2024-01 247→243 · 2025-01 368→356 · 2025-07 484→458 · "2026-01" (chỉ record ts 2026-01-01 00:00) 590→532 (chênh lớn nhất 58 = số mã đuôi chạm DEV end). Bảng đủ 61 tháng trong `docs/audit/DATA_AUDIT_20261003.json`.

**Phân phối lỗ (giờ thiếu giữa 2 record hữu hạn cùng mã)** — v1 → v2: 1h 24→24 · 2–5h 7→0 · 6–23h 461→355 · 24–167h 318→268 (6 912h) · 168–719h 9→4 · ≥720h 6→4 (28 140h: SC, FTT, RAY, BTCDOM — v1 thiếu thật). Lỗ còn lại là dữ liệu **thiếu**, không phải giả; loader ma trận cho NaN.

**Mẫu Aerospike 1 ngày/tháng** (ngày 15, 60 ngày × 1 440 phút; symbol-giờ "thật" = ≥1 phút v>0):

| năm | giờ thật (Aero) | v1: thiếu | v1: giả (có record, không giao dịch) | v2: thiếu | v2: giả |
|---|---|---|---|---|---|
| 2021 | 31 409 | 0 | 0 | 0 | 0 |
| 2022 | 39 393 | 3 (0,008 %) | 163 (0,41 %) | 3 | **0** |
| 2023 | 53 143 | 0 | 840 (1,56 %) | 0 | **0** |
| 2024 | 78 240 | 2 | 1 180 (1,49 %) | 2 | **0** |
| 2025 | 116 025 | 119 (0,10 %) | 7 367 (5,98 %) | 119 | **0** |

Close v2 vs close phút :59 Aerospike trên mẫu: 318 086 cặp, 0 lệch > 1e-4, max |rel| = 0.
**Spot-check 30 symbol ngẫu nhiên** (seed 20261003, 1 ngày ngẫu nhiên/mã, 24 giờ): 720/720 giờ khớp tuyệt đối (max |rel| = 0), trải 2021–2025.
**Outlier |ret 1h| > 50 %**: 147 trong v2, 147/147 khớp Aerospike (cả 2 đầu) → biến động thật, không phải lỗi giá.

**Funding cache `/tmp/fund_cache.npz`** (1 814 663 kỳ, 633 mã; 626/627 mã v1 có funding, thiếu 币安人生):
- 4 kỳ ts vô nghĩa (ts = 0 / −28 800 000, rate 0: GAIB, GRAM, STPT×2) — vô hại (bị lọc bởi `ts > t_start`).
- 743 724 kỳ ts lệch giờ tròn 1–3 ms (vd `…:00:00.002`): `funding_cum` (P0A/R3) dùng trần lên lưới → đúng; `Fund.window` (R2) dùng `(t0, t1]` với t1 tròn giờ → kỳ settle đúng lúc thoát bị đẩy sang cửa sổ sau (lệch ≤ 1 kỳ/lệnh, chưa đo, nhỏ).
- 4 rate ngoài [−3 %, +3 %]: ALPACA ±3–4 % ngày 2025-04-29/30 (trước delist; sát trần ±4 % — khả năng thật, chưa đối chiếu nguồn thứ 2).
- 6 khe > 8h (6 mã), cận dưới 5 469 kỳ thiếu (chưa phân rã theo mã; khe dài khả năng là đoạn relist).
- **50 092 kỳ funding (54 mã, rate ≠ 0, median +0,01 %) sau giờ giao dịch thật cuối +8h** — funding giả trong đoạn settle (SC, FTT, RAY… tới 2025-06; MATIC, FRONT tới 2025-12-31).
- 147 mã có kỳ funding đầu trước giờ thật đầu (median 11,5h — funding niêm yết trước lệnh đầu; 4 mã > 30 ngày: BNT, OG, RIF → relist §3; UNFI trước đầu dữ liệu 2021-01).

**qv cache** (`p0a_cache/qv`, 2021-09-01 → 2025-12-31, 405 938 symbol-ngày, 626 mã): mọi ngày `nrec = 1 440` (Aerospike đủ phút); 13 484 symbol-ngày `qv = 0` (78 mã) — **13 164 sau giờ thật cuối** (stale), 320 trong đời sống (ngừng giao dịch tạm); 0 NaN; 0 ngày qv>0 sau giờ thật cuối. Trên v2: 392 454 symbol-ngày có close → **0 ngày qv = 0**, 0 ngày thiếu dòng qv.

## 6. Ảnh hưởng lên benchmark cũ (chạy lại đúng code cũ, chỉ đổi đường dẫn CLOSES; không biến thể mới)

Tái lập v1 trước: P0A ALL|7 (n 338 375, bleed −0,390 %, pSQ10 0,3658), R3 BRK|3/7 (netproxy, excess_short), R2 D0 (n 489, net +4,410 %, excess +2,449 %) **khớp JSON đã commit tới mọi chữ số** ⇒ so sánh v1/v2 hợp lệ.

| benchmark | chỉ số | v1 | v2 | verdict v1 → v2 |
|---|---|---|---|---|
| P0A ALL T=7 | n · bleed_7d · pSQ10 · netproxy | 338 375 · −0,390 % · 0,3658 · +0,829 % | 338 302 · −0,390 % · 0,3658 · +0,829 % | FAIL → FAIL |
| P0A ALL T=7 theo năm (bleed / pSQ10) | 2022 · 2023 · 2024 · 2025 | −2,182/0,348 · +1,802/0,346 · +1,206/0,412 · −1,807/0,350 | −2,182/0,348 · +1,802/0,346 · +1,206/0,412 · −1,808/0,350 | — |
| P0A ALL T=3 / T=14 | bleed · pSQ10 | −0,151 / 0,2017 · −0,755 / 0,4982 | −0,151 / 0,2018 · −0,755 / 0,4983 | — |
| P0A BLEED T=7 | excess · netproxy · CI raw | +0,054 % · +0,947 % · [−0,10; +2,09] | +0,055 % · +0,948 % · [−0,10; +2,09] | không ô nào pass (C2/C3) |
| R3 BRK T=3 | netproxy · excess_short · pSQ10 / ALL | −2,420 % · −0,021 % · 0,4355 / 0,2055 | −2,422 % · −0,023 % · 0,4359 / 0,2055 | NO-GO → NO-GO (G1–G5 đều False) |
| R3 BRK T=7 | netproxy · excess_short · pSQ10 / ALL | −1,657 % · −0,150 % · 0,5223 / 0,3690 | −1,659 % · −0,151 % · 0,5228 / 0,3691 | — |
| R2 D0 1h | net · excess vs ALL · excess CI raw | +4,410 % · +2,449 % · [−1,56; +6,54] | +4,410 % · +2,436 % · [−1,56; +6,48] | GO → GO (vẫn "ảo" theo audit 10-02) |
| R2b D0 1m, toàn tập 489 | net · CI raw · CI infl · bỏ top10 % · excess | +2,097 % · [−0,10; +4,69] · [−0,49; +5,16] · −2,81 % · +2,449 % | như v1 · excess +2,436 % | NO-GO (G1, G5 trượt) |
| R2b D0 1m, −16 | (tái lập auditor trước) | +1,984 % · [−0,22; +4,54] · [−0,62; +5,00] · −3,04 % | excess +2,479 → +2,473 % | NO-GO |
| R2b D0 1m, **−26 (listing_clean_v2)** | n 464 | +1,999 % · [−0,15; +4,51] · [−0,54; +4,97] · −3,04 % · excess +2,314 % | excess +2,307 % | NO-GO |

Cơ học: P0A chỉ mất 73/338 375 quan sát T=7 (ngày cuối đời có cả cửa sổ forward là stale → v2 không còn giá hữu hạn), **0 quan sát đổi ret**. R2 `all_ret7`: v2 bớt trung bình 15,7 coin/thời điểm, lệch −0,013 pp (max |Δ| 2,35 pp/lệnh), PnL lệnh không đổi (Δ = 0). Beta-neutral (`short_betaneutral_score.py`) **không đọc CLOSES_1H** (dùng nhãn `ds_label15m` + bins) → không đo ở đây; nhãn có thể dính cùng hiện tượng settle nếu sinh từ kline không lọc volume — chưa kiểm.

**Kết luận ảnh hưởng: không verdict nào (P0A, R3, R2, R2b) đổi; mọi thay đổi ≤ 0,02 pp.** Đuôi stale là lỗi dữ liệu thật nhưng các vòng trước miễn nhiễm phần lớn nhờ gate quoteVol (P0A/R3) và nhờ mẫu số lớn (R2). Rủi ro thật nằm ở các phép dùng `last finite` (ngày chết, rename, survivorship, đếm universe theo tháng — lệch tới 58 mã cuối 2025) và ở tập listing (26/490 nhiễm).

## 7. Khuyến nghị

1. **Mọi vòng sau dùng `CLOSES_1H_v2.bin` + `CLOSES_1H_v2_mask.bin`**, ghi md5 v2 trong pre-reg. Loader dạng dài phải lọc `np.isfinite(close)`; không trỏ reader Java sang v2 trước khi thêm xử lý NaN.
2. **Listing**: dùng `data/meta/listing_clean_v2.csv` (`keep=True`, 464 mã cho cửa sổ R2) thay cho `first finite` của CLOSES. Ngày chết / rename: dùng `symbol_lineage_v2.csv` (`last_real_ts`, `status`) — không dùng `last finite`.
3. **Funding**: cắt mọi kỳ funding sau `last_real_ts` (50 092 kỳ giả). Nếu dùng `Fund.window` (R2), chuẩn hoá ts funding về giờ tròn (`ts // H * H`) trước khi so `(t0, t1]`.
4. **Benchmark ALL**: thêm gate "có giao dịch thật tại t0" (qv>0 hoặc mask=0) cho mọi phép trung bình kiểu `all_ret7` — hiện chỉ P0A/R3 có gate ngầm.
5. **Sửa builder** (`research/pipeline/closes1h_build.py` là .py → đề xuất, KHÔNG áp lên dữ liệu cũ):

```python
# one_month(): giu volume + trades thay vi bo
    K = K.iloc[:, :9].apply(pd.to_numeric, errors="coerce")
    ot = K[0].to_numpy(np.int64); c = K[4].to_numpy(np.float32)
    v = K[5].to_numpy(np.float64); n = K[8].to_numpy(np.float64)
    return ot, c, v, n
# one_sym(): sau khi sort/unique — cat dau/duoi khong giao dich, NaN run >= 24h giua chuoi
    real = (v > 0) | (n > 0)
    if not real.any(): return sid, empty...
    k0, k1 = np.flatnonzero(real)[[0, -1]]
    ot, c, real = ot[k0:k1 + 1], c[k0:k1 + 1], real[k0:k1 + 1]
    for s, e in runs(~real):                     # run lien tiep khong giao dich
        if (ot[e - 1] - ot[s]) // HOUR_MS + 1 >= 24:
            c[s:e] = np.nan
# va ghi them file volume/trades song song (hoac mask) de reader tu quyet dinh
```
Generator gốc của v1 (trước F0) không có trong repo; F0 tái lập cùng logic ⇒ cùng lỗi. Nếu có generator Java ở nơi khác: cần cùng thay đổi (không sửa ở đây).

## 8. Giới hạn / việc còn lại

- v2 **không lấp** dữ liệu thật mà v1 thiếu (112 516 giờ vol>0 có trong Vision hiện tại: BTCDOM, USDC, BNX, ICP, TLM, EOS, PUMP, AERGO, MAVIA, ~60 mã thiếu 1 ngày). Nếu cần: dựng `CLOSES_1H_v3` = v2 ∪ Vision-vol>0 (khác byte, phải pre-reg lại).
- Phân loại relist/rename ở §3 dựa một phần vào hiểu biết ngoài (danh sách tường minh); ca không chắc liệt kê ở cột `uncertain` (32 mã). BNT/OG/RIF relist chỉ có chứng cứ funding cache.
- Chưa kiểm reader Java với NaN; chưa kiểm nhãn `ds_label15m` / bins `predict_wf_*` (beta-neutral, S1) có dính giờ settle không.
- Funding: chưa đo tác động off-by-one ms ở `Fund.window`; chưa phân rã 6 khe > 8h.
- Không dùng dữ liệu 2026 để chấm (Vision quét tới 2025-12; Aerospike chỉ đọc tới phút 2025-12-31 23:59).

## 9. Tái lập

```
cd /home/ubuntu/src/BinanceFuturesJava
python3 research/analysis/data_audit_v2.py vision scan aero lineage build audit impact   # ~12 phut; build tu choi ghi de v2 (FORCE_V2=1)
```
Đầu ra phụ (không commit, ngoài repo): `~/claude_master/1003/data_v2/` (`vision1h.npz` snapshot Vision 2026-10-03, `stale_v1.csv`, `gaps_v1.csv`, `outliers_*.csv`, `rename_candidates.csv`, `aero_sample.parquet`, `audit.json`, `impact.json`). Commit: `docs/audit/DATA_AUDIT_20261003.{md,json}`, `data/meta/{symbol_lineage_v2.csv, listing_clean_v2.csv, stale_scan_v1.csv, DATA_MANIFEST_v2.json}`, `research/analysis/data_audit_v2.py`.
Lưu ý tái lập: Vision là nguồn biến động (RESULT_F0) — chạy lại `vision` ở ngày khác có thể đổi vài record cờ; v2 md5 chỉ đảm bảo với snapshot `vision1h.npz` ngày 2026-10-03.
