import numpy as np
import pandas as pd

from src import config

AQI_BANDS = [
    (50, "Good"),
    (100, "Moderate"),
    (150, "Unhealthy for sensitive groups"),
    (200, "Unhealthy"),
    (300, "Very unhealthy"),
]

AQI_ADVICE = {
    "Good": "Air quality is fine for outdoor activity.",
    "Moderate": "Acceptable for most people. Unusually sensitive people may want to limit long outdoor effort.",
    "Unhealthy for sensitive groups": "Children, older adults and people with asthma should cut back on heavy outdoor activity.",
    "Unhealthy": "Everyone should reduce prolonged outdoor exertion. A mask helps outdoors.",
    "Very unhealthy": "Avoid outdoor exercise and keep windows closed if possible.",
    "Hazardous": "Stay indoors and use an air purifier if you have one.",
}

SOURCE_COLUMNS = ["coal_co2", "oil_co2", "gas_co2", "cement_co2"]


def format_value(value, unit="", digits=0):
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:,.{digits}f}{unit}"


def aqi_category(value):
    if value is None or pd.isna(value):
        return "Unknown"
    for upper_limit, label in AQI_BANDS:
        if value <= upper_limit:
            return label
    return "Hazardous"


def aqi_advice(category):
    return AQI_ADVICE.get(category, "")


def daily_normals(history):
    years = history["date"].dt.year
    baseline = history[years.between(config.BASELINE_START_YEAR, config.BASELINE_END_YEAR)]
    day_key = baseline["date"].dt.strftime("%m-%d")
    normals = baseline.groupby(day_key)["temp_mean"].mean().sort_index()
    padded = pd.concat([normals.iloc[-3:], normals, normals.iloc[:3]])
    return padded.rolling(7, center=True).mean().iloc[3:-3]


def prepare_forecast(daily, history=None):
    result = daily.copy()
    result["temp_mean"] = (result["temp_max"] + result["temp_min"]) / 2
    if history is None:
        result["normal_temp"] = np.nan
    else:
        normals = daily_normals(history)
        result["normal_temp"] = result["date"].dt.strftime("%m-%d").map(normals)
    result["anomaly"] = result["temp_mean"] - result["normal_temp"]
    return result


def build_alerts(daily):
    records = []
    for row in daily.itertuples():
        if row.temp_max >= config.EXTREME_HEAT_C:
            records.append((row.date, "Extreme heat", f"High of {row.temp_max:.1f} °C"))
        if row.anomaly >= config.WARM_ANOMALY_C:
            records.append((row.date, "Warmer than normal", f"{row.anomaly:+.1f} °C above the usual"))
        if row.precipitation >= config.HEAVY_RAIN_MM:
            records.append((row.date, "Heavy rain", f"{row.precipitation:.0f} mm expected"))
        if row.wind_max >= config.STRONG_WIND_KMH:
            records.append((row.date, "Strong wind", f"Gusts up to {row.wind_max:.0f} km/h"))
        if row.uv_index >= config.HIGH_UV_INDEX:
            records.append((row.date, "High UV", f"UV index {row.uv_index:.0f}"))
    return pd.DataFrame(records, columns=["date", "alert", "detail"])


def yearly_anomalies(history):
    years = history["date"].dt.year
    yearly = history.groupby(years).agg(
        avg_temp=("temp_mean", "mean"),
        days=("temp_mean", "count"),
    )
    yearly = yearly[yearly["days"] >= config.MIN_DAYS_PER_YEAR]
    baseline = yearly.loc[config.BASELINE_START_YEAR : config.BASELINE_END_YEAR, "avg_temp"].mean()
    yearly["anomaly"] = yearly["avg_temp"] - baseline
    return yearly.rename_axis("year").reset_index()


def fit_trend(yearly):
    slope, intercept = np.polyfit(yearly["year"], yearly["anomaly"], 1)
    fitted = slope * yearly["year"] + intercept
    return slope * 10, fitted


def yearly_co2_growth(co2):
    latest = co2.iloc[-1]
    same_month_last_year = co2[co2["date"] == latest["date"] - pd.DateOffset(years=1)]
    if same_month_last_year.empty:
        return None
    return float(latest["ppm"] - same_month_last_year["ppm"].iloc[0])


def real_countries(emissions):
    rows = emissions.dropna(subset=["iso_code", "co2"])
    return rows[~rows["iso_code"].str.startswith("OWID")]


def country_list(emissions):
    return sorted(real_countries(emissions)["country"].unique())


def country_series(emissions, country):
    rows = emissions[emissions["country"] == country].dropna(subset=["co2"])
    return rows.sort_values("year").reset_index(drop=True)


def emissions_snapshot(emissions, country):
    series = country_series(emissions, country)
    world = country_series(emissions, "World")
    if series.empty or world.empty:
        return None
    latest = series.iloc[-1]
    world_row = world[world["year"] == latest["year"]]
    if world_row.empty:
        return None
    world_row = world_row.iloc[0]
    return {
        "year": int(latest["year"]),
        "total_mt": latest["co2"],
        "per_capita": latest["co2_per_capita"],
        "world_per_capita": world_row["co2_per_capita"],
        "world_share_pct": latest["co2"] / world_row["co2"] * 100,
    }


def top_emitters(emissions, year, count=10):
    rows = real_countries(emissions)
    rows = rows[rows["year"] == year]
    return rows.nlargest(count, "co2")[["country", "co2"]].reset_index(drop=True)
