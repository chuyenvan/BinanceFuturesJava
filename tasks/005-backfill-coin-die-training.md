# TASK-005: Backfill ticker coin die cho TRAINING (226 → audit → 242 → re-export 100%)

- **status:** in-progress — B1 chốt 36 coin; PILOT LUNA B2-B5 XONG & PASS cả 226+242 (giá khớp CSV, coin khác bit-nguyên, mapper→760 nhất quán). ⏸️ chờ duyệt batch phần core còn lại.
- **Milestone:** ADR-0009 **P1** — điều kiện cần để train model mới. Mục tiêu THẤP: đủ data, KHÔNG cầu toàn.
- **Thực thi bởi:** Claude Code (**Java/Python**). Ghi Aerospike (226 trước, rồi 242).
- **Quyết định nền:** ADR-0009 (pivot) · ADR-0007 (39 coin die) · INGEST_FORMAT.md (format ghi) · TASK-001 (danh sách coin thiếu).

## An toàn (user xác nhận)
242 live chỉ dùng ~2 ngày gần nhất; lịch sử xa (coin die 2021-22) live KHÔNG đụng ⇒ ghi 242 vùng lịch sử **không rủi ro**. Vẫn **fill 226 trước → audit → mới đưa 242**.

## Mục tiêu (1 câu)
Có đủ ticker coin die trong 242 để **re-export 100% training data** không còn méo survivorship (feature avg top-100-sập + basket phụ thuộc TOÀN tập coin).

## Scope
**Trong:** ticker (giá) coin die; fill 226 → audit → 242; re-export training.
**Ngoài:** KHÔNG gen prediction (để P3 sau khi có model mới); KHÔNG funding (fee đang tắt); KHÔNG tinh chỉnh chất lượng (mục tiêu đủ, không hoàn hảo).

## Các bước (tuần tự, tự cập nhật trạng thái)
- [ ] **B1 — Chốt danh sách coin:** 39 coin die (TASK-001) + kiểm có đủ phủ top-100-sập/basket không (nếu thiếu, bổ sung coin delist khác từ enumerate Binance Vision). Liệt kê + khoảng đời mỗi coin.
- [ ] **B2 — Tải ticker** 1m từ data.binance.vision toàn vòng đời mỗi coin (trước delist). Đọc về, KHÔNG ghi vội.
- [ ] **B3 — Fill 226:** ghi ticker vào `kline_1m_opt` cluster **226** theo INGEST_FORMAT (key `yyyyMMdd-HHmm` GMT+7, value Snappy(MinuteDataFinal), **read-modify-write giữ coin khác**). ⚠️ Helper sẵn hardcode `getClient242()` → cần đường ghi **226** riêng (read-modify-write thủ công + **cấp id thủ công**, KHÔNG gọi `getId()` vì nó ghi mapper 242). Mapper id < 1000 (nextId 760).
- [ ] **B4 — Audit 226:** đọc lại vài mốc mẫu → (a) coin die CÓ mặt đúng giá; (b) **coin khác KHÔNG đổi** (so trước/sau); (c) mapper nhất quán. PASS mới sang B5.
- [ ] **B5 — Đưa lên 242:** sau audit OK, ghi cùng data lên cluster **242** (sync 226→242 nếu có cơ chế, hoặc chạy lại B3 trỏ 242). Audit 242 như B4.
- [ ] **B6 — Re-export 100% training data** (`RunFullDataCollection`) — BẮT BUỘC toàn bộ vì feature/label market-level đổi khi tập coin đổi. Xác nhận training data mới gồm coin die.

## Acceptance criteria
- [ ] Coin die có trong `kline_1m_opt` ở **cả 226 và 242**; audit xác nhận coin khác không đổi.
- [ ] Chỉ ticker (KHÔNG prediction/funding).
- [ ] Training data **re-export 100%**, có coin die trong feature/label.
- [ ] **Rollback ghi sẵn:** cách gỡ coin die khỏi 226/242 (theo id/symbol) nếu phát hiện hỏng.
- [ ] Java/Python, SLF4J (Java), KHÔNG System.out.

## ⚠️ Hệ quả sau task (ADR-0009)
Data nền đổi ⇒ **mọi golden baseline cũ + breaker 006 + scenario 006.1 thành vô hiệu**, phải chụp lại ở P3. Bump CONFIG_VERSION.

---
## (Code điền) Kết quả

### B1 — chốt danh sách coin (read-only, từ `outputs/survivorship_missing_symbols.csv` TASK-001)
Nguồn = universe data.vision USDT-perp (730) − coverage dataset (711) = 39 thiếu; 38 có monthly klines (LENDUSDT loại). **Trừ 2 rác meme** (`我踏马来了USDT`, `龙虾USDT`) → **36 coin backfill**. CSV đã có sẵn lifespan (firstDate/lastDate/daysAlive) + drawdown + diedNearZero + avgQV ⇒ không cần enumerate lại để lấy khoảng đời.

**Nhóm A — 12 coin DIED-NEAR-ZERO (đuôi ruin, ưu tiên):**
| coin | lifespan | days | DD đáy | diedNearZero | avgQV |
|---|---|--:|--:|:--:|--:|
| LUNAUSDT | 2021-01-28→2022-05-13 | 470 | −99.7% | ✓ | 609 837 |
| ANCUSDT | 2022-03-08→2022-05-13 | 67 | −99.7% | ✓ | 57 471 |
| DODOUSDT | 2021-02-19→2022-05-27 | 462 | −98.1% | ✓ | 41 722 |
| RAYUSDT | 2021-08-20→2026-06-01 | 1746 | −97.6% | ✓ | 6 486 |
| FTTUSDT | 2022-04-15→2026-06-01 | 1508 | −97.1% | ✓ | 8 901 |
| AUDIOUSDT | 2021-08-19→2024-05-28 | 1014 | −96.2% | ✓ | 27 098 |
| SRMUSDT | 2021-01-01→2024-05-28 | 1244 | −89.7% | ✓ | 29 486 |
| SCUSDT | 2021-04-12→2026-06-01 | 1876 | −88.4% | ✓ | 5 212 |
| AKROUSDT | 2021-01-19→2022-05-27 | 494 | −81.4% | ✓ | 22 373 |
| WAVESUSDT | 2021-01-01→2026-06-01 | 1977 | −80.6% | ✓ | 63 416 |
| BTSUSDT | 2021-02-01→2024-05-28 | 1213 | −78.9% | ✓ | 6 722 |
| HNTUSDT | 2021-01-01→2024-05-28 | 1244 | −97% từ đỉnh* | ✓ | 23 705 |
*HNT: drawdownToBottom(−9%) tính theo firstOpen gây hiểu lầm; lastClose/maxClose=0.026 ⇒ thật sự sập −97% từ đỉnh 55.

**Nhóm B — 24 coin còn lại (delist/thiếu, không near-zero):** ANT(−88.5%,884d), DGB(−95.7%,1867d), GAL(−94.8%,817d), TOMO(−62.9%,1244d), YFII(−28%,467d), BTT(−83.7%,296d), 1000BTTC(76d), BLUEBIRD(573d), BTCST(1915d), BZRX(353d), COCOS(462d), DOTECO(31d), FOOTBALL(636d), GLMR(979d), IDEX(1125d), KEEP(238d), MBL(196d), MDT(1067d), NU(117d), RAD(1118d), RNDR(544d), SNT(942d), STPT(957d), STRAX(964d). (DD/lifespan đầy đủ trong CSV.)

### Kiểm phủ "top-100-sập / basket"
- **Đầy đủ theo cấu trúc:** 36 = TOÀN BỘ USDT-perp-có-monthly-klines vắng khỏi dataset (universe data.vision − coverage). Mọi coin ruin lịch sử lớn đều có (LUNA/FTT/RAY/SRM/WAVES/DODO/AUDIO/ANC/BTS/SC/AKRO/HNT). 12 diedNearZero phủ đúng đuôi nặng → de-distort feature avg-top-sập + basket.
- ⚠️ **Phát hiện:** 13 coin có `lastDate=2026-06-01` (RAY, FTT, SC, DGB, WAVES, BTCST, GLMR, IDEX, MDT, RAD, SNT, STPT, STRAX) = **vẫn niêm yết, chỉ KHÔNG có trong dataset** (không phải delist). ⇒ gap survivorship gồm cả (i) coin chết thật + (ii) coin sống nhưng dataset chưa từng track. Cả hai cần thêm để basket đúng.
- ⚠️ **Giới hạn:** danh sách này KHÔNG gồm coin sập-nhưng-ĐANG-CÓ-một-phần trong dataset (đó là vấn đề data-completeness khác, ngoài survivorship-thiếu). Universe (730) lấy từ S3 listing đầy đủ ở TASK-001 — nếu muốn chắc 100% có thể enumerate lại data.vision (read-only, ~1') để xác nhận count, nhưng theo cấu trúc 36 đã là tập thiếu đầy đủ.

### Quy mô để B2/B3 lượng sức (CHƯA tải/ghi)
36 coin × daysAlive (31→1977) ≈ ~32k coin-ngày × 1440 ≈ ~46M bản ghi phút để đọc; ghi = read-modify-write theo key-phút (gộp coin) trên span ~2021→2026 (~2.85M key). NẶNG — cần xác nhận hướng/giới hạn trước khi chạy.

## DUYỆT B1 (Desktop) — chốt hướng thực thi

**1. Phạm vi coin — tách survivorship khỏi data-completeness:**
- **LÀM đợt này (core survivorship):** Nhóm A (12 near-zero) + các coin Nhóm B **DD sâu / sập mạnh** (ANT −88.5%, DGB −95.7%, GAL −94.8%, BTT −83.7%, TOMO −62.9%, + coin nào DD ≥ ~60%). Đây là phần méo feature top-100-sập + basket nhiều nhất.
- **HOÃN:** 13 coin `lastDate=2026-06-01` (sống-chưa-track) — chúng KHÔNG về-0 nên KHÔNG phải survivorship; thiếu chúng là data-completeness khác. Không lọt top-100-crashed ⇒ ít ảnh hưởng feature sập. Thêm sau NẾU re-export thấy basket còn lệch. (Lý do: mục tiêu ADR-0009 là sửa survivorship = thiếu coin CHẾT, không phải làm dataset hoàn chỉnh.)

**2. Thực thi PILOT trước (reversible + verify trước khi scale):**
- **Pilot = CHỈ LUNA**: B2(tải)→B3(226)→B4(audit coin-khác-KHÔNG-đổi + mapper)→B5(242)→audit. Validate trọn cơ chế ghi + cấp id trên 1 coin. **CHƯA re-export.**
- Pilot PASS (coin khác bit-nguyên, LUNA đọc lại đúng giá) → mới **batch** các coin core còn lại.
- **B6 re-export 100% chỉ chạy 1 LẦN** sau khi fill đủ core (KHÔNG re-export mỗi coin).

**3. Enumerate lại data.vision:** KHÔNG cần — TASK-001 (universe 730) đủ; coin chết quá khứ không đổi.

**4. Hướng ghi 226 + cấp id thủ công:** xác nhận. ⚠️ **id phải nhất quán 226↔242** (cùng coin = cùng id ở cả 2 cluster), KHÔNG trùng id hiện có (cấp từ nextId 760+), và **audit mapper sau ghi** (cả 2 cluster khớp).

**5. Tải về đĩa + audit mẫu giá TRƯỚC khi ghi Aerospike:** đồng ý — verify giá hợp lý/không gap lớn/format đúng trên đĩa trước, mới đụng cluster.

### B2-B5 — PILOT LUNA (XONG, validate cả 226 & 242)
- Tool: `ai_ml/validation/backfill/BackfillTickerPilot.java` (modes inspect/write/audit; đường ghi client226/242 riêng; cấp id THỦ CÔNG, KHÔNG getId; read-modify-write giữ coin khác; audit before/after).
- **B2** tải LUNAUSDT 1m data.vision 2021-01→2022-05 (17 file, 669590 nến) về `226:luna_csv/`. Audit đĩa: quỹ đạo $1.21→đỉnh$119→$0.0033 hợp lý; chỉ 2022-02 thiếu ~3 ngày (gap nhỏ, chấp nhận).
- **Inspect (cứu lỗi format):** key ticker là **FULL symbol** (`SUSHIUSDT`), KHÔNG phải short → tool sửa ghi full `LUNAUSDT`. Mapper LỆCH cluster: 226=751 / 242=759 (226 sau 242 8 id) → chọn **id=760** (free trên CẢ hai).
- **B3/B4 (226):** ghi 669590 record (100% record đã có coin khác → THUẦN thêm, 0 tạo mới); mapper[226] LUNAUSDT→760; **audit 8/8 mốc: coin khác BIT-NGUYÊN + LUNAUSDT present**; audit đọc-lại **giá 8/8 KHỚP CSV** suốt vòng đời. (~3.2')
- **B5 (242):** ghi 669590 record (0 tạo mới); mapper[242]→760; **audit 8/8 coin khác bit-nguyên**; đọc-lại **giá 8/8 KHỚP CSV**. (~5.5')
- **Nhất quán cluster:** LUNAUSDT→760 trên CẢ 226 & 242; cả hai nextId=761.

### Rollback (ghi sẵn — gỡ LUNA nếu cần)
Với mỗi key phút trong vòng đời LUNA: đọc record → `tickersMap.remove("LUNAUSDT")` → ghi lại (giữ coin khác); + `MapOperation.removeByKey(symbol_mapper/global_id_map, "LUNAUSDT")` trên cluster. (Sẽ thêm mode `remove SYMBOL CLUSTER` vào tool trước khi BATCH để rollback 1 lệnh.)

### ⚠️ Tác động baseline (theo ADR-0009)
Pilot ghi LUNA ticker vào 242 — NHƯNG sim chỉ trade theo **prediction** (LUNA chưa có ai_pred_market) ⇒ golden baseline + 006/006.1 **CHƯA bị đổi** bởi pilot này (ticker LUNA trơ với sim). Vô hiệu hóa baseline + bump CONFIG_VERSION xảy ra ở **P3** sau khi re-export + train model trên tập coin mới.

## (Code điền) Phát hiện ngoài scope

- **Mapper 226 sau 242 8 id (751 vs 759)** TRƯỚC pilot — coin die không liên quan, là lệch sync sẵn có. LUNA cấp 760 nhất quán; nhưng BATCH phần còn lại phải cấp id từ `max(226,242)+1` và audit mapper 2 cluster mỗi coin để KHÔNG để id lệch nghĩa giữa 2 node.
- Ghi 242 cross-VPN từ 226 vẫn nhanh (~5.5' cho 669k) — batch core (~vài triệu record) khả thi trong vài chục phút.

## (Code điền) Quyết định phát sinh
