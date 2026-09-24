# RESULT — EXIT VARIANTS TRÊN NỀN NHIỀU LỆNH (GD92 & T100)

Pre-reg: `docs/PREREG_EXIT_HIGH_N.md` (commit **`33f0b77`**, viết TRƯỚC khi chạy).
Script: `research/analysis/exithighn_run.py` + `research/analysis/exithighn_score.py` (commit **`875cd75`**).
Code: `git cherry-pick -n 1db0613` (branch `gd92-recheck`) vào `module` HEAD `b50833f`
— **KHÔNG commit, KHÔNG merge**; sau khi build đã `git reset` + `git checkout -- src/`
⇒ `git diff HEAD -- src/` **rỗng**, `module/src` **NGUYÊN TRẠNG** (không còn file mới, không còn sửa).
Jar mới sha256 **`bb282f40d66b97ec435d4f5bd2678dbbd29dc11965bda700f43e14c2f28654bb`**
(99,709,921 byte; `mvn -o package` tests BẬT: **154 test / 0 fail**, BUILD SUCCESS 24.1s),
đóng gói trong Kaggle dataset **`chuyendinh/sim-jar-exithighn`** (`JAR_PROVENANCE.txt` kèm theo).
Mọi sim chạy **trên Kaggle CPU kernel** (`docs/KAGGLE_SIM.md`) — **KHÔNG** chạy Java/sim trên Oracle
(Oracle chỉ build jar). Cửa sổ `20210701 .. 20251231` (DEV, 1,644 ngày), `TICKER_SOURCE=file`,
mapper **863** (≥ 800 guard) ở **MỌI** chân, `jar_sha256` = `bb282f40…` ở **MỌI** chân.
Chi phí Kaggle: **0**.

---

## 0. KẾT LUẬN (một dòng)

> **NULL, và câu trả lời cho câu hỏi trung tâm là KHÔNG: hiệu ứng của exit KHÔNG tăng theo n.**
> Trên **cả hai nền nhiều lệnh** (GD92 **2,632 leg**, T100 **2,559 leg**) — gấp ~2.4 lần T170 (1,089) —
> **6/6 chân exit cho 0 TỐT / 0 XẤU ngoài CI** (ngoài ở CẢ HAI độ rộng), y hệt mốc **T170 = 0/5**.
> Độ lớn Δ **không lớn hơn** ở n cao — nó **nhỏ hơn** (nền G: |Δ| ≤ 0,13; nền T: |Δ| ≤ 0,24 so với
> biên độ nhiễu của chính rate đó). Giả thuyết của owner ("trailing không đổi vì T170 ít lệnh")
> **bị bác bỏ có kiểm chứng**: nhiều lệnh gấp 2.4 lần **vẫn** không làm exit đo được.
> **KHÔNG GO** — và điều đó là **tất yếu** vì T100/GD92 base đã **FAIL rào cứng toàn kỳ** từ trước
> (T100 UW 248 + conc 27.23%; GD92 UW 278). Đây là **phép đo cơ chế**, không phải vòng tìm incumbent.

---

## 1. GIẢI TRÌNH KẾT QUẢ VÒNG TRƯỚC (bắt buộc, làm trước)

### 1.1 Vòng trước **sai NHÃN NỀN**, số liệu **không sai**

`docs/RESULT_GD92_X_EXIT.md` (commit `4e263c2`) gọi chân **"(A) GD92-only"**, nhưng runner của vòng đó
(`research/analysis/gd92xexit_run.py`, `JOBS["a"]`) dùng **`profile="x1_gs_t170"`** + 2 key rolling.
`x1_gs_t170` = **T170** (gate scale **1.70**, 1,089 leg); định nghĩa GD92 là
**`x1_c3_full`** (gate scale **1.00**) + 2 key rolling. Bằng chứng nằm ngay trong chính báo cáo cũ:
chân "A" ra **1,108 leg / equity 99,179** — đúng cỡ **nền T170** (1,089 leg), **không** phải cỡ
**nền GD92 (2,632 leg)**.

⇒ **Chưa bao giờ có phép thử exit trên nền nhiều lệnh.** Cả A/B/C/D vòng trước đều nằm trên nền
T170 (1,089 leg) — chỗ đã test 6 lần trước đó. Số liệu vòng trước **vẫn đúng** (parity byte-identical,
CI đúng, rào cứng đúng); chỉ **nhãn nền** sai. Ghi rõ: **lỗi dán nhãn, không phải lỗi số.**

### 1.2 Tái lập GD92 base trong **đúng setup này** — **KHỚP CHÍNH XÁC**

| | tham chiếu `RESULT_GD92_RECHECK` (Oracle, `wfo_ds_x1_2021`) | vòng này (`hn-g92`, Kaggle) |
|---|---|---|
| leg | **2,632** | **2,632** ✅ |
| equity | **133,944** | **133,944** ✅ |
| CAGR / maxDD / UW | 34.76% / −16.55% / 278 | 34.76% / −16.55% / 278 ✅ |

`hn-g92` = profile `x1_c3_full` + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`.

**Chứng minh cục bộ tập key/giá trị trùng khít `profiles/archive/x1_gd92.properties`** (21 key,
0 dòng khác) ⇒ `PROFILE_HASH` JVM-kiểu = **`52ee74bb5477b363`** (khớp `RESULT_GD92_RECHECK` §0(c)).
Trên Kaggle hash in ra là `3b747e30f1bac7b6` — **khác là ĐÚNG**, vì `WFO_FUNDING_PRED_DIR` bị ghi đè
sang đường mount Kaggle (`docs/KAGGLE_SIM.md` §0.3); hash này **không** dùng để so parity.

Nếu chạy từ **2022-01** (`wfo_ds_x1`) thì mốc là **2,355 / 128,979** (bản cũ `X1_C3_FULL_GD92`) —
vòng này **không** rơi vào trường hợp đó (đó là dấu hiệu SAI CỬA SỔ, pre-reg §3 P3).

### 1.3 T100 baseline — dùng lại chân parity, cùng jar

`hn-t100` = `x1_c3_full`, md5 `dc16e4da6ff6cb7b8d41c592bc3d9c45`, **2,559 leg / 121,770** — trùng
byte với `dc16e4da` đã xác minh nhiều vòng (`RESULT_GD92_RECHECK` §0(b), `RESULT_GD92_X_EXIT` §0).

### 1.4 Trả lời 1 câu

> **Lần trước chạy SAI không?** — Chạy **đúng hết** (cùng jar, cùng cổng parity PASS, cùng dataset
> vòng); chỉ **dán nhãn nền sai** (gọi "GD92-only" cho cấu hình trên nền T170). **Số liệu không sai,
> nhãn sai** — và hệ quả nghiêm trọng của nhãn sai là: **kết luận "exit không tác dụng" chưa từng
> được kiểm trên nền nhiều lệnh**, đúng như owner nghi ngờ.

---

## 2. CỔNG CHẶN — **TẤT CẢ PASS** (đo trước khi đọc bất kỳ kết quả nào)

| cổng | kỳ vọng | đo được | kết |
|---|---|---|---|
| **P1** `hn-par1` = T170 | md5 `efb793e2…`, n 1089, eq 111,070 | md5 **`efb793e2468ca3a7318da0f0ad23d4fc`**, n **1089**, eq **111,070** | **PASS** |
| **P2** `hn-t100` | md5 `dc16e4da…`, n 2559, eq 121,770 | md5 **`dc16e4da6ff6cb7b8d41c592bc3d9c45`**, n **2559**, eq **121,770** | **PASS** |
| **P3** `hn-g92` tái lập | n ≈ 2,632 · eq ≈ 133,944 | n **2,632** · eq **133,944** | **PASS** |
| **P4** `[GATE-ROLL]` bật thật | pct=0.92 / W=90d / `nBeforeFirst=0` | `pct=0.92 window=90d \| 39510 moc gio \| moc dau 1624989600000` (2021-06-30) `\| nguong min=0.00456 max=0.01265`; **0** cảnh báo truy vấn trước mốc đầu | **PASS** |
| **P5** key bind thật | md5 khác baseline | **6/6** chân exit có md5 riêng (khác md5 baseline nền) | **PASS** |

`hn-par1/hn-t100` **byte-identical** với md5 tham chiếu dù cũng bật `SIM_TRAIL_TRACE=1`
⇒ **jar mới (`bb282f40`) không dịch một bit nào** khi không khai báo key rolling, và file trace
là **đo-lường-only** (xác nhận lại tiền lệ `tl-par == tl-part`).

**md5 `printDone.csv` 9 chân** (đều **khác** nhau ⇒ mọi override **bind thật**):

| tag | md5 | tag | md5 |
|---|---|---|---|
| `hn-par1` | `efb793e2468ca3a7318da0f0ad23d4fc` | `hn-g-cp` | `43fb90ee41c29b39ebd2ffc64b19996b` |
| `hn-t100` | `dc16e4da6ff6cb7b8d41c592bc3d9c45` | `hn-t-hi` | `055ca7fbfc58a6805707877c96315d9a` |
| `hn-g92` | `cd913759ecd4bf50adab2b818eaf9525` | `hn-t-la` | `b9ccfb767ad892c0fd5c7be36193bae4` |
| `hn-g-hi` | `f98ded9d40632df2e0896a7aa897cd0e` | `hn-t-cp` | `82e70f47641622199e6803e2ddc6eb12` |
| `hn-g-la` | `058d51bb5f6b38a981a79eb08bbe4e75` | | |

`hn-g92` (`cd913759…`) **≠** `hn-t100` (`dc16e4da…`) ⇒ rolling gate **thật sự tác động** ở nền này.
`grep "GATE-ROLL"` có mặt ở **cả 4** chân nền G (`hn-g92`, `hn-g-hi`, `hn-g-la`, `hn-g-cp`) và **không** có ở 4 chân nền T (log `[GATE-ROLL]` giống nhau tuyệt đối ở cả 4 chân nền G).
`[CFG] TS_LADDER ON lo=[0.0, 0.1, 0.25, 0.5, 1.0] gaps=[0.04, 0.08, 0.15, 0.25, 0.35]` có ở
`hn-g-la`/`hn-t-la`.

---

## 3. BẢNG CHÍNH — 5 RATE CHẤT LƯỢNG (toàn bộ leg)

| tag | nhãn | n | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---|---|---|---|---|---|---|
| `hn-par1` | **T170** (mốc incumbent) | 1,089 | 88.25 | 9.73 | 7.642 | −16.992 | 5.244 |
| `hn-t100` | **T100 base** | 2,559 | 84.33 | 15.36 | 7.230 | −19.189 | 3.173 |
| `hn-g92` | **GD92 base** | 2,632 | 83.66 | 16.15 | 7.231 | −17.020 | 3.315 |
| `hn-g-hi` | GD92 + HINGE V3 | 2,640 | 83.71 | 16.10 | 7.237 | −17.028 | 3.331 |
| `hn-g-la` | GD92 + LADDER L1 | 2,628 | 83.79 | 16.10 | 7.156 | −16.965 | 3.274 |
| `hn-g-cp` | GD92 + CAP 10/30 | 2,608 | 83.67 | 16.22 | 7.363 | −16.797 | 3.444 |
| `hn-t-hi` | T100 + HINGE V3 | 2,571 | 84.40 | 15.29 | 7.279 | −19.214 | 3.229 |
| `hn-t-la` | T100 + LADDER L1 | 2,557 | 84.47 | 15.21 | 7.112 | −18.949 | 3.147 |
| `hn-t-cp` | T100 + CAP 10/30 | 2,547 | 84.41 | 15.23 | 7.223 | −19.013 | 3.226 |

Exit **không** đổi số leg đáng kể (2,608–2,640 vs 2,632; 2,547–2,571 vs 2,559 ≈ ±1%) — đúng cơ chế:
exit chỉ đổi **đường ra**, không đổi **điểm vào**.

---

## 4. CI — 3 MỐC ĐO

CI block-72h, 2000 rep, seed **20260905**, anchor 2021-07-01, **CẢ HAI** độ rộng (legacy **×1.21** +
chuẩn hoá **`inflate(k=3)=1.482304`**). **"Ngoài CI" = ngoài ở CẢ HAI độ rộng.**

### 4.1 ⭐ MỐC 1 — exit arm vs **BASELINE CỦA CHÍNH NỀN** (câu hỏi trung tâm)

| nền | chân | win% Δ | TSloss% Δ | mP\|SM Δ | mP\|SL Δ | meanP Δ | **TỐT** | **XẤU** |
|---|---|---|---|---|---|---|---|---|
| **G** (n=2,632) | `hn-g-hi` | +0.050 | −0.049 | +0.006 | −0.007 | +0.016 | **0/5** | **0/5** |
| **G** | `hn-g-la` | +0.127 | −0.052 | −0.075 | +0.056 | −0.041 | **0/5** | **0/5** |
| **G** | `hn-g-cp` | +0.003 | +0.072 | +0.132 | +0.224 | +0.130 | **0/5** | **0/5** |
| **T** (n=2,559) | `hn-t-hi` | +0.073 | −0.072 | +0.049 | −0.025 | +0.057 | **0/5** | **0/5** |
| **T** | `hn-t-la` | +0.144 | −0.144 | −0.118 | +0.239 | −0.025 | **0/5** | **0/5** |
| **T** | `hn-t-cp` | +0.083 | −0.124 | −0.007 | +0.175 | +0.054 | **0/5** | **0/5** |

- **TỔNG: 0 TỐT / 0 XẤU trên 30 phép so (6 chân × 5 rate), ở CẢ HAI độ rộng.**
- Chỉ **2/30** phép ra **ngoài ở độ rộng legacy ×1.21** và **rơi vào trong** ở độ rộng chuẩn hoá:
  `hn-t-hi` win% `+0.073` CI@1.21 `[+0.006, +0.145]` (CI@1.4823 `[−0.009, +0.160]`) và
  `hn-t-hi` TSloss% `−0.072` `[−0.144, −0.006]` (`[−0.159, +0.009]`). Theo luật đã khoá
  ("ngoài ở CẢ HAI") ⇒ **không tính**. Ghi ra để không tô hồng: đây là **2 tín hiệu dương yếu nhất**
  trong cả vòng, và chúng **không sống sót** khi mở rộng CI cho đúng `k=3`.
- **Độ lớn Δ ở nền G nhỏ hơn cả nền T** (|Δ| ≤ 0,13 vs ≤ 0,24) ⇒ thêm lệnh **không** làm hiệu ứng lớn lên.

### 4.2 ⭐ TRẢ LỜI CÂU HỎI TRUNG TÂM — hiệu ứng exit có TĂNG theo n không?

| nền | n leg | # rate ngoài CI (CẢ HAI độ rộng) | |Δ| lớn nhất |
|---|---|---|---|
| **T170** (3 exit trên nền T170, vòng `RESULT_GD92_X_EXIT` §2b: (B)−(A), (C)−(A)) | 1,089 | **0/5** | — |
| **T100** (3 exit trên nền T100, vòng này) | **2,559** | **0/5** | 0.239 (mP\|SL, `hn-t-la`) |
| **GD92** (3 exit trên nền GD92, vòng này) | **2,632** | **0/5** | 0.224 (mP\|SL, `hn-g-cp`) |

⇒ **KHÔNG tăng theo n.** n tăng **2.42×** (1,089 → 2,632) mà số rate ngoài CI **giữ nguyên 0**,
và biên độ điểm-ước-lượng **không** phóng to tương ứng. **Giả thuyết "T170 ít lệnh nên trailing không
đổi" bị bác bỏ.** Lý do đúng của việc exit không đổi **không phải** n nhỏ, mà là **cơ chế**:
exit chỉ dịch đường ra của một tập leg có **cùng điểm vào**, và trong 5 rate chất lượng nó chỉ
đổi **phân bố đuôi** của một số ít leg (xem §6) — dưới ngưỡng nhiễu của block-72h.

### 4.3 MỐC 2 — tách riêng **tác dụng GATE** (GD92 base vs T100 base)

| rate | Δ | CI @1.21 | CI @1.4823 | ngoài CẢ HAI | hướng |
|---|---|---|---|---|---|
| win% | −0.667 | [−2.092, +0.674] | [−2.403, +0.985] | – | – |
| TSloss% | +0.790 | [−0.697, +2.343] | [−1.039, +2.685] | – | – |
| mP\|SM | +0.001 | [−0.331, +0.331] | [−0.406, +0.406] | – | – |
| mP\|SL | +2.168 | [+0.068, +4.671] | [−0.450, +5.189] | – (chỉ ngoài @1.21) | – |
| meanP | +0.142 | [−0.329, +0.686] | [−0.444, +0.801] | – | – |

⇒ **0 TỐT / 0 XẤU** — **trùng khớp kết luận `RESULT_GD92_RECHECK` §3** ("cơ chế rolling không tạo ra
khác biệt chất lượng lệnh nào đo được so với chính nền của nó"), lần này ở `k=3` và trên Kaggle.

### 4.4 MỐC 3 — mọi chân vs **T170** (mốc incumbent; tham chiếu, không phải tiêu chí)

**Tất cả 8 chân còn lại đều 3 XẤU / 0 TỐT** ngoài CI (cả hai độ rộng): `win%` −3.77…−4.58 ·
`TSloss%` +5.48…+6.49 · `meanP` −1.80…−2.10; `mP|SM`, `mP|SL` **trong** CI. Bao gồm cả
`hn-t100` (−3.916/+5.624/−2.071) và `hn-g92` (−4.583/+6.414/−1.929 — trùng đúng điểm-ước-lượng của
`RESULT_GD92_RECHECK` §3).
⇒ **Không chân nào trong vòng này tiến gần T170 về chất lượng lệnh**, dù equity/CAGR của nền G
**cao hơn** T170 (xem §5).

---

## 5. RÀO CỨNG `docs/RISK_APPETITE.md` — theo năm **VÀ** toàn kỳ

`maxDD ≤ 30%/năm` · `UW ≤ 200 ngày` · `quỹ xấu nhất ≥ −15%` · `không năm âm` · `tập trung 1 coin ≤ 15%`.

| tag | equity | CAGR% | maxDD toàn kỳ | UW toàn kỳ | qmin% | conc% | n | hold med (h) | turn (leg/ngày) | SumPnL |
|---|---|---|---|---|---|---|---|---|---|---|
| T170 (`hn-par1`) | 111,070 | 29.27 | −11.84 | 92 | −0.92 | 9.77 | 1,089 | 4.8 | 0.662 | 76,070 |
| **T100 base** | 121,770 | 31.94 | −16.13 | **248** | −4.64 | **27.23** | 2,559 | 11.1 | 1.557 | 86,770 |
| **GD92 base** | 133,944 | 34.76 | −16.55 | **278** | −4.59 | 14.38 | 2,632 | 12.5 | 1.601 | 98,944 |
| GD92 + HINGE V3 | 134,540 | 34.90 | −16.50 | **278** | −4.00 | 14.40 | 2,640 | 11.5 | 1.606 | 99,541 |
| GD92 + LADDER L1 | 136,044 | 35.23 | −17.48 | **245** | −5.56 | 14.44 | 2,628 | 13.6 | 1.599 | 101,045 |
| GD92 + CAP 10/30 | **149,400** | **38.08** | **−17.65** | **249** | −5.58 | **15.29** | 2,608 | 14.2 | 1.586 | 114,400 |
| T100 + HINGE V3 | 128,464 | 33.52 | −15.80 | **240** | −3.59 | **27.08** | 2,571 | 9.8 | 1.564 | 93,465 |
| T100 + LADDER L1 | 119,710 | 31.44 | −17.07 | **240** | −5.00 | **28.35** | 2,557 | 12.0 | 1.555 | 84,710 |
| T100 + CAP 10/30 | 126,466 | 33.05 | −17.11 | **241** | −5.34 | **28.34** | 2,547 | 12.6 | 1.549 | 91,466 |

**Theo năm (maxDD% / UW / ret%)** — `P` = PASS năm đó:

| tag | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| T170 | −2.46/37/+12.21 P | −11.84/72/+19.58 P | −2.73/63/+34.96 P | −6.60/92/+32.14 P | −4.23/52/+32.71 P |
| T100 base | −7.35/47/+9.28 P | −12.46/64/+17.31 P | −2.51/45/+60.43 P | −11.36/121/+45.36 P | −10.60/**227**/+16.45 **F** |
| GD92 base | −7.74/47/+3.83 P | −13.21/69/+7.26 P | −5.24/63/+74.11 P | −11.36/114/+43.91 P | −6.11/116/+36.77 P |
| GD92 + HINGE V3 | −8.08/47/+3.44 P | −12.84/53/+8.16 P | −5.05/63/+73.97 P | −11.31/103/+42.20 P | −6.29/142/+38.27 P |
| GD92 + LADDER L1 | −7.83/46/+4.44 P | −13.11/73/+9.56 P | −5.48/63/+78.26 P | −11.43/129/+44.74 P | −6.81/164/+31.30 P |
| GD92 + CAP 10/30 | −7.89/47/+5.60 P | −13.25/73/+8.76 P | −5.48/63/+78.06 P | −12.03/149/+53.89 P | −7.00/112/+35.28 P |
| T100 + HINGE V3 | −7.50/47/+9.62 P | −12.10/113/+17.81 P | −2.51/45/+64.02 P | −11.31/119/+45.45 P | −12.00/**223**/+19.21 **F** |
| T100 + LADDER L1 | −7.41/46/+10.40 P | −12.48/158/+19.90 P | −2.79/57/+57.24 P | −11.43/129/+43.76 P | −10.79/**234**/+14.37 **F** |
| T100 + CAP 10/30 | −7.44/47/+10.44 P | −12.60/158/+18.88 P | −2.83/61/+60.06 P | −11.77/148/+44.85 P | −9.33/**223**/+18.78 **F** |

- **Không năm nào âm** ở **mọi** chân. Quỹ xấu nhất ≥ −5.58% (trần −15%). maxDD năm ≤ 13.25% (trần 30%).
- **Theo năm:** nền **G** (base + 3 exit) **PASS cả 5 năm**; nền **T** (base + 3 exit) **FAIL 2025**
  (UW 223–234) — exit **không** sửa được bệnh UW 2025 của T100.
- **Toàn kỳ:**

| tag | toàn kỳ | lý do fail |
|---|---|---|
| T170 (`hn-par1`) | **PASS** | — |
| T100 base | **FAIL** | UW 248; conc 27.23% |
| GD92 base | **FAIL** | UW 278 |
| GD92 + HINGE V3 | **FAIL** | UW 278 |
| GD92 + LADDER L1 | **FAIL** | UW 245 |
| GD92 + CAP 10/30 | **FAIL** | UW 249; conc **15.29%** (> 15%) |
| T100 + HINGE V3 | **FAIL** | UW 240; conc 27.08% |
| T100 + LADDER L1 | **FAIL** | UW 240; conc 28.35% |
| T100 + CAP 10/30 | **FAIL** | UW 241; conc 28.34% |

> **Phải nói rõ (pre-reg §5 đã ghi trước):** T100 và GD92 base **đã FAIL toàn kỳ từ đầu**, nên
> **GO là KHÔNG THỂ** cho 2 nền này — **không phải** vì exit kém, mà vì **nền đã trượt veto**.
> Vòng này là **phép đo CƠ CHẾ**. Trong khung đó vẫn có thông tin thật:
> **CAP 10/30 trên nền GD92 hạ UW toàn kỳ 278 → 249 và UW 2025 116 → 112** (nhưng **đẩy maxDD lên
> −17.65%** và **vượt trần tập trung 15.29%**) — tức đổi chỗ rủi ro, **không** thêm chất lượng lệnh.
> **LADDER L1** hạ UW 278 → **245** nhưng cũng **đẩy maxDD lên −17.48%**.

---

## 6. ⭐ BẢNG PnL CHI TIẾT THEO NĂM (bắt buộc) — 9 chân

Cột `PnL(USDT)` = Σ cột `pnl` của `printDone.csv` theo năm **vào lệnh** (`start`);
`ret%`/`maxDD%`/`UW`/`qmin%`/`equity` từ **đường equity thật** trong `sim.out`.
`PnL/equity` **chỉ để báo cáo, KHÔNG dùng để chọn**.

### T170 (mốc, `hn-par1`, md5 `efb793e2`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 149 | 92.62 | 7.38 | 4.368 | 4,273 | +12.21 | −2.46 | 37 | +4.44 | 39,272 |
| 2022 | 198 | 83.84 | 11.11 | 3.861 | 7,688 | +19.58 | −11.84 | 72 | +2.90 | 46,960 |
| 2023 | 126 | 88.10 | 15.87 | 8.074 | 16,331 | +34.96 | −2.73 | 63 | −0.37 | 63,378 |
| 2024 | 281 | 90.04 | 10.68 | 4.769 | 20,403 | +32.14 | −6.60 | 92 | −0.92 | 83,695 |
| 2025 | 335 | 87.46 | 6.87 | 5.784 | 27,375 | +32.71 | −4.23 | 52 | +1.27 | **111,070** |

### T100 base (`hn-t100`, md5 `dc16e4da`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 293 | 81.57 | 18.43 | 2.122 | 3,248 | +9.28 | −7.35 | 47 | −0.56 | 38,247 |
| 2022 | 406 | 82.27 | 17.00 | 2.200 | 6,619 | +17.31 | −12.46 | 64 | +0.63 | 44,866 |
| 2023 | 308 | 88.64 | 13.64 | 5.767 | 27,014 | +60.43 | −2.51 | 45 | +7.80 | 71,978 |
| 2024 | 668 | 86.23 | 14.52 | 3.902 | 32,687 | +45.36 | −11.36 | 121 | −4.64 | 104,567 |
| 2025 | 884 | 83.26 | 14.82 | 2.512 | 17,202 | +16.45 | −10.60 | **227** | −2.47 | **121,770** |

### GD92 base (`hn-g92`, md5 `cd913759`) — **tái lập đúng 2,632 / 133,944**

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 277 | 79.78 | 20.22 | 1.665 | 1,343 | +3.83 | −7.74 | 47 | −0.65 | 36,342 |
| 2022 | 416 | 79.57 | 19.71 | 1.276 | 2,637 | +7.26 | −13.21 | 69 | −3.81 | 38,980 |
| 2023 | 509 | 86.05 | 16.50 | 4.659 | 29,241 | +74.11 | −5.24 | 63 | +13.32 | 67,868 |
| 2024 | 792 | 84.47 | 16.29 | 3.572 | 29,714 | +43.91 | −11.36 | 114 | −4.59 | 97,935 |
| 2025 | 638 | 85.11 | 11.60 | 3.968 | 36,009 | +36.77 | −6.11 | 116 | +1.72 | **133,944** |

### GD92 + HINGE V3 (`hn-g-hi`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 276 | 79.71 | 20.29 | 1.652 | 1,206 | +3.44 | −8.08 | 47 | −1.18 | 36,205 |
| 2022 | 419 | 79.71 | 19.57 | 1.377 | 2,956 | +8.16 | −12.84 | 53 | −4.00 | 39,161 |
| 2023 | 508 | 86.02 | 16.54 | 4.678 | 29,369 | +73.97 | −5.05 | 63 | +13.55 | 68,129 |
| 2024 | 795 | 84.53 | 16.23 | 3.526 | 28,775 | +42.20 | −11.31 | 103 | −3.93 | 97,305 |
| 2025 | 642 | 85.20 | 11.53 | 4.021 | 37,235 | +38.27 | −6.29 | 142 | +2.25 | **134,540** |

### GD92 + LADDER L1 (`hn-g-la`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 276 | 80.07 | 19.93 | 1.894 | 1,556 | +4.44 | −7.83 | 46 | −0.20 | 36,555 |
| 2022 | 428 | 80.37 | 19.16 | 1.272 | 3,495 | +9.56 | −13.11 | 73 | −2.90 | 40,050 |
| 2023 | 504 | 86.31 | 16.47 | 4.711 | 31,676 | +78.26 | −5.48 | 63 | +13.48 | 71,392 |
| 2024 | 789 | 84.41 | 16.35 | 3.616 | 31,887 | +44.74 | −11.43 | 129 | −5.56 | 103,613 |
| 2025 | 631 | 84.94 | 11.73 | 3.659 | 32,431 | +31.30 | −6.81 | 164 | +1.06 | **136,044** |

### GD92 + CAP 10/30 (`hn-g-cp`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 275 | 79.64 | 20.36 | 1.923 | 1,961 | +5.60 | −7.89 | 47 | +0.47 | 36,961 |
| 2022 | 416 | 79.81 | 19.71 | 1.332 | 3,167 | +8.76 | −13.25 | 73 | −2.97 | 40,200 |
| 2023 | 499 | 86.37 | 16.43 | 4.813 | 31,750 | +78.06 | −5.48 | 63 | +13.43 | 71,580 |
| 2024 | 783 | 84.29 | 16.48 | 3.818 | 38,558 | +53.89 | −12.03 | 149 | −5.58 | 110,437 |
| 2025 | 635 | 85.04 | 11.65 | 3.950 | 38,963 | +35.28 | −7.00 | 112 | +0.74 | **149,400** |

### T100 + HINGE V3 (`hn-t-hi`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 294 | 81.63 | 18.37 | 2.150 | 3,367 | +9.62 | −7.50 | 47 | −0.59 | 38,366 |
| 2022 | 407 | 82.31 | 16.95 | 2.279 | 6,833 | +17.81 | −12.10 | 113 | +0.24 | 45,199 |
| 2023 | 307 | 88.60 | 13.68 | 5.988 | 28,834 | +64.02 | −2.51 | 45 | +8.37 | 74,134 |
| 2024 | 670 | 86.27 | 14.48 | 3.900 | 33,730 | +45.45 | −11.31 | 119 | −3.59 | 107,763 |
| 2025 | 893 | 83.43 | 14.67 | 2.566 | 20,701 | +19.21 | −12.00 | **223** | −1.63 | **128,464** |

### T100 + LADDER L1 (`hn-t-la`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 293 | 81.91 | 18.09 | 2.355 | 3,642 | +10.40 | −7.41 | 46 | +0.08 | 38,641 |
| 2022 | 413 | 82.81 | 16.71 | 2.198 | 7,688 | +19.90 | −12.48 | 158 | −0.06 | 46,330 |
| 2023 | 306 | 88.56 | 13.73 | 5.504 | 26,419 | +57.24 | −2.79 | 57 | +6.57 | 72,848 |
| 2024 | 665 | 86.17 | 14.59 | 3.828 | 31,916 | +43.76 | −11.43 | 129 | −5.00 | 104,665 |
| 2025 | 880 | 83.41 | 14.55 | 2.523 | 15,045 | +14.37 | −10.79 | **234** | −2.71 | **119,710** |

### T100 + CAP 10/30 (`hn-t-cp`)

| năm | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 291 | 81.44 | 18.56 | 2.318 | 3,654 | +10.44 | −7.44 | 47 | +0.03 | 38,654 |
| 2022 | 405 | 82.47 | 16.79 | 2.185 | 7,298 | +18.88 | −12.60 | 158 | +0.03 | 45,952 |
| 2023 | 306 | 88.56 | 13.73 | 5.656 | 27,501 | +60.06 | −2.83 | 61 | +7.22 | 73,552 |
| 2024 | 663 | 86.12 | 14.63 | 3.817 | 33,023 | +44.85 | −11.77 | 148 | −5.34 | 106,475 |
| 2025 | 882 | 83.56 | 14.40 | 2.717 | 19,991 | +18.78 | −9.33 | **223** | −3.27 | **126,466** |

**Đọc bảng:** ở nền **G**, ba exit gần như **không dịch** gì về chất lượng lệnh; chúng chỉ **dịch
PnL giữa các năm** (2024 +43.9% → +53.9% ở CAP; 2025 +36.8% → +31.3% ở LADDER). Ở nền **T**, exit
**không** sửa được **UW 2025 (227 → 223/234/223)** — bệnh đặc trưng của T100 vẫn còn nguyên.
**Tăng equity (149,400 ở `hn-g-cp`) KHÔNG phải bằng chứng** — luật đã khoá: tiêu chí là rate chất
lượng + rào cứng, và `hn-g-cp` trượt cả hai (UW 249 + conc 15.29% + 0 rate).

---

## 7. Bắt sóng lớn — `n` / `hold` / `turnover` / **capture ratio** (`trailTrace.csv`)

`SIM_TRAIL_TRACE=1` ở **cả 9** chân ⇒ **không** thiếu chân nào (khác vòng GD92×EXIT trước).
Nhóm = leg có **đỉnh đã xảy ra** ≥ 20% / 50% / 100%. **Nhóm hậu-chọn theo đỉnh ⇒ chỉ dùng chẩn đoán.**

### n / hold / turnover (toàn bộ leg)

| tag | n | hold med (h) | turnover (leg/ngày) |
|---|---|---|---|
| T170 | 1,089 | 4.8 | 0.662 |
| T100 base | 2,559 | 11.1 | 1.557 |
| GD92 base | 2,632 | 12.5 | 1.601 |
| GD92 + HINGE V3 | 2,640 | 11.5 | 1.606 |
| GD92 + LADDER L1 | 2,628 | 13.6 | 1.599 |
| GD92 + CAP 10/30 | 2,608 | 14.2 | 1.586 |
| T100 + HINGE V3 | 2,571 | 9.8 | 1.564 |
| T100 + LADDER L1 | 2,557 | 12.0 | 1.555 |
| T100 + CAP 10/30 | 2,547 | 12.6 | 1.549 |

### capture — peak ≥ +20%

| tag | n | %trailing | med_gap_pp | med_capture | mean_capture | SumPnL |
|---|---|---|---|---|---|---|
| T170 (`hn-par1`) | 123 | 98.4 | 8.14 | 0.662 | 0.596 | 51,997 |
| T100 base | 262 | 88.5 | 8.10 | 0.665 | 0.555 | 88,656 |
| GD92 base | 258 | 93.4 | 8.07 | **0.673** | **0.592** | 92,800 |
| GD92 + HINGE V3 | 152 | 88.8 | 8.07 | 0.668 | 0.535 | 48,908 |
| GD92 + LADDER L1 | 317 | 94.6 | 12.32 | 0.616 | 0.544 | 111,713 |
| GD92 + CAP 10/30 | 331 | 94.6 | 13.64 | **0.504** | 0.497 | 130,969 |
| T100 + HINGE V3 | 166 | 81.9 | 8.17 | 0.634 | 0.489 | 47,785 |
| T100 + LADDER L1 | 304 | 90.5 | 14.76 | 0.612 | 0.513 | 98,301 |
| T100 + CAP 10/30 | 330 | 91.2 | 14.77 | 0.503 | 0.468 | 113,483 |

### capture — peak ≥ +50%

| tag | n | %trailing | med_gap_pp | med_capture | mean_capture | SumPnL |
|---|---|---|---|---|---|---|
| T170 | 29 | 93.1 | 64.70 | 0.406 | 0.420 | 23,049 |
| T100 base | 66 | 54.5 | 120.63 | 0.125 | 0.212 | 19,232 |
| GD92 base | 51 | 66.7 | 114.80 | 0.171 | 0.240 | 20,885 |
| GD92 + HINGE V3 | 49 | 65.3 | 115.03 | 0.171 | 0.218 | 19,520 |
| GD92 + LADDER L1 | 63 | 73.0 | 79.31 | **0.326** | 0.302 | 33,939 |
| GD92 + CAP 10/30 | 83 | 78.3 | 37.98 | **0.502** | 0.375 | 59,767 |
| T100 + HINGE V3 | 63 | 52.4 | 124.04 | 0.112 | 0.185 | 16,524 |
| T100 + LADDER L1 | 77 | 62.3 | 111.51 | 0.172 | 0.263 | 29,981 |
| T100 + CAP 10/30 | 91 | 68.1 | 69.86 | 0.313 | 0.311 | 49,444 |

### capture — peak ≥ +100%

| tag | n | %trailing | med_gap_pp | med_capture | mean_capture | SumPnL |
|---|---|---|---|---|---|---|
| T170 | 21 | 90.5 | 112.34 | 0.262 | 0.308 | 15,906 |
| T100 base | 56 | 46.4 | 128.94 | 0.029 | 0.129 | 11,760 |
| GD92 base | 42 | 59.5 | 122.03 | 0.085 | 0.150 | 15,233 |
| GD92 + HINGE V3 | 42 | 59.5 | 122.03 | 0.086 | 0.151 | 15,542 |
| GD92 + LADDER L1 | 41 | 58.5 | 124.04 | 0.058 | 0.138 | 16,128 |
| GD92 + CAP 10/30 | 48 | 64.6 | 118.39 | 0.159 | 0.239 | 34,155 |
| T100 + HINGE V3 | 56 | 46.4 | 129.38 | 0.029 | 0.131 | 12,351 |
| T100 + LADDER L1 | 57 | 49.1 | 126.54 | 0.054 | 0.146 | 14,581 |
| T100 + CAP 10/30 | 62 | 53.2 | 123.40 | 0.125 | 0.197 | 26,199 |

**Đọc bảng (rất quan trọng):** Ở **nền G**, các exit **thật sự "chạm" được vào nhóm sóng lớn** —
`peak≥50%`: n 51 → **83** và SumPnL 20,885 → **59,767** (CAP); `peak≥100%`: 42 → **48**,
SumPnL 15,233 → **34,155**. **Nhưng đó KHÔNG phải capture tốt hơn** — `med_capture` ở nhóm `≥20%`
**GIẢM** (0.673 → 0.504), `med_gap_pp` **TĂNG** (8.07 → 13.64): leg được giữ lâu hơn nên **rơi vào
nhóm ≥X% nhiều hơn** (đổi thành phần nhóm) **và** thoát xa đỉnh hơn. Đúng hình mẫu đã thấy ở
`RESULT_TRAIL_LADDER` và `RESULT_TRAIL_CAP_1030`. **nội dung capture theo lệnh không cải thiện.**

---

## 8. VERDICT

| chân | rate vs baseline nền | rào cứng **năm** | rào cứng **toàn kỳ** | kết luận |
|---|---|---|---|---|
| **GD92 + HINGE V3** | 0 TỐT / 0 XẤU | PASS 5/5 | FAIL (UW 278) | **NULL** |
| **GD92 + LADDER L1** | 0 TỐT / 0 XẤU | PASS 5/5 | FAIL (UW 245) | **NULL** |
| **GD92 + CAP 10/30** | 0 TỐT / 0 XẤU | PASS 5/5 | FAIL (UW 249, conc 15.29%) | **NULL** |
| **T100 + HINGE V3** | 0 TỐT / 0 XẤU | FAIL 2025 (UW 223) | FAIL (UW 240, conc 27.08%) | **NULL** |
| **T100 + LADDER L1** | 0 TỐT / 0 XẤU | FAIL 2025 (UW 234) | FAIL (UW 240, conc 28.35%) | **NULL** |
| **T100 + CAP 10/30** | 0 TỐT / 0 XẤU | FAIL 2025 (UW 223) | FAIL (UW 241, conc 28.34%) | **NULL** |

### (a) **Trailing/exit có tác dụng ở n cao không? → KHÔNG.**

- **6/6 chân, 30/30 phép so: 0 TỐT / 0 XẤU ngoài CI (cả hai độ rộng)** — đúng bằng mốc **T170 = 0/5**.
- n tăng **2.42×** (1,089 → 2,632) **không** làm exit đo được hơn. ⇒ **giả thuyết "T170 ít lệnh" SAI.**
- Nguyên nhân đúng: **cơ chế exit không sinh rate mới** — nó chỉ dịch **đường ra** của leg đã vào.
  Bằng chứng cứng: exit **chạm thật** vào nhóm sóng lớn (n nhóm `≥50%` 51 → 83; SumPnL nhóm đó
  ×2.9) **nhưng** capture theo lệnh **giảm** ở nhóm `≥20%` (0.673 → 0.504). Đây là **đổi phân bố**,
  không phải **tăng chất lượng**.
- **2/30** phép dương yếu nhất (`hn-t-hi` win%/TSloss%) chỉ **ngoài ở ×1.21**, **trong** ở
  `inflate(k=3)` ⇒ theo luật đã khoá **không tính**.

### (b) **Có nên GO không? → KHÔNG.**

- **Không chân nào** đạt tiêu chí (≥2 rate TỐT ngoài CI + 0 XẤU ngoài CI + hết rào cứng toàn kỳ).
- Với **T100/GD92** thì GO **vốn đã bất khả** (base FAIL toàn kỳ: UW 248/278, conc 27.23%/14.38%).
- **Đề xuất bước tiếp? Không có bước tiếp nào từ vòng này** cho trục exit. Nếu muốn theo đuổi
  hướng *"exit hạ được UW toàn kỳ"*, tín hiệu **duy nhất** trong vòng là:
  **GD92 + LADDER L1** (UW 278 → **245**) và **GD92 + CAP 10/30** (UW 278 → **249**), **nhưng cả hai
  đều đẩy maxDD lên (−17.48% / −17.65%)** và **0 rate ngoài CI** ⇒ **không đủ cơ sở** để mở vòng mới;
  và **cái giá phải trả (maxDD + ~1pp) lớn hơn cái thu được (UW −30 ngày, vẫn > 200)**.

### **Có nên ĐÓNG HẲN trục exit không? → CÓ, ở mức bằng chứng.**

Lý do **đủ mạnh** để đóng: (1) **exit đã test 7 vòng** chống T170 (TRAIL-HINGE 3 · TRAIL-LADDER 3 ·
TRAIL-CAP-1030 2 · CLOSE-BIGGAP 18 · PEAK-CLOSE 1 · GD92×EXIT 3 · vòng này 6 = **36 biến thể**) —
**36/36 NULL**; (2) vòng này **bác bỏ cơ chế thoát duy nhất còn hợp lý** cho 36 lần NULL đó
("chưa đủ lệnh") — ở **2.4×** số lệnh, hiệu ứng vẫn **0**; (3) chính cơ chế exit (chỉ dịch đường ra)
**không thể** sinh rate chất lượng mới, và capture theo lệnh đi **ngược** chiều khi gap lớn hơn.
**Điều duy nhất còn để mở:** nếu owner muốn một **endpoint khác** (không phải 5 rate chất lượng:
vd tối ưu **Calmar/UW** trên nền **đã PASS** T170) thì phải **pre-reg endpoint đó riêng** —
**không** dùng kết quả vòng này để GO.

---

## 9. Đối chiếu với dự đoán ghi trước (pre-reg §8)

| dự đoán | thực tế | đúng/sai |
|---|---|---|
| ≥1 chân exit ở nền nhiều lệnh có ≥1 rate ngoài CI (khả năng cao: TSloss%/meanP) | **0/30** — không chân nào | **SAI** |
| Không chân nào đạt GO | đúng, 0/6 | **ĐÚNG** |
| LADDER L1 tăng n nhóm ≥50% và SumPnL nhóm đó nhưng KHÔNG tăng capture | đúng: G 51→63 (SumPnL ×1.63), T 66→77 (×1.56); capture `≥20%` giảm | **ĐÚNG** |
| GD92 base xấu hơn T100 base về rate chất lượng | điểm-ước-lượng: win% −0.667, TSloss% +0.790, meanP +0.142 ⇒ **cùng chiều "xấu" ở 2/3 rate** nhưng **0 rate ngoài CI** | **ĐÚNG (yếu)** |
| CAP 10/30 hạ UW | trên nền G: UW 278 → 249 ✅; trên nền T: 248 → 241 ✅ | **ĐÚNG** (nhưng kèm maxDD tăng & chất lượng 0) |

Một quan sát ngoài dự đoán, ghi lại **không tô hồng**: **`hn-g-cp` có equity cao nhất vòng
(149,400; CAGR 38.08%)** — nhưng đó là **hệ quả của việc giữ lệnh lâu hơn** (hold med 14.2h vs 12.5h),
đi kèm **maxDD xấu nhất (−17.65%)**, **vượt trần tập trung (15.29% > 15%)** và **0 rate ngoài CI**.
Equity **không phải tiêu chí**. Ngoài ra **GD92 sửa được tập trung của T100** (conc 27.23% → 14.38%)
— nhất quán `RESULT_GD92_RECHECK`, và **không** cứu được verdict.

---

## 10. Multiplicity + kỷ luật

- `k = 3` cho **mỗi nền** (3 exit × 2 nền), `inflate(3) = sqrt(2 ln 3) = 1.482304`; báo **cả**
  legacy ×1.21. Tính cả chương trình, đây là **vòng exit thứ 7** chống T170 / đo cơ chế exit
  (≈ **36 biến thể**). Kết quả NULL ⇒ **không cần** viện đến multiplicity.
- **Không push.** Branch `gd92-recheck` **KHÔNG merge** vào `module`; code rolling **KHÔNG commit**
  (đã `git reset` + `git checkout -- src/`; `git diff HEAD -- src/` = rỗng). Chỉ commit **docs + script**.
- **KHÔNG** chạm 242. **KHÔNG** đóng holdout 2026 (dữ liệu ≤ 2025-12-31). **KHÔNG** quét biến thể
  GD92 (0.88/0.90/0.94/0.96, W=60/120/180) hay biến thể exit mới. **KHÔNG** đổi incumbent
  (**T170 giữ nguyên**).

## 11. Thời gian / chi phí

| hạng mục | giá trị |
|---|---|
| số kernel | **9** (`hn-par1`, `hn-t100`, `hn-g92`, `hn-g-hi`, `hn-g-la`, `hn-g-cp`, `hn-t-hi`, `hn-t-la`, `hn-t-cp`) |
| JVM mỗi chân | **1,198 – 1,369 s** (≈ 20–23 phút) |
| push → COMPLETE | ≈ 25–30 phút/kernel; **2 lượt** (5 slot + 4 slot) ⇒ **~65 phút wall-clock** |
| **chi phí Kaggle** | **0** (CPU kernel không tính quota) |
| build jar (Oracle) | `mvn -o package` **24.1 s**, 154 test PASS |
