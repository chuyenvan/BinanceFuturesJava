# PREREG_RANGE4H_TOPK — LUẬT QUAY VÒNG 4h: LONG top-K coin có NẾN 4h BIÊN ĐỘ RỘNG NHẤT

Chốt: **2026-09-22, TRƯỚC khi chạy bất kỳ phép đo nào.** File này commit **TRƯỚC** mọi commit
script/kết quả (đúng `docs/AGENT_RUNBOOK.md` luật 2; thứ tự commit ngược ⇒ kết quả **VOID**).
Sau khi chạy **KHÔNG sửa thiết kế** (định nghĩa biến xếp hạng, mốc rebalance, K, HOLD, phí/slip,
cổng thống kê, số rep, seed, cửa sổ, định nghĩa turnover).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/RESULT_RANGE4H_TOPK.md`).

---

## 0. Luật cần đo + vì sao đáng đo (và tiên lượng GHI TRƯỚC)

**Luật:** cứ mỗi **4 giờ** (mốc **00/04/08/12/16/20 UTC**) với **mỗi symbol** lấy **nến 4h ĐÃ ĐÓNG
gần nhất**, tính **biên độ** = `(high − low) / open`; **xếp hạng GIẢM DẦN theo biên độ** ⇒
**LONG top-K coin có biên độ RỘNG NHẤT**, trọng số **bằng nhau**, giữ **đúng 1 chu kỳ 4h**, rồi
**quay vòng** ở mốc kế tiếp.

Cơ chế biện luận cho luật này: biên độ nến 4h là proxy **biến động/thanh khoản bị hút** ở khung
ngắn; "long coin đang có nến rộng nhất" = **bắt momentum biến động** ở khung 4h.

**Tiên lượng GHI TRƯỚC (không sửa sau khi thấy số):**

1. **NO-GO** là kết cục nhiều khả năng nhất, và lý do **chính là cấu trúc chi phí**, không phải
   thiếu lực:
   - Biến xếp hạng **trùng hướng với chi phí**: `range 4h` rộng ⇔ biến động cao ⇔ **slip cao**.
     Vòng `RESULT_FUNDING_TOPK_ROTATE.md` (commit `fdf61d7`) đã đo: nhóm biến động nhất có
     slip/chiều **0,334%** so với **0,139%** của universe (**×2,4**). Luật này **chọn trực tiếp**
     nhóm đó ⇒ kỳ vọng `slip/chiều` **≥ 0,3%**, tức **cost/chu kỳ ≳ 0,3%** ở turnover ~40–45%,
     và **cao hơn** nếu turnover cao hơn.
   - Ở khung **4h/chu kỳ** (ngắn hơn 8h vòng trước), chu kỳ nhiều gấp đôi ⇒ số lần trả cost cũng
     **gấp đôi/tuần**: cost/year ≈ `net_per_cycle × 6 × 365` (số học). Ngay cả khi `gross ≈ 0`,
     **cost 0,3%/chu kỳ ⇒ −6,6%/năm**.
   - Chân giá: bằng chứng ngắn hạn từ chính repo (neo MOM15 ngược dấu, xem §7c) cho thấy **đuôi
     biến động ngắn hạn không có edge dương ổn định**; tiên lượng `raw` của basket ∈ **[−0,15%,
     +0,10%]/chu kỳ**, xấp xỉ 0 hoặc âm nhẹ.
2. **Điều kiện để tôi bị chứng minh sai (điều kiện GO):** net/chu kỳ **> 0 sau TẤT CẢ chi phí**,
   `CI72h×1.21` **ngoài 0** (cận dưới > 0), **≥60% số chu kỳ dương**, `|net| ≥ MDE80`, **và CẢ BỐN
   giá trị K đều đạt** (§6). Nếu chỉ **một số** K đạt ⇒ **UNCONFIRMED (post-hoc)**, **không áp dụng**.
3. **Kịch bản tôi cho là ĐÁNG CHÚ Ý nhất** (vẫn không phải GO): basket **thắng universe** (do
   momentum ngắn hạn dương) nhưng **net tuyệt đối ≤ 0** vì cost — khi đó phải nói rõ **bằng số**
   (gross vs cost, cost/gross) và **kết luận NO-GO**, đúng tiền lệ funding.

## 1. Ràng buộc (bắt buộc) — tuân thủ ghi rõ

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java trên Oracle (đang có job shadow).
- **THUẦN PYTHON**: chỉ **ĐỌC** `raw/<sym>.f32` (bản extract 1m của `kline_1m_opt`, đúng nguồn
  vòng reversal-bounce/funding-factor/funding-topk) + Aerospike `test.funding_data` (host tunnel
  `127.0.0.1:3222`, **chỉ đọc**). 0-sim, không Java.
- **KHÔNG chạm HOLDOUT 2026**: cắt ≤ `2025-12-31 23:59 UTC`.
- **KHÔNG push** (commit branch `module`, để user push).
- **KHÔNG tự tích hợp** vào hệ thống (nếu có đề xuất ⇒ chỉ là đề xuất, cờ **default OFF**).

## 2. BUOC 0 — dữ liệu (giống hệt 2 vòng trước; ghi lại để truy vết)

| Mục | Giá trị |
|---|---|
| Giá 1m | `raw/<sym>.f32` = **627** file (1 nến 1 phút/dòng: `int32 epoch_minute + float32 O/H/L/C/V`, UTC, 2021-01-01..2025-12-31) — bản extract của `kline_1m_opt` |
| Funding | Aerospike `test.funding_data`, bin `f_data` = Snappy(JSON `{ts_ms: rate}`) (chỉ đọc) |
| Universe | **627** symbol = giao của (có `raw/*.f32`) ∩ (có record funding) — kỳ vọng **627/627** (khớp vòng trước); nếu khác ⇒ ghi rõ |
| Đơn vị | rate thập phân (0,00009642 = 0,009642%/kỳ); **funding dương = long TRẢ** |
| Rác | lọc `ts ≥ 2021-01-01` (3 symbol `GAIBUSDT`/`GRAMUSDT`/`STPTUSDT` có ts 0/âm) |

## 3. Mốc rebalance + lấy mẫu + ĐỊNH NGHĨA BIẾN XẾP HẠNG (KHOÁ)

- `BASE` = phút epoch của `2021-01-01T00:00Z` = **26 824 320**; `NMIN` = **2 629 440** phút (5 năm).
  `BASE % 240 == 0` ⇒ mốc 4h UTC trùng `r % 240 == 0` với `r` = phút **tương đối** so với `BASE`.
- **Mốc rebalance** `r ∈ {0, 240, 480, …}` (tức **00/04/08/12/16/20 UTC**), nhận nếu
  `r + 240 ≤ NMIN − 1` (nếu vượt ⇒ mốc đó **edge-censored, LOẠI** — không cắt ngắn chu kỳ).
  Số mốc kỳ vọng = `NMIN/240` = **10 956**.
- **BIẾN XẾP HẠNG (KHOÁ, công thức):**

  > ```
  > range4h(sym, r) = ( max_{t ∈ [r−240, r−1]} high_t  −  min_{t ∈ [r−240, r−1]} low_t ) / open_{r−240}
  > ```
  >
  > = biên độ của **nến 4h ĐÃ ĐÓNG** kết thúc tại mốc `r` (nến này đóng ở `r`, **không** chứa
  > phút `r`). **LOẠI** nếu `open_{r−240} <= 0` **hoặc** số nến 1m có trong cửa sổ **< 200/240**
  > (dữ liệu khuyết ⇒ biên độ không đáng tin). Đây là **predictor**, KHÔNG phải số hạng PnL.

- **Xếp hạng:** `range4h` **GIẢM DẦN** ⇒ **top-K = K giá trị `range4h` LỚN NHẤT**. Đồng hạng
  (biên độ bằng nhau) phá bằng **chỉ số symbol tăng dần** (argsort ổn định) — khoá trước.
- **Entry** = `close(r)` (nến `r` **đã đóng**; giá biết ở `r+1` phút — cùng convention 2 vòng trước).
  **Exit** = `close(r+240)`.
- **Delist**: nếu symbol hết dữ liệu trước `r+240` ⇒ exit tại **nến cuối có dữ liệu** (nến đó phải
  `> r`, nếu không ⇒ LOẠI mốc cho symbol đó) và đánh cờ `short_delist=1` (**GIỮ**, không lọc
  survivorship — như vòng trước).
- **Eligible tại mốc `r`**: có nến tại phút `r`; `range4h` hợp lệ (§3); exit hợp lệ; `f_cum`
  (§4) hữu hạn. **Eligibility KHÔNG phụ thuộc giá trị biến xếp hạng** (xếp hạng chỉ là tie-break
  giữa các tên đã eligible). Đếm `n_elig(r)`. **Chỉ chạy mốc khi `n_elig(r) ≥ MIN_SYM = 50`**
  (khoá; mốc bị bỏ thì mốc kế tiếp vẫn so set với **set đã giao dịch gần nhất** để tính turnover).
- Một **chu kỳ** = một mốc `r`; chuỗi thống kê = chuỗi `net/chu kỳ` theo `r`.

## 4. Vị thế, HOLD, PnL, CHI PHÍ (KHOÁ — giống hệt vòng funding-topk)

- **Long, trọng số BẰNG NHAU** (`w = 1/K`) — đo **factor thuần**, không sizing.
- **HOLD = 240 phút (đúng 1 chu kỳ 4h)**, quay vòng tại mốc kế tiếp.
- `raw(sym, r) = exit_price/entry_price − 1` (long).
- **Funding thực trả/thu** trong kỳ: `f_cum(sym, r) = cum(ts ≤ (BASE+r+240)·60000) −
  cum(ts ≤ (BASE+r)·60000)` ⇒ cộng **các event có `ts ∈ (r·60000, (r+240)·60000]`** — convention
  vòng trước `(m_e, m_x]`. Long: funding **dương ⇒ TRỪ**, âm ⇒ **cộng**.
- **Phí + slip (mỗi chiều, tại mốc tái cân):**
  - `fee_rt ∈ {0,05%, 0,10%, 0,15%}` (round-trip) ⇒ `fee_side = fee_rt/2`. **Phí chính = 0,10%**.
    Funding **không** đếm hai lần (đã là `f_cum`).
  - `slip(sym, r) = 0.5 × (high(r) − low(r)) / close(r)` — nửa biên độ **nến 1m tại mốc `r`**
    (đúng công thức 2 vòng trước, để chi phí **so được** giữa các vòng), dùng cho **cả** chiều mua
    của tên mới **và** chiều bán của tên bị loại, cùng nến mốc `r`.
  - `n_in(r)` = số tên **mới vào**, `n_out(r)` = số tên **bị loại** so với **set đã giao dịch gần
    nhất** (chu kỳ đầu: `n_out = 0`, `n_in = K`).

  > `cost(r) = (n_in/K)·(fee_side + mean_slip_in) + (n_out/K)·(fee_side + mean_slip_out)`

- **TURNOVER (báo bắt buộc):** `turnover(r) = n_in(r)/K` (1 chiều, = `n_out/K` vì 2 set cùng cỡ K)
  ⇒ khối lượng giao dịch = `2·turnover`. Báo mean/median/p90.
- **COST DRAG (báo bắt buộc):** `cost(r)` theo **pp/chu kỳ** và **% của gross** (`cost/gross`,
  mẫu số = `mean_K(raw) − mean_K(f_cum)` khi > 0), tách **phí** vs **slip** vs **funding**.
- **net/chu kỳ (đại lượng đo):** `net(r) = mean_K(raw) − mean_K(f_cum) − cost(r)` — **sau TẤT CẢ
  chi phí** (phí + slip + funding).
- **FULL-CHURN (biến thể phụ, descriptive):** `cost(r) = fee_rt + 2·mean_slip_K` — **cận trên**
  chi phí, in riêng cạnh bản chính.
- **HOLD 24h (PHỤ, bắt buộc báo — dán nhãn):** lấy **tập con mốc `r % 1440 == 0`** (00 UTC),
  `range4h` **vẫn** là nến 4h đóng tại `r` (§3), **HOLD = 1440'**, exit `close(r+1440)`,
  `f_cum` trên `(r, r+1440]`; turnover/cost tính **giữa 2 basket 24h liên tiếp** theo đúng công
  thức §4. Đây là **descriptive**, không dùng để tuyên bố GO/NO-GO.

## 5. K, đại lượng đo, cổng thống kê (KHOÁ)

| # | Thành phần | Khoá |
|---|---|---|
| K | **K = {1, 3, 5, 10}** | **báo CẢ BỐN**, không chọn K tốt nhất; multiplicity **4** |
| Cửa sổ | **DEV = mốc ∈ [2022-01-01, 2026-01-01)** (**CHÍNH/headline**); **ALL = [2021-01-01, 2026-01-01)** (**PHỤ, dán nhãn rõ**) | **KHÔNG dùng 2026** |
| Đại lượng | `net`/chu kỳ (§4); quy đổi tham khảo: ≈ `net × 6 × 365`/năm (số học, dán nhãn "xấp xỉ") | |
| CI | **block-bootstrap block = 72h** (`blk = (BASE+r) // (72·60)`, **phút epoch** — đúng fix vòng trước), **2000 rep**, **seed 20260905**, percentile 2,5/97,5, nửa-độ-rộng **×1,21** ⇒ `CI72h×1.21`; báo `p(mean>0)` |
| Bonferroni | `K_test = 4` (4 giá trị K) ⇒ `α_B = 0,05/4 = 0,0125` (một phía) ⇒ `CI-Bonf4` |
| Null test | mỗi chu kỳ: lấy **K coin NGẪU NHIÊN** từ đúng eligible pool của mốc đó (không hoàn lại), **cùng mô hình chi phí** (turnover riêng của basket ngẫu nhiên) ⇒ **≥200 rep** (dùng **300**), seed `20260905 + K`; `p = P(null ≥ obs)`; báo mean/sd |
| MDE | `MDE(80%)` = X nhỏ nhất trong lưới **{0,01; 0,02; 0,05; 0,10; 0,20; 0,50}% /chu kỳ** có `power ≥ 80%` (2000 outer × 200 inner trên khung block-72h) — **lưới riêng cho khung 4h/chu kỳ** |
| Nhất quán dấu | **% số chu kỳ có `net > 0` ≥ 60%** |
| Theo năm | bảng `net/chu kỳ` theo năm (**GMT+7**, `+420'`) + N chu kỳ + % chu kỳ dương |
| Độ nhạy phí | lưới `fee_rt ∈ {0,05%; 0,10%; 0,15%}` × **4 K** — báo đủ |

**CỔNG KẾT LUẬN (KHOÁ):**

- **GO** cho một K ⟺ **đồng thời**: (1) `net/chu kỳ > 0` **sau TẤT CẢ chi phí** ở phí 0,10%;
  (2) `CI72h×1.21` **ngoài 0** (cận dưới > 0); (3) `CI-Bonf4` ngoài 0 (tức `p < 0,0125`);
  (4) **≥60% chu kỳ dương**; (5) `|net| ≥ MDE80` của chính chuỗi đó; (6) **không đổi dấu** ở ALL;
  (7) **không đổi dấu** ở chiều xấu hơn của độ nhạy phí (0,15%) — nếu đổi dấu ⇒ **fragile**.
- **BỀN VỮNG QUA K:** **GO chỉ được tuyên bố khi CẢ 4 K đều đạt** (1)–(6). Nếu **một số** K đạt mà
  K khác không ⇒ ghi **UNCONFIRMED (post-hoc)**, **KHÔNG áp dụng** (multiplicity).
- **NO-GO** ⟺ CI chứa 0 **hoặc** net ≤ 0 sau chi phí **hoặc** |hiệu ứng| < MDE (⇒ ghi rõ "không
  phân giải được"). **NULL phải nói NULL**, không có "gần đạt".
- Nếu **turnover/chi phí giết luật** ⇒ **phải nói rõ bằng số**: `cost drag/chu kỳ` (pp và % của
  gross), tách **phí vs slip vs funding**, và **gross/chu kỳ vs net/chu kỳ**.

## 6. Đối chứng (KHOÁ — phải báo)

1. **(a) Trung bình universe cùng kỳ**: long **toàn bộ eligible** (equal-weight, cùng mô hình chi
   phí với turnover riêng của universe) tại mỗi chu kỳ.
2. **(b) Neo MOM15**: tái tạo **đúng** harness (bộ đo còn lực) —
   `total_rows` = **619 073 711**; phút MOM15 = **13 150**; M-LEVEL MOM15 `k=1` ALL = **11 367**,
   DEV = **7 128**; MOM15 `k=1` DEV 24h phí 0,10% net = **+1,6690%**; ALL 24h = **+2,2622%`;
   `N_blk` DEV = **301**. **Sai khớp > 0,05pp ⇒ VOID** (báo lỗi harness, không kết luận luật).
3. **(c) Dẫn chiếu vòng trước**: `RESULT_FUNDING_TOPK_ROTATE.md` (commit `fdf61d7`) — top-K funding
   nhỏ nhất khung 8h: net **−0,2223%/−0,1709%/−0,1460%** (K=5/10/20), cost/gross **351%/350%/435%**,
   slip/chiều basket **0,334%** vs universe **0,139%**; universe equal-weight **−0,0129%/chu kỳ
   (8h)**. Vòng này **phải đối chiếu** với các con số đó (nhất quán hay mâu thuẫn, và vì sao).
   Tiền lệ xa: `docs/SURVEY_OLDCODE_SIGNALS.md` (`FUNDING_FEE_BUY` → FAIL WFE 0,098).

## 7. Descriptives bắt buộc báo (KHÔNG tính là test)

1. `n_elig` theo mốc: min/median/max; số mốc dùng; số mốc bị bỏ (<50); **turnover** mean/median/p90;
2. `range4h` của basket chọn: mean/median/min/max; **phân vị của basket trong phân bố universe**
   (vd trung vị phân vị của tên được chọn);
3. Bóc chi phí: `gross_raw` (= raw), `f_cum`, `phí`, `slip`, `net` — **tách thành phần** mỗi chu kỳ;
   **slip/chiều của basket vs universe** (dự đoán: basket ≫ universe);
4. `net`/chu kỳ theo **năm** (GMT+7) + **% chu kỳ dương**; ICC theo **ngày** và theo **block-72h**;
5. Đường **MDE** theo N và MDE từng K; **null test** cho cả 4 K;
6. **HOLD 24h** (PHỤ) cho cả 4 K;
7. **Biến thể full-churn** (cận trên chi phí) cho cả 4 K;
8. **Độ nhạy phí** 0,05/0,10/0,15% cho cả 4 K; **độ nhạy `MIN_SYM`** (50 vs 100) nếu rẻ — descriptive.

## 8. Artifacts + vệ sinh

- Script: `research/analysis/range4h_topk.py` (sinh grid mốc 4h + neo MOM15),
  `research/analysis/range4h_topk_stats.py` (thống kê/báo cáo). **Thuần Python**.
- Trung gian: `/tmp/range4h_topk/*.npz` + `*.log` (**resume được**; checkpoint mỗi 150 symbol;
  **ngoài repo**). Ghi kết quả trung gian **ngay sau mỗi K** để resume được.
- Kết quả: `docs/RESULT_RANGE4H_TOPK.md`. Commit pre-reg + script + kết quả. **KHÔNG push.**
- Dọn file tạm sau khi chốt số.

## 9. Nhánh vô hiệu ghi trước

1. Neo MOM15 (§6b) sai khớp > 0,05pp ⇒ **VOID**, báo lỗi harness (không kết luận luật).
2. `n_elig < 50` ở **đa số** mốc ⇒ báo descriptive, không kết luận.
3. Số block 72h quá nhỏ (không tính được CI có nghĩa) ⇒ chỉ descriptive.
4. Nếu lộ ra lỗi cài đặt: sửa **TRƯỚC khi chốt số** và **ghi lại** trong kết quả (đúng tiền lệ
   vòng trước); nếu đã chốt số rồi mới lộ ⇒ **VOID**.

## 10. Multiplicity

`K_test = 4` **giá trị K** (1/3/5/10) là 4 test khoá ⇒ Bonferroni `0,05/4 = 0,0125`. Các bảng: theo
năm, độ nhạy phí, HOLD 24h, full-churn, universe control, ICC, `MIN_SYM` — **descriptive**; ô "đẹp"
ngoài 4 test khoá **không được** tuyên bố.
