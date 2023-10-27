/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.utils;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class Storage {

    public static final Logger LOG = LoggerFactory.getLogger(Storage.class);

    public static class Writer {

        private final ObjectOutputStream oos;

        public Writer(File output) throws FileNotFoundException, IOException {
            Path file = Paths.get(output.getAbsolutePath());
            if (!file.getParent().toFile().exists()) {
                Files.createDirectories(file.getParent());
            }
            oos = new ObjectOutputStream(new FileOutputStream(output));
        }

        public void write(Object o) throws IOException {
            oos.writeObject(o);
        }

        public void close() throws IOException {
            oos.close();
        }
    }

    public static class Reader {

        private final ObjectInputStream ois;

        public Reader(File input) throws IOException {
            ois = new ObjectInputStream(new BufferedInputStream(new FileInputStream(input)));
        }

        public Object next() {
            try {
                return ois.readObject();
            } catch (IOException | ClassNotFoundException ex) {
                ex.printStackTrace();
                return null;
            }
        }

        public void close() throws IOException {
            ois.close();
        }
    }

    public static void writeObject2File(String fileName, Object data) {
        try {
            Storage.Writer writer = new Storage.Writer(new File(fileName));
            writer.write(data);
            writer.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static Object readObjectFromFile(String fileName) {
        Object object = null;
        try {
            File file = new File(fileName);
            if (!file.exists()) {
                return object;
            }
            Storage.Reader reader = new Storage.Reader(file);
            object = reader.next();
            reader.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return object;
    }
}
