# RESULT_BREADTH_CONT_T50.md — TASK B2 Bước 9: gate LIÊN TỤC theo breadth TOP50 (BRCT50)

Thực thi 2026-09-22, executor (session `session_01UoVRjusfNM2USSVNKQrm7z`), branch `module`, repo
`/home/ubuntu/src/BinanceFuturesJava`. PREREG khoá trước: `docs/prereg/PREREG_BREADTH_CONT_T50.md`
(commit `6312e06`). Code BRCT50: commit `601dbed` (profile + top50 CSV gen + metrics harness; 0
dòng Java mới — dùng lại jar breadth-cont `06def68b`). Sim CHẠY TRÊN KAGGLE (account chuyendinh),
KHÔNG đụng shadow-c3 Oracle.

Đây là hoán vị DUY NHẤT chưa chạy của hướng breadth: gate **LIÊN TỤC** dùng breadth **TOP50**
(BR=top50 nhị phân NULL Bước 6; BRC=all-coin liên tục NULL Bước 7; subset NO-GO Bước 8). Chạy
để đóng dứt điểm.

## 0. Cổng an toàn
- **Cổng OFF byte-identical: PASS.** T170 + jar mới (overlay `sim-brc-overlay` version BRCT50) +
  cờ TẮT, chạy trên Kaggle (`sim-brct50-off-t170`): md5 `printDone.csv` =
  **`efb793e2468ca3a7318da0f0ad23d4fc`**, n=1089, equity=111070 — trùng TỪNG BYTE tham chiếu
  Oracle `X1_GS_T170_2021`. Xác nhận overlay mới (thêm top50 CSV + prof_brct50) KHÔNG đổi nền.
- **shadow-c3 KHÔNG bị đụng**: PID 1338696 (`BinanceOrderTradingManager`) `active` xuyên suốt, KHÔNG
  restart bởi executor. KHÔNG stop/kill/systemctl. Sim nặng 100% trên Kaggle.
- **HOLDOUT 2026**: mọi sim `SIM_END_DATE=20251231`; CSV gate phủ tới 2025-12-31. Không đụng seal.
- **git**: không push/checkout; index.lock không gặp. **Diff Java = 0 dòng** (kỳ vọng, dùng lại jar).

## 1. Cơ chế đã chạy
- gate top50/MA200/thr50, causal <= t-1: `gate=1.0+0.7*clip((0.5-score_top50)/0.5,0,1)`, cột
  `gate_top50_ma200` của `breadth_score_series.csv` (proxy universe symId<=50, y ĐỊNH NGHĨA A).
  Sinh `regime_cont_top50.csv` (cột scale idx 4) qua `breadth_cont_csv_t50.py`.
- Gate top50: min 1.0, max 1.7, **mean toàn kỳ 1.3301**; **mean 2025 = 1.3140** (thấp hơn hẳn BRC
  all-coin 1.423) — ĐÚNG dự báo MASTER "gate-2025 top50 ~1.33": top50 gồm majors mạnh 2025 (breadth
  top50 đầu 2025 ~94% -> gate 1.0), nên gate NỚI hơn nhiều so với all-coin (breadth ~11% -> 1.42).
- Java: `RegimeSchedule` đọc gate float ở cột `SIM_REGIME_GATE_VALUE_COL=4`; profile
  `x1_c3_full_regime_brct50` (SIM_GATE_REGIME_ADAPTIVE=1, SIM_REGIME_FILE=regime_cont_top50.csv).
  Overlay `sim-brc-overlay` (version mới) mount cùng bundle `sim-x1-2021-bundle`.

## 2. Bảng chính (metric `bigdown_struct` icc_anova + `c3_rates`, cửa sổ 2021-07-01..2025-12-31)

| tag | n | n_eff_total | ICC | maxDD% | UW(ngày) | CAGR% | equity | ret-2025% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| T170 (`X1_GS_T170_2021`) | 1089 | 606.26 | 0.0516 | -11.844 | 92 | 29.27 | 111,070 | 32.7 |
| gate-1.0=T100 (`X1_C3_FULL_2021`) | 2559 | 1103.86 | 0.1016 | -16.129 | 248 | 31.94 | 121,770 | 16.5 |
| BR nhị phân (top-50, Bước 6) | 1582 | 741.83 | 0.0827 | -11.842 | 180 | 30.12 | 114,410 | 22.9 |
| BRC (liên tục, all-coin, Bước 7) | 1689 | 753.54 | 0.0925 | -13.216 | 221 | 31.28 | 119,066 | 28.7 |
| **BRCT50 (liên tục, top50)** | **1776** | **811.96** | **0.0892** | **-13.223** | **223** | **31.04** | **118,080** | **26.8** |

CAGR CI: u2 dùng CI-floor T170 = **14.80%** (block-bootstrap 72h, cagrci_t170.txt) — BRCT50 CAGR
31.04 clear thừa. (Không tính CI block-bootstrap riêng cho BRCT50; theo tiền lệ BRC — u-tiêu chí
chỉ cần CI-floor T170.)

### UW theo năm | CAGR theo năm (%)
| tag | UW21 | UW22 | UW23 | UW24 | UW25 || C21 | C22 | C23 | C24 | C25 |
|---|--:|--:|--:|--:|--:||--:|--:|--:|--:|--:|
| T170 | 37 | 72 | 63 | 92 | 52 || 12.2 | 19.6 | 35.0 | 32.1 | 32.7 |
| T100 | 47 | 64 | 45 | 121 | 227 || 9.3 | 17.3 | 60.4 | 45.3 | 16.5 |
| BR | 46 | 72 | 63 | 121 | 58 || 4.2 | 19.6 | 47.0 | 45.2 | 22.9 |
| BRC | 46 | 76 | 66 | 119 | 221 || 5.9 | 17.0 | 47.7 | 44.5 | 28.7 |
| **BRCT50** | 46 | 73 | 66 | 119 | **223** || 6.0 | 17.2 | 46.8 | 46.0 | **26.8** |

## 3. Khẩu vị hiện hành (`x1_rates.py --appetite current --k 1`; coin<=15% KHÔNG đo)

| tag | 2021 | 2022 | 2023 | 2024 | 2025 | Tổng |
|---|---|---|---|---|---|---|
| T170 | PASS | PASS | PASS | PASS | PASS | **PASS 5/5** |
| BR | PASS | PASS | PASS | PASS | PASS(UW=58) | **PASS 5/5** |
| BRC | PASS | PASS | PASS | PASS | FAIL(UW=221) | **FAIL 2025** |
| **BRCT50** | PASS | PASS | PASS | PASS | **FAIL**(UW=223) | **FAIL 2025** |

BRCT50-2025: maxDD -6.49%, ret 26.75%, quý_min +0.37% ĐỀU đạt, chỉ **UW=223>200** vỡ khẩu vị
(y hệt cơ chế fail của BRC).

## 4. u1–u5 (khoá PREREG)
| # | Tiêu chí | Ngưỡng | BRCT50 | KQ |
|---|---|---|---|---|
| u1 | n_eff(BRCT50) >= 1.5×n_eff(T170) | >=909.38 | 811.96 (×1.339) | **FAIL** |
| u2 | khẩu vị current PASS mọi năm + CAGR>=14.80 | 5/5 + CAGR>=14.8 | FAIL 2025 (UW=223); CAGR=31.04 | **FAIL** |
| u3 | maxDD >= -14.805 VÀ UW <= 115 | cả 2 | maxDD -13.223 (PASS), UW 223 (FAIL) | **FAIL** |
| u4 | ret2025 >= 0.95×32.7=31.07 VÀ (nếu flat) UW<flat | ret-part | ret2025 26.75<31.07 (FAIL) | **FAIL** |
| u5 | CAGR23&24 >= 90%×T100 | 23>=54.39, 24>=40.75 | 23=46.78 (FAIL), 24=46.00 (PASS) | **FAIL** |

Không chạy flat-control BRCT50-0: BRCT50 KHÔNG pass u2+u4 (điều kiện kích hoạt PREREG §3/§7) ⇒
NULL rõ, KHÔNG cần attribute adaptive-vs-flat.

**Verdict: NULL** — u1–u5 đều fail. Chỉ các NỬA tiêu chí đạt: u3-maxDD (-13.2>=-14.8), u5-2024
(46.0>=40.75), quý/maxDD của khẩu vị 2025.

## 5. Phát hiện cốt lõi (cho MASTER) — DỰ BÁO SAI Ở TẦNG KẾT QUẢ
1. **Gate-2025 top50 NỚI hơn all-coin ĐÚNG dự báo (mức GATE)**: mean 1.314 (top50) < 1.423
   (all-coin BRC) — top50 gồm majors mạnh 2025 nên "đọc" thị trường khoẻ hơn, gate mở gần 1.0
   đầu 2025. Dự báo (a) MASTER về HƯỚNG gate đúng.
2. **NHƯNG ret-2025 KHÔNG gần T170 hơn — NGƯỢC dự báo (mức KẾT QUẢ)**: ret-2025(BRCT50)=**26.8**
   < BRC 28.7 < T170 32.7. Xếp hạng giữ-2025: **T170 32.7 > BRC 28.7 > BRCT50 26.8 > BR 22.9 >
   T100 16.5.** Top50 giữ 2025 KÉM HƠN cả BRC (all-coin), TRÁI hẳn giả thuyết "loosen 2025 nhiều
   hơn -> giữ 2025 tốt hơn". UW-2025=223 (≈ BRC 221, vẫn vỡ khẩu vị).
3. **Nghịch lý này CỦNG CỐ kết luận audit đối kháng**: nới gate 2025 (size lớn hơn, +87 lệnh so
   BRC) KHÔNG kiếm thêm lợi — thậm chí ret-2025 GIẢM nhẹ trong khi UW-2025 vẫn dài y nguyên. Đúng
   như audit: lệnh mở lúc breadth-thấp lãi NGANG lệnh breadth-cao ⇒ gate breadth cắt/nới KHÔNG
   phân biệt được theo lãi/lỗ (coverage thời-gian ≠ discrimination tầng-lệnh). Mở gate rộng hơn
   chỉ TĂNG phơi nhiễm vào đúng chuỗi chop/underwater 2025 mà không tăng edge.
4. **BRCT50 vs BRC (cùng họ liên tục)**: n 1776 vs 1689 (+87), n_eff 812 vs 754, nhưng equity
   118.1k < 119.1k, CAGR 31.04 < 31.28, maxDD -13.22 ≈ -13.22, UW 223 ≈ 221. Đổi định nghĩa
   breadth all-coin->top50 gần như KHÔNG đổi hồ sơ risk/return toàn cục — chỉ dịch nhẹ theo hướng
   XẤU hơn.
5. **BRCT50 vs T170**: CAGR 31.04 vs 29.27 (+1.8pp), equity +6.3%, nhưng maxDD XẤU hơn (-13.2 vs
   -11.8), UW XẤU hơn nhiều (223 vs 92, vỡ khẩu vị 2025), ret-2025 THẤP hơn (26.8 vs 32.7). ⇒
   KHÔNG phải "ứng viên incumbent mạnh".

## 6. Đối chiếu dự báo PREREG (khoá trước)
| Dự báo | Thực tế | KQ |
|---|---|---|
| gate-2025 top50 ~1.33 (nới hơn all-coin 1.42) | 1.314 | ĐÚNG (mức gate) |
| BRCT50 giữ ret-2025 GẦN T170 NHẤT (>28.7) | 26.8 < BRC 28.7 | **SAI** (mức kết quả) |
| (1) u1 vẫn fail ×1.5 | ×1.339 FAIL | ĐÚNG |
| (2) u3 UW<=115 fail | UW=223 FAIL | ĐÚNG |
| (3) u2 khẩu vị fail 2025 | UW=223>200 FAIL | ĐÚNG |
| (4) u4-ret có thể PASS (điểm sáng kỳ vọng) | 26.8<31.07 **FAIL** | **SAI** |
| (5) u5-2023 fail | 46.8<54.39 FAIL | ĐÚNG |
| Phán quyết NULL "ít tệ nhất" | NULL, KHÔNG "ít tệ nhất" (BRC giữ 2025 tốt hơn) | Verdict ĐÚNG, sắc thái SAI |

Điểm sáng kỳ vọng DUY NHẤT (u4-ret) KHÔNG thành: top50 không những không giữ 2025 gần T170 hơn
mà còn kém BRC. Dự báo cốt lõi của round (top50 khắc phục điểm yếu 2025 của all-coin) BỊ BÁC.

## 7. Kết luận & khuyến nghị — ĐÓNG DỨT ĐIỂM HƯỚNG BREADTH
- **NULL.** BRCT50 (hoán vị cuối: liên tục × top50) fail u1–u5, và điều bất ngờ là giữ 2025 KÉM
  hơn BRC dù gate-2025 nới hơn. Ba biến thể gate breadth (BR nhị phân / BRC all-coin liên tục /
  BRCT50 top50 liên tục) + subset recon (Bước 8) + audit đối kháng đều NULL/NO-GO.
- **Bằng chứng hội tụ**: dù đổi (nhị phân↔liên tục) × (all-coin↔top50↔subset), trade-off
  breadth↔UW-2025 KHÔNG phá được cho T170. Nới gate = tăng phơi nhiễm KHÔNG tăng edge (audit:
  lệnh breadth-thấp ≈ breadth-cao về lãi). BRCT50 là bằng chứng mạnh nhất: nới ĐÚNG cửa 2025 (gate
  1.31) vẫn cho ret-2025 kém hơn — coverage thời-gian ≠ discrimination tầng-lệnh.
- **T170 vẫn là incumbent tốt nhất** trên khẩu vị + giữ-2025 (ret-2025 32.7, UW-2025 52).
- **Đóng dứt điểm hướng breadth-gate.** CẤM dredging (PREREG): KHÔNG mở biến thể mới trong round
  này. Roadmap: TASK D (event-alpha listing/delisting).

## 8. Thay đổi (0 dòng Java; dùng lại jar breadth-cont `06def68b`)
- Mới: `research/analysis/breadth_cont_csv_t50.py` (sinh `regime_cont_top50.csv`),
  `research/analysis/breadth_cont_t50_metrics.py` (u1-u5), `profiles/x1_c3_full_regime_brct50.properties`,
  `docs/prereg/PREREG_BREADTH_CONT_T50.md`, `docs/result/RESULT_BREADTH_CONT_T50.md`,
  `research/analysis/out/breadth_cont_t50_metrics.json`.
- Kaggle: dataset `sim-brc-overlay` version mới (thêm top50 CSV + prof_brct50, giữ jar `06def68b`
  + file BRC). Kernel `sim-brct50` (BRCT50), `sim-brct50-off-t170` (cổng OFF).
- Diff Java giữa `e66345e` (trước round) và HEAD = **0 dòng**.

---
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
