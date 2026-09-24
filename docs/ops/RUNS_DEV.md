# Nhat ky run DEV (2022-01 -> 2024-06, von goc 35,000)

Do bang `python3 /home/ubuntu/java/fsrun/qret.py <TAG>...` tren `devrun/<TAG>/storage/printDone.csv`.
Ung vien hien tai: **C2b**. Chua co gi thay the duoc no.

| run | cau hinh khac C2b | equity | 2022 | 2023 | 2024H1 | maxDD | underwater | verdict |
|---|---|---|---|---|---|---|---|---|
| **C2b** | — (ung vien) | **60,390** | +11.6 | +45.4 | +6.3 | **−13.1** | **93d** | giu |
| H1a_mom006 | **nen C2a** + mom 0.006 | 60,953 | +4.1 | +53.6 | +8.9 | −21.1 | 108d | truot maxDD |
| H1b_rmax30 | nen C2a + RATE_MAX 0.30 | 47,143 | **−31.6** | +94.4 | +1.3 | **−44.3** | 444d | tham hoa |
| H1c_both | nen C2a + ca hai | 37,145 | −35.2 | +67.0 | −2.0 | **−51.3** | 699d | tham hoa |
| K0_h1a_prof | **nen C2b** + mom 0.006 | 59,580 | +4.5 | +51.6 | +7.4 | −21.0 | 133d | kem C2b |
| K1_conc25 | K0 + MAX_CONCURRENT=25 | 59,580 | | | | | | **VO HIEU** (giong het K0 tung byte) |
| K2_conc20 | K0 + MAX_CONCURRENT=20 | 59,580 | | | | | | **VO HIEU** |
| BR1_margin | SIM_BREAKER_MODE=MARGIN | 60,272 | +11.5 | +45.5 | +6.1 | −13.1 | 93d | khong doi gi |
| BR2_both | SIM_BREAKER_MODE=BOTH | 60,272 | *giong het BR1* | | | −13.1 | 93d | khong doi gi |
| BR3_mg006 | MARGIN + mom 0.006 | 59,542 | +5.6 | +50.9 | +6.8 | **−20.9** | 133d | breaker KHONG cuu duoc DD |

## Ket luan

1. **`PREDICT_SYMBOL_RATE_MAX` la truc chet** (H1b/H1c). Khong dung nua.
2. **Noi `MIN_MOMENTUM_15M` nhap ve lenh xau cua RIENG 2022**: 2022 roi +11.6 -> +4.5 trong khi
   2023/2024 tot len.
3. **BR3 vs K0: DD −21.0 -> −20.9.** Breaker margin gan nhu khong nhuc nhich => DD do noi gate
   KHONG phai tu viec mo qua nhieu lenh, ma tu gia chay nguoc tren lenh DA MO.
   => Khong co che phoi nhiem nao thay duoc **tin hieu regime**.
4. **`MAX_CONCURRENT` tro khi `BREAKER_MODE=OFF`** — sim khong co tran cung lenh dong thoi.
5. Breaker MARGIN o muc phoi nhiem cua C2b gan nhu khong bind (970 -> 962 lenh, equity −118).

## Bay baseline — PHAI kiem truoc khi so
`dev_h1.sh` KHONG dat `TS_GAP_CONST`/`TIER_FLAT`/`SELECTOR_ONLY_ENTRY` => H1a/H1b/H1c dung tren
**C2a**, khong phai C2b. Da co mot lan so nham hai baseline.
Tu nay moi run in `PROFILE_HASH` (he TRADING_PROFILE, commit cb073af) — tra hash thay vi doan.
Profile cua tung run luu trong `profiles/`.
