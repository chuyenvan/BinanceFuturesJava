# PREREG_TAIL_ROBUST_RULERS — BỘ THƯỚC "KHÔNG-ĐUÔI" + LÀM MỊN LẠI THƯỚC CI

Chốt **TRƯỚC khi đo** (2026-09-26 23:04 GMT+7). Thuần **Python offline trên Oracle**; **KHÔNG** train,
**KHÔNG** Java/sim, **KHÔNG** chạm production/242/ONNX/LIVE, **KHÔNG** push git. DEV only:
mọi dữ liệu **`<= 2025-12-31`**, **không đọc 2026** (holdout nguyên vẹn).
Code: `research/analysis/tail_robust_rulers.py`. Kết quả: `docs/result/RESULT_TAIL_ROBUST_RULERS.md`
(+ `docs/result/tail_robust_rulers.json`). Sao lưu số thô: `/tmp/trr/`.

## 0. Động cơ (số đã đo — KHÔNG diễn giải lại)

`docs/result/RESULT_FRAGILITY_N.md` (3 nền T170/T100/GD92): `share top-1% leg` = **25,9% / 40,9% / 37,8%**;
`share top-5%` = **56,7% / 96,8% / 85,0%**; `share top-10%` = **76,8% / 136,1% / 118,4%** (>100 ⇒ **bỏ
top-10% thì PnL ÂM**). Các vòng chấm gần nhất (`RESULT_PNL_RULER` `acb88bd`, `RESULT_MONEY_RANKER`,
`RESULT_OFI_MONEY`) đều dùng **thước TIỀN mean-based** (`ic`, `pacc`, `dec_mono`, `glift8`, `netm8`)
⇒ **1–2 leg đuôi quyết định kết luận**. Vòng này: đo lại bằng **họ thước bất trị đuôi**, kèm **CI làm mịn**.

## 1. CÂU HỎI CHỐT TRƯỚC (trả lời sau khi đo, không đổi luật)

**(1)** Sau khi **bỏ đuôi**, có thước nào cho **alpha NGOÀI CI** không?
**(2)** Bao nhiêu % "alpha" cũ **đến từ đuôi** (đo bằng thước tập trung + tail-free sum)?
**(3)** Thước nào **nên dùng** (2–3 chuẩn cho các vòng sau, kèm CI đã làm mịn) · thước nào **nên bỏ**?
**(4)** **Bảng tổng hợp** thước × CI × độ rộng để owner chốt bộ chuẩn.

## 2. NGUỒN DỮ LIỆU (dùng lại, KHÔNG build lại)

- **Thước chính `P32`**: `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet`
  (**309.024** dòng = **9.657 tick × 32**, `sha256 1d42b7f6…`) — `y = gross` của **luật thoát**
  (nhãn (b) của `RESULT_PNL_RULER`). **KHÔNG** dùng cột `net` (cột đó = `gross − 0,008` = **một** mức phí).
- **Đường phụ B2** (nếu rẻ): pool mở rộng `/home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext.parquet`
  (166.080 dòng mới; pool_ext = **475.104** dòng) — **chỉ** dùng để kiểm độ nhạy, **không** dùng cho luật.
- **Điểm các đối tượng** (đọc artifact ĐÃ CÓ, không train lại):
  `45deploy` = `predwf_G015x26/predict_wf_*.bin` (slot `p`) · `A44`/`A45` = `ruler_bins/g015p2-arm44-gpu/stage2/<arm>`
  · `V1`/`V5` = `ruler_bins/g015p2-stage2-featvar-gpu/stage2/<arm>` · `MRA4`/`MRB8`/`MRB32` = `/tmp/mrbins/<arm>`
  (**thiếu fold 20220101** ở MRB8/MRB32 — khai báo trước, ghép cặp theo tick chung) ·
  `S1` = cột `E` trong `label_b_pnl.parquet` (**`score = −E`**, tăng dần theo `rank`).
- **OFI** `candidate`/`baseline_fresh`/`noise_ofi_check`: dùng **điểm seed 42 v2** đang có trên đĩa
  `/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_*.parquet` (phủ **100 %** cặp của `P32`, đã kiểm).
  **KHAI BÁO TRƯỚC (lệch so với vòng trước):** ensemble 43/44/45 **không** lưu per-row pred (chỉ có
  per-tick `ms_diffs` + `ofi_result*.json`) ⇒ seed 42 là **proxy** đã ghi rõ; mọi kết luận OFI ở đây
  **chỉ** dùng để **kiểm thước**, **không** thay kết luận của `RESULT_OFI_MONEY`.
- **Không** chạm `242`, `242` ledger, ONNX, LIVE.

## 3. ĐỐI TƯỢNG CHẤM (10) VÀ ĐỐI CHỨNG BẮT BUỘC (2)

- **Đối tượng:** `45deploy` · `A44` · `A45` · `MRA4` · `MRB8` · `MRB32` · `S1` · OFI `candidate` ·
  OFI `baseline_fresh` · OFI `noise_ofi_check`.
- **Đối chứng bắt buộc #1 (retrain):** `A45 − 45deploy` (cùng bộ feature, retrain ⇒ Δ = nhiễu train).
- **Đối chứng bắt buộc #2 (noise):** `V5 − V1` (2 biến thể nhiễu của cùng bộ feature ⇒ Δ ≈ 0).
- Đối chứng phụ: `45deploy` (nền deploy) và `V1` (nền nhiễu) khi cần so từng đối tượng.

## 4. CÁCH CHỌN VÀ ĐƠN VỊ (chốt trước)

- Mỗi tick: xếp hạng **các coin CỦA `P32`** theo điểm từng đối tượng → lấy **`top-K`**, **`K = 8`**
  (K vận hành, bằng mọi vòng trước). Chỉ số tính trên **tập leg được chọn** (danh mục vận hành).
- **`net = gross − f`**; **`f = 0,006`/vòng là mức QUYẾT ĐỊNH** (owner 26/09); báo thêm `0`, `0,004`, `0,008`.
- **Trần gross 70 %** (như `RESULT_CAP70_FEE06.md`): áp **3 cách** (`A_mean` = 70/`gross_TB`;
  `B95` = 70/`gross_p95`; `Bmax` = 70/`gross_max`) trên **net/tick** theo đúng công thức
  `net_tick_sized = 100·0,02·s·net_tick`. **LƯU Ý CHỐT TRƯỚC:** trần là **hệ số nhân HẰNG theo `K`**
  ⇒ nó **không đổi thứ hạng bất trị-đuôi** của các leg; vì vậy trần **chỉ** báo ở **bảng TIỀN**,
  **không** đưa vào họ thước chống đuôi (ghi rõ để không over-claim).
- **Đơn vị báo cáo:** mọi thước theo **`net`/leg** (phân số), **trừ** `net_tick`/`sized_net_tick`
  (phân số/tick) — ghi nhãn từng dòng.

## 5. HỌ THƯỚC "KHÔNG-ĐUÔI" — **CHỐT 17 THƯỚC** (k_ruler = 17)

Mọi ngưỡng winsor/trim/drop-top đều **tính trên CHÍNH mẫu DEV đang chấm** (thước **mô tả**, không
phải luật giao dịch ⇒ **khai báo trước** là dùng pooled quantile; **không** dùng để suy ra chiến lược).

| # | tên | định nghĩa 1 dòng (trên leg/net của tập top-8) |
|---|---|---|
| R1 | `wmean_p1p99` | trung bình `net` sau **winsorise `[p1,p99]`** |
| R2 | `wmean_p5p95` | trung bình `net` sau winsorise `[p5,p95]` |
| R3 | `tmean_1` | **trimmed mean** bỏ **1 %** mỗi đuôi |
| R4 | `tmean_5` | trimmed mean bỏ **5 %** mỗi đuôi |
| R5 | `median` | **trung vị** `net`/leg |
| R6 | `sign_frac` | **tỷ lệ leg `net > 0`** (kèm **sign test** = CI của tỷ lệ này) |
| R7 | `tf_1` | **tail-free**: trung bình `net` sau **bỏ top-1 %** leg tốt nhất |
| R8 | `tf_5` | tail-free sau **bỏ top-5 %** |
| R9 | `tf_10` | tail-free sau **bỏ top-10 %** |
| R10 | `conc_1` | **tỷ lệ PnL** đến từ **top-1 %** leg (Σ`net` nhóm đó / Σ`net`) |
| R11 | `conc_5` | tỷ lệ PnL đến từ **top-5 %** |
| R12 | `hhi_gain` | **Herfindahl trên đóng góp LÃI**: `Σ(g_i/G)²`, `g_i = max(net_i,0)`, `G = Σg_i` |
| R13 | `ic_wmean` | **rank-IC per tick** giữa điểm và **`net` đã winsorise `[p1,p99]`**, lấy **mean** |
| R14 | `ic_med` | **median theo tick** của rank-IC per tick ở R13 (KHÔNG lấy mean) |
| R15 | `loss_mean` | độ lớn trung bình của leg **lỗ** (`|net|` khi `net<0`) — báo **dấu âm** |
| R16 | `wl_ratio` | **mean win / mean loss** (độ lớn) |
| R17 | `max_loss` | **lỗ lớn nhất**: mean theo tick của `min(net)` trong tick |

**Bổ sung (không thuộc họ 17, chỉ báo cáo — KHÔNG dùng cho luật):** `netm8` = `net`/tick của top-8,
`sized_netm8` (trần 70 % × 3 cách), `p25`/`p75` của `net`/leg (kèm `median` ở R5).

## 6. LÀM MỊN LẠI THƯỚC CI (ma trận cấu hình)

- **Bắt buộc cho MỌI thước:** block **24 h / 72 h / 168 h** · `NREP` **2000 / 5000** · seed
  **20260905** (chính) + **20260907** + **20260911** (2 seed phụ). ⇒ **18 cấu hình**.
- **Bắt buộc cho thước CẦN (cần gather leg):** `median`, `p25/p75` — **6 cấu hình**:
  `(72,2000,905)` chính · `(24,2000,905)` · `(168,2000,905)` · `(72,5000,905)` · `(72,2000,907)` ·
  `(72,2000,911)`. **Khai báo trước** lý do: đây là 2 thước **phi tuyến theo leg**, chi phí gather
  leg gấp ~30× thước còn lại; co hẹp **theo cấu hình, KHÔNG co hẹp theo luật**.
- **Bootstrap theo KHỐI tick** (giống `stage2_score.block_boot_mean`): mỗi block = `block_h` giờ,
  resample **block** (có hoàn lại), dựng lại **tập leg** của tick được chọn ⇒ **paired** (mọi đối
  tượng dùng **cùng một** ma trận block-index/seed/cấu hình).
- **LUẬT (chốt trước):** *ngoài CI* = **ngoài raw95 (`k=1`) VÀ ngoài `inflate(k_ruler)=inflate(17)=2,3805`**.
  `inflate(k)` **import** từ `c3_rates.inflate` (không hardcode). Báo thêm `raw95`, `inflate(k_obj=10)=2,1460`.
- **Độ rộng:** mọi bảng báo **`độ rộng CI / |điểm ước lượng|`** cho từng ô ⇒ ô nào **thực sự phân giải được**
  (tỷ số nhỏ) vs ô nào là **nhiễu** (tỷ số ≥ 1 = CI rộng hơn cả điểm).

## 7. LUẬT QUYẾT ĐỊNH (chốt TRƯỚC, không sửa sau khi thấy số)

**D1 — "alpha không-đuôi" của một ĐỐI TƯỢNG `X`:** CHỈ khi Δ so **CẢ HAI** nền (`X − 45deploy` và
`X − V1`) **cùng dấu**, đều **ngoài CI** (theo §6), trên **CÙNG ≥ 2 thước** của họ 17.
**D2 — hiệu ứng retrain** đánh giá bằng `A45 − 45deploy`; **hiệu ứng nhiễu** bằng `V5 − V1`.
Hai Δ này được coi là **đối chứng hiệu chuẩn của THƯỚC**: nếu một **thước** cho **cả hai** đối chứng
này **ngoài CI** ⇒ thước **không phân giải được** (bắt nhiễu), **bị loại khỏi bộ chuẩn** (dù có thể
"có tín hiệu" ở đối tượng khác).
**D3 — xếp hạng độ ưu tiên thước (chốt trước):** `median` > `tf_5` > `wmean_p1p99` > `sign_frac` >
`conc_5` > `ic_med` > `loss_mean` > (các thước còn lại). Ưu tiên = **bền với đuôi trước**, rồi tới
**kinh tế dễ hiểu**, rồi tới **ổn định CI** (độ rộng tương đối nhỏ).
**D4 — kết luận dứt khoát:** nếu **0** đối tượng đạt D1 ⇒ phát biểu **"alpha = 0 khi bỏ đuôi"**.
Nếu **1–2** đối tượng đạt D1 ⇒ phát biểu **"có tín hiệu hẹp, cần vòng xác nhận"** (KHÔNG gọi là alpha).
Nếu **≥3** ⇒ phát biểu **"có alpha không-đuôi"** (kèm bảng CI đã làm mịn).

## 8. KIỂM HỢP LỆ (bắt buộc, chốt trước)

- (a) Điểm phủ **100 %** cặp `P32` cho **mọi** đối tượng (thiếu ⇒ **báo**, không bịa; MRB8/MRB32 hụt
  fold `20220101` ⇒ ghép cặp theo tick chung, ghi rõ số tick).
- (b) `S1` (dùng `−E`) phải tái lập **đúng** thứ tự `rank` của pool ⇒ kiểm bằng tỷ lệ tăng khớp = 100 %.
- (c) Tổng tổng: `Σnet` của toàn pool ở `f` phải bằng `Σgross − f·n` (kiểm số học, lệch 0).
- (d) Ở `k = 1` (raw) **không** ô nào được gọi "ngoài CI" nếu raw95 chứa 0.

## 9. RÀNG BUỘC CHI PHÍ / ĐĨA / OUTPUT

`df -h /` ~93 % ⇒ chỉ ghi file **NHỎ** (`docs/result/*.json` vài trăm KB, `/tmp/trr/` xoá sau khi xong).
Output tool **THẬT NHỎ** (log ra file). Không train, không sim, không push.
