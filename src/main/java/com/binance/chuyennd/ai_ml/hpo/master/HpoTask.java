package com.binance.chuyennd.ai_ml.hpo.master;

public class HpoTask {

    public String taskId; // Hash của 11 tham số để không bao giờ chạy trùng
    public String status; // PENDING, RUNNING, DONE

    // 11 Tham số
    public float ds, dm, db, us, um, ub, d15s;
    public float aiRisk, ai15m, ai24h, aiMaxThres;

    public float fitnessScore = -10000f; // Điểm số sau khi Kaggle chạy xong
    public String logDetail = "";
    public long startTime = 0L;
}