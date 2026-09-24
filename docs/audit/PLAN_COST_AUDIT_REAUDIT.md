# PLAN_COST_AUDIT_REAUDIT — Kế hoạch audit lại chi phí (Phase A–E)

Ngày lập: 2026-09-23. Trạng thái: **kế hoạch** (viết TRƯỚC khi đo; Phase A/B thực thi ngay sau).
Phạm vi lần này = **Phase A + Phase B**. Phase C/D/E ghi ở đây để định hướng, **chưa làm**.

**Ràng buộc đã tuân thủ:** thuần Python · **không** Java trên Oracle (shadow đang chạy) ·
**không** `claude-run`/Claude Code · **không push** · 242 **CHỈ ĐỌC** (ssh `-i ~/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.242`)
· **không** chạm HOLDOUT 2026 (mốc dữ liệu ≤ 2025-12-31) · pre-reg/định nghĩa chỉ số chốt TRƯỚC khi đọc số.

---

## 0. VẤN ĐỀ

1. **Sim đắt hơn thực tế.** Sim trừ **0,800000% round-trip** phẳng cho mọi lệnh
   (`RATE_FEE` 0,002 ×**1 chân** `Configs.java:103` + `SLIPPAGE_RATE` 0,003 ×**2 chân** `Configs.java:117`;
   đã kiểm chứng đóng kín **1089/1089** lệnh ở `RESULT_COST_LIQUIDITY.md` §4.2 và `RESULT_EXECUTION_MAKER.md` G3).
   Thực tế Binance USDⓈ-M: **maker 0,02% / taker 0,05% mỗi chân** ⇒ sim **đắt ~8× (taker) / ~20× (maker)**
   ở riêng phần **phí**; phần **slip 0,60% flat** còn đắt hơn nữa vì không co giãn theo thanh khoản.
2. **Funding có thể là THU, không phải chi.** `calTp()` trừ `funding` theo dữ liệu Aerospike;
   đo lại trên 1089 lệnh cho **mean −0,1209%/lệnh** (âm = **được thu**) — đã ghi ở
   `RESULT_COST_LIQUIDITY.md` §4.2/§4.4 và `RESULT_EXECUTION_MAKER.md` G3.
   ⇒ Nếu phần lớn lệnh **NHẬN** funding, mô hình 0,8% + funding của sim là **bảo thủ kép**.
3. **Hệ quả owner nêu:** hạ phí + đưa funding về đúng dấu có thể **lật** nhiều kết luận **NULL** thành **có alpha**.
   **Nhưng** chỉ đúng với **một nhóm test nhất định** — đây là điểm phải phân biệt trước khi nói gì.

---

## 1. HAI NHÓM TEST — KHÁC NHAU VỀ BẢN CHẤT CHI PHÍ (đọc kỹ, đừng gộp)

### (i) NHÓM **SIM-based** — `pnl` trong `printDone` **đã trừ 0,8%** ⇒ **CÓ KHẢ NĂNG bị lật**

Các test đọc **`pnl` của `printDone.csv`/`OrderTestDone.data`** (tức `net = gross − 0,80% − funding`), hoặc
các biến thể chạy CÙNG jar/profile có `SIM_RATE_FEE`/`SIM_SLIPPAGE_RATE` **không đặt**
(⇒ dùng default 0,002/0,003):

| Test | Nhóm |
|---|---|
| GATEDYN (gate A/B), GATEDYN2 | SIM-based |
| SELECTOR_LEG_CUT / selcut | SIM-based |
| TICK_BLOCK (DEPTH/DROP15M/BREADTH) | SIM-based |
| DCA (`DCA_*`: SIGNAL_GATE, ROUND_CAP, MORELEGS, AGG_PERCOIN, HOLDDCA, GATEWIDEN) | SIM-based |
| D3D4_FILTER | SIM-based |
| Neo MOM15 (M-LEVEL / P-COIN) | SIM-based (harness có fee riêng – xem dưới) |

Với nhóm này: nếu chi phí thật chỉ **0,04–0,10%** + funding **đúng dấu**, thì `net` **tăng ~0,7–0,76%/lệnh**.
Vì phần lớn test này có `mean` gross lớn hơn chi phí rất nhiều (T170 `c* = +5,244%`, selector `+4,221%`,
BIG_DOWN `+4,786%`), **hạ phí KHÔNG tạo alpha mới ở nhóm này — nó chỉ làm cái đã dương dương hơn**.
Việc "lật" chỉ có ý nghĩa với các biến thể **sát 0** (ví dụ chân bị cắt làm net về ~0); **chưa đo được
biến thể nào như vậy** ⇒ đây là **giả thuyết cần kiểm ở Phase D**, không phải kết luận.

### (ii) NHÓM **SCREENING** — harness **KHÔNG** dùng 0,8% ⇒ **KHÔNG lật được**

Các study chạy bằng **harness Python** (không phải `printDone`), chi phí harness = **0,10% RT
(taker 0,05%×2) + slip proxy 0,5×(high−low) + funding** (hoặc biến thể 0,05/0,15% để kiểm độ nhạy):

| Test | Chi phí harness | `c*` (chi phí tối đa còn hòa vốn) | Kết luận hiện có |
|---|---|---|---|
| FUNDING_TOPK_ROTATE (K=5/10/20) | 0,10% + slip + funding | **−0,046%** (K=20) → **−0,122%** (K=5) | NO-GO |
| RANGE4H_TOPK (K=1/3/5/10) | 0,10% + slip + funding | **−0,325%** (K=10) | NO-GO |
| REVERSAL_BOUNCE | 0,10% + slip + funding | (edge ≤ 0 OOS) | NO-GO |
| OI_STUDY (H1/H2/H3) | 0,10% + slip + funding | (toàn decile net âm) | NO-GO/NULL |
| BIG_UP / MEDIUM_UP / MEDIUM_DOWN (+ M-LEVEL) | 0,05/0,10/0,15% | 0/27 ô vượt ngưỡng | UNCONFIRMED |

**Các nhóm này ĐÃ đo `c*` ÂM** ⇒ kết luận **độc lập với mức phí**: kể cả **phí = 0** thì `net = gross`
vẫn **âm** (nút thắt là **slip × turnover**, không phải phí exchange). ⇒ **hạ phí KHÔNG cứu được**;
"lật" các nhóm này là **bất khả** trừ khi `slip` thật **nhỏ hơn nhiều** so với proxy — và đó là
giả định **chưa có bằng chứng** (xem §4 rủi ro).

**Tóm tắt 1 dòng:** hạ phí về thực tế là cần thiết cho **đúng đắn của thước đo**, nhưng **không tự sinh alpha**:
nhóm SIM-based dương sẵn (hạ phí chỉ tăng độ lớn), nhóm SCREENING âm sẵn vì `c* < 0` (hạ phí vô nghiệm).

---

## 2. NĂM PHASE

### Phase A — TRÍCH DỮ LIỆU CHI PHÍ THẬT (làm ngay)
Tìm & kiểm kê **mọi nguồn có thể chứa chi phí/mức khớp thật**:
- `printOrder.csv` (đề bài nêu) — tìm ở Oracle (`find /home/ubuntu -maxdepth 5`) và 242 (chỉ đọc).
- log khop lenh: `OrderTestDone.data`, `printDone.csv`, `BalanceIndex.data`, `java/devrun/*/storage/`,
  `/home/ubuntu/shadow_c3/**` (ledger/open_positions/logs), 242 `/home/chuyennd/java/{v_t_m,shadow_c3}/**`.
- đếm **thực nghiệm** xem có trường `orderId` / `commission` / `FILLED` / `executedQty` không (grep log).
**Xuất:** bảng "file nào tồn tại · cột gì · bao nhiêu dòng · khoảng thời gian". **Không có thì báo RÕ.**

### Phase B — ĐO PHÂN BỐ CHI PHÍ THẬT (làm ngay, trên dữ liệu Phase A)
- **fee/leg**: maker vs taker nếu log phân biệt được; nếu **không có** ⇒ nói rõ "không đo được", chỉ nêu mốc tham chiếu.
- **slip/leg**: **giá ý định (`entry`) vs giá khớp** — dùng nến `kline_1m_opt`/`raw/*.f32` tại đúng phút khớp.
  Không có giá khớp thật ⇒ dùng **proxy `0,5·(h−l)/c`** và **dán nhãn là proxy biến động**, không phải tác động.
- **funding/leg**: **funding THẬT** trong cửa sổ giữ lệnh bằng Aerospike `funding_data`
  (đã xác minh: ~831 symbol, 2,395 M event, cadence 4h/8h, 2021-01 → 2026-08). **Báo CẢ DẤU**:
  % lệnh **THU** funding, % **TRẢ**, mean/median %/lệnh.
- **tỉ lệ khớp khi đặt limit**: tính từ trạng thái order (NEW/FILLED/CANCELED) **nếu có**;
  không có ⇒ báo rõ + nêu con số `p*` đã công bố (biên lý thuyết, không phải đo).
- **đối chiếu gross → net** ở 3 mức chi phí: (a) sim 0,80%, (b) phí thật + slip đo được, (c) phí thật + slip = 0.

### Phase C — MODEL MỚI + VALIDATE (chưa làm)
Dựng bộ chi phí mới: `fee ∈ {maker 0,02%, taker 0,05%}/chân` × `slip(thanh khoản, size)` + `funding` thật.
**Bắt buộc pre-reg** trước khi đo; phải tái tạo được số cũ (đóng kín) **và** cho ra số mới trên **cùng 1089 lệnh**
(kiểm: `net_new − net_sim = 0,80% − fee_new − slip_new + Δfunding` phải khớp tới 1e−9).
Không có bước này thì mọi "lật" chỉ là đổi thước đo.

### Phase D — RA LẠI NHÓM SIM-BASED (chưa làm)
Chạy lại **đúng các test trong bảng §1(i)** với model mới, **cùng code, cùng seed, cùng ngưỡng**, chỉ đổi
chi phí. Chỉ những biến thể có `net_sim ≈ 0` mới có khả năng **đổi dấu**; nhóm đã dương đậm thì chỉ **đổi độ lớn**.

### Phase E — KẾT LUẬN (chưa làm)
- Mọi "lật" tìm được ở Phase D là **POST-HOC** ⇒ **phải forward** (paper/shadow) mới được coi là alpha.
- Model mới **phải** pre-reg + áp dụng **nhất quán** cho **mọi** kết luận cũ (nếu không, ta tự tạo survivorship).
- Ngưỡng: một thay đổi chi phí **không** được coi là "khám phá" — nó là **sửa thước đo**.

---

## 3. RỦI RO & QUY TẮC CHỐNG TỰ LỪA (ghi trước)

1. **Log live 2026 = bằng chứng FORWARD, KHÔNG phải "mở seal holdout".** Không được dùng nó để **tune**.
   Chỉ được dùng để **mô tả** cơ chế/chi phí. Mọi tham số học từ đây ⇒ phải pre-reg lại.
2. **Đổi model chi phí = đổi chuẩn đo.** Hai bảng số (cũ 0,8% / mới ~0,04–0,10%) **không so sánh trực tiếp**
   như hai "thí nghiệm"; chúng là **hai thước đo**. Cấm chọn cái cho kết quả đẹp.
3. **Không có fill thật ⇒ không đo được slip thật.** Proxy `0,5·(h−l)/c` đo **biến động**, **không đo tác động**
   (tác động ∝ size/thanh khoản). Dùng nó làm "slip thực" là **sai bản chất** (đã ghi ở `RESULT_COST_LIQUIDITY.md` §4.5).
4. **`c*` ÂM là kết luận phí-độc-lập**: 2 ứng viên quay vòng chết vì `slip×turnover`; đổi phí không có tác dụng.
5. **Không tune tham số hệ thống** trong lần audit này (chỉ đọc/đo; sửa code = việc khác, phải pre-reg riêng).

---

## 4. SẢN PHẨM KỲ VỌNG LẦN NÀY

| File | Nội dung |
|---|---|
| `docs/audit/PLAN_COST_AUDIT_REAUDIT.md` | file này (kế hoạch, viết trước) |
| `docs/result/RESULT_COST_REAL_AUDIT.md` | Phase A + Phase B (inventory + phân bố fee/slip/funding-limit + gross→net) |
| `research/analysis/cost_real_audit.py` | script tái tạo Phase A/B (thuần Python, đọc dữ liệu đã có) |
| `/tmp/cost_real_audit/` | trung gian — **dọn sau khi commit** |

**Giới hạn phạm vi:** lần này **KHÔNG** sửa code sim, **KHÔNG** chạy lại test nào, **KHÔNG** push.
