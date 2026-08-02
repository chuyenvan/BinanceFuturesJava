# SPEC — 2 tín hiệu vào, chung một cách quản lý, DCA CÓ TRẦN (2026-08-01, CHỜ UNI DUYỆT)

> Trạng thái: **BẢN THẢO ĐỂ DUYỆT. CHƯA CODE, CHƯA CHẠY.**
> **Sửa framing (2026-08-01 tối):** bản trước đóng khung việc này là "momentum vs mean-reversion mâu
> thuẫn". Uni phản biện đúng: **không mâu thuẫn.** Đây là **2 tín hiệu vào ĐỘC LẬP** dùng **chung một
> cách quản lý**. Vấn đề thật không phải chọn hướng — mà là hệ **thiếu một đơn vị rủi ro**. Đơn vị rủi
> ro đó là **trần cỡ cược mỗi cụm, KHÔNG phải lệnh cắt lỗ.** Toàn bộ spec viết lại theo mô hình này.

## 0. Mô hình đúng (chốt bởi Uni)

**Hai tín hiệu vào, độc lập:**
- **Sleeve BIG_DOWN** — cả thị trường sập mạnh → tỉ lệ hồi cao → mua bắt đáy.
- **Sleeve selector** — model chấm coin sắp pump (nhãn maxFav ≥ +6%) → mua theo.

**Một cách quản lý, chung cho cả hai:**
- **Đúng (giá lên)** → trailing nuôi lãi, cố giữ đuôi.
- **Sai (giá xuống)** → KHÔNG cắt, DCA nhồi cho rẻ trung bình, chờ hồi. "Trước sau gì cũng hồi" là
  luận điểm nền — với coin không delist.
- **Delist** → chấp nhận mất. Đây là trường-hợp-mất DUY NHẤT.

Đây là thiết kế hợp lệ. Cái sai KHÔNG nằm ở việc trộn hai tư duy.

## 0.1 Chỗ DUY NHẤT còn thiếu — đơn vị rủi ro

Toàn bộ mô hình đứng trên câu "trước sau gì cũng hồi". Đúng với coin sống. Vấn đề: **chưa chặn được
cái giá của lần "không hồi" (delist).** Vì DCA hiện **không có trần số leg** (và `BIG_DOWN` còn bỏ qua
thang chặn margin, `isAll=true`), một cụm có thể nhồi vô hạn → khi delist, mất **không giới hạn**.

Ba hệ quả — CÙNG một lỗ hổng, không phải ba lỗi:

| # | Hệ quả | Bằng chứng |
|---|---|---|
| 1 | **Không tính được lời/lỗ ròng.** Thắng cho +X qua trailing, delist cho −(bao nhiêu leg). Leg không trần ⇒ mất khi delist không giới hạn ⇒ không so được asymmetry. | Sweep 2 ngày ra Spearman train↔holdout **0.14** — kết quả bị đuôi delist chi phối, không phải tham số |
| 2 | **"Tỉ lệ hồi cao" đo trên kẻ sống sót.** Coin nằm luôn / delist biến khỏi thống kê. | Handoff: "97.4% hồi vốn là ảo" (SurvivorProbe survivorship bias) |
| 3 | **Selector mù đường xuống.** Train trên nhãn +6% (chỉ nhìn phần LÊN) ⇒ không biết coin rớt sâu bao nhiêu trước khi hồi, hay có hồi không. | nhãn maxFav ≥ +6% |

**Sửa mà KHÔNG đụng triết lý "không cắt" — ĐƯỜNG LAI (Uni chốt 2026-08-01 tối):** đơn vị rủi ro =
**trần vốn mỗi cụm**, thực thi bằng một **"phao" cắt rất sâu, chỉ arm SAU khi đã nhồi hết leg**.

- Nhồi `N=4` leg (0/−5/−10/−15% so `firstEntryPrice`). Suốt vùng này **KHÔNG cắt** — giữ, chờ hồi.
- Chỉ khi **đã rót hết 4 leg** mà giá **vẫn** cắm xuống tới **phao** (độ sâu `F`) thì mới cắt cả cụm.
- Size tính ngược từ `R` và `F` sao cho **cắt ở phao mất đúng R%**. Delist (gap xuyên phao) ≈ mất R%.

Vẫn không cắt ở gần hết trường hợp (coin dao động trong vùng trước phao thì không đụng gì). Chỉ can
thiệp đúng cái đuôi hiện đang không được chặn. Số tiền tệ nhất một cụm mất = **biết trước** ⇒ tính
được ⇒ học được.

**⚠️ `F` (độ sâu phao) là con số quan trọng nhất và phải ĐO, không đoán.** MAE của chính hệ: p50=−56%,
p75=−70%. Đặt phao nông hơn vùng dip bình thường sẽ cắt nhầm coin đáng lẽ hồi. Phao đúng nằm ở chỗ
**xác suất hồi rơi khỏi vách** theo đường "hồi-theo-độ-sâu" (khử survivorship) — đo bằng `SurvivalProbe`.

---

## 1. Bất biến — chốt TRƯỚC, không sweep

Ràng buộc thiết kế, đặt bằng lý lẽ rủi ro/chi phí, KHÔNG phải tham số đem tối ưu.

| # | Bất biến | Giá trị đề xuất | Lý do |
|---|---|---|---|
| I1 | **Rủi ro tối đa mỗi cụm** `R` | **1% vốn** | Cụm tệ nhất (delist) không được làm hỏng tháng. 40 cụm × 1% = trần lý thuyết 40%, khớp maxDD quan sát ~30% |
| I2 | **Trần số leg mỗi cụm** `N` | **4** | Tới leg 4 thì DỪNG NHỒI — **không cắt**, vẫn giữ. Phao chỉ arm SAU leg 4 |
| I3 | **Đơn vị rủi ro = phao cắt sâu, arm sau leg 4** | bắt buộc | Đường lai: không cắt suốt vùng nhồi; chỉ cắt cả cụm khi đã hết leg mà giá vẫn thủng phao `F`. `HARD_SL_PCT` (đo trên `firstEntryPrice`, bất biến qua DCA) làm đúng cái phao — chỉ cần gate "arm sau leg 4" |
| I4 | **Sizing suy ra, không chọn** | `Σwᵢ = R / F` | `F` = độ sâu phao (nơi thật sự cắt). Cắt ở phao mất đúng R. Sizing là HỆ QUẢ của R và F, không phải lựa chọn |
| I5 | **Time-stop cho cụm** | có (48h) | Thesis hết hạn → nhả vốn. Đo từ `clusterFirstLegTime` (KHÔNG phải leg cuối, nếu không mỗi DCA reset đồng hồ) |
| I6 | **Exit theo ĐƯỜNG ĐI** (sửa từ bản trước) | xem §1.1 | Cụm chưa DCA (thesis đúng ngay) → **trailing** nuôi đuôi. Cụm đã DCA (rescued) → **TP cố định** thoát nhẹ nhàng |

> Chú thích `S` (I4): đây KHÔNG phải giá cắt. Nó là mức sụt dùng để **định cỡ** — chọn `S` = biên
> delist/worst-case bạn muốn phòng. `R=1%`, `S=15%` ⇒ tổng notional cụm = 6.7% vốn ⇒ 3 leg đều ⇒
> mỗi leg 2.2% vốn. Nếu coi delist = mất TOÀN BỘ vốn cụm thì đặt `S=100%` ⇒ tổng cụm ≤ 1% (bảo thủ
> hơn nhiều). **Cần Uni chốt `S` phản ánh khẩu vị nào** (xem §6 câu 2b).

### 1.1 Exit — sửa lớn so với bản trước

Bản trước ghi "KHÔNG trailing". **Sai** — Uni muốn giữ trailing cho lệnh thắng. Sửa: exit theo đường đi.

- **Cụm thắng ngay (chưa từng DCA):** trailing nuôi đuôi. Nhưng **trailing hiện đang cắt non đuôi** —
  `gap = min(đỉnh × tỉ lệ, TS_MAX_GAP=8%)`: trần 8% tuyệt đối bám sát đỉnh khi lãi lớn ⇒ một nhịp
  chỉnh 8% bình thường của crypto là cắt ở +40%, bỏ lỡ cú x3. **Sửa:** `gap = max(đỉnh × tỉ lệ, sàn)`
  (cờ `TS_GIVEBACK_FLOOR`, đã code) — nhả theo % đỉnh, có sàn cho lãi nhỏ ⇒ đuôi có chỗ thở.
- **Cụm rescued (đã DCA rồi hồi):** chốt lời cố định `avgEntry × (1+p)`, `p` nhỏ. Đã lỗ rồi được cứu
  thì thoát nhẹ, không tham. Trailing một cụm vừa suýt chết là mời nó chết lại.

---

## 2. Vòng đời một cụm

```
leg 1  : tín hiệu vào (BIG_DOWN hoặc selector)     → size w1
leg 2  : giá về  −d1%  so firstEntryPrice          → size w2
leg 3  : giá về  −d2%  so firstEntryPrice          → size w3
TRẦN   : hết leg N=3 → DỪNG NHỒI (không cắt, vẫn giữ)
TP     : giá hồi  avgEntry × (1 + p%)              → chốt cả cụm (đường rescued)
TRAIL  : nếu cụm CHƯA DCA → trailing nuôi đuôi     → chốt khi SL trail chạm
TIME   : quá T giờ từ leg 1 chưa TP/thoát          → nhả ở giá thị trường
DELIST : chấp nhận mất = tổng đã rót (đã chặn = R%)
```

**Ràng buộc tự nhất quán (giảm không gian tìm kiếm):**
- `0 < d1 < d2 < S` — nhồi nằm gọn trong vùng định cỡ
- `S ≥ d2 + biên` (biên ≥ ⅓ khoảng `d2`)
- `w1 + w2 + w3 = R / S` — I4
- `p > 0.8%` chi phí round-trip

⇒ Tự do thực tế chỉ còn **`d1, d2, S, p` (+ T)** — `w` suy ra. Không gian nhỏ ⇒ overfit thấp.

**Giá trị khởi điểm (đặt bằng lý lẽ, chưa sweep):** `d1=−5% · d2=−10% · S=−15% · p=+3% · T=48h ·
ladder 1:1:1`.

---

## 3. Hai sleeve — cả hai đều giữ, KHÔNG chọn một

Bản trước hỏi "chọn A/B/C cho tín hiệu vào". Sửa: **giữ cả hai sleeve** (đúng ý Uni — 2 tín hiệu độc
lập). Chúng chia nhau vòng đời §2. Câu hỏi còn lại chỉ về **selector**:

Selector train nhãn maxFav ≥ +6% = dự đoán pump, **mù đường xuống** (§0.1 hệ quả 3). Nó vẫn dùng tốt
làm tín hiệu vào cho sleeve của nó, nhưng nếu muốn nó cũng "biết sợ đường xuống" thì **re-label** theo
triple-barrier khớp spec (chạm +p% trước hay −S% trước, trong T giờ). Đây là **nâng cấp tùy chọn, làm
SAU**, không chặn gì:

| | Cách | Khi nào |
|---|---|---|
| Mặc định | Giữ selector nguyên như hiện tại làm tín hiệu sleeve selector | ngay |
| Nâng cấp | Re-label selector theo triple-barrier khớp §2 (train lại 17-fold WF) | chỉ sau khi S0-S1 cho thấy khung có edge |

BIG_DOWN đã là tín hiệu độc lập sẵn có trong code — test được NGAY, không phụ thuộc model.

---

## 4. Thước đo — chốt TRƯỚC khi chạy

Không dùng PnL thô (bị beta thị trường 2021-2026 chi phối). Bốn số:

1. **PnL / R** — lãi theo bội số đơn vị rủi ro. Giờ mới tính được, vì đã có `R`.
2. **PnL vượt beta** — so mua-và-giữ rổ coin cùng kỳ, cùng vốn. Tách kỹ năng khỏi thị trường.
3. **`ddPctMtm`** (KHÔNG `ddPct` — nó mù với tham số exit; xem INFRA_FACTS).
4. **Tỉ lệ fold thắng** (sign test) — không phải tổng, vì tổng dễ bị 1-2 fold kéo (w15).

**Riêng cho phần trailing** (đo tách): **tỉ lệ giữ được so với đỉnh** = `lãi lúc thoát / lãi đỉnh`
trên nhóm THẮNG. Đây là số bắt trực tiếp bệnh "cắt non đuôi", không cần đi qua fitness harness.

**Kỉ luật chống overfit (áp từ đầu):** giữ holdout 2024H2-2026H1 chưa chạm tới lần chấm cuối; báo số
cấu hình đã thử; báo Spearman train↔holdout — nếu ~0 thì kết luận "không học được, giữ mặc định",
KHÔNG tuyên bố giá trị tối ưu.

---

## 5. Thứ tự thực thi

| bước | việc | gate dừng |
|---|---|---|
| **M0** | **[HARNESS-FREE, làm NGAY]** A/B đo cơ chế trên window có lệnh: (a) trailing `TS_GIVEBACK_FLOOR` off vs on → tỉ lệ giữ/đỉnh; (b) DCA off vs cũ vs grid-có-trần → PnL/maxDD/held | nếu grid-có-trần KHÔNG hạ maxDD/held mà giữ PnL ⇒ trần chưa đúng |
| **S0** | Đóng khung đầy đủ: bật trần vốn cụm theo I1-I4, exit theo đường đi §1.1. Chạy **1 cấu hình** (giá trị khởi điểm) | PnL/R < 0 trên train ⇒ dừng, hình mẫu sai |
| **S1** | A/B `WFO_DISABLE_DCA=1` — DCA có khung **có hơn** không-DCA không? | không hơn ⇒ bỏ DCA, chỉ giữ trailing |
| **S2** | Sweep hẹp `d1,d2,S,p` ±1 bậc, **chỉ trên train** | báo Spearman; ~0 ⇒ giữ mặc định |
| **S3** | Chấm **một lần** trên holdout | pre-register ngưỡng trước khi nhìn |
| **S4** | Nếu S1-S3 qua: mới xét re-label selector (§3 nâng cấp) | — |

**M0 làm được NGAY với code hiện có** (cờ `TS_GIVEBACK_FLOOR`, `WFO_DISABLE_DCA`, `DCA_GRID_SCALAR`
đều đã code). Nó không cần sửa harness — đọc raw PnL/maxDD/held, bỏ qua verdict pass/fail. S0 cần code
thêm sizing theo I4 (trần vốn cụm) + exit-theo-đường-đi.

---

## 6. Cần Uni chốt trước khi code S0

1. **Exit theo đường đi** (§1.1): cụm chưa-DCA trailing, cụm rescued TP cố định — đúng ý không?
2. **`R` = 1% vốn/cụm** hợp khẩu vị rủi ro không?
3. **Giá trị khởi điểm** `d1=−5 d2=−10 d3=−15 p=+3 T=48h`, ladder khởi điểm 1:1:1:1 — duyệt hay sửa?

> **Đã chốt (2026-08-01 tối):** đường lai · N=4 leg · phao cắt chỉ arm sau leg 4 · cả hai sleeve GIỮ.
> **Đang ĐO, không chọn:** `F` (độ sâu phao) — từ đường hồi-theo-độ-sâu của `SurvivalProbe`.
