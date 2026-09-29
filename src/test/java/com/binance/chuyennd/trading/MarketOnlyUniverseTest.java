package com.binance.chuyennd.trading;

import org.junit.Test;

import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * [B4-SPEED] Bang chung cho phan THUAN {@code marketOnlyUniverse(universe, held)}: tick market-only
 * KHÔNG tín hiệu chỉ predict symbol đang giữ (đủ cho DCA + giữ pNoPump tươi cho trailing) => quyết
 * định BIT-IDENTICAL, bỏ predict ~650 coin phí mỗi tick 1'. Khong cham mang/ONNX/live.
 */
public class MarketOnlyUniverseTest {

    private static Set<String> set(String... s) { return new LinkedHashSet<>(Arrays.asList(s)); }

    @Test
    public void heldRong_traRong() {
        Set<String> u = set("AUSDT", "BUSDT", "CUSDT");
        assertTrue("khong co symbol giu => khong predict gi",
                DetectEntrySignal2TradeNormal.marketOnlyUniverse(u, new HashSet<>()).isEmpty());
    }

    @Test
    public void giuLaiDungSymbolDangGiu() {
        Set<String> u = set("AUSDT", "BUSDT", "CUSDT", "DUSDT");
        Set<String> held = set("BUSDT", "DUSDT");
        Set<String> out = DetectEntrySignal2TradeNormal.marketOnlyUniverse(u, held);
        assertEquals("chi giu symbol DANG GIU (DCA can pred cua chinh no)", set("BUSDT", "DUSDT"), out);
    }

    @Test
    public void heldNgoaiUniverse_khongDuocThemVao() {
        Set<String> u = set("AUSDT", "BUSDT");
        Set<String> held = set("BUSDT", "ZZZUSDT");
        Set<String> out = DetectEntrySignal2TradeNormal.marketOnlyUniverse(u, held);
        assertEquals("held ngoai universe khong duoc sinh them", set("BUSDT"), out);
        assertTrue("ket qua ⊆ universe", u.containsAll(out));
    }

    @Test
    public void giuToanBoKhiCaUniverseDeuDangGiu() {
        Set<String> u = set("AUSDT", "BUSDT", "CUSDT");
        Set<String> held = set("AUSDT", "BUSDT", "CUSDT");
        assertEquals("tat ca deu giu => giu het", u,
                DetectEntrySignal2TradeNormal.marketOnlyUniverse(u, held));
    }
}
