from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

from src import api

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def patched_sources(monkeypatch, history, raw_forecast, emissions, co2_record, air_quality):
    monkeypatch.setattr(
        api,
        "search_city",
        lambda name: [{"name": "New Delhi", "region": "Delhi", "country": "India", "latitude": 28.6, "longitude": 77.2}],
    )
    monkeypatch.setattr(
        api,
        "fetch_forecast",
        lambda latitude, longitude, days: {
            "current": {"temperature_2m": 31.2, "apparent_temperature": 34.0, "relative_humidity_2m": 55, "wind_speed_10m": 9.4, "precipitation": 0.0},
            "daily": raw_forecast,
        },
    )
    monkeypatch.setattr(api, "fetch_air_quality", lambda latitude, longitude: air_quality)
    monkeypatch.setattr(api, "fetch_history", lambda latitude, longitude: history)
    monkeypatch.setattr(api, "fetch_co2_record", lambda: co2_record)
    monkeypatch.setattr(api, "fetch_emissions", lambda: emissions)


def test_dashboard_renders_every_section(patched_sources):
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    assert not app.exception
    assert len(app.tabs) == 4
    labels = [metric.label for metric in app.metric]
    assert "Temperature" in labels
    assert "US AQI" in labels
    assert "Warming trend" in labels
    assert "World average per person" in labels


def test_dashboard_survives_a_failed_source(patched_sources, monkeypatch):
    def broken():
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(api, "fetch_emissions", broken)
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    assert not app.exception
    assert any("country emissions" in warning.value for warning in app.warning)
