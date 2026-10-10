import numpy as np
import pandas as pd
import pytest

from src import processing


def test_aqi_category_edges():
    assert processing.aqi_category(50) == "Good"
    assert processing.aqi_category(51) == "Moderate"
    assert processing.aqi_category(168) == "Unhealthy"
    assert processing.aqi_category(450) == "Hazardous"
    assert processing.aqi_category(None) == "Unknown"
    assert processing.aqi_category(np.nan) == "Unknown"


def test_format_value():
    assert processing.format_value(12.345, " °C", 1) == "12.3 °C"
    assert processing.format_value(1234.6) == "1,235"
    assert processing.format_value(None) == "n/a"
    assert processing.format_value(np.nan, " mm") == "n/a"


def test_daily_normals_cover_every_calendar_day(history):
    normals = processing.daily_normals(history)
    assert len(normals) == 366
    assert normals.notna().all()


def test_prepare_forecast_adds_normal_and_anomaly(history, raw_forecast):
    prepared = processing.prepare_forecast(raw_forecast, history)
    assert prepared["temp_mean"].iloc[0] == 28.0
    assert prepared["normal_temp"].notna().all()
    assert (prepared["anomaly"] > 0).all()


def test_prepare_forecast_without_history(raw_forecast):
    prepared = processing.prepare_forecast(raw_forecast)
    assert prepared["anomaly"].isna().all()


def test_build_alerts_finds_each_hazard(history, raw_forecast):
    prepared = processing.prepare_forecast(raw_forecast, history)
    alerts = processing.build_alerts(prepared)
    counts = alerts["alert"].value_counts()
    assert counts["Extreme heat"] == 1
    assert counts["Heavy rain"] == 1
    assert counts["Strong wind"] == 1
    assert counts["High UV"] == 2
    assert counts["Warmer than normal"] >= 1


def test_build_alerts_quiet_week(raw_forecast):
    calm = raw_forecast.assign(temp_max=30.0, precipitation=0.0, wind_max=10.0, uv_index=3.0)
    alerts = processing.build_alerts(processing.prepare_forecast(calm))
    assert alerts.empty
    assert list(alerts.columns) == ["date", "alert", "detail"]


def test_yearly_anomalies_and_trend(history):
    yearly = processing.yearly_anomalies(history)
    per_decade, fitted = processing.fit_trend(yearly)
    assert per_decade == pytest.approx(0.3, abs=0.02)
    assert len(fitted) == len(yearly)
    baseline_years = yearly[yearly["year"].between(1991, 2020)]
    assert baseline_years["anomaly"].mean() == pytest.approx(0, abs=1e-9)


def test_incomplete_years_are_dropped(history):
    partial = history[history["date"] < "2025-06-01"]
    yearly = processing.yearly_anomalies(partial)
    assert 2025 not in yearly["year"].values


def test_yearly_co2_growth(co2_record):
    growth = processing.yearly_co2_growth(co2_record)
    assert growth == pytest.approx(co2_record["ppm"].iloc[-1] - co2_record["ppm"].iloc[-13])


def test_yearly_co2_growth_needs_a_year_of_data(co2_record):
    assert processing.yearly_co2_growth(co2_record.tail(5)) is None


def test_country_list_hides_aggregates(emissions):
    assert processing.country_list(emissions) == ["China", "India", "United States"]


def test_emissions_snapshot(emissions):
    snapshot = processing.emissions_snapshot(emissions, "India")
    assert snapshot["year"] == 2023
    assert snapshot["total_mt"] == 3100
    assert snapshot["world_share_pct"] == pytest.approx(3100 / 37100 * 100)
    assert snapshot["world_per_capita"] == 4.7


def test_emissions_snapshot_unknown_country(emissions):
    assert processing.emissions_snapshot(emissions, "Atlantis") is None


def test_top_emitters_ranked_without_aggregates(emissions):
    top = processing.top_emitters(emissions, 2023, count=2)
    assert list(top["country"]) == ["China", "United States"]
