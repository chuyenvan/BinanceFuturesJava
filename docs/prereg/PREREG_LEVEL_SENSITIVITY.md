# PREREG_LEVEL_SENSITIVITY — tăng N (per-coin event) + độ nhạy (HOLD × phí) cho nhóm level-signal

Chốt: **2026-09-22, TRƯỚC khi chạy bất kỳ phép đo nào.** Commit file này phải có TRƯỚC mọi commit
script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; thứ tự commit ngược ⇒ kết quả **VOID**). Sau
khi chạy **KHÔNG sửa thiết kế** (pool, trigger, lưới 9 ô, chi phí, cổng thống kê, số rep, seed).

## 0. Vì sao + câu hỏi phải trả lời

`docs/result/RESULT_HARNESS_CONTROL.md` (commit `4f83902`) kết luận: bộ đo **đáng tin** (positive control
MOM15 p(>0)=1.000, null p=0.0000, negative control **0/200 false-positive**) NHƯNG **DEV thiếu
power**: MDE = **0,50%**/lệnh (basis pre-reg) / **2,00%**/lệnh (basis đúng cụm, N≈3,2k) /
**4,00%**/lệnh (N≈100–1 000). Vì vậy mọi NULL trước đây với N nhỏ (BIG_UP N≈89, MEDIUM_UP N≈316,
MEDIUM_DOWN N≈158 trên DEV cũ) là **"chưa phân giải được"**, KHÔNG phải "đã chứng minh không có".

Ba việc của vòng này:

- **(i) TĂNG N** bằng **per-coin event** thay vì chỉ đo ở tầng market-level.
- **(iii) ĐỘ NHẠY (sensitivity)** theo **2 giả định**: `HOLD ∈ {4h, 24h, 72h}` × `phí ∈ {0.05%,
  0.10%, 0.15%}` = **9 ô cho mỗi level-signal**, báo **TOÀN BỘ 9 ô** (không chọn ô tốt nhất).
- **(C) MDE mới** sau khi tăng N ⇒ trả lời: **với N mới, hiệu ứng cỡ %/lệnh nào mới phân giải được.**

## 1. Ràng buộc (bắt buộc)

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java trên Oracle (đang có job shadow).
  **THUẦN PYTHON** (đọc `raw/*.f32` + Aerospike `funding_data` chỉ-ĐỌC). **KHÔNG push**.
- **KHÔNG chạm HOLDOUT 2026** (dữ liệu chặn ≤ `2025-12-31`).
- Pre-reg này commit TRƯỚC; sau đó không sửa thiết kế. Dọn file tạm sau khi chốt số.

## 2. Cửa sổ mẫu (khác 2 vòng trước — ghi rõ lý do)

| Nhãn | Cửa sổ | Vai trò |
|---|---|---|
| **DEV** | `entry_ts ∈ [2022-01-01 00:00 UTC, 2026-01-01 00:00 UTC)` = **2022-01 → 2025-12** (4 năm) | **CHÍNH (headline)** |
| **ALL** | `[2021-01-01, 2026-01-01)` = 2021-01 → 2025-12 (5 năm) | **PHỤ** |

**Cảnh báo ghi trước:** `ALL` **gồm 2021** (ngoài DEV) ⇒ `ALL` **KHÔNG sạch như DEV** (2021 là
bull/alt-season cực mạnh, đã thấy ở mọi vòng trước: MOM15 2021 +3,26%, BIG_UP 2021 +24,89%…).
Mọi số `ALL` phải đọc kèm nhãn này; **kết luận chỉ dựa trên DEV**, `ALL` để đối chiếu.

Ghi chú so táo-với-táo: DEV ở đây **rộng hơn** DEV của 2 vòng trước (2022-01..2024-06). Vì vậy
**N và MDE sẽ khác**; khi so N cũ vs N mới phải so **cùng cửa sổ DEV** (tính lại N cũ trên cửa sổ
mới), không so số đã công bố của cửa sổ hẹp hơn.

## 3. Harness TÁI SỬ DỤNG NGUYÊN (không được đổi — để so được với 3 vòng trước)

Chép nguyên từ `docs/prereg/PREREG_HARNESS_CONTROL.md` §2 / `PREREG_BIGUP_MEDIUPDOWN.md` §2:

| Thành phần | Giá trị (KHÓA) |
|---|---|
| Nguồn | `raw/<sym>.f32` (627 USDT-perp, 1 nến 1M/dòng, `int32 epoch_minute + float32 O/H/L/C/V`, UTC, 2021-01-01..2025-12-31) = dẫn xuất causal của Aerospike `kline_1m_opt`; chỉ nến **đã đóng** |
| Funding | Aerospike `funding_data` (chỉ đọc), 8h cadence; tổng rate trong `(m, exit]`; long trả funding dương |
| Entry | `close(m)` / Exit | close của nến cuối cùng có dữ liệu trong `(m, m+HOLD]`; hụt ⇒ `short_delist=1` (GIỮ); `m+HOLD` vượt cuối dải ⇒ **edge-censored, LOẠI** |
| Slippage | `0.5 × (high(m) − low(m)) / entry` (không phụ thuộc HOLD) |
| net | `net = raw − phí − slip − funding` |
| CI | block-bootstrap moving-block **block = 72h** (`entry_ts // (72·60)`), **2000 rep**, **seed 20260905**, percentile 2.5/97.5, nửa-độ-rộng **×1.21** (`CI_INFLATE_LEGACY`) ⇒ `CI72h×1.21`; báo kèm `p(mean>0)` |
| Null | block **sign-flip** 72h, 2000 rep, seed 20260905 ⇒ `p(≥obs)` |
| ICC | theo ngày entry (GMT+7) và theo block 72h |
| Decay | theo năm (nhãn GMT+7 = `entry_ts+420`) |
| Universe | toàn bộ 627 symbol có file 1M (gồm coin delist; không lọc survivorship) |

**Scalar cross-sectional** (tái tạo đúng `calRateChangeAvg`, k = `min(100, ⌊n·4/5⌋)`, `n ≥ 50`
symbol/phút): `rc_i(m)=close/open−1`; `d15_i(m)=close_i/max(high_i, 15 nến gồm m)−1`;
`rateDownAvg` = mean k giá trị **nhỏ nhất** của `rc`; `rateUpAvg` = mean k giá trị **lớn nhất**;
`rateDown15MAvg` = mean k giá trị **nhỏ nhất** của `d15`.

## 4. Signals (tập quyết định k = 3) + 1 dòng reference

Nhãn level mỗi phút 1M theo **đúng thứ tự if-else loại trừ nhau** của code cũ `157cf4d`
(`PREREG_BIGUP_MEDIUPDOWN.md` §1.1/§2.3), fire mỗi phút khi nhãn = level:

| Signal | Điều kiện (nguyên văn code cũ) | Trong tập quyết định |
|---|---|---|
| **BIG_UP** | `rateUpAvg > 0.025` | ✔ |
| **MEDIUM_UP** | `rateUpAvg > 0.015` | ✔ |
| **MEDIUM_DOWN** | `rateDownAvg < −0.030` ∨ (`rateDownAvg < −0.014` ∧ `rateDown15MAvg < −0.07`) | ✔ |
| *MOM15 (reference)* | `rateDown15MAvg < −0.028` (= `SMALL_DOWN_15M`, "= MOM15 live") | ✘ descriptive |

`BIG_DOWN_OLD`, `SMALL_UP`, `SMALL_DOWN`, `MEDIUM_DOWN_15M` **được sinh nhãn** (để loại trừ đúng
thứ tự) nhưng **không đo** ⇒ giữ k=3 (chống multiple-comparison len lỏi).

**MOM15 (reference)** dùng làm **positive control neo** ở N mới: nó đã được chứng nhận là thật ở
`RESULT_HARNESS_CONTROL` §2. Nếu phép đo mới **không** nhìn thấy nó ⇒ bộ đo vẫn hỏng. MOM15 **ngoài
tập quyết định**, không tính vào multiplicity của 27 ô.

## 5. Pool đo — market-level vs per-coin (câu trả lời cho "(i) TĂNG N")

**Pool 1 — `M-LEVEL` (đối chiếu "đúng code", N nhỏ):** đúng luật 2 vòng trước: duyệt `d15` **tăng
dần** (rớt 15M sâu nhất trước), bỏ symbol đang **lock** (`lock` = sau fire `(m,s)`, `s` khoá tới
`m+HOLD`), lấy **2** coin (`NUMBER_ORDER = 2`). Một event = `(m, s)`. Dùng để **tái tạo lại N cũ**
(kiểm chứng tái tạo) và để so với pool 2.

**Pool 2 — `P-COIN` (PRIMARY, N lớn):** với mỗi phút fire `m` của level `L`, **mọi coin** `s` trong
**cross-section hợp lệ tại `m`** — đúng **tập ứng viên** mà code cũ duyệt (`getTopSymbol` trên
`rateDown15M2Symbols`, `DetectEntrySignal2TradeNormal.java:246-266`): coin có file 1M, có nến tại
`m`, `rc` và `d15` **hữu hạn**, và `n(m) ≥ 50`. Một event = `(m, s)`; **KHÔNG lock** (đo toàn bộ
tập coin mà luật chọn coin của code "nhìn thấy", không chỉ 2 coin nó bốc ra).

> **Diễn giải ghi trước (để không tự lừa):** `P-COIN` **bỏ thành phần chọn coin** ⇒ nó đo **hiệu
> ứng THỜI ĐIỂM** của level-signal (trung bình forward return của một coin bất kỳ trong universe
> trong lúc level fire). `M-LEVEL` = thời điểm **+** chọn coin. Vì vậy `P-COIN` **không** trả lời
> "chọn top-2 coin rớt sâu nhất có edge không" — câu đó thuộc `M-LEVEL`; `P-COIN` trả lời "ở cấp
> độ mẫu lớn, lúc big-up/dip level fire thì universe forward ra sao". Cả hai **đo cùng một giả
> thuyết vào-lệnh** (fire + mua coin), chỉ khác luật chọn coin; phần chênh = **selection
> contribution** (descriptive, §7.3).

**Pool 3 — `P-COIN-DEDUP` (secondary, chống lạm phát N):** từ `P-COIN`, giữ **1 event cho mỗi
`(coin, block-72h)`** = phút fire **sớm nhất** của coin đó trong block. Dùng để kiểm tra kết luận
`P-COIN` không phải do một vài episode dài được đếm lặp.

**Báo cáo bắt buộc:** `N` market-level (M-LEVEL) **vs** `N` per-coin (P-COIN), và **`N_eff` (block
72h)** = số block 72h **khác nhau** có chứa event (+ N/N_block).

## 6. Lưới độ nhạy — 9 ô (câu trả lời cho "(iii)")

`HOLD ∈ {240, 1440, 4320}` phút (= 4h, 24h, 72h) × `phí ∈ {0.05%, 0.10%, 0.15%}` (taker **mỗi
chiều** = ½ phí; tức 0.025%/0.05%/0.075%). Slippage + funding **giữ nguyên** luật harness §3
(funding tính lại đúng theo từng HOLD). **24h/0.10% = ô đúng harness 3 vòng trước** (neo so sánh).

- **Báo cáo TOÀN BỘ 9 ô cho MỖI signal** (N, meanNet, CI72h×1.21, p(>0), ICC) — **KHÔNG được chọn
  ô tốt nhất** để kết luận. Nếu chỉ một ô "sống" ⇒ §9 luật UNCONFIRMED, **không được áp dụng**.
- **Multiplicity:** lưới chính = 3 signal × 9 ô = **K = 27** phép kiểm định (pool P-COIN, DEV).
  Ngưỡng hiệu chỉnh: **Bonferroni một phía `p(mean≤0) < 0.05/27 = 0.001852`**, CI hiệu chỉnh =
  percentile bootstrap tại `[0.05/(2·27), 1 − 0.05/(2·27)]` = `[0.0926%, 99.9074%]` (**không** nhân
  ×1.21 — ×1.21 là hệ số legacy cho ứng viên đơn, báo kèm riêng). Báo **cả** `CI72h×1.21` (chuẩn
  legacy để so 3 vòng) **và** `CI72h-Bonf27`; chỉ coi là "sống" khi `CI72h-Bonf27 lo > 0`.
- Phí vào **tuyến tính như dịch hằng số**: `net(fee) = net(0.10%) ∓ 0.05%`; CI percentile **dịch
  đúng bằng hằng số đó** (kiểm chứng đẳng thức ở §8.C) ⇒ 3 ô phí là **cùng một chuỗi bị dịch**.
  Ghi rõ điều này khi đọc bảng (không coi 3 ô phí là 3 bằng chứng độc lập).

## 7. Phép đo thống kê (khóa trước khi chạy)

1. **Headline mỗi ô:** `meanNet`, `win = P(net>0)`, `meanRaw`, `CI72h×1.21`, `p(>0)` (tỉ lệ rep
   bootstrap có mean > 0), `half-width`.
2. **Null test:** block sign-flip 72h ⇒ `p(≥obs)`.
3. **Selection contribution (descriptive):** hiệu `mean(M-LEVEL) − mean(P-COIN)` **trên cùng phút
   fire** (tính tại tầng phút: mỗi phút fire lấy `mean(net)` của 2 coin được chọn − `mean(net)`
   của toàn bộ pool), block-bootstrap như trên. Không dùng để quyết định GO/NO-GO.
4. **ICC** (ngày, block 72h), **`%coin+`** (≥1/≥5/≥10 trade), **theo năm** (2021..2025).
5. **`N_eff` (block 72h)** cho mỗi pool/signal (§5).

## 8. C. MDE cho N mới (đơn vị **%/lệnh**)

Dùng **cách đã làm** ở `RESULT_HARNESS_CONTROL` §4: với chuỗi `net` của một ô, lấy **chuỗi đã
center** `x − mean(x)`; mỗi rep bootstrap (`r = 1..2000`, seed 20260905) cho nửa-độ-rộng
`h_r = (p97.5 − p2.5)/2 × 1.21`; `power(X) = P(h_r < X)`; **MDE(80%)** = `X` nhỏ nhất trong lưới
`X ∈ {0.02, 0.05, 0.10, 0.20, 0.25, 0.50, 1.00, 2.00, 4.00}` (%) có `power ≥ 80%`. Báo kèm
`h_r` p50/p80/p95.

**Đẳng thức phải kiểm chứng (ghi trước):** với dịch hằng số `X`, percentile CI dịch **đúng** `X`
⇒ `CI_lo(X) = CI_lo(0) + X` ⇒ `phát hiện ⟺ X > h_r`. Kiểm chứng bằng cách tính trực tiếp
`CI_lo(X=1%)` cho 3 rep và so với `CI_lo(0)+1%`; **sai khớp phải < 1e-9**, nếu không ⇒ MDE VOID.

MDE báo cho: **mỗi signal × mỗi pool (P-COIN, M-LEVEL, DEDUP) × mỗi ô (9)** trên **DEV** — để trả
lời trực tiếp "với N mới, hiệu ứng cỡ nào mới phân giải được". Kèm **đường MDE theo N** (200, 500,
1 000, 5 000, 20 000, 100 000 event — lấy mẫu con không lặp từ chuỗi P-COIN DEV, 200 rep/N).

## 9. Luật kết luận (khóa trước — chống chọn ô sau khi thấy số)

- **R1 — "sống" ở một ô nào đó nhưng KHÔNG vượt hiệu chỉnh multiplicity** ⇒ kết quả đó ghi rõ
  **UNCONFIRMED**: nó là **chọn ô sau khi nhìn kết quả** (post-hoc grid) ⇒ **KHÔNG được áp dụng**;
  muốn dùng phải **pre-reg riêng + test forward trên dữ liệu mới**.
- **R2 — TẤT CẢ 9 ô × 3 signal đều NULL (kể cả sau hiệu chỉnh hay không)** ⇒ đây mới là **NULL
  ĐÁNG TIN** (vì lúc đó MDE đã nhỏ, xem §8) — **khác hẳn** các NULL cũ với N nhỏ, vốn là "chưa
  phân giải được".
- **R3 — GO-đủ-điều-kiện** chỉ khi: `CI72h-Bonf27 lo > 0` **và** dấu ổn định theo HOLD, phí, năm,
  **và** `P-COIN-DEDUP` cùng dấu, **và** `%coin+ ≥ 50%`. Kể cả khi đó **vẫn KHÔNG tự tích hợp**;
  chỉ đề xuất bước forward riêng.
- **Kết luận cuối phải trả lời đúng 1 câu:** *sau khi tăng N, level-signal nào (nếu có) còn đáng
  theo, và vì sao.*

## 10. Tiên lượng ghi trước (không sửa sau khi thấy số)

1. `P-COIN` cho N lớn (10^4–10^5 mỗi signal DEV) nhưng **`N_eff` (block 72h) bị chặn bởi số block**
   (DEV 4 năm ≈ 487 block) ⇒ **MDE không nhỏ vô hạn**; dự kiến `MDE(P-COIN) ≈ 0,5–1,0%`/lệnh (so
   4,00%/lệnh ở N≈100–1 000 cũ) — tức **vẫn không đủ** để phân giải hiệu ứng ≲ 0,5%.
2. `P-COIN` là hiệu ứng **thời điểm**: dự kiến **MEDIUM_DOWN dương** (cùng họ dip-buy với MOM15) và
   **BIG_UP/MEDIUM_UP ≈ 0 hoặc âm** (mua dip trong lúc breadth đang xanh = nghịch pha).
3. `M-LEVEL ≈ P-COIN` (chênh ≈ 0) ⇒ **chọn top-2 coin rớt sâu nhất không thêm alpha** — lặp lại
   B-SECONDARY của `RESULT_HARNESS_CONTROL` §3.
4. Lưới: **dấu không đổi** theo HOLD; độ lớn giảm tuyến tính theo phí (dịch hằng số, §6).
5. Dự kiến **KHÔNG ô nào vượt hiệu chỉnh Bonferroni K=27**.
6. MOM15 (reference) **vẫn dương** ở N mới — nếu không ⇒ bộ đo hỏng, mọi kết luận VOID.

Đây là **tiên lượng**, KHÔNG phải kết luận. NULL thì báo NULL.

## 11. Artifact

- Sinh tín hiệu + pool: `research/analysis/level_sensitivity.py` → `/tmp/level_sens/*.npz`
  (nén; gồm `minute, sym, level, block, raw{h}, slip, fund{h}` cho `h ∈ {240,1440,4320}`).
- Thống kê/lưới/MDE: `research/analysis/level_sensitivity_stats.py` → `report.txt`.
- Kết quả: `docs/result/RESULT_LEVEL_SENSITIVITY.md`. File tạm dọn sau khi chốt số.
