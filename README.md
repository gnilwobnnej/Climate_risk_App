# Climate_risk_App

## README IN PROGRESS, getting better##

## Project Overview

This project analyzes and visualizes flood, wildfire, and heat risks for ZIP Code Tabulation Areas (ZCTAs) in Cowlitz County, Washington. It consists of two main components:

- A backend script to calculate normalized risk scores and export GeoJSON layers.

- An interactive Streamlit-based web app that maps each risk type and the dominant threat per area.

**Goal:**
To find the climate risks for the area in southern Washington area.

**Tools used:**
- `rasterio`- for geospatial raster (tif) image processing
- `geopandas`- for handling shapefiles
- `rasterstats`- for calculating raster values within polygons
- `pandas`- general purpose data analysis
- `os`- for filesystem operations
- `streamlit`- builds the interactive web interface.
- `streamlit_folium`- displays folium maps in Streamlit.
- `folium`- creates the interactive Leaflet-based map.

**Information used:**

## Dataset and Files
- [Heat Risk data](https://earthexplorer.usgs.gov/)
- [Flood Data](https://www.fema.gov/)
- [County Lines](https://www.census.gov/geographies/mapping-files/2020/geo/tiger-line-file.html)
- [Wild Fire](https://research.fs.usda.gov/)

## Workflow
1. Run Risk Calculation
**Script: climate_risk_v2.py** 

 `python climate_risk_v2.py`
- This script:

    - Clips data to Cowlitz County

    - Processes flood, wildfire, and heat datasets

- Generates:

    - outputs/flood_risk.geojson

    - outputs/wildfire_risk.geojson

    - outputs/heat_risk.geojson

    - outputs/combined_risk.geojson

    - outputs/risk_summary.csv

2. Launch the Interactive Map
**App: app_v2.py**

`streamlit run app_v2.py`
Features:

- Toggle layers for individual risks

- View polygons shaded by dominant risk type

- Hover for tooltip values

- Built-in map legend

## Example Output

