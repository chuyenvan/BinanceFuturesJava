package com.binance.chuyennd.tradecore.selector;

import java.util.TreeMap;

/**
 * [L5] Chon pool cho VONG ENTRY cua SO GIAY khi {@code LIVE_PROFILE=c3_shadow}.
 *
 * <p>LUAT: co C3 BAT ma S1 chua co score (warm-up chua xong / model hong / Aerospike loi)
 * => so giay <b>BO TICK</b> (pool RONG). TUYET DOI khong quay ve thu tu {@code pNoPump} cua
 * {@code Funding_Classifier_Final.onnx}: do la mot selector KHAC (ho maxFav, hieu chuan lech
 * 2 lan ? {@code G4_RECIPE_C4} muc 6.2). Mo entry theo no roi ghi vao so giay C3 lam ban CA
 * chuoi do. Mot tick TRONG hon mot tick SAI. Cung nguyen tac L4 da ap cho thang gia tri
 * net015 ({@code [MAP] chua co thang gia tri ... KHONG mo entry giay}).
 *
 * <p>Co TAT => tra dung pool cu => duong HEAD byte-identical.
 */
public final class EntryPoolGate {

    private EntryPoolGate() {
    }

    /** {@code true} khi pool S1 dung duoc (khac null va khong rong). */
    public static boolean usable(TreeMap<Float, String> s1Pool) {
        return s1Pool != null && !s1Pool.isEmpty();
    }

    /**
     * @param profileOn co {@code LIVE_PROFILE=c3_shadow}
     * @param pnpPool   pool cu xep theo {@code pNoPump} (duong HEAD)
     * @param s1Pool    pool xep theo score S1; {@code null}/rong = chua san sang
     * @return pool dung cho vong entry giay
     */
    public static TreeMap<Float, String> choose(boolean profileOn,
                                                TreeMap<Float, String> pnpPool,
                                                TreeMap<Float, String> s1Pool) {
        if (!profileOn) return pnpPool;
        if (!usable(s1Pool)) return new TreeMap<>();
        return s1Pool;
    }
}
