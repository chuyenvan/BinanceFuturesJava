# RESULT_EXECUTION_MAKER — maker (post-only) vs taker trên 1089 lệnh T170

Ngày: 2026-09-23. Pre-reg: `docs/prereg/PREREG_EXECUTION_MAKER.md` (**commit `e2eb646`**, chốt **TRƯỚC** khi
chạy; sau đó **không sửa thiết kế**). Script: `research/analysis/exec_maker_t170.py`.
**Thuần Python** — **không** Java trên Oracle (đang có job shadow), **không** `claude-run`/Claude Code,
**không push**, **không** chạm HOLDOUT 2026. Trung gian `/tmp/exec_maker/` (dọn sau khi commit).

---

## 0. KẾT LUẬN (đọc trước)

> **(1) Lợi ích của maker KHÔNG BỀN theo giả định slip.** Net/lệnh của kịch bản **B** (entry maker /
> exit taker) hơn **A** (taker thật) từ **+0,04pp** (nếu slip thật ≈ 1bp/chân) tới **+2,08pp** (nếu slip
> thật ≈ proxy biến động tại đúng phút khớp) — **cùng một dữ liệu, chỉ khác giả định slip**. ⇒ Không có
> một con số "maker lãi hơn X%" nào đáng tin; chỉ có **"hòa vốn ở p = ?"**.

> **(2) HÒA VỐN `p` (xác suất khớp maker) = 0,47 → 0,99** (mô hình i.i.d., biên TRÊN lạc quan), và
> **0,88 → 1,00** (mô hình adverse-selection, biên DƯỚI). Cực nhỏ của khoảng (0,35–0,47) đến từ **mốc
> slip "proxy biến động"** — mốc mà chính repo đã ghi là **KHÔNG phải slip thật** (đo biến động, không
> đo tác động). Ở **2 mốc slip thực tế hơn (p75 toàn cục 0,147%/chân và 1bp)** thì `p*_B = 0,96 → 0,99`
> ⇒ **phải khớp gần như 100% lệnh maker** mới không mất gì so với taker.

> **(3) "CHỈ ĐỔI THANG ĐO".** Ở 2 mốc slip thực tế, `win%` **không đổi** (88,2–88,3% cho cả A, B, C, sim
> 88,0%) và phân phối chỉ dịch chuyển đúng bằng phần fee (0,03–0,06pp/lệnh) ⇒ maker **không** cải thiện
> chất lượng mỗi lệnh, chỉ đổi **mức chi phí/độ lớn** — đúng bài học SIZING. Chỉ khi dùng mốc proxy biến
> động thì `win%` mới đổi (A 77,6% → B 86,0%), và đó là hệ quả của một **giả định slip sai bản chất**.
> **Không đề xuất chuyển sang maker.** Cần pre-reg riêng + dữ liệu fill thật (orderId/giá khớp) mới nói
> được gì thêm.

---

## 1. Cổng tự-kiểm (chạy trước mọi phép tính)

| Cổng | Kỳ vọng | Vòng này | Đạt |
|---|---|---|---|
| **G1** md5 `printDone.csv` | `efb793e2468ca3a7318da0f0ad23d4fc` | y hệt, n = **1089** | ✔ |
| **G2** `notional = quantity×entry` vs cột `margin` | < 1e−6 | **1,52e−07** | ✔ |
| **G3** tái tạo `net_sim`: `gross − 0,80 − funding` | = `100·pnl/notional` | **resid max 1,78e−15** (1089/1089) | ✔ |
| **G4** proxy slip đủ **cả 2 chân** (nến phút vào + phút ra) | 1089 | **1089/1089** (thiếu file 0, thiếu nến 0) | ✔ |
| **G5** không có dòng ≥ 2026 | 0 | **0** | ✔ |

**Chi phí thực của sim (đo lại trên dữ liệu):** `cost_actual = gross% − net%` có **median = 0,800000%**
(min **−21,7128%**, max **+2,1777%**); `funding = cost_actual − 0,80` ⇒ **mean −0,1209%/lệnh** (funding
là **khoản THU ròng**, khớp độ lớn con số +0,1209 đã công bố ở `RESULT_COST_LIQUIDITY.md` §4.4).
⇒ Xác nhận: sim trừ **0,80% phẳng + funding thật**, không phân biệt maker/taker, không co giãn theo biến động.

---

## 2. Proxy slip — và vì sao mốc "0,140%" của đề bài KHÔNG dùng được cho lệnh này

| Mốc đo | Giá trị |
|---|---|
| Proxy tại **đúng phút VÀO lệnh** (`0,5·(h−l)/c`) | mean **2,0476%** · median **1,1006%** |
| Proxy tại **đúng phút RA lệnh** | mean **1,2973%** · median **0,6338%** |
| Round-trip proxy tại 2 phút khớp | mean **3,3449%** · median **1,9099%** |
| **Toàn cục (đo lại §5 pre-reg)**: 358 coin, **7,30 M nến 1m** | p50 **0,0849%** · p75 **0,1466%** · p90 0,2447% · p95 0,3406% · p99 0,6864% |

- Mốc **"universe 0,140%/chân"** trong đề bài **khớp p75 của toàn bộ nến** (0,1466%) — tức là một mốc
  **nền thị trường**, **KHÔNG** phải slip của các lệnh này: nến vào lệnh là nến **được CHỌN vì biến động**
  ⇒ proxy tại đó **lớn hơn ~13×** (median 1,10% vs 0,085%). Đây là điểm phải nói rõ, không được lẫn 2 mốc.
- Vì proxy **đo biến động chứ không đo tác động** (`RESULT_COST_LIQUIDITY.md` §5.2: size ≈ 700–5 000 USDT
  trên coin 2e4–3e6 USDT/phút ⇒ impact thật **nhỏ hơn proxy nhiều**), kết quả được lặp ở **3 mốc**:
  `proxy` (biên cao), `universe 0,140%/chân` (trung), `1bp/chân` (biên thấp).

---

## 3. BẢNG CHÍNH — 3 kịch bản × 3 mốc slip (`p = 1,0`, không bỏ lệnh)

`net = gross − fee − slip − funding` (%/notional). **S** phải khớp sim (G3).

| Kịch bản | slip base | n | ΣNotional | **ΣNet (USDT)** | **meanP/notional** | agg (%/notional) | **win%** | chi phí/lệnh |
|---|---|---|---|---|---|---|---|---|
| **S** sim (0,80% RT) | proxy | 1089 | 2 016 019 | +76 070,2 | **+4,5647%** | +3,7733% | 88,0 | 0,6791% |
| **A** taker thật | proxy | 1089 | 2 016 019 | +32 277,8 | **+1,9198%** | +1,6011% | 77,6 | 3,3240% |
| **A** taker thật | universe | 1089 | 2 016 019 | +84 537,4 | **+4,9847%** | +4,1933% | 88,2 | 0,2591% |
| **A** taker thật | 1bp | 1089 | 2 016 019 | +89 779,1 | **+5,2447%** | +4,4533% | 88,3 | −0,0009% |
| **B** entry maker / exit taker | proxy | 1089 | 2 016 019 | +68 166,9 | **+3,9974%** | +3,3813% | 86,0 | 1,2464% |
| **B** entry maker / exit taker | universe | 1089 | 2 016 019 | +87 964,7 | **+5,1547%** | +4,3633% | 88,2 | 0,0891% |
| **B** entry maker / exit taker | 1bp | 1089 | 2 016 019 | +90 585,5 | **+5,2847%** | +4,4933% | 88,3 | −0,0409% |
| **C** cả hai maker (trần) | proxy | 1089 | 2 016 019 | +91 391,9 | **+5,3247%** | +4,5333% | 88,3 | −0,0809% |

CI95 block-72h (mô tả, 2000 rep) cho `meanP/notional`: S **+4,5647 [+3,3761, +5,7007]** ·
A/proxy **+1,9198 [+0,8533, +3,2118]** · A/universe **+4,9847 [+3,8237, +6,1741]** ·
A/1bp +5,2447 [+4,0406, +6,3611] · B/proxy **+3,9974 [+3,1665, +4,9860]** ·
B/universe **+5,1547 [+3,9997, +6,3496]** · B/1bp +5,2847 [+4,0977, +6,4675] ·
C/proxy **+5,3247 [+4,1383, +6,4849]**.

**Đọc bảng:**

- **Fee chỉ là 0,03–0,06pp/lệnh** giữa A/B/C ⇒ một mình phí **không** quyết định; **slip** quyết định.
  Ở mốc `1bp`, net A = +5,2447% **≈ đúng gross** (chi phí/lệnh ≈ 0) ⇒ sim **đắt hơn thực tế** phần lớn
  nằm ở **slip phẳng 0,30%/chân**, không ở `RATE_FEE`.
- **Ordering bất biến qua mọi mốc slip: C > B > A** ⇒ "maker tốt hơn taker" **đúng về dấu**, nhưng
  **độ lớn đổi 0,04pp → 2,08pp/lệnh tuỳ giả định**.
- **Δ(B − A) = +2,0776pp (proxy) · +0,1700pp (universe) · +0,0400pp (1bp)**; **Δ(C − B) = +1,3273pp
  (proxy) · +0,1700pp (universe) · +0,0400pp (1bp)**.
- **`win%` không đổi** ở 2 mốc thực tế (88,2 / 88,2 / 88,3 vs sim 88,0) ⇒ **chỉ đổi thang đo**.
  Ở mốc proxy, `win%` A tụt còn 77,6 chỉ vì cost 3,32%/lệnh ăn vào các lệnh gross nhỏ — hiệu ứng
  **của giả định slip**, không phải của cơ chế maker.

---

## 4. Quét `p` (xác suất khớp maker) — mô hình (i) i.i.d. vs (ii) adverse selection

**Chứng minh trước:** dưới mô hình (i) (khớp độc lập với kết quả lệnh), tập con còn lại **cùng phân
phối** với tập đầy đủ ⇒ `meanP`, `win%`, `chi phí/lệnh` **KHÔNG phụ thuộc `p`** (đúng cả về lý thuyết
lẫn số đo: B/proxy `meanP` dao động 3,97–4,09% quanh giá trị đầy đủ 3,997%, `win%` 85,7–86,2% quanh 86,0%).
⇒ **hòa vốn theo LỆNH là tầm thường** (B/C rẻ hơn A mỗi lệnh ở mọi `p`); **hòa vốn phải định nghĩa theo
TỔNG**: bỏ lệnh làm **mất lệnh**, nên `Σnet_B(p) = p·Σnet_B`.

| scn | slip | p | n còn lại | (i) ΣNet | (i) meanP | (i) win% | (ii) ΣNet | (ii) meanP | (ii) win% |
|---|---|---|---|---|---|---|---|---|---|
| B | proxy | 0,2 | ~218 | +13 299 | +4,04% | 85,7 | **−54 157** | −11,81% | 29,8 |
| B | proxy | 0,4 | ~436 | +26 912 | +4,09% | 86,2 | **−41 574** | −4,35% | 64,9 |
| B | proxy | 0,6 | ~653 | +40 613 | +3,97% | 86,0 | **−25 665** | −1,58% | 76,6 |
| B | proxy | 0,8 | ~871 | +54 477 | +3,98% | 85,9 | **−1 995** | +0,22% | 82,4 |
| B | proxy | 1,0 | 1089 | +68 167 | +4,00% | 86,0 | +68 167 | +4,00% | 86,0 |
| B | universe | 0,8 | ~871 | +70 192 | +5,14% | 88,3 | **+13 432** | +1,31% | 85,3 |
| B | 1bp | 0,8 | ~871 | +72 252 | +5,24% | 88,2 | **+15 559** | +1,44% | 85,4 |
| C | proxy | 0,2 | ~218 | +18 315 | +5,23% | 88,4 | **−46 895** | −9,55% | 41,7 |
| C | proxy | 0,8 | ~871 | +72 759 | +5,27% | 88,2 | **+16 213** | +1,48% | 85,4 |
| C | universe/1bp | 0,8 | ~871 | +72 607 / +73 027 | +5,30% | 88,3 | **+16 213** | +1,48% | 85,4 |

(i) i.i.d. R = 200, seed 20260923; (ii) adverse selection = `round(p·n)` lệnh **net xấu nhất trước**.
**Đọc:** mô hình (ii) là **điểm mấu chốt** — nếu lệnh maker chỉ khớp khi giá đi ngược (queue thật luôn
có adverse selection; pre-reg đã ghi không đo được `p` vì **không có dữ liệu L2**), thì ở `p = 0,8`
**tổng net của B/proxy = −1 995 USDT** (so với A +32 278) và của C = +16 213 (so A +32 278) ⇒ **thua A
rõ rệt**. Bảng đầy đủ ở `/tmp/exec_maker/report_exec.txt` (đã chép vào §4 này phần chính) và
`summary.json`.

---

## 5. ⛳ HÒA VỐN `p` (theo TỔNG — kết quả chính)

| Mốc slip | Σnet A | Σnet B | Σnet C | **p\*_B (iid)** | **p\*_C (iid)** | p\*_B (stress) | p\*_C (stress) |
|---|---|---|---|---|---|---|---|
| **proxy biến động** | +32 278 | +68 167 | +91 392 | **0,47** | **0,35** | 0,96 | 0,88 |
| **universe 0,140%/chân** | +84 537 | +87 965 | +91 392 | **0,96** | **0,92** | 1,00 | 1,00 |
| **1bp/chân** | +89 779 | +90 586 | +91 392 | **0,99** | **0,98** | 1,00 | 1,00 |

`p*_B = Σnet_A / Σnet_B` (mô hình i.i.d.); stress = `p` nhỏ nhất để tổng net của tập **xấu-nhất-trước**
≥ tổng net A.

**Đọc:** chỉ ở mốc proxy (mốc sai bản chất) mới có "dư địa" `p* ≈ 0,35–0,47`; ở **2 mốc slip thực tế
hơn**, hòa vốn đòi **`p ≥ 0,92–0,99`**, và nếu có **adverse selection** thì hòa vốn ≈ **1,00** (tức
gần như vô vọng). Với mốc `1bp`, **trần lợi ích của việc chuyển sang maker (C)** chỉ là
**+0,08pp/lệnh so với taker thật** (5,3247 − 5,2447) và **+0,76pp/lệnh so với sim** (5,3247 − 4,5647).

---

## 6. Trả lời thẳng câu hỏi + hạn chế

1. **Có đáng theo dõi sang maker không?** **Không có cơ sở để theo đuổi.** Lợi ích dao động
   **+0,04 → +2,08pp/lệnh** tuỳ giả định slip (chênh nhau **52×**), `win%` gần như không đổi ở mốc thực tế
   ⇒ đây là **đổi thang đo chi phí**, không phải cải thiện chất lượng. Thêm nữa, **`p` không đo được**
   và **adverse selection** (không mô hình hoá được) đẩy hòa vốn về **≈ 1,00**.
2. **Hạn chế (bắt buộc ghi):**
   - **`p` là GIẢ ĐỊNH QUÉT**, không phải số đo — repo **không có** order book/L2, không có `orderId`
     hay giá khớp thật. Mọi kết luận về maker **đứng trên giả định** này.
   - **Proxy slip = biến động, KHÔNG phải tác động thị trường**; impact thật (phụ thuộc size 700–5 000 USDT)
     thường **nhỏ hơn proxy nhiều** ⇒ mốc `proxy` là **biên trên**, kết luận phải đọc theo cả 3 mốc.
   - **Adverse selection** bị bỏ qua ở mô hình chính (i); mô hình (ii) chỉ là **biên dưới thô** theo thứ
     tự net xấu-nhất-trước, không mô phỏng queue/partial fill.
   - **Một run duy nhất** (`X1_GS_T170_2021`), N = 1089 lệnh; funding giữ **nguyên** từ sim; giả định
     maker khớp **nguyên khối** (không partial), và lệnh bỏ đi **không được thay thế** bằng lệnh khác.
   - Không mô hình hoá: phí funding áp trên qty khớp **muộn hơn**, phí maker có thể bị hạ bậc (VIP),
     rebate, hoặc **taker bị từ chối post-only** (khi đó entry **thành taker** — trường hợp này
     **không** được tính, làm B/C **lạc quan hơn** thực tế).
3. **Không tự ý đề xuất áp dụng**, không tune. Mọi thay đổi cần pre-reg riêng + dữ liệu fill thật
   (`orderId` + giá khớp) + xác nhận live.

---

## 7. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_EXECUTION_MAKER.md` | pre-reg, commit **`e2eb646`** |
| `research/analysis/exec_maker_t170.py` | counterfactual thuần Python (gates + 3 kịch bản + quét `p` + hòa vốn) |
| `docs/result/RESULT_EXECUTION_MAKER.md` | file này |
| `/tmp/exec_maker/` | `report_exec.txt` (bảng đầy đủ), `summary.json` — **dọn sau khi commit** |

**Commit (pre-reg `e2eb646` + commit kết quả), KHÔNG push.**
