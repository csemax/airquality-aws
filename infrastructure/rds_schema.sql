CREATE DATABASE IF NOT EXISTS airquality_db;
USE airquality_db;

CREATE TABLE IF NOT EXISTS air_quality_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    station_name VARCHAR(255),
    station_id VARCHAR(50),
    recorded_at DATETIME NOT NULL,
    aqi FLOAT,
    pm25 FLOAT,
    pm10 FLOAT,
    o3 FLOAT,
    no2 FLOAT,
    so2 FLOAT,
    co FLOAT,
    temperature FLOAT,
    humidity FLOAT,
    category VARCHAR(50),
    level INT,
    health_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_city_time (city, recorded_at),
    INDEX idx_category (category),
    UNIQUE KEY unique_city_time (city, recorded_at)
);
