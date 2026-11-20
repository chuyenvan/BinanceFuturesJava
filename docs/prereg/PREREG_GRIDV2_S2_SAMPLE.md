# PREREG_GRIDV2_S2_SAMPLE - chot danh sach mau TRUOC khi tai bat ky aggTrades nao (2026-11-21) - buoc (2) muc 13 PREREG_GRIDV2_S2.md
Prereg: docs/prereg/PREREG_GRIDV2_S2.md (commit 56eddec8). Giai doan 1 (v12/GRIDV2_S2_RUN_STAGE1.md): 5 kernel su kien
chuyendinh/gridv2-s2-events0..4 (code S1 ghim), validate all_pass 5/5, E1a ok, E1b max_abs_diff 2,9e-11 so voi run2 cua S1.
Su kien COND_A c0.2 k2: 268 356 don vi (134 178 su kien x 2 ben), 70 432 cum (sym, ngay); nua A 97 324 don vi / 26 461 cum; nua B 171 032 / 43 971.
Lay mau theo LUAT prereg (sample.py nguyen trang, SE muc tieu 4,5 bps): f nua A = 0,125, f nua B = 0,075; 6 604 cum duoc chon
(A 3 307, B 3 297), 153 cum audit; SE du doan (K_OPT / K_PESS) nua A 3,16 / 4,46, nua B 3,78 / 4,45. HEAD: 7 950 file, 28,35 GB zip,
7950/7950 HTTP 200; tran 150 GB khong bi ap.
MOC W1 (bat buoc cho run_s2 --sample-sha):
  5bb7b139a3dcf2f3d1f208609ca5dd7a84805ee717f23428777ae26802d95ad5  sample.csv  (70 432 dong: cum duoc chon + danh sach du phong theo rank)
  e200235786d8336927df1db08d7cfadf8affb11d1fa9b996175828fcbb10ec15  sample_manifest.json
  bff0782093b9fccda3d7e675e8da12e0534a2304a792a1d6be2016342736b59a  head.json
  5653cae418130475254fe6b66e83aaac3daa96b8ae245ffe553be16490801bc7  precheck.json
Ban sao: docs/result/gridv2_s2/sample.csv.gz (gunzip ra dung sha tren), sample_manifest.json, precheck.json.
Tai thoi diem commit nay CHUA co byte aggTrades nao duoc tai (chi HTTP HEAD lay kich thuoc). Khong doi mau sau commit.
