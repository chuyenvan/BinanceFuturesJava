# PREREG_FUNDING_TOPK_K13 — MỞ RỘNG **K = 1** và **K = 3** CHO LUẬT QUAY VÒNG 8h: LONG top-K coin có FUNDING FEE NHỎ NHẤT

Chốt: **2026-09-22, TRƯỚC khi chạy bất kỳ phép đo nào.** File này commit **TRƯỚC** mọi commit script/kết quả
(đúng `docs/AGENT_RUNBOOK.md` luật 2; thứ tự commit ngược ⇒ kết quả **VOID**).
Quan hệ với vòng trước: `docs/PREREG_FUNDING_TOPK_ROTATE.md` (**commit `55b8280`**) +
`docs/RESULT_FUNDING_TOPK_ROTATE.md` (**commit `fdf61d7`**) đã đo **K = {5, 10, 20}** ⇒ **NO-GO cả 3**.

Trạng thái: **ĐANG CHỜ ĐO** (kết quả ⇒ `docs/RESULT_FUNDING_TOPK_K13.md`).

---

## 0. Phạm vi thay đổi: **CHỈ THÊM K = 1 VÀ K = 3**

Đây **KHÔNG** phải thiết kế mới. Toàn bộ thiết kế của vòng trước được **giữ NGUYÊN VĂN**; thứ duy nhất
được mở rộng là **danh sách K** (thêm 1 và 3). Mọi câu hỏi "có đúng thiết kế không?" ⇒ đối chiếu
`docs/PREREG_FUNDING_TOPK_ROTATE.md` §3–§6 + `docs/RESULT_FUNDING_TOPK_ROTATE.md` §1 (neo MOM15 7/7 khớp).

**Vì sao vẫn đáng đo (ghi TRƯỚC khi thấy số):** ở vòng trước net **xấu hơn khi K nhỏ**
(K=5 −0,2223% vs K=20 −0,1460%), **ngược** chiều với trực giác "K nhỏ ⇒ harvest funding tập trung hơn".
Nhưng chuỗi này chưa chạm **K = 1 và K = 3** — hai điểm ở **rìa trái** của cùng một họ tham số, nơi
(i) **harvest funding lớn nhất** (chọn đúng 1/3 coin funding âm nhất) nhưng (ii) **turnover + slip + chân
giá xấu nhất**. Đo nốt để **chốt họ K** (không chọn K tốt nhất — xem §4 multiplicity) và để biết kết luận
vòng trước có phải là một **đường đơn điệu theo K** hay không.

**Tiên lượng GHI TRƯỚC (không sửa sau khi thấy số):** **NO-GO cả K=1 và K=3**, và **net(K=1) ≤ net(K=5)
≤ net(K=10) ≤ net(K=20)** (đơn điệu: K nhỏ ⇒ cost drag lớn hơn phần funding thu thêm). Dự đoán cụ thể
net/chu kỳ DEV @0,10% **K=1 nằm trong khoảng −0,20% … −0,60%/chu kỳ**; **K=3 trong khoảng −0,20% …
−0,35%**. Nếu **K=1 hoặc K=3 dương** thì tiên lượng này **sai** và phải ghi rõ là **đảo chiều ngoài dự
đoán** (không được "diễn giải lại" thành dự đoán cũ).

## 1. Ràng buộc (bắt buộc) — giữ y vòng trước

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java (Oracle đang có job shadow dùng slot JVM).
- **THUẦN PYTHON**: chỉ **ĐỌC** Aerospike `test.funding_data` (tunnel `127.0.0.1:3222`, chỉ đọc) +
  `raw/<sym>.f32` (`kline_1m_opt` extract). 0-sim.
- **KHÔNG chạm HOLDOUT 2026**: cắt ≤ `2025-12-31 23:59 UTC`.
- **KHÔNG push.** Pre-reg commit TRƯỚC; sau khi chạy **không sửa thiết kế**.
- **KHÔNG tự tích hợp** vào hệ thống; **không** đề xuất feature nếu không có GO.

## 2. Giữ NGUYÊN (danh sách khoá — copy nguyên trạng vòng trước)

| # | Thành phần | Giá trị (KHÔNG đổi trong vòng này) |
|---|---|---|
| 1 | Mốc rebalance | `r % 480 == 0` (00/08/16 UTC), `BASE = 26 824 320` (2021-01-01), mốc phải có `r+480 ≤ NMIN−1` |
| 2 | Entry/Exit | entry `close(r)`, exit `close(r+480)`; delist ⇒ exit tại nến cuối (> r) + cờ `short_delist` (GIỮ) |
| 3 | Predictor | `f_entry` = rate của event funding **cuối cùng có `ts ≤ (BASE+r)·60000`** (causal) |
| 4 | Xếp hạng | funding **tăng dần** ⇒ top-K = K giá trị nhỏ nhất; đồng hạng phá bằng **chỉ số symbol tăng dần** |
| 5 | Trọng số / HOLD | equal-weight `w = 1/K`; **HOLD 480'** đúng 1 chu kỳ, quay vòng ở mốc kế tiếp |
| 6 | Eligibility | có nến tại `r`; exit hợp lệ; `f_entry` hữu hạn ⇒ `n_elig(r)`; chỉ chạy mốc khi **`n_elig ≥ MIN_SYM = 50`** |
| 7 | Funding thực trả | `f_cum` = tổng event `ts ∈ (r·60000, (r+480)·60000]` (event tại mốc exit **được tính**), long: dương ⇒ trừ |
| 8 | Phí | `fee_rt ∈ {0,05%; 0,10%; 0,15%}`, **phí chính 0,10%**; `fee_side = fee_rt/2` |
| 9 | Slip | `slip(sym,r) = 0.5·(high(r)−low(r))/close(r)`, áp **mỗi chiều** trên phần book quay vòng |
| 10 | Cost | `cost(r) = (n_in/K)(fee_side+slip_in) + (n_out/K)(fee_side+slip_out)`; **turnover** = `n_in/K` (1 chiều), chu kỳ đầu `n_out=0, n_in=K` |
| 11 | Đại lượng | `net(r) = mean_K(raw) − mean_K(f_cum) − cost(r)` (sau **TẤT CẢ** chi phí) |
| 12 | Cửa sổ | **DEV = mốc ∈ [2022-01-01, 2026-01-01) CHÍNH**; **ALL = [2021-01-01, 2026-01-01) PHỤ** (dán nhãn) |
| 13 | CI | block-**72h** theo **phút epoch** (`(BASE+mark)//(72·60)`), **2000 rep**, **seed 20260905**, percentile 2,5/97,5, nhân **×1,21** |
| 14 | Null | **300 rep** (≥200), **K coin ngẫu nhiên** không hoàn lại từ đúng eligible pool, cùng mô hình chi phí, seed `20260905 + K`, `p = P(null ≥ obs)` |
| 15 | MDE | lưới `{0,01; 0,02; 0,05; 0,10; 0,20; 0,50}% /chu kỳ`, 2000 outer × 200 inner, power ≥ 80% |
| 16 | Cổng | (1) net>0 @0,10%; (2) cận dưới CI72h×1.21 > 0; (3) CI-Bonferroni ngoài 0; (4) **≥60% chu kỳ dương**; (5) `|net| ≥ MDE80`; (6) không đổi dấu ở ALL; (7) không đổi dấu ở phí 0,15% |
| 17 | Đối chứng | (a) universe equal-weight cùng mô hình chi phí; (b) **neo MOM15** phải khớp 7/7 (nếu lệch >0,05pp ⇒ **VOID**); (c) dẫn chiếu H2 vòng `RESULT_FUNDING_FACTOR` (D1 24h −0,1913%, CI chứa 0) |
| 18 | Nhãn phụ | full-churn (cận trên), cách phụ (B) universe cadence 8h, độ nhạy `MIN_SYM` 50/100, ICC, bảng theo năm — **descriptive**, không dùng để tuyên bố |

## 3. KHOÁ MỚI (chỉ ở vòng này)

1. **Họ K của vòng này: `K ∈ {1, 3, 5, 10, 20}`.** K=5/10/20 **không** đổi cách đo; số của vòng trước
   được **đối chiếu lại** (re-run cùng script) và **phải trùng trong sai số làm tròn** (net, CI, turnover,
   cost). Lệch > 1 đơn vị ở chữ số cuối đã công bố ⇒ **VOID** (báo lỗi harness, không kết luận).
2. **Multiplicity: `K_test = 5`** (cả họ K) ⇒ **Bonferroni `α_B = 0,05/5 = 0,01`** (một phía).
   Cột "CI-Bonf" trong kết quả vòng này dùng **p < 0,01** cho **mọi** K. (Số K=5/10/20 của vòng trước đã
   tính với `K_test=3`, `p<0,016667`; vòng này **siết chặt hơn** — chỉ làm việc bác bỏ **khó hơn**, không
   nới lỏng. Cả hai mức đều được in để truy vết.)
3. **Bền vững qua K (giữ luật vòng trước):** **GO chỉ được tuyên bố khi TẤT CẢ K ∈ {1,3,5,10,20} đều đạt**
   các cổng (1)–(7). Nếu **một** K đạt mà K khác không ⇒ **UNCONFIRMED (post-hoc)**, **KHÔNG áp dụng**.
4. **K=1 — ghi chú cơ học (khoá trước):** turnover mỗi chu kỳ ∈ {0; 1} (giữ coin cũ hoặc đổi hoàn toàn),
   nên cost drag **không** bị pha loãng; `w = 1` ⇒ phương sai chu kỳ lớn nhất ⇒ CI rộng nhất ⇒
   MDE80 có thể chạm trần lưới 0,50% (nếu vậy ghi `>0,50%` và **không** kết luận "có lực" giả tạo).
5. **Thứ tự đo + resume:** chạy **từng K một** (`TKR_KLIST` = 1, rồi 3, rồi 5,10,20), mỗi lần ghi
   báo cáo riêng vào **ngoài repo** (`/tmp/funding_topk_k13/report_K*.txt` + `summary_K*.json`), để nếu
   run sau lỗi thì các K đã xong **vẫn còn trên đĩa**. Grid (`mark_grid.npz`) dựng **1 lần**, có checkpoint.

## 4. Kết luận dự kiến + nhánh vô hiệu (ghi trước)

- **GO** chỉ khi **cả 5 K** đạt cổng (1)–(7) — xác suất gần 0 theo số vòng trước.
- **NO-GO** nếu CI chứa 0 hoặc net ≤ 0 sau chi phí, ở **mọi** K. Nhánh "1 K dương, K khác không" ⇒
  **UNCONFIRMED (post-hoc)**, không áp dụng.
- Nhánh vô hiệu: (i) neo MOM15 sai khớp >0,05pp; (ii) `n_elig < 50` ở đa số mốc; (iii) K=5/10/20 re-run
  lệch số đã công bố; (iv) lỗi cài đặt lộ ra ⇒ sửa **TRƯỚC khi chốt số** và ghi lại (tiền lệ vòng trước),
  nếu đã chốt số mới lộ ⇒ **VOID**.

## 5. Artifacts

- Script dùng lại **nguyên bản**: `research/analysis/funding_topk_rotate.py` (grid + neo MOM15),
  `research/analysis/funding_topk_rotate_stats.py` (**chỉ** thêm 2 biến môi trường `TKR_KLIST`, `TKR_KTESTS`
  + ghi `summary_K*.json`; **mặc định giữ nguyên** `5,10,20`/`K_test=3` ⇒ không đổi hành vi cũ).
- Trung gian ngoài repo: `/tmp/funding_topk_k13/` (resume được).
- Kết quả: `docs/RESULT_FUNDING_TOPK_K13.md` — bảng **đầy đủ K ∈ {1,3,5,10,20}** + turnover + cost drag +
  gross + null + MDE + cổng GO/NO-GO. Commit pre-reg + result. **KHÔNG push.**
