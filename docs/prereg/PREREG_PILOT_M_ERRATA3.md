# PREREG_PILOT_M_ERRATA3 - 3 diem lam ro truoc lan cham D = 2026-11-26 (va truoc time-stop dau tien 28/11)
Commit boi MASTER 2026-11-26 12:09 +0700. Ap cho PREREG_PILOT_M 2a21fe35 + ERRATA1 c0f35f3c + ERRATA2 efc4f9c1, tu ngay cham D = 2026-11-26.
Da cham truoc errata nay: D = 2026-11-24 va D = 2026-11-25 (deu XANH, khong su kien nao thuoc 3 diem duoi day: khong TIME-STOP, khong dong TOM
TAT co latch rong bi tinh vi pham, khong co 2 cum cung symbol dong gan nhau) => khong cham lai. Nguon: audit cong cu A1_PILOT_M_TOOL_V2 (m1-m3),
phat hien bang ca pha tong hop, khong tu du lieu sau moc.
Bao cao ngay ghi 'prereg=2a21fe35+E1+E2+E3'.

H1 (M-T, bo sung ERRATA1 E7): dong "[C3-LIVE-TRAIL] TIME-STOP <SYM>" hoac dong CLOS ly do TIME_STOP_168H cua mot cum DANG co pha arm hieu luc
   (dong ARM cuoi cua cum khong co dong RST sau no, tinh toi thoi diem dong do) => VI_PHAM M-T (bac DO nhu moi VI_PHAM M-T). Co che: cum co pha
   arm chi thoat bang trailing (TrailingStopManager :207-231); time-stop mot cum dang arm la sai logic.
H2 (K2, lam ro ERRATA1 E2 (b)): cum tu "(khi truong khong rong)" ap cho CA BA truong latch, khan, jar. Truong rong (luot monitor doc 242 hong)
   khong sinh VI_PHAM; chi dem vao so_luot_doc_hong.
H3 (I10, lam ro ERRATA1 E6): ghep BOOK / CLOS / SFIL theo CUM (symbol + lan mo cum), khong theo symbol. Hai cum lien tiep cua cung symbol dong
   cach nhau < 600 s la HOP LE neu moi cum co dung 1 CLOS + 1 BOOK cua chinh no. Dong BOOK / CLOS khong gan duoc vao cum nao dang mo ("mo coi")
   => VI_PHAM I10.
