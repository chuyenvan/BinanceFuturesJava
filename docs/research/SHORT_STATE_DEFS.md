# SHORT_STATE_DEFS — CƠ SỞ (paper + dữ liệu thật) cho định nghĩa STATE short

Ngày: **2026-10-01/02**, branch `module`. Đây là **cơ sở** cho `RESULT_SHORT_STATE` (owner: *"tôi chỉ có
cảm nhận trực quan, không có số liệu, không có cơ sở"* ⇒ tài liệu này cung cấp **paper + số data thật**).

Dữ liệu thật: `CLOSES_1H.bin` (daily close, DEV ≤ 2025-12-31) · tier notional (`/tmp/short_state_tier.parquet`,
mẫu 14 ngày) · script `research/analysis/short_state_defs.py` · số: `research/analysis/out/short_state_defs.json`.

---

## 1. PAPER (abstract đã đọc qua OpenAlex/arXiv)

| # | Paper | DOI | Ý chính (abstract) dùng cho định nghĩa |
|---|---|---|---|
| P1 | Kamps & Kleinberg 2018, "To the moon" | 10.1186/s40163-018-0093-5 | đề xuất **tiêu chí định nghĩa P&D**; tín hiệu anomaly trong order/trade; **P&D tụ vào một số sàn & coin nhất định** |
| P2 | Victor & Gerharts 2019 ICDMW | 10.1109/icdmw.2019.00045 | **149 sự kiện** Binance; P&D hay xảy ra ở coin **mcap < $50M**; **giá bị bơm phồng DUY TRÌ dài hơn** |
| P3 | La Morgia et al. 2022, "Doge of Wall Street" | 10.1145/3561300 | ~**900 sự kiện / >3 năm**; phát hiện P&D trong **25 giây**; nhiều coin **thanh khoản thấp, dễ bị thao túng** |
| P4 | Xu & Livshits 2019 (arXiv 1811.10109) | 10.48550/arXiv.1811.10109 | **412** P&D Telegram; model dự báo **xác suất pump trước khi pump** |
| P5 | Hamrick et al. 2021 | 10.1016/j.ipm.2021.102506 | khảo sát **hệ sinh thái P&D** (no abstract) |
| P6 | **Zaremba et al. 2021** short-term reversal | 10.1016/j.irfa.2021.101908 | **reversal theo "last-day return"**, do **illiquidity**; **các coin LỚN nhất (tradeable) lại MOMENTUM, không reversal** ⇒ **hành vi khác nhau theo tier** |
| P7 | Ozdamar et al. 2021 MAX effect | 10.1186/s40854-021-00291-9 | **MAX effect DƯƠNG**: high-MAX − low-MAX = **+3,03 %/tuần** (raw), +1,99 % (risk-adj) ⇒ **pump gần đây tiếp tục tăng ngắn hạn** |
| P8 | Grobys et al. 2021 lottery demand | 10.1016/j.intfin.2021.101289 | lottery-like demand: chênh MAX quintile **> 1,50 %/tuần** ⇒ **đừng short coin vừa pump** |
| P9 | **Dobrynskaya 2023** momentum/reversal | 10.3905/jai.2023.1.189 | **momentum ≤ 2–4 tuần**, **reversal > 1 tháng** ("faster metabolism of crypto") ⇒ **up-leg ngắn, bleed dài** |
| P10 | Long et al. 2020 seasonality | 10.1016/j.frl.2020.101566 | seasonality cross-section (bối cảnh) |
| P11 | Ardia et al. 2018 MS-GARCH | 10.1016/j.ribaf.2018.12.009 | **cần regime-switching** (không 1 GARCH tĩnh) ⇒ hợp lý hoá **state/regime** |
| P12 | Soska et al. 2021 BitMEX | 10.1145/3442381.3450059 | derivative/liquidation (tới 100×) **gây biến động mạnh giá spot** ⇒ tail có cơ chế |
| P13 | BenSaïda et al. 2021 regime spillover | 10.1186/s40854-020-00210-4 | **MS-VARX 18 coin**: spillover **khác nhau ở regime vol thấp / cao**, **bùng mạnh ở regime vol cao** (COVID) ⇒ hợp lý hoá **state theo vol** (B cần vol thấp/xả) |
| P14 | Kavya 2026 stop-loss density | 10.2139/ssrn.7293038 | **lý thuyết ngưỡng cascade thanh lý** (preprint 2026, **không abstract**) ⇒ cơ chế đuôi +10 % = cụm stop/liquidation |

## 2. DỮ LIỆU THẬT — PHÂN BỐ THỜI LƯỢNG CHU KỲ (daily, ZigZag θ=25%)

538 coin có ≥120 ngày; 6 207 up-leg + 6 052 bleed-leg. Đơn vị: **ngày**.

| tập | up-leg median | up p75 | up p90 | **bleed median** | bleed p75 | bleed p90 | up-ret median | bleed-ret median |
|---|---|---|---|---|---|---|---|---|
| ALL | **18** | 35 | 54 | **24** | 45 | 79 | **+53,9 %** | **−42,2 %** |
| big-alt (notional ≥ p70) | 21 | 40 | 62 | 24 | 48 | 83 | +55,4 % | −40,8 % |
| rac (notional ≤ p30) | **15** | 31 | 50 | **23** | 43 | 72 | +52,7 % | −43,2 % |

**Kết luận data (đo được):**
1. **Up-leg NGẮN hơn bleed-leg ở MỌI tier** (median 18 vs 24 ngày; p90 54 vs 79) ⇒ **thesis owner ĐÚNG**:
   bơm **nhanh** (+54 % trong ~18 ngày), **xả chậm/dài** (24+ ngày). Khớp P9 (momentum ≤2–4 tuần, reversal >1 tháng).
2. **rac bơm NHANH hơn big-alt** (up median 15 vs 21 ngày) và bleed tương đương (~23–24) ⇒ "alt rác":
   up ngắn + xả dài — **đúng mô tả owner**; nhưng **đuôi pump của rac cũng dữ hơn** (khớp P2/P3: coin nhỏ,
   thanh khoản thấp dễ bơm/xả).

## 3. ĐỊNH NGHĨA STATE (ngưỡng LẤY TỪ SỐ ĐO, không bịa)

Chu kỳ đo: up median **18 ngày**, up-ret median **+54 %**; bleed median **24 ngày**.

### STATE A — "gương thanh khoản" (pump/momentum) ⇒ **AVOID cho short**
- Điều kiện ex-ante: **`pump_age_d ≤ 18`** (trong/ngay sau up-leg, ngưỡng = median up-leg) **HOẶC
  `ret7 ≥ +50 %`** (≈ median up-ret của 1 leg) [tuỳ chọn: `vol_decay > 1`].
- Cơ sở: **P7/P8** (MAX effect DƯƠNG → pump còn tăng) · **P9** (momentum ≤2–4 tuần) · **P2/P3** (coin nhỏ,
  thanh khoản thấp, giá bơm "duy trì") ⇒ short vào đây dính **đuôi +10 %**. Vai trò = **đuôi rủi ro**, không vào.

### STATE B — "xả dần" (bleed) ⇒ **ứng viên short**
- Điều kiện ex-ante: **`pump_age_d > 18`** (đã qua uptrend) **VÀ `vol_decay = vol7/vol30 < 1`** **VÀ
  `ret30 < 0`** **VÀ `dd_from_high30 < −20 %`** (bleed median −42 % ⇒ −20 % là mốc "đang xả" thận trọng).
- Cơ sở: **P9** (reversal >1 tháng) · **P6** (daily reversal do illiquidity) · **P11** (regime switching) ·
  **data §2** (bleed leg dài 24+ ngày ⇒ cửa sổ short đủ dài).

> ⚠️ Ngưỡng là **mốc dữ liệu** (median/p75), công bố TRƯỚC khi đo drift; không quét mũ. Probe drift theo
> đúng 2 state này nằm trong `RESULT_SHORT_STATE`.

## 4. Giới hạn
- ZigZag θ=25 % là **một** lựa chọn (không quét θ); đổi θ đổi số tuyệt đối nhưng **bất đối xứng up<bleed giữ nguyên**.
- tier = notional **mẫu 14 ngày** (xấp xỉ), không phải notional 30d đầy đủ.
- P1–P5 đo P&D **có tổ chức** (Telegram) — không đồng nhất "mọi pump"; dùng làm **cơ chế**, không phải tần suất.
