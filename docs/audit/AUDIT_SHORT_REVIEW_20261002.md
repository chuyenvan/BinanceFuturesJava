# AUDIT_SHORT_REVIEW_20261002 — rà độc lập chuỗi 12 vòng SHORT (NULL/NO-GO)

Ngày **2026-10-02**, branch `module` (HEAD lúc rà `4a47d9dc`). Auditor độc lập: **chỉ đọc + tính lại nhỏ 0-sim**
(1 script ~20 s CPU), **không** chạy thí nghiệm mới, **không** sửa `.java`, **không** chạm 242/LIVE/2026.
Script tính lại: `research/analysis/audit_short_state_beta.py` (output `~/claude_master/1002/audit_short_state_beta.json`).

## 0. KẾT LUẬN (1 dòng)

> **CÓ CỬA (HẸP).** **Không** lỗi nào tìm được lật được một NO-GO nào (kể cả đảo dấu funding); nhưng **cả 12 vòng
> chấm short theo khung DIRECTIONAL per-trade**, nên alpha xếp hạng thật (rank-IC +0,052, 3/3 seed; IC S1 âm
> **mọi năm**) bị chìm trong **beta alt** (CI ±0,6 %/72h, MDE80 ≈ 0,85 %/lệnh) — **chưa vòng nào đo alpha tách beta**.
> Đúng **1 vòng** 0-sim trên bins sẵn có (§10); FAIL ⇒ **đóng hẳn** short trên dữ liệu hiện có.

Xác suất chủ quan vòng §10 GO: **~20–30 %** (biên ước tính chỉ ~+0,1 %/72h sau phí 2 chân). Không phải "đã có edge".

## 1. Bảng phát hiện (mức: LỖI-ĐỔI-KẾT-LUẬN / LỖI-NHỎ / ĐÚNG / THIẾU-SÓT)

| # | Phát hiện | Mức | Đổi verdict? |
|---|---|---|---|
| F1 | **Dấu funding** trong mọi script Python: `rate>0 ⇒ short NHẬN` (`pnl + Σrate`) — đúng Binance | **ĐÚNG** | — |
| F2 | `−0,585 %/72h` là funding **thật** của top-K8 model SHORT13 (DEEP §4), nhưng bị **ghép như HẰNG SỐ** sang tập ứng viên khác (LABEL2 flat; PATHEXIT/PSOFT/REGIME/FULLCHAIN pro-rata) | LỖI-NHỎ | Không (đảo dấu vẫn NO-GO, §2.3) |
| F3 | DEEP/V3/V3B/V4 tính funding **cả cửa sổ T** kể cả lệnh đã bị cắt +30 % ⇒ **thu oan** funding sau exit (nhóm squeeze, funding âm nặng) | LỖI-NHỎ | Không (độ lớn chưa đo; CI ±0,6 % nuốt) |
| F4 | V3/V3C "+0,547 %" **không phải sửa dấu**: là **LỌC** N1b (giữ coin có rate kỳ kế ≥0) ⇒ fund_mean −0,58 → +0,0004 % | ĐÚNG (tiền đề owner đọc nhầm) | — |
| F5 | FEASIBILITY **đếm phí 2 lần**: `fee_rt = 2×0,000982` trong khi Java trừ `notional×RATE_FEE` **1 lần/vòng** ⇒ cost đúng 0,112 %, không 0,2098 % | LỖI-NHỎ | Không (d8 −0,0898 vẫn < 0,112; lật năm 2/4) |
| F6 | STATE chép `COST24=0,21 %` từ F5 ⇒ net bị trừ thừa 0,098 pp | LỖI-NHỎ | Không |
| F7 | STATE báo **CI của GROSS** dưới nhãn net; `by_year`/`years_pos` cũng là **GROSS** | LỖI-NHỎ (báo cáo sai) | Không |
| F8 | STATE A2 là **post-hoc** (commit 3 phút sau kết quả A1); "4 biến thể >0 ⇒ nghi overfit" **áp sai luật** (luật nói >1 biến thể GO) và 4 biến thể **lồng nhau** | LỖI-NHỎ | Không (NULL đúng, lý do sai) |
| F9 | **Tính lại**: drift của STATE B_ev **~90 % là beta** (β=0,95; excess vs EW cùng giờ **+0,026 %/24h**, CI [−0,018; +0,070]) | ĐÚNG-NULL (củng cố) | Đóng hẳn cửa STATE |
| F10 | Luật C (winrate ≥ base+5 pp) ở V3/V3B/V4 **không có cơ sở kinh tế** | LỖI-NHỎ (thiết kế luật) | Không (A đã FAIL độc lập) |
| F11 | `predRisk4H` in-sample ⇒ nhánh D **lạc quan**; sửa sẽ làm D **xấu hơn**; không có nguồn predRisk4H leak-free | ĐÚNG (caveat đã ghi) | Không |
| F12 | FULLCHAIN: picks bước 3 **83 % là 2025** (541 693/654 326); D chiếm 28,8 % picks bước 3 vs 9,2 % bước 2 (lệch phân phối gate) | LỖI-NHỎ | Không |
| F13 | Bootstrap block-72h = **cluster theo thời gian** ⇒ tương quan chéo cùng giờ **đã được xử lý**; n hiệu dụng ≈ **số block ≈ 464–487**, không phải 10⁶ lệnh | ĐÚNG (hơi hẹp do lệnh 72h vắt block) | — |
| F14 | **Chưa vòng nào đo alpha beta-neutral** (short top-K vs long EW cùng tick) ⇒ thiết kế directional **thiếu lực** (MDE80 ≈ 0,85 %/lệnh ≫ biên kỳ vọng 0,3 %) | **THIẾU-SÓT LỚN** | **Có thể** — là cửa duy nhất còn lại |
| F15 | "Chỉ đảo công cụ long" **không đúng**: 9/12 vòng dùng tín hiệu short độc lập (model nhãn ngược, carry, state) — nhưng **mọi model đều cùng 45 feature long** | ĐÚNG một phần | — |
| F16 | Java SELL funding còn **DRAFT dấu đảo** (commit `5a7aa348`, `OrderTargetInfoTest.computeFundingOnClose`) | LỖI tiềm ẩn (chỉ khi build) | Không ảnh hưởng số Python |

## 2. Câu 1 — DẤU FUNDING cho SHORT (nghi vấn số 1) ⇒ **dấu ĐÚNG; hằng số bị ghép sai tập; đảo dấu vẫn NO-GO**

### 2.1 Quy ước gốc
`RESULT_FUNDING_SIGN.md` §0(1): Aerospike lưu nguyên `fundingRate` Binance (`HistoricalFundingCrawlerLocal.java:75`),
`rate>0 ⇒ LONG trả / SHORT nhận`; BTC dương 85,6 % kỳ. Sổ long G2 **thu ròng** funding (mean f_pp −0,2518 %/lệnh
theo dấu chi phí) vì G2 mua-đáy đúng coin **short đông** (rate<0). Tập short-alpha là **cùng nhóm coin đó** ⇒ short
**TRẢ** là hợp logic, không mâu thuẫn với "80 % kỳ dương" (đó là thống kê toàn universe/mode).

### 2.2 Từng script

| Script | Funding dùng | Dấu | Ghi chú |
|---|---|---|---|
| `short_model_deep.py:17-18,163,195-201` | **exact** Σrate (t, t+T] mỗi lệnh | `pnl + f` ⇒ rate>0 short nhận ✅ | cả cửa sổ T kể cả lệnh bị cắt (F3) |
| `short_v3_score.py:9,56-98,165-201` (dùng lại ở `short_v3b_score.py:251-257`, `short_v4_score.py`) | **exact** `Fund.compute` | `ptf = pnl + f` ✅ | `f = S["f_%d"%T]` cả cửa sổ (F3) |
| `short_model_label2_analyze.py:15,68-69` | **hằng** `DF_RAW = −0,00585` trừ phẳng | chi phí ✅ | ghép từ DEEP cho tập PA/PW khác (F2) |
| `short_pathexit_sim.py:30,283-284,613` | **hằng** `FUND72·held/4320` | chi phí ✅ | F2 |
| `short_fullchain_sim.py:22-23,202` | **hằng** pro-rata | chi phí ✅ | áp cho **S1 decile-0** — tập hoàn toàn khác (F2) |
| `short_regime_0sim.py:20-21,191` | **hằng** pro-rata | chi phí ✅ | F2 |
| `short_state_0sim.py:30,228` | **không có funding** | — | chỉ trừ 0,21 % (F6) |

**−0,585 % là gì:** mean Σrate 72h của **top-K8/tick model SHORT13 (nhãn ndown)**, raw; median **+0,055 %**, p01
**−13,1 %**, 62,6 % lệnh nhận (`RESULT_SHORT_DEEP.md:106-112`); V3 đo exact lại **−0,580 %** (khớp). Là số **thật của
tập đó**, **không** phải giả định — nhưng **không** phải funding của S1-d0 / PA / regime-subset.

### 2.3 Tính lại nếu funding SAI (dùng `RESULT_SHORT_FULLCHAIN.json`, `mean_held_h` từng ô)

| Nhánh / ô tốt nhất | held | funding đã trừ | net báo cáo | net nếu funding=0 | **net nếu ĐẢO dấu** | CI95 đảo dấu | năm dương (đảo) |
|---|---|---|---|---|---|---|---|
| D NGHỊCH `T3_SL30..100_TS24h` | 6,81 h | 0,0553 % | −0,0402 % | +0,0151 % | **+0,0705 %** | [−0,113; +0,244] | 2/4 (22 +0,26 · 23 −0,19 · 24 +0,10 · 25 −0,08) |
| A không gate `T3_SL50..100_TS72h` | 14,69 h | 0,1194 % | −0,2343 % | −0,1149 % | **+0,0044 %** | [−0,164; +0,190] | 2/4 (22 +0,05 · 23 −0,57 · 24 −0,05 · 25 +0,02) |

⇒ **Cả kịch bản cực đoan (đảo dấu, tức short NHẬN 0,585 %/72h)** vẫn **CI chứa 0 và 2/4 năm** ⇒ NO-GO giữ nguyên.
Nhánh A "−0,23 %" nói trong đề là ô tốt nhất A; D "−0,040 %" như trên.

**F3 (thu oan sau exit):** lệnh cắt +30 % (10 % số lệnh) là coin squeeze — funding âm nặng nhất — nhưng vẫn bị trừ
funding tới hết 72h. Chưa đo được (.pb chỉ có thời điểm cực trị). Dấu hiệu độ lớn có giới hạn: cường độ funding/giờ
**giảm** theo T (4h −0,0148 %/h · 24h −0,0115 · 72h −0,0081, suy từ `RESULT_SHORT_V4.md` §2) ⇒ funding dồn **đầu**
cửa sổ, phần thu oan sau exit ước **≤ ~0,1–0,2 pp/lệnh** ⇒ baseline −0,171 % có thể về ≈ 0, **không** ra ngoài CI ±0,6 %.

## 3. Câu 2 — COST MODEL ⇒ **FEASIBILITY + STATE trừ thừa 0,098 pp; các vòng khác = long**

| Nguồn | Phí vòng | Bằng chứng |
|---|---|---|
| **Java (long G2/R4)** | `notional×RATE_FEE` **1 lần** + `notional×SLIPPAGE_RATE×2` = 0,0982 + 0,0134 = **0,1116 %** | `OrderTargetInfoTest.java:~280-288`; `Configs.java:103` ("đã sửa thành 2 chân"); `profiles/r4_kg0_k16_f015_g155.properties:63-64`; `RESULT_COST_TRUTH.md:60` |
| FEASIBILITY P1/P2 | `2×0,000982 + 2×0,000067` = **0,2098 %** | `short_feas_reverse.py:10,30` — coi 0,000982 là **phí/chân** ⇒ **đếm phí 2 lần** |
| STATE | **0,21 %/24h** (chép từ FEASIBILITY) | `short_state_0sim.py:30` |
| MODEL/DEEP/V3/V3B/V4/LABEL2/PATHEXIT/PSOFT/FULLCHAIN/REGIME | **0,112 %** | `COST_BASE=0.00112` các script |
| CARRY | taker 0,05 %/chân + slip proxy 0,5·(h−l)/c (khác, gắt hơn) | `RESULT_SHORT_CARRY.md` §3–4; slip 1 bp vẫn −0,02 % CI chứa 0 ⇒ bền |

Thiên lệch: short bị trừ **thêm 0,098 pp/vòng** ở FEASIBILITY và STATE. Hệ quả: P2 ngưỡng đúng **−0,112 %**, d8
−0,0898 % vẫn FAIL (thiếu 0,022 pp) + lật năm 2/4; P1 −102 173 → ≈ **−99 709 USDT** (vô nghĩa). STATE B_ev net24
**+0,055 → +0,153 %**, B gốc −0,058 → +0,040 % — nhưng xem §6/F9: phần lớn là beta. Các vòng còn lại **cùng 0,112 %
với long** ⇒ không thiên lệch. (Lưu ý: long hưởng look-ahead "vào ở close" khi sập +1,675 %/chân, `COST_TRUTH` §0;
short ở nhãn .pb cũng vào ở close 15m ⇒ xấp xỉ đối xứng.)

## 4. Câu 3 — V3C net +0,547 % bị NO-GO theo luật nào ⇒ **luật C thừa, nhưng A FAIL độc lập ⇒ NULL đúng**

Luật V3 §6 (giữ cho V3B/V3C/V4): **A** net sau funding > 0 ngoài CI raw **và** ×1,21 · **B** ≥3/4 năm dương ·
**C** winrate ≥55 % **và** ≥ baseline + 5 pp. **Không** đòi 4/4 năm. Số (`RESULT_SHORT_V3B.json`, mean 3 seed):

| Cấu hình | n | net_post | CI raw | CI ×1,21 | 2022 | 2023 | 2024 | 2025 | yrs+ | winrate | A/B/C |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline K8 C30 | 1 114 016 | −0,171 % | [−0,763; +0,397] | [−0,887; +0,516] | +0,98 | −0,92 | −0,24 | −0,48 | 1/4 | 0,558 | ✗✗✗ |
| **L1b′+N1b K8** | 251 713 | **+0,547 %** | [−0,054; +1,152] | [−0,180; +1,279] | +1,70 | −0,23 | +0,07 | +0,77 | 2,67 | 0,570 | ✗✗✗ |
| **L1b′+N1b K3** | 87 951 | **+0,754 %** | **[+0,050; +1,451]** | [−0,097; +1,598] | +1,96 | +0,03 | +0,26 | +0,95 | 3,67 | 0,578 | ✗✓✗ |

Đánh giá: (i) **C không có cơ sở kinh tế** (net/lệnh mới là thứ cần; một short 57 % winrate kỳ vọng dương là hợp lệ)
⇒ **LỖI-NHỎ thiết kế luật**, nhưng **không binding**. (ii) **A FAIL độc lập**: K8 chứa 0 cả raw; K3 chỉ ra khỏi raw
(cận dưới +0,05 %) — và K3 là **cực đại của ~56 cấu hình** (V3 18 + V3B 21 + V4 17), dựng bằng cách **chồng** filter
tốt nhất của V3 (N1b) lên filter mới ⇒ một CI raw vừa chạm 0 là **đúng mức kỳ vọng do multiplicity**. (iii) 2022 (năm
bear) đóng góp ~½ tổng; 2023 ≈ 0 ⇒ chữ ký beta. ⇒ **NULL đúng; không phải áp luật quá chặt.**

## 5. Câu 4 — Candidate definition: vòng nào dùng tín hiệu short ĐỘC LẬP?

| Vòng | Ứng viên | Độc lập với long? |
|---|---|---|
| CARRY | top-decile funding | **CÓ** (funding) |
| FEASIBILITY P1 / P2 | mirror lệnh G2 / decile S1 đảo | KHÔNG (đảo long) |
| MODEL · DEEP · V3 · V3B/V3C · V4 | XGB **train lại nhãn ngược** `retEnd_72h ≤ −1,5 %` | **CÓ** (model riêng) — nhưng **cùng 45 feature selector long**; V4 thêm OI-LIQ |
| LABEL2 · PATHEXIT · PSOFT | model nhãn path-aware (pa/pw) | **CÓ** (cùng 45 feature) |
| FULLCHAIN | S1 decile-0 + gate long `predRisk4H` | KHÔNG (đảo long) |
| REGIME | pick PA + regime giá tự dựng | CÓ (pick model short) |
| STATE | state giá theo coin (pump_age/vol_decay/dd30/ret30) | **CÓ** (luật giá thuần) |

⇒ Nghi vấn "chỉ thử đảo công cụ long" **không đúng** (9/12 vòng độc lập). Lỗ hổng thật hẹp hơn: (a) **mọi model đều
cùng không gian 45 feature long** (không feature crowding/LS-ratio/basis/liquidation); (b) **mọi vòng cùng một khung
chấm DIRECTIONAL** (F14) — đây mới là lỗ hổng che edge.

## 6. Câu 5 — `predRisk4H` không leak-free

`RESULT_PREDBIN_REPRO.md:31,171`: cột 2 `pred.bin` lấy từ set CŨ `ai_pred_market_full_basket_v2`, train tới ~19/12/2025
⇒ DEV **in-sample**. Ảnh hưởng: nhánh D (vào khi risk CAO) dùng đúng vùng model "biết trước" ⇒ ret24 −0,616 % (4/4
năm âm) ở bước 2 là **lạc quan cho short**; sửa leak gần như chắc chắn làm D **xấu hơn** ⇒ verdict NO-GO **được củng cố**,
không lật. Nguồn thay: **không có `predRisk4H` leak-free** trong repo; cái leak-free duy nhất là **cột 1 `p15`
(predReturn15M)** do `WfoDataset.export` `leakFreeFrom=2021-07-01` (`RESULT_PREDBIN_REPRO.md:45`) — target khác (15m return),
không thay thế 1-1. Thêm F12: bước 3 D chiếm 28,8 % picks (bước 2: 9,2 %) vì picks 83 % rơi vào 2025 ⇒ ngưỡng q10 tính
trên cả DEV không còn nghĩa "10 % rủi ro nhất" trên tập picks.

## 7. Câu 6 — STATE tập B (A2): CI, biến thể, NULL

1. **CI là của GROSS, không phải net** (`short_state_0sim.py:221-229`: `ci = ci_mean(short24, ts)` còn `short_net24 =
   mean − COST24`). Bằng chứng nội tại: ALL net −0,222 % nằm **ngoài** "CI" [−0,216; +0,202] của chính nó. CI net đúng
   của B_ev = gross CI − cost = **[−0,285; +0,426]** (cost 0,21) hoặc [−0,187; +0,524] (cost 0,112) ⇒ vẫn chứa 0.
2. **`by_year`/`years_pos` cũng GROSS** (`:232-233`). Net theo năm @0,21 %: B gốc **−0,07/−0,43/+0,09/−0,01 ⇒ 1/4**
   (báo 3/4); B_ev +0,18/−0,51/+0,35/+0,07 ⇒ 3/4.
3. CI là của **1 nhánh**, raw, **không** inflate theo k (×1,21 chỉ trong `out_both`). 
4. **A2 là post-hoc**: `596c5890` (kết quả A1, B −0,058 %) 09:06:09 → `93a6d280` (A2) 09:09:33. Ngưỡng 18 d/50 %/−20 %
   suy từ phân bố leg ZigZag (không từ forward return) — rò rỉ nhẹ, nhưng việc **chọn đổi định nghĩa sau khi thấy A1** là post-hoc.
5. "4 biến thể >0 ⇒ nghi overfit" **áp sai luật** (pre-reg §4: ">1 biến thể đều **GO**"; không biến thể nào GO) và 4 biến
   thể **lồng nhau** (big-alt, rac ⊂ B_ev; dd10 ⊃ B_ev) nên không phải 4 bằng chứng độc lập.
6. **Tính lại (F9)** — `audit_short_state_beta.py`, dùng nguyên `build_states()`, forward 24h từ CLOSES_1H, DEV 2022–2025:

| Tập | n | short gross | CI gross | **excess vs EW cùng giờ** | CI excess | β | excess theo năm (22/23/24/25) |
|---|---|---|---|---|---|---|---|
| B_ev | 1 536 617 | **+0,282 %** (pb: +0,265) | [−0,075; +0,651] | **+0,026 %** | [−0,018; +0,070] | 0,95 | +0,042/−0,025/+0,064/+0,019 |
| B gốc | 2 806 171 | +0,169 % | [−0,137; +0,468] | **−0,000 %** | [−0,030; +0,029] | 0,95 | +0,008/−0,014/+0,007/−0,003 |
| A_ev | 3 887 002 | +0,002 % | [−0,265; +0,263] | −0,011 % | [−0,040; +0,019] | 1,06 | — |

   ⇒ Gross tái lập khớp .pb; **~90 % drift của B_ev là beta alt** (DEV alt giảm), alpha thuần **+0,026 %/24h ≪ cost 0,112 %**.
   **Kết luận NULL đúng — và đúng vì lý do mạnh hơn lý do đã ghi.** Cửa STATE **đóng hẳn**.

## 8. Câu 7 — Thống kê: block-72h có đúng khi short cùng giờ tương quan chéo mạnh?

- `ci_mean` (`short_model_score.py:96-122`, bản sao ở các script): chia trục thời gian thành **block lịch 72h**, mỗi block
  mang **tổng của MỌI lệnh** trong nó, resample block ⇒ thực chất là **cluster bootstrap theo thời gian** ⇒ tương quan
  chéo cùng giờ (pump/dump chung) **đã được tính đúng**. Đây **không** phải lỗi.
- Điểm yếu: lệnh giữ 72h **vắt sang block kế** ⇒ block liền nhau phụ thuộc ⇒ CI **hơi hẹp**; ×1,21 là bù thô (chưa
  kiểm bằng block 144h). Ảnh hưởng chiều "lạc quan", không che edge.
- **n hiệu dụng của mean directional ≈ số block ≈ 464–487** (DEV 2022–2025), **không** phải 10⁶ lệnh. Đo được: với B_ev,
  half-width CI gross 24h = 0,36 % vs excess = 0,044 % ⇒ **phương sai giảm ~67× khi bỏ beta**; n_eff(excess) ≈ 2,1·10⁴.
- **Hệ quả quyết định (F14):** CI directional của top-K8 72h ≈ ±0,6 %/lệnh ⇒ **MDE80 ≈ 0,85 %/lệnh**. Biên alpha kỳ vọng từ
  rank-IC (~0,3 %/72h) **không thể** vượt CI trong khung này dù có thật. 12 vòng NULL phần lớn là **thiếu lực**, không phải
  "đã chứng minh không có alpha". (Ngược lại, chúng **đã** chứng minh: short directional không có net>0 đủ bền để build.)
- FULLCHAIN: 83 % picks là 2025 ⇒ mean per-trade ≈ 2025; năm 2023 chỉ 9 236 picks.

## 9. Câu 8 — Hướng short chưa thử (liệt kê, KHÔNG chạy)

| # | Hướng | Vì sao có thể có edge | Rủi ro/đánh giá trước |
|---|---|---|---|
| 1 | **Beta-neutral: short top-K model vs long EW universe cùng tick** | IC +0,052 bền 3 seed; IC S1 âm **mọi năm**; directional bị beta che (F14) | biên mỏng sau phí 2 chân; funding pick âm (cần N1b) — **chọn làm vòng §10** |
| 2 | Short sau khi lệnh LONG G2 bị SL/trailing-out (dip-buy thất bại ⇒ momentum tiếp diễn) | điều kiện hoá bằng thất bại của chính edge long; tần suất thấp, sự kiện rõ | n nhỏ (~vài trăm/năm); dùng `printDone` + 1m |
| 3 | Short sleeve đánh giá ở **mức SỔ** (long R4 + short) theo §9 MTM | short thắng năm bear (2022) bù long; §9 T1 "0 năm âm" là luật **sổ**, không phải sleeve | cần sim MTM phút — chưa có đường SELL |
| 4 | Feature crowding ngoài 45 feature long (LS top-trader, basis, OI-crowding — kernel 07/2026 `4d5cbf8a`) | short-alpha nằm đúng nhóm short đông ⇒ cần feature đo đông | kết quả 07/2026 chưa được tổng hợp vào chuỗi này |
| 5 | Breadth-crash trigger (short rổ alt khi breadth sụp) | time-series momentum alt index | thuần beta/timing; REGIME đã cho thấy lọc regime không cắt đuôi |
| 6 | Top-K rvol15m sau pump ≥X % + time-stop | exhaustion | **bằng chứng ngược**: MAX-effect dương (P7/P8), A_ev ret7≥50 % drift lên, SL-rate 55 % ⇒ ưu tiên thấp |
| 7 | Funding cực đoan dương (top 1 %, long đông) | short nhận funding + long đông dễ xả | CARRY decile: chân giá ≈0, cost ăn hết; chỉ đáng nếu kèm #4 |

Liquidation feed (`liq_ws.py`) chỉ có từ 09/2026 ⇒ **không dùng được cho DEV**; chỉ forward.

## 10. ĐÚNG 1 vòng kế tiếp — PRE-REG NHÁP `PREREG_SHORT_BETANEUTRAL` (chưa commit thành prereg; owner duyệt trước)

**Giả thuyết H1.** Kỹ năng xếp hạng của model short nhãn ngược (`ndown` 1,5 %/72h; rank-IC +0,052) là **alpha
cross-section thật** bị beta alt che; đo **beta-neutral** thì spread `short top-K8 − long EW` **> 0 sau phí CẢ 2 chân +
funding CẢ 2 chân**, ngoài CI, bền theo năm. H0: spread ≤ 0.

**Dữ liệu (đã có, 0 kernel, 0 Java):** bins `~/sm_pathexit/sm/OLD_ndown_S42/predict_wf_*.bin` (16 fold OOS, recipe = SHORT42)
· nhãn `.pb` 72h (`retEnd_72h`, `maxFav_72h`, `nBars_72h≥288`) · funding `fund_cache.npz` (tái tạo bằng
`funding_sign_reconcile.py` nếu đã dọn) · DEV **2022-01-01..2025-12-31**, 2026 **không chạm**.
Sanity bắt buộc trước khi đọc số chính: tái lập baseline V3 `net_pre` K8 C30 trong ±0,03 pp (+0,409 %) và
`fund_mean` ±0,03 pp (−0,580 %); lệch ⇒ **VOID**, không báo kết quả.

**Cấu hình DUY NHẤT (khoá, không quét):** mỗi tick: short **top-K=8** theo score **sau** lọc N1b (rate kỳ settle kế tiếp ≥0,
đúng định nghĩa V3 — filter duy nhất, **không** chồng L1b′/K3); long **EW toàn universe nhãn** cùng tick, cùng notional;
giữ T=72h; cắt cứng short **+30 %** (`maxFav_72h`, như V3). Lệnh i:
`spread_i = (−ret_short_i | cut) − mean_EW(ret_72h) − 2×0,112 % + f_short_i − f̄_EW` (funding exact, cả cửa sổ 72h — bảo thủ, như V3).

**Metric:** mean spread/lệnh (trung bình theo tick) · CI block-72h NREP 2000 seed 20260905, raw và ×1,21 · theo năm 2022–2025 ·
β chân short vs EW (kỳ vọng ≈1, spread β ≈0) · IC theo năm · bản stress phí 0,150 %/chân · báo kèm directional (không hedge)
cùng tập để đối chiếu · báo F3-bound: funding cắt tại `tHitFav` (chỉ báo phụ, **không** dùng cho verdict).

**Luật GO/NO-GO (cố định, cơ học):** **GO-nghiên-cứu** ⇔ (1) sanity PASS **và** (2) mean spread > 0 với CI **raw và ×1,21**
ngoài 0 **và** (3) ≥ 3/4 năm spread > 0 **và** (4) IC > 0 cả 4 năm **và** (5) stress 0,150 % vẫn > 0 ở điểm ước lượng.
Thiếu bất kỳ ⇒ **NO-GO và ĐÓNG HƯỚNG SHORT trên dữ liệu hiện có** (chỉ mở lại khi có data mới: liquidation/L2 từ 09/2026
tích luỹ đủ forward). **Không** có luật winrate. **Không** có vòng "thử thêm biến thể" sau khi thấy số.
GO ở vòng này **chỉ** mở bước kế: đánh giá ở mức SỔ (long R4 + short sleeve) theo §9 MTM — **không** build đường SELL.

**Cấm:** tune K/C/T/filter; thêm feature; dùng seed khác để "chọn"; chạm 2026; sửa `.java`; Java sim trên Oracle.
**Ước tính trước (để chống tự lừa):** excess gross ~+0,34 %/72h − phí 2 chân 0,224 % ⇒ **~+0,1 %/72h**; nếu CI excess
co ~5–8× như STATE thì half-width ~±0,08–0,12 % ⇒ **ngưỡng sát**; khả năng GO ~20–30 %.

## 11. Sản phẩm + tuân thủ

- `docs/audit/AUDIT_SHORT_REVIEW_20261002.md` (file này) · `research/analysis/audit_short_state_beta.py` (tính lại F9, ~20 s CPU).
- Chỉ đọc docs/script/JSON; tính lại trên `CLOSES_1H.bin` + JSON kết quả có sẵn. Không Java, không `.java`, không 242/LIVE,
  không 2026, không xoá dữ liệu, không đọc secret. Không có job nặng khác chạy lúc tính (chỉ collector cron).
