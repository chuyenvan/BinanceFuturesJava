# HOLD_TO_DIE — 306 lenh time-stop 168h cua X1_C3 (48 thang): neu KHONG cat ma giu tiep?

Script: research/analysis/hold_to_die.py. Counterfactual tren CLOSES_1H.bin (hourly close, khong funding/phi).
CAVEAT: loser 2025H2 bi censor (CLOSES het 2026-01-01) => be90/arm90 nam 2025 la cận DUOI.

```

=== NEU GIU TIEP sau khi bi time-stop (n=306, hourly close):
ngay     ve_BE% cham+7%% MDD_tiep_med
14         38.0     22.8      -33.9
30         45.9     32.0      -43.4
60         51.5     40.9      -49.4
90         56.4     46.2      -53.2
180        61.7     52.8      -64.8

=== DELIST: coin het gia truoc cuoi CLOSES (>30 ngay): 15 / 306 = 4.9%  | >90 ngay: 4.9%
delist trong nhom loser sau nhat (p10, profit<=-46.7): 9.7%

=== theo do sau lo luc cat:
           n  be30  be90  arm90  mdd90  delist
bin                                           
<-50      26   4.2   8.3    4.2  -79.6    11.5
-50..-30  42  16.7  23.8   21.4  -65.2     2.4
-30..-20  64  31.2  51.6   42.2  -58.5     3.1
-20..-10  93  53.8  66.7   50.5  -46.8     6.5
-10..0    70  72.5  76.8   68.1  -38.7     2.9

=== theo nam:
        n  meanP  be90  arm90  delist
yr                                   
2022   59  -22.9  64.3   50.0    11.9
2023   35  -13.2  71.4   57.1    11.4
2024   94  -15.5  62.8   51.1     4.3
2025  118  -28.9  43.2   37.3     0.0
```
