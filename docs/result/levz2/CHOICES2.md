# CHOICES2 - lua chon cai dat LEVZ2 (PREREG_LEVZ2 @278725ae) - ghi TRUOC khi chay luoi
Nguyen tac: cho prereg khong noi ro => chon cach BAT LOI hon (neu xac dinh duoc), khong thi chon cach trung tinh + ghi lai.
Muc "CAN MASTER QUYET" o cuoi: da cai mac dinh nhung MASTER phai xac nhan truoc khi chay luoi.

## Du lieu / nhan gio
1. Luoi gio: chi so k <-> T_k = 2021-12-01 + k gio = gio quyet dinh `h` cua tang 1 (thong tin den het T_k). Gia: hang k = nen store
   [T_k - 1h, T_k) (store ts_h = gio DONG = T_k). Quy uoc xac dinh BANG DU LIEU (S2): store t == panel h + 1h khop 99.999 %, store t == h chi 10.6 %.
2. Gia vao = close nen [t-1h, t) cua store (prereg "close gio t"). Tang 1 dung close nen 1m mo luc t (som hon ~1 phut sau) => lech nho
   (smoke: median |lech gia vao| 0.16 %, max 7.3 %).
3. Reader store: assert gio MO nen < 2026-01-01 (nen dong luc 2026-01-01 00:00 = du lieu 2025-12-31 23:xx, duoc phep doc nhung sim KHONG
   dung vi luoi ket thuc o T = 2025-12-31 23:00). Funding / tin hieu: reader tang 1 (assert ts < 2026-01-01).
4. Funding: ky thanh toan gan vao moc gio gan nhat (lech quan sat 0..47 ms). Nguon = funding lake tang 1 (common.read_funding; dedupe (sym, ts)
   giu ban cuoi; rate huu han; interval_h > 0).
5. Thu tu coin = D.syms tang 1 (sap xep tang dan) => pha hoa "sym tang dan" = chi so coin tang dan.

## Ung vien
6. LEV = u & z_oi >= z_min & z_f >= z_min & f > 0.0001 (">=" theo prereg2; tang 1 dung ">" - bang nhau xac suat 0). NaN => khong.
7. Can gia store tai gio vao (khong co nen store => khong ung vien; prereg muc 1). Universe chi xet tai gio LEV (E1: gio vao KHONG can universe,
   nhu tang 1 CHOICES 17).
8. E1 (xem CAN MASTER QUYET #A): moc = gio LEV GAN NHAT s trong [t-24, t-1]; ung vien neu z_r(t) <= -2 va KHONG co gio nao trong (s, t) co
   z_r <= -2; diem s = min(z_oi, z_f) tai gio s.
9. Cooldown: vao lai chi khi k - k_vao_truoc > 72 (dung 72 h van chan, nhu tang 1 CHOICES 9); coin dang co vi the thi bo qua.

## Thu tu trong moi buoc gio k (nen k = [T_k - 1h, T_k))
10. (i) voi tung vi the (thu tu chi so coin): thoat trong nen (a) SL -> (b) DCA -> (c) trailing; (ii) funding tai moc T_k cho vi the con mo;
    (iii) time-stop / thieu gia / cuoi ky tai close T_k; (iv) equity MTM; (v) vao lenh moi tai close T_k. Thoat truoc vao => cho trong cung gio
    duoc dung ngay.
11. Size = equity MTM tai close T_k (sau thoat + funding, TRUOC phi vao) x 0.60 / K_max; moi lenh vao trong cung gio dung cung size. Phi vao tru ngay.
12. Funding: vi the nhan ky tai moc b neu vao TRUOC b (vao tai T_k KHONG nhan ky tai T_k - lenh dat sau thanh toan vai ms) va KHONG thoat
    trong nen ket thuc tai b (thoat trong nen => khong nhan ky cuoi nen; thoat tai close => nhan). Notional = qty x close tai b (thieu nen =>
    close cuoi co). Tuong duong cua so (te+1m, tx+1m] cua tang 1 voi thoat time-stop.

## Co che thoat
13. SL: muc = gia vao DAU x (1+SL) ca khi da DCA; open >= muc => thoat tai open (khong cong truot); high >= muc => muc x 1.005.
14. DCA: chi 1 lan; them notional = size0 (USD cua lenh dau) tai p0 x 1.10 KE CA khi open nhay qua (bat loi: short gia thap hon). Tran: (notional cac
    vi the KHAC theo close truoc + qty_hien_tai x p0 x 1.10 + size0) <= 0.60 x equity_now, equity_now = tien mat + lai/lo chua thuc hien cac vi
    the khac theo close truoc + vi the nay danh gia tai p0 x 1.10. Phi 0.07 %. SL cham trong nen => KHONG DCA (thu tu prereg).
15. Trailing: day = LOW thap nhat tu nen sau nen vao (khoi tao +inf); kich hoat khi low nen hien tai <= gia binh quan hien tai x 0.90 (sau DCA cung
    nen neu co); da kich hoat thi giu; muc = day x 1.05 cap nhat SAU khi kiem. Thoat khi high >= muc cua nen truoc, gia = max(open, muc x 1.001)
    (open nhay qua muc => thoat tai open: bat loi; prereg chi noi muc x 1.001).
16. Time-stop: tai close nen k = k_vao + H (sau a-c). Nen do thieu => dong tai close cuoi co ('time_sub', gan co).
17. Thieu gia: dem so nen thieu LIEN TIEP; khi > 24 (nen thieu thu 25) => dong tai close cuoi co ('gap', gan co). Trong gio thieu: khong kiem thoat,
    van cong funding theo close cuoi.
18. Cuoi ky (DEV va moi fold): khong vao lenh o gio cuoi (T = end - 1h); moi vi the mo bi dong tai close gio cuoi ('eod'). Fold doc lap tu 10 000,
    vao lenh chi voi T trong [start, end); trang thai cooldown reset dau fold; moc LEV cua E1 truoc start van dung (thong tin co san).

## Thuoc do (muc 4)
19. ret = equity cuoi / 10 000 - 1. maxDD close = dinh-day tren equity MTM close. maxDD xau-nhat-trong-gio = max(1 - worst_k / dinh close den k-1
    (gom 10 000)), worst_k = equity close k - sum qty x (high_k - close_k) cua vi the mo qua close k (gom vi the time-stop tai k).
20. CAGR theo so gio cua cua so (nam = gio / 8766); Calmar = CAGR / maxDD (bao ca close va worst). Sharpe ngay: equity tai moc 00:00 UTC,
    mean / sd(ddof 1) x sqrt(365). Phoi nhiem = sum qty x close / equity, TB moi gio (khong vi the = 0). Thang = net > 0. Lai rong TB/lenh =
    net / tong notional vao (gom DCA). PnL theo nam = thay doi equity close trong nam lich.
21. Diem muc 5 va Calmar muc 7 dung maxDD XAU-NHAT-TRONG-GIO (prereg chi ghi "maxDD fold" / "Calmar" - chon ban bat loi). San DD 1e-9.

## Luat chon (muc 5) / doi chung (muc 6)
22. Hoa diem: cfg_id tang dan. Hang xom khong can hop le; "loi nhuan > 0 o ca 3 fold" = ret fold > 0. Cao nguyen: frac >= 0.60 qua, < 0.60 loai.
23. Ngau nhien: so ung vien THO (truoc loc vi the/cooldown/top-K) cua cau hinh chon theo thang lich trong DEV; pool = (coin, gio) co universe
    VA gia store trong thang; rut KHONG hoan lai; s ~ U(0,1); cung tap ngau nhien dung cho DEV va 3 fold cua lan rut do; tinh diem cho MOI lan
    (ke ca khong hop le); p_rand = ti le diem >= diem chon (hoa tinh la >=). Seed 20261126, lan r: default_rng([seed, r]).
    Voi cau hinh E1: pool yeu cau universe tai gio vao (E1 that khong yeu cau) - khac biet nho.

## CAN MASTER QUYET (da cai mac dinh, CHUA chay luoi)
A. Dinh nghia E1 "lan dau ke tu dot LEV do": cai = moc la gio LEV GAN NHAT trong 24 h truoc (muc 8). Phuong an khac: moc = gio LEV DAU dot (vd
   dot tach bang cooldown 72 h nhu tang 1) => it ung vien lap hon. Anh huong chua do (khong duoc chay cau hinh E1 that).
B. Tran phoi nhiem 60 % khi VAO LENH MOI: prereg chi gioi han bang K_max (size = 0.60 x equity / K). Cai: KHONG kiem tran khi vao lenh moi (chi kiem
   khi DCA) => sau khi cac short cu bi day len, tong phoi nhiem co the > 60 % (toi da ~ (1+SL) x 60 %). Phuong an khac: bo qua/giam lenh moi neu
   vuot 60 %.
C. Ket thuc fold: cai = dong cuong buc tai gio cuoi fold ('eod'). Phuong an khac: cho vi the chay het H sau end (dung du lieu thang ke tiep trong DEV).
   Anh huong <= 1 dot H gio cuoi moi fold.
D. maxDD dung cho diem muc 5 va Calmar muc 7 = xau-nhat-trong-gio (muc 21). Neu MASTER muon ban close thi chi doi 1 dong trong select.py
   (score_of) - can chot TRUOC khi xem ket qua luoi.
