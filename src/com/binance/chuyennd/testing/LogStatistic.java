/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.testing;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class LogStatistic {

    public static final Logger LOG = LoggerFactory.getLogger(LogStatistic.class);

    public static void main(String[] args) throws IOException {
        statisticLogBigChangeInTime();
    }

    private static void statisticLogBigChangeInTime() throws IOException {
        List<String> lines = FileUtils.readLines(new File("target/nohup.out"));
        Map<String, List<String>> symbol2Logs = new HashMap<>();
        for (String line : lines) {
            if (StringUtils.contains(line, "symbol:")) {
                String symbol = getSymbol(line);
                List<String> logs = symbol2Logs.get(symbol);
                if (logs == null) {
                    logs = new ArrayList();
                }
                logs.add(line);
                symbol2Logs.put(symbol, logs);
            }
        }
        for (Map.Entry<String, List<String>> entry : symbol2Logs.entrySet()) {
            Object symbol = entry.getKey();
            List<String> symnbolLogs = entry.getValue();
            boolean check = false;
            for (String symnbolLog : symnbolLogs) {
                if (StringUtils.containsIgnoreCase(symnbolLog, "Warning symbol")) {
                    check = true;
                }
                if (check) {
                    LOG.info(symnbolLog);
                }
            }
        }

    }

    private static String getSymbol(String line) {
        String[] parts = StringUtils.split(line, "symbol:");
        String symbol = parts[3];
        symbol = StringUtils.split(symbol, " ")[0];
        return symbol.trim();
    }
}
