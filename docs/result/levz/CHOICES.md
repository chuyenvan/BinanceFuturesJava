# LUA CHON CAI DAT (ghi TRUOC khi chay KHAM PHA va XAC NHAN; 2026-11-25 ~17:10 UTC+0)
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
