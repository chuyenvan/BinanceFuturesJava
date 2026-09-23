# RESULT_LIMIT_ENTRY — test entry LIMIT 15' (fill-or-fail) trên C1 = REVERSAL-BOUNCE

Ngày: 2026-09-23. Pre-reg: `docs/PREREG_LIMIT_ENTRY.md` (**commit `493c02f`, chốt TRƯỚC khi chạy**, không sửa thiết kế sau đó).
Script: `research/analysis/limit_entry.py`. Trung gian: `/home/ubuntu/claudedata/limit_entry/`
(`report.txt`, `summary.json`, `run.log` — giữ; **`events_d00.npz`/`events_d00015.npz` đã dọn sau commit**, tái tạo bằng script).

**Tuân thủ:** thuần Python (0-sim) · **không** Java trên Oracle (shadow đang chạy) · **không** `claude-run`/Claude Code
· **không push** · **không chạm 2026** (mọi cửa sổ `< 2026-01-01`). Nguồn 1m: `raw/*.f32` (627 symbol, nến đã đóng);
funding: Aerospike `funding_data` (read-only, cache `fund_cache.npz` của Phần 1).

---

## 0. KẾT LUẬN NGẮN

> **KHÔNG LẬT ĐƯỢC.** Entry LIMIT có **tỉ lệ khớp rất cao** (δ=0: **98,60%**) và **cải thiện net một cách cơ học
> (+0,31…+0,48 pp/lệnh)** — nhưng phần cải thiện **≈90% KHÔNG phải đo được**: nó là do **bỏ số hạng "slip entry"
> của mô hình** (0,276–0,296 pp) cộng **fee 0,03 pp**; **adverse selection là thật và rất lớn** (nhóm khớp xấu hơn
> nhóm không-khớp **0,85–1,30 pp** tính từ chính giá tín hiệu). Trên **DEV**, net(B) = **−0,0115%** (δ=0) /
> **−0,0017%** (δ=0,15%) ⇒ **≤ 0**; **CI72h×1,21 đều chứa 0**; **2022 và 2025 âm** ⇒ **trượt cổng §2.6**.
> Ngay cả **trần trên nhân tạo C (slip = 0)** cũng chỉ **+0,1413% trên DEV, CI chứa 0**.

**Bằng chứng gate (harness có lực):**
- `A0` (**tái lập nguyên bản** `RESULT_REVERSAL_BOUNCE`, template `fee 0,10 + slip@signal + funding`):
  **ALL = +0,0027%** (đã đăng **+0,003%**) và **DEV cũ 2022-01..2024-06 = −0,0798%** (đã đăng **−0,080%**) ⇒ **khớp**.
- Tập fire tái tạo **đúng số đã đăng**: **3.785.409** fire dùng được (624 symbol) — **trùng khít**.

| | δ = 0 (limit tại `p0`) | δ = 0,15% (limit tại `p0×0,9985`) |
|---|---|---|
| **Tỉ lệ khớp ALL / DEV** | **98,60% / 98,63%** | **82,26% / 81,96%** |
| Thời gian khớp (offset phút) | median **1**, 96,2% khớp ngay nến 1 | median 1, p90 7, 52,8% nến 1 |
| **AS1** (khớp − fail, tính từ giá tín hiệu) | **−1,3010 pp** | **−0,8498 pp** |
| **DEV net(B)** (limit entry + market exit) | **−0,0115%** | **−0,0017%** |
| **DEV net(C)** (slip = 0, trần trên) | **+0,1413%** (CI chứa 0) | **+0,1565%** (CI chứa 0) |

**Cổng §2.6 (5 điều kiện, KHOÁ trước):** (a) `DEV net(B) > 0` → **KHÔNG** (âm ở cả 2 δ);
(b) `CI72h×1,21` ngoài 0 → **KHÔNG** (chứa 0 ở mọi hàng, kể cả C); (c) `|Δ| ≥ MDE80` → **KHÔNG** (δ=0: 0,3063 < 0,4043;
δ=0,15%: 0,4761 > 0,4131 nhưng chỉ so với A1); (d) ≥60% năm dương + 2025 không âm → **KHÔNG** (2022, 2025 âm);
(e) win% không sụp → **CÓ** (46,2% vs 44,5%). ⇒ **4/5 điều kiện trượt ⇒ NO FLIP.**
**Dù có đạt**: đây vẫn là **POST-HOC** (đổi mô hình chi phí sau khi đã biết gross/net cũ) ⇒ chỉ là **ứng viên forward**.

---

## 1. Thiết kế đã chốt + cổng tái lập

- **Ứng viên C1 = REVERSAL-BOUNCE**, trigger **nguyên bản** (`DROP_THRESH=0.01`, mốc `%15==14`, `max15/max30`,
  `priceReverse=open[j−14]`, fire tại nến đầu `close[t]>priceReverse`, **HOLD 24h**), exit = nến có mặt cuối cùng
  trong `(fire, fire+1440]`. Chọn C1 vì **đúng tiêu chí "gross>0, net≤0"** đã đo trước
  (`RESULT_REVERSAL_BOUNCE`: raw +0,31%, net ALL +0,003%, DEV −0,080%).
- **C2 = BIG_UP: KHÔNG CHẠY.** Lý do (theo đúng §2.1 pre-reg): (i) BIG_UP **không đạt tiêu chí chọn**
  (`RESULT_BIGUP_MEDIUPDOWN`: **DEV net +0,87% > 0**); (ii) pre-reg chỉ cho chạy C2 "nếu ngân sách cho phép" và
  yêu cầu **ghi rõ lý do nếu không chạy** — đã ghi. **Không** thay bằng ứng viên khác, **không** hạ tiêu chí.
- **Mô hình entry (causal):** tại nến tín hiệu `f` (đã đóng), đặt limit `L = p0 = close[f]` (δ=0) hoặc `p0×0,9985` (δ=0,15%).
  Xét nến `f+1..f+15`: nếu `min(low) ≤ L` ⇒ **KHỚP** tại nến khớp **đầu tiên**, giá khớp **= L**, phí **maker**;
  nếu không chạm ⇒ **FAIL ⇒ BỎ LỆNH**. **Exit luôn MARKET** (luôn khớp) ⇒ **fee taker + slip đầy đủ**; **không**
  mô hình hoá "tỉ lệ khớp khi exit" (§2.2 pre-reg).
- **4 hàng chi phí:** `A0` = tái lập bản đăng (fee 0,10% + slip@**nến tín hiệu** + funding); `A1` = market/market
  **đối xứng** (fee 0,10% + slip@entry + slip@exit + funding); `B` = **limit entry + market exit** (maker 0,02% +
  taker 0,05% + slip@exit + funding từ **nến khớp**); `C` = B với **slip = 0** (trần trên).
- **GATE:** A0 phải khớp số đã đăng ⇒ **khớp** (+0,0027% / −0,0798% so với +0,003% / −0,080%).

---

## 2. Tỉ lệ khớp & ADVERSE SELECTION (đo từ GIÁ KHỚP, tách 2 nhóm)

| δ | Tỉ lệ khớp | nhóm **KHỚP**: E[raw\|khop] | nhóm **FAIL**: E[raw\|fail] | **AS1** | AS2 (cơ học của δ) |
|---|---|---|---|---|---|
| **0** | **98,60%** (n=3.732.405) | +0,2924% (med **−0,2879%**, win 48,0%) | **+1,5934%** (med +0,9635%, win 56,4%) | **−1,3010 pp** | +0,0000 pp |
| **0,15%** | **82,26%** (n=3.113.990) | +0,1599% (med **−0,4525%**, win 46,9%) | **+1,0096%** (med +0,4580%, win 53,4%) | **−0,8498 pp** | +0,1505 pp |

**Đọc (đây là cơ chế, không phải phụ lục):** `raw` ở đây là **`C[exit]/p0 − 1` cho CẢ HAI nhóm** (thước đo chung),
nên **AS1 < 0** nghĩa là **những lệnh KHỚP được chọn đúng là những lệnh vốn dĩ xấu hơn** (giá đã đi ngược đủ để
chạm limit rồi không hồi phục) — còn **nhóm không khớp (0,4–1,8% số fire) là nhóm chạy thẳng lên** (+1,01…+1,59%).
Ở δ=0 (đặt đúng `p0`), **96,2% số lệnh khớp ngay nến kế tiếp** ⇒ gần như **mọi** fire đều khớp, nhưng **nhóm 1,4%
không khớp lại là nhóm lãi nhất** — chính là "bỏ lệnh thắng, giữ lệnh thua".
Mọi chỉ tiêu của B/C đều tính **từ giá khớp `L`** (§2.4 pre-reg), **không** từ `p0`.

---

## 3. Bảng 3 mức (đơn vị **%/lệnh**; `meanNet = meanP`; CI = **block-72h**, `N_blk` ALL 609 / DEV 487)

### δ = 0 (limit tại `p0`)

| Hàng (tập mẫu) | N | meanNet | win% | CI72h ×1,0 | **CI72h ×1,21** | p(>0) | MDE80 (2,8×sd) |
|---|---|---|---|---|---|---|---|
| **A0** baseline đăng (toàn bộ fire) | 3.785.409 | **+0,0027** | 46,1 | [−0,2521, +0,2516] | [−0,3021, +0,3074] | 0,513 | 0,3734 |
| A1 market/market (toàn bộ fire) | 3.785.409 | −0,1898 | 45,4 | [−0,4476, +0,0555] | [−0,4942, +0,1146] | 0,069 | 0,3773 |
| A1 market/market (tập khớp) | 3.732.405 | −0,2089 | 45,3 | [−0,4670, +0,0355] | [−0,5129, +0,0951] | 0,050 | 0,3770 |
| **(ii) B limit entry + market exit** | 3.732.405 | **+0,0974** | 46,8 | [−0,1579, +0,3453] | [−0,2070, +0,4018] | 0,763 | 0,3723 |
| **(iii) C = B, slip=0 (trần trên)** | 3.732.405 | **+0,2566** | 47,6 | **[+0,0020, +0,5031]** | [−0,0466, +0,5597] | 0,977 | 0,3725 |
| **DEV A0** | 3.186.700 | −0,1082 | 45,5 | [−0,3824, +0,1864] | [−0,4523, +0,2359] | 0,214 | 0,4043 |
| DEV A1 (toàn bộ fire) | 3.186.700 | −0,3188 | 44,7 | [−0,5972, −0,0250] | [−0,6650, +0,0273] | 0,017 | 0,4079 |
| DEV A1 (tập khớp) | 3.143.118 | −0,3367 | 44,5 | [−0,6134, −0,0435] | [−0,6814, +0,0081] | 0,014 | 0,4078 |
| **DEV (ii) B** | 3.143.118 | **−0,0115** | 46,2 | [−0,2878, +0,2799] | **[−0,3550, +0,3319]** | 0,475 | 0,4028 |
| **DEV (iii) C** | 3.143.118 | +0,1413 | 47,0 | [−0,1360, +0,4341] | [−0,2036, +0,4861] | 0,845 | 0,4029 |

### δ = 0,15% (limit tại `p0×0,9985`)

| Hàng (tập mẫu) | N | meanNet | win% | CI72h ×1,0 | **CI72h ×1,21** | p(>0) | MDE80 |
|---|---|---|---|---|---|---|---|
| A1 market/market (tập khớp) | 3.113.990 | −0,3595 | 44,2 | [−0,6244, −0,1086] | [−0,6716, −0,0475] | 0,002 | 0,3885 |
| **(ii) B limit entry + market exit** | 3.113.990 | **+0,1166** | 46,8 | [−0,1468, +0,3653] | [−0,1933, +0,4264] | 0,800 | 0,3809 |
| **(iii) C = B, slip=0** | 3.113.990 | **+0,2809** | 47,6 | **[+0,0204, +0,5292]** | [−0,0269, +0,5887] | 0,983 | 0,3812 |
| **DEV (ii) B** | 2.611.844 | **−0,0017** | 46,1 | [−0,2872, +0,2954] | **[−0,3541, +0,3508]** | 0,504 | 0,4131 |
| **DEV (iii) C** | 2.611.844 | +0,1565 | 46,9 | [−0,1297, +0,4527] | [−0,1958, +0,5089] | 0,864 | 0,4132 |

**Null test** (block sign-flip 72h, seed 20260905, NREP=2000): mọi hàng có `null sd ≈ 0,133–0,151%` và `p(≥obs)`
từ 0,02 (C) đến 0,93 (A1) ⇒ **C là hàng duy nhất có p thấp (0,021–0,027)**, nhưng **C là trần trên nhân tạo** và
**vẫn trượt CI×1,21 + trượt DEV**. **Dấu theo năm** (δ=0, B, tập khớp): 2021 **+0,68** | 2022 **−0,33** | 2023 +0,26 |
2024 +0,29 | 2025 **−0,15** ⇒ **không nhất quán dấu** (δ=0,15%: +0,73 / −0,35 / +0,27 / +0,29 / −0,13 — y hệt).

---

## 4. Phân rã: "cải thiện" đến từ đâu? (B − A1 trên **cùng tập khớp**)

| δ | B − A1 | AS2 (giá khớp tốt hơn) | fee tiết kiệm (0,10%→0,07%) | **slip entry bỏ được** | funding |
|---|---|---|---|---|---|
| 0 | **+0,3063 pp** | +0,0000 | **+0,0300** | **+0,2764** | −0,0000 |
| 0,15% | **+0,4761 pp** | +0,1505 | **+0,0300** | **+0,2957** | −0,0000 |

- **Fee taker→maker chỉ đáng +0,03 pp** — **nhỏ hơn MDE80 (0,38–0,41 pp) 13 lần**. Tự nó **không lật được gì**.
- **~90% "cải thiện" là BỎ SỐ HẠNG SLIP ENTRY CỦA MÔ HÌNH** (0,276–0,296 pp). Đây **là INPUT của mô hình, không phải
  phép đo**: audit đã ghi rõ sim **không** mô hình spread/impact (`RESULT_COST_REAL_AUDIT` §2.2b: giá khớp sim =
  close nến, sai số 0,0000%) và `slip 0,30%/chân` trong sim **là hằng số cộng thêm**; proxy biến động tại nến =
  **0,276 pp** (entry). Nói cách khác: **kết quả "lật hay không" phụ thuộc giả định slip entry có thật hay không —
  và ta KHÔNG đo được nó** (không có fill thật). Vì vậy hàng **B không được coi là bằng chứng**.
- `C − B` = **+0,159…+0,164 pp** = đóng góp của **slip exit** — cũng là một số hạng mô hình tương tự.
- **AS2 = +0,1505 pp** (δ=0,15%) = "được mua rẻ 0,15%" — **cơ học**, đúng bằng δ, **không** phải edge; và nó **đã
  bị trả giá** bởi **AS1 = −0,85 pp** ở nhóm khớp.

---

## 5. Cổng kết luận (§2.6 pre-reg, áp cho cả 2 δ)

| # | Điều kiện | δ=0 | δ=0,15% |
|---|---|---|---|
| a | `DEV net(B) > 0` | −0,0115 ⇒ **KHÔNG** | −0,0017 ⇒ **KHÔNG** |
| b | `CI72h×1,21` ngoài 0 | [−0,355, +0,332] ⇒ **KHÔNG** | [−0,354, +0,351] ⇒ **KHÔNG** |
| c | `|Δ| ≥ MDE80` | 0,3063 < 0,4028 ⇒ **KHÔNG** | 0,4761 > 0,4131 ⇒ CÓ (chỉ vs A1) |
| d | ≥60% năm dương & 2025 không âm | 2022, 2025 âm ⇒ **KHÔNG** | idem ⇒ **KHÔNG** |
| e | win% không sụp | 46,2 vs 44,5 ⇒ CÓ | 46,1 vs 44,2 ⇒ CÓ |
| | **⇒ KẾT LUẬN** | **KHÔNG LẬT ĐƯỢC** | **KHÔNG LẬT ĐƯỢC** |

**Trả lời câu hỏi gốc:** cơ chế limit-entry **không** biến ứng viên "gross dương / net ≤ 0" thành alpha;
nó **dịch net về ≈ 0** (DEV: −0,319 → −0,012), tức **đưa về hoà vốn**, và tuyệt đại phần dịch chuyển đó là
**giả định slip**. Đây là **"đổi thang đo"**, khớp kết luận `RESULT_EXECUTION_MAKER` (win% gần như không đổi,
cần khớp ~96–100% mới trung tính) — ở đây **δ=0 khớp 98,6%** nhưng vẫn **chỉ về ~0**, vì phần "lợi" bị
**adverse selection** (AS1 −1,30 pp) ăn lại và vì **slip exit** (0,159 pp) vẫn còn.

---

## 6. Giới hạn (nói rõ, không tô hồng)

1. **Không có dữ liệu fill thật** (242 store chỉ có `REQUEST`; không `orderId`/`commission`/`executedQty`)
   ⇒ **giá khớp limit là giả định lý tưởng** ("chạm limit là khớp đủ, không hàng đợi, không partial fill").
   Đây là **biên LẠC QUAN** cho khối lượng, và **không đo được** tỉ lệ khớp thực.
2. **Adverse selection chỉ đo được theo cách "within-sample"** (2 nhóm khớp/fail trên cùng thước raw từ `p0`);
   không mô hình hoá được **tác động giá** của chính lệnh mình (impact) hay **thứ tự ưu tiên hàng đợi**.
3. **Số hạng slip là mô hình, không phải đo** (điểm 4 mục §4) ⇒ B/C **không** đủ để kết luận về "execution thật".
4. Kết quả **không ổn định theo năm** (2022/2025 âm) và **không** vượt MDE ở δ=0.
5. `meanP` trong bảng = **mean net/lệnh** (các lệnh cùng notional trong harness này) ⇒ đọc như
   *%/lệnh*, không phải %/vốn-danh-mục.
6. Chỉ **1 ứng viên** được chạy (C1); C2 không chạy (§1). ⇒ kết luận **giới hạn trong họ trigger reversal-bounce**.

---

## 7. SẢN PHẨM

| File | Nội dung |
|---|---|
| `docs/PREREG_LIMIT_ENTRY.md` | chốt trước (commit `493c02f`) |
| `docs/RESULT_LIMIT_ENTRY.md` | file này |
| `docs/RESULT_FUNDING_SIGN.md` | Phần 1 (funding) |
| `research/analysis/limit_entry.py` | script (thuần Python, chỉ đọc; `LE_STATS_ONLY=1` để chạy lại phần thống kê từ npz) |
| `research/analysis/funding_sign_reconcile.py` | script Phần 1 |
| `/home/ubuntu/claudedata/limit_entry/` | `report.txt`, `summary.json`, `run.log` (ngoài repo). **`events_*.npz` (250 MB) đã dọn sau commit** để lấy chỗ đĩa — tái tạo được bằng `python3 research/analysis/limit_entry.py` (~4 phút) |
