# PREREG_SHORT_CARRY — LUONG MOI: SHORT-SIDE FUNDING HARVEST (carry)

Chốt: **2026-09-23, TRƯỚC khi chạy bất kỳ phép đo nào.** File này commit **TRƯỚC** mọi commit
script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự commit ⇒ kết quả **VOID**).
Sau khi chạy **KHÔNG sửa thiết kế** (mốc rebalance, định nghĩa tín hiệu causal, decile, cửa sổ giữ,
chi phí, cổng thống kê, số rep, seed, cách xử lý cadence/delist, định nghĩa turnover/MAE/squeeze).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_CARRY.md`).

---

## 0. Vì sao đây là **luồng MỚI** (cấu trúc khác), không phải tối ưu thêm

Vòng long-side đã đo và **THUA**:

- `docs/result/RESULT_FUNDING_TOPK_ROTATE.md` (commit `55b8280`/kết quả): **LONG top-K funding nhỏ nhất**
  net **−0,146 … −0,222 %/chu kỳ 8h**, CI72h×1,21 **ngoài 0 về phía ÂM**, 45,8–48,6% chu kỳ dương.
  Cơ chế chết: (i) chân giá âm (nhóm funding nhỏ nhất = nhóm **đang bị bán mạnh nhất**),
  (ii) chi phí quay vòng ăn hết.
- `docs/result/RESULT_FUNDING_FACTOR.md`: D1 (funding thấp nhất) net 24h **−0,1913%**, CI chứa 0.

**Nhưng phép đo này chỉ nói về phía LONG.** `docs/result/RESULT_FUNDING_SIGN.md` §0(5) chốt ở tầng
**unconditional**: **80,6% số kỳ settle (DEV) có `rate > 0`**, và theo Binance thật
**`rate > 0` ⇒ long TRẢ, short THU** (quy ước đã kiểm chứng 2 tầng độc lập, §1 của doc đó).
⇒ **Bên SHORT là bên THU khi funding dương** — tức **80,6% số kỳ**. Đó là **cấu trúc carry**,
không phải "long nhưng thông minh hơn".

**Vì sao vẫn có thể vẫn NO-GO (tiên lượng ghi trước):** funding dương trung vị chỉ **+0,5 bp/kỳ**
(≈ **+0,0015%/ngày** với 3 kỳ/ngày) trong khi **fee taker 2 chiều = 0,10%** và slip đo được ở vòng
trước là **0,13–0,33%/chiều** ⇒ **thu funding nhỏ hơn chi phí 1–2 bậc độ lớn nếu phải quay vòng**.
Điểm **dương** của short: (a) short **nhận** funding, (b) short là chân **đối xứng dấu** với chân
"bán-mạnh" đã giết long-side — cùng một nhóm coin nhưng **cược ngược chiều giá**. Cả hai đều phải đo,
không được suy đoán.

**Tiên lượng (không sửa sau khi thấy số):** nhiều khả năng **NO-GO** ở dạng "thu funding thật nhưng
không thắng nổi chi phí + rủi ro squeeze". Điều kiện tôi bị chứng minh sai = §7.

---

## 1. Ràng buộc (bắt buộc) — tuân thủ ghi rõ

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java trên Oracle (đang có job shadow).
- **THUẦN PYTHON**, 0-sim: chỉ **ĐỌC** Aerospike `test.funding_data` + `raw/<sym>.f32`.
- **KHÔNG touch engine/Java**: engine hiện **không có đường SELL** (`ENABLE_SHORT` đã gỡ,
  `createOrderSELL` không còn — `docs/design/DESIGN_HEDGED_BOOK.md` §1a) ⇒ vòng này **CHỈ đo offline
  (counterfactual)**. **KHÔNG** build/sim Java, **KHÔNG** đề xuất tích hợp ở kết quả.
- **KHÔNG push.** Pre-reg commit TRƯỚC; sau khi chạy không sửa thiết kế.
- **Dữ liệu ≤ 2025-12-31** (giá `raw/*.f32` chỉ có tới 2025-12-31 16:59 UTC). DEV **2022-01…2025-12
  là CHÍNH**; **2021 là phụ (pre-DEV)**. **2026**: giá không có ⇒ **không đo được**; funding 2026
  **không dùng** (giữ holdout tinh khiết, không tune gì trên nó).

## 2. BƯỚC 0 — nguồn dữ liệu + QUY ƯỚC DẤU (chốt cứng)

| Mục | Giá trị |
|---|---|
| Funding | Aerospike `test.funding_data`, bin `f_data` = **Snappy(JSON `{ts_ms: rate}`)**; tunnel `127.0.0.1:3222` (**chỉ đọc**) |
| Coverage funding (đo lúc lập pre-reg) | **831** symbol / **2 394 587** cặp; ts_max **2026-08-05 12:00 UTC** |
| Giá 1m | `raw/<sym>.f32` = 1 nến/phút: `int32 epoch_minute` + `float32 O/H/L/C/V`, UTC; **627** file; **619 082 489** dòng; ts ∈ [2021-01-01, **2025-12-31 16:59 UTC**] |
| Universe | 627 = (có `raw/*.f32`) ∩ (có record funding); lọc rác `ts < 2021-01-01` (`GAIBUSDT`,`GRAMUSDT`,`STPTUSDT`) |
| Cadence | hỗn hợp 4h/8h (vòng trước: 422×4h, 202×8h) ⇒ giữ 1 "chu kỳ" 8h có thể chứa **2 kỳ settle** với coin 4h |
| **QUY ƯỚC DẤU (KHOÁ)** | **`rate > 0` ⇒ LONG TRẢ, SHORT THU.** `f_pp = 100 × Σ rate` (%/notional) ⇒ `>0` = **long TRẢ / short THU**. Đã kiểm chứng 2 tầng độc lập ở `docs/result/RESULT_FUNDING_SIGN.md` (nguồn Binance nguyên bản, không đảo dấu). |

## 3. Mốc + tín hiệu (KHOÁ, causal)

- `BASE` = phút epoch `2021-01-01T00:00Z` = **26 824 320**; `NMIN` = 2 629 440. `BASE % 480 == 0`
  ⇒ mốc rebalance 8h UTC (`00/08/16`) là `r ≡ 0 (mod 480)` (r = phút tương đối).
- **Vào**: `close(r)`. **Ra**: `close(r + 480)`. Mốc nhận nếu `r + 480 ≤ NMIN − 1`; nếu không ⇒
  **edge-censored, LOẠI** (không cắt ngắn chu kỳ).
- **Delist**: nếu symbol hết nến trước `r+480` ⇒ ra tại **nến cuối cùng `> r`** (nếu nến cuối `≤ r`
  ⇒ loại symbol đó khỏi mốc), cờ `short_delist=1`, **GIỮ** (không lọc survivorship — như vòng trước).
- **Tín hiệu xếp hạng (causal):** `f_sig(r)` = **rate của event cuối cùng có `ts_ms ≤ t_entry`**
  (rate **ĐÃ settle**, biết chắc tại mốc) — **KHÔNG** dùng rate tương lai. Cùng định nghĩa `f_entry`
  của `funding_factor.py` để so sánh được với vòng trước.
- **Funding thu trong chu kỳ:** `f_cyc(r,s) = 100 × Σ rate` trên các event có `t_entry < ts ≤ t_exit`
  (nửa mở, đúng như các vòng trước).
- **Ret 24h (cho V2):** `ret24(r) = close(r)/close(r−1440) − 1` (cần nến tại `r−1440`, nếu thiếu ⇒
  symbol **không** đủ điều kiện V2).

## 4. Universe đủ điều kiện (KHOÁ)

Tại mốc `r`, symbol đủ điều kiện nếu: (a) có nến tại `r` **và** tại `r+480` (hoặc nhánh delist §3);
(b) có `f_sig(r)`; (c) `close(r) > 0`. Mốc chỉ dùng nếu **`n_elig ≥ 50`** (khớp `MIN_SYM` vòng trước).
Decile: `K = max(1, round(n_elig / 10))`.

## 5. Ba biến thể + 2 đối chứng (KHOÁ — tối đa 3 biến thể)

**V1 — PURE CARRY.** Short **top-decile `f_sig`** (rate cao nhất), trọng số **bằng nhau** (mỗi tên
`1/K`), giữ **1 chu kỳ 8h**, rebalance mốc kế. Không lọc gì thêm.

**V2 — CARRY + FILTER chống squeeze.** Chỉ short tên thoả **CẢ HAI**: (i) `f_sig > p90(f_sig)` trên
universe đủ điều kiện tại mốc đó (**p90 cross-sectional**, đo tại chỗ); (ii) `ret24 ≤ 0` (giá **không**
đang bay lên). Trọng số bằng nhau trên **số tên thoả**; **nếu 0 tên thoả ⇒ đứng ngoài (flat, pnl = 0,
cost = 0)**.

**V3 — DOLLAR-NEUTRAL CARRY (factor carry kinh điển).** **Long bottom-decile `f_sig`** (0,5 notional)
**+ short top-decile `f_sig`** (0,5 notional), bằng nhau trong từng chân. Funding: chân short **thu**,
chân long **trả** (đúng dấu §2). Giữ 1 chu kỳ.

**Đối chứng A — universe EW short:** short **toàn bộ** universe đủ điều kiện, bằng nhau (baseline
"funding trung bình"). **Đối chứng B — kết quả long-side đã đo** (`RESULT_FUNDING_TOPK_ROTATE`,
`RESULT_FUNDING_FACTOR`): để trả lời "liệu đổi dấu có thật sự lật không".

## 6. Chi phí + kế toán (KHOÁ)

Đơn vị: **%/notional/chu kỳ**. Mọi con số báo **gross (giá+funding)** và **net (trừ chi phí)**.

- **Fee:** taker **0,05%/chân** (chính). Biến thể maker **0,02%/chân** (báo cáo).
- **Slip (mỗi chân):** proxy `0,5 × (h − l) / c` tại **nến của chân đó** (chân mở: nến `r`;
  chân đóng: nến cuối của chu kỳ) — **chính**. Báo thêm 2 mức phẳng: **0,140%/chân** và **1 bp (0,01%)/chân**.
- **Turnover (KHOÁ):** gọi `w_t` = vector trọng số (Σ|w| = 1 trên vế đang giữ). **Traded units**
  `τ_t = Σ_i |w_{t,i} − w_{t−1,i}|` (đi từ flat ⇒ τ = 1; đổi hết sổ ⇒ τ = 2).
  **Turnover 1 vế** `= τ_t / 2` (báo cáo, so được với vòng trước). Sổ phẳng khi V2 không có tên ⇒ τ = 0.
- **Cost_t = τ_t × (fee_chân + slip_chân)**, với `slip_chân = 0,5×(h_r − l_r)/c_r` (nến mốc rebalance).
- **Bắt buộc báo:** turnover trung bình, cost drag, **gross vs net** (bài học long-side: chết vì slip × turnover).
- **Biến thể bảo thủ (báo cáo):** `cost_rt_t = 2 × (fee + slip)` **mỗi chu kỳ** (giả định đóng/mở
  toàn sổ mỗi chu kỳ) — cận trên chi phí.
- **Funding:** cộng **thu/TRA thực** đúng dấu §2 (short: `+f_cyc`; long: `−f_cyc`).

## 7. Cổng thống kê + kết luận (KHOÁ)

- **CI block-72h ×1,21**: block = `floor((BASE + r) / 4320)` (72h = 9 chu kỳ 8h), **2000 rep**,
  **seed 20260905**, khoảng phân vị 2,5–97,5%, nửa rộng × **1,21**.
- **Null (bắt buộc):** short **N coin NGẪU NHIÊN** cùng số lượng với decile thật (N = K tại mốc đó,
  lấy từ cùng universe đủ điều kiện), EW, lặp **≥200 rep** (dùng **300**) seed 20260905 ⇒ so `mean`
  thật với phân bố null ⇒ **p-value 1 vế**.
- **MDE80**: bootstrap lồng (outer 2000 / inner 200), lưới `{0,01; 0,02; 0,05; 0,10; 0,20; 0,50} %/chu kỳ`.
- **Khác:** %chu kỳ dương, net theo **năm**, net **DEV** (chính) vs **ALL** (phụ).
- **Rủi ro short (bắt buộc):** phân bố **max adverse excursion (MAE)** của mỗi vị thế short =
  `max_{t ∈ (r, r+480]} (high_t / close_r − 1)` (dùng nến 1m) và **tỉ lệ squeeze** = % vị thế có
  drawup **> +20%**; báo thêm p50/p90/p99 của MAE và worst-case.
- **GO chỉ khi ĐỦ TẤT CẢ:** (1) **net > 0 sau TẤT CẢ chi phí** ở **chi phí chính**; (2) **CI72h×1,21
  ngoài 0**; (3) **≥60% số chu kỳ dương**; (4) **bền vững qua các biến thể** (không có biến thể nào
  đảo dấu về âm có ý nghĩa); (5) **squeeze không quá lớn** (MAE p99 không thảm; nêu rõ tiêu chí ở kết quả).
  **Một biến thể dương còn biến thể khác không ⇒ UNCONFIRMED (post-hoc)**, KHÔNG áp dụng.
- **NULL ⇒ nói rõ NULL.** Không tô hồng, không đề xuất build/tích hợp.

## 8. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_CARRY.md` | file này (chốt trước, commit TRƯỚC khi đo) |
| `docs/result/RESULT_SHORT_CARRY.md` | kết quả + kết luận GO/NO-GO |
| `research/analysis/short_carry.py` | script thuần Python (đọc Aerospike + `raw/*.f32`) |
| `/home/ubuntu/claudedata/short_carry/` | trung gian **ngoài repo** (resume được): `grid.npz`, `report.txt`, `summary.json` |

## 9. Điểm mù biết trước (ghi trước để không hậu biện)

(i) Không có dữ liệu **fill thật** ⇒ chi phí là **mô hình**, không phải khớp lệnh.
(ii) Funding 4h/8h hỗn hợp: 1 chu kỳ 8h có thể gồm 2 kỳ settle với coin 4h — đã tính đủ theo event.
(iii) `f_sig` là rate **đã settle** (trễ ≤ 1 chu kỳ); đây là causal đúng nhưng **không** phải "rate kỳ tới".
(iv) Không mô hình hoá **margin/liquidation/borrow** cho short; MAE chỉ là **cảnh báo rủi ro**, không
phải mô phỏng thanh lý.
(v) Decile cross-section **phụ thuộc #symbol theo thời gian** (2021 ít coin hơn 2025).
