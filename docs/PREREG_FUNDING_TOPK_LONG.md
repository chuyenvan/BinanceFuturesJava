# PREREG_FUNDING_TOPK_LONG — LUONG DOI XUNG: **LONG top-K coin FUNDING CAO**

Chốt: **2026-09-23, TRƯỚC khi chạy bất kỳ phép đo nào.** File này commit **TRƯỚC** mọi commit
script/kết quả (đúng `docs/AGENT_RUNBOOK.md` luật 2; sai thứ tự commit ⇒ kết quả **VOID**).
Sau khi chạy **KHÔNG sửa thiết kế** (mốc rebalance, định nghĩa tín hiệu causal, decile, cửa sổ giữ,
chi phí, cổng thống kê, số rep, seed, xử lý cadence/delist, định nghĩa turnover/MAE, cách neo MOM15).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/RESULT_FUNDING_TOPK_LONG.md`).

> **AMEND 2026-09-23 (TRƯỚC mọi phép đo — chưa có grid/stats nào tồn tại):** chỉ **làm rõ nguồn dữ
> liệu** cho universe V3 (§4): (i) dùng file `printDone.csv` của **`X1_GS_T170_2021_SEL_DROP_TOP8`**
> (biến thể đúng `SELECTOR_RANK_TOPK=8` của cùng run T170) thay vì `X1_GS_T170_2021` trần;
> (ii) map tên `sym` (không hậu tố) → `sym + "USDT"`; (iii) nới điều kiện V3 "đứng ngoài" sang
> **< 3 tên**. **KHÔNG** đổi bất kỳ định nghĩa nào khác (biến thể, chi phí, cổng, seed). Đã kiểm
> **365/365** tên khớp TRƯỚC khi đo.

---

## 0. Vì sao đây là phép đo MỚI (và vì sao tiên lượng là NO-GO)

Ba vòng trước đã đo **hướng funding** và **hướng short**:

| Vòng | Luật | Kết quả |
|---|---|---|
| `RESULT_FUNDING_TOPK_ROTATE.md` (commit `55b8280`) | **LONG top-K funding NHỎ NHẤT** | net **−0,146 … −0,222 %/chu kỳ 8h**, CI72h×1,21 **ngoài 0 về ÂM** ⇒ THUA |
| `RESULT_FUNDING_FACTOR.md` | D1 (funding thấp nhất), HOLD 24h | net **−0,1913%**, CI chứa 0 ⇒ THUA |
| `RESULT_SHORT_CARRY.md` (commit `edd1e70`) | **SHORT top-decile funding CAO** | net **−0,1402** (ALL) / **−0,0935** (DEV) %/chu kỳ; chân giá short ≈ **−0,0054%** (≈0 ⇒ coin funding cao **KHÔNG** giảm giá!) ⇒ THUA |

Chủ dự án chốt: *"không short được coin funding cao thì **BUY** nó xem thử"*. Đó là **phép đo này**:
**LONG top-decile funding CAO** = momentum thuần **được xác nhận bằng funding** (dòng tiền trả phí
để giữ long = cầu thật, không phải nhiễu).

**CẢNH BÁO DẤU (điểm chết khác hẳn 2 vòng trước):** theo quy ước đã kiểm chứng 2 tầng
(`docs/RESULT_FUNDING_SIGN.md`): **`rate > 0` ⇒ LONG TRẢ, SHORT THU**. Long coin funding cao ⇒
**MỖI CHU KỲ PHẢI TRẢ `f_cyc`** — đây là **CHI PHÍ BẮT BUỘC**, không được bỏ qua hay cộng dương.
Mức phải trả đo được ở vòng short: chân long của top-decile **TRẢ −0,0251 %/chu kỳ** (đối xứng với
chân short THU). Tức long phải vượt **fee+slip (~0,16%/chu kỳ) + funding (~0,025%) ≈ 0,185%/chu kỳ**
mới hoà vốn — trong khi chân giá long của chính nhóm coin này (suy ra từ vòng short, dấu đối xứng)
chỉ **≈ +0,0054 %/chu kỳ**.

**Tiên lượng ghi TRƯỚC (không sửa sau khi thấy số):** nhiều khả năng **NO-GO** — momentum của coin
funding cao **có thật** (đó là lý do short thua) nhưng **cỡ quá nhỏ** so với (i) phí quay vòng và
(ii) **funding phải TRẢ**; thêm nữa long là chân **mua đuôi** (rủi ro mua đỉnh squeeze, MAE lớn).
Điều kiện để tiên lượng này bị chứng minh sai = §7 (một biến thể GO đủ 5 cổng).

---

## 1. Ràng buộc (bắt buộc) — tuân thủ ghi rõ

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java trên Oracle (đang có job shadow).
- **THUẦN PYTHON**, 0-sim: chỉ **ĐỌC** Aerospike `test.funding_data` + `raw/<sym>.f32`.
- **KHÔNG touch engine/Java**: **KHÔNG** build/sim Java, **KHÔNG** đề xuất tích hợp ở kết quả.
- **KHÔNG push.** Pre-reg commit TRƯỚC; sau khi chạy không sửa thiết kế.
- **Dữ liệu ≤ 2025-12-31** (giá `raw/*.f32` chỉ tới 2025-12-31 16:59 UTC). **DEV 2022-01…2025-12 là
  CHÍNH**; 2021 phụ (pre-DEV). **2026**: giá không có ⇒ **không đo được**, và **không dùng** funding
  2026 (giữ holdout tinh khiết, không tune).
- Trung gian **ngoài repo**: `/home/ubuntu/claudedata/funding_topk_long/`.

## 2. BƯỚC 0 — nguồn dữ liệu + QUY ƯỚC DẤU (chốt cứng)

| Mục | Giá trị |
|---|---|
| Funding | Aerospike `test.funding_data`, bin `f_data` = **Snappy(JSON `{ts_ms: rate}`)**; tunnel `127.0.0.1:3222` (**chỉ đọc**) |
| Giá 1m | `raw/<sym>.f32` = `int32 epoch_minute` + `float32 O/H/L/C/V`, UTC; **627** file; ts ∈ [2021-01-01, **2025-12-31 16:59 UTC**] |
| Universe | 627 = (có `raw/*.f32`) ∩ (có record funding) |
| Cadence | hỗn hợp 4h/8h ⇒ 1 "chu kỳ" 8h có thể chứa **2 kỳ settle** với coin 4h (tính đủ theo event) |
| **QUY ƯỚC DẤU (KHOÁ)** | **`rate > 0` ⇒ LONG TRẢ, SHORT THU.** `f_cyc = 100 × Σ rate` trên `(t_entry, t_exit]` ⇒ **long: funding = `−f_cyc`** (chi phí khi `f_cyc>0`) |

## 3. Mốc + tín hiệu (KHOÁ, causal)

- `BASE` = phút epoch `2021-01-01T00:00Z` = **26 824 320**; `NMIN` = 2 629 440. `BASE % 480 == 0`
  ⇒ mốc 8h UTC (`00/08/16`) là `r ≡ 0 (mod 480)`.
- **Vào**: `close(r)`. **Ra**: `close(r + 480)`. Mốc nhận nếu `r + 480 ≤ NMIN − 1`; nếu không ⇒
  **edge-censored, LOẠI**. **Delist**: symbol hết nến trước `r+480` ⇒ ra tại **nến cuối `> r`**
  (nến cuối `≤ r` ⇒ loại khỏi mốc), cờ `delist=1`, **GIỮ** (không lọc survivorship — như 2 vòng trước).
- **Tín hiệu xếp hạng (causal):** `f_sig(r)` = rate của **event cuối cùng có `ts_ms ≤ t_entry`**
  (rate **ĐÃ settle**) — **KHÔNG** dùng rate tương lai. Cùng định nghĩa `f_entry` các vòng trước.
- **Funding trong chu kỳ:** `f_cyc(r,s) = 100 × Σ rate` trên event có `t_entry < ts ≤ t_exit`.
- **Ret 24h (cho V2):** `ret24(r) = close(r)/close(r−1440) − 1` (thiếu nến ⇒ không đủ điều kiện V2).

## 4. Universe đủ điều kiện (KHOÁ)

Tại mốc `r`, symbol đủ điều kiện nếu: (a) có nến tại `r` **và** tại `r+480` (hoặc nhánh delist §3);
(b) có `f_sig(r)` và `f_cyc(r)`; (c) `close(r) > 0`. Mốc chỉ dùng nếu **`n_elig ≥ 50`**.
Decile: `K = max(1, round(n_elig / 10))` (khớp 2 vòng trước ⇒ so sánh được).

**Universe V3 (hệ thống) — KHOÁ:** tại mốc `r`, symbol thuộc **universe hệ thống** nếu nó có **ít nhất
1 lệnh đã mở** trong run `devrun/X1_GS_T170_2021_SEL_DROP_TOP8/storage/printDone.csv` (biến thể
**selector top-K = 8** của chính run T170, tức đúng run có `SELECTOR_RANK_TOPK=8`) với `start`
(đọc là **UTC**, hướng bảo thủ: nếu file là giờ GMT+7 thì mốc đọc ra **muộn hơn** thực ⇒ **không**
look-ahead) **≤ thời điểm mốc `r`**. Map tên: `sym` trong printDone **không có hậu tố** `USDT` ⇒
khớp `sym` **hoặc** `sym + "USDT"` với `raw/<tên>.f32` (đã kiểm: **365/365** tên khớp TRƯỚC khi đo).
Tập này **mở rộng dần** (causal, không dùng tương lai). Ghi rõ: đây là **proxy** cho universe mà
selector/TOPK (`SELECTOR_RANK_TOPK=8`) thực sự giao dịch, không phải danh sách cấu hình.

## 5. Ba biến thể + 4 đối chứng (KHOÁ — tối đa 3 biến thể)

**V1 — PURE.** Long **top-decile `f_sig`** (rate **cao nhất**), trọng số **bằng nhau** (`1/K` mỗi tên),
giữ **1 chu kỳ 8h**, rebalance mốc kế. Không lọc gì thêm.

**V2 — LOC MOMENTUM.** Chỉ long tên thoả **CẢ HAI**: (i) `f_sig > p90(f_sig)` cross-sectional tại mốc;
(ii) `ret24 > 0` (giá **đang tăng** — tránh "bắt đỉnh đang gãy"). EW trên **số tên thoả**;
**0 tên thoả ⇒ đứng ngoài (flat, pnl = 0, cost = 0)**.

**V3 — TRONG UNIVERSE HỆ THỐNG.** Y hệt V1 nhưng **chỉ** trên symbol thuộc universe V3 (§4) tại mốc đó
(nếu < 3 tên đủ điều kiện trong universe hệ thống ⇒ **đứng ngoài**, cờ đếm riêng).

**Đối chứng:** (a) **U — long toàn universe đủ điều kiện EW** (baseline "funding trung bình");
(b) **neo MOM15** (M-LEVEL k=1, HOLD 24h, từ `cache2.npz` của các vòng trước — **phải tái lập đúng**
+1,6690%/lệnh DEV @0,10%); (c) **L2** = long **bottom-decile** (funding **thấp nhất**) — tái lập hướng
long-side đã THUA; (d) **S1** = **short top-decile** — tái lập `RESULT_SHORT_CARRY` V1 (DEV **−0,0935%**).

## 6. Chi phí + kế toán (KHOÁ)

Đơn vị: **%/notional/chu kỳ**. Mọi con số báo **gross (giá + funding)** và **net (trừ chi phí)**.

- **Fee:** taker **0,05%/chân** (chính); maker **0,02%/chân** (báo cáo).
- **Slip (mỗi chân):** proxy `0,5 × (h − l) / c` tại nến của chân đó (**chính**); báo thêm phẳng
  **0,140%/chân** và **1 bp (0,01%)/chân**; báo thêm slip nến-ra.
- **Turnover (KHOÁ):** `τ_t = Σ_i |w_{t,i} − w_{t−1,i}|` (flat ⇒ τ=1; đổi hết sổ ⇒ τ=2);
  **turnover 1 vế = τ_t / 2**. V2 flat ⇒ τ = 0.
- **Cost_t = τ_t × (fee_chân + slip_chân)**. Bắt buộc báo **turnover, cost drag, gross vs net**.
- **Biến thể bảo thủ:** round-trip toàn sổ mỗi chu kỳ (`τ = 2`) — cận trên chi phí.
- **FUNDING PHẢI TRẢ:** long ⇒ `funding = −f_cyc` (**bắt buộc**, `f_cyc>0` ⇒ âm). Báo riêng cột
  "funding TRA" và **% chu kỳ `f_cyc>0`**.

## 7. Cổng thống kê + kết luận (KHOÁ)

- **CI block-72h ×1,21**: block = `floor((BASE + r) / 4320)`; **2000 rep**, **seed 20260905**,
  phân vị 2,5–97,5%, nửa rộng × **1,21**.
- **Null (bắt buộc):** **long N coin NGẪU NHIÊN** cùng số lượng với decile thật (N = K tại mốc đó,
  cùng universe đủ điều kiện), EW, **300 rep**, seed 20260905 ⇒ **p-value 1 vế** `p(null ≥ thật)`.
- **MDE80**: bootstrap lồng (outer 2000 / inner 200), lưới `{0,01; 0,02; 0,05; 0,10; 0,20; 0,50} %/chu kỳ`.
- **Khác:** %chu kỳ dương, net theo **năm**, net **DEV** (chính) vs **ALL** (phụ).
- **Rủi ro long (bắt buộc):** phân bố **max adverse excursion (MAE) = drawdown** của mỗi vị thế long =
  `min_{t ∈ (r, r+480]} (low_t / close_r − 1)` (nến 1m); báo p50/p90/p99/max, tỉ lệ vị thế có
  drawdown **> 20%**, và MFE (max high).
- **Đối chiếu MOM15 (KHOÁ):** (i) neo phải tái lập **đúng** (+1,6690% DEV @0,10%, N=7128, N_blk=301,
  total_rows 619 073 711) ⇒ nếu lệch ⇒ **VOID**; (ii) **overlap thời gian**: định nghĩa
  `MOM15-active(r)` = có **ít nhất 1 phút MOM15 fire** (`rd15 < −0,028`, từ `fire8` của `cache2.npz`)
  trong `[r − 1440, r]`; báo **% mốc active**, và **net/chu kỳ trên tập active vs quiet**;
  (iii) **kết luận trùng lặp**: nếu net dương chỉ đến từ tập MOM15-active (quiet ≈ 0/âm) **hoặc**
  cỡ net ≈ MOM15 ⇒ **TRÙNG LẶP (redundant)**.
- **GO chỉ khi ĐỦ TẤT CẢ:** (1) **net > 0 sau TẤT CẢ chi phí** (kể cả **funding TRẢ**) ở chi phí chính;
  (2) **CI72h×1,21 ngoài 0**; (3) **≥60% số chu kỳ dương**; (4) **bền vững qua các biến thể**;
  (5) **KHÔNG trùng MOM15** (§7 đối chiếu) và **không âm ở biến thể chi phí bảo thủ**.
  **Một biến thể dương còn biến thể khác không ⇒ UNCONFIRMED (post-hoc)**, KHÔNG áp dụng.
- **NULL ⇒ nói rõ NULL.** Không tô hồng, **KHÔNG đề xuất tích hợp** (engine cũng chưa có đường long
  funding đặc thù — đây là đo counterfactual offline).

## 8. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/PREREG_FUNDING_TOPK_LONG.md` | file này (chốt trước, commit TRƯỚC khi đo) |
| `docs/RESULT_FUNDING_TOPK_LONG.md` | kết quả + kết luận GO/NO-GO |
| `research/analysis/funding_topk_long.py` | script thuần Python (đọc Aerospike + `raw/*.f32` + `cache2.npz`) |
| `/home/ubuntu/claudedata/funding_topk_long/` | trung gian **ngoài repo** (resume được): `grid.npz`, `report.txt`, `summary.json` |

## 9. Điểm mù biết trước (ghi trước để không hậu biện)

(i) Không có **fill thật** ⇒ chi phí là **mô hình**. (ii) Funding 4h/8h hỗn hợp — đã tính đủ event.
(iii) `f_sig` là rate **đã settle** (trễ ≤ 1 chu kỳ): causal đúng, **không** phải "rate kỳ tới".
(iv) Không mô hình **margin/liquidation**; MAE chỉ là **cảnh báo rủi ro**. (v) Decile phụ thuộc
#symbol theo thời gian. (vi) **Universe V3 là proxy** từ `printDone.csv` (không phải list cấu hình),
và symbol vào universe **sau** lệnh đầu tiên ⇒ muộn hơn thực tế (bảo thủ, không look-ahead nhưng
**loại** các coin chỉ được giao dịch muộn). (vii) Neo MOM15 dùng `cache2.npz` do **vòng trước** sinh
(cùng nguồn `kline_1m_opt`) — tái lập ở đây chỉ kiểm **chuỗi + bộ đo**, không phải sinh lại từ đầu.
