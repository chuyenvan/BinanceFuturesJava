# RESULT_FAMILY2_TP_SL (v2 — AMENDMENT 2026-09-27) — HỌ MỚI #1: **TP nhỏ + SL nhỏ, KHÔNG DCA → 0/4 PASS**

**Ngày:** 2026-09-27 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_FAMILY2_TP_SL.md` — bản gốc + **AMENDMENT viết TRƯỚC khi chạy arm**.
**Bản v1 (`372317b`) = BLOCKER** (không có công tắc TP) → **đã gỡ** bằng key GATED `SIM_TAKE_PROFIT_RATE`.
**Runner:** `research/analysis/family2_tp_run.py` · **Scorer:** `size_count_score.py --base cd-sel15 --k 4` · **Martingale:** `shape1_martingale.report`.
**Số thô:** `docs/result/family2_tp_sl.json` · `docs/result/family2_tp_martingale.json`.
**Chi phí:** 6 chặn Kaggle CPU (2 parity + 4 arm), **0** (0 sim Oracle). DEV only ≤ 2025-12-31 (0 run chạm 2026).

## 0. PHÁN QUYẾT
**0/4 arm PASS (a) VÀ (b′).** Cả 4 arm **LỖ NẶNG** (equity 11.111–12.465 từ 35.000; CAGR −20,5…−22,9 %; maxDD −64…−68 %;
UW 1.538–1.618). TP cố định **đã chạy đúng cơ học** (`TAKE_PROFIT_DONE` khớp đúng `entry·(1+TP)`, 709–1.141 lệnh/arm) —
nhưng **họ mới phía-thoát KHÔNG khả thi**: chốt lãi nhỏ (1–3 %) trong khi chi phí round-trip ~0,6–0,8 % + SL −1/−1,5 %
⇒ **lỗ đều đặn**; bỏ trailing ⇒ **mất luôn nguồn PnL duy nhất** (đuôi thắng).

## 1. CÔNG TẮC MỚI (VIỆC 1) — gated, mặc định OFF
| key | field | đơn vị | mặc định | nghĩa |
|---|---|---|---|---|
| `SIM_TAKE_PROFIT_RATE` | `Configs.TAKE_PROFIT_RATE` | rate (>0) | **`0f` = OFF** | cum đóng khi `priceClose ≥ firstEntryPrice·(1+TP)` |
| `SIM_TAKE_PROFIT_ONLY` | `Configs.TAKE_PROFIT_ONLY` | bool | **`false`** | `true` (khi TP>0): bỏ arm/trailing |

- **Causal**: chỉ dùng `priceClose` (đóng nến), **không** high/low; giá đóng = **mức TP** (không bao giờ tốt hơn TP).
- Thứ tự: sau cổng cắt lỗ (`PRE_ARM_SL`→`LOSER_TS`→`COND_EXIT`), **trước** cổng arm ⇒ **TP đóng trước, trailing fallback**;
  cùng nến cả SL lẫn TP ⇒ **SL thắng** (quy ước X2). `TP_ONLY=1` ⇒ bỏ hẳn arm/trailing.
- **Diff tối thiểu:** `Configs.java` **+11 dòng** · `SimulatorMarketLevelTicker1MStopLoss.java` **+24 dòng** ·
  `tools/kaggle_sim.py` **+6 dòng** (`extra_env`, cho `WFO_DISABLE_DCA=1` — key INFRA đọc từ env). Commit **`04f4039`**.

## 2. CỔNG PARITY (VIỆC 2) — **PASS CẢ HAI**
Jar mới `sim-jar-tpsl` (sha256 `d45f2f86680051f1fd577ba046f61b014f00809c80c6c101002d7d244c816146`), key TP **KHÔNG khai**:

| run | md5 `printDone.csv` | n | equity | so chuẩn | kết |
|---|---|---|---|---|---|
| `tp-par-kg0` (KEEPLEG0) | **`99e42b75cf1a2142f9cd14dc72e371ba`** | 1.085 | 103.083 | `99e42b75…/1085/103083` | **KHỚP** |
| `tp-par-t170` (T170) | **`efb793e2468ca3a7318da0f0ad23d4fc`** | 1.089 | 111.070 | `efb793e2…/1089/111070` | **KHỚP** |

⇒ key OFF **byte-identical** ⇒ cổng cho phép chạy arm.

## 3. BẢNG ARM (nền `N0`=`cd-sel15` DÙNG LẠI; `k=4`, inflate 1,6651)

| arm | cấu hình | n | entry/m | CAGR% | maxDD% | UW | qmin | conc% | `%top-1` | TF50 (USDT) | q*% | asym | sign% | equity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **N0** `cd-sel15` | (base, dùng lại) | 744 | 13,77 | **+17,29** | −6,27 | 166 | −3,36 | 6,77 | **19,13** | **−17.551** | 21,2 | **3,375** | 88,44 | 71.718 |
| **N1** `tp-n1` | TP 2 % + SL −1 % + DCA OFF | 2.563 | 47,45 | **−22,51** | −68,27 | 1.575 | −26,45 | 5,36 | −1,97* | **−26.940** | 3,90 | **1,976** | 31,25 | 11.111 |
| **N2** `tp-n2` | TP 1 % + SL −1 % + DCA OFF | 2.734 | 53,21 | **−22,90** | −67,14 | 1.538 | −20,99 | 5,39 | −0,48* | **−25.566** | 3,66 | **11,462** | 41,84 | 11.502 |
| **N3** `tp-n3` | TP 3 % + SL −1,5 % + DCA OFF | 2.270 | 42,03 | **−20,51** | −64,39 | 1.618 | −23,36 | 5,34 | −3,23* | **−29.669** | 4,41 | **1,312** | 31,37 | 12.465 |
| **N4** `tp-n4` | = N1 + `LOSER_TIME_STOP=24h` | 2.563 | 47,45 | **−22,51** | −68,27 | 1.575 | −26,45 | 5,36 | −1,97* | **−26.940** | 3,90 | **1,976** | 31,25 | 11.111 |

\* `%top-1` **âm** = artifact của `ΣPnL<0` ⇒ **KHÔNG** phải PASS (a).
**N4 ≡ N1 y hệt** ⇒ `SIM_LOSER_TIME_STOP_HOURS=24` **vô hiệu** (mọi cụm đã bị TP/SL đóng trong ~1 nến; không cụm nào sống tới 24h).

### 3.1 Bộ 4 thước chuẩn + dự bị
| arm | wl_ratio | tf_5 | loss_mean | conc_5 | median | tf_10 |
|---|---|---|---|---|---|---|
| N0 | 0,296 | 27,75 | −337,0 | 46,65 | 62,08 | 17,42 |
| N1 | 0,506 | −10,59 | −17,6 | −7,9 | −11,03 | −11,78 |
| N2 | 0,087 | −9,89 | −17,0 | −1,5 | −7,65 | −10,55 |
| N3 | 0,762 | −11,86 | −22,2 | −13,4 | −15,21 | −13,64 |
| N4 | 0,506 | −10,59 | −17,6 | −7,9 | −11,03 | −11,78 |

## 4. RÀO — PASS/FAIL
| arm | (a) `%top-1≤15` (& `ΣPnL>0`) | (b′) `TF50>0` | CẢ HAI | rào cũ (appetite latest) | gross TB/MAX ≤70 |
|---|---|---|---|---|---|
| N0 | FAIL 19,13 | FAIL −17.551 | **FAIL** | PASS | PASS 0,03 / 33,2 |
| N1 | **FAIL (LỖ)** | FAIL −26.940 | **FAIL** | **FAIL** (ret≤0 mọi năm; UW 343–363; qmin −20,2/−26,4) | PASS 0,03 / 33,2 |
| N2 | **FAIL (LỖ)** | FAIL −25.566 | **FAIL** | **FAIL** (ret≤0 mọi năm; UW 264–363; qmin −21,0) | PASS 0,02 / 33,3 |
| N3 | **FAIL (LỖ)** | FAIL −29.669 | **FAIL** | **FAIL** (ret≤0 mọi năm; UW 303–363; qmin −23,4) | PASS 0,05 / 33,0 |
| N4 | **FAIL (LỖ)** | FAIL −26.940 | **FAIL** | **FAIL** (như N1) | PASS 0,03 / 33,2 |

**PASS (a)=0/4 · PASS (b′)=0/4 · CẢ HAI=0/4.** Trần gross 70 % (định nghĩa LEDGER, errata §11) **không bind** (MAX 33,3 % < 60 %).

## 5. 5 RATE + CI vs N0 (block-72h, 2.000 rep, seed `20260905`, inflate 1,6651) + luật siết §10.2
| arm | ngoài CI | "hướng TỐT" §10.2 | kết |
|---|---|---|---|
| N1 | win%, TSloss%, mP\|SL, meanP, mMargin | **mP\|SL** (artifact size) | KHÔNG (<2) |
| N2 | win%, TSloss%, mP\|SL, meanP, mMargin | **mP\|SL** | KHÔNG (<2) |
| N3 | win%, TSloss%, mP\|SM, mP\|SL, meanP, mMargin | **mP\|SL** | KHÔNG (<2) |
| N4 | như N1 | **mP\|SL** | KHÔNG (<2) |

- `win%` (−46,6…−57,2) và `TSloss%` (+48,5…+59,1) **ngoài CI theo hướng XẤU ở cả 4** — **thay đổi chất lượng THẬT**
  (win-rate sụp, tỉ trọng lệnh thua-tăng), không phải artifact.
- `mP|SL` dương ngoài CI ở mọi arm nhưng **là artifact nhân size USDT** ⇒ luật siết chỉ còn **1 rate** ⇒ **KHÔNG đạt**.

## 6. 3 CHỈ SỐ MARTINGALE
| arm | conc 1 coin% | conc>15 | lỗ lớn nhất 1 vị thế/1 coin (USDT) | coin "chết" (ΣPnL<0) |
|---|---|---|---|---|
| N0 | 6,77 | KHÔNG | **−2.483** (2025) | 52 / 272 |
| N1 | 5,36 | KHÔNG | −276 (2025) | **203 / 254** |
| N2 | 5,39 | KHÔNG | −252 (2025) | **202 / 254** |
| N3 | 5,34 | KHÔNG | −297 (2025) | **193 / 254** |
| N4 | 5,36 | KHÔNG | −276 (2025) | **203 / 254** |

- **conc 1 coin ≤15 %: PASS mọi arm** (không tập trung 1 coin).
- **SL nhỏ CÓ chặn lỗ đuôi 1 vị thế** (−2.483 → −252…−297, **giảm ~9×**) — nhưng **coin "chết" 52 → 193–203** (≈ 80 % coin âm) ⇒ chặn đuôi nhưng **giết toàn bộ expectancy**.

## 7. CƠ CHẾ (vì sao lỗ) — kiểm trên `printDone` N1
- `TAKE_PROFIT_DONE` **đúng cơ học**: cột `profit` = **+2,0000 %** chính xác (min 1,99999 · max 2,00000), 798 lệnh; giữ TB 0,1 h.
- `STOP_LOSS_DONE` 1.765 lệnh; PnL/lệnh: **TP +8,94 USDT** vs **SL −17,58 USDT** vs win 31,2 % ⇒
  `0,312·8,94 − 0,688·17,58 ≈ −9,4 USDT/lệnh` ⇒ lỗ hệ thống.
- Bỏ trailing ⇒ lệnh thắng **không còn được nuôi**; TP nhỏ (1–3 %) **nhỏ hơn/sát chi phí** (fee 0,006 + slippage 2 chân
  ≈ 0,6–0,8 %) trong khi SL −1 % ăn lỗ thật ⇒ **asym không thể <1 cùng PnL dương**.

## 8. TRẢ LỜI (bắt buộc)
1. **Parity OFF (key không khai) khớp cả 2 md5?** **CÓ** — `99e42b75…` (KEEPLEG0) & `efb793e2…` (T170), n/eq khớp.
2. **Arm nào PASS (a) VÀ (b′)?** **KHÔNG arm nào (0/4)**. (a) 0/4 (cả 4 **LỖ**, `ΣPnL<0`); (b′) 0/4
   (`TF50` = −26.940 / −25.566 / −29.669 / −26.940, **âm hơn cả N0** −17.551).
3. **`asym`<1 mà PnL DƯƠNG — có chưa?** **KHÔNG.** Cả 4 arm `asym` **>1** (min = N3 `1,312`) **và đều LỖ**. Không có
   arm nào vừa `asym<1` vừa dương ⇒ **câu hỏi trung tâm vẫn NULL**, thậm chí **xấu hơn** họ cũ (ở đó `asym<1` ⟺ lỗ).
4. **Bỏ trailing/arm có làm `%top-1` giảm mạnh?** **Có, nhưng theo nghĩa vô nghĩa**: `ΣPnL<0` ⇒ `%top-1` **âm** (artifact).
   Bỏ trailing **phá luôn nguồn PnL duy nhất** (đuôi thắng) ⇒ "hết phụ thuộc đuôi" nhưng **PnL cũng biến mất** — không phải
   họ "PnL không phụ thuộc đuôi" mà là họ **không còn PnL**.
5. **KẾT LUẬN — họ mới khả thi?** **KHÔNG** (phía-thoát, trong engine hiện tại + nhãn hiện tại). Bước tiếp:
   **(a) ĐỔI PHÍA TÍN HIỆU/nhãn train** sang mục tiêu nhỏ + horizon ngắn (nhãn dự báo move nhỏ để TP nhỏ > chi phí);
   **(b) đổi khung thời gian** (nhịp/khung nến lớn hơn để 1–3 % vượt phí); **(c) đổi cách chọn coin** (thanh khoản/chi phí thấp
   để hạ fee+slippage). Trần cơ học: **TP phải > chi phí round-trip (~0,8 %)** ⇒ TP 1 % gần như chắc lỗ sau phí.

## 9. MỤC BỎ + LÝ DO
- **Không bỏ arm nào** (ngân sách đủ: 4 arm ≤ 5 slot, chạy song song 4).
- **N4 vô hiệu** (`LOSER_TIME_STOP=24h` không đổi gì: TP/SL đóng trước 24h) — báo cáo, giữ số liệu.
- **Không bỏ CI cho (a)/(b′)/4 thước**: là đại lượng tổng toàn chuỗi, không phải ước lượng mẫu (nhất quán vòng trước).
- **KHÔNG chạm** 2026 (date_last ≤ 20251230), production/242/ONNX/`NUM_FEATURES`/`extractFeatures45`/LIVE.

## 10. TÁI LẬP
```
python3 research/analysis/family2_tp_run.py par        # 2 chặn parity (key TP không khai)
python3 research/analysis/family2_tp_run.py arms       # 4 arm N1..N4
python3 research/analysis/size_count_score.py tp-n1 tp-n2 tp-n3 tp-n4 --base cd-sel15 --k 4 \
        --json docs/result/family2_tp_sl.json
python3 research/analysis/shape1_martingale.py cd-sel15 tp-n1 tp-n2 tp-n3 tp-n4   # (JSON -> family2_tp_martingale.json)
```
Kernel: `chuyendinh/sim-tp-par-kg0` · `sim-tp-par-t170` · `sim-tp-n1` · `sim-tp-n2` · `sim-tp-n3` · `sim-tp-n4`
(private, Kaggle CPU, chi phí 0). Jar dataset mới: `chuyendinh/sim-jar-tpsl`. Commit code: `04f4039`. **KHÔNG push.**
