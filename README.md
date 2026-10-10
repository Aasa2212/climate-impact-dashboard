# Climate Impact Dashboard

A live dashboard that answers one question for any city in the world: what is the climate doing here, right now and over the next two weeks, and how does it connect to global carbon emissions?

Built with Python, pandas, Plotly and Streamlit. Every number comes from a free public source. No API keys are needed.

## What it shows

| Tab | What you get |
|---|---|
| Right now | Temperature, feels-like, humidity, wind, rain, US AQI, PM2.5, PM10, NO₂, ozone, plus a 5-day air quality forecast with health advice |
| Weather ahead | Up to 16 days of forecast, each day compared with the 1991-2020 normal for that calendar day, and an extreme weather watch (extreme heat, unusual warmth, heavy rain, strong wind, high UV) |
| Long-term warming | Yearly temperature anomaly for the chosen city since 1981 with a fitted warming trend in °C per decade |
| Carbon emissions | Monthly atmospheric CO₂ at Mauna Loa, and for any country: yearly emissions, share of the world total, emissions per person against the world average, fuel source mix and the ten largest emitters |

## Data sources

| Source | Used for | Refresh |
|---|---|---|
| Open-Meteo Forecast API | Current weather and 16-day forecast | 15 minutes |
| Open-Meteo Air Quality API | Current and forecast pollutants, US AQI | 15 minutes |
| Open-Meteo Archive API (ERA5 reanalysis) | Daily temperatures since 1981 | Daily |
| Open-Meteo Geocoding API | City search | 15 minutes |
| NOAA Global Monitoring Laboratory | Monthly CO₂ at Mauna Loa | Daily check, new data monthly |
| Our World in Data CO₂ dataset | National CO₂ emissions and fuel sources | Daily check, new data yearly |

## Project layout

```
app.py                  Streamlit interface and page layout
src/config.py          URLs, thresholds and cache settings in one place
src/api.py             Fetching and parsing for every data source
src/processing.py      Analysis: normals, anomalies, trends, alerts, emissions
src/charts.py          Plotly figures
tests/                 Unit tests and a full-app smoke test
.github/workflows/     Runs the tests on every push
```

## Run it on Windows

1. Install Python 3.12 from python.org. Tick "Add python.exe to PATH" in the installer.
2. Open the project folder in File Explorer, click the address bar, type `powershell` and press Enter.
3. Create a virtual environment:
   ```
   python -m venv .venv
   ```
4. Activate it:
   ```
   .venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and retry.
5. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
6. Start the dashboard:
   ```
   streamlit run app.py
   ```
   It opens at http://localhost:8501.

Run the tests with `pytest`.

## Deploy it free

1. Push the repository to GitHub.
2. Sign in at share.streamlit.io with your GitHub account.
3. Choose the repository, set the main file to `app.py` and deploy.
4. Add the live link to the top of this README and to your resume.

## Method notes

- **Normals.** For each calendar day, the mean temperature across 1991-2020 is smoothed with a 7-day circular window so one odd year does not distort a day. The forecast anomaly is the forecast daily mean minus this normal.
- **Warming trend.** Full years only (at least 350 days of data) are compared with the 1991-2020 average, then a least-squares line gives the trend per decade.
- **CO₂ growth.** The yearly rise compares the latest month with the same month a year earlier, which removes the seasonal cycle.
- **Alert thresholds.** Extreme heat at 40 °C or more, unusual warmth at 5 °C above normal, heavy rain at 64.5 mm a day, strong wind at 50 km/h, high UV at index 8. All live in `src/config.py`.

## Limitations

- The forecast daily mean is the average of the high and low, while the ERA5 daily mean averages 24 hourly values. This can add a small bias to the anomaly of a few tenths of a degree.
- ERA5 is a roughly 25 km grid model, so city temperatures are smoothed compared with a single weather station.
- There is no free global feed of real-time emissions. The most current carbon signal is the monthly atmospheric CO₂ record. National emissions are annual and lag by about a year.
- Heat thresholds are fixed numbers, so they suit hot cities better than mild ones. The anomaly alert covers that gap.

## Ideas to extend it

- Add a city comparison view
- Pull live electricity grid carbon intensity for regions that publish it
- Store daily snapshots in a database to track forecast accuracy over time

## Credits

Weather data by Open-Meteo.com (CC BY 4.0). CO₂ data from NOAA GML. Emissions data from Our World in Data (CC BY).
