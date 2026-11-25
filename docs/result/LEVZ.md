# RESULT_LEVZ - PREREG_LEVZ @5e1031bc (agent RUN, chua audit)
Thoi gian chay: V0 16:56-17:04, build 17:05-17:12, KHAM PHA 17:12, checks 17:13-17:16, FREEZE 17:17:41 (+07), XAC NHAN 17:17-17:18 (1 lan), V5 rerun 17:19-17:21.
Code dong bang: FREEZE.txt (sha256 7 file; sha256sum -c OK truoc V5). Khong sua code sau freeze; KHONG co bug sau freeze duoc khai.

## VERDICT: NO-GO (DONG ho LEVZ). Ca 4 nhanh truot C1 (p Holm 0.53-0.79) va C5 (bo 5% tot nhat => am o moi nhanh).

## V0 - du lieu (logs/v0.log, work/v0.json)
- kline1m 49 file 2021-12..2025-12: 138 -> 611 sym/thang, median phut/sym = du thang, lien tuc theo phut (median count/span = 1.000), dup 0. File nho vi CHI giu cot (ts, sym, close) - KHONG phai tap con thoi gian.
- Phu coin-ngay universe (qv30>=20M): 2022 99.77% (thieu 84 coin-ngay o 2022-02/04), 2023 100%, 2024 100%, 2025 100%. metrics5m va funding: 100% sym-coin-ngay universe moi nam. => KHONG DUNG.
- HAN CHE: khong co cot high => MAE do bang close 1m (can duoi). Nguon co high: /home/ubuntu/java/fsrun/OHLCV_1H_v2.bin (+manifest; 1h OHLCV, 626 sym, 2021-01..2025-12, tu Aerospike kline_1m_opt) - CHUA dung, chi liet ke.

## V1-V3 (KHAM PHA, out/checks_explore.json)
- V1a: 200 moc x 2 W, thay ngau nhien moi du lieu sau t (OI, close, funding) => z_oi, z_r, f, z_f tai t KHONG doi: 0 mismatch.
- V1b: 200 moc tai dung tu file tho (x=ln oi ban ghi (t-70m,t-10m], close gio, P0, f): 0 mismatch.
- V2: 3 lenh A1 co fund_24>0 (CELR 2022-03-31 16h, IOST 17h, TRB 2022-08-10 01h): tong rate tho = fund_24, net - gross + 0.14% = +fund => short duoc CONG.
- V3: 10/10 lenh (5 A1, 5 A2) P(te) = close tho nen 1m open_time==te.
## V5: chay lai explore+confirm+score: md5 14 file output trung 100% (logs/md5_run1.txt vs md5_run2.txt).

## V4 (mo ta)
- So dot (t0) theo nam: W14: 2022 4, 2023 161, 2024 365, 2025 104. W7: 2022 6, 2023 174, 2024 419, 2025 158. 2022 gan nhu khong co dot: chi 0.14-0.20% gio-universe co f>0.0001 (2023-H2: 19.5%) - che do funding, khong phai thieu du lieu (z_f huu han >=99.4%).
- Ti le dot dang chiu san sd (z_f hoac z_oi): KHAM PHA W14 45.5% (toan bo do san f), W7 46.1%; XAC NHAN W14 17.7%, W7 27.4%.
- f(t0) quantile 5/25/50/75/95 (XAC NHAN W14): 0.026%/0.040%/0.061%/0.098%/0.244% per 8h; dOI24h: 2.8%/8.3%/13.9%/25.8%/59.4%.
- E1: KHAM PHA W14 122/165 = 73.9% co xac nhan trong 24h, tre trung vi 7h; W7 130/180 = 72.2%, 5.5h. XAC NHAN W14 340/469 = 72.5%, 6h; W7 406/577 = 70.4%, 6h.

## Bang ket qua chinh (net_ex 24h la chi tieu; % la loi suat/lenh)
### GIA THUYET A1-A4 - explore
| nhanh | n | mean net_ex24 | median | CI95 | p1 | p_holm | MDE80 | net tho24 | net_ex4 | net_ex72 | net4 | net72 | net_ex24 stress | net24 stress | drop top5 | MAE>=10% | MAE>=20% | fund24 | E1 xac nhan / lag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 165 | 0.3954% | 0.6828% | [-0.9052% ; 1.3661%] | 0.2502 | NA | 1.4605% | 0.8625% | 0.0010% | 0.6669% | 0.2877% | 0.4472% | 0.2954% | 0.7625% | -0.2922% | 14.5% | 3.0% | 0.0867% | -/165, -h |
| A2 | 122 | 0.3686% | 1.1598% | [-1.1152% ; 1.4321%] | 0.2534 | NA | 1.5803% | 0.1497% | -0.1793% | 0.4169% | 0.0418% | 0.2259% | 0.2686% | 0.0497% | -0.1900% | 16.4% | 2.5% | 0.0783% | 122/165, 7.0h |
| A3 | 180 | 0.3261% | 0.9458% | [-1.2847% ; 1.2666%] | 0.3543 | NA | 1.6898% | 0.5846% | -0.0654% | 0.9717% | 0.3014% | -0.0505% | 0.2261% | 0.4846% | -0.3118% | 13.9% | 3.3% | 0.0844% | -/180, -h |
| A4 | 130 | 0.2960% | 1.1399% | [-2.0148% ; 1.7996%] | 0.3998 | NA | 2.4478% | -0.6595% | 0.0496% | 0.1198% | 0.2095% | -1.2610% | 0.1960% | -0.7595% | -0.4158% | 16.2% | 4.6% | 0.0762% | 130/180, 5.5h |

Theo nam (t0) mean net_ex24 (n):
- A1: 2022 9.8147% (4), 2023 0.1614% (161)
- A2: 2022 -1.1423% (2), 2023 0.3937% (120)
- A3: 2022 4.5357% (6), 2023 0.1809% (174)
- A4: 2022 8.9479% (2), 2023 0.1608% (128)

### CHI MO TA (khong dung de tuyen bo) - explore
| nhanh | n | mean net_ex24 | median | CI95 | p1 | p_holm | MDE80 | net tho24 | net_ex4 | net_ex72 | net4 | net72 | net_ex24 stress | net24 stress | drop top5 | MAE>=10% | MAE>=20% | fund24 | E1 xac nhan / lag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D_W14_mirror | 1071 | -0.0209% | -0.9113% | [-0.4902% ; 0.4797%] | 0.5202 | NA | 0.6123% | -0.0838% | -0.1171% | -0.3461% | -0.1522% | -0.5674% | -0.1209% | -0.1838% | -1.4041% | NA | NA | 0.2267% | -/1071, -h |
| D_W14_only_zf | 1065 | 0.1158% | 0.5524% | [-0.2066% ; 0.4833%] | 0.2583 | NA | 0.4377% | 0.4505% | -0.1061% | 0.2870% | 0.1490% | -0.2717% | 0.0158% | 0.3505% | -0.3484% | 9.7% | 2.2% | 0.0799% | -/1065, -h |
| D_W14_only_zoi | 3974 | 0.0875% | 0.7189% | [-0.0926% ; 0.2671%] | 0.1731 | NA | 0.2273% | 0.2713% | -0.0932% | 0.0403% | -0.0743% | 0.5113% | -0.0125% | 0.1713% | -0.5268% | 13.9% | 4.2% | -0.0652% | -/3979, -h |
| D_W7_mirror | 1346 | -0.3660% | -0.9078% | [-0.7324% ; 0.0033%] | 0.9747 | NA | 0.4692% | -0.2736% | -0.1298% | -0.5100% | -0.1959% | -0.4623% | -0.4660% | -0.3736% | -1.4902% | NA | NA | 0.1846% | -/1346, -h |
| D_W7_only_zf | 1097 | 0.1881% | 0.5867% | [-0.1086% ; 0.5054%] | 0.1198 | NA | 0.3869% | 0.3964% | -0.1027% | 0.3808% | 0.1513% | -0.4444% | 0.0881% | 0.2964% | -0.2653% | 9.1% | 2.0% | 0.0723% | -/1097, -h |
| D_W7_only_zoi | 5687 | 0.0932% | 0.5752% | [-0.0436% ; 0.2350%] | 0.0992 | NA | 0.1778% | 0.2497% | -0.0319% | 0.0766% | 0.0340% | 0.4867% | -0.0068% | 0.1497% | -0.4436% | 11.3% | 3.0% | -0.0429% | -/5692, -h |
| D_hard | 64 | 2.0172% | 1.5709% | [-0.0743% ; 3.6754%] | 0.0066 | NA | 2.4285% | 2.3638% | 0.4771% | 1.9264% | 0.5407% | 1.7766% | 1.9172% | 2.2638% | 0.8186% | 18.8% | 7.8% | 0.0986% | -/64, -h |

Theo nam (t0) mean net_ex24 (n):
- D_W14_mirror: 2022 0.6762% (596), 2023 -0.8955% (475)
- D_W14_only_zf: 2022 1.3390% (36), 2023 0.0730% (1029)
- D_W14_only_zoi: 2022 0.1521% (2055), 2023 0.0183% (1919)
- D_W7_mirror: 2022 -0.1155% (753), 2023 -0.6841% (593)
- D_W7_only_zf: 2022 1.1193% (77), 2023 0.1178% (1020)
- D_W7_only_zoi: 2022 0.2327% (2928), 2023 -0.0548% (2759)
- D_hard: 2022 -4.3769% (2), 2023 2.2235% (62)

V4 explore: ```{"W14_lev": {"doi24_q": [0.027380040663150872, 0.09453615196133347, 0.15342336053459027, 0.2816317017209059, 0.9629997796146912], "episodes_by_year": {"2022": 4, "2023": 161}, "f_q": [0.00023785400000000002, 0.00029948, 0.00040337, 0.0005204, 0.0009285699999999999], "floor_any_rate": 0.45454545454545453, "floor_f_rate": 0.45454545454545453, "floor_oi_rate": 0.0}, "W7_lev": {"doi24_q": [0.03767321056697739, 0.08693650947439546, 0.14647174856690937, 0.2240077070776909, 0.7932170905237129], "episodes_by_year": {"2022": 6, "2023": 174}, "f_q": [0.000255517, 0.000318535, 0.0004045, 0.0005525575, 0.0009239024999999994], "floor_any_rate": 0.46111111111111114, "floor_f_rate": 0.4388888888888889, "floor_oi_rate": 0.03333333333333333}}```

### GIA THUYET A1-A4 - confirm
| nhanh | n | mean net_ex24 | median | CI95 | p1 | p_holm | MDE80 | net tho24 | net_ex4 | net_ex72 | net4 | net72 | net_ex24 stress | net24 stress | drop top5 | MAE>=10% | MAE>=20% | fund24 | E1 xac nhan / lag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 469 | 0.4412% | 1.5910% | [-0.5845% ; 1.6200%] | 0.2255 | 0.6764 | 1.3915% | 0.3201% | 0.0515% | 0.7647% | 0.2834% | 0.2245% | 0.3412% | 0.2201% | -0.8548% | 25.8% | 10.9% | 0.1517% | -/469, -h |
| A2 | 340 | 0.8483% | 1.1642% | [-0.3743% ; 2.5355%] | 0.1329 | 0.5315 | 1.8107% | -0.1271% | 0.4311% | -1.0832% | 0.2489% | -3.1535% | 0.7483% | -0.2271% | -0.7123% | 30.9% | 11.2% | 0.1247% | 340/469, 6.0h |
| A3 | 577 | -0.0819% | 0.7399% | [-0.9126% ; 0.8952%] | 0.5774 | 0.7871 | 1.1310% | 0.0354% | 0.1133% | 0.0871% | 0.2154% | 0.0305% | -0.1819% | -0.0646% | -1.4526% | 25.0% | 10.4% | 0.1450% | -/577, -h |
| A4 | 406 | 0.1578% | 0.7354% | [-1.0346% ; 1.5333%] | 0.3936 | 0.7871 | 1.6037% | -0.6493% | 0.4824% | 0.4839% | 0.3862% | -0.8808% | 0.0578% | -0.7493% | -1.3256% | 29.8% | 9.4% | 0.1149% | 406/577, 6.0h |

Theo nam (t0) mean net_ex24 (n):
- A1: 2024 0.1392% (365), 2025 1.5011% (104)
- A2: 2024 0.0128% (263), 2025 3.7018% (77)
- A3: 2024 -0.4878% (419), 2025 0.9945% (158)
- A4: 2024 -0.5714% (299), 2025 2.1955% (107)

### CHI MO TA (khong dung de tuyen bo) - confirm
| nhanh | n | mean net_ex24 | median | CI95 | p1 | p_holm | MDE80 | net tho24 | net_ex4 | net_ex72 | net4 | net72 | net_ex24 stress | net24 stress | drop top5 | MAE>=10% | MAE>=20% | fund24 | E1 xac nhan / lag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D_W14_mirror | 1007 | 0.3680% | -1.0960% | [-0.3764% ; 1.1464%] | 0.1732 | NA | 0.9708% | 0.4122% | -0.4804% | 0.7856% | -0.5182% | 0.9924% | 0.2680% | 0.3122% | -1.7233% | NA | NA | 0.6747% | -/1007, -h |
| D_W14_only_zf | 2526 | 0.1244% | 0.7548% | [-0.2340% ; 0.5518%] | 0.2603 | NA | 0.4954% | 0.2153% | -0.0979% | 0.3824% | -0.0685% | -0.1983% | 0.0244% | 0.1153% | -0.7716% | 17.9% | 5.1% | 0.1323% | -/2526, -h |
| D_W14_only_zoi | 5091 | -0.1893% | 0.5825% | [-0.4476% ; 0.0584%] | 0.9265 | NA | 0.3240% | -0.0125% | 0.0041% | -0.6378% | 0.0227% | -0.1902% | -0.2893% | -0.1125% | -1.0860% | 18.8% | 6.6% | -0.1385% | -/5091, -h |
| D_W7_mirror | 1330 | 0.2294% | -1.1049% | [-0.4488% ; 0.9835%] | 0.2608 | NA | 0.9103% | 0.3987% | -0.3129% | 0.9069% | -0.3006% | 1.2663% | 0.1294% | 0.2987% | -1.8113% | NA | NA | 0.5805% | -/1330, -h |
| D_W7_only_zf | 2884 | 0.1017% | 0.6154% | [-0.1629% ; 0.4789%] | 0.2555 | NA | 0.4055% | 0.3149% | -0.0244% | 0.7188% | -0.0465% | 0.4619% | 0.0017% | 0.2149% | -0.7782% | 17.9% | 5.0% | 0.1209% | -/2884, -h |
| D_W7_only_zoi | 7421 | -0.1851% | 0.5180% | [-0.3996% ; 0.0283%] | 0.9530 | NA | 0.2735% | -0.0548% | -0.0985% | -0.6033% | -0.0546% | -0.1264% | -0.2851% | -0.1548% | -0.9859% | 16.9% | 5.5% | -0.0897% | -/7421, -h |
| D_hard | 392 | -2.0435% | 1.9868% | [-5.9445% ; 0.5413%] | 0.8815 | NA | 4.1155% | -2.1522% | -0.0603% | -6.5280% | -0.1055% | -6.5214% | -2.1435% | -2.2522% | -4.1152% | 37.8% | 23.2% | 0.1944% | -/392, -h |

Theo nam (t0) mean net_ex24 (n):
- D_W14_mirror: 2024 -0.0543% (380), 2025 0.6239% (627)
- D_W14_only_zf: 2024 -0.0260% (1941), 2025 0.6233% (585)
- D_W14_only_zoi: 2024 -0.0938% (2469), 2025 -0.2793% (2622)
- D_W7_mirror: 2024 -0.2011% (490), 2025 0.4805% (840)
- D_W7_only_zf: 2024 -0.0653% (2143), 2025 0.5847% (741)
- D_W7_only_zoi: 2024 -0.1232% (3683), 2025 -0.2461% (3738)
- D_hard: 2024 -0.6927% (246), 2025 -4.3195% (146)

V4 confirm: ```{"W14_lev": {"doi24_q": [0.028354421878930315, 0.08294241294101723, 0.13890099108581633, 0.25849208733166495, 0.5941142362510654], "episodes_by_year": {"2024": 365, "2025": 104}, "f_q": [0.000259304, 0.0004015, 0.00060801, 0.00098023, 0.0024416439999999998], "floor_any_rate": 0.17697228144989338, "floor_f_rate": 0.16844349680170576, "floor_oi_rate": 0.008528784648187633}, "W7_lev": {"doi24_q": [0.03910643198565707, 0.07535262170411627, 0.12710684495829572, 0.24139983556589772, 0.5999993683689793], "episodes_by_year": {"2024": 419, "2025": 158}, "f_q": [0.000259096, 0.00038406, 0.0005685, 0.00092216, 0.002508335999999998], "floor_any_rate": 0.2738301559792028, "floor_f_rate": 0.2270363951473137, "floor_oi_rate": 0.0658578856152513}}```

### C1-C8
| nhanh | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | ket luan |
|---|---|---|---|---|---|---|---|---|---|
| A1 | TRUOT | DAT | DAT | DAT | TRUOT | DAT | CHUA_KET_LUAN_proxy_close | DAT | TRUOT |
| A2 | TRUOT | DAT | TRUOT | DAT | TRUOT | TRUOT | TRUOT | DAT | TRUOT |
| A3 | TRUOT | DAT | DAT | DAT | TRUOT | DAT | CHUA_KET_LUAN_proxy_close | TRUOT | TRUOT |
| A4 | TRUOT | DAT | TRUOT | DAT | TRUOT | TRUOT | CHUA_KET_LUAN_proxy_close | DAT | TRUOT |

VERDICT: NO-GO (DONG ho LEVZ)

Ghi chu bang: C7 dung MAE_close (can duoi MAE that). A2 MAE_close>=10% = 30.9% > 30% => TRUOT chac chan; A1/A3/A4 (25.8/25.0/29.8%) <= 30% theo close nhung MAE that co the cao hon => CHUA KET LUAN (khong anh huong verdict vi da truot C1, C5). n_sub (gia cuoi thay the): 24h 1 lenh, 72h 2 lenh moi nhanh XAC NHAN (do cham 2025-12-31 23:59); 0 lenh thieu P(te).

## CHI MO TA (khong tinh k, KHONG duoc dung de tuyen bo) - xem bang D_* o tren
- Nguong CUNG (f>=0.05%/8h & dOI24h>=25%): KHAM PHA +2.02% (n 64, p 0.007) nhung XAC NHAN -2.04% (n 392), MAE_close>=10% 37.8% - dao dau.
- Chi z_oi: XAC NHAN am (W14 -0.19%, W7 -0.19%); chi z_f: duong nho khong y nghia (+0.10..+0.12%).
- Guong LONG: mean net_ex XAC NHAN +0.37%/+0.23% nhung median -1.1% (duoi phai), KHAM PHA ~0/-0.37%.

## LUA CHON CAI DAT (ghi trong CHOICES.md truoc khi chay KHAM PHA)
1. Gia: kline1m chi co (ts, sym, close) - KHONG co high/open/low. close(t) cho r1h = close phut cuoi co trong gio [t-1h, t) (open_time <= t-1m). P(te) = close nen 1m open_time == te (dung prereg); thieu => lenh bi loai (dem n_noprice).
2. MAE: KHONG co high 1m => do MAE_close = max(close 1m, open_time trong [te, te+H-1m]) / P(te) - 1. Day la CAN DUOI cua MAE that. C7: neu ti le MAE_close>=10% > 30% => TRUOT chac chan; neu <= 30% => C7 CHUA KET LUAN (bao MASTER), khong tu thay nguon.
3. P(te+H): close nen 1m open_time == te+H; thieu => close cuoi cung co voi open_time <= te+H (gan co), dem n_sub. Voi XAC NHAN, te+H vuot 2025-12-31 23:59 => dung close cuoi <= 2025-12-31 23:59 (dem n_sub), khong doc 2026.
4. Funding cong cho lenh: tong rate cac ky ts in (te+1m, te+H+1m] (khop thoi gian giu thuc: khop lenh o close nen te, thoat o close nen te+H). Ban "chu nghia" (te, te+H] chi luu cot fund_lit_* de A1 doi chieu, KHONG dung cho C. (Bao thu: ky thanh toan ngay sau te ~ te+6ms khong duoc tinh vi lenh chua mo.)
5. OI hop le tai t: ban ghi moi nhat co ts in (t-70m, t-10m], oi>0 (toi da tre 1h; cu hon => NaN).
6. f(t): ky thanh toan moi nhat ts <= t-1m va con "hien hanh" (t - ts <= interval_h gio + 1m), nguoc lai NaN. Cua so z_f: cac ky ts in [t-W, ky moi nhat) ; ky vong = W_gio / interval_h(ky moi nhat); can n >= 0.8*ky vong va n >= 2.
7. sd: ddof=1 cho moi z (oi, f, r1h). Cua so z_oi, z_r: W*24 moc gio [t-W, t-1h], can >= ceil(0.8*W*24) gia tri. z_r: khong san sd; sd==0 => NaN; cung yeu cau 80%.
8. Universe ngay D: sym ket thuc USDT, khong co '_', base khong thuoc {USDC,BUSD,TUSD,FDUSD,USDP,DAI,UST,USDE,EUR,AEUR,BTCDOM,DEFI,BLUEBIRD,FOOTBALL}; qv30 = trung binh qv d1 cua 30 ngay lich D-30..D-1 (du ca 30 ngay) >= 20M; niem yet: ngay dau co trong d1 <= D-45 (d1 bat dau 2021-01-01 => coin cu coi nhu da niem yet). Ap cho moi gio cua ngay D.
9. Cooldown: t0 moi chi khi t0 truoc cua coin do cach > 72h (t0 cu dung 72h truoc => van chan). Cooldown tinh tren toan chuoi tu 2021-12 (ke ca dot truoc ky) roi moi loc theo ky.
10. Ky gan lenh theo t0 (KHAM PHA: t0 in [2022-01-01, 2024-01-01); XAC NHAN: [2024-01-01, 2026-01-01)). Nam (C4) theo t0. Lan chay KHAM PHA chi nap du lieu < 2024-02-01 (du cho H=72h + E1). Buoc build (hr_/oi_ parquet) va V0 da doc tho 2024-2025 de dung bang gio/dem phu, KHONG tinh tin hieu/ket qua.
11. EW tai te: trung binh deu (P_i(end)/P_i(te) - 1) tren moi coin universe tai te co P(te) huu han (gom ca chinh coin), cung quy tac P(end) muc 3; net_ex = net - side*EW (short: net + EW).
12. Bootstrap: cum tuan lich bat dau thu Hai (UTC) theo te; 10000 lan, seed 20261125; mean trong so theo lenh; CI percentile 2.5/97.5; p mot phia = (1 + #(boot - obs >= obs)) / 10001 (bootstrap dich tam); SE = sd boot; MDE80 = (1.645+0.842)*SE.
13. Holm: 4 nhanh, ky XAC NHAN. Bo 5% tot nhat: bo ceil(0.05 n) lenh net_ex_24 lon nhat.
14. Stress phi: net - 0.001 (0.24% thay 0.14%); C8 ap cho mean net_ex_24 stress (chi tieu chinh) - net tho stress cung bao.
15. C7 ap tren XAC NHAN H=24h (cung ky voi C5/C6/C8); KHAM PHA bao kem.
16. Mo ta: guong LONG (z_oi>2.5, z_f<-2.5, f<0; side +1, funding long tra khi rate>0, net_ex = net - EW, khong co MAE); chi z_oi (z_oi>2.5); chi z_f (z_f>2.5, khong them dieu kien f); nguong cung (f>=0.0005 VA dOI24h>=0.25, dOI24h = oi(t)/oi(t-24h)-1 cung quy tac tre OI). Tat ca chi E0, cooldown 72h. Khong dung de tuyen bo.
17. Lenh E1: z_r tai t1 in (t0, t0+24h]; khong yeu cau universe tai t1. Mot t0 -> toi da 1 lenh moi kieu.

## File
- code/: common.py v0.py build_hourly.py levz.py checks.py score.py diag_explore.py ; FREEZE.txt ; CHOICES.md ; RUN_EXPLORE.md ; RUN.progress
- out/: events_{A1..A4,D_hard}_{explore,confirm}.parquet, summary_{explore,confirm}.json, score.json, tables_all.md, checks_explore.json
- work/: hr_*.parquet, oi_*.parquet (bang gio trung gian, ~213 MB), v0.json
