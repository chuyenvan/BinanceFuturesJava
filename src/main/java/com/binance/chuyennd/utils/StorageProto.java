package com.binance.chuyennd.utils;

import com.binance.chuyennd.proto.KlineArchiveProto;
import org.xerial.snappy.Snappy;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;

/**
 * Utility class for reading and writing Protobuf objects, with optional Snappy compression.
 */
public class StorageProto {

    /**
     * Writes a Protobuf message to a file after compressing it with Snappy.
     *
     * @param path         The file path to write to.
     * @param protoArchive The Protobuf message object.
     */
    public static void writeProtoWithSnappy(String path, KlineArchiveProto.KlineArchive protoArchive) {
        try {
            // 1. Serialize Protobuf object to byte array
            byte[] protoBytes = protoArchive.toByteArray();
            // 2. Compress the byte array using Snappy
            byte[] compressedBytes = Snappy.compress(protoBytes);
            // 3. Write the compressed bytes to the file
            Files.write(Paths.get(path), compressedBytes);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     * Reads a Snappy-compressed file and parses it into a Protobuf message.
     *
     * @param path The file path to read from.
     * @return The parsed Protobuf message object, or null if an error occurs.
     */
    public static KlineArchiveProto.KlineArchive readProtoWithSnappy(String path) {
        try {
            // 1. Read all bytes from the compressed file
            byte[] compressedBytes = Files.readAllBytes(Paths.get(path));
            // 2. Decompress the bytes using Snappy
            byte[] protoBytes = Snappy.uncompress(compressedBytes);
            // 3. Parse the decompressed bytes into a Protobuf object
            return KlineArchiveProto.KlineArchive.parseFrom(protoBytes);
        } catch (IOException e) {
            e.printStackTrace();
            return null;
        }
    }
}

