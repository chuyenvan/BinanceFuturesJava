# PREREG_SHORT_GATECLOSED — SHORT top-K8 selector tại tick GATE LONG ĐÓNG × trailing CÓ ARM (+ no-SL)

Ngày **2026-10-03**, branch `module`. Chốt **TRƯỚC** mọi phép đo kết quả (chưa chạy stage `sim`/`sanity`/`report`).
Nền: `REAUDIT_SHORT_FULLCHAIN_20261002.md` (`eeb55cb9`: F1 pool `cand_dev_x1` = 100 % tick gate mở; F4 trailing
không arm), `DATA_AUDIT_20261003.md` (`e5b89a31`: dữ liệu sạch v2). Code: `research/analysis/short_gateclosed_sim.py`
(stage `picks` đã chạy — chỉ đếm, không có PnL). k = 3 ô (E1/E2/E3), **1 selector, 1 seed**.

## 1. Feasibility (đo 2026-10-03, chỉ đọc)

**(a) Bins short — pool KHÔNG phải `cand_dev_x1`.** `~/sm_pathexit/sm/{OLD_ndown_S42,PA_t15_E10_S42,PA_t15_E10_S7}/predict_wf_*.bin`
(Kaggle `sm-pathexit`, pipeline `wfo-selector-v2-1m-canonical-20260804`, 45 feature selector, 16 fold 20220101..20251001,
purge 288 bước = 72h, nest 400, seed 42/7) chấm **toàn universe tại MỌI tick 15'**: PA_t15_E10_S42 = 35 806 379 dòng,
**140 244 tick** (= mọi tick 2022–2025 + 28 tick mép fold TZ+7), trung vị 233 dòng/tick, 621 symbol; OLD_ndown_S42 35 450 551
dòng / 139 381 tick (khớp `RESULT_SHORT_MODEL` §2). ⇒ Chỉ **FULLCHAIN** (`pred_s1a2x1`) chấm trên `cand_dev_x1`; các vòng
SHORT_MODEL / LABEL2 / PATHEXIT / BETANEUTRAL dùng bins toàn-tick ⇒ **trộn** gate mở ∪ đóng (≈92 % tick là gate đóng), chưa
từng **tách** gate đóng, và đều dùng trailing KHÔNG arm (`short_pathexit_sim.py:369-377`: `runmin·(1+T)` từ lúc vào, gồm
low nến kích), funding hằng số 0,585 %/72h, dữ liệu v1 (symbol ma sau delist).
**(b) Feature panel** — không cần: score đã có cho mọi (tick, symbol). Không export Java. **(c) Không train mới**:
`PA_t15_E10_S42` **chính là** model phương án (c) (nhãn `y=1[retEnd_72h ≤ −1,5 % ∧ maxFav_72h ≤ +10 %]`, recipe SHORT42
giữ hyper-param, seed 42, 16 fold, pool toàn universe mọi tick) ⇒ chi phí Kaggle 0. **Chọn `PA_t15_E10_S42`, cột `p3`**
(không dùng OLD_ndown_S42 / S7 ⇒ không có bội số selector).
Giới hạn: nhãn train lấy từ `.pb` dữ liệu v1 (symbol sau delist có nhãn giả ≈0 ⇒ nhiễu nhãn, không leak); model train
trên mọi tick (không riêng gate đóng).

**Gate.** `research/parity/data/p15_dev.csv` (WFO OOS 21 fold, AUDIT_G2FLAT3 Q3 không leak), `predReturn15M` tại **phút m0
= giờ mở nến 15'** (khớp cột `p15` của `cand_dev_x1` 100 %, đo trên 21 396 tick; lệch 1 phút chỉ khớp 0,02 %). Biết trước
entry ≥ 14 phút ⇒ causal. Gate đóng ⇔ `p15 < 0,008`.

**Tick 15' trong cửa sổ (UTC, sau lọc mép DEV `e+4320 ≤` 2025-12-31 23:59):**

| năm | gate ĐÓNG | gate MỞ | (đối chiếu F1 `cand_dev_x1`) |
|---|---|---|---|
| 2022 | 32 066 | 2 970 | 2 926 |
| 2023 | 34 529 | 510 | 510 |
| 2024 | 32 866 | 2 264 | 2 258 |
| 2025 | 23 266 | 11 484 (11 680 trước lọc mép) | 11 653 |

(Gate mở theo p15_dev hơi nhiều hơn F1 vì `cand_dev_x1` còn lọc ứng viên; không ảnh hưởng gate đóng.)

## 2. Cấu hình KHÓA

- **Universe tại tick** (lọc TRƯỚC xếp hạng): dòng bins có `p3` hữu hạn; symbol trong `data/meta/symbol_lineage_v2.csv`,
  `status ∉ {index, stable/fiat-like}`; `first_real_ts ≤ m0` và phút entry `e < last_real_ts`; bản ghi
  `CLOSES_1H_v2.bin` (md5 `58f56069…`) của giờ đã đóng gần nhất trước entry hữu hạn (NaN = không giao dịch).
  Loại 256 711 dòng lineage + 2 115 dòng v2-NaN. **KHÔNG lọc N1b** (funding đã tính exact vào net; tránh thêm 1 bậc tự do).
- **Tick**: mọi tick 15' (`ts` = giờ mở nến, UTC) 2022-01-01..2025-12-28 với `p15(m0) < 0,008`.
- **Ứng viên**: **top-K8 theo `p3`** (score short) trong universe tại tick. **Entry SHORT** tại **close phút 1m m0+15**
  (phút cuối nến 15' là m0+14 ⇒ t+1); giá P = close Aerospike `kline_1m_opt`; thiếu nến entry ⇒ bỏ lệnh (không thay).
- **Cooldown 24h/coin**: duyệt theo (tick, hạng); coin đã vào trong 1 440' trước (tính theo tick vào) ⇒ bỏ, không thay.
  Lệnh cùng coin có thể chồng nhau khi giữ > 24h (thống kê theo lệnh, không phải danh mục).
- **Exit** (đường giá phút e+1..e+TS, cắt tại `last_real_ts`):

| ô | arm | gap | SL cứng | time-stop |
|---|---|---|---|---|
| **E1** | 5 % | 3 % | +10 % | 72h |
| **E2** | 5 % | 3 % | **không** (giả thuyết owner) | 72h |
| **E3** | 3 % | 2 % | +10 % | 24h |

  Trailing: khi `min_low_since_entry ≤ P·(1−arm)` ⇒ mức trail = `min_low·(1+gap)`. Mức hiệu lực phút j chỉ dùng dữ liệu
  tới j−1 (low của chính nến kích KHÔNG được dùng). Hai stop cùng phía ⇒ mức hiệu lực = **mức gần giá hơn** =
  `min(trail, SL)`. Kích khi **HIGH 1m ≥ mức**; fill = `max(mức, open)` (gap-open ⇒ open). Hết TS ⇒ close phút cuối (ffill).
  Symbol hết đời thật trước TS ⇒ đóng tại close phút thật cuối (lý do DELIST).
- **Phí** 0,112 % RT trừ 1 lần. **Funding EXACT theo coin** (`/tmp/fund_cache.npz`, ts chuẩn hoá giờ tròn): Σ rate các kỳ
  trong (close entry, close exit]; SHORT **nhận** +rate, LONG trả. net = gross − 0,112 % + funding.

**Số lệnh (stage `picks`, trước sim — chỉ đếm):** SG 38 342 (2022 11 610 · 2023 9 503 · 2024 9 369 · 2025 7 860; 981 816 top-K8
trước cooldown); SO 14 334; RG 241 682.

## 3. Đối chứng (cùng universe/lọc/cooldown/exit/phí/funding)

- **(a) SO** — cùng selector top-K8 SHORT tại tick gate **MỞ** (`p15 ≥ 0,008`) — để so với FULLCHAIN.
- **(b) SG-LONG** — **cùng tập lệnh SG**, vào **LONG** với exit gương (arm/gap/SL/TS đối xứng: trail = `max_high·(1−gap)`,
  kích khi LOW ≤ mức, fill `min(mức, open)`), funding LONG trả. Kiểm hướng.
- **(c) RG** — **random-K8** tại tick gate đóng (u ~ U(0,1), `default_rng(20261003)`, top-8 theo u), SHORT, cooldown riêng.
  Beta thuần. RG có n lớn hơn (random ít trùng coin ⇒ cooldown ít chặn) — đã biết trước, không chỉnh.

## 4. Metric (mỗi ô × mỗi tập)

n, net mean & median, CI **block-72h** (block = `entry_ms // 72h`, NREP 2000, seed 20260905) **raw** và **inflate** (nhân
half-width `√(2 ln 3)` = **1,4823**), theo năm (UTC năm entry; mean, n), **trọng số theo NGÀY** (mean các mean ngày UTC) —
chỉ là thước đo tập trung, không phải quy tắc giao dịch, **bỏ top-5 ngày** (bỏ mọi lệnh của 5 ngày có Σnet lớn nhất, mean
theo lệnh; báo kèm bản theo ngày), SL-rate / trail-rate / time-rate / delist-rate, gross, funding TB, giữ TB, winrate,
đuôi p1/p5/min/p99/max. **Chênh SG − RG** và **SG − SO**: CI block-72h resample CHUNG tập block.

## 5. Luật GO (áp cơ học trên SG, từng ô E1/E2/E3; GO ⇔ ≥ 1 ô đạt ĐỦ)

1. net mean > 0 **và** CI raw **và** CI inflate nằm hoàn toàn > 0;
2. ≥ 3/4 năm (2022–2025) mean > 0;
3. theo-ngày > 0 **và** bỏ-top-5-ngày > 0;
4. n ≥ 1 500;
5. SL-rate ≤ 25 % (chỉ ô có SL: E1, E3; E2 miễn);
6. alpha không phải beta: RG cùng ô mean ≤ 0 **hoặc** CI raw của (SG − RG) > 0.

Không GO ⇒ NO-GO cho "short khi gate đóng + selector PA_t15_E10_S42 + trailing có arm". Đối chứng (a)(b) chỉ để diễn giải,
không vào luật. Không thêm ô, không đổi tham số, không đổi selector sau khi thấy số.

## 6. Sanity (bắt buộc trước khi báo)

- Assert causal: `e = m0+15`, `ts = m0·60 000`, p15 đọc tại m0, đường giá từ e+1; SG/RG p15 < 0,008, SO ≥ 0,008;
  `e+4320 < 2026-01-01` (0 phút 2026 được đọc).
- **So vectorized vs loop** (`exit_vec` vs `exit_loop`) trên MỌI lệnh có entry ngày **2024-03-05** (UTC): pnl |Δ| ≤ 1e-9,
  cùng phút thoát, cùng lý do.
- **10 lệnh mẫu** (tháng 202403, `default_rng(20261003)`): đọc lại Aerospike **độc lập** từng phút (`client.get`), tính lại
  bằng loop; P và pnl/phút thoát/lý do mọi ô phải khớp. Ghi bảng vào RESULT.
- Sai sót code phát hiện sau khi chốt ⇒ sửa bug (không đổi thiết kế), ghi rõ trong RESULT.

## 7. Kỳ vọng (ghi trước)

Tham chiếu gần nhất: PATHEXIT `PA_t15_E10_S42` TRAIL 5 % (không arm, mọi tick) net −0,09 % [−0,20; +0,01]; FULLCHAIN
(gate mở) âm. Kỳ vọng net SG ≈ 0 ± 0,3 %/lệnh; với n ≈ 38k lệnh, ~1 450 ngày, MDE ước 0,3–0,6 %/lệnh ⇒ power thấp cho
edge nhỏ. E2 (không SL) có đuôi trái dày (short không chặn) — p1/min báo bắt buộc.
