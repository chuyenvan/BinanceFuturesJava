> ⚠️ **TRANG THAI: DONG TAM 2026-09-16** — user chot trong chat: "đóng tạm gd92 lại".
>
> **Ly do dong tam** (theo `docs/audit/AUDIT_GATEDYN_GD92.md`): audit doc lap ket luan
> **KHONG PHAN BIET DUOC (nhieu)** o tang hieu qua (CI95 chenh lech CAGR chua so 0, UW 116 vs
> nguong 120 chi lech 4 ngay, be mat tham so gap ghenh), va dot GATEDYN2 **vi pham phuong phap**
> (mo 6 bien the quanh diem thang tren cung khong gian — bi cam ten trong `docs/result/B4_RESULT.md`
> dong 179-180). ⇒ **KHONG chot GD92 vao san xuat**. Profile `x1_c3_full.properties` van **KHONG**
> co key `SIM_GATE_ROLLING_*` (san xuat giu nguyen gate cung).
>
> **Dieu duy nhat audit cong nhan**: muc tieu "phan bo lenh deu hon giua cac quy" **DAT THAT**
> (CV quy 0.712 -> 0.518), so lieu tai lap byte-identical.
>
> **Code GD92 da bi xoa o commit `f1c43a3`**; lay lai duoc bang `git show f1c43a3^:<path>`:
> - `src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/GateRollingThreshold.java`
> - `profiles/x1_gd92.properties` + 6 file `profiles/x1_gd2_*.properties` (`G90W120/G90W60/G92W120/G92W60/G94W120/G94W60`)
>
> **Neu can lam lai**: phai pre-reg MOI + du lieu NGOAI MAU (khong duoc tai su dung DEV 48 thang
> da lam nhieu GD92). Xem chi tiet o muc 3 phia duoi.

---

# GD92 — GATE p15 ĐỘNG THEO PHÂN VỊ TRƯỢT — CODE + KẾT QUẢ + AUDIT

File tổng hợp, tạo 2026-09-15. Nguồn: repo `BinanceFuturesJava` branch `module`.

## ⚠️ ĐỌC TRƯỚC — 3 trạng thái quan trọng
1. **Code GD92 KHÔNG còn trong working tree**: `GateRollingThreshold.java` + các profile
   `x1_gd92/x1_gd2_*.properties` đã bị XÓA ở commit `f1c43a3` (12/09, refactor gate về class
   `EntryGate`, xóa "cờ trỏ" vì nhánh B4 đóng). Code vẫn lấy lại được từ git — xem mục 4.
2. **Audit độc lập `docs/audit/AUDIT_GATEDYN_GD92.md` (11/09) đã bác claim "GD92 THẮNG"** mà em (OpenClaw)
   từng báo. Phán quyết: **KHÔNG PHÂN BIỆT ĐƯỢC (nhiễu)** ở tầng hiệu quả + GATEDYN2 **vi phạm
   phương pháp**. Chi tiết đầy đủ ở mục 3 — đọc kèm trước khi dùng số.
3. Việc **độ đều phân bổ lệnh** (mục tiêu gốc của user) là **THẬT và tái lập được**
   (CV quý 0.712 → 0.518). Audit công nhận điểm này + công nhận tái lập byte-identical.

---

## 1. CODE

### 1.1 Cơ chế — `GateRollingThreshold.java` (149 dòng, lấy từ `$DELCOMMIT^`)
Thay ngưỡng CỨNG `MIN_MOMENTUM_15M` (0.008) bằng **percentile trượt**: ngưỡng(t) = phân vị `pct`
của `predReturn15M` trong cửa sổ NỬA MỞ `[t-W, t)` — chỉ dữ liệu QUÁ KHỨ (không leak). Mẫu lấy
trên lưới 15 phút; bảng `giờ → ngưỡng` tính sẵn lúc init, cập nhật mỗi giờ, truy vấn `floorEntry`.
Đầu kỳ: mốc phải đủ cửa sổ W; mốc < 96*7 mẫu thì bỏ; trước mốc đầu → fallback 0.008 + WARN.
Chỉ đổi NGƯỠNG CƠ SỞ; phần nhân hệ số theo `symbolPred` giữ nguyên.

```java
package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;

/**
 * NGUONG GATE TRUOT THEO PHAN VI — nhanh B4, cai lai 2026-09-03.
 *
 * <p>Ban goc viet 2026-09-02, bi xoa o commit {@code 5f40a90} (DOT 2 xoa co tro) vi luc do B4 da
 * bi dong. Nhanh mo lai theo {@code docs/audit/CI_REAUDIT.md} HE QUA (ii): ca 3 hieu RG vs C2b nam TRONG
 * CI va maxDD ca 3 khong te hon C2b => cau "EV am" khong duoc du lieu ho tro. Co che va 3 bien the
 * duoc chot TRUOC o {@code docs/prereg/PREREG_B4.md} (commit a0c7ad6).
 *
 * <p>Van de do duoc: mean predReturn15M troi tu 0.0036 (2023Q3) len 0.0091 (2025Q4) — gap 2.5 lan.
 * Nguong CO DINH 0.008 lam ty le thoi gian gate mo dao dong manh giua cac quy. Do la phi-dung cua
 * model gate, khong phai tin hieu thi truong.
 *
 * <p>Co che (PREREG_B4 section 1.2): nguong tai thoi diem t = phan vi p cua predReturn15M trong cua
 * so NUA MO [t - W, t) — CHI dung du lieu TRUOC t (nhan qua, khong nhin truoc). Mau lay tren luoi
 * 15 phut. Bang {@code gio -> nguong} tinh san MOT LAN luc init, cap nhat moi GIO wall-clock, truy
 * van bang {@code floorEntry}. Phan vi khong noi suy: k = min(m-1, max(0, floor(p*(m-1)))).
 * Dau ky: moc dau tien phai co DU cua so W, va moc nao co m &lt; 96*7 mau thi bo; truy van truoc moc
 * dau tien tra ve {@code Configs.MIN_MOMENTUM_15M} (hanh vi cu) va LOG.warn MOT lan.
 *
 * <p>Chi thay nguong CO SO cua gate MOM15; phan nhan he so theo score trong
 * {@link AIRejectFilter#checkSignalDynamic} KHONG doi.
 *
 * <p>Tham so di qua cong {@link Cfg} (khai trong profile, KHONG doc System.getenv):
 * {@code SIM_GATE_ROLLING_PCT} (0..1, vd 0.95; khong khai bao / rong / ngoai (0,1) = TAT =&gt; hanh vi
 * byte-identical voi C2b), {@code SIM_GATE_ROLLING_DAYS} (mac dinh 90).
 */
public final class GateRollingThreshold {
    private static final Logger LOG = LoggerFactory.getLogger(GateRollingThreshold.class);
    private static final long HOUR = 3600_000L;
    private static final long GRID = 15 * 60_000L;   // lay mau pred moi 15 phut cho cua so
    private static final int MIN_SAMPLES = 96 * 7;   // < 7 ngay du lieu trong cua so -> bo moc gio

    private static float pct = -1f;
    private static int days = 90;
    private static TreeMap<Long, Float> hour2thr = null;
    private static long nQuery = 0, nBeforeFirst = 0;
    private static boolean warnedBeforeFirst = false;

    private GateRollingThreshold() {}

    public static boolean isOn() {
        return hour2thr != null && pct > 0f;
    }

    /** Doc cau hinh va tinh san bang nguong theo gio. Goi 1 lan sau khi co predictionMap. TAT -> no-op. */
    public static synchronized void init(TreeMap<Long, AiPredictionData> predictionMap) {
        hour2thr = null;
        nQuery = 0;
        nBeforeFirst = 0;
        warnedBeforeFirst = false;
        String v = Cfg.get("SIM_GATE_ROLLING_PCT");
        if (v == null || v.isBlank()) return;
        pct = Float.parseFloat(v.trim());
        if (pct <= 0f || pct >= 1f) {
            LOG.warn("[GATE-ROLL] SIM_GATE_ROLLING_PCT={} ngoai (0,1) -> TAT", pct);
            return;
        }
        String d = Cfg.get("SIM_GATE_ROLLING_DAYS");
        if (d != null && !d.isBlank()) days = Integer.parseInt(d.trim());
        if (predictionMap == null || predictionMap.isEmpty()) {
            LOG.warn("[GATE-ROLL] predictionMap rong -> TAT");
            return;
        }

        long t0 = System.currentTimeMillis();
        // 1) chuoi pred tren luoi 15m (TreeMap => da sap xep theo ts)
        int n = 0;
        for (Map.Entry<Long, AiPredictionData> e : predictionMap.entrySet()) if (e.getKey() % GRID == 0) n++;
        if (n < MIN_SAMPLES) {
            LOG.warn("[GATE-ROLL] chi co {} mau tren luoi 15m (< {}) -> TAT", n, MIN_SAMPLES);
            return;
        }
        long[] ts = new long[n];
        float[] val = new float[n];
        int i = 0;
        for (Map.Entry<Long, AiPredictionData> e : predictionMap.entrySet()) {
            if (e.getKey() % GRID != 0) continue;
            ts[i] = e.getKey();
            val[i] = e.getValue().predReturn15M;
            i++;
        }
        // 2) moi gio h: phan vi cua val[ts in [h - W, h)]
        long w = (long) days * 24 * HOUR;
        long hStart = ((ts[0] + w) / HOUR + 1) * HOUR;      // gio tron dau tien co DU cua so
        long hEnd = ts[n - 1];
        TreeMap<Long, Float> out = new TreeMap<>();
        int lo = 0, hi = 0;
        float[] buf = new float[n];
        for (long h = hStart; h <= hEnd; h += HOUR) {
            while (lo < n && ts[lo] < h - w) lo++;
            while (hi < n && ts[hi] < h) hi++;
            int m = hi - lo;
            if (m < MIN_SAMPLES) continue;
            System.arraycopy(val, lo, buf, 0, m);
            Arrays.sort(buf, 0, m);
            int k = Math.min(m - 1, Math.max(0, (int) Math.floor(pct * (m - 1))));
            out.put(h, buf[k]);
        }
        if (out.isEmpty()) {
            LOG.warn("[GATE-ROLL] khong sinh duoc moc gio nao (pct={} window={}d) -> TAT", pct, days);
            return;
        }
        hour2thr = out;
        float mn = Float.MAX_VALUE, mx = -Float.MAX_VALUE;
        for (float f : out.values()) {
            mn = Math.min(mn, f);
            mx = Math.max(mx, f);
        }
        LOG.warn("*** [GATE-ROLL] BAT: pct={} window={}d | {} moc gio | moc dau {} | nguong min={} max={} | tinh {} ms ***",
                pct, days, out.size(), out.firstKey(), String.format("%.5f", mn), String.format("%.5f", mx),
                System.currentTimeMillis() - t0);
    }

    /** Nguong tai thoi diem t (dung bang cua GIO &lt;= t). Truoc moc dau tien -> Configs.MIN_MOMENTUM_15M. */
    public static float threshold(long t) {
        nQuery++;
        Map.Entry<Long, Float> e = hour2thr.floorEntry(t);
        if (e == null) {
            nBeforeFirst++;
            if (!warnedBeforeFirst) {
                warnedBeforeFirst = true;
                LOG.warn("[GATE-ROLL] truy van t={} TRUOC moc gio dau tien {} -> fallback hang so MIN_MOMENTUM_15M={}",
                        t, hour2thr.firstKey(), Configs.MIN_MOMENTUM_15M);
            }
            return Configs.MIN_MOMENTUM_15M;
        }
        return e.getValue();
    }

    /** Thong ke cho log cuoi run (PREREG_B4 section 1.2 muc 5: bao cao phai in nBeforeFirst). */
    public static String stats() {
        return isOn()
                ? String.format("GATE-ROLL pct=%.2f days=%d moc=%d query=%d beforeFirst=%d",
                        pct, days, hour2thr.size(), nQuery, nBeforeFirst)
                : "GATE-ROLL off";
    }
}
```

### 1.2 Điểm nối (wiring) — theo code thời điểm đó
- `AIRejectFilter.thres15M(pred)`: `GateRollingThreshold.isOn() ? threshold(ts) : Configs.MIN_MOMENTUM_15M`
- `checkSignalDynamic`: `dyn_thr = thres15M(pred) * max(0.26787, symbolPred/0.15 * 1.28760)`
- `SimulatorMarketLevelTicker1MStopLoss:632,1068`: `GateRollingThreshold.init(predictionMap)`

### 1.3 Profile GD92 — `profiles/x1_gd92.properties` (từ git)
```properties
# ============================================================================
# PROFILE GIAO DICH — C3 (BASELINE MOI): c2b_min + 3 fix B1/B2/B3 BAT
# Sinh tu profiles/c2b_min.properties (KHONG sua tay 16 key goc), them 3 co FIX_B*.
# Xem docs/prereg/PREREG_C3.md + docs/experiment/C3_BASELINE.md.
# ============================================================================


# --- SELECTOR: chon coin trong tick ---
SELECTOR_RANK_TOPK=8
SELECTOR_ONLY_ENTRY=0

# --- BINS SELECTOR (PIN 2026-09-03) ---
# Day la BIEN QUYET DINH cua S1: +7.35pp CAGR va maxDD -13.12 vs -20.82 so voi bins G015 o
# CUNG thang exit cua profile nay (C2_g015 b:51903 vs C2a b:59471). SELECTOR_RANK_TOPK /
# SELECTOR_ONLY_ENTRY KHONG lam nen S1 - hai key do giong y nguyen o run C2_g015.
# Truoc 2026-09-03 key nay o Cfg.INFRA_KEYS (dat tuy y qua env, khong pin) va thieu no thi
# WfoDataset chi LOG.warn roi fallback Aerospike => ra so KHAC ma khong bao loi.
# Nay: thieu / tro sai => ExportWfoDataset THROW (fail cung).
# sha256 tung file bins: research/pipeline/BINS_MANIFEST.md muc 2.
# Sao luu ngoai may: Kaggle dataset PRIVATE chuyendinh/predwf-map-s1a2-bins version 1.
WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1

# --- GATE: dieu kien thi truong de duoc vao lenh ---
# Nguong THUC TE (gate tang 2 = AIRejectFilter.checkSignalDynamic):
#   dyn_thr = SIM_MIN_MOMENTUM_15M * max(SIM_AI_DYNAMIC_MIN, score/0.15*SIM_AI_DYNAMIC_MULTIPLIER)
#   <-- CHI CO CAN DUOI. Nhanh Math.min(..., AI_DYNAMIC_MAX) da bi xoa khoi code.
#   => nguong TANG DON DIEU theo score, KHONG phai hang so: 0.214 phan tram o san
#      den 2.206 phan tram o score 0.3212.
#   AI_DYNAMIC_MAX la tran UNG VIEN o gate tang 1, ma tang 1 BI BO QUA khi SELECTOR_RANK_TOPK>0.
# DINH CHINH 2026-09-03: ban cu o day ghi clamp co ca can tren => nguong hang 1.713 phan tram.
#   Do la SAI. Xem docs/design/C2B_SPEC.md muc 0.
SIM_MIN_MOMENTUM_15M=0.008
SIM_GATE_ROLLING_PCT=0.92
SIM_GATE_ROLLING_DAYS=90

# --- EXIT: arm + trailing + cat lo ---
SIM_RATE_PROFIT_STOP_MARKET=0.07
SIM_TS_GIVEBACK=1
SIM_LOSER_TIME_STOP_HOURS=168
# 2026-09-03 (B3): 3 tham so exit duoi day TRUOC DAY VO HINH — khong co trong file cau hinh nao,
# chi ton tai lam default hardcode trong Java. Nay ghi ro bang dung gia tri dang chay.
TS_GIVEBACK_RATIO=0.5

# --- SIZING ---
DCA_GRID_SCALE=19.5
TIER_FLAT=1
# 2026-09-03 (B3): BASE_BUDGET = CAPITAL_START / NUMBER_ORDER_BUDGET = 35000/50 = 700 USDT / lenh.
# Truoc day nam trong config.properties (CAPITAL_START) va default Java (50) — khong ai nhin cung mot cho.
CAPITAL_START=35000

# --- DCA (tat: chi 1 leg, toan bo budget) ---
DCA_GRID_ENABLED=true
DCA_GRID_WEIGHTS=1,1,3,8

# --- CHI PHI & FUNDING ---
SIM_APPLY_FUNDING=true
SIM_FUNDING_MARK=true

# --- BREAKER ---
SIM_BREAKER_MODE=OFF

# --- SLEEVE ---
# false = giu sleeve selector (hanh vi dang chay). true = tat het, chi con DCA_LEVEL1 + BIG_DOWN.

# --- BA CO SUA BUG (2026-09-05) ---
# B1 mergeOrder chep symbolPred | B2 tong trong so DCA chia dung 1 lan | B3 sizing theo equity.
# false = tai lap hanh vi CU byte-identical (cong hoi quy C2b).
SIM_FIX_B1=true
SIM_FIX_B2=true
SIM_FIX_B3=true
```

### 1.4 Grid profiles — 6 file `x1_gd2_*.properties` (từ git), khác nhau đúng 2 dòng
| profile | SIM_GATE_ROLLING_PCT | SIM_GATE_ROLLING_DAYS |
|---|---|---|
| x1_gd2_G90W60 | 0.90 | 60 |
| x1_gd2_G90W120 | 0.90 | 120 |
| x1_gd2_G92W60 | 0.92 | 60 |
| x1_gd2_G92W120 | 0.92 | 120 |
| x1_gd2_G94W60 | 0.94 | 60 |
| x1_gd2_G94W120 | 0.94 | 120 |

### 1.5 Key cấu hình
```properties
SIM_GATE_ROLLING_PCT=0.92    # 0..1; không khai báo/rỗng/ngoài (0,1) => TẮT = hành vi cũ byte-identical
SIM_GATE_ROLLING_DAYS=90     # cửa sổ trượt (ngày), mặc định 90
```

---

## 2. KẾT QUẢ (số gốc, trước audit)

### 2.1 GATEDYN — 3 biến thể cơ bản
| run | pct/W | n | win% | TSloss% | mP|SL | maxDD% | UW | equity | CV quý |
|---|---|---|---|---|---|---|---|---|---|
| PARITY_R | 0.008 cứng | 2,266 | 84.69 | 14.96 | −19.570 | −12.46 | 227 | 111,428 | 0.712 |
| GD88 | 0.88/90 | 2,661 | 83.22 | 16.88 | −18.027 | −18.94 | 223 | 99,382 | 0.494 |
| **GD92** | **0.92/90** | **2,355** | **84.12** | **15.67** | **−17.026** | **−13.21** | **116** | **128,979** | **0.518** |
| GD96 | 0.96/90 | 1,873 | 84.04 | 15.64 | −17.066 | −11.90 | 175 | 104,680 | 0.559 |

### 2.2 GATEDYN2 — grid pct × W (6 biến thể)
| run | pct/W | n | win% | TSloss% | mP|SL | maxDD% | UW | equity | CV quý |
|---|---|---|---|---|---|---|---|---|---|
| G90W60 | 0.90/60 | 2,490 | 83.53 | 16.39 | −17.057 | −15.22 | 221 | 124,625 | 0.469 |
| G90W120 | 0.90/120 | 2,503 | 83.62 | 16.34 | −17.933 | −18.73 | 223 | 108,251 | 0.525 |
| G92W60 | 0.92/60 | 2,328 | 84.15 | 15.68 | −17.327 | −14.51 | 183 | 130,175 | 0.483 |
| G92W120 | 0.92/120 | 2,320 | 83.92 | 15.91 | −16.981 | −12.33 | 153 | 125,953 | 0.538 |
| G94W60 | 0.94/60 | 2,142 | 83.75 | 15.97 | −17.175 | −13.43 | 185 | 112,171 | 0.498 |
| G94W120 | 0.94/120 | 1,680 | 77.80 | 27.32 | −8.875 | −16.81 | 575 | 45,134 | 0.537 |

### 2.3 GD92 vs Parity — chi tiết theo QUÝ
```
=== SO LENH (n) ===
tag     X1_C3_FULL_GD92  X1_C3_FULL_PARITY_R
quy                                         
2022Q1               62                   61
2022Q2              210                  218
2022Q3               66                   51
2022Q4               78                   76
2023Q1              102                   60
2023Q2              103                   86
2023Q3               72                   54
2023Q4              232                  108
2024Q1              211                  184
2024Q2              163                  161
2024Q3              146                  104
2024Q4              272                  219
2025Q1              225                  259
2025Q2              117                  141
2025Q3               46                   61
2025Q4              250                  423

=== WIN% ===
tag     X1_C3_FULL_GD92  X1_C3_FULL_PARITY_R
quy                                         
2022Q1            74.19                75.41
2022Q2            83.33                84.40
2022Q3            92.42                94.12
2022Q4            62.82                73.68
2023Q1            94.12                93.33
2023Q2            74.76                83.72
2023Q3            88.89                88.89
2023Q4            86.64                89.81
2024Q1            88.15                88.59
2024Q2            79.14                80.12
2024Q3            82.19                84.62
2024Q4            86.03                89.50
2025Q1            86.67                86.10
2025Q2            82.91                80.85
2025Q3            82.61                80.33
2025Q4            85.20                82.74

=== TSLOSS% ===
tag     X1_C3_FULL_GD92  X1_C3_FULL_PARITY_R
quy                                         
2022Q1            25.81                24.59
2022Q2            16.67                16.06
2022Q3             7.58                 5.88
2022Q4            33.33                21.05
2023Q1             9.80                11.67
2023Q2            26.21                17.44
2023Q3            18.06                16.67
2023Q4            14.66                10.19
2024Q1            11.85                11.41
2024Q2            22.70                21.74
2024Q3            18.49                16.35
2024Q4            14.71                10.96
2025Q1            12.89                14.67
2025Q2            17.09                19.15
2025Q3            13.04                21.31
2025Q4             7.60                12.53

=== PNL (USD, tong lenh dong trong quy) ===
tag     X1_C3_FULL_GD92  X1_C3_FULL_PARITY_R
quy                                         
2022Q1           -546.7               -396.0
2022Q2            994.4               1447.3
2022Q3           3576.2               4280.9
2022Q4          -1488.0                724.2
2023Q1           5096.8               3201.3
2023Q2           7491.0               9727.1
2023Q3           4847.1               4180.9
2023Q4          10724.7               7611.5
2024Q1          12109.0              10463.8
2024Q2          -3566.7              -3541.0
2024Q3           4015.7               5539.9
2024Q4          16055.6              17447.8
2025Q1          11839.1              11256.8
2025Q2           2756.9               2548.0
2025Q3           1878.7              -2702.2
2025Q4          18195.7               4638.2

=== maxDD noi bo QUY (%) — tu equity hang ngay ===
tag     X1_C3_FULL_GD92  X1_C3_FULL_PARITY_R
quy                                         
2022Q1            -3.53                -3.74
2022Q2           -11.31                -9.72
2022Q3            -0.87                -0.38
2022Q4            -9.02                -5.39
2023Q1            -2.47                -2.47
2023Q2            -4.22                -2.39
2023Q3            -1.23                -1.23
2023Q4            -5.04                -2.49
2024Q1            -3.91                -3.61
2024Q2            -9.21                -8.94
2024Q3            -3.71                -2.02
2024Q4            -3.31                -1.74
2025Q1            -5.51                -7.78
2025Q2            -6.93                -6.98
2025Q3            -2.87                -4.27
2025Q4            -4.32               -12.89

=== TONG ===
X1_C3_FULL_PARITY_R: n=2266 pnl=76428 winTB=84.69%
X1_C3_FULL_GD92: n=2355 pnl=93980 winTB=84.12%
```

### 2.4 GD92 vs Parity — rate + CI (block 72h x1.21)
```
=== BANG CHINH (equity/CAGR KHONG phai tieu chi) ===
tag              n   win% TSloss%    mP|SM    mP|SL    meanP  mMargin  maxDD%    UW   equity   CAGR%
X1_C3_FULL_PARITY_R  2266  84.69   14.96    7.333  -19.570    3.308     1945  -12.46   227   111428   33.63
X1_C3_FULL_GD92  2355  84.12   15.67    7.324  -17.026    3.509     1841  -13.21   116   128979   38.61

=== PHAN BO PROFIT CUA WINNER (B1 doi hinh dang cai nay) ===
tag           n_win      p10      p25      med      p75      p90      max
X1_C3_FULL_PARITY_R   1919    3.500    4.000    5.000    7.499   12.999   207.00
X1_C3_FULL_GD92   1981    3.500    4.000    5.000    7.499   12.999   207.00

=== NHANH TRAILING (symbolPred leg-1; <= 0.29 = STRONG cap 0.08) ===
tag            STRONG     WEAK  no-pred   STRONG%
X1_C3_FULL_PARITY_R     1693      303      216     76.5%
X1_C3_FULL_GD92     1658      442      216     71.6%

=== mean(margin) THEO NAM (phep kiem B3: phai TANG theo equity) ===
tag                2022       2023       2024  margin_leg1   n_leg1   n_dca
X1_C3_FULL_PARITY_R      855.9     1688.3     1943.6      1945.28     2212      54
X1_C3_FULL_GD92      819.7     1454.2     1899.0      1851.34     2316      39

=== RETURN THEO QUY (%%) ===
tag           2022Q1  2022Q2  2022Q3  2022Q4  2023Q1  2023Q2  2023Q3  2023Q4  2024Q1  2024Q2  2024Q3  2024Q4  2025Q1  2025Q2  2025Q3  2025Q4
X1_C3_FULL_PARITY_R     0.6     2.4    11.9     1.8     7.8    18.1    11.3    13.2    15.8    -4.6     7.6    22.3    11.8     2.4    -2.5     4.3
X1_C3_FULL_GD92     0.7     0.6    10.1    -3.8    13.9    13.3    13.5    18.9    19.0    -4.6     5.4    20.5    12.6     2.6     1.7    16.4

=== RANG BUOC CUNG (maxDD<=15, UW<=120, khong nam am, khong quy < -5) ===
X1_C3_FULL_PARITY_R FAIL   nam={'2022': np.float64(17.3), '2023': np.float64(60.4), '2024': np.float64(45.3), '2025': np.float64(16.5)} qmin=-4.6
               vi pham: UW=227
X1_C3_FULL_GD92 PASS   nam={'2022': np.float64(7.2), '2023': np.float64(74.1), '2024': np.float64(44.3), '2025': np.float64(36.8)} qmin=-4.6

=== RATE THEO NAM ===
tag            nam      n   win%  TSloss%    mP|SM    mP|SL    meanP  mMargin
X1_C3_FULL_PARITY_R  2022    406  82.27    17.00    6.240  -17.534    2.200      856
X1_C3_FULL_PARITY_R  2023    308  88.64    13.64    8.487  -11.463    5.767     1688
X1_C3_FULL_PARITY_R  2024    668  86.23    14.52    7.232  -15.701    3.902     1944
X1_C3_FULL_PARITY_R  2025    884  83.26    14.82    7.491  -26.105    2.513     2535
X1_C3_FULL_GD92  2022    416  79.57    19.71    6.135  -18.514    1.276      820
X1_C3_FULL_GD92  2023    509  86.05    16.50    7.820  -11.335    4.659     1454
X1_C3_FULL_GD92  2024    792  84.47    16.29    7.298  -15.578    3.572     1899
X1_C3_FULL_GD92  2025    638  85.11    11.60    7.684  -24.359    3.967     2743

--- CI khoi-72h x1.21 : X1_C3_FULL_GD92 - X1_C3_FULL_PARITY_R [TOAN CUA SO] (n_A=2355 n_B=2266)
rate            hieu          lo          hi  ngoaiCI
n             89.000    -108.970     294.020        -
win%          -0.568      -2.069       0.866        -
TSloss%        0.709      -0.903       2.313        -
mP|SM         -0.009      -0.368       0.370        -
mP|SL          2.544       0.051       5.363      YES
meanP          0.200      -0.346       0.784        -
mMargin     -103.717    -213.373       3.898        -
  => so rate CHAT LUONG ngoai CI (bo n, mMargin): 1

--- CI khoi-72h x1.21 : X1_C3_FULL_GD92 - X1_C3_FULL_PARITY_R [2022] (n_A=416 n_B=406)
rate            hieu          lo          hi  ngoaiCI
n             10.000     -32.350      52.350        -
win%          -2.699      -6.628       0.611        -
TSloss%        2.716      -1.005       7.116        -
mP|SM         -0.105      -0.700       0.352        -
mP|SL         -0.980      -3.580       2.489        -
meanP         -0.923      -2.085       0.132        -
mMargin      -36.164     -92.305      20.563        -
  => so rate CHAT LUONG ngoai CI (bo n, mMargin): 0

--- CI khoi-72h x1.21 : X1_C3_FULL_GD92 - X1_C3_FULL_PARITY_R [2023] (n_A=509 n_B=308)
rate            hieu          lo          hi  ngoaiCI
n            201.000     116.092     310.933      YES
win%          -2.585      -5.950       0.785        -
TSloss%        2.867      -0.958       6.355        -
mP|SM         -0.667      -2.297       0.541        -
mP|SL          0.128      -2.925       3.035        -
meanP         -1.108      -2.783       0.205        -
mMargin     -234.038    -367.726    -113.388      YES
  => so rate CHAT LUONG ngoai CI (bo n, mMargin): 0

--- CI khoi-72h x1.21 : X1_C3_FULL_GD92 - X1_C3_FULL_PARITY_R [2024] (n_A=792 n_B=668)
rate            hieu          lo          hi  ngoaiCI
n            124.000      71.340     182.660      YES
win%          -1.758      -4.216       0.414        -
TSloss%        1.767      -0.373       4.139        -
mP|SM          0.066      -0.163       0.309        -
mP|SL          0.123      -1.778       2.049        -
meanP         -0.330      -0.866       0.200        -
mMargin      -44.615    -137.303      47.099        -
  => so rate CHAT LUONG ngoai CI (bo n, mMargin): 0

--- CI khoi-72h x1.21 : X1_C3_FULL_GD92 - X1_C3_FULL_PARITY_R [2025] (n_A=638 n_B=884)
rate            hieu          lo          hi  ngoaiCI
n           -246.000    -366.243    -144.782      YES
win%           1.852      -0.086       3.937        -
TSloss%       -3.220      -5.859      -0.557      YES
mP|SM          0.193      -1.041       1.154        -
mP|SL          1.746      -3.661       6.829        -
meanP          1.455       0.371       2.336      YES
mMargin      208.365     -58.254     644.196        -
  => so rate CHAT LUONG ngoai CI (bo n, mMargin): 2

=== DCA THEO NAM (leg>=2 = leg thu 2 tro di trong cum) ===
tag            nam   n_leg1  n_leg2+    pnl_leg2+ meanP_leg2+
X1_C3_FULL_PARITY_R  2022      386       20       2758.3     14.279
X1_C3_FULL_PARITY_R  2023      308        0          0.0        nan
X1_C3_FULL_PARITY_R  2024      666        2       -164.2    -10.613
X1_C3_FULL_PARITY_R  2025      852       32       4813.2     23.918
X1_C3_FULL_GD92  2022      396       20       2129.1     12.580
X1_C3_FULL_GD92  2023      508        1        455.6     52.104
X1_C3_FULL_GD92  2024      790        2       -167.3    -10.613
X1_C3_FULL_GD92  2025      622       16       9454.3     44.760

=== RANG BUOC CUNG THEO NAM (maxDD<=15%, UW<=120, nam khong am, quy>=-5%) ===
tag            nam    maxDD%     UW  ret_nam%  quy_min%   PASS
X1_C3_FULL_PARITY_R  2022    -12.46     64     17.30      0.63   PASS
X1_C3_FULL_PARITY_R  2023     -2.51     45     60.43      7.80   PASS
X1_C3_FULL_PARITY_R  2024    -11.36    121     45.36     -4.64 **FAIL**
X1_C3_FULL_PARITY_R  2025    -10.60    227     16.45     -2.47 **FAIL**
X1_C3_FULL_GD92  2022    -13.21     69      7.24     -3.81   PASS
X1_C3_FULL_GD92  2023     -5.24     63     74.12     13.33   PASS
X1_C3_FULL_GD92  2024    -11.36    114     43.91     -4.58   PASS
X1_C3_FULL_GD92  2025     -6.11    116     36.76      1.72   PASS

=== CONG PARITY NOI BO (cat end <= 2024-06-30) ===

=== n_eff muc LENH = so khoi 72h CO it nhat 1 lenh ===
    (908 cua F4_TIMING la n_eff muc TICK cua tang gate — KHAC don vi, dung so sanh)
  X1_C3_FULL_PARITY_R n_eff=174
  X1_C3_FULL_GD92 n_eff=177
```

### 2.5 Độ đều phân bổ lệnh theo quý (CV) — 8 run
```
                tag    n   std  mean    cv  minq  maxq qmin_name qmax_name
X1_C3_FULL_PARITY_R 2266 100.8 141.6 0.712    51   423    2022Q3    2025Q4
    X1_C3_FULL_GD92 2355  76.2 147.2 0.518    46   272    2025Q3    2024Q4
  X1_C3_FULL_G90W60 2490  73.0 155.6 0.469    59   278    2025Q3    2024Q4
 X1_C3_FULL_G90W120 2503  82.2 156.4 0.525    52   284    2025Q3    2024Q4
  X1_C3_FULL_G92W60 2328  70.2 145.5 0.483    51   266    2025Q3    2024Q4
 X1_C3_FULL_G92W120 2320  78.0 145.0 0.538    45   271    2025Q3    2024Q4
  X1_C3_FULL_G94W60 2142  66.7 133.9 0.498    45   238    2025Q3    2024Q4
 X1_C3_FULL_G94W120 1680  56.4 105.0 0.537    32   198    2022Q3    2024Q4

Chi tiet n/quy:
X1_C3_FULL_PARITY_R: 2022Q1:61 2022Q2:218 2022Q3:51 2022Q4:76 2023Q1:60 2023Q2:86 2023Q3:54 2023Q4:108 2024Q1:184 2024Q2:161 2024Q3:104 2024Q4:219 2025Q1:259 2025Q2:141 2025Q3:61 2025Q4:423
X1_C3_FULL_GD92: 2022Q1:62 2022Q2:210 2022Q3:66 2022Q4:78 2023Q1:102 2023Q2:103 2023Q3:72 2023Q4:232 2024Q1:211 2024Q2:163 2024Q3:146 2024Q4:272 2025Q1:225 2025Q2:117 2025Q3:46 2025Q4:250
X1_C3_FULL_G90W60: 2022Q1:65 2022Q2:211 2022Q3:89 2022Q4:84 2023Q1:119 2023Q2:115 2023Q3:85 2023Q4:241 2024Q1:213 2024Q2:177 2024Q3:152 2024Q4:278 2025Q1:232 2025Q2:121 2025Q3:59 2025Q4:249
X1_C3_FULL_G90W120: 2022Q1:71 2022Q2:216 2022Q3:63 2022Q4:83 2023Q1:115 2023Q2:108 2023Q3:77 2023Q4:250 2024Q1:233 2024Q2:168 2024Q3:138 2024Q4:284 2025Q1:242 2025Q2:123 2025Q3:52 2025Q4:280
X1_C3_FULL_G92W60: 2022Q1:60 2022Q2:189 2022Q3:78 2022Q4:75 2023Q1:113 2023Q2:112 2023Q3:78 2023Q4:220 2024Q1:202 2024Q2:168 2024Q3:137 2024Q4:266 2025Q1:218 2025Q2:117 2025Q3:51 2025Q4:244
X1_C3_FULL_G92W120: 2022Q1:62 2022Q2:202 2022Q3:52 2022Q4:77 2023Q1:100 2023Q2:105 2023Q3:72 2023Q4:237 2024Q1:221 2024Q2:158 2024Q3:127 2024Q4:271 2025Q1:221 2025Q2:117 2025Q3:45 2025Q4:253
X1_C3_FULL_G94W60: 2022Q1:51 2022Q2:169 2022Q3:67 2022Q4:68 2023Q1:106 2023Q2:106 2023Q3:73 2023Q4:202 2024Q1:188 2024Q2:154 2024Q3:118 2024Q4:238 2025Q1:214 2025Q2:107 2025Q3:45 2025Q4:236
X1_C3_FULL_G94W120: 2022Q1:49 2022Q2:139 2022Q3:32 2022Q4:36 2023Q1:74 2023Q2:78 2023Q3:53 2023Q4:164 2024Q1:141 2024Q2:128 2024Q3:102 2024Q4:198 2025Q1:173 2025Q2:99 2025Q3:35 2025Q4:179
```

---

## 3. AUDIT ĐỘC LẬP — `docs/audit/AUDIT_GATEDYN_GD92.md` (11/09/2026)

**Phán quyết: KHÔNG PHÂN BIỆT ĐƯỢC (nhiễu) ở tầng hiệu quả; GATEDYN2 vi phạm phương pháp.**

### 3.1 Cái ĐƯỢC công nhận
- **Tái lập byte-identical**: chạy lại GD92 trên dataset build lại → md5 `eb607396fadb…` trùng,
  bảng `[GATE-ROLL]` trùng (39,510 mốc, min 0.00456 max 0.01265). Không bịa số, không lỗi scope,
  không chạm holdout, bins sạch.
- **Pre-reg có trước run** ở cả 2 đợt (đúng thứ tự). **Baseline hợp lệ** (md5 parity `2478e90d…`,
  khớp canonical). **Mọi số trong RESULT tái lập 100%** bằng `x1_rates.py`.
- **Mục tiêu PRIMARY đạt THẬT**: độ đều phân bố lệnh CV quý 0.712 → 0.518 (đúng yêu cầu user 09/09).

### 3.2 Cái BỊ BÁC
- **"THẮNG" không đứng vững**: `d = CAGR(GD92) − CAGR(PARITY) = +4.98pp`, `CI95 [−4.47, +16.09]`
  **chứa 0** → theo `PREREG_CI` mục 4 là "KHÔNG PHÂN BIỆT ĐƯỢC", trước cả khi hiệu chỉnh bội.
  Hiệu chỉnh bội k=9: ngưỡng `2.0963×sd = 10.90pp` — `d` thua hơn 2.2 lần.
- **UW 116 bị dùng sai vai trò**: UW/underwater là **số quan sát MỘT LẦN, KHÔNG có CI**
  (`PREREG_CI` mục 2.5 nói thẳng). Em đã dùng nó làm **bằng chứng quyết định chính** — vượt bằng
  chứng. UW 116 vs ngưỡng 120 chỉ **dư 4 ngày**; cùng cơ chế W=60/W=120 cho 183/153.
- **GATEDYN2 vi phạm `B4_RESULT` dòng 179-180**: *"KHÔNG mở thêm biến thể trên cùng không gian
  (nới cửa sổ, đổi phân vị, đổi tần số cập nhật…). Thêm biến thể = chọn trên nhiều = leak L2."*
  Grid 6 điểm quanh winner = đúng 2 thao tác bị cấm. Pre-reg riêng không tẩy trắng được thiết kế
  đã bị kết quả đợt 1 điều hướng.
- **Đọc ngược kết quả grid**: 6/6 láng giềng FAIL, 3 metric đạt đỉnh ở 3 điểm khác nhau
  (CV thấp nhất G90W60, equity cao nhất G92W60, UW thấp nhất GD92) = dấu hiệu **đỉnh nhiễu**,
  không phải "vùng ổn định". GD92 chỉ là điểm **lọt khe** UW≤120.
- **"0 rate xấu ngoài CI" ≠ "không hy sinh chất lượng"** — chỉ là "không bác bỏ được"; CI win%
  rộng ~3pp nên giảm thật 1.5pp vẫn không bị phát hiện. Rate "TỐT" duy nhất (mP|SL +2.544) có
  cận dưới **0.051** (sát 0), trong ~225 lần kiểm CI không hiệu chỉnh bội.
- **Theo năm**: `d` đổi chiều (2022 **−10.06pp** — GD92 KÉM hơn, là năm duy nhất CI không chứa 0;
  2023 +13.69; 2024 −0.97; 2025 +20.38). GD92 **đổi rủi ro từ 2025 sang 2022** (2022: maxDD
  −13.21 vs −12.46, ret +7.24 vs +17.30, quy min −3.81 vs +0.63).

### 3.3 Khuyến nghị của audit
Không chốt GD92 vào production dựa trên bằng chứng hiện tại. Nếu vẫn muốn giữ hướng "gate động
theo phân vị": tách bạch (a) **công nhận độ đều đạt được**, (b) **không tuyên bố cải thiện hiệu
quả**. Muốn nâng (b) thành kết luận → cần dữ liệu ngoài mẫu (VALIDATION/holdout) với pre-reg
riêng, **một cấu hình duy nhất đã chốt (0.92/90)**, không quét thêm.

---

## 4. LẤY LẠI CODE TỪ GIT (nếu muốn dùng/khôi phục)

```bash
cd /home/ubuntu/src/BinanceFuturesJava
DEL=f1c43a3                       # commit da xoa code rolling

# xem lai code
git show $DEL^:src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/GateRollingThreshold.java
git show $DEL^:profiles/x1_gd92.properties

# khoi phuc file vao working tree (neu can chay lai)
git checkout $DEL^ -- src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/GateRollingThreshold.java
git checkout $DEL^ -- profiles/x1_gd92.properties profiles/x1_gd2_G90W60.properties \
    profiles/x1_gd2_G90W120.properties profiles/x1_gd2_G92W60.properties \
    profiles/x1_gd2_G92W120.properties profiles/x1_gd2_G94W60.properties profiles/x1_gd2_G94W120.properties
```
LƯU Ý: khôi phục code rolling đưa lại "cờ trỏ" mà `f1c43a3` cố tình xóa. Cần cân nhắc trước khi
commit; `AIRejectFilter` hiện tại đã đổi (gate gộp về `EntryGate`) nên phải kiểm lại điểm nối.

---

## 5. TÁI LẬP KẾT QUẢ

```bash
R=/home/ubuntu/src/BinanceFuturesJava; JAR=$R/target/binance-java-sdk-1.2.4.jar
# build dataset 1 lan: ExportWfoDataset WFO_SET_PRED=ai_pred_market_gate_wfo
#   WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1 -> wfo_ds_x1_gd
# roi chay profile tuong ung:
env WFO_DATA_DIR=<ds> WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
    EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json \
    TRADING_PROFILE=$R/profiles/x1_gd92.properties \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
    com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss
# cham: python3 research/analysis/{gd_evenness,gd_quarterly,x1_rates}.py X1_C3_FULL_PARITY_R X1_C3_FULL_GD92
```
Script vận hành gốc: `/home/ubuntu/gate_feat_study/run_gatedyn*.sh`.
Artifact: 8 printDone trong `/home/ubuntu/java/devrun/X1_C3_FULL_{PARITY_R,GD92,GD88,GD96,G*W*}`.
Docs: `docs/prereg/PREREG_GATEDYN.md`, `docs/result/RESULT_GATEDYN.md`, `docs/prereg/PREREG_GATEDYN2.md`,
`docs/result/RESULT_GATEDYN2.md`, `docs/audit/AUDIT_GATEDYN_GD92.md`.

## 6. COMMIT REFS
| commit | nội dung |
|---|---|
| 3cdccd0 | PREREG_GATEDYN |
| 272d8f1 | RESULT_GATEDYN (GD92 đạt độ đều; claim "thắng" — về sau bị audit bác) |
| 1c1ecca | PREREG_GATEDYN2 (grid pct×W) |
| 41d5d76 | RESULT_GATEDYN2 |
| f1c43a3 | xóa GateRollingThreshold + profiles rolling (refactor gate → EntryGate) |
| (audit) | docs/audit/AUDIT_GATEDYN_GD92.md |
