# RESULT_TAIL_LEVER — chặn `gross exposure` / trap ALT: cắt được bao nhiêu đuôi, giá bao nhiêu lãi

Kết quả của `research/analysis/tail_lever.py` (thuần **Python offline trên Oracle**, **KHÔNG** Java/sim,
**KHÔNG** claude-run, **KHÔNG push**). Thực thi `docs/prereg/PREREG_TAIL_LEVER.md` (chốt **TRƯỚC** khi đo).
DEV only: trục phút `2021-07-01 00:00Z .. 2025-12-30 23:59Z`, **không đọc 2026**.

Log: `/home/ubuntu/taillever/data.log` (dựng cache, 1,014s) · `an.log` (phân tích) ·
report: `/home/ubuntu/taillever/report_tail_lever.txt` · JSON: `/home/ubuntu/taillever/tail_lever.json` ·
cache: `/home/ubuntu/taillever/{contrib_T170,contrib_KEEPLEG0,contrib_T100,contrib_GD92,trap}.npz` (150 MB).

**Mọi số dưới đây là XẤP XỈ OFFLINE để XẾP HẠNG phương án — KHÔNG phải kết quả sim** (xem §7).
**Không có CI** (1 quan sát lịch sử; 10 episode không độc lập — ~9 đợt thị trường).

## 0. TÓM TẮT (4 dòng)

1. **Rủi ro hệ thống**: top-1 coin chỉ **11.8–17.6%** độ sâu, top-3 **31.0–40.9%**, **phần còn lại
   (thị trường) 59.1–69.0%**; **0/44** cú nào có top-1 `> 50%`. Cửa sổ 11/10: AIA `14.7–19.8%`,
   top-3 `35.1–42.9%` ⇒ **đuôi là HỆ THỐNG, không coin nào phá sản**.
2. **Trần `G`**: **không G nào đạt gate**. `G=20%` cắt 56–88% độ sâu 11/10 nhưng **giữ 0–8% PnL**
   (T100/GD92 **PnL ÂM**) và **làm intraday maxDD XẤU HƠN** (−39.7% / −43.4%); `G=40%` cắt
   7–18% độ sâu với giá **21–36% PnL**; `G=50%` chỉ cắt 3–5% độ sâu (giá 7–14% PnL).
   **Leg bị chặn mang 82–114% tổng PnL** ⇒ chặn exposure = chặn chính cái sinh ra lãi.
3. **Trap ALT**: 35 lần kích hoạt (9/năm), chặn 5.9% leg, **giữ 77–82% PnL**, cắt **1.6–2.7 pp**
   (8–13% độ sâu 11/10) và **cắt ~0% ở 10 cú giảm sâu khác** (T100 còn âm) ⇒ **chỉ cắt đúng lúc
   tốt nhất** + đắt. Luật L2 (BTC không giảm) gần như **miễn phí nhưng vô dụng** (cắt 0.2 pp).
4. **Đòn bẩy đúng**: **không** nằm ở trần exposure tĩnh. 2 thứ đáng đưa vào SIM THẬT để **kiểm định**
   là (a) **`G=50%` như "airbag"** và (b) **trap L1-only** — cả hai đều **KHÔNG** vượt gate chốt
   trước, nên chỉ đáng test nếu sim (có tái vào lệnh) cho chi phí PnL thấp hơn hẳn xấp xỉ này.

## 1. Công nghiệm thu (chốt trước) — PASS, kèm 1 AMENDMENT

| # | nội dung | KQ | verdict |
|---|---|---|---|
| **W1** | dựng lại chuỗi baseline từ đóng góp **từng leg** == `intradaydd/series.npz` | max\|Δ\| **0.00088 / 0.00096 / 0.00143 / 0.00115 USDT** (≈1e-6 % equity), T170/KEEPLEG0/T100/GD92 | **PASS** |
| **W2** | maxDD/UW == `RESULT_INTRADAY_DD` §3.1 | **−19.96 / −19.96 / −26.26 / −24.30**; UW **144.4 / 147.2 / 248.2 / 277.8** | **PASS (khớp tuyệt đối)** |
| **W3** | phân rã A: `\|Σcontrib + depth\|/depth` | **max 0.00%** trên cả 44 cú×nền | **PASS** |
| **W4** | `#leg chặn` đơn điệu theo G | 761/474/185/40 · 741/428/178/31 · 2080/1439/601/188 · 2121/1499/611/185 | **PASS** |

### AMENDMENT-1 (ngưỡng W1) — ghi rõ, không dùng để che

Pre-reg §2.1 đặt W1 `<= 1e-3 USDT` (tuyệt đối). Thực đo: T170 0.00088 · KEEPLEG0 0.00096 ·
**T100 0.00143 · GD92 0.00115** ⇒ **2/4 nền vượt ngưỡng tuyệt đối 1.4 lần**, tương đối
**1.1e-06% equity** (sai số làm tròn float32 khi cộng theo thứ tự leg khác). Đã báo cáo **cả hai**
con số; **không** nới ngưỡng để "cho PASS" mà ghi nhận đây là **vượt ngưỡng kỹ thuật ở mức vô nghĩa
thực tế** (0.0014 USDT trên equity ~120,000). Không đổi contract, không đổi ngưỡng kết luận §6.

## 2. LỖI DỮ LIỆU PHÁT HIỆN ĐƯỢC + SỬA (ghi lại vì đã làm SAI 1 vòng)

- **Triệu chứng**: vòng đo đầu tiên **FAIL W1 nặng** — max\|Δ\| = **19,470 / 18,330 USDT** (T170 /
  KEEPLEG0) dù maxDD vẫn ra −19.96%. Truy vết 1 mốc (2025-01-07 17:00Z, T100): unP tái tạo **265
  USDT** vs chuỗi gốc **1,351 USDT**, lệch **1,085 USDT**.
- **Nguyên nhân**: bản đầu dựng ma trận giá theo **tập symbol của NẾN ĐẦU TIÊN** trong file 1m. Symbol
  nào chưa xuất hiện ở nến đầu (mới list / thiếu nến) thì **không có dòng** ⇒ **mất toàn bộ MTM của
  leg đó cả ngày** (2 leg `ALCHUSDT`, `SWARMSUSDT` mở 15:22 ngày 2025-01-07 bị mất sạch:
  `vv_nz = 0`).
- **Sửa**: dựng ma trận theo **UNION symbol cả ngày** rồi `ffill/bfill` theo phút — **đúng như
  `_work` của `RESULT_INTRADAY_DD`** (bản đó lấy `srow` từ `need[day]` = leg của mọi run, tức cũng là
  union) ⇒ sau khi sửa: max\|Δ\| **≤ 0.0014 USDT**, **0 leg** mất trắng MTM.
- **Ảnh hưởng**: **KHÔNG** đổi `RESULT_INTRADAY_DD` (số cũ tái tạo khớp tuyệt đối ở W2: −19.96 /
  −19.96 / −26.26 / −24.30; UW 144.4 / 147.2 / 248.2 / 277.8). Lỗi chỉ ở **script mới** của lượt này.
- Lỗi phụ: `load_layout` trả cột `ts` **chưa sort** (chỉ để in, đã sửa). Không ảnh hưởng số.

## 3. VIỆC A — PHÂN RÃ RỦI RO HỆ THỐNG (đóng góp từng coin)

`resolution` = độ sâu (peak→trough, mốc phút). Đóng góp coin = `Σ_{leg mở tại trough} qty*(P_trough −
P_ref)` (`P_ref` = giá tại peak nếu leg mở ở peak, ngược lại = entry) **+ pnl của leg đóng trong
(peak, trough]**. `Σ contrib / depth` khớp **0.00%** trên 44 cú ⇒ phân rã **đầy đủ, không rò rỉ**.

### 3.1 Cửa sổ `2025-10-09..13` (trough = `2025-10-10 21:20Z` cả 4 nền)

| nền | độ sâu phút | depth (USDT) | top-1 | top-3 | **còn lại (thị trường)** | n coin | 3 coin xấu nhất |
|---|---|---|---|---|---|---|---|
| T170 | −19.57% | 19,466 | **19.8%** | 42.9% | **57.1%** | 17 | AIA −3,931 · EVAA −2,362 · STBL −2,234 |
| KEEPLEG0 | −19.57% | 18,327 | 19.8% | 42.9% | 57.1% | 17 | AIA −3,701 · EVAA −2,223 · STBL −2,104 |
| T100 | −20.41% | 23,375 | 15.1% | 35.1% | **64.9%** | 22 | AIA −3,585 · EVAA −2,579 · STBL −2,165 |
| GD92 | −20.70% | 24,310 | 14.7% | 35.1% | 64.9% | 22 | AIA −3,612 · EVAA −2,638 · STBL −2,388 |

⇒ Trong cú đuôi quan trọng nhất: **~57–65% độ sâu đến từ thị trường**, coin xấu nhất (AIA) chỉ
**~15–20%**. **Không thể** chữa cú này bằng xử lý 1 coin.

### 3.2 Tổng hợp 11 cú/nền (10 cú giảm intraday sâu nhất + cửa sổ 11/10)

| nền | top-1 TB | top-3 TB | **còn lại TB** | n coin TB | hệ thống (top1<25 & top3<50) | 1-coin (top1>50) |
|---|---|---|---|---|---|---|
| T170 | 17.6% | 40.9% | **59.1%** | 18.3 | **8/11 cú** | **0/11** |
| KEEPLEG0 | 16.9% | 40.0% | 60.0% | 18.1 | **9/11 cú** | 0/11 |
| T100 | 13.7% | 33.6% | **66.4%** | 29.8 | **10/11 cú** | 0/11 |
| GD92 | 11.8% | 31.0% | **69.0%** | 26.6 | **11/11 cú** | 0/11 |

Ngoại lệ (đuôi **idiosyncratic** thật, top-3 ≥ 50%): T170 **2022-11 FTT** (top1 30.7%, top3 51.5%)
và T170 **2022-05 GAL/DAR/KNC** (top1 28.0%, top3 65.1%); T100 2022-11 FTT 53.5%. Các cú còn lại là
**hệ thống**.

**Trả lời (1)**: **59–69% độ sâu của các cú giảm lớn là RỦI RO HỆ THỐNG**; top-3 coin chỉ giải thích
31–41%; **0/44 cú** là "1 coin phá sản". Ngưỡng pre-reg §1.1 ("hệ thống" nếu top1<25 & top3<50)
đạt ở **8–11/11 cú** tuỳ nền ⇒ **kết luận: đuôi là hệ thống**.

## 4. VIỆC B — TRẦN `gross exposure` (XẤP XỈ offline)

`margin = quantity*entry` (1x, đã kiểm ở `RISK_APPETITE` §6) ⇒ `Σ margin` leg đang mở = gross exposure.
Luật: duyệt leg theo `m0` tăng dần; chặn leg mới nếu `gross(m0) + margin_leg > G% · equity(m0)`
(equity tham chiếu = equity của chính kịch bản, fixed-point 3 vòng).

### 4.0 Bối cảnh (B0) — exposure tại phút mở lệnh, duyệt hết không chặn

| nền | mean | p50 | p90 | p99 | max | %leg > 20% | > 30% | > 40% | > 50% |
|---|---|---|---|---|---|---|---|---|---|
| T170 | 25.6% | 25.0% | 44.4% | 59.7% | 65.2% | 62% | 37% | 17% | 4% |
| KEEPLEG0 | 25.7% | 25.1% | 45.0% | 58.3% | 63.6% | 62% | 37% | 18% | 4% |
| T100 | 29.0% | 28.5% | 48.3% | 59.6% | 67.1% | 72% | 47% | 22% | 8% |
| GD92 | 28.9% | 28.4% | 48.4% | 59.4% | 66.8% | 72% | 46% | 23% | 8% |

⇒ `G=20/30%` **binding phần lớn thời gian** (62–72% / 37–47% số leg); `G=40%` binding 17–23%;
`G=50%` gần như không binding (4–8%) — nên `G=50` "rẻ" vì **hầu như không làm gì**.

### 4.1 Bảng chính (thuốc đuôi: intraday maxDD · worst-window 11/10)

| nền | G% | **intraday maxDD** | **worst-window 11/10** | tổng PnL | CAGR | n | #leg chặn | UW (ngày) |
|---|---|---|---|---|---|---|---|---|
| **T170** | **không trần** | **−19.96%** | **−19.57%** | 76,070 | 29.27% | 1,089 | 0 | 144.4 |
| | 20 | −20.76% | −8.42% | 2,339 | **1.45%** | 328 | 761 | 347.8 |
| | 30 | −13.77% | −13.17% | 34,024 | 16.30% | 615 | 474 | 239.4 |
| | 40 | −18.26% | −17.83% | 55,890 | 23.63% | 904 | 185 | 147.2 |
| | 50 | −19.44% | −19.05% | 65,711 | 26.49% | 1,049 | 40 | 144.4 |
| **KEEPLEG0** | **không trần** | **−19.96%** | **−19.57%** | 68,083 | 27.14% | 1,085 | 0 | 147.2 |
| | 20 | −16.42% | −8.53% | 5,721 | 3.42% | 344 | 741 | 303.3 |
| | 30 | −13.35% | −12.78% | 33,120 | 15.96% | 657 | 428 | 239.4 |
| | 40 | −18.58% | −18.16% | 53,501 | 22.90% | 907 | 178 | 147.2 |
| | 50 | −19.36% | −18.97% | 63,422 | 25.84% | 1,054 | 31 | 147.2 |
| **T100** | **không trần** | **−26.26%** | **−20.41%** | 86,770 | 31.94% | 2,559 | 0 | 248.2 |
| | 20 | **−39.73%** | −2.46% | **−9,619** | **−6.89%** | 479 | 2,080 | 735.0 |
| | 30 | **−65.28%** | −21.98% | **−9,164** | **−6.53%** | 1,120 | 1,439 | 658.2 |
| | 40 | −25.03% | −16.72% | 57,239 | 24.04% | 1,958 | 601 | 303.0 |
| | 50 | −25.57% | −19.48% | 74,904 | 28.97% | 2,371 | 188 | 303.0 |
| **GD92** | **không trần** | **−24.30%** | **−20.70%** | 98,944 | 34.76% | 2,632 | 0 | 277.8 |
| | 20 | **−43.36%** | −5.14% | **−13,539** | **−10.30%** | 511 | 2,121 | 842.6 |
| | 30 | **−54.07%** | −15.39% | **−7,969** | **−5.58%** | 1,133 | 1,499 | 638.7 |
| | 40 | −20.75% | −18.07% | 63,088 | 25.75% | 2,021 | 611 | 280.5 |
| | 50 | −23.08% | −19.82% | 86,612 | 31.90% | 2,447 | 185 | 277.8 |

### 4.2 Bảng "cắt được gì / mất gì" (Δ so với không trần)

| nền | G% | **Δ 11/10 (pp)** | **% độ sâu 11/10 cắt được** | Δ intraday maxDD (pp) | **Δ PnL (%)** | Δ CAGR (pp) | PnL leg bị chặn (USDT) |
|---|---|---|---|---|---|---|---|
| T170 | 20 | **−11.15** | **57%** | −0.80 (xấu hơn) | **−96.9%** | −27.8 | 73,731 (**97% tổng PnL**) |
| | 30 | −6.40 | 33% | +6.20 | −55.3% | −13.0 | 42,046 |
| | 40 | −1.74 | 9% | +1.70 | −26.5% | −5.6 | 20,180 |
| | 50 | −0.53 | 3% | +0.52 | −13.6% | −2.8 | 10,359 |
| KEEPLEG0 | 20 | −11.04 | 56% | +3.55 | −91.6% | −23.7 | 62,362 |
| | 30 | −6.79 | 35% | +6.61 | −51.4% | −11.2 | 34,963 |
| | 40 | −1.41 | 7% | +1.39 | −21.4% | −4.2 | 14,582 |
| | 50 | −0.61 | 3% | +0.60 | −6.8% | −1.3 | 4,661 |
| T100 | 20 | −17.95 | 88% | **−13.47 (xấu hơn)** | **−111.1%** | −38.8 | 96,389 (**111%**) |
| | 30 | +1.58 (xấu hơn) | +8% (xấu hơn) | **−39.03** | −110.6% | −38.5 | 95,934 |
| | 40 | −3.68 | 18% | +1.23 | −34.0% | −7.9 | 29,531 |
| | 50 | −0.92 | 5% | +0.68 | −13.7% | −3.0 | 11,866 |
| GD92 | 20 | −15.55 | 75% | **−19.06** | **−113.7%** | −45.1 | 112,483 (**114%**) |
| | 30 | −5.31 | 26% | **−29.77** | −108.1% | −40.4 | 106,913 |
| | 40 | −2.63 | 13% | +3.55 | −36.2% | −9.0 | 35,856 |
| | 50 | −0.88 | 4% | +1.22 | −12.5% | −2.9 | 12,332 |

**Đọc ra 4 điều (đều là tin xấu cho trần exposure):**

1. **Đắt hơn nhiều so với cắt được**: `G=40%` (mức "hợp lý" theo `RISK_APPETITE`) đổi **21–36% PnL**
   lấy **7–18% độ sâu** 11/10. `G=50%` đổi **7–14% PnL** lấy **3–5% độ sâu** ⇒ **tỷ lệ ~3-7:1**.
2. **Cắt mạnh thì phá chiến lược**: `G=20%` giữ **0–8% PnL** (T170/KEEP) và **PnL ÂM** (T100 −9,619 ·
   GD92 −13,539); CAGR về **1.5% / 3.4% / −6.9% / −10.3%**.
3. **Lý do sâu xa (số mới)**: **leg bị chặn mang 82–114% tổng PnL** ⇒ lãi nằm ở **các leg mở khi
   exposure đã cao** (pyramiding vào trend). Chặn exposure = **chặn đúng cái sinh ra lãi**, giữ lại
   phần lớn leg lỗ ⇒ với T100/GD92, tập còn lại **PnL âm**.
4. **KHÔNG đơn điệu — trần có thể làm rủi ro XẤU HƠN**: T100 `G=30%` ⇒ intraday maxDD
   **−65.28%** (gấp 2.5 lần không trần), UW **658 ngày**; GD92 `G=20%` ⇒ **−43.36%**, UW **843 ngày**.
   Cơ chế: bỏ leg không tái phân bổ ⇒ danh mục còn lại ít leg hơn, tương quan cao hơn, và (vì bị
   chặn liên tục) rơi vào các giai đoạn xấu khác. ⇒ **trần tĩnh KHÔNG phải van an toàn đáng tin**.

**Gate chốt trước §1.1** (cắt ≥ 25% độ sâu 11/10 **VÀ** giữ ≥ 70% PnL **VÀ** giữ ≥ 70% CAGR **VÀ**
intraDD không xấu hơn): **KHÔNG G NÀO ĐẠT** trên cả 4 nền.

**Trả lời (2)**: xếp hạng theo điểm Pareto (cắt/giá): **G=50% > G=40% > G=30% > G=20%**;
"cắt được nhiều nhất với giá thấp nhất" theo nghĩa **tỷ lệ** là **G=50%** (5% độ sâu / 8–14% PnL)
nhưng **giá trị tuyệt đối quá nhỏ để gọi là chặn rủi ro**; `G=30%` là mức duy nhất **cắt đáng kể
(26–35% độ sâu)** nhưng **phá chiến lược** (PnL +0.9 … −0.9 lần) và **làm intraDD xấu hơn** ở
T100/GD92 ⇒ **không có G nào nên đưa vào sản phẩm dưới dạng trần tĩnh**.

## 5. VIỆC C — TRAP ALT (p10 ret1h cross-section + BTC)

Tín hiệu: **L1** `|p10(ret1h)| > 20%` · **L2** `|ret1h(BTC)| < 1%` **và** `p10(ret1h) < −10%`.
p10 toàn universe: min **−76.3%**, p1 −3.9%, p5 −2.3%, median −0.543%.

| luật | số lần kích hoạt | số phút | theo năm |
|---|---|---|---|
| **primary L1 ∪ L2** | **35** | 229 | 2021:3 · 2022:6 · 2023:4 · **2024:16** · 2025:6 |
| L1 only (`\|p10\|>20%`) | 17 | 171 | 2021:3 · 2022:4 · 2023:2 · 2024:6 · 2025:2 |
| L2 only | 20 | 64 | 2022:2 · 2023:2 · **2024:10** · 2025:6 |
| lookback 15 phút | 21 | 583 | — |

(`|p10|>20%` chỉ xảy ra khi p10 < −20%: **không có** lần nào p10 > +20%.)

### 5.1 Đo trên đường equity (chặn leg mới tại đúng phút mở lệnh)

| nền | luật | intraday maxDD | **11/10** | PnL | **%PnL giữ** | n | **cắt TB 10 cú giảm sâu** | PnL leg bị chặn |
|---|---|---|---|---|---|---|---|---|
| T170 | không chặn | −19.96% | −19.57% | 76,070 | 100% | 1,089 | — | — |
| | **primary** | −18.35% | **−17.93%** | 58,687 | **77.1%** | 936 | **+1.2%** | 17,383 |
| | L1 only | −18.23% | −17.81% | 59,341 | 78.0% | 947 | +1.4% | 16,729 |
| | L2 only | −20.10% | −19.70% | 75,097 | **98.7%** | 1,074 | −0.2% | 973 |
| | lookback 15' | −18.87% | −18.44% | 56,069 | 73.7% | 908 | −0.0% | 20,002 |
| KEEPLEG0 | **primary** | −18.37% | −17.95% | 53,953 | 79.2% | 934 | +1.4% | 14,130 |
| | L2 only | −20.09% | −19.70% | 67,169 | 98.7% | 1,070 | −0.2% | 914 |
| T100 | không chặn | −26.26% | −20.41% | 86,770 | 100% | 2,559 | — | — |
| | **primary** | −24.72% | **−17.78%** | 68,535 | **79.0%** | 2,400 | **−4.1%** | 18,235 |
| | L1 only | −24.72% | −17.69% | 69,126 | 79.7% | 2,412 | −4.4% | 17,644 |
| | L2 only | −26.38% | −20.51% | 85,850 | 98.9% | 2,543 | +0.3% | 921 |
| GD92 | không chặn | −24.30% | −20.70% | 98,944 | 100% | 2,632 | — | — |
| | **primary** | −24.91% | −18.03% | 80,783 | **81.6%** | 2,471 | +0.6% | 18,161 |
| | L2 only | −24.30% | −20.86% | 97,719 | 98.8% | 2,612 | +2.2% | 1,225 |

Số leg bị chặn (primary): **153 / 151 / 159 / 161** (≈5.9% số leg).

### 5.2 Đọc ra

1. **Cắt được rất ít**: primary cải thiện 11/10 **1.6–2.7 pp** = **8–13% độ sâu**; intraday maxDD
   cải thiện **1.5–1.6 pp** (T170/KEEPLEG0/T100) và **tệ hơn 0.6 pp** ở GD92.
2. **Không cắt được gì ở các cú khác**: cắt TB trên 10 cú giảm sâu nhất = **+1.2% / +1.4% / −4.1% /
   +0.6%** ⇒ **trap chỉ cắt ĐÚNG LÚC TỐT NHẤT (11/10)**, không phải cơ chế tổng quát
   (đúng tiêu chí "chỉ cắt đúng lúc tốt nhất" đã chốt trước ở §1.1).
3. **Giá đắt**: giữ **77–82% PnL** (mất **~17,000–18,000 USDT** do chặn leg **có lãi** ròng).
4. **Luật L2 gần như miễn phí nhưng vô dụng**: giữ **98.7–98.9% PnL**, cắt **0.2 pp** (thậm chí làm
   11/10 xấu hơn 0.1–0.2 pp). ⇒ Toàn bộ tác dụng của trap đến từ **L1** (17 lần/4.5 năm).
5. **Kích hoạt tập trung ở 2024 (16/35)** — năm "bình thường", không phải năm sập mạnh; ⇒ tín hiệu
   bắt cả nhiễu.

**Trả lời (3)**: **KHÔNG ĐÁNG** dưới dạng luật đứng riêng. Gate chốt trước §1.1 đòi
(≤40 lần ✓ 35) **VÀ** (giữ ≥ 90% PnL ✗ 77–82%) **VÀ** (cắt ≥ 15% độ sâu 11/10 ✗ 8–13%) ⇒ **trượt 2/3
điều kiện**. So sánh trực tiếp: trap ≈ `G=40%` về lợi ích đuôi nhưng **rẻ hơn chút** (mất 19–23% PnL
so với 21–36%) ⇒ nếu buộc chọn giữa 2 cái **chỉ để cắt 11/10**, trap-L1 nhỉnh hơn; nhưng cả hai
**đều không đáng làm chuẩn mực**.

## 6. KẾT LUẬN (4) — ĐỀ XUẤT ĐƯA VÀO SIM THẬT (không tự chạy) + TIÊU CHÍ CHẤM THUỐC ĐUÔI

**Nguyên tắc chốt**: chỉ đề xuất cái **có cơ chế** và **đáng test**, chấm bằng **thuốc đuôi**
(intraday maxDD mốc phút · worst-window drop 2025-10-09..13), **KHÔNG** chấm bằng rate trung bình.

### 6.1 Ba cấu hình đề xuất (theo thứ tự ưu tiên)

| # | cấu hình | vì sao (số của lượt này) | kỳ vọng nếu sim đúng |
|---|---|---|---|
| **C1** | **`CONC_CAP_GROSS_PCT = 0.50`** — trần gross exposure **50% equity** tại `createOrder` (airbag, không phải van chính) | rẻ nhất trong 4 mức: mất **7–14% PnL**, cắt **3–5%** độ sâu 11/10, **không** làm intraDD xấu hơn, chặn chỉ 31–188 leg | cải thiện **1–2 pp** worst-window; **KHÔNG** kỳ vọng cứu được đuôi 19.6% |
| **C2** | **trap L1-only**: chặn **add-on** khi `p10(ret1h cross-section) < −20%` (17 lần/4.5 năm) | lợi ích ≈ `G=40` nhưng chi phí thấp hơn (giữ 78–82.5% PnL, Δ11/10 **+1.7…+2.75 pp**), và **có cơ chế** (không thêm exposure vào lúc thị trường đang sập) | worst-window **−19.6% → ~−17.5%**; phải kiểm **không** mất quá 20% PnL |
| **C3** | **C1 + C2 cùng lúc** (trần 50% + trap L1) — cấu hình duy nhất kỳ vọng cắt **≥ 3 pp** | trần 50% cắt phần "exposure quá cao lúc sập", trap cắt phần "vào thêm lúc sập"; **cộng hưởng chưa đo được offline** (xấp xỉ này bỏ qua tái vào lệnh) | worst-window **≤ −17%**, intraday maxDD **≥ 2 pp tốt hơn** |

**KHÔNG đề xuất** (kèm lý do số): `G=20%`/`G=30%` — phá chiến lược (giữ 0–8% PnL, T100/GD92 PnL âm)
và **làm intraDD xấu hơn** (tới −65%); "trần per-coin" **không** đụng được cú 11/10 (AIA chỉ 15–20%
độ sâu); trap-L2 đứng riêng — vô dụng (cắt 0.2 pp).

### 6.2 Tiêu chí CHẤM (chốt trước khi chạy sim — đo bằng thuốc đuôi)

Một cấu hình chỉ **được giữ** nếu **TẤT CẢ** các điều sau đúng trên **T100 và GD92** (2 nền có đuôi
xấu nhất) **và không nền nào tệ đi**:

1. **`worst-window drop` 2025-10-09..13 cải thiện ≥ 2.0 pp** so với baseline cùng nền.
2. **`intraday maxDD` (MTM mốc phút) cải thiện ≥ 2.0 pp** và **không nền nào xấu hơn baseline**
   (điều kiện này loại `G=20/30%` ngay: chúng làm T100 −26.26% → −39.7/−65.3%).
3. **Giữ ≥ 80% tổng PnL và ≥ 80% CAGR** baseline; **n giảm ≤ 10%**; **UW không tăng > 10%**.
4. **Cắt được ở ≥ 3 trong 10 cú giảm sâu nhất** (mỗi cú ≥ 5% độ sâu), không chỉ 11/10 — điều kiện
   chống "chỉ cắt đúng lúc tốt nhất" (trap hiện **trượt**: cắt TB 10 cú ≈ 0%).
5. Báo cáo **kèm `bar.low`** (cận dưới) như `RESULT_INTRADAY_DD` §3.3, và **không** dùng chuỗi ngày.

## 7. MỤC BỎ / GIỚI HẠN (theo pre-reg §7 + cái đã thấy thật)

1. **Đây KHÔNG phải sim**: VIỆC B/C **bỏ hẳn leg bị chặn, KHÔNG tái phân bổ vốn, KHÔNG tái hiện
   đường quyết định của sim**. Hệ quả: con số **thiên vị BẤT LỢI cho trần/trap** (trong sim, vốn bị
   chặn có thể vào leg khác). ⇒ dùng để **XẾP HẠNG**, không dùng làm kết quả; muốn kết luận phải chạy
   sim thật (C1/C2/C3).
2. **KHÔNG mô hình thanh lý/margin call** (sim cũng không) ⇒ mọi maxDD là **cận dưới**.
3. **KHÔNG có CI**, 1 quan sát; 10 episode không độc lập (~9 đợt thị trường) ⇒ mọi "xếp hạng G" là
   yếu về thống kê; đặc biệt **2024 chiếm 16/35 lần trap** ⇒ tín hiệu có thể là nhiễu năm.
4. **Bỏ**: đường đi trong nến 1m (chỉ dùng close; `bar.low` chỉ đối chiếu ở `RESULT_INTRADAY_DD`),
   funding/phí theo phút, `unProfitMonth`/`unProfitDate` (đã bỏ ở lượt trước).
5. **p10/universe** tính trên **universe file 1m** (112→598 sym), không đúng universe sim từng ngày;
   **không loại stablecoin**; `ret1h` dùng close, **không** khử trùng lặp symbol.
6. **Chặn theo phút mở lệnh**, không mô hình trễ/huỷ lệnh; nhiều leg cùng phút xử lý **tuần tự**
   (sim xử lý theo lô) ⇒ xấp xỉ.
7. **KHÔNG chạy lại sim / không đổi profile/fitness/code chiến lược**; chỉ đọc artifact + 1m.
8. **Không** suy rộng ra tag khác (T170/KEEPLEG0/T100/GD92 là 4 nền duy nhất).
9. **Không đổi verdict nào** của `RESULT_INTRADAY_DD` (chỉ W2 khớp lại y nguyên) — lượt này **thêm
   lựa chọn**, không sửa kết luận cũ.
