# GRIDV2_S2_RUN_STAGE1 - giai doan 1/2 (kernel su kien + HEAD + lay mau). DUNG TRUOC fetch. 2026-11-21 (ASCII)
Dir: ~/claude_master/w3/gridv2/s2run/ (kern/ ev/ evflat/ precheck_out/ smp/ head.json headout/ head_wrap.py)
1. Tuan thu: EXPECTED_SHA b852e849... khop; 9 file S2 + 4 file S1 khop. 7 dataset dung allowlist, internet false, private. 5 kernel
   chuyendinh/gridv2-s2-events0..4, push 1 lan moi, 0 lan chay lai. Kernel ~1698-1900 s. validate_s0..4 all_pass True, E1a ok (max_abs 0).
   precheck (W0_events + E1b vs run2): ok True, E1b max_abs_diff 2.9e-11. Cach lam them: wrapper head_wrap.py (throttle 12 rps + retry) goi
   fetch_reduce.main(head-only) - khong sua code ghim.
2. Su kien: 268356 don vi (= 134178 su kien x BUY/SELL), 70432 cum (sym,ngay). Nua A 97324 don vi/26461 cum; nua B 171032/43971.
   Theo tang (units/cum N): 2021H2 T1 902/276 T2 5848/1577 T3 8508/2232; 2022 T1 2194/579 T2 10088/2898 T3 15776/4371;
   2023 T1 2754/824 T2 14518/4055 T3 36736/9649; 2024 T1 2628/734 T2 12104/3279 T3 60116/14723; 2025 T1 2072/684 T2 8960/2696 T3 85152/21855.
3. Mau: f A 0,125 ; f B 0,075 (luat SE_TARGET 4,5). Cum chon 6604 (A 3307, B 3297), audit 153 cum. SE du doan (K_OPT/K_PESS):
   A 3,16/4,46 ; B 3,78/4,45. 7950 file, 28,35 GB zip (2021 3,35; 2022 4,43; 2023 5,64; 2024 7,72; 2025 7,21), cap 150 GB KHONG ap.
   Tai uoc ~20-40 phut + doc CSV ~1-1,5 h.
4. sha256: sample.csv 5bb7b139a3dcf2f3d1f208609ca5dd7a84805ee717f23428777ae26802d95ad5 (chua ca du phong: selected=0 + rank; 70432 dong)
   smp/sample_manifest.json e200235786d8336927df1db08d7cfadf8affb11d1fa9b996175828fcbb10ec15 ; head.json bff0782093b9fccda3d7e675e8da12e0534a2304a792a1d6be2016342736b59a
5. HEAD: 7950/7950 status 200, 0 thieu, 0 retry.
6. Dia: 18 GB trong (/ 91%).
