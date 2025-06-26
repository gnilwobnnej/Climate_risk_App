import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from branca.colormap import linear

st.set_page_config(layout="wide")
st.title("Climate Risk Map Longview, WA Area")

# Load GeoJSON data
@st.cache_data
def load_data():
    return gpd.read_file("outputs/longview_climate_risk.geojson")

gdf = load_data()

# Color scale based on climate risk
colormap = linear.YlOrRd_09.scale(gdf["climate_risk_index"].min(), gdf["climate_risk_index"].max())
colormap.caption = "Climate Risk Index (Flood, Wildfire, Heat)"

# Create Folium map
m = folium.Map(location=[46.15, -122.96], zoom_start=9, tiles="CartoDB positron")

def style_function(feature):
    risk = feature["properties"]["climate_risk_index"]
    return {
        "fillOpacity": 0.7,
        "weight": 0.5,
        "color": "gray",
        "fillColor": colormap(risk)
    }

# Add GeoJSON layer
folium.GeoJson(
    gdf,
    name="Climate Risk",
    style_function=style_function,
    tooltip=folium.features.GeoJsonTooltip(
        fields=["ZCTA5CE20", "climate_risk_index"],
        aliases=["ZIP Code", "Risk Score"],
        localize=True
    )
).add_to(m)

colormap.add_to(m)

# Render Map
st_data = st_folium(m, width=1000, height=600)