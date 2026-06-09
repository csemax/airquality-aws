import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1] / "lambda" / "fetcher"))
from classifier import classify_aqi

def test_good_aqi():
    result = classify_aqi({"aqi": 40, "pm25": 4})
    assert result["category"] == "Good"
    assert result["pm25_category"] == "Safe"

def test_moderate_aqi():
    result = classify_aqi({"aqi": 80, "pm25": 10})
    assert result["category"] == "Moderate"
    assert result["pm25_category"] == "Moderate"
