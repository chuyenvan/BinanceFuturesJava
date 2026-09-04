# E1_EXIT_RESULT — Ket qua batch loser time-stop horizon

Pre-registration: `docs/PREREG_EXIT.md` (commit `e6777b8`, viet va commit TRUOC khi chay
run dau tien). Profile copies: commit `1cde8e0`. Moi tieu chi duoi day duoc cham theo
dung quy tac da chot o day, khong sua sau khi thay so.

Batch: 4 run, dung quota 4/4. Dataset dung chung `/home/ubuntu/wfo_ds_e1`
(BUILD_RC=0, marketCount=2554812 predCount=2500260 fundingCount=1275677,
md5_market=459b7363f1cfa2ffb5311ac974aa2c36). `TICKER_SOURCE=aerospike` ca 4 run.

## 0. Sai lech co che so voi pre-reg (da ghi truoc khi chay)

Pre-reg muc 8 da ghi: khong dat duoc `SIM_LOSER_TIME_STOP_HOURS` qua env vi `Cfg`
fail-fast exit 2 khi `TRADING_PROFILE` da co ma con env tien to `SIM_`. Da xac thuc
truoc khi chay bang `DumpConfig` (rc=2). Vi vay TS_H dat TRONG profile:

| Tag | Profile | PROFILE_HASH |
|---|---|---|
| `X168_parity` | `profiles/c2b_min.properties` | `a2f859b2463108fe` |
| `X120` | `profiles/e1_x120.properties` | `31c1a6269aa2215e` |
| `X96` | `profiles/e1_x96.properties` | — |
| `X72` | `profiles/e1_x72.properties` | — |

Moi ban copy khac `c2b_min.properties` dung MOT dong. Khong doi tham so nao khac.
Key khong tro: `Cfg.get("SIM_LOSER_TIME_STOP_HOURS")` -> `Configs.LOSER_TIME_STOP_HOURS`
(Configs.java:469), dung tai SimulatorMarketLevelTicker1MStopLoss.java:644-646.

## 1. Parity gate — PASS (byte-identical)

| Kiem | Neo | X168_parity | Ket qua |
|---|---|---|---|
| md5 printDone.csv | `8f7afdfb27b15f5b6d4c886700def93c` | `8f7afdfb27b15f5b6d4c886700def93c` | PASS |
| so lenh | 970 | 970 | PASS |
| equity | `b:60390` | `b:60390` | PASS |

Parity dat du ba nghi pham da neu truoc o pre-reg muc 8 (dataset `wfo_ds_c2` cu da bi
xoa nen phai build lai; jar moi hon luc chay C2b; X168_parity chay o duong profile con
C2b chay o duong legacy env). Ket luan: dataset build lai reproducible va duong profile
tuong thich nguoc dung nhu tai lieu `Cfg` khai.

Ca 4 run tra `rc=1` — theo pre-reg day KHONG phai tin hieu that bai; tieu chi la log co
`done:` + `b:` va `printDone.csv` co dong. Ca 4 dat (911 dong `done:`).

## 2. Tieu chi PRIMARY

### P1 — mean(profit | status=STOP_LOSS_DONE) phai bot am va don dieu

| Tag | TS_H | n STOP_LOSS_DONE | mean(profit) | Δ vs buoc truoc |
|---|---|---|---|---|
| `X168_parity` | 168 | 147 | −18.8964 | — |
| `X120` | 120 | 172 | −16.1508 | +2.7457 |
| `X96` | 96 | 188 | −13.9948 | +2.1559 |
| `X72` | 72 | 210 | −12.3072 | +1.6877 |

**P1 = PASS** cho ca ba muc cat. Don dieu chat qua 168 -> 120 -> 96 -> 72, buoc nao cung
bot am. Do lon cua buoc giam dan (+2.75, +2.16, +1.69), phu hop voi co che da neu: cang
cat ngan cang thu them nhung lenh chet som, nhung phan gia tri con lai it dan.

### P2 — count(STOP_MARKET_DONE) khong giam qua 10% (san 741)

| Tag | TS_H | n STOP_MARKET_DONE | giam vs parity | San | P2 |
|---|---|---|---|---|---|
| `X168_parity` | 168 | 823 | base | — | — |
| `X120` | 120 | 810 | −1.58% | 741 | PASS |
| `X96` | 96 | 814 | −1.09% | 741 | PASS |
| `X72` | 72 | 800 | −2.79% | 741 | PASS |

**P2 = PASS** cho ca ba muc cat. Muc giam thuc te (−2.79% o 72h) NHO HON du bao tu
ground truth (~6.7%). Xem muc 5 ve ly do va ve mat P2 khong bat duoc.

## 3. Rang buoc CUNG

| Tag | maxDD | 2022 | 2023 | 2024 | Co nam am? | Ket qua |
|---|---|---|---|---|---|---|
| `X168_parity` | −13.1% | +11.6% | +45.4% | +6.3% | Khong | PASS |
| `X120` | −13.4% | +12.8% | +42.7% | +7.9% | Khong | PASS |
| `X96` | −10.7% | +18.0% | +41.7% | +6.5% | Khong | PASS |
| `X72` | −11.2% | +13.8% | +43.2% | +10.3% | Khong | PASS |

Ca ba muc cat thoa maxDD <= 15% va khong co nam am. maxDD KHONG don dieu theo TS_H
(13.1 -> 13.4 -> 10.7 -> 11.2) — day khong phai tieu chi nen khong anh huong phan quyet,
nhung xac nhan maxDD o day nhieu chu khong phai tin hieu.

## 4. PHAN QUYET

Quy tac da chot (pre-reg muc 7): chon TS_H NGAN NHAT thoa P1 + P2 + ca hai rang buoc cung.

Ca ba muc 120, 96, 72 deu thoa het. Ngan nhat la 72.

> ## `SIM_LOSER_TIME_STOP_HOURS = 72`

Day la ap dung may moc quy tac da pre-register, khong phai lua chon sau khi xem so.
Luu y ranh gioi: 72 la muc NGAN NHAT trong grid da khai bao, khong phai muc toi uu da
duoc chung minh. Grid khong chua muc nao ngan hon 72 nen khong biet duong cong con di
tiep hay khong — va theo pre-reg muc 7, quota 4/4 da dung, CAM chay them bien the
horizon de tim.

## 5. Rui ro va dieu P1/P2 KHONG bat duoc (ghi nhan, khong doi tieu chi)

Nhung diem duoi day khong nam trong tieu chi da pre-register nen khong duoc dung de
doi phan quyet. Ghi lai vi chung la thong tin that va can vao pre-reg lan sau.

1. **P2 do count tuyet doi, nen bo qua win rate tut.** Tong so lenh TANG theo do cat
   ngan (970 -> 982 -> 1002 -> 1010): cat som giai phong margin nen he vao them lenh
   moi. Ket qua la `STOP_MARKET_DONE` gan nhu khong giam, nhung TY LE thang tut ro:

   | Tag | STOP_MARKET_DONE / tong | win rate |
   |---|---|---|
   | `X168_parity` | 823 / 970 | 84.85% |
   | `X120` | 810 / 982 | 82.48% |
   | `X96` | 814 / 1002 | 81.24% |
   | `X72` | 800 / 1010 | 79.21% |

   P2 nhu da viet (count tuyet doi, san 741) PASS de dang vi mau so thay doi. Neu
   pre-reg dat nguong tren win rate thi ket luan co the khac. Day la loi thiet ke tieu
   chi cua toi o buoc 1, khong phai ly do de doi phan quyet bay gio.

2. **Co che thuc te khac gia thuyet.** Pre-reg gia dinh cat ngan lam MAT ~6.7% lenh
   thang. Thuc te chi mat 2.79%, vi lenh thang khong bi mat 1:1 ma duoc thay the phan
   nao bang lenh vao moi. `mean(profit | STOP_MARKET_DONE)` gan nhu khong doi (7.476 /
   7.488 / 7.463 / 7.478) — chat luong lenh thang khong bi hong, chi so luong va mau so
   doi. Gia thuyet dung ve huong nhung sai ve duong truyen.

3. **Underwater dai ra nhieu.** Chuoi ngay underwater dai nhat: 93 -> 119 -> 123 -> 156
   ngay. X72 xau nhat, dai hon parity 68%. Khong phai rang buoc da pre-register nen
   khong loai, nhung day la chi phi that va la ung vien ro rang cho rang buoc cung lan sau.

4. **2022Q1 xau di don dieu.** Quarterly ret%: +0.7 -> +0.3 -> −1.6 -> −4.4. Rang buoc
   cung dat theo NAM nen 2022 (+13.8% o X72) khong vi pham. Neu rang buoc dat theo quy
   thi X96 va X72 deu bi loai. Do phan giai cua rang buoc la mot lua chon co hau qua.

5. **mean(margin) tang** 971 -> 997 -> 1013 -> 1023: cat ngan lam von quay nhanh hon nen
   margin binh quan tren lenh cao hon. Nghia la X72 dung von nang hon parity de dat ket
   qua cua no.

## 6. Equity — KHONG phai tieu chi

Muc nay chi de bao cao. Theo pre-reg muc 6, equity khong duoc dung de chon:
`sd(Δ CAGR)` cho mot thay doi tham so exit = 2.57pp, `E[max nhieu]` cua 50 phep thu =
+7.2pp, va DEV da chay khoang 125 run.

| Tag | Equity cuoi | Tong ret | sumPNL | meanP |
|---|---|---|---|---|
| `X168_parity` | 60390 | +72.5% | 25391 | 3.48 |
| `X120` | 60812 | +73.7% | 25812 | 3.35 |
| `X96` | 62370 | +78.2% | 27371 | 3.44 |
| `X72` | 62894 | +79.7% | 27895 | 3.36 |

Bien do chenh lech (+1.2pp den +7.2pp tong ret tren 2.5 nam) nam gon trong bien nhieu
da neu. Khong dien giai nhu bang chung. Trong batch nay equity di cung chieu voi phan
quyet nen khong phat sinh xung dot; neu nguoc chieu thi P2 van thang.

## 7. Truy nguyen

| Tag | md5 printDone.csv | n lenh | equity |
|---|---|---|---|
| `C2b` (baseline) | `8f7afdfb27b15f5b6d4c886700def93c` | 970 | 60390 |
| `X168_parity` | `8f7afdfb27b15f5b6d4c886700def93c` | 970 | 60390 |
| `X120` | `1696a477e99b20f3b3984c6d1be317d4` | 982 | 60812 |
| `X96` | `358ed9fcf5c3bc3cd6a936e946dec6cc` | 1002 | 62370 |
| `X72` | `ae777461373470152b79ee73caf1dc34` | 1010 | 62894 |

Dataset `/home/ubuntu/wfo_ds_e1` da xoa sau khi cham diem (theo ke hoach, dia con ~14G).
Build lai duoc bang `ExportWfoDataset` voi `WFO_SET_PRED=ai_pred_market_gate_wfo`,
`WFO_SEL_HORIZON_IDX=0`, `WFO_CODE_SHA=1cde8e0`.
