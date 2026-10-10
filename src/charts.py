import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import processing

INK = "#12343b"
TEAL = "#00798c"
HEAT = "#d1495b"
COOL = "#2e86ab"
MUTED = "#8d99ae"
SAND = "#edae49"
LEAF = "#6a994e"

AQI_COLORS = [
    (0, 50, LEAF),
    (50, 100, SAND),
    (100, 150, "#f4845f"),
    (150, 500, HEAT),
]

SOURCE_LABELS = {
    "coal_co2": ("Coal", INK),
    "oil_co2": ("Oil", COOL),
    "gas_co2": ("Gas", SAND),
    "cement_co2": ("Cement", MUTED),
}


def style(fig, title, height=380, legend=True):
    fig.update_layout(
        title=title,
        height=height,
        template="plotly_white",
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
        showlegend=legend,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def forecast_chart(daily):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=daily["date"], y=daily["precipitation"], name="Rain (mm)", marker_color=COOL, opacity=0.35),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(x=daily["date"], y=daily["temp_max"], name="High (°C)", line=dict(color=HEAT, width=3)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=daily["date"], y=daily["temp_min"], name="Low (°C)", line=dict(color=TEAL, width=3)),
        secondary_y=False,
    )
    fig.update_yaxes(title_text="Temperature (°C)", secondary_y=False)
    fig.update_yaxes(title_text="Rain (mm)", showgrid=False, secondary_y=True)
    return style(fig, "Daily temperature and rain")


def anomaly_bars(x, values, title):
    colors = [HEAT if value >= 0 else COOL for value in values]
    fig = go.Figure(go.Bar(x=x, y=values, marker_color=colors, name="Anomaly"))
    fig.update_yaxes(title_text="°C vs normal")
    return style(fig, title, legend=False)


def forecast_anomaly_chart(daily):
    return anomaly_bars(daily["date"], daily["anomaly"], "Forecast vs the 1991-2020 normal for each day")


def yearly_anomaly_chart(yearly, fitted):
    fig = anomaly_bars(yearly["year"], yearly["anomaly"], "Yearly temperature vs the 1991-2020 average")
    fig.add_trace(go.Scatter(x=yearly["year"], y=fitted, name="Linear trend", line=dict(color=INK, width=3, dash="dash")))
    fig.update_layout(showlegend=True)
    return fig


def aqi_chart(hourly):
    top = max(160, hourly["us_aqi"].max() * 1.1)
    fig = go.Figure()
    for low, high, color in AQI_COLORS:
        fig.add_hrect(y0=low, y1=high, fillcolor=color, opacity=0.12, line_width=0)
    fig.add_trace(go.Scatter(x=hourly["time"], y=hourly["us_aqi"], name="US AQI", line=dict(color=INK, width=2)))
    fig.update_yaxes(range=[0, top], title_text="US AQI")
    return style(fig, "Air quality over the next 5 days", legend=False)


def co2_chart(co2):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=co2["date"], y=co2["ppm"], name="Monthly average", line=dict(color=MUTED, width=1)))
    fig.add_trace(go.Scatter(x=co2["date"], y=co2["trend"], name="Seasonally adjusted", line=dict(color=HEAT, width=3)))
    fig.update_yaxes(title_text="CO₂ (ppm)")
    return style(fig, "Atmospheric CO₂ at Mauna Loa")


def emissions_history_chart(series, country):
    fig = go.Figure(
        go.Scatter(x=series["year"], y=series["co2"], fill="tozeroy", line=dict(color=TEAL, width=2), name=country)
    )
    fig.update_yaxes(title_text="Million tonnes CO₂")
    return style(fig, f"{country}: yearly CO₂ emissions", legend=False)


def per_capita_chart(series, world_series, country):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["year"], y=series["co2_per_capita"], name=country, line=dict(color=TEAL, width=3)))
    fig.add_trace(go.Scatter(x=world_series["year"], y=world_series["co2_per_capita"], name="World", line=dict(color=MUTED, width=2)))
    fig.update_yaxes(title_text="Tonnes CO₂ per person")
    return style(fig, f"{country} vs the world: emissions per person")


def source_mix_chart(series, country):
    available = series.dropna(subset=processing.SOURCE_COLUMNS, how="all")
    if available.empty:
        return None
    fig = go.Figure()
    for column, (label, color) in SOURCE_LABELS.items():
        fig.add_trace(
            go.Scatter(x=available["year"], y=available[column], name=label, stackgroup="one", line=dict(width=0.5, color=color))
        )
    fig.update_yaxes(title_text="Million tonnes CO₂")
    return style(fig, f"{country}: where the CO₂ comes from")


def top_emitters_chart(top, highlight, year):
    ordered = top.sort_values("co2")
    colors = [HEAT if name == highlight else MUTED for name in ordered["country"]]
    fig = go.Figure(go.Bar(x=ordered["co2"], y=ordered["country"], orientation="h", marker_color=colors))
    fig.update_xaxes(title_text="Million tonnes CO₂")
    fig.update_layout(hovermode="closest")
    return style(fig, f"Ten largest emitters in {year}", height=420, legend=False)
