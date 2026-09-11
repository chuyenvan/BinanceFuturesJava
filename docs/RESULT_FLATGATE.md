# RESULT_FLATGATE — gate PHANG (chien luoc 242 dang chay) tren 48 thang: **TE HON RO**

Pre-reg `docs/PREREG_FLATGATE.md` (commit `ee00475`, TRUOC khi chay). Nen
`X1_C3_FULL_PARITY_R`. Audit nguon: `docs/AUDIT_GATE_DYN_PARITY.md` (`3a36f02`) muc 5.2 huong C.
**Day la phep do MO TA chien luoc dang chay tren 242, KHONG phai ung vien adopt.**

## 0. PHAN QUYET (theo quy tac chot truoc, PREREG muc 6)

**Ket luan A — gate phang TE HON RO.** Ca hai dieu kien cua A deu dat, doc lap nhau:
- `d CAGR = -61.08 pp`, **CI95 `[-85.76, -32.82]`, tran < 0**, ben o ca block 10/21/42
  (`[-85.40,-32.65]` / `[-85.76,-32.82]` / `[-85.04,-35.24]`), `P(d>0) = 0.000`.
- **Vo rang buoc cung o ca 4/4 nam**, ke ca 2022 va 2023 la hai nam nen `PARITY_R` **PASS**.

Ket luan nay **khong** cho phep sua sim theo huong B cua audit. No **ung ho** huong A
(sua live cho khop sim) — patch da soan o `docs/L6_GATE_DYN_FIX.md`, **chua deploy**.

## 1. CONG NGHIEM THU — PASS

| buoc | ket qua |
|---|---|
| `mvn -DskipTests -o package` | `BUILD_RC=0`, jar 99,654,791 B |
| `tools/check_cfg_gateway.sh` | `OK — khong co tham so giao dich nao lach cong Cfg` |
| jar MOI + `x1_c3_full.properties` -> `devrun/X1_C3_FULL_FLATOFF` | `b:111428`, `done:339/2266/2266`, 2,267 dong |
| `md5sum printDone.csv` FLATOFF | **`2478e90d4e6147bf4cc64f75967ef47d`** = **KHOP** `PARITY_R` |
| `cmp` phan bo header FLATOFF vs PARITY_R | **rc = 0** (IDENTICAL) |
| md5 FLATGATE vs PARITY_R | `ed04e59edc60f76953756e16647a3736` **KHAC** => key da an that |

=> Key `SIM_GATE_DYN_BYPASS` khong khai / `0` la **byte-identical HEAD**, da chung minh bang run
day du 48 thang chu khong phai bang doc code. `PROFILE_HASH`: FLATOFF `135750e04d67c263` (19 key),
FLATGATE `86636ae99c0de2d4` (20 key) — dung mot key khac nhau.

> Ghi chu ky thuat: ca hai run deu in `rc=1` sau tien trinh java (ma thoat cua sim, giong
> `run_x1_sim.sh` cu). Khong phai loi: FLATOFF tai lap `PARITY_R` **byte-identical**.

## 2. BANG CHINH — FLATGATE vs PARITY_R (48 thang, 2022-01..2025-12)

| | `X1_C3_FULL_PARITY_R` (gate DYN) | `X1_C3_FULL_FLATGATE` (gate PHANG) |
|---|---|---|
| n (dong printDone) | 2,266 | **21,382** (x9.4) |
| win% | 84.69 | **74.29** (-10.40) |
| TSloss% | 14.96 | **26.81** (+11.85) |
| mean(profit\|STOP_MARKET) | 7.333 | 7.253 (-0.08) |
| mean(profit\|STOP_LOSS) | -19.570 | -17.307 (+2.26) |
| mean(profit) | 3.308 | **0.602** (-2.71) |
| mean(margin) | 1,945 | **197** (-90%) |
| equity cuoi (b+unP) | **111,428** | **9,666** |
| CAGR% | +33.58 | **-27.51** |
| maxDD% (toan ky) | -12.46 | **-73.19** |
| underwater (ngay) | 227 | **1,456** |
| n_eff (khoi 72h co lenh) | 174 | 459 |

**CI khoi-72h x1.21, paired, toan cua so** (FLATGATE - PARITY_R):

| rate | hieu | lo | hi | ngoai CI |
|---|---|---|---|---|
| win% | -10.395 | -13.586 | -7.168 | **YES** |
| TSloss% | +11.847 | +8.471 | +15.159 | **YES** |
| mean(profit\|SM) | -0.080 | -1.220 | +1.046 | - |
| mean(profit\|SL) | +2.263 | -1.766 | +6.609 | - |
| mean(profit) | -2.706 | -4.497 | -0.899 | **YES** |
| (kiem soat) n | +19,116 | +17,384 | +20,895 | YES |
| (kiem soat) mMargin | -1,747.6 | -1,980.8 | -1,528.8 | YES |

**3/5 rate chat luong ngoai CI, ca ba cung huong XAU.** Theo nam: 2022 = 2 rate, 2023 = 3,
2024 = 3, 2025 = 2 — **khong nam nao doi chieu**.

## 3. d CAGR tren equity ngay MTM (`research/analysis/ci_flatgate.py`)

Block 21 ngay, 2000 rep, seed 20260903, 1,460 ngay, `CAP0=35000`. k=1 => **CI95 hai phia**.

| | d (pp) | lo95 | hi95 | sd_boot | P(d>0) |
|---|---|---|---|---|---|
| toan cua so | **-61.084** | -85.758 | -32.820 | 13.475 | 0.000 |
| 2022 | -68.931 | -97.567 | -23.452 | 18.107 | 0.004 |
| 2023 | -10.335 | -76.536 | +79.953 | 38.623 | 0.405 |
| 2024 | -56.227 | -100.554 | -3.398 | 25.140 | 0.021 |
| 2025 | -73.797 | -129.428 | -19.222 | 27.627 | 0.007 |

**3/4 nam CI95 tran < 0**; 2023 la nam duy nhat khong phan biet duoc (`P(d>0)=0.405`) — va do
cung la nam duy nhat FLATGATE co return duong (+49.8%). Ket qua ben theo do dai block (muc 3
cua `ci_flatgate.out`): tran cua CI95 nam trong `[-35.24, -32.65]` voi ca L=10/21/42.

## 4. NAM + RANG BUOC CUNG (tuyet doi: maxDD<=15% / UW<=120 / nam>=0 / quy>=-5%)

| tag | nam | maxDD% | UW | ret_nam% | quy_min% | PASS |
|---|---|---|---|---|---|---|
| PARITY_R | 2022 | -12.46 | 64 | +17.30 | +0.63 | **PASS** |
| PARITY_R | 2023 | -2.51 | 45 | +60.43 | +7.80 | **PASS** |
| PARITY_R | 2024 | -11.36 | 121 | +45.36 | -4.64 | FAIL (chi UW, tran 120) |
| PARITY_R | 2025 | -10.60 | 227 | +16.45 | -2.47 | FAIL (chi UW) |
| FLATGATE | 2022 | **-54.25** | 361 | **-51.63** | **-36.41** | **FAIL 4/4 muc** |
| FLATGATE | 2023 | -17.13 | 228 | +49.80 | -4.28 | **FAIL** (maxDD, UW) |
| FLATGATE | 2024 | **-33.12** | 291 | **-10.41** | **-21.72** | **FAIL 4/4 muc** |
| FLATGATE | 2025 | **-59.14** | 360 | **-57.29** | **-37.25** | **FAIL 4/4 muc** |

Doc cho dung: nen `PARITY_R` **cung** vo rang buoc o 2024/2025 — nhung chi o **underwater**
(121 va 227 ngay, tran 120), con maxDD/nam/quy deu qua. FLATGATE vo **maxDD**, **nam am** va
**quy** o 3/4 nam, tuc vo o dung nhung muc ma nen KHONG vo. Return theo quy: FLATGATE am
**11/16 quy**, te nhat `2025Q1 = -37.1%` va `2022Q2 = -36.4%`.

DCA leg 2+ (bien kiem soat): PARITY_R 20/0/2/32 leg, pnl +2,758 / 0 / -164 / +4,813;
FLATGATE 40/3/17/243 leg, pnl +192 / +32 / +31 / +60 — **nhieu leg hon 7.6 lan nhung pnl
gan nhu bang 0**, vi von moi leg da bi chia vun (mMargin 197 vs 1,945).

## 5. CO CHE + NHIP — vi sao no thua (mo ta, KHONG phai tieu chi)

| tag | nam | n | entry/ngay | collapse-day | open max | open p90 | von khoa max |
|---|---|---|---|---|---|---|---|
| PARITY_R | 2022 | 406 | 1.11 | 5 | 30 | 7.0 | 47.8% |
| PARITY_R | 2023 | 308 | 0.84 | 1 | 21 | 4.0 | 52.1% |
| PARITY_R | 2024 | 668 | 1.83 | 9 | 27 | 8.5 | 48.4% |
| PARITY_R | 2025 | 884 | 2.43 | 10 | 29 | 11.0 | 57.0% |
| FLATGATE | 2022 | 4,593 | **12.58** | **146** | 96 | 75.6 | **90.5%** |
| FLATGATE | 2023 | 2,701 | **7.40** | **79** | 55 | 39.0 | 60.6% |
| FLATGATE | 2024 | 4,946 | **13.51** | **133** | 115 | 70.0 | 67.3% |
| FLATGATE | 2025 | 9,142 | **25.12** | **245** | 113 | 80.0 | 82.2% |

**Doi chieu nhip voi 242**: so giay C3 07-11/09/2026 chay **17.0 entry/ngay**. FLATGATE
2024-2025 cho **13.5-25.1 entry/ngay** — **242 nam TRONG dai nay**, con `PARITY_R` cho
**0.84-2.43**. Day la bang chung doc lap thu tu (sau code, bins offline, va `printDone`)
rang **242 dang chay dung nhanh FLATGATE**, khong phai `C3_FULL`.

Co che thua, ba manh, do duoc:
1. **Chat luong tin hieu tut** — gate phang lay ca phan `p15` thap: `win%` -10.4pp,
   `TSloss%` +11.8pp, `meanP` 3.31 -> 0.60. Nhung `mean(profit|SM)` **khong doi** (7.33 vs 7.25):
   lenh THANG van thang y het, cai doi la **ti le** thang/thua. Gate dyn khong lam lenh tot hon,
   no **loai bo lenh xau**.
2. **Von vun** — `mMargin` 1,945 -> 197 (-90%). Lap dung pattern `5MGRID`/`K12`:
   **nhieu lenh hon = mMargin giam**. Ngan sach co dinh chia cho 9.4 lan so lenh.
3. **Von khoa + bag** — `open p90` 4-11 -> 39-76 vi the, von khoa cham **90.5%** equity (2022).
   Khi ngan sach day thi lenh tot den sau khong con cho. Collapse-day (>=4 SL/ngay) tu 1-10
   len **79-245 ngay/nam** — tuc gan **2 ngay/3** cua 2025 la collapse-day.

## 6. DU DOAN GHI TRUOC vs THUC TE (`PREREG_FLATGATE` muc 7)

| # | du doan | thuc te | dung? |
|---|---|---|---|
| 1 | ket luan A, ~75% | **A** | ✅ |
| 2 | n tang 8-15 lan | **x9.4** (2,266 -> 21,382) | ✅ |
| 3 | mMargin giam >= 60% | **-90%** | ✅ |
| 4 | win% -4..-10pp, TSloss% +4..+10pp | **-10.40pp / +11.85pp** | ✅ (hoi vuot bien duoi) |
| 5 | rang buoc cung vo >= 2 nam, nang nhat 2022 va 2025 | **vo 4/4 nam**, nang nhat **2025** roi **2022** | ✅ |
| 6 | von khoa + vi the mo tang manh | **von khoa 90.5%, open p90 x9** | ✅ |
| 7 | neu chi 2025 duong thi doc la regime | khong xay ra (2025 **am** -57.3%) | n/a |

6/6 du doan kiem duoc deu dung. Khong co du doan nao phai giai thich lai sau khi thay so.

## 7. KHONG LAM / GIOI HAN

**Khong lam**: khong adopt gi; khong sua sim theo huong B cua audit (ket qua nay bac bo huong
do); khong sweep nguong; khong doi selector/bins/dataset/cua so; khong cham 242; khong deploy;
khong mo holdout 2026; khong xoa devrun cua nguoi khac.

**Gioi han phai ghi**:
1. **Chi 1 bien the, 1 seed.** Khong do duoc phuong sai giua cac seed cua chinh FLATGATE.
   Voi do lon `d = -61 pp` va `sd_boot = 13.5` thi dieu do khong doi ket luan, nhung
   con so chinh xac -61.08 khong nen trich dan nhu mot uoc luong diem chac chan.
2. **Ngan sach la rang buoc trung tam.** FLATGATE thua mot phan lon vi von khoa 60-90%; neu
   ai do doi `CAPITAL_START` / `NUMBER_ORDER_BUDGET` thi so se khac. Run nay do **dung cau
   hinh von dang chay**, do la dieu can biet — nhung no **khong** chung minh "gate dyn tot"
   trong moi che do von. Cau hoi do chua duoc hoi va khong duoc suy ra tu day.
3. `PARITY_R` khong phai chuan vang: no cung vo `UW <= 120` o 2024/2025.
4. Do tren DEV 48 thang, **khong co VAL sach** (`AGENT_RUNBOOK` muc 0.1).
5. Nhip 17.0 entry/ngay cua 242 do tren **4.6 ngay / 1 regime** — chi dung de doi chieu
   BAC DO LON, khong phai uoc luong nhip dai han.

## 8. TAI LAP

```
cd /home/ubuntu/src/BinanceFuturesJava
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
mvn -DskipTests -o package && tools/check_cfg_gateway.sh
bash research/pipeline/x1/run_flatgate.sh FLATOFF     # cong nghiem thu, ~13'
cmp <(tail -n +2 /home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv) \
    <(tail -n +2 /home/ubuntu/java/devrun/X1_C3_FULL_FLATOFF/storage/printDone.csv)
bash research/pipeline/x1/run_flatgate.sh FLATGATE    # bien the, ~14'
python3 research/analysis/x1_rates.py X1_C3_FULL_PARITY_R X1_C3_FULL_FLATGATE
python3 research/analysis/ci_flatgate.py X1_C3_FULL_FLATGATE
```

Log tho: `/home/ubuntu/x1log/fg_build.out`, `fg_flatoff.out`, `fg_flatgate.out`,
`fg_rates.out`, `ci_flatgate.out`.
devrun: `/home/ubuntu/java/devrun/X1_C3_FULL_FLATOFF` va `.../X1_C3_FULL_FLATGATE`.
Code: commit `ee00475` (pre-reg + co che). Profile FLATGATE `PROFILE_HASH=86636ae99c0de2d4`.

## 9. HE QUA — viec tiep theo (master chot)

1. **Huong A cua audit duoc du lieu ung ho**: sua LIVE cho khop SIM. Patch da soan:
   `docs/L6_GATE_DYN_FIX.md` + goi `deploy_242_l6`. **CHO USER DUYET, chua deploy.**
2. **Huong B bi bac bo bang so**: neu sua SIM cho khop LIVE thi baseline moi la duong
   equity 9,666 / CAGR -27.5% / maxDD -73% — khong co gi de xay tiep tren do.
3. `docs/SHADOW_EVAL_20260911.md` va `docs/DEV_COLLAPSE_CHECK_20260911.md` da duoc dan khung
   canh bao: phan **nhip / so bag** cua so giay 07-11/09 khong so sanh duoc voi DEV C3_FULL.
