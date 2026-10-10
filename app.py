import pandas as pd
import requests
import streamlit as st

from src import api, charts, config, processing

st.set_page_config(page_title="Climate Impact Dashboard", page_icon="🌍", layout="wide")

live = st.cache_data(ttl=config.LIVE_CACHE_SECONDS, show_spinner=False)
slow = st.cache_data(ttl=config.SLOW_CACHE_SECONDS, show_spinner=False)

load_cities = live(api.search_city)
load_forecast = live(api.fetch_forecast)
load_air = live(api.fetch_air_quality)
load_history = slow(api.fetch_history)
load_co2 = slow(api.fetch_co2_record)
load_emissions = slow(api.fetch_emissions)

failed_sources = []


def try_load(loader, label, *args):
    try:
        return loader(*args)
    except (requests.RequestException, KeyError, ValueError):
        failed_sources.append(label)
        return None


def place_label(place):
    parts = [place["name"], place["region"], place["country"]]
    return ", ".join(part for part in parts if part)


with st.sidebar:
    st.header("Choose a location")
    query = st.text_input("City", value=config.DEFAULT_CITY)
    matches = try_load(load_cities, "city search", query.strip()) if query.strip() else []
    if not matches:
        st.error("No city found. Check the spelling and try again.")
        st.stop()
    choice = st.selectbox("Best match", range(len(matches)), format_func=lambda i: place_label(matches[i]))
    place = matches[choice]
    forecast_days = st.slider("Forecast days", 3, config.MAX_FORECAST_DAYS, 10)
    st.button("Refresh data", on_click=st.cache_data.clear)
    st.caption("Live weather and air quality refresh every 15 minutes. Climate history and emissions refresh daily.")

latitude, longitude = place["latitude"], place["longitude"]

forecast = try_load(load_forecast, "weather forecast", latitude, longitude, forecast_days)
air = try_load(load_air, "air quality", latitude, longitude)
history = try_load(load_history, "historical temperatures", latitude, longitude)
co2 = try_load(load_co2, "NOAA CO₂ record")
emissions = try_load(load_emissions, "country emissions")

st.title(f"Climate impact in {place['name']}")
st.caption("Current conditions, the weather ahead, long-term warming and the carbon behind it.")

if failed_sources:
    st.warning(f"These sources did not respond: {', '.join(failed_sources)}. Press Refresh data to try again.")

tab_now, tab_ahead, tab_warming, tab_carbon = st.tabs(
    ["Right now", "Weather ahead", "Long-term warming", "Carbon emissions"]
)

with tab_now:
    if forecast is None:
        st.info("Current weather is unavailable right now.")
    else:
        current = forecast["current"]
        columns = st.columns(5)
        columns[0].metric("Temperature", processing.format_value(current.get("temperature_2m"), " °C", 1))
        columns[1].metric("Feels like", processing.format_value(current.get("apparent_temperature"), " °C", 1))
        columns[2].metric("Humidity", processing.format_value(current.get("relative_humidity_2m"), " %"))
        columns[3].metric("Wind", processing.format_value(current.get("wind_speed_10m"), " km/h"))
        columns[4].metric("Rain now", processing.format_value(current.get("precipitation"), " mm", 1))

    if air is None:
        st.info("Air quality is unavailable right now.")
    else:
        now_air = air["current"]
        category = processing.aqi_category(now_air.get("us_aqi"))
        columns = st.columns(5)
        columns[0].metric("US AQI", processing.format_value(now_air.get("us_aqi")))
        columns[0].caption(category)
        columns[1].metric("PM2.5", processing.format_value(now_air.get("pm2_5"), " µg/m³", 1))
        columns[2].metric("PM10", processing.format_value(now_air.get("pm10"), " µg/m³", 1))
        columns[3].metric("Nitrogen dioxide", processing.format_value(now_air.get("nitrogen_dioxide"), " µg/m³", 1))
        columns[4].metric("Ozone", processing.format_value(now_air.get("ozone"), " µg/m³", 1))
        advice = processing.aqi_advice(category)
        if advice:
            st.info(advice)
        st.plotly_chart(charts.aqi_chart(air["hourly"]))

with tab_ahead:
    if forecast is None:
        st.info("The forecast is unavailable right now.")
    else:
        daily = processing.prepare_forecast(forecast["daily"], history)
        alerts = processing.build_alerts(daily)
        columns = st.columns(3)
        columns[0].metric("Hottest day ahead", processing.format_value(daily["temp_max"].max(), " °C", 1))
        columns[1].metric("Total rain ahead", processing.format_value(daily["precipitation"].sum(), " mm"))
        columns[2].metric("Days with alerts", int(alerts["date"].nunique()))

        st.plotly_chart(charts.forecast_chart(daily))

        if daily["anomaly"].notna().any():
            st.plotly_chart(charts.forecast_anomaly_chart(daily))

        st.subheader("Extreme weather watch")
        if alerts.empty:
            st.success("No extreme heat, heavy rain, strong wind or high UV expected in this window.")
        else:
            shown = alerts.assign(date=alerts["date"].dt.strftime("%a %d %b"))
            st.dataframe(shown, hide_index=True)

        with st.expander("See the daily numbers"):
            table = daily.rename(
                columns={
                    "date": "Date",
                    "temp_max": "High °C",
                    "temp_min": "Low °C",
                    "precipitation": "Rain mm",
                    "wind_max": "Wind km/h",
                    "uv_index": "UV index",
                    "normal_temp": "Normal °C",
                    "anomaly": "Vs normal °C",
                }
            ).drop(columns=["temp_mean"])
            table["Date"] = table["Date"].dt.strftime("%a %d %b")
            st.dataframe(table.round(1), hide_index=True)

with tab_warming:
    if history is None:
        st.info("Historical temperatures are unavailable right now.")
    else:
        yearly = processing.yearly_anomalies(history)
        per_decade, fitted = processing.fit_trend(yearly)
        hottest = yearly.loc[yearly["avg_temp"].idxmax()]
        latest = yearly.iloc[-1]
        columns = st.columns(3)
        columns[0].metric("Warming trend", f"{per_decade:+.2f} °C per decade")
        columns[1].metric("Hottest year since 1981", int(hottest["year"]))
        columns[2].metric(f"{int(latest['year'])} vs 1991-2020", f"{latest['anomaly']:+.2f} °C")
        st.plotly_chart(charts.yearly_anomaly_chart(yearly, fitted))
        st.caption(
            "Based on ERA5 reanalysis for the grid cell around this city. "
            "Each bar is a full year, compared with the 1991-2020 average."
        )

with tab_carbon:
    if co2 is None:
        st.info("The CO₂ record is unavailable right now.")
    else:
        latest_co2 = co2.iloc[-1]
        growth = processing.yearly_co2_growth(co2)
        above = latest_co2["ppm"] - config.PRE_INDUSTRIAL_PPM
        columns = st.columns(3)
        columns[0].metric(
            f"CO₂ in {latest_co2['date'].strftime('%b %Y')}",
            processing.format_value(latest_co2["ppm"], " ppm", 1),
        )
        columns[1].metric("Rise over the past year", processing.format_value(growth, " ppm", 2))
        columns[2].metric("Above pre-industrial level", processing.format_value(above, " ppm", 1))
        st.plotly_chart(charts.co2_chart(co2))

    st.divider()

    if emissions is None:
        st.info("Country emissions are unavailable right now.")
    else:
        countries = processing.country_list(emissions)
        wanted = place["country"] if place["country"] in countries else config.DEFAULT_COUNTRY
        start = countries.index(wanted) if wanted in countries else 0
        country = st.selectbox("Country", countries, index=start)

        snapshot = processing.emissions_snapshot(emissions, country)
        series = processing.country_series(emissions, country)
        world_series = processing.country_series(emissions, "World")

        if snapshot is None:
            st.info("No emissions data for this country.")
        else:
            columns = st.columns(4)
            columns[0].metric(f"Emissions in {snapshot['year']}", processing.format_value(snapshot["total_mt"], " Mt"))
            columns[1].metric("Share of world total", processing.format_value(snapshot["world_share_pct"], " %", 1))
            columns[2].metric("Per person", processing.format_value(snapshot["per_capita"], " t", 1))
            columns[3].metric("World average per person", processing.format_value(snapshot["world_per_capita"], " t", 1))

            left, right = st.columns(2)
            left.plotly_chart(charts.emissions_history_chart(series, country))
            right.plotly_chart(charts.per_capita_chart(series, world_series, country))

            mix = charts.source_mix_chart(series, country)
            if mix is not None:
                st.plotly_chart(mix)

            top = processing.top_emitters(emissions, snapshot["year"])
            st.plotly_chart(charts.top_emitters_chart(top, country, snapshot["year"]))

st.divider()
st.caption(
    "Data: Open-Meteo (weather, air quality, ERA5 history), NOAA Global Monitoring Laboratory (Mauna Loa CO₂), "
    "Our World in Data (national CO₂ emissions). Emissions are reported yearly, so they lag by about a year."
)
