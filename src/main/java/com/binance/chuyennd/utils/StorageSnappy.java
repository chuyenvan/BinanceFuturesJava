

package com.binance.chuyennd.utils;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

import com.binance.chuyennd.proto.KlineProto;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;


/**
 * @author pc
 */
public class StorageSnappy {

    public static final Logger LOG = LoggerFactory.getLogger(StorageSnappy.class);

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
            // Nén dữ liệu trước khi ghi
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ObjectOutputStream tempOos = new ObjectOutputStream(baos);
            tempOos.writeObject(o);
            tempOos.close();
            byte[] compressedData = Snappy.compress(baos.toByteArray());
            oos.writeObject(compressedData);
        }

        public void close() throws IOException {
            oos.close();
        }
    }

    public static void main(String[] args) {
        System.out.println("test");
    }

    public static class Reader {

        private final ObjectInputStream ois;

        public Reader(File input) throws IOException {
            ois = new ObjectInputStream(new BufferedInputStream(new FileInputStream(input)));
        }

        public Object next() {
            try {
                // Đọc và giải nén dữ liệu
                byte[] compressedData = (byte[]) ois.readObject();
                byte[] decompressedData = Snappy.uncompress(compressedData);
                ObjectInputStream tempOis = new ObjectInputStream(new BufferedInputStream(new ByteArrayInputStream(decompressedData)));
                return tempOis.readObject();
            } catch (IOException | ClassNotFoundException ex) {
                ex.printStackTrace();
                return null;
            }
        }

        public void close() throws IOException {
            ois.close();
        }
    }

    public static void writeObject2File(String path, Object obj) {
        // 1. Định nghĩa file gốc và file tạm
        File finalFile = new File(path);
        File tempFile = new File(path + ".tmp");

        try {
            // 2. Luôn ghi dữ liệu vào file tạm
            Writer writer = new Writer(tempFile);
            writer.write(obj);
            writer.close(); // Đảm bảo file tạm được ghi xong và đóng lại

            // 3. Đổi tên file tạm thành file gốc (thao tác nguyên tử)
            //    REPLACE_EXISTING đảm bảo file gốc cũ sẽ bị ghi đè bởi file tạm mới.
            Files.move(tempFile.toPath(), finalFile.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);

            // LOG.info("Ghi file {} thành công.", path);

        } catch (Exception e) {
            // Nếu có lỗi, xóa file tạm đi để tránh rác
            if (tempFile.exists()) {
                tempFile.delete();
            }
        }
    }

    public static Object readObjectFromFile(String fileName) {
        Object object = null;
        try {
            File file = new File(fileName);
            if (!file.exists()) {
                return object;
            }
            StorageSnappy.Reader reader = new StorageSnappy.Reader(file);
            object = reader.next();
            reader.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return object;
    }

    public static void writeProto2File(String path, KlineProto.KlineObjectSimpleProto klineProto) {
        try (FileOutputStream fos = new FileOutputStream(path)) {
            klineProto.writeTo(fos);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // Đọc file
    public static KlineProto.KlineObjectSimpleProto readProtoFromFile(String path) {
        try (FileInputStream fis = new FileInputStream(path)) {
            return KlineProto.KlineObjectSimpleProto.parseFrom(fis);
        } catch (IOException e) {
            e.printStackTrace();
            return null;
        }
    }
}