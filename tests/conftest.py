import numpy as np
import pandas as pd
import pytest

from src import api


@pytest.fixture
def history():
    dates = pd.date_range("1981-01-01", "2025-12-31", freq="D")
    seasonal = 10 * np.sin(2 * np.pi * (dates.dayofyear - 80) / 365.25)
    warming = 0.03 * (dates.year - 1981)
    return pd.DataFrame({"date": dates, "temp_mean": 25 + seasonal + warming})


@pytest.fixture
def raw_forecast():
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-10-10", periods=5, freq="D"),
            "temp_max": [34.0, 35.0, 41.0, 33.0, 30.0],
            "temp_min": [22.0, 23.0, 26.0, 21.0, 20.0],
            "precipitation": [0.0, 0.0, 0.0, 70.0, 5.0],
            "wind_max": [10.0, 12.0, 15.0, 55.0, 20.0],
            "uv_index": [7.0, 8.0, 9.0, 5.0, 4.0],
        }
    )


@pytest.fixture
def emissions():
    rows = []
    countries = {"India": ("IND", 3000, 2.1), "China": ("CHN", 11000, 7.8), "United States": ("USA", 5000, 14.9), "World": (None, 37000, 4.7)}
    for year in (2022, 2023):
        for name, (iso, total, per_capita) in countries.items():
            rows.append(
                {
                    "country": name,
                    "year": year,
                    "iso_code": iso,
                    "population": 1e9,
                    "co2": total + (year - 2022) * 100,
                    "co2_per_capita": per_capita,
                    "coal_co2": total * 0.5,
                    "oil_co2": total * 0.3,
                    "gas_co2": total * 0.15,
                    "cement_co2": total * 0.05,
                }
            )
    rows.append({"country": "Asia", "year": 2023, "iso_code": "OWID_ASI", "population": 4e9, "co2": 20000, "co2_per_capita": 4.0, "coal_co2": None, "oil_co2": None, "gas_co2": None, "cement_co2": None})
    return pd.DataFrame(rows, columns=api.OWID_COLUMNS)


@pytest.fixture
def co2_record():
    dates = pd.date_range("2023-01-01", periods=30, freq="MS")
    ppm = np.linspace(419, 427, 30)
    return pd.DataFrame({"date": dates, "decimal_year": dates.year + 0.5 / 12, "ppm": ppm, "trend": ppm})


@pytest.fixture
def air_quality():
    times = pd.date_range("2026-10-10", periods=120, freq="h")
    return {
        "current": {"us_aqi": 168, "pm2_5": 82.5, "pm10": 140.2, "nitrogen_dioxide": 40.1, "ozone": 55.0},
        "hourly": pd.DataFrame({"time": times, "us_aqi": np.linspace(120, 220, 120), "pm2_5": np.linspace(40, 110, 120)}),
    }
