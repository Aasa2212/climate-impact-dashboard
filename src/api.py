import io
from datetime import date

import pandas as pd
import requests

from src import config

CURRENT_WEATHER = "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m"
DAILY_WEATHER = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,uv_index_max"
CURRENT_AIR = "us_aqi,pm2_5,pm10,nitrogen_dioxide,ozone"
HOURLY_AIR = "us_aqi,pm2_5"
OWID_COLUMNS = [
    "country",
    "year",
    "iso_code",
    "population",
    "co2",
    "co2_per_capita",
    "coal_co2",
    "oil_co2",
    "gas_co2",
    "cement_co2",
]


def get(url, params=None):
    response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response


def numeric(values):
    return pd.to_numeric(pd.Series(values), errors="coerce")


def search_city(name):
    params = {"name": name, "count": 5, "language": "en", "format": "json"}
    payload = get(config.GEOCODING_URL, params).json()
    return [
        {
            "name": item["name"],
            "region": item.get("admin1", ""),
            "country": item.get("country", ""),
            "latitude": item["latitude"],
            "longitude": item["longitude"],
        }
        for item in payload.get("results", [])
    ]


def parse_daily_forecast(payload):
    daily = payload["daily"]
    return pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_max": numeric(daily["temperature_2m_max"]),
            "temp_min": numeric(daily["temperature_2m_min"]),
            "precipitation": numeric(daily["precipitation_sum"]),
            "wind_max": numeric(daily["wind_speed_10m_max"]),
            "uv_index": numeric(daily["uv_index_max"]),
        }
    )


def fetch_forecast(latitude, longitude, days):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_WEATHER,
        "daily": DAILY_WEATHER,
        "timezone": "auto",
        "forecast_days": days,
    }
    payload = get(config.FORECAST_URL, params).json()
    return {"current": payload["current"], "daily": parse_daily_forecast(payload)}


def parse_hourly_air(payload):
    hourly = payload["hourly"]
    return pd.DataFrame(
        {
            "time": pd.to_datetime(hourly["time"]),
            "us_aqi": numeric(hourly["us_aqi"]),
            "pm2_5": numeric(hourly["pm2_5"]),
        }
    )


def fetch_air_quality(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_AIR,
        "hourly": HOURLY_AIR,
        "timezone": "auto",
        "forecast_days": 5,
    }
    payload = get(config.AIR_QUALITY_URL, params).json()
    return {"current": payload["current"], "hourly": parse_hourly_air(payload)}


def parse_history(payload):
    daily = payload["daily"]
    history = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_mean": numeric(daily["temperature_2m_mean"]),
        }
    )
    return history.dropna().reset_index(drop=True)


def fetch_history(latitude, longitude):
    last_full_year = date.today().year - 1
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": f"{config.HISTORY_START_YEAR}-01-01",
        "end_date": f"{last_full_year}-12-31",
        "daily": "temperature_2m_mean",
        "timezone": "auto",
    }
    payload = get(config.ARCHIVE_URL, params).json()
    return parse_history(payload)


def parse_noaa_co2(text):
    raw = pd.read_csv(
        io.StringIO(text),
        comment="#",
        sep=r"\s+",
        header=None,
        usecols=[0, 1, 2, 3, 4],
        names=["year", "month", "decimal_year", "ppm", "trend"],
    )
    valid = raw[(raw["ppm"] > 0) & (raw["trend"] > 0)].copy()
    valid["date"] = pd.to_datetime(valid[["year", "month"]].assign(day=1))
    return valid[["date", "decimal_year", "ppm", "trend"]].reset_index(drop=True)


def fetch_co2_record():
    return parse_noaa_co2(get(config.NOAA_CO2_URL).text)


def parse_owid(frame):
    return frame.reindex(columns=OWID_COLUMNS)


def fetch_emissions():
    text = get(config.OWID_CO2_URL).text
    frame = pd.read_csv(io.StringIO(text), usecols=lambda column: column in OWID_COLUMNS)
    return parse_owid(frame)
