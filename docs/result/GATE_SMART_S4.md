# GATE_SMART Pha 0b — S4 (prereg 6d92cdba §2.3–2.5) — 2026-11-10: S4 = FALSE

- Kernel `chuyendinh/gsm-s4-fwd` (code `research/gate_smart/s4k.py` blob ebbd5b99, commit 2fa10cc3; push lần 1 11-09 15:20Z kẹt queued ~12 h chưa chạy, push lại 11-10 03:32Z cùng code/input). Input dataset `gsm-s4-cells` (sha256 efe56688): near 18 981 / pass_low 3 273 ô (ts, sym) gộp 8 seed (n_seed).
- Chấm `research/gate_smart/s4score.py`: ret = close(t+1′+H)/close(t+1′) − 1 − 0,2 %; gộp 8 seed trọng số n_seed; CI90 bootstrap cụm NGÀY (+07), 2 000 lần, seed RNG 20261110. nan0 = 0, nan72 = 139 (0,6 %, bỏ). Raw `docs/result/gate_smart_s4.json`.

| H | near (n) | mean [CI90] | pass_low (n) | mean [CI90] | near − pass_low [CI90] |
|---|---|---|---|---|---|
| 24h | 18 938 | 2,59 % [0,14; 4,94] | 3 271 | 3,54 % [1,73; 5,41] | −0,95 pp [−2,37; +0,39] |
| 72h | 18 849 | 3,83 % [1,82; 5,85] | 3 266 | 4,83 % [2,67; 7,04] | −1,00 pp [−2,75; +0,70] |

Trung vị 72h: near 1,55 % / pass_low 1,56 %.
**S4 FALSE** (near-miss không tốt hơn pass [1;1,1); CI chứa 0, ước lượng điểm nghiêng về pass). Cùng S1/S2/S3/S5 FALSE ⇒ theo §2.5: **ĐÓNG GATE_SMART**, không chạy Pha 1 (EWQ/VOLN/SEP/BX24). Hệ quả R3: arm G5 TIER-DOWN bị loại trước Pha 1.
Giới hạn: fwd return không có exit/DCA (chỉ mô tả, đúng prereg); ô trùng thời điểm giữa 2 nhóm cùng ngày ⇒ CI theo cụm ngày.
