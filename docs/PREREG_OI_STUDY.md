# PREREG_OI_STUDY — OPEN INTEREST (OI) như trục dữ liệu CHƯA TỪNG dùng

Ngày chốt: 2026-09-23. **Chốt TRƯỚC khi đo bất kỳ số nào.** Sau khi đo **không sửa thiết kế**;
mọi thứ không có trong file này là **post-hoc** và phải dán nhãn như vậy.

Ràng buộc thi hành: thuần **Python**, **không** Java trên Oracle (shadow đang chạy), **không**
`claude-run`/Claude Code, **không push**, **không chạm HOLDOUT 2026** (mọi cửa sổ thống kê
`< 2026-01-01`). Trung gian ra file **ngoài repo** (`/tmp/oi_study/`) để resume được.

---

## 0. Dữ liệu — Bước 0 đã xác minh (schema in ra từ chính file)

| mục | giá trị |
|---|---|
| OI | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` |
| sha256 | `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec` (đã đối chiếu `OI_FIX_LOG.md` §3) |
| kích thước | 4 227 723 300 byte = **140 924 110** bản ghi × **30 byte**, dư 0 |
| dtype | `>i8 ts_ms`, `>i2 symId`, `>f4 ×5` — khớp `OI_DT` của `train_funding_selector.py` / `compare_features.py` |
| lưới thời gian | `ts % 300000 == 0` **100%** ⇒ nhịp **5 phút**; `ts` range **2021-01-01 00:00 → 2026-06-30 23:55 UTC**; 0 trùng lặp (file build theo block symbol, **không** sort theo ts) |
| symbol | **779** symId (id 1..828); `symbol_map.csv` 863 dòng `symId,symbol` |
| 5 cột | `oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`, `taker_buy` (tên theo `OI_NAMES`, 2 nơi dùng độc lập) |
| chiều thời gian | **CỬA SỔ ĐÃ ĐÓNG `[t−5m, t)`** ⇒ mọi bản ghi tại `t` là **CAUSAL** (`OI_FIX_LOG` §2: `taker_buy` khớp cửa sổ đã đóng **450/450** mẫu; `ts=2024-03-04 00:00` không tồn tại ở 0/259 symbol = dấu vết phép dịch `+5m` đã áp **khi build**) |

### 0.1 Ngữ nghĩa 5 cột (đọc trực tiếp `ExportFundingOiPerCoin.writeCoin`, dòng 93-140)

```
oi_delta24h(t) = oi[t] / oi.floorEntry(t-24h) - 1        guard: STALE_MS=1h, past != 0
oi_z(t)        = (oi[t] - mean_{<=t}) / sd_{<=t}          expanding TRÊN TOÀN lịch sử (n>=2, var>0)
ls_global(t)   = floorStale(lsg_raw, t, 1h)               (RAW, không biến đổi)
ls_toptrader(t)= floorStale(lst_raw, t, 1h)
taker_buy(t)   = r/(1+r), r = floorStale(takerLS_vol, t, 1h)
```
⇒ **Hai cột thực sự là OI** (`oi_delta24h` = ΔOI% 24h; `oi_z` = z-score expanding của **mức** OI).
`ls_*`/`taker_buy` **không phải OI** ⇒ **ngoài phạm vi** nghiên cứu này (không dùng, không báo).

**Hệ quả đã biết trước (ghi để không tự lừa):** file **không chứa mức OI thô** và **không chứa ΔOI
cửa sổ ngắn** (1h/4h). Do đó "ΔOI causal" khả dụng = `oi_delta24h` (ΔOI 24h) và các **sai phân**
của nó. Đây là hạn chế **chốt trước**, không phải phát hiện sau.

### 0.2 Giá / volume
`/home/ubuntu/claudedata/rvb_1m/raw/<SYM>.f32` — `ts <i4` (phút từ 2021-01-01 UTC), `o,h,l,c,v <f4`.
**627** symbol, 619 082 489 dòng, phủ **2021-01-01 → 2025-12-31 16:59 UTC** (không có 2026).
Giao với OI: **627/627** symbol raw đều có trong OI. Median dòng/symbol 654 030.
Đây đúng là nguồn `harness_control.py` / `range4h_topk.py` đã dùng (cùng `totalUsdt`⇒`v`, đã audit
trong `RESULT_COST_LIQUIDITY` G2).

### 0.3 Cửa sổ & đơn vị (CHỐT)
- **DEV = 2022-01-01 00:00 UTC → 2026-01-01 00:00 UTC (exclusive)** = 4 năm. Trùng
  `cost_breakeven.py` (`DEV_START=1640995200/60`, `DEV_END=1767225600/60`). 2021 chỉ là **warm-up**
  (dữ liệu OI bắt đầu 2021-01-01, `oi_delta24h` native nên warm-up ~0); **2026 KHÔNG đọc vào thống kê**.
- **IS/OOS nội bộ** (chốt trước, để có "OOS"): **IS = 2022-01-01..2023-12-31**, **OOS = 2024-01-01..2025-12-31**.
  Mọi phán quyết dựa **OOS**; IS chỉ để mô tả.
- **Thời điểm quyết định**: bản ghi OI tại mốc 5m `t` mô tả trạng thái **tại** `t`; giá vào =
  `close` của nến 1m tại **đúng phút `t`**. Nến `t` đóng ở `t+1m` ≥ thời điểm OI biết được ⇒ **không
  nhìn trước**. Đây là cùng quy ước với `harness_control.py` (`entry = cD[epos]`).

---

## 1. Ba giả thuyết (k = 3, KHÔNG thêm)

**Lưới cross-section: 1 GIỜ (UTC :00)** — chốt 1 trong 2 lựa chọn (5m | 1h). Lý do chốt: dữ liệu
OI 5m bị lấy mẫu thừa (96% dư), lưới 1h trùng quy ước repo (OI giới hạn về `ts % 1h == 0` trong
`AUDIT_OI_FEAT_PARITY` §1), và giảm cộng dồn thời gian. **Universe tại mỗi mốc** = symbol có
`close` **và** `oi_delta24h` hữu hạn tại mốc đó; yêu cầu **≥ 50 symbol** (MIN_SYM, theo
`harness_control.py`). Decile/tercile = **rank tất định**: `bin = min(rank*K // N, K-1)`.

### H1 — ΔOI như FACTOR cross-section
- Factor chính `f = oi_delta24h(t)` (ΔOI 24h, causal).
- Forward return `H = 24h` (CHÍNH) từ `close(t)`; phụ: 4h, 1h.
- Xếp hạng **giảm dần** ⇒ **Q9 = ΔOI cao nhất**, Q0 = thấp nhất.
- Đo: `net` trung bình từng decile; **chênh với universe equal-weight cùng kỳ**
  (`Q_d − EW`); và "spread" `Q9 − Q0` (chỉ là **thông tin**, không phải leg giao dịch).
- **LONG-ONLY** ⇒ câu hỏi quyết định: **Q9 (và/hoặc EW đã) có `net > 0` sau phí, CI ngoài 0?**
  Nếu chỉ `Q0 < 0` (short mới ăn) thì kết luận **long-only KHÔNG khả thi**, không đề xuất short.
- **Biến thể đã đăng ký trước** (tất cả cùng 1 lưới/horizon chính): `dd24_1h = d24(t) − d24(t−1h)`,
  `dd24_4h = d24(t) − d24(t−4h)`, `oiz` (mức/z OI). H1 GO đòi hỏi **nhất quán dấu ở ≥3/4** biến thể.

### H2 — OI + GIÁ PHÂN KỲ
- Tại mỗi mốc giờ: `ΔOI = oi_delta24h(t)` **và** `P24 = close(t)/close(t−24h) − 1` (causal).
- Tercile độc lập theo `ΔOI` (T_OI ∈ {thấp, giữa, cao}) × tercile theo `P24` (T_P ∈ {thấp, giữa, cao}).
- Bảng **3×3 `net` H=24h**. Giả thuyết: ô **(T_OI cao, T_P thấp)** — OI tăng mạnh mà giá không tăng/giảm —
  có forward return **tệ hơn** ô **(T_OI cao, T_P cao)** và **tệ hơn universe EW**.
- Đo tương phản `net(T_OI cao, T_P thấp) − net(T_OI cao, T_P cao)` + CI + null.

### H3 — OI overlay lên MOM15
- Event = **đúng bộ MOM15 đang chạy live**: "M-LEVEL MOM15 k=1" (ledger `ml_min`/`ml_sym` của
  `/tmp/funding_factor/cache2.npz`, n=11 367 ALL / **7 128 DEV**), HOLD 24h.
- Tại entry `m` tra OI **causal**: bản ghi OI gần nhất ≤ `m` (**tolerance 15 phút**; 5m grid nên
  thực tế lệch ≤ 4 phút). Giữ event **chỉ khi** tra được (nếu thiếu ⇒ báo %coverage).
- Tách theo 3 cách: (a) `d24` **mức**, (b) `oiz` **mức**, (c) **rank percentile cross-section của `d24`**
  trong universe tại mốc giờ đó (đây là dạng "thông tin", không phải "lọc coin").
- Đo `net` 24h theo tercile + tương phản (cao − thấp) + CI + null + AUC(tách thắng/thua).
- **Bài học đã đo, ghi TRƯỚC để không tự lừa:** mọi **filter cấp-coin** trong repo này đều **VÔ HIỆU**
  (hệ lấy coin kế tiếp). ⇒ H3 **chỉ đo THÔNG TIN**. Nếu H3 dương, kết luận vẫn là
  **"thông tin, KHÔNG được đề xuất lọc coin"**, và bất kỳ đề xuất filter nào bị coi là **đã biết vô hiệu**.

---

## 2. Đo lường — harness chuẩn (dùng nguyên `research/analysis/harness_control_stats.py`)

- **Chi phí CHÍNH (mô hình harness đã dùng ở các vòng trước):**
  `net = raw − FEE_RT − SLIP − FUNDING`, với `FEE_RT = 0,0010` (taker 0,0005 × 2 chân),
  `SLIP = 0,5 × (high − low)/close` của **nến 1m tại phút vào**, `FUNDING` = tổng funding event có
  `ts ∈ (t, t+H]` (Aerospike `test/funding_data`, chỉ ĐỌC) — y hệt `harness_control.returns_for`.
- **Chi phí BIẾN THỂ (mô hình sim):** `net = raw − 0,0080 − FUNDING` (RATE_FEE 0,002 + SLIPPAGE 0,003×2 chân,
  `RESULT_COST_LIQUIDITY` §1). Báo kèm, **không** dùng để phán quyết.
- **CI**: block-72h bootstrap, **2000 rep, seed 20260905**, percentile 2.5/97.5, nửa-độ-rộng **×1.21**,
  centered trên `obs` ⇒ `CI72h_x1.21`. Hàm `block_boot` **chép nguyên**.
- **Null**: block sign-flip 72h (`block_perm`), 2000 rep, cùng seed. Báo `p(>=obs)`.
- **MDE**: (i) theo công thức harness: **p80** phân bố nửa-độ-rộng (×1.21) của chuỗi đã center trên
  500 rep null sign-flip; (ii) đối chiếu `2,8 × sd(null)`. Báo cả hai; ngưỡng phán quyết = (i).
- **N và N_eff**: `N_eff = N / (1 + (n̄_b − 1)·ICC72h)`, `n̄_b = N / n_blocks`; báo kèm ICC(day), ICC(72h),
  `n_blocks`. OI event **cum mạnh theo thời gian** ⇒ N_eff nhỏ là **kỳ vọng**, không phải lỗi.
- **Độ bền**: tách theo **quý** (16 quý) và theo **năm**; báo `%quý dương`.

## 3. Đối chứng (bắt buộc, chạy TRƯỚC khi kết luận)
- **(a) Universe equal-weight cùng kỳ** — mọi decile/tercile đều so với EW của **đúng mốc đó**.
- **(b) NEO MOM15** — tái lập `net@0,10% = +1,6690%` (±0,05pp), n = **7 128**, DEV 2022-01..2025-12,
  HOLD 24h, từ `m_raw[24h] − m_slip − m_fund[24h]` (`/tmp/funding_factor/pools.npz`).
  **Lệch ⇒ báo RỎ và KHÔNG kết luận.** (Đã tái lập trong lúc soạn pre-reg: **+1,6690%** ✔)

## 4. Luật kết luận (chốt trước)
Một giả thuyết **GO** chỉ khi **đồng thời**:
1. hiệu ứng **OOS** (2024-2025) > 0 **sau phí CHÍNH**;
2. **CI72h_x1.21 OOS ngoài 0** (hai đầu cùng dấu);
3. **nhất quán ≥ 60%** số **quý OOS** có hiệu ứng > 0 (và báo thêm `%coin+`);
4. **bền vững qua các biến thể đã đăng ký** (H1: ≥3/4 biến thể cùng dấu).
- Một biến thể dương mà biến thể khác không ⇒ **UNCONFIRMED (post-hoc)**.
- Không có hiệu ứng ⇒ nói thẳng **NULL**.
- **Không đề xuất áp dụng/tích hợp.** Không đề xuất lọc coin (đã biết vô hiệu).
- HOOK: **không** dùng 2026 dù chỉ 1 dòng; nếu vô tình đọc, dán nhãn và loại.

## 5. Output
`docs/RESULT_OI_STUDY.md` + script `research/analysis/oi_study_build.py`,
`research/analysis/oi_study.py`. Commit (**KHÔNG push**), dọn `/tmp/oi_study` sau khi commit.
