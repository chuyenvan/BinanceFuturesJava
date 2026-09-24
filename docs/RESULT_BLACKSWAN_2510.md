# RESULT_BLACKSWAN_2510 — stress THIEN NGA DEN quanh 2025-10-10/11 (alt cascade)

Ket qua cua `research/analysis/blackswan_2510.py` (thuan Python offline, KHONG Java tren Oracle,
KHONG claude-run, DEV only: moi leg `end <= 2025-12-31`, khong doc 2026). Thuc thi DUNG
`docs/PREREG_BLACKSWAN_2510.md` (commit `ffece1f`). **Khong push.** Khong tich hop gi vao code/profile.

Log: `/home/ubuntu/blackswan/blackswan.log` · report: `report_blackswan.txt` · JSON: `blackswan.json`.

## 0. Parity artifact (bat buoc)

| nhan | md5 `printDone.csv` | n leg | eq_end | CAGR (4.50 nam) | maxDD daily toan ky |
|---|---|---|---|---|---|
| **T170** (`x1_gs_t170`, nen cu) | `efb793e2…` | 1,089 | 111,070 | 29.27% | −11.84% |
| **KEEPLEG0** (BASELINE moi) | `99e42b75…` | 1,085 | 103,083 | 27.14% | −11.21% |
| **T100** (`x1_c3_full`) | `dc16e4da…` | 2,559 | 121,770 | 31.94% | −16.13% |
| **GD92** | `cd913759…` | 2,632 | 133,944 | 34.76% | −16.55% |
| `CC_TIGHT_T170` (doi chieu) | `fad1b63e…` | 1,008 | — | — | — |

`CAPITAL_START = 35,000`. Du lieu 1m: 8,640 phut × 551 symbol (ALT universe = 549).
**Moi so duoi day la MOT quan sat lich su — KHONG co CI.** Cac muc dan nhan `[tham khao]` nam
ngoai danh sach pre-reg ⇒ **exploratory**, khong dung lam ket luan.

**Sua loi script (lan chay bi ngat truoc):** (a) bang ngay `dr` dung sai nhan cot ⇒ `KeyError`
(da sua: `dr = close(W_DAYS[i]) / close(DAYS[i]) - 1`, `DAYS[0]=20251008` la ngay neo);
(b) BTC/ETH ngay 10-09 lay sai nen (`DAYS[-2]` = 10-12 ⇒ nhin tuong lai) ⇒ da sua ve `DAYS[0]`;
(c) `conc_replay` hong (purge `open_mg` khong bao gio giam + bien `keep` khong ton tai) ⇒ viet lai
bang heap theo `end`; (d) `%` tran trong chuoi khong-format; (e) `np.percentile` → `np.nanpercentile`.
**Contract da kiem bang du lieu that** (khong tin comment): stream `KlineObjectSimple` ghi field theo
thu tu `maxPrice, minPrice, priceClose, priceOpen, totalUsdt` ⇒ `tup = (startTime, H, L, C, O, V)`,
tuc `tup[3]` = **close** nhu script gia dinh (comment trong `jbin.py` ghi `(o,h,l,c,v)` la SAI).

## 1. VIEC A — su kien that (1m UTC)

`W (UTC) = 2025-10-09 00:00 .. 2025-10-13 23:59` (5 ngay), `E = 2025-10-10`.

**A1. Bien do NGAY** `r = close(23:59 d)/close(23:59 d-1) − 1`:

| ngay (UTC) | BTC | ETH | ALT p1 | ALT p10 | ALT p50 | ALT p90 | ALT p99 | % ALT < 0 |
|---|---|---|---|---|---|---|---|---|
| 20251009 | −1.35% | −3.49% | −24.81% | −8.60% | −2.98% | 0.43% | 16.11% | 80.9% |
| **20251010 (E)** | **−7.29%** | **−12.50%** | **−49.88%** | **−37.74%** | **−28.11%** | 0.00% | 8.12% | **88.5%** |
| 20251011 | −1.89% | −1.96% | −18.51% | −6.54% | 0.00% | 9.29% | 35.28% | 41.3% |
| 20251012 | +3.90% | +10.81% | −4.77% | 0.00% | +10.44% | 18.02% | 48.75% | 2.7% |
| 20251013 | +0.19% | +2.16% | −7.45% | 0.00% | +5.02% | 11.09% | 33.76% | 8.2% |

**A2. Gio xau nhat (UTC):** `10-10 21:00` ALT p1 = **−47.22%**, p10 −29.42%, p50 −18.39% trong khi
**BTC chi −0.83%** gio do ⇒ dung kieu "BTC khong sap, ALT sap". Ke tiep: 10-10 22:00 (p1 −16.01%),
10-10 20:00 (−15.36%), 10-11 01:00 (−11.56%).

**A3. Phut:** BTC cham day `2025-10-10 21:19Z` close **103,441 = −16.35%** tu dinh W (10-09 12:41Z);
drop 1 phut lon nhat cung tai **21:19Z = −5.00%**; phut ALT sap manh nhat cung **21:19Z**
(p10 ret 1m = **−32.05%**). ⇒ Su kien la 1 cu giam trong ~1-2 gio, khong phai ca ngay.

**A4. Sap bao nhieu (close 10-13 vs close 10-09):** BTC −5.32%, ETH −2.89%;
ALT p1 −41.22% p10 −25.17% p50 −14.05%. Worst-20 ca cua so: TUT −64.0%, PORT3 −58.5%, HIPPO −58.4%,
SOLV −52.1%, DEXE −43.1%. Worst-20 **rieng ngay E**: HIPPO −62.1%, PORT3 −61.7%, TUT −57.8%,
DEXE −51.0%, PIPPIN −50.7%.
**Drawdown trong W (peak→trough tung coin):** p1 **−90.53%**, p10 −82.45%, p50 −65.69%, worst −94.3% (AIA).

## 2. VIEC B — he da bi gi trong W (artifact that)

| nhan | leg mo trong W | leg dong trong W | Σpnl(W) | max drop daily trong W | lai luy ke truoc→sau W | % bi xoa |
|---|---|---|---|---|---|---|
| T170 | 133 | 125 | **+12,106** | **0.00%** | 63,676 → 73,871 | −16.0% |
| KEEPLEG0 | 131 | 123 | **+9,943** | **0.00%** | 57,906 → 66,051 | −14.1% |
| T100 | 156 | 139 | **+14,721** | **0.00%** | 78,383 → 88,398 | −12.8% |
| GD92 | 145 | 134 | **+15,318** | **0.00%** | 80,233 → 91,967 | −14.6% |

`% bi xoa` am ⇒ **lai KHONG bi xoa, ma TANG** 12.8-16.0% trong W (equity 10-08 → 10-14:
98,676→108,871 / 92,906→101,051 / 113,383→123,398 / 115,233→126,967).

**% lai 2025 (theo leg, moc `end`) truoc / trong / sau W** — tong lai 2025 theo equity:
T170 27,375 · KEEPLEG0 24,282 · T100 17,203 · GD92 36,009.

| nhan | truoc W | trong W | sau W |
|---|---|---|---|
| T170 | 14,981 (54.7%) | 12,106 (44.2%) | 287 (1.0%) |
| KEEPLEG0 | 14,105 (58.1%) | 9,943 (41.0%) | 233 (1.0%) |
| T100 | 8,816 (51.2%) | 14,721 (85.6%) | −6,335 (−36.8%) |
| GD92 | 17,298 (48.0%) | 15,318 (42.5%) | 3,393 (9.4%) |

**Coin nang nhat trong W (max_t margin 1 coin / equity):** ca 4 nen deu la **AIA** tai
`2025-10-10 21:26Z`: T170 8,623 USDT = **8.74%** equity · KEEPLEG0 7,146 = 7.69% ·
T100 7,648 = 6.75% · GD92 7,959 = 6.91%. Doi chieu toan ky: T170 FTT 9.77% (2022-11-10),
KEEPLEG0 GAS 7.92%, T100 **CUDIS 27.84%** (2025-11-11, NGOAI W), GD92 JELLYJELLY 14.38% (2025-11-07).
⇒ Trong W, khong mot coin nao vuot 9%; thiet hai (neu co) la **he thong**, khong phai 1 coin.

`[tham khao]` (exploratory): open margin tai dinh exposure `2025-10-10 21:22Z` = 55,964 /
50,368 / 65,661 / 66,998 USDT = **56.7% / 54.2% / 57.9% / 58.1% equity**. Neu ca book −50% cung luc
⇒ −28…−29% equity. (Luu y: con so "52,151 @ 10-11 04:22 local" ghi trong pre-reg gan voi KEEPLEG0
50,368 cua ta, lech ~3% do dinh nghia `margin`: ta cong truc tiep cot `margin` cua leg dang mo.)
`[tham khao]` moc-to-market trong ngay (`b+unPMin`): W low = 82,629 / 76,523 / 93,847 / 96,298
= **−16.3% / −17.6% / −17.2% / −16.4%** so voi dinh truoc W ⇒ **lon hon maxDD daily toan ky**
(11.8-16.6%). Tuc chuoi equity NGAY (moc 07:00 local) che mat cu giam trong ngay.
`[tham khao]` leg mo trong ngay E: n = 99 / 97 / 106 / 105; Σpnl = **+5,906 / +4,198 / +5,840 / +6,687**;
phan am = −9,986 / −8,342 / −11,569 / −11,590; leg te nhat = −2,370 / −1,525 / −2,203 / −2,157 (AIA).

## 3. VIEC C — stress execution

**C1. Chi phi × k** tren moi leg dong trong W (`cost = 0.008 × margin`):

| nhan | Σmargin(W) | x2 | x5 | x10 | ΔPnL x10 / lai 2025 |
|---|---|---|---|---|---|
| T170 | 184,932 | −1,479 (−0.38 pp CAGR) | −5,918 (−1.56 pp) | −13,315 (−3.62 pp) | **48.6%** |
| KEEPLEG0 | 164,583 | −1,317 | −5,267 | −11,850 (−3.41 pp) | **48.8%** |
| T100 | 223,643 | −1,789 | −7,157 | **−16,102 (−4.10 pp)** | **93.6% ⇒ NGHIEM TRONG** |
| GD92 | 216,882 | −1,735 | −6,940 | −15,615 (−3.66 pp) | **43.4%** |

Theo nguong chot truoc (§8: > 50% lai 2025 = nghiem trong): **T100 nghiem trong**; T170/KEEPLEG0
sat nguong (48.6/48.8%); GD92 an toan.

**C2. 1 coin ve −90% / −100% khi dang giu:**

| nhan | KHONG cap (max toan ky) | ⇒ −90% | TRONG W | ⇒ −90% | CO cap replay 0.15 |
|---|---|---|---|---|---|
| T170 | FTT 9.77% | 8.79% | AIA 8.74% | 7.86% | n 1,089/1,089, chan 0 |
| KEEPLEG0 | GAS 7.92% | 7.12% | AIA 7.69% | 6.92% | n 1,085/1,085, chan 0 |
| T100 | CUDIS 27.84% | 25.06% | AIA 6.75% | 6.07% | n 2,557/2,559, chan 2, max con 13.00% (FTT) |
| GD92 | JELLYJELLY 14.38% | 12.94% | AIA 6.91% | 6.22% | n 2,632/2,632, chan 0 |

Bound ly thuyet cua cap: `0.15 × 0.90 = 13.5%` equity / su kien (khong the hon).
⇒ Trong W, **cap 0.15 khong rang buoc** (max thuc te 6.75-8.74%). Toan ky, T100 co 1 su kien
CUDIS 27.84% (2025-11-11) vuot xa 15%; GD92 sat 14.38%.
**Doi chieu artifact THAT** `CC_TIGHT_T170` (cap 0.05/5%, `fad1b63e`, n 1,008): max 1 coin =
**7.92%** (GAS) < T170 9.77% ⇒ huong dung (cap lam giam tap trung, mat 81 leg). Luu y cap KHONG
phai bound cung: 7.92% > 5% (equity tut sau luc mo ⇒ ty le vuot cap).
**C3. Stress 1 coin ve 0:** co xu ly **ca 2 che do** (co cap / khong cap) — xem bang C2.

## 4. VIEC D — "1–2 lenh lech" (trong tam)

Leg margin lon nhat dang mo trong W (ca 4 nen): **AIA**, margin 4,459 (T170) / 4,199 (KEEPLEG0) /
5,101 (T100) / 5,185 (GD92) USDT, mo `10-10 20:57Z → 21:26Z` (dung dinh su kien), pnl goc
−2,370 / −1,525 / +726 / +737.

| nhan | 1 leg Σm | −100% ⇒ ΔPnL (ΔCAGR) | %lai2025 | 2 leg Σm | −100% ⇒ ΔPnL (ΔCAGR) | %lai2025 |
|---|---|---|---|---|---|---|
| T170 | 4,459 | −4,459 (−1.17 pp) | 16.3% | 8,900 | −8,900 (−2.38 pp) | 32.5% |
| KEEPLEG0 | 4,199 | −4,199 (−1.17 pp) | 17.3% | 8,379 | −8,379 (−2.37 pp) | 34.5% |
| T100 | 5,101 | −5,101 (−1.25 pp) | 29.7% | 9,821 | −9,821 (−2.44 pp) | 57.1% |
| GD92 | 5,185 | −5,185 (−1.18 pp) | 14.4% | 9,982 | −9,982 (−2.30 pp) | 27.7% |

`ΔmaxDD = +0.00 pp` trong **moi** o (loss 1 lan <= maxDD daily san co 11.2-16.6%).
X = 20/50/80/90% day du trong `report_blackswan.txt` / `blackswan.json` (`D_grid`).

**Nguong X* xoa sach lai:**

| nhan | lai 2025 | eq_end−35,000 | X*_nam 1 leg | X*_ky 1 leg | X*_nam 2 leg | X*_ky 2 leg |
|---|---|---|---|---|---|---|
| T170 | 27,375 | 76,070 | **613.9%** | 1,705.8% | **307.6%** | 854.7% |
| KEEPLEG0 | 24,282 | 68,083 | **578.3%** | 1,621.4% | **289.8%** | 812.5% |
| T100 | 17,203 | 86,770 | **337.2%** | 1,700.9% | **175.2%** | 883.5% |
| GD92 | 36,009 | 98,944 | **694.4%** | 1,908.2% | **360.7%** | 991.2% |

⇒ Moi X*_nam > 100% ⇒ theo nguong chot truoc (§8): **BOUND**.

## 5. KET LUAN (tra loi 4 cau hoi)

1. **Su kien 11/10 ton bao nhieu PnL trong sim (4 nen)?** Theo thang do pre-reg (equity NGAY, moc
   07:00 local): **KHONG ton dong nao — W lai DUONG**: Σpnl leg dong trong W = **+12,106 / +9,943 /
   +14,721 / +15,318 USDT** (T170/KEEPLEG0/T100/GD92); equity tu 10-08 den 10-14 **tang** 10.3% / 8.8% /
   8.8% / 10.2%. Ly do: he mo leg rat nhieu ngay TRONG cu sap (10-10 20:57Z, dung day) va ALT hoi
   manh 10-12/13. Nhung `[tham khao]` moc-to-market trong ngay `b+unPMin` cho thay cu giam thuc su
   **−16.3 / −17.6 / −17.2 / −16.4% equity** — **lon hon maxDD daily toan ky** — va 99-106 leg mo
   trong ngay E co phan am −8.3k…−11.6k (leg te nhat AIA −1.5k…−2.4k). ⇒ Cau "ton bao nhieu" phu
   thuoc thang do: **daily = 0 (lai +), intraday = 16-18% equity**. Khong co CI, 1 quan sat.
2. **Can 1-2 lenh lech bao nhieu de xoa sach lai?** X*_nam (theo margin **leg lon nhat dang mo trong W**,
   do bang equity daily): **614% / 578% / 337% / 694%** cho 1 leg; **308% / 290% / 175% / 361%** cho 2 leg.
   X*_ky = 812-1,908%. ⇒ Một lenh lech toi da (−100% margin) **khong the** xoa sach lai 1 nam: phai mat
   3.4x-6.9x margin (1 leg) / 1.8x-3.6x (2 leg). Cu the: −100% 2 leg = −9.8k USDT = **57% lai 2025 cua
   T100** (nen xau nhat), 27-35% voi 3 nen con lai.
3. **`conc <= 15%` co bound duoc thiet hai khong?** **Bound cho 1 coin, KHONG bound cho he thong.**
   Ly thuyet: 1 coin ≤ 15% equity ⇒ mat toi da 13.5%/su kien (dung). Thuc te trong W: max 1 coin
   = 6.75-8.74% equity (AIA) ⇒ cap **khong he rang buoc** trong cu sap 11/10. Cai lam thiet hai
   trong W la **nhieu coin cung luc**: ALT p50 ngay E −28.1%, drawdown trong W p50 = −65.7% moi coin;
   open margin cung luc = **54-58% equity** ⇒ book −50% = −28% equity. Doi chieu that
   `CC_TIGHT_T170` (cap 5%) chi ha max 1 coin 9.77% → 7.92% (huong dung, nhung 7.92% > 5% ⇒ cap
   khong phai bound cung) va mat 81 leg.
4. **Co su kien nao xoa sach lai khong?** Tren artifact DEV nay: **KHONG** — moi kich ban lech/chi phi
   toi da chi an 14-57% lai 2025, va X*_nam ≥ 175% ⇒ **BOUND** theo §8. De xuat (khong tu tich hop):
   (a) **tran mat-that/leg** theo `X*` chu khong chi theo `% margin` — dat so tuyet doi
   (vi du `max loss/leg <= 5% lai 2025`), vi margin 5k USDT hien tai da ~15-30% lai nam cua nen xau;
   (b) **tran gross exposure** (hien 54-58% equity mo cung luc; 1 cu −50% toan book = −28% equity) —
   day moi la rang buoc that su, khong phai `conc 15%`;
   (c) **do va tran theo bien dong trong NGAY** (`unPMin`): tail 16-18% lon hon maxDD daily
   11-17% ⇒ neu chi nhin equity ngay se danh gia thap rui ro duoi;
   (d) hedge/backstop khi `|1h ALT p10| > 20%` va BTC khong giam (dac trung cascade 11/10) — can
   kiem bang sim truoc khi tich hop.

## 6. Gioi han (bat buoc noi ro)

- **Khong co CI**: moi so la 1 quan sat lich su; khong duoc goi nen nao la "tot hon" tu 1 su kien.
- Do thi VIEC D/C la **xap xi offline** (equity moc NGAY, khong phai moc phut; khong phai sim lai).
- `conc_replay` la **xap xi** (khong phai sim): T100 chan 2 leg, khong doi 2,559→2,557.
- Kich ban "exit fail" = gia dinh chiu −X% margin; khong mo hinh hoa slippage thuc khi dung thanh khoan.
- Deviation nho da ghi: T100 max 1 coin toan ky do ta tinh = **27.84%** vs **28.51%** neu trong pre-reg
  (khac diem tham chieu equity: moc phut peak vs luc mo leg); T170 9.77% va GD92 14.38% **khop**.
- Khong doc 2026. Khong push.
