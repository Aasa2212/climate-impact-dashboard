import pandas as pd

from src import api

NOAA_SAMPLE = """# Mauna Loa monthly mean CO2
# year month decimal average deseasonalized ndays stdev unc
1958   3    1958.208     315.71     314.44     -1     -9.99    -0.99
1958   4    1958.292     317.45     315.16     -1     -9.99    -0.99
1958   5    1958.375     317.51     314.69     -1     -9.99    -0.99
1958   6    1958.458     -99.99     315.15     -1     -9.99    -0.99
2026   8    2026.625     422.80     426.10     28      0.35     0.13
"""


def test_parse_noaa_co2_skips_comments_and_missing_values():
    co2 = api.parse_noaa_co2(NOAA_SAMPLE)
    assert len(co2) == 4
    assert co2["date"].iloc[0] == pd.Timestamp("1958-03-01")
    assert co2["ppm"].iloc[-1] == 422.80
    assert co2["trend"].iloc[-1] == 426.10


def test_parse_daily_forecast_handles_missing_values():
    payload = {
        "daily": {
            "time": ["2026-10-10", "2026-10-11"],
            "temperature_2m_max": [33.1, None],
            "temperature_2m_min": [21.0, 22.0],
            "precipitation_sum": [0.0, 1.2],
            "wind_speed_10m_max": [12.0, 14.0],
            "uv_index_max": [7.5, 8.1],
        }
    }
    daily = api.parse_daily_forecast(payload)
    assert list(daily.columns) == ["date", "temp_max", "temp_min", "precipitation", "wind_max", "uv_index"]
    assert daily["temp_max"].isna().tolist() == [False, True]


def test_parse_hourly_air():
    payload = {"hourly": {"time": ["2026-10-10T00:00", "2026-10-10T01:00"], "us_aqi": [150, None], "pm2_5": [60.2, 61.0]}}
    hourly = api.parse_hourly_air(payload)
    assert hourly["us_aqi"].isna().tolist() == [False, True]
    assert hourly["time"].iloc[1] == pd.Timestamp("2026-10-10 01:00")


def test_parse_history_drops_missing_days():
    payload = {"daily": {"time": ["2020-01-01", "2020-01-02", "2020-01-03"], "temperature_2m_mean": [10.0, None, 12.0]}}
    history = api.parse_history(payload)
    assert len(history) == 2


def test_parse_owid_adds_missing_columns():
    frame = pd.DataFrame({"country": ["India"], "year": [2023], "co2": [3000.0]})
    parsed = api.parse_owid(frame)
    assert list(parsed.columns) == api.OWID_COLUMNS
    assert parsed["gas_co2"].isna().all()
