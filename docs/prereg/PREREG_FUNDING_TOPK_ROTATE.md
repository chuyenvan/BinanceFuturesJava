# PREREG_FUNDING_TOPK_ROTATE — LUẬT QUAY VÒNG 8h: LONG top-K coin có FUNDING FEE NHỎ NHẤT

Chốt: **2026-09-22, TRƯỚC khi chạy bất kỳ phép đo nào.** File này commit **TRƯỚC** mọi commit
script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; thứ tự commit ngược ⇒ kết quả **VOID**).
Sau khi chạy **KHÔNG sửa thiết kế** (mốc rebalance, xếp hạng, K, HOLD, phí/slip, cổng thống kê,
số rep, seed, cửa sổ, cách xử lý cadence, định nghĩa turnover).

Trạng thái: **ĐANG CHỜ ĐO** (khi kết quả xong ⇒ `docs/result/RESULT_FUNDING_TOPK_ROTATE.md`).

---

## 0. Luật cần đo + vì sao đáng đo (và vì sao tôi tiên lượng NO-GO)

**Luật:** cứ mỗi **8 giờ** (mốc 00/08/16 UTC) **xếp hạng toàn universe theo funding rate tăng dần**
và **LONG top-K coin có funding NHỎ NHẤT**, trọng số **bằng nhau**, giữ **đúng 1 chu kỳ 8h**, rồi
**quay vòng** ở mốc kế tiếp.

Cơ chế biện luận cho luật này: với hệ **long-only perp**, funding là **khoản tiền trả định kỳ**;
long coin có funding nhỏ nhất/âm nhất ⇒ (i) **giảm chi phí carry**, (ii) hưởng **funding âm = thu
nhập**. Câu hỏi là liệu phần "tiết kiệm/thu nhập funding" + chênh lệch giá có **sống sót qua chi
phí quay vòng** (fee + slip **mỗi chiều**) không.

**Tiên lượng GHI TRƯỚC (không sửa sau khi thấy số):**

1. **NO-GO** là kết cục nhiều khả năng nhất. Lý do:
   - Vòng trước (`docs/result/RESULT_FUNDING_FACTOR.md`, commit `5b548e4`) đo **đúng hướng này** ở dạng
     tĩnh: decile funding thấp nhất (D1) net 24h = **−0,1913%**, **CI chứa 0**; IC cross-section
     `f_entry`→net chỉ **+0,0009** ⇒ hướng "funding thấp ⇒ long tốt" **chưa từng dương có ý nghĩa**.
   - H1 của vòng trước cho thấy funding **dai dẳng** (Spearman(f_entry, f_cum) = 0,60 ở 24h) ⇒
     tiết kiệm funding là **thật nhưng NHỎ** (biên độ đo được: D10 +0,0742%/24h; toàn bộ chênh
     lệch funding giữa 2 đầu decile chỉ ≈ **0,03%/lệnh @24h** — nhỏ hơn **slip 0,13–0,21%** và
     **fee 0,10%**).
   - Ở khung **8h/chu kỳ**, chi phí quay vòng bị **chia cho 1/3 thời gian** so với 24h ⇒ cost drag
     mỗi chu kỳ kỳ vọng **≈ 0,2–0,4%** (fee 0,05–0,1% + 2×slip ~0,15–0,3%), trong khi "lợi thế
     funding" kỳ vọng **≲0,05%/chu kỳ** ⇒ **lệch 1 bậc độ lớn về phía chi phí**.
2. **Điều kiện để tôi bị chứng minh sai (điều kiện GO):** net/chu kỳ **> 0 sau TẤT CẢ chi phí**,
   CI **ngoài 0**, **≥60% số chu kỳ dương**, |hiệu ứng| ≥ MDE, và **cả 3 giá trị K** đều đạt
   (§6). Nếu chỉ **một** K đạt ⇒ **UNCONFIRMED (post-hoc)**, **không áp dụng**.

## 1. Ràng buộc (bắt buộc) — tuân thủ ghi rõ

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java trên Oracle (đang có job shadow).
- **THUẦN PYTHON**: chỉ **ĐỌC** Aerospike `test.funding_data` (set funding) + `raw/<sym>.f32`
  (bản extract 1m của `kline_1m_opt`, đúng nguồn vòng reversal-bounce/funding) — 0-sim, không Java.
- **KHÔNG chạm HOLDOUT 2026**: cắt ≤ `2025-12-31 23:59 UTC`.
- **KHÔNG push.** Pre-reg commit TRƯỚC; sau khi chạy không sửa thiết kế.
- **KHÔNG tự tích hợp** vào hệ thống (nếu có đề xuất ⇒ chỉ là đề xuất, cờ **default OFF**).

## 2. BUOC 0 — dữ liệu (đã xác minh ở vòng trước; ghi lại đúng nguồn dùng lần này)

| Mục | Giá trị |
|---|---|
| Funding | Aerospike `test.funding_data`, bin `f_data` = **Snappy(JSON `{ts_ms: rate}`)**; host tunnel `127.0.0.1:3222` → `103.157.218.242:3222` (**chỉ đọc**) |
| Funding coverage | 831 symbol / **2 394 587** event / 2021-01-01 → 2026-08-05 (dùng ≤ 2025-12-31) |
| Cadence funding | **hỗn hợp**: 476 symbol **4h**, 345 symbol **8h**, 10 symbol khác (1h–6h) |
| Giá 1m | `raw/<sym>.f32` = **627** file (1 nến 1 phút/dòng: `int32 epoch_minute + float32 O/H/L/C/V`, UTC, 2021-01-01..2025-12-31) — bản extract của `kline_1m_opt` |
| Universe | **627** symbol = giao của (có `raw/*.f32`) ∩ (có record funding) = **627/627** (khớp universe sim ~627). Nếu số khác ⇒ ghi rõ cách map trong kết quả |
| Đơn vị | rate thập phân (0,00009642 = 0,009642%/kỳ); **funding dương = long TRẢ** |
| Rác | 3 symbol ts = 0/âm (`GAIBUSDT`, `GRAMUSDT`, `STPTUSDT`) ⇒ đã lọc `ts ≥ 2021-01-01` |

## 3. Mốc rebalance + lấy mẫu (KHOÁ)

- `BASE` = phút epoch của `2021-01-01T00:00Z` = **26 824 320**; `NMIN` = 2 629 440 phút (5 năm).
  `BASE % 480 == 0` ⇒ mốc 8h UTC trùng `r % 480 == 0` với `r` = phút **tương đối** so với `BASE`.
- **Mốc rebalance** `r ∈ {0, 480, 960, …}` (tức **00/08/16 UTC**), nhận nếu `r + 480 ≤ NMIN − 1`
  (nếu vượt ⇒ mốc đó **edge-censored, LOẠI** — không cắt ngắn chu kỳ).
- **Entry** = `close(r)` (nến `r` **đã đóng**; giá biết ở `r+1` phút). **Exit** = `close(r+480)`.
- **Delist**: nếu symbol hết dữ liệu trước `r+480` ⇒ exit tại **nến cuối có dữ liệu** (nến đó
  phải `> r`, nếu không ⇒ LOẠI mốc cho symbol đó) và đánh cờ `short_delist=1` (**GIỮ**, như vòng
  trước — không lọc survivorship).
- **Eligible tại mốc `r`**: có nến tại phút `r`; exit hợp lệ (§3); `f_entry` hữu hạn (§4). Đếm
  `n_elig(r)`. **Chỉ chạy mốc khi `n_elig(r) ≥ MIN_SYM = 50`** (khoá; nếu mốc bị bỏ thì mốc kế tiếp
  vẫn so set với **set đã giao dịch gần nhất** để tính turnover).
- Một **chu kỳ** = một mốc `r`; chuỗi thống kê = chuỗi `net/chu kỳ` theo `r`.

## 4. Xếp hạng + cadence hỗn hợp (KHOÁ, ghi rõ cách chọn + cách còn lại)

**Biến xếp hạng (causal, KHÔNG nhìn tương lai):**

> `f_entry(sym, r)` = **rate của event funding CUỐI CÙNG có `ts ≤ (BASE+r)·60000`**.
> Đây là rate **đã biết tại thời điểm vào lệnh** (với đa số symbol, event 8h/4h rơi **đúng** vào
> mốc `r`). Đây là **predictor**, KHÔNG phải số hạng PnL.

**Xếp hạng:** funding **tăng dần** ⇒ **top-K = K giá trị `f_entry` NHỎ NHẤT**. Đồng hạng
(rate bằng nhau, gồm rate = 0) phá bằng **chỉ số symbol tăng dần** (argsort ổn định) — khoá trước.

**Cadence hỗn hợp — chốt 1 cách + 1 cách phụ:**

- **CÁCH CHÍNH (A):** lấy `f_entry` = giá trị funding **hiệu lực tại mốc 8h cho MỌI symbol**
  (định nghĩa `f_entry` ở trên, event cuối ≤ mốc). Universe = **cả 627** symbol. Chi phí funding
  thực trả trong chu kỳ = `f_cum` (§5) ⇒ symbol cadence 4h tự động bị tính **2 event/chu kỳ**.
  Cách này giữ nguyên universe (so được với sim ~627) và **không tạo look-ahead**.
- **CÁCH PHỤ (B) — báo riêng, KHÔNG dùng để tuyên bố:** universe **chỉ symbol cadence 8h**
  (≈345 symbol, phân loại cadence = **trung vị khoảng cách event** trên `≤2025-12-31` như vòng
  coverage) — để kiểm tra kết quả (A) không phải artefact của việc trộn 2 cadence.

## 5. Vị thế, HOLD, PnL, CHI PHÍ (KHOÁ)

- **Long, trọng số BẰNG NHAU** (`w = 1/K`) — để đo **factor thuần**, không sizing.
- **HOLD = 480 phút (đúng 1 chu kỳ 8h)**, quay vòng tại mốc kế tiếp.
- `raw(sym, r) = exit_price/entry_price − 1` (long).
- **Funding thực trả/thu** trong kỳ: `f_cum(sym, r) = cum(ts ≤ (BASE+r+480)·60000) −
  cum(ts ≤ (BASE+r)·60000)` ⇒ cộng **các event có `ts ∈ (r·60000, (r+480)·60000]`** — **giống
  convention vòng trước** (`(m_e, m_x]`), tức **event tại mốc exit được tính** (vị thế vẫn mở tại
  mốc đó; và mốc exit cũng là mốc tái cân). Long: funding **dương ⇒ TRỪ**, âm ⇒ **cộng**.
- **Phí + slip (mỗi chiều, tại mốc tái cân):**
  - `fee_rt ∈ {0,05%, 0,10%, 0,15%}` (round-trip) ⇒ `fee_side = fee_rt/2`. **Phí chính = 0,10%**
    (khớp vòng trước). Funding **không** đếm hai lần (đã là `f_cum`).
  - `slip(sym, r) = 0.5 × (high(r) − low(r)) / close(r)` (nửa biên độ nến 1m tại mốc; dùng cho
    **cả** chiều mua của tên mới **và** chiều bán của tên bị loại, cùng nến mốc `r`).
  - Gọi `n_in(r)` = số tên **mới vào**, `n_out(r)` = số tên **bị loại** so với **set đã giao dịch
    gần nhất** (chu kỳ đầu: `n_out = 0`, `n_in = K` — chỉ có chiều mua).

  > `cost(r) = (n_in/K)·(fee_side + mean_slip_in) + (n_out/K)·(fee_side + mean_slip_out)`

- **TURNOVER (KHOÁ, báo bắt buộc):** `turnover(r) = n_in(r)/K` (1 chiều, = `n_out/K` vì 2 set cùng
  cỡ K) ⇒ khối lượng giao dịch = `2·turnover`. Báo **turnover trung bình/chu kỳ** (và phân vị).
- **COST DRAG (báo bắt buộc):** `cost(r)` tính bằng **pp/chu kỳ** và **% của gross** (tỷ lệ
  `cost / (gross_raw − f_cum)` khi mẫu số > 0), tách **phí** vs **slip** vs **funding**.
- **net/chu kỳ (đại lượng đo):**
  `net(r) = mean_K(raw) − mean_K(f_cum) − cost(r)` — **sau TẤT CẢ chi phí** (phí + slip + funding).
- **FUll-CHURN (biến thể phụ, descriptive):** `cost(r) = fee_rt + 2·mean_slip_K` (quay vòng
  **toàn bộ** book mỗi chu kỳ) — **cận trên** chi phí, in riêng cạnh bản chính.

## 6. K, đại lượng đo, cổng thống kê (KHOÁ)

| # | Thành phần | Khoá |
|---|---|---|
| K | **K = {5, 10, 20}** | **báo CẢ BA**, không chọn K tốt nhất; multiplicity **3** |
| Cửa sổ | **DEV = mốc ∈ [2022-01-01, 2026-01-01)** (**CHÍNH/headline**); **ALL = [2021-01-01, 2026-01-01)** (**PHỤ, dán nhãn rõ**) | **KHÔNG dùng 2026** |
| Đại lượng | `net`/chu kỳ (§5); quy đổi tham khảo: ≈ `net × 3 × 365`/năm (số học, dán nhãn "xấp xỉ") | |
| CI | **block-bootstrap block = 72h** (`blk = (BASE+r) // (72·60)`), **2000 rep**, **seed 20260905**, percentile 2,5/97,5, nửa-độ-rộng **×1,21** ⇒ `CI72h×1.21`; báo `p(mean>0)` |
| Bonferroni | `K_test = 3` (3 giá trị K) ⇒ `α_B = 0,05/3 = 0,016667` (một phía) ⇒ `CI-Bonf3` |
| Null test | với **mỗi chu kỳ**: lấy **K coin NGẪU NHIÊN** từ đúng eligible pool của mốc đó (không hoàn lại), **cùng mô hình chi phí** (turnover riêng của basket ngẫu nhiên) ⇒ **≥200 rep**, seed `20260905 + K`; `p = P(null ≥ obs)`; báo mean/sd null |
| MDE | `MDE(80%)` = X nhỏ nhất trong lưới **{0,01; 0,02; 0,05; 0,10; 0,20; 0,50}% /chu kỳ** có `power ≥ 80%` (thủ tục lặp như vòng trước, 2000 outer × 200 inner) — **lưới riêng cho khung 8h/chu kỳ**, vì đơn vị nhỏ hơn khung 24h/72h cũ |
| Nhất quán dấu | **% số chu kỳ có `net > 0` ≥ 60%** (cùng luật đã dùng ở vòng harness) |
| Theo năm | bảng `net/chu kỳ` theo năm (**GMT+7**) + N chu kỳ + % chu kỳ dương |
| Độ nhạy phí | lưới `fee_rt ∈ {0,05%; 0,10%; 0,15%}` × K — **báo đủ 3 mức** |

**CỔNG KẾT LUẬN (KHOÁ):**

- **GO** cho một K ⟺ **đồng thời**: (1) `net/chu kỳ > 0` **sau TẤT CẢ chi phí** ở phí 0,10%;
  (2) `CI72h×1.21` **ngoài 0** (cận dưới > 0); (3) `CI-Bonf3` ngoài 0 (tức `p < 0,016667`);
  (4) **≥60% chu kỳ dương**; (5) `|net| ≥ MDE80` của chính chuỗi đó; (6) **không đổi dấu** ở ALL
  (cùng K); (7) **không đổi dấu** ở chiều xấu hơn của độ nhạy phí (0,15%) — nếu đổi dấu ⇒ **fragile**.
- **BỀN VỮNG QUA K:** **GO chỉ được tuyên bố khi CẢ 3 K đều đạt** (1)–(6). Nếu **một** K đạt mà K
  khác không ⇒ ghi **UNCONFIRMED (post-hoc)**, **KHÔNG áp dụng** (multiplicity).
- **NO-GO** ⟺ CI chứa 0 **hoặc** net ≤ 0 sau chi phí **hoặc** |hiệu ứng| < MDE (⇒ ghi rõ "không
  phân giải được"). **NULL phải nói NULL**, không có "gần đạt".
- Nếu **turnover/chi phí giết luật** ⇒ **phải nói rõ bằng số**: `cost drag/chu kỳ` (pp và % của
  gross), tách **phí vs slip vs funding**, và so **gross/chu kỳ** vs **net/chu kỳ**.

## 7. Đối chứng (KHOÁ — phải báo)

1. **(a) Trung bình universe cùng kỳ**: long **toàn bộ eligible** (equal-weight, cùng mô hình chi
   phí với turnover riêng của universe) tại mỗi chu kỳ — để biết luật top-K **hơn/kém basket** bao nhiêu.
2. **(b) Neo MOM15**: tái tạo **đúng** harness (để xác nhận bộ đo còn lực) —
   `total_rows` = **619 073 711**; phút MOM15 = **13 150**; M-LEVEL MOM15 `k=1` ALL = **11 367**,
   DEV = **7 128**; MOM15 `k=1` DEV 24h phí 0,10% net = **+1,6690%** (tham chiếu đã công bố
   `+1,6431%`; vòng trước đo 1,6690%); ALL 24h = **+2,2622%** (ref "+2,26%"). **Sai khớp > 0,05pp
   ⇒ VOID** (báo lỗi harness, không kết luận).
3. **(c) Dẫn chiếu H2 vòng trước**: `docs/result/RESULT_FUNDING_FACTOR.md` §0/§5 — D1 (funding thấp nhất)
   net 24h = **−0,1913%**, **CI chứa 0**, IC **+0,0009**. Kết quả lần này **phải đối chiếu** với
   con số đó (nhất quán hay mâu thuẫn, và vì sao — khung 8h + quay vòng + chi phí quay vòng).
   Tiền lệ xa hơn: `docs/analysis/SURVEY_OLDCODE_SIGNALS.md` — rule cũ `FUNDING_FEE_BUY` → ML
   `funding_selector` → **FAIL (WFE med 0,098)**.

## 8. Descriptives bắt buộc báo (KHÔNG tính là test)

1. `n_elig` theo mốc: min/median/max; số mốc dùng; số mốc bị bỏ (<50); **turnover** mean/median/p90;
2. `f_entry` của basket chọn: mean/median/min/max; **% tên có `f_entry ≤ 0`**; **% tên `= 0`**;
3. Bóc chi phí: `gross_raw`, `f_cum`, `phí`, `slip`, `net` — **ttách thành phần** mỗi chu kỳ;
4. `net`/chu kỳ theo **năm** (GMT+7) + **% chu kỳ dương**; ICC theo **ngày** và theo **block-72h**;
5. Đường **MDE** theo N và MDE của từng K; **null test** cho cả 3 K;
6. **Cách phụ (B)** universe chỉ cadence 8h: đủ 3 K;
7. **Biến thể full-churn** (cận trên chi phí) cho cả 3 K;
8. **Độ nhạy phí** 0,05/0,10/0,15% cho cả 3 K; và **độ nhạy `MIN_SYM`** (50 vs 100) nếu rẻ — descriptive.

## 9. Artifacts + vệ sinh

- Script: `research/analysis/funding_topk_rotate.py` (sinh grid mốc 8h + neo MOM15),
  `research/analysis/funding_topk_rotate_stats.py` (thống kê/báo cáo). **Thuần Python.**
- Trung gian: `/tmp/funding_topk/*.npz` + `*.log` (**resume được**; ghi checkpoint; **ngoài repo**).
- Kết quả: `docs/result/RESULT_FUNDING_TOPK_ROTATE.md`. Commit pre-reg + script + kết quả. **KHÔNG push.**
- Dọn file tạm sau khi chốt số (giữ `pools.npz`/`mark_grid.npz` tới khi commit xong).

## 10. Nhánh vô hiệu ghi trước

1. Neo MOM15 (§7b) sai khớp > 0,05pp ⇒ **VOID**, báo lỗi harness (không kết luận luật).
2. `n_elig < 50` ở **đa số** mốc ⇒ báo descriptive, không kết luận.
3. Số block 72h quá nhỏ (không tính được CI có nghĩa) ⇒ chỉ descriptive.
4. Nếu lộ ra lỗi cài đặt (đơn vị phút epoch/tương đối, lệch thứ tự dòng): sửa **TRƯỚC khi chốt số**
   và **ghi lại** trong kết quả (đúng tiền lệ vòng trước); nếu đã chốt số rồi mới lộ ⇒ **VOID**.

## 11. Multiplicity

`K_test = 3` **giá trị K** (5/10/20) là 3 test khoá ⇒ Bonferroni `0,05/3 = 0,016667`.
Các bảng: theo năm, độ nhạy phí, cách phụ (B), full-churn, universe control, ICC, `MIN_SYM` —
**descriptive**; ô "đẹp" ngoài 3 test khoá **không được** tuyên bố.
