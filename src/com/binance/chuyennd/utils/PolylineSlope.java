package com.binance.chuyennd.utils;

import java.util.ArrayList;
import java.util.List;

public class PolylineSlope {
    public static void main(String[] args) {
        // Ví dụ các điểm của đường gấp khúc
        List<Point> points = new ArrayList<Point>();

        points.add(new Point(1, 1));
        points.add(new Point(2, 5));
        points.add(new Point(3, 9));
        points.add(new Point(4, 12));


        calculateSlopes(points);
        System.out.println(calculateSlopesAvg(points));
    }

    public static void calculateSlopes(List<Point> points) {
        for (int i = 0; i < points.size() - 1; i++) {
            Point p1 = points.get(i);
            Point p2 = points.get(i + 1);

            double slope = calculateSlope(p1, p2);
            System.out.println("Slope between (" + p1.x + ", " + p1.y + ") and (" + p2.x + ", " + p2.y + ") is: " + slope);
        }
    }

    public static double calculateSlopesAvg(List<Point> points) {
        Double total = 0d;
        for (int i = 0; i < points.size() - 1; i++) {
            Point p1 = points.get(i);
            Point p2 = points.get(i + 1);
            double slope = calculateSlope(p1, p2);
            total += slope;
        }
        return total / (points.size() - 1);
    }

    public static double calculateSlope(Point p1, Point p2) {
        if (p2.x == p1.x) {
            throw new IllegalArgumentException("Slope is undefined for vertical line segments.");
        }
        return (p2.y - p1.y) / (p2.x - p1.x);
    }

}
