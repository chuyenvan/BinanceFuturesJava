# PREREG_AUDIT_PNL — Audit độc lập NHÃN (b) + MÔ HÌNH PHÍ + NGUỒN GIÁ TRỊ CỦA RỔ

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC khi đọc bất kỳ số nào của lần audit này.
**Đối tượng bị audit:** `docs/result/RESULT_PNL_RULER.md` (commit `acb88bd`) — kết luận "alpha xếp hạng
trên 45 feature = 0 (0 chỉ số Δ ngoài CI)" và "mức lợi nhuận của rổ = 1,27–1,56 %/vòng".
**Luật:** không nới ngưỡng · không đổi định nghĩa sau khi đọc số · kết quả ≈ 0 thì **NÓI RỔ** · KHÔNG push ·
KHÔNG `claude-run` · **thuần Python offline** (không train, không chạy Java/sim, không build lại nhãn).

---

## 0. VÌ SAO AUDIT NÀY ĐỘC LẬP ĐƯỢC

Nhãn (b) KHÔNG được kiểm bằng chính output của nó. Toàn bộ audit **chạy lại exit engine từ đầu** trên
dữ liệu tick 1m thô, đọc TRỰC TIẾP từ file, rồi so với nhãn đã lưu.

**Cổng danh tính nguồn dữ liệu (chạy TRƯỚC, đã đo):**

| Nguồn | Neo | Bằng chứng |
|---|---|---|
| bins 1m tick | `/home/ubuntu/java/simulator/kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz` | `zcat … ticker_20220101.bin.gz \| md5sum` = `cf8f38ae65564187b5a19774c2c2d39f` = md5 file `ticker_20220101.bin` tải trực tiếp từ dataset Kaggle `chuyendinh/wfo-ticker-2022` (kernel `mr-labelb-cpu` đọc đúng 7 dataset `wfo-ticker-*`) ⇒ **byte-identical**. |
| tick size | `/home/ubuntu/java/exchange_info_pin.json` | md5 `5a815948d8909ea5b9615b28e28b53da` = `ds_mr_inputs/exchange_info_pin.json` của kernel |
| điểm S1 | `/home/ubuntu/mr_kaggle/ds_mr_inputs/pred_s1a2x1.parquet` | md5 `94d703a195e0d5b62ff9a3c7fac9cf87` = `ledger/pred_s1a2x1.parquet` |
| map symId→symbol | `/home/ubuntu/claudedata/symbol_map_20260806.csv` | khớp **559/559** cặp `(symId,symbol)` có trong `label_b_pnl.parquet` (các map khác khớp 559/559 nhưng thiếu symId) |
| nhãn | `/tmp/mrout/mrout/label_b_pnl.parquet` (309.024 dòng) | đối tượng audit |

**Mẫu/tham số KAGGLE của nhãn (đọc từ `research/kaggle/money_ranker/make_mr_kernels.py`, không suy đoán):**
`KMAX=32`, `CHUNK_DAYS=90`, `TS_MAX_MS=1758992400000` (2025-10-01 00:00 GMT+7), `CUTS` = 15 mốc
`20220401…20251001`, `MAX_INTERVAL_SEC=7200`, luật `P0` (`pred=None` ⇒ nhánh WEAK `cap=0,03`), entry
`E = close(t)`, `FEE_RT = 0,008`.

---

## 1. BA CÂU HỎI PHẢI TRẢ LỜI

- **(a)** Nhãn (b) có **đúng** không: chạy lại engine trên mẫu ⇒ lệch bao nhiêu, **có hệ thống** không?
- **(b)** **Phí thực** là bao nhiêu, và kết luận "alpha = 0" **có đổi** ở mức phí nào không?
- **(c)** Giá trị của rổ (**1,27 %/vòng**) đến từ **S1 pool** hay từ **luật thoát**? (số cụ thể + CI)

---

## 2. VIỆC 1 — AUDIT NHÃN (b)

**Cách chạy lại (độc lập):** gọi `research/exitfit/exit_engine.simulate` với `make_p0()` và
`pred=None`, entry `E=close(t)`, 1 leg — **giống hệt** đường của `research/pipeline/mr_label_build.sim_one`.
Bars đọc TRỰC TIẾP từ bins thô (`jbin.iter_minutes`), cửa sổ `[day(t) … day(t)+8]` (≥ 168 h + 1 ngày đệm).

**V1a — tái lập trên mẫu NHỎ (200 cặp):**
- Mẫu: 200 cặp `(t, sym)` **ngẫu nhiên không hoàn lại** từ 309.024 dòng nhãn, `SEED_A = 20260925`
  (`np.random.default_rng`), lấy theo **chỉ số dòng đã sort `(ts, sym)`** ⇒ tái lập được.
- So: `gross` (Δ = replay − nhãn), `tp`, `status`, `exit_ts`.
- Báo: **trung vị / mean / p05 / p95 của Δgross**, `%` cặp **khớp tuyệt đối** (`tp` và `exit_ts` bằng nhau),
  và **kiểm HỆ THỐNG**: (i) Δgross trung vị = 0? (ii) phân bố `sign(Δ)` theo **năm** và theo **status**
  (`TRAIL`/`TS168`/`OPEN_AT_END`); (iii) tương quan hạng giữa `gross_replay` và `gross_nhãn` (Spearman).
- Luật: `|trung vị Δgross| ≤ 1e-4` **và** ≥ 90 % cặp khớp tuyệt đối ⇒ **nhãn ĐÚNG**; ngược lại ⇒ **nhãn SAI**,
  báo rõ chiều và độ lớn (không hoà giải).

**V1b — 6,9 % cặp bị BỎ (chia khối 90 ngày):** bỏ có làm **lệch** không?
- Tái lập danh sách **ngày bị bỏ**: mỗi interval, `days_needed=[day_min(interval) … day_max+8]`, cắt thành
  khối 90 ngày, giữ `day ≤ b1−8` ⇒ khối nào cũng bỏ **8 ngày cuối** (trừ khối cuối của interval — ngoài
  dải tick nên không mất gì). **Cổng tự-kiểm:** số cặp bị bỏ phải ≈ **22,8k** (khai báo 6,9 %); nếu không
  khớp ⇒ dừng, báo là không tái lập được cơ chế bỏ.
- Mẫu: **200 cặp BỊ BỎ** (`SEED_B1 = 20260926`) + **200 cặp ĐƯỢC GIỮ** (`SEED_B2 = 20260926`), chạy lại engine.
- So phân bố `gross` (mean, trung vị, p05/p25/p75/p95, tỉ lệ `gross>0`) + **CI khối 72 h** của hiệu 2 mẫu.
- Luật: hiệu nằm trong CI ⇒ **không lệch**; ngoài CI ⇒ **bỏ gây lệch**, báo chiều.

**V1c — `OPEN_AT_END` (113 dòng, 0,037 %):** xử lý thế nào? Ghi RÕ theo **code** (`exit_engine.simulate`:
`price_tp = close(nến cuối mảng)`, `status="OPEN_AT_END"` ⇒ **mark-to-market tại nến cuối** trong cửa sổ,
**KHÔNG bỏ**). Báo: phân bố `gross` của 113 dòng + **mức gross/`glift8` của rổ khi BỎ 113 dòng** ⇒ xem
có đổi kết luận không (dự phóng thô: 0,037 % × Δ ≈ 0,02 % ⇒ không).

## 3. VIỆC 2 — AUDIT MÔ HÌNH PHÍ

- **Đo lại ước tính PHÍ THỰC/vòng** từ bằng chứng đã có (`RESULT_COST_REAL_AUDIT.md` §2.1/§2.2/§2.4 +
  `Configs.java`): **không** có `commission`/`orderId`/`FILLED` ở bất kỳ log nào ⇒ fee/slip **KHÔNG ĐO ĐƯỢC**;
  chỉ có mốc Binance USDⓈ-M VIP0 **taker 0,05 %/chân ⇒ 0,10 %/vòng = 0,001**. ⇒ mô hình 0,008 gồm
  `fee 0,002` (= **2×** mốc taker thật) + `slip 0,006` (**giả định**, chưa đo); proxy duy nhất liên quan
  ("khớp lệnh") là biến động, RT trung vị **1,91 %** — **không phải** slip. Ghi rõ đây là **khoảng**, không phải số đo.
- **Độ nhạy theo 4 mức phí CHOT TRUOC: `f ∈ {0,004 · 0,006 · 0,008 · 0,012}`**, cộng thêm **`f = 0,001`
  (taker thật)** và **`f = 0,002` (phần fee của mô hình)**. Ở mỗi `f`:
  1. `Δglift8` = `mean(gross|top-8) − mean(gross|tick)` ghép cặp theo tick chung — **với `y = gross − f`**;
  2. `Δnetm8(f)`, `netm8(f)` **mức tuyệt đối của rổ** + **CI khối 72 h** (`BLOCK_H=72`, `NREP=2000`,
     `SEED=20260905`, chuẩn CHẶT 1,21 — không nới);
  3. các chỉ số nhị phân `Δic/Δpacc/Δdec_mono` (nếu đổi theo `f` thì báo).
- **Dự đoán chốt TRƯỚC (để kết quả có thể phản bác):** Δglift8 **bất biến** với `f` (dịch hằng số không đổi
  hiệu 2 trung bình) ⇒ kết luận "alpha = 0" **KHÔNG THỂ đổi ở bất kỳ mức phí nào**. Nếu đo ra Δglift8 **đổi**
  ⇒ dự đoán này SAI ⇒ phải báo và giải thích. Cái **sẽ** đổi theo `f` là **mức net của rổ**; báo ngưỡng `f*`
  mà `netm8(f)` **rời 0** (ngoài CI) ⇒ chuyển hoá thành câu "rổ có lãi ở mức phí ≤ f*".
- Chi phí: **KHÔNG đọc bins** — dùng lại per-tick parquet `/tmp/mrpnp/cache/*.parquet` (do `mr_pnl_score.py`
  đã commit sinh); + 1 phép kiểm bất biến trực tiếp trên bins thô **1 fold** (`45deploy`, fold `20220101`).

## 4. VIỆC 3 — TÁCH NGUỒN GIÁ TRỊ CỦA RỔ

Cùng **luật thoát** (P0, `pred=None`), cùng **cửa sổ**, chỉ đổi **cách chọn rổ**:
- **R1 = top-32 theo S1** (pool P32 — đã có trong nhãn, KHÔNG chạy lại);
- **R2 = ngẫu nhiên 32 coin/tick** — rút **không hoàn lại** từ universe S1 tại tick đó, `SEED_C = 20260927`;
- **R3 = toàn thị trường** = **mọi coin có điểm S1 tại tick đó** (universe S1; coin không có nến tại `t`
  bị loại, báo số loại);
- **R4 (phụ, miễn phí)** = **bottom-32 theo S1** (tập con của R3) — để biết S1 có phân biệt chéo không.
- Mẫu: **200 tick** ngẫu nhiên không hoàn lại từ 9.657 tick của pool, `SEED_C = 20260927`.
- Báo: `mean(gross)` từng rổ + **CI khối 72 h** (cùng tham số CI như §3), **hiệu ghép cặp theo tick**
  (R1−R3, R2−R3, R1−R2, R1−R4); thêm **thành phần status** (% `TRAIL` / `TS168`, mean gross từng nhóm)
  để quy giá trị về **luật thoát** hay **chọn coin**.
- **Cổng tự-kiểm:** R2 phải ≈ R3 (cùng là mẫu ngẫu nhiên của cùng phân bố) — lệch lớn ⇒ nghi harness.
- **Đọc:** R3 ≈ +1,27 % mà R2 ≈ R3 ⇒ **giá trị đến từ LUẬT THOÁT (+ giai đoạn thị trường), KHÔNG từ S1**;
  R3 ≈ 0 ⇒ giá trị đến từ **chọn coin S1**.

## 5. SẢN PHẨM + CHI PHÍ

`docs/prereg/PREREG_AUDIT_PNL.md` (file này) · `docs/result/RESULT_AUDIT_PNL.md` ·
`research/analysis/audit_pnl_lib.py` · `research/analysis/audit_pnl_label.py` ·
`research/analysis/audit_pnl_cost.py` · `research/analysis/audit_pnl_ro.py` · JSON thô trong `/tmp/auditpnl/`.
Ước tính: ~3.100 lượt đọc ngày-bin (~1,05 s/ngày/lõi, 4 lõi) + ~61k sim ⇒ **~20–30 phút**, RAM thấp
(chỉ giữ bars của coin cần). `free -g` trước mỗi bước nặng; nếu vượt RAM ⇒ đẩy sang Kaggle CPU (không tự ý).
**Không push.**
