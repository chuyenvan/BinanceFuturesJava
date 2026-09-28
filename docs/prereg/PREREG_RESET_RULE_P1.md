# PREREG_RESET_RULE_P1 — CHẤM LẠI HẬU KIỂM ARTIFACT CÓ SẴN theo LUẬT 4 TẦNG (D2, 0 sim)

**Chốt TRƯỚC khi tính số.** Ngày: 2026-09-28. Nhánh `module`. Nguồn yêu cầu:
`Claude outputs/PLAN_OPENCLAW_BASELINE_RESET_20260928.md` §3 (luật 4 tầng) + `PLAN_OPENCLAW_ADDENDUM_20260928.md` §D2.
Chi phí mới: `docs/result/RESULT_COST_TRUTH.md` (commit `d059cc3`) ⇒ `base 0,112` / `stress 0,150` / `legacy 0,800` (%/vòng).

Ràng buộc cứng: **offline Python, 0 sim / 0 train** · giữ box Oracle nhẹ · KHÔNG chạm production/`242`/ONNX/LIVE ·
KHÔNG push file dữ liệu · **DEV ≤ 2025-12-31** (không chạm 2026 = HOLDOUT) · output nhỏ.

---

## 0. MỤC ĐÍCH (1 câu)

Chấm lại **một lượt, không sim**, các artifact sim ĐÃ CÓ trên đĩa dưới **luật 4 tầng** ở **hai mức chi phí**
`base` và `stress`, để (i) xác nhận luật chạy được, (ii) đối chiếu dự báo MASTER ghi trước, (iii) đo xem
**hạ phí 0,8 → 0,112 %/vòng có làm lật verdict "nhiều lệnh = rác"** hay không.

> Đây là **hậu kiểm mô tả (post-hoc re-scoring)**, KHÔNG phải một round thí nghiệm mới, KHÔNG chạy sim,
> KHÔNG đổi cấu hình. Mọi số là **mô tả quá khứ DEV**, không phải cam kết forward.

---

## 1. ĐỐI TƯỢNG (khoá trước — 20 artifact, GỒM mốc `B*`)

Đường dẫn artifact: `P` = `/home/ubuntu/kaggle_sim/out/<tag>`; `B*` dùng
`/home/ubuntu/java/devrun/FG_KEEPLEG0` (đã kiểm **byte-identical** với `P/kg0-g170`, md5 `99e42b75`).

| # | tag | vị trí | cấu hình (từ `prof_run.properties`) | n leg (đã kiểm tồn tại) |
|---|---|---|---|---|
| 0 | **`FG_KEEPLEG0` / `kg0-g170`** = **`B*`** | devrun / out | KEEPLEG0, nhịp **1'**, gate 1.70, K=8 | 1 085 |
| 1 | `cd-sel15` | out | KEEPLEG0 + **`SIM_ENTRY_SAMPLE_MIN=15`**, K=8 | 744 |
| 2 | `sc-b1` | out | nền sel15, `SIM_F_BASE=0.015` (×0,5), K=8 | 745 |
| 3 | `sc-b2` | out | nền sel15, ×0,5, **K=16** | 1 152 |
| 4 | `sc-b3` | out | nền sel15, `SIM_F_BASE=0.0075` (×0,25), **K=32** | 1 885 |
| 5 | `sc-b4` | out | nền sel15, ×0,5, **K=32** | 1 878 |
| 6 | `kg0-g155` | out | KEEPLEG0 1', `SIM_GATE_DYN_SCALE=1.55` | 1 245 |
| 7 | `kg0-g140` | out | KEEPLEG0 1', scale 1.40 | 1 411 |
| 8 | `kg0-g125` | out | KEEPLEG0 1', scale 1.25 | 1 701 |
| 9 | `gs2-t155` | out | nền **T170**, scale 1.55 (gatescale v2) | 1 249 |
| 10 | `gs2-t140` | out | nền T170, scale 1.40 | 1 416 |
| 11 | `gs2-t125` | out | nền T170, scale 1.25 | 1 708 |
| 12 | `cc-t100` | out | T100 + `CONC_CAP_PERCOIN` ON (blocked 44) | 2 557 |
| 13 | `gr-kg0-q995` | out | KEEPLEG0 + `SIM_GATE_P15_Q=0.995` | 1 021 |
| 14 | `gr-kg0-q998` | out | KEEPLEG0 + `SIM_GATE_P15_Q=0.998` | 954 |
| 15 | `gr-kg0-q999` | out | KEEPLEG0 + `SIM_GATE_P15_Q=0.999` | 868 |
| 16 | `gr-kg0-q998-15m` | out | như #14 + **`SIM_ENTRY_SAMPLE_MIN=15`** (nhịp 15') | 420 |
| 17 | `rc-a-q995` | out | KEEPLEG0 + 15' + `P15_Q=0.995` + `DYN_SCALE=0.001` (gate MỞ) | 3 256 |
| 18 | `rc-a-q998` | out | như #17, `Q=0.998` | 1 875 |
| 19 | `rc-a-q999` | out | như #17, `Q=0.999` | 1 297 |

`rc-a-*` là **phương án A của `PREREG_GATE_ROOTCAUSE`** (KEEPLEG0 + `SAMPLE_MIN=15` + `P15_Q=Q` + `DYN_SCALE≈0`).
`gs2-*` là gatescale v2 trên **nền T170** (khác nền với `kg0-g*`).

**Thiếu artifact ⇒ ghi rõ "thiếu artifact"**, KHÔNG bịa số. **Thiếu ticker 1m cho một tag ⇒ ghi
"KHÔNG CHẤM ĐƯỢC" ở tầng cần MTM phút, KHÔNG thay bằng daily.**

---

## 2. CÔNG THỨC HẬU KIỂM CHI PHÍ (khai RÕ là XẤP XỈ)

Sim trừ **flat `0,8 %/vòng`**; chi phí ĐO đúng là `base 0,112` / `stress 0,150` (%/vòng).
Hậu kiểm **từng leg** (`margin == quantity·entry` — đã kiểm `ratio = 1,0000` trên 100 % leg, đánh **1x**):

```
net_pnl_leg(c) = pnl_sim_leg + (0,008 − c) · margin_leg          # c ∈ {0,00112 ; 0,00150} (phân số)
```

- **XẤP XỈ, bỏ qua compounding**: dùng chênh TUYẾN TÍNH trên từng leg, KHÔNG chạy lại sim, KHÔNG tái
  tính sizing/throttle. Vì vậy `equity`, `CAGR`, `maxDD`, `q*`, episode… ở mức phí mới là **ước lượng**.
- `margin_leg` = `notional_leg` (1x, đã kiểm). Hệ số hiệu chỉnh: `base` **+0,688 %** · `stress` **+0,650 %** notional/leg.
- **LƯU Ý CẤU TRÚC (khai TRƯỚC):** cột `profit` trong `printDone.csv` là **return giá (%)**, KHÔNG chứa phí
  (đã kiểm: `profit = (exit−entry)/entry` khớp từng leg; ví dụ `cd-sel15` leg-1 `(0,09519−0,14562)/0,14562 = −34,63 % = profit`).
  ⇒ **Tầng 3 (`win%`, `TSloss%`, `mP|SM%`, `mP|SL%` tính trên `profit` %) KHÔNG phụ thuộc chi phí** ⇒
  kết quả tầng 3 ở `base` và `stress` **sẽ giống hệt**; tầng 3 vẫn được tính & báo cáo đầy đủ.

---

## 3. CÔNG CỤ & ĐỊNH NGHĨA (khoá trước)

Một script dùng chung: **`research/analysis/reset_rule_score.py`** (offline, không `print()` — dùng `logging`).

| đại lượng | định nghĩa / nguồn |
|---|---|
| `n` | số leg = số dòng `printDone.csv` (parse `on_bad_lines=skip`) |
| equity / CAGR / maxDD **daily** | chuỗi equity NGÀY của artifact (`sim.out` `b + unP`), khuôn `c3_rates.py`; CAGR = `(E_last/E_first)^(1/(năm))−1` |
| `q*` | bỏ `q %` leg TỐT NHẤT (giảm dần) đến khi Σ còn lại ≤ 0 ⇒ `100·(i+1)/n` trên `pnl` (USDT), khuôn `size_count_score.tail()` |
| `%PnL top-1 %` | `100 · Σ(k1 leg tốt nhất) / Σpnl`, `k1 = max(1, ceil(0,01n))` |
| **episode** | ngày CÓ lệnh; nối 2 ngày có lệnh khi khoảng trống **≤ 2 ngày** (diff ngày > 2 ⇒ cắt episode); ΣPnL theo episode |
| `conc/coin` | `max_t Σ margin(coin)/equity(t)` — khuôn `size_count_score.gross()` (equity ngày) |
| `gross` | `max_t Σ margin(mọi vị thế mở)/equity(t)` |
| `qmin` | quý xấu nhất (%) theo chuỗi equity ngày (khuôn `c3_rates.stats`, `q0` = đỉnh quý trước) |
| `0 năm âm` | mọi năm dương (%) |
| **MTM phút** | tái tạo `equity_min = 35 000 + realized(m) + unP(m)` từ ticker **1 phút** (`/home/ubuntu/kaggle_data_hpo`, `priceClose`), khuôn `intraday_dd.py`: `realized` cộng dồn `pnl` tại **phút kết thúc leg**, `unP = Σ q·(close − entry)`; ca GMT+7 → trừ 7 h; ffill/bfill; symbol không có dữ liệu ⇒ **đếm là thiếu, không bịa** |
| `maxDD MTM phút` | `min(s/cummax(s) − 1)` trên chuỗi phút — báo **toàn kỳ** và **từng năm** (tầng 1 dùng **năm xấu nhất**) |
| `UW` | số ngày dài nhất liên tục dưới đỉnh chạy, trên chuỗi **phút** (`/1440`) |
| `Calmar_MTM` | `CAGR / |maxDD MTM phút toàn kỳ|` |

**Seed / bootstrap (khoá):** `SEED = 20260905`, `NREP = 2000`, block `72 h`, paired theo khối.
**Hệ số nở CI:** `inflate(k) = sqrt(2·ln k)` với **`k = 19`** (số ỨNG VIÊN so với `B*`; `B*` không tính)
⇒ `inflate = 2,4264`.

---

## 4. LUẬT 4 TẦNG (chốt trước, y nguyên PLAN §3)

- **TẦNG 1 — RÀO RỦI RO** (đo trên MTM phút + equity hậu kiểm): maxDD MTM phút **năm xấu nhất ≤ 40 %** ·
  `UW ≤ 250` ngày · quý xấu nhất **≥ −20 %** · **0 năm âm** · `conc/coin ≤ 15 %` · `gross ≤ 70 %`.
- **TẦNG 2 — RÀO ĐỘ BỀN** (thay (a)/(b′)): `q* ≥ 15 %` · `%PnL top-1 % ≤ 25 %` ·
  **bỏ top-3 EPISODE** ⇒ ΣPnL còn lại **> 0**.
- **TẦNG 3 — NON-INFERIORITY vs `B*`** (trên `profit` %, CI block-72h, 2000 rep, seed `20260905`, `inflate(19)`):
  `win%` không kém quá **−2,0 pp** · `TSloss%` không tệ quá **+2,5 pp** · `mP|SM%` và `mP|SL%` **không tệ ngoài CI**
  (kém có ý nghĩa ⇔ CI hiệu `(ứng viên − B*)` nằm HOÀN TOÀN < 0). **KHÔNG** tính `meanP` (trùng đại số).
- **TẦNG 4 — MỤC TIÊU (điểm, không đòi significance)**: `Calmar_MTM ≥ B*` **VÀ** `n ≥ 1,3 × n(B*)` **VÀ**
  `conc/coin ≤ conc/coin(B*)`.

`B*` = `FG_KEEPLEG0` (nhịp 1', `CONC_CAP 15 %`, md5 kỳ vọng `99e42b75`). Tầng 3 của `B*` vs chính nó = 0 (PASS hiển nhiên);
tầng 4 của `B*` là **mốc tham chiếu**, không tự chấm.

**Lật verdict?** định nghĩa: một đối tượng **đổi trạng thái tổng** (PASS↔FAIL) khi chuyển mức phí từ `legacy 0,800`
→ `base 0,112` (và báo thêm `stress`). Đếm **số đối tượng đổi trang thái** ở tầng 2 và tầng 4 (2 tầng nhạy phí).

---

## 5. TỰ KIỂM BẮT BUỘC (cổng DỪNG)

Script phải tái tạo đúng số ĐÃ CÔNG BỐ (mức phí `legacy` = nguyên trạng artifact):

| đối tượng | n | equity | CAGR % | maxDD daily % | q* % | %top-1 % | nguồn |
|---|---|---|---|---|---|---|---|
| `FG_KEEPLEG0` | 1 085 | 103 083 | +27,14 | −11,21 | 19,0 | 23,74 | `PLAN…RESET` §1.1 · `RESULT_GATESCALE_KEEPLEG0` §147 · `RESULT_TAIL50…` §1 |
| `cd-sel15` | 744 | 71 718 | +17,29 | −6,27 | 21,2 | 19,13 | `RESULT_SIM_CADENCE_MATCH` §3 · `RESULT_SIZE_COUNT` §1 |

Dung sai: `n`/`equity` tuyệt đối ≤ 1 đơn vị; CAGR/`maxDD`/`q*`/`%top-1` ≤ **±0,15 pp** (các số công bố có làm tròn).
**Thêm cổng cứng:** `md5(printDone)` phải = `99e42b75` (`B*`) và `13171916…` (`cd-sel15`).
**Thêm cổng MTM:** tái tạo MTM phút `KEEPLEG0` phải khớp `RESULT_INTRADAY_DD` §3: maxDD phút toàn kỳ **−19,96 %**, `UW ≈ 147,2` ngày
(dung sai ≤ 0,2 pp / ≤ 1 ngày). **Lệch ⇒ DỪNG, sửa trước khi chấm tiếp.**

---

## 6. DỰ BÁO GHI TRƯỚC (để đối chiếu, KHÔNG được sửa sau)

1. `B*` **qua tầng 1–2** (đã biết: MTM phút −19,96 % < 40 %; `q* = 19,0 % ≥ 15`; `%top-1 = 23,74 % ≤ 25`;
   `conc 7,12 % ≤ 15`; 0 năm âm).
2. **gate-loosened FAIL tầng 3**: `kg0-g155/g140/g125` + `gs2-t1xx` — win% kém / TSloss% tệ hơn `B*`
   ngoài CI (theo `RESULT_GATESCALE_SWEEP`).
3. **`sc-b2` qua tầng 1–3 nhưng tầng 4 kém `B*`** (nhịp 15' ⇒ `n = 1 152` chỉ ≈ **1,06× < 1,3×**, Calmar thấp).
4. **`rc-a-*` thất bại tầng 1** (UW 568–773 ≫ 250, `qmin` −13…−23).
5. **Hạ phí làm "nhiều lệnh" BỚT xấu** (q*/tail dương lên, Calmar tăng) nhưng **không cứu** được
   các arm mà trần là **UW/nhịp** hay `%top-1` ⇒ verdict "gate-loosened = rác" **vẫn FAIL tầng 3** (do tầng 3
   không phụ thuộc phí).

---

## 7. OUTPUT

`docs/prereg/PREREG_RESET_RULE_P1.md` (file này) · `research/analysis/reset_rule_score.py` ·
`docs/result/RESULT_RESET_RULE_P1.md` + `docs/result/reset_rule_p1.json`. Commit + push (chỉ file nhỏ; KHÔNG push dữ liệu).
