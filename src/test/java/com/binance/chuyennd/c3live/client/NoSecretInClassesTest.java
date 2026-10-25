package com.binance.chuyennd.c3live.client;

import org.junit.Test;

import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.junit.Assert.*;

/**
 * [V12 C2] Lop c3live da bien dich (thu muc classes hoac jar) KHONG chua chuoi giong key (>= 32 ky tu [A-Za-z0-9]) va
 * khong chua vector test. Key that chi nam o file root-only tren 242 -> khong the co trong jar.
 */
public class NoSecretInClassesTest {
    static final Pattern KEYLIKE = Pattern.compile("[A-Za-z0-9]{32,}");

    @Test
    public void compiledC3liveClassesHaveNoKeyLikeStrings() throws Exception {
        URL loc = C3LiveClient.class.getProtectionDomain().getCodeSource().getLocation();
        Path p = Paths.get(loc.toURI());
        List<String> hits = new ArrayList<>();
        int scanned = 0;
        if (Files.isDirectory(p)) {
            Path root = p.resolve("com/binance/chuyennd/c3live");
            try (Stream<Path> s = Files.walk(root)) {
                for (Path f : (Iterable<Path>) s.filter(x -> x.toString().endsWith(".class"))::iterator) {
                    scanned++;
                    scan(f.toString(), Files.readAllBytes(f), hits);
                }
            }
        } else {
            try (JarFile jf = new JarFile(p.toFile())) {
                Enumeration<JarEntry> en = jf.entries();
                while (en.hasMoreElements()) {
                    JarEntry e = en.nextElement();
                    if (!e.getName().startsWith("com/binance/chuyennd/c3live/") || !e.getName().endsWith(".class")) continue;
                    scanned++;
                    try (InputStream in = jf.getInputStream(e)) { scan(e.getName(), in.readAllBytes(), hits); }
                }
            }
        }
        assertTrue("phai quet duoc lop c3live: " + scanned, scanned >= 10);
        assertTrue("chuoi giong key trong lop c3live: " + hits, hits.isEmpty());
    }

    private static void scan(String name, byte[] b, List<String> hits) {
        String s = new String(b, StandardCharsets.ISO_8859_1);
        Matcher m = KEYLIKE.matcher(s);
        while (m.find()) hits.add(name + ":" + m.group().substring(0, 6) + "..(" + m.group().length() + ")");
        if (s.contains(C3LiveClientTest.KEY) || s.contains(C3LiveClientTest.SECRET)) hits.add(name + ": vector test");
    }
}
