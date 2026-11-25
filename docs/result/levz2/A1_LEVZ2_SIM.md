# A1_LEVZ2_SIM - audit doc lap simulator LEVZ2 (truoc luoi 1 296). Agent A1 (Opus), 2026-11-25. Khong sua code DEV, khong commit.
Doi chieu: PREREG_LEVZ2 @278725ae + ADDENDUM1 @f6157c87 + CHOICES2.md. Artefact: a1/ (s1s2.py, refsim.py, cmp.py, brk.py, rstat.py, out/*).
Luu y: a1/out/ref_*.json|parquet, refeq_*.npz chua PnL cua 4 cau hinh audit - chi de doi chieu, KHONG doc/bao cao.

## VERDICT: FAIL co dieu kien (chua duoc chay chuoi grid && select && rand nhu README)
Loi sim.py/grid.py/select.py: KHONG tim thay loi ke toan / look-ahead / thu tu (tinh lai doc lap khop 1e-15). Nhung:
- rand.py sai ve thiet ke dem ung vien (B1) => doi chung muc 6 khong so sanh duoc => BAT BUOC sua truoc khi chay rand.
- 1 diem dien giai prereg (B2: SL va DCA cung nen) DEV chon cach LAC QUAN, trai nguyen tac "bat loi hon" cua chinh CHOICES2
  => MASTER phai chot (ADDENDUM2) TRUOC khi chay luoi vi doi ket qua luoi.
Sau khi chot B2 (+ sua neu chon phuong an bao thu, them test) va sua B1: duoc chay luoi, khong can audit lai toan bo (chi diff + test).

## BAT BUOC truoc khi chay
B1. code/rand.py:271-280 (build_pools: cnt = so (k,c) ung vien THO theo thang). Ung vien that dong cum: E0 LEV keo dai nhieu gio lien
    tiep cung coin (cooldown 72 h + top-K chi cho vao gio dau). Do bang rstat.py (khong chay sim): W14 E0 z2.5 DEV: 5 391 gio ung vien
    tho = 632 "dot" (dedupe 72 h/coin) tren 274 coin; mot lan rut ngau nhien cung 5 391 gio => 4 284 dot (x6.8). W7 E0 z2.5: 755 vs 3 962
    (x5.2); W14 E0 z3.5: 181 vs 982 (x5.4); E1: x1.4-1.7. => lan ngau nhien luon day K, so lenh va phoi nhiem gap nhieu lan cau hinh that
    => p_rand do "nhieu lenh hon" chu khong do tin hieu. Sua: dem theo DOT (lan dau moi coin sau dedupe 72 h tren tap ung vien tho cua cau
    hinh chon), rut ngau nhien dung so dot moi thang tu pool universe+gia (pool 4.65 trieu coin-gio nen trung lap ~0); s ~ U(0,1).
    Cau ADDENDUM2 de xuat: "Muc 6: 'so ung vien that cua thang' = so DOT ung vien (gio dau tien cua moi coin sau khi gop cac gio ung vien
    cach nhau <= 72 h) cua cau hinh chon trong thang; ngau nhien rut dung so do (coin, gio) tu universe co gia cua thang."
B2. code/sim.py:275-299 (CHOICES2 #14 'SL cham trong nen => KHONG DCA'). Muc stop >= p0 x 1,15 > muc DCA p0 x 1,10: trong nen co high >=
    stop ma open < p0 x 1,10, gia PHAI di qua muc DCA truoc => thuc te lenh DCA khop roi bi SL voi khoi luong gap doi (neu tran cho phep).
    DEV bo DCA => lo SL bi giam mot nua o dung ca xau nhat. Do tren du lieu that (c2 = W14 E1 z3.0 K3 SL15 H72 trail+DCA, fold 2024):
    10/30 lenh SL roi vao truong hop nay (chua tru truong hop tran 60 % chan). Uu ai co he thong cho to hop SL15 + DCA.
    Prereg doc duoc 2 cach ("chua cham SL"); nguyen tac CHOICES2 "chon cach bat loi hon" => phai la DCA truoc.
    Cau ADDENDUM2 de xuat: "Trong mot nen, neu chua DCA va open < p0 x 1,10 <= high: DCA khop tai p0 x 1,10 (neu tran 60 % cho phep) TRUOC,
    roi moi kiem SL tren khoi luong moi; open >= muc stop => thoat toan bo tai open, khong DCA." (sua ~6 dong: dua khoi DCA len truoc
    kiem 'h >= stop', giu kiem gap open truoc). Neu MASTER giu ban literal: ghi ro day la gia dinh LAC QUAN.

## MINOR (khong chan, nen ghi vao ADDENDUM2 / sua re)
M1. sim.py:280-309 DCA roi trailing cung nen: trail da kich hoat (muc <= 0,945 x gia BQ) ma nen bat len >= p0 x 1,10: DEV khop DCA o 1,10
    roi thoat trail o muc x 1,001 => lai "ao" tren chan DCA (test brk t_dca_then_trail_same_bar). Thuc te gia cham muc trail truoc, khong
    DCA. Tan suat that: 0 lan o c2 2024. De xuat: "trail da kich hoat va high >= muc => thoat trail, bo qua DCA nen do".
M2. CHOICES2 #15 trailing gap: thoat tai max(open, muc x 1,001) - lech chu prereg ("muc x 1,001") theo huong BAO THU. Can 1 dong ADDENDUM.
M3. CHOICES2 #9 cooldown: dung 72 h van chan (vao lai tu 73 h) - nhu tang 1; prereg khong noi bien. 1 dong ADDENDUM.
M4. DCA gan nhu tro (he qua ADDENDUM B): voi K3, DCA chi qua tran khi <= 1 vi the khac dang mo; c4 (K3) 2024: 10 DCA khop / 481 lan-nen
    bi tran chan; c2: 9 / 100. K10 gan nhu khong bao gio. Khong phai bug - can biet khi doc anh huong bien cua tham so DCA.
M5. Gia vao = close nen gio = dung gia dung trong z_r (do tre 0). Tang 1 vao sau 1 phut. Dung chu prereg "close gio t"; lech gia vao
    median 0,16 % (smoke). Ghi nhan, khong sua.
M6. grid.py:74 assert acct_err chi DEV/F1; nen them F2/F3. rand.py: E1 pool doi universe tai gio vao, E1 that khong doi: do duoc chi
    0-0,36 % ung vien E1 that nam ngoai universe => thien lech khong dang ke; de nguyen hoac bo dieu kien U cho pool E1 (khong can).
M7. CHOICES2 #12 funding: vao tai T khong nhan ky T, thoat tai close T nhan ky T (doi xung, moi moc dem 1 lan) - hop ly, giu.
M8. Guard sys.path cho select.py: tren Oracle python3 'select' la module BUILTIN (import select khong guard van ra builtin) => khong the
    bi che; grid/rand dung fork (khong re-import) => khong rui ro. Guard vo hai.

## Ket qua kiem (code/test, khong phai suy doan)
- sha256: 9/9 OK theo SHA256SUMS.txt; w3/levz FREEZE.txt 7/7 OK. out/grid.parquet khong ton tai.
- S1 (chay lai, tu dung bang dense tu sig_W*.parquet + levz.episodes/e1_entry dong bang): W14 A1 634/634, A2 462/462; W7 A3 757/757,
  A4 536/536 - 100 %, 0 le.
- S2 (reader .bin rieng cua A1): store t == panel h + 1h: 4 744 683/4 744 733 = 99,999 % lech <= 1e-3 trong universe (coverage 99,09 %). PASS.
- Look-ahead tin hieu: tinh lai levz.signals voi du lieu cat tai 2023-06 so bang day du: 1 466 664 dong x {z_oi,z_f,f,z_r,u} W14 va W7:
  0 lech. Can gio: tin hieu tai T dung OI <= T-10m, funding <= T-1m, z_r tu close nen ket thuc tai T; gia vao = close store ket thuc tai T.
- Look-ahead sim tren du lieu THAT (2024-01..03, 4 cau hinh x 3 moc cat): hoan vi + nhan nhieu OHLC sau t, funding ngau nhien, thay ung vien
  sau t => lenh dong truoc t, tap lenh vao truoc t, equity va equity-xau-nhat den t TRUNG TUYET DOI: 12/12.
- Tinh lai doc lap (refsim.py: vong lap python thuan, tu doc .bin, tu tinh ung vien E0/E1 tu sig parquet, funding lake, KHONG import levz2):
  fold 2024: c1 smoke (W14 E0 z2.5 K10 SL50 H24) 320 lenh; c2 (W14 E1 z3.0 K3 SL15 H72 trail DCA) 81; c3 (W7 E0 z3.5 K5 SL30 H168 trail) 71;
  c4 (W14 E0 z2.5 K3 SL30 H72 DCA) 99; + c1 toan DEV 584. Ca 5: trung 100 % (sym, gio vao, gio ra, ly do, co DCA); PnL lenh lech toi da
  2e-15 x notional; equity cuoi lech tuong doi <= 3e-15; duong equity close va xau-nhat-trong-gio lech <= 3e-15; maxDD lech <= 3e-15.
  Ti le ly do thoat (2024): c1 time 97,8 % / SL 1,6 % / eod 0,6 %; c2 SL 37 % / trail 37 % / time 26 % (9 DCA); c3 trail 69 % / time 17 % /
  SL 14 %; c4 time 87 % / SL 11 % / eod 2 % (10 DCA). Bat bien ke toan |sum PnL - (equity cuoi - 10 000)| <= 4e-11 ca hai ben.
- grid.py: 1 296 cau hinh, khong trung, gia tri dung muc 3; resume bang part file ghi .tmp + os.replace, gop drop_duplicates, assert 1 296;
  Pool(3) fork; moi cau hinh du thuoc do muc 4 cho DEV + F1/F2/F3 (n, win, mean_ret, worst_ret, cagr, maxdd close + worst, calmar 2 ban,
  sharpe_d, expo_mean, x_<ly do>, fund_total, pnl_<nam>).
- select.py (luoi gia 1 296, brk t_select_cases 11/11): hang 1 truot cao nguyen -> chon hang 2; khong hop le -> None; hoa diem -> cfg_id nho;
  60 % dung bien qua, 50 % truot; 29 lenh/fold -> khong hop le; DD 0,30 hop le, 0,3000001 khong; ret = 0 khong hop le; so hang xom 8..12 chi
  gia tri ke; maximin = MIN. maxDD = 0 -> san 1e-9 (diem rat lon) - thuc te khong xay ra (phi vao luon tao DD > 0 khi co >= 1 lenh).
- rand.py: dung seed/so lan/rut khong hoan lai/s U(0,1)/cung tap cho DEV + 3 fold/p_rand = ti le >= ; SAI dinh nghia so ung vien (B1).
- Test DEV: 46/46 PASS (chay ban sao chi doi duong dan ghi report sang a1/out).
- Ca pha cua A1 (brk.py, tong hop, tinh tay): 17/17 PASS: SL+DCA cung nen (literal), trailing kich hoat va cham cung nen (khong thoat nen do),
  gap qua ca DCA lan SL (SL tai open, khong DCA), hai ung vien cung s (sym nho), K day roi trong giua gio (vao ngay, size theo equity sau
  thoat), funding o gio vao (khong) / gio ra time-stop (co) / thoat trong nen (khong), equity am (khong vao tiep, CAGR -1, khong loi),
  thieu gia 23 h roi co lai (tiep tuc), thieu 25 h (dong 'gap' tai close cuoi), lenh qua bien fold (eod; fold sau khong ro cooldown;
  DEV run giu lenh), cooldown bien 72/73, DCA roi trail cung nen (ghi nhan M1), equity xau-nhat-trong-gio, E1 (bien 24 h, z_r o gio LEV),
  select 11 ca, rand pool.

## Thoi gian / RAM (do 20 cau hinh that, run_all = DEV+F1+F2+F3, khong in loi nhuan)
0,11 s/cau hinh TB (median 0,09; max 0,25 o K10 H168 trail DCA); nap inputs 0,8 s; RSS dinh 1,0 GB/tien trinh.
Luoi 1 296: ~145 s CPU => ~1 phut voi 3 tien trinh. rand 500 lan: ung vien ngau nhien day K hon => uoc 0,2-0,5 s/lan => 1-2 phut.
RAM dinh uoc 1-3 GB (3 con fork chia se mang COW). Dia trong 21 GB.

## Khong kiem duoc / gioi han
- Thu tu that trong nen gio va truot thuc te (gia dinh prereg). Gia mark cho funding (dung close).
- refsim dung cung quy uoc CHOICES2 o cho prereg im lang (funding vao/ra, tran DCA, cooldown 72, thieu gia) => khop chung minh code dung
  QUY UOC, khong chung minh quy uoc dung (danh gia rieng o B2/M1-M3).
- rand.py chua chay end-to-end tren du lieu that (khong duoc phep); chi kiem ham + thong ke tap ung vien.
