/*
 * The MIT License
 *
 * Copyright 2023 pc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
package com.binance.chuyennd.utils;

/**
 *
 * @author pc
 */
import org.apache.commons.lang3.StringUtils;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.Proxy;
import java.net.URL;
import java.net.URLConnection;
import java.nio.channels.Channels;
import java.nio.channels.ReadableByteChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.zip.GZIPInputStream;

public class HttpRequest {

    private static final String J_CONNECTION = "close";
    // UserAgent
    public static String J_USER_AGENT = " Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0";
    //	private static final String J_ACCEPT = "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5";
    private static final String J_ACCEPT = "text/plain,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8";
    private static final String J_ACCEPT_CHARSET = "UTF-8,iso-8859-1;q=0.7,*;q=0.7";
    private static final String J_ACCEPT_LANGUAGE = "vi,en-US;q=0.8,en;q=0.6";
    private static final int NUM_RETRY_CONNECTION = 5;
    // Thoi gian connect
    public static int connect_time_out = 30 * 1000; // 30s
    // Thoi gian doc
    public static int read_time_out = 30 * 1000; // 30s
    // Do dai max content
    public static int max_content_length = 8 * 1024 * 1024; // 8M
    // Neu do dai cua content ma duoi gia tri nay thi day co the la trang redirect sang trag khac hoac la trang loi
    public static int min_content_length = 2000; // 2k
    // Cho phep redirect
    public static boolean follow_redirect = true;
    // Do sau cua lay redirect
    public static int max_depth_redirect = 6;

    /**
     * Tao ket noi den URL
     *
     * @param url_
     * @return
     */
    public static HttpURLConnection connect(URL url_, Map<String, String> extendedHeader) {
        return connect(url_, extendedHeader, null);
    }

    public static HttpURLConnection connectMp3(URL url_, Map<String, String> extendedHeader) {
        return connectMp3(url_, extendedHeader, null);
    }

    private static HttpURLConnection connect(URL url_, Map<String, String> extendedHeader, Proxy proxy) {
        try {
            URLConnection ucon;
            if (proxy == null) {
                ucon = (HttpURLConnection) url_.openConnection();
            } else {
                ucon = (HttpURLConnection) url_.openConnection(proxy);
            }
            HttpURLConnection conn = (HttpURLConnection) ucon;
            //conn.setRequestProperty("Cookie", "");
            conn.setUseCaches(false);
            conn.setAllowUserInteraction(true);
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(connect_time_out); // 10 sec
            conn.setReadTimeout(read_time_out); // 10 sec

            HttpURLConnection.setFollowRedirects(follow_redirect);
            conn.setInstanceFollowRedirects(follow_redirect);

            conn.addRequestProperty("Connection", J_CONNECTION);
            conn.addRequestProperty("User-Agent", J_USER_AGENT);
            conn.addRequestProperty("Accept", J_ACCEPT);
            conn.addRequestProperty("Accept-Charset", J_ACCEPT_CHARSET);
            conn.addRequestProperty("Accept-Language", J_ACCEPT_LANGUAGE);
            if (extendedHeader != null) {
                for (String field : extendedHeader.keySet()) {
                    conn.addRequestProperty(field, extendedHeader.get(field));
                }
            }

            conn.setDoOutput(true);
            conn.connect();
            return conn;
        } catch (Exception e1) {
//			e1.printStackTrace();
            return null;
        }
    }

    private static HttpURLConnection connectMp3(URL url_, Map<String, String> extendedHeader, Proxy proxy) {
        try {
            URLConnection ucon;
            if (proxy == null) {
                ucon = (HttpURLConnection) url_.openConnection();
            } else {
                ucon = (HttpURLConnection) url_.openConnection(proxy);
            }
            HttpURLConnection conn = (HttpURLConnection) ucon;
            //conn.setRequestProperty("Cookie", "");
            conn.setUseCaches(false);
            conn.setAllowUserInteraction(true);
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(connect_time_out); // 10 sec
            conn.setReadTimeout(read_time_out); // 10 sec

            HttpURLConnection.setFollowRedirects(follow_redirect);
            conn.setInstanceFollowRedirects(follow_redirect);

            conn.addRequestProperty("Content-Type", "media");
            conn.addRequestProperty("Connection", J_CONNECTION);
            conn.addRequestProperty("User-Agent", J_USER_AGENT);
            conn.addRequestProperty("Accept", J_ACCEPT);
            conn.addRequestProperty("Accept-Charset", J_ACCEPT_CHARSET);
            conn.addRequestProperty("Accept-Language", J_ACCEPT_LANGUAGE);
            if (extendedHeader != null) {
                for (String field : extendedHeader.keySet()) {
                    conn.addRequestProperty(field, extendedHeader.get(field));
                }
            }

            conn.setDoOutput(true);
            conn.connect();
            return conn;
        } catch (Exception e1) {
//			e1.printStackTrace();
            return null;
        }
    }

    public static void getContentFromUrl(String url, FileOutputStream out) {
        for (int i = 0; i < 1; i++) {
            try {
                HttpURLConnection hc = connect(new URL(url), null);
                int contentLength = hc.getContentLength();
                String contentType = hc.getContentType();
                if (contentType.startsWith("text/") || contentLength == -1) {
                    throw new IOException("This is not a binary file: " + url);
                }

                int c = 0;
                InputStream raw = hc.getInputStream();
                InputStream in = new BufferedInputStream(raw);
                byte[] data = new byte[contentLength];
                int bytesRead = 0;
                int offset = 0;
                while (offset < contentLength) {
                    bytesRead = in.read(data, offset, data.length - offset);
                    if (bytesRead == -1) {
                        break;
                    }
                    offset += bytesRead;
                }
                in.close();
                if (offset != contentLength) {
                    throw new IOException("Only read " + offset + " bytes; Expected " + contentLength + " bytes: " + url);
                }
                out.write(data);
                out.flush();
                return;
            } catch (Exception ex) {
                ex.printStackTrace();
            }
            try {
                Thread.sleep(10000);
            } catch (InterruptedException ex) {
                Logger.getLogger(HttpRequest.class.getName()).log(Level.SEVERE, null, ex);
            }
        }
    }

    public static String getContentFromUrl(String url) {
        return getContentFromUrl(url, new HashMap<String, String>());
    }

    public static int getUrlResponCode(String url) {
        url = StringUtils.replace(url, "[^a-zA-Z1-90_\\- \\.//:]*", "");
        int content = 404;
        for (int i = 0; i < NUM_RETRY_CONNECTION; i++) {
            try {
                HttpURLConnection hc = connect(new URL(url), new HashMap<String, String>());
                int content_length = hc.getContentLength();
                if ((content_length > max_content_length) || (content_length == -1)) {
                    content_length = max_content_length;
                }
                return hc.getResponseCode();
            } catch (Exception ex) {
//				ex.printStackTrace();
                if (i == NUM_RETRY_CONNECTION - 1) {
                    return 404;
                }

            }
        }
        return content;
    }

    public static int getUrlResponCodeMp3(String url) {
        url = StringUtils.replace(url, "[^a-zA-Z1-90_\\- \\.//:]*", "");
        int content = 404;
        for (int i = 0; i < NUM_RETRY_CONNECTION; i++) {
            try {
                HttpURLConnection hc = connectMp3(new URL(url), new HashMap<String, String>());
                int content_length = hc.getContentLength();
                if ((content_length > max_content_length) || (content_length == -1)) {
                    content_length = max_content_length;
                }
                return hc.getResponseCode();
            } catch (Exception ex) {
//				ex.printStackTrace();
                if (i == NUM_RETRY_CONNECTION - 1) {
                    return 404;
                }

            }
        }
        return content;
    }

    public static String getContentFromUrl(String url, Map<String, String> extendedHeader) {
        String content = "";
        boolean useGZip = false;
        for (int i = 0; i < NUM_RETRY_CONNECTION; i++) {
            try {
                HttpURLConnection hc = connect(new URL(url), extendedHeader);
                int content_length = hc.getContentLength();
                if ((content_length > max_content_length) || (content_length == -1)) {
                    content_length = max_content_length;
                }

                StringBuilder sb = new StringBuilder();
                int c = 0;
                InputStream is = null;

                if (useGZip) {
                    is = new GZIPInputStream(hc.getInputStream());
                    content_length = 1 * 1024 * 1024;
                } else if (hc.getResponseCode() < 400) {
                    is = hc.getInputStream();
                } else {
                    /* error from server */
                    is = hc.getErrorStream();
                }
                BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
                char ch[] = new char[content_length];

                while (c < content_length) {
                    int t = br.read(ch, 0, content_length);

                    if (t > 0) {
                        sb.append(ch, 0, t);
                    } else {
                        break;
                    }

                    c = c + t;
                }

                br.close();
                content = sb.toString();
                if (hc.getURL() != null) {
                    url = hc.getURL().toString();
                }
                //System.out.println(hc.getHeaderField("Content-Encoding"));
                try {
                    if (!content.contains("<body>") && hc.getHeaderField("Content-Encoding").equals("gzip")) {
                        useGZip = true;
                        continue;
                    }
                } catch (Exception ex) {
                }
                break;
            } catch (Exception ex) {
//				ex.printStackTrace();
                if (i == NUM_RETRY_CONNECTION - 1) {
                    return null;
                }

            }
        }
        return content;
    }

    public static void getFileFromUrl(String url, String filePath) {
        try {
            URL website = new URL(url);
            ReadableByteChannel rbc = Channels.newChannel(website.openStream());
            Path file = Paths.get(filePath);
            if (StringUtils.containsIgnoreCase(filePath, "/")) {
                Files.createDirectories(file.getParent());
            }
            FileOutputStream fos = new FileOutputStream(filePath);
            fos.getChannel().transferFrom(rbc, 0, Long.MAX_VALUE);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) throws MalformedURLException {
//        System.out.println(Crawler.getContentFromUrl("https://ipfind.co?ip=8.8.8.8"));
//        Crawler.getFileFromUrl("http://stream.dict.laban.vn/uk/54187d75298ba173b0f1500859ef5e46/160e9dd569c/A/April.mp3", "test/April.mp3");
        String url = "https:\\/\\/cdn.edupia.vn\\/resource\\/video\\/word\\/sing_ng.mp4";
        System.out.println(StringUtils.replace(url, "[^a-zA-Z1-90_\\- \\.//:]*", ""));
//        System.out.println(Crawler.getUrlResponCode(URLEncoder.encode(url)));
//        System.out.println(Crawler.getUrlResponCode("https://181f620f0.vws.vegacdn.vn/video/2018/07/12/Unit-12-vid2-mute-all-fn.mp4"));
    }

}
