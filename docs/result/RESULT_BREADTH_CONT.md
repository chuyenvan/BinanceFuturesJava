# RESULT_BREADTH_CONT.md — TASK B2 Bước 7: gate LIÊN TỤC theo breadth (BRC)

Thực thi 2026-09-22, executor (session `session_01UoVRjusfNM2USSVNKQrm7z`), branch `module`, repo
`/home/ubuntu/src/BinanceFuturesJava`. PREREG khoá trước: `docs/prereg/PREREG_BREADTH_CONT.md` (commit `b620770`).
Code BRC: commit `a224e88` (+ `extra_ds` kaggle_sim, commit ở round này). Sim CHẠY TRÊN KAGGLE
(account chuyendinh), KHÔNG đụng shadow-c3 trên Oracle.

## 0. Cổng an toàn
- **Cổng OFF byte-identical: PASS.** T170 + jar mới (RegimeSchedule gate liên tục) + cờ TẮT, chạy trên
  Kaggle (`sim-brc-off-t170`): md5 `printDone.csv` = **`efb793e2468ca3a7318da0f0ad23d4fc`**, n=1089,
  equity=111070 — trùng TỪNG BYTE tham chiếu Oracle `X1_GS_T170_2021`. Xác nhận thay đổi Java thuần
  cộng-thêm (OFF không đổi hành vi) VÀ bundle overlay + jar mới đúng.
- **shadow-c3 KHÔNG bị đụng**: PID 1329374 (`BinanceOrderTradingManager`) `active` xuyên suốt (etimes
  tăng đều, không restart bởi executor). KHÔNG stop/kill/systemctl. Sim nặng chạy 100% trên Kaggle.
- **HOLDOUT 2026**: mọi sim `SIM_END_DATE=20251231`; CSV gate phủ tới 2025-12-31. Không đụng seal.
- **git**: không push/checkout đổi tree (dùng `git show HEAD:` khi cần khôi phục). index.lock không gặp.

## 1. Cơ chế đã chạy
- Java (RegimeSchedule): thêm chế độ đọc gate float/ngày từ cột CSV khi `SIM_REGIME_GATE_VALUE_COL>=0`
  (mặc định −1 = nhị phân cũ). BRC: `SIM_GATE_REGIME_ADAPTIVE=1`, `SIM_REGIME_GATE_VALUE_COL=4`,
  `SIM_REGIME_FILE=regime_cont_allcoin.csv` (cột scale = gate all-coin/MA200/thr50, 1.0→1.7 causal).
  Log Kaggle xác nhận: `[REGIME] adaptive ON file=.../sim-brc-overlay/regime_cont_allcoin.csv`.
- Kaggle: overlay dataset `sim-brc-overlay` (jar mới + profiles + CSV, 96MB) mount CÙNG bundle lớn
  `sim-x1-2021-bundle` (dữ liệu không đổi). Glob theo thứ tự abc ("sim-b..."<"sim-x...") đảm bảo kernel
  chọn jar/profile/CSV MỚI. Gate value all-coin: min 1.0, max 1.7, mean toàn kỳ 1.367; **mean 2025 = 1.423**
  (breadth all-coin 2025 chỉ ~11% → gate CAO gần suốt 2025, KHÁC dự báo thiết kế "~1.33").

## 2. Bảng chính (metric `bigdown_struct` icc_anova + `c3_rates`, cửa sổ 2021-07-01..2025-12-31)

| tag | n | n_eff_total | ICC | maxDD% | UW(ngày) | CAGR% | equity |
|---|---:|---:|---:|---:|---:|---:|---:|
| T170 (`X1_GS_T170_2021`) | 1089 | 606.26 | 0.0516 | -11.844 | 92 | 29.27 | 111,070 |
| gate-1.0=T100 (`X1_C3_FULL_2021`) | 2559 | 1103.86 | 0.1016 | -16.129 | 248 | 31.94 | 121,770 |
| BR nhị phân (top-50, Bước 6) | 1582 | 741.83 | 0.0827 | -11.842 | 180 | 30.12 | 114,410 |
| **BRC (liên tục, all-coin)** | 1689 | 753.54 | 0.0925 | -13.216 | 221 | 31.28 | 119,066 |
| BRC0 (đối chứng, g=1.27) | 1647 | 735.45 | 0.0967 | -19.513 | 221 | 23.91 | 91,817 |

Chú ý confound (đã ghi PREREG): BR dùng breadth **top-50**, BRC dùng **all-coin** (theo thiết kế §1).

### UW theo năm | CAGR theo năm (%)
| tag | UW21 | UW22 | UW23 | UW24 | UW25 || C21 | C22 | C23 | C24 | C25 |
|---|--:|--:|--:|--:|--:||--:|--:|--:|--:|--:|
| T170 | 37 | 72 | 63 | 92 | 52 || 12.2 | 19.6 | 35.0 | 32.1 | 32.7 |
| T100 | 47 | 64 | 45 | 121 | 227 || 9.3 | 17.3 | 60.4 | 45.3 | 16.5 |
| BR | 46 | 72 | 63 | 121 | 58 || 4.2 | 19.6 | 47.0 | 45.2 | 22.9 |
| **BRC** | 46 | 76 | 66 | 119 | **221** || 5.9 | 17.0 | 47.7 | 44.5 | **28.7** |
| BRC0 | 47 | 69 | 42 | 162 | 221 || 8.6 | 18.8 | 47.5 | 27.3 | 8.3 |

## 3. Khẩu vị hiện hành (`x1_rates.py --appetite current --k 1`; coin≤15% KHÔNG đo — khoảng trống đã biết)

| tag | 2021 | 2022 | 2023 | 2024 | 2025 | Tổng |
|---|---|---|---|---|---|---|
| T170 | PASS | PASS | PASS | PASS | PASS | **PASS 5/5** |
| BR | PASS | PASS | PASS | PASS | PASS(UW=58) | **PASS 5/5** |
| **BRC** | PASS | PASS | PASS | PASS | **FAIL** (UW=221>200) | **FAIL 2025** |

BRC-2025: maxDD −5.36%, ret 28.71%, quý_min −1.12% ĐỀU đạt, chỉ **UW=221>200** làm vỡ khẩu vị. (Trái với
BR: BR ép UW-2025 xuống 58 → pass, nhưng cắt return-2025 còn 22.9%.)

## 4. u1–u5 (khoá PREREG)
| # | Tiêu chí | Ngưỡng | BRC | KQ |
|---|---|---|---|---|
| u1 | n_eff(BRC) ≥ 1.5×n_eff(T170) | ≥909.38 | 753.54 (×1.243) | **FAIL** |
| u2 | khẩu vị current PASS mọi năm + CAGR≥14.80 | 5/5 + CAGR≥14.8 | FAIL 2025 (UW=221); CAGR=31.28 | **FAIL** |
| u3 | maxDD ≥ −14.805 VÀ UW ≤ 115 | cả 2 | maxDD −13.216 (PASS), UW 221 (FAIL) | **FAIL** |
| u4 | UW(BRC)<UW(BRC0) VÀ ret2025(BRC)>ret2025(BR) | cả 2 | UW 221=221 (FAIL, hoà), ret 28.7>22.9 (PASS) | **FAIL** |
| u5 | CAGR23&24(BRC) ≥ 90%×T100 | 23≥54.39, 24≥40.75 | 23=47.69 (FAIL), 24=44.49 (PASS) | **FAIL** |

**Verdict: NULL** (u1–u5 đều fail theo định nghĩa chặt; chỉ các NỬA tiêu chí u4-ret & u3-maxDD & u5-2024 đạt).

## 5. Phát hiện cốt lõi (cho MASTER)
1. **Gate liên tục GIỮ return-2025 tốt hơn nhị phân**: ret2025 BRC=28.7% > BR=22.9% (u4-ret PASS) — đúng
   giả thuyết (a). NHƯNG vẫn < T170 (32.7%): BRC KHÔNG "giữ 2025" bằng incumbent.
2. **Cái giá: UW-2025 = 221 ngày** (vs BR 58, T170 52) → vỡ khẩu vị (u2 FAIL). Nguyên nhân: breadth
   all-coin 2025 ~11% (thị trường HẸP: BTC/majors lên, alt sập dưới MA200) → gate liên tục ở mức ~1.42
   gần SUỐT 2025, không "nhả" như thiết kế giả định ~1.33. Chuỗi underwater 2025 là đặc tính CẤU TRÚC thị
   trường, gate breadth không thoát được về mặt THỜI LƯỢNG.
3. **Adaptive > flat (cùng n)**: BRC vs BRC0 (n 1689 vs 1647, khớp ~2.5%): maxDD −13.2 vs **−19.5**,
   CAGR 31.3 vs 23.9, equity 119k vs 92k, ret2025 28.7 vs 8.3 — "giãn theo breadth" THẮNG rõ flat trên
   ĐỘ SÂU sụt & lợi nhuận. CHỈ HOÀ ở UW (221=221): thời lượng underwater 2025 giống nhau (cùng kẹt regime
   hẹp). → u4-UW fail trên HOÀ, nhưng TINH THẦN u4 (adaptive nhắm đúng) được ủng hộ mạnh ở maxDD/CAGR.
4. **BRC vs T170**: CAGR 31.28 vs 29.27 (+2.0pp, nhẹ), equity +7.2%, nhưng maxDD XẤU hơn (−13.2 vs −11.8),
   UW XẤU hơn nhiều (221 vs 92, vỡ khẩu vị). → KHÔNG phải "ứng viên incumbent mạnh": không vượt trội rõ,
   không trong khẩu vị, không giữ 2025 bằng T170.

## 6. Đối chiếu dự báo PREREG (khoá trước — 5/5 ĐÚNG)
| Dự báo | Thực tế | KQ |
|---|---|---|
| (1) n(BRC)>n(BR)=1582 | 1689 | ĐÚNG |
| (2) u1 vẫn có thể fail ×1.5 | ×1.243 FAIL | ĐÚNG |
| (3) ret2025(BRC)>BR | 28.7>22.9 | ĐÚNG (nhưng gate-2025 thực 1.42, không 1.33 như giả định) |
| (4) UW(BRC) giữa BR(180)&T100(248), có thể >115 | 221, >115 | ĐÚNG |
| (5) u5-2023 có thể fail | 47.7<54.4 FAIL | ĐÚNG |

## 7. Kết luận & khuyến nghị
- **NULL**, cấu trúc GIỐNG Bước 6 (BR) nhưng ĐÁNH ĐỔI KHÁC: BR mua được khẩu vị-2025 (UW 58) bằng cách
  cắt return; BRC giữ return-2025 (28.7) nhưng mất khẩu vị (UW 221). Không cái nào vượt T170 toàn cục.
- Hướng breadth-gate (Bước 4→7) đã tới GIỚI HẠN: breadth all-coin 2025 quá thấp làm gate liên tục ~cứng
  cao suốt 2025, không tạo được "nhả đúng lúc". T170 vẫn là incumbent tốt nhất trên khẩu vị + 2025.
- CẤM dredging (PREREG): KHÔNG mở biến thể mới (thr khác, gate_up/down khác) trong round này. Nếu MASTER
  muốn tiếp: cần PREREG mới — có thể xét breadth theo NHÓM (majors vs alts) thay all-coin, để 2025 (majors
  mạnh) không bị kéo gate lên bởi alt-breadth thấp. TASK D là hướng chính theo roadmap.

## 8. Thay đổi code (diff Java tối thiểu, thuần cộng-thêm)
- `RegimeSchedule.java` (+18/−2): field `gateValueCol=-1`, `setGateValueCol(int)`, nhánh đọc float cột
  `gateValueCol` trong `load()` (mặc định giữ nhị phân → OFF byte-identical).
- `Configs.java` (+4): `SIM_REGIME_GATE_VALUE_COL` (int, −1) + parse.
- `SimulatorMarketLevelTicker1MStopLoss.java` (+1): gọi `setGateValueCol` trước `load`.
- `tools/kaggle_sim.py` (+6 SIM_REGIME_FILE resolve mount, +2 `extra_ds`).
- Mới: `research/analysis/breadth_cont_csv.py`, `breadth_cont_metrics.py`, `out/breadth_cont_metrics.json`,
  `profiles/x1_c3_full_regime_brc.properties`, `profiles/x1_c3_full_regime_brc0.properties`.
- Kaggle: dataset `sim-brc-overlay` (mới); jar md5 `06def68b8a0cbc618e9ccd2ae3184ba5`.
- GHI CHÚ MASTER: task-prompt ghi u1 "≥1364" mâu thuẫn design-doc "909"; đã khoá theo CÔNG THỨC
  1.5×n_eff(T170)=909.38 (design-doc). Với cả 2 mốc BRC (753.54) đều FAIL.

---
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
