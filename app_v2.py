import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd


#Loads three GeoJSON files into GeoDataFrames. Each file contains polygons with a risk score for one hazard.

flood = gpd.read_file("outputs/flood_risk.geojson")
wildfire = gpd.read_file("outputs/wildfire_risk.geojson")
heat = gpd.read_file("outputs/heat_risk.geojson")


#adds an ID column based on each row's index to help join data across layers later.

flood["id"] = flood.index
wildfire["id"] = wildfire.index
heat["id"] = heat.index

#Checks if the normalized score column exists in each dataset. If not, it throws an error.
assert "flood_score_norm" in flood.columns, "Column 'flood_score_norm' is missing"
assert "wildfire_score_norm" in wildfire.columns, "Column 'wildfire_score_norm' is missing"
assert "heat_score_norm" in heat.columns, "Column 'heat_score_norm' is missing"


#Joins the three datasets into one, combining their risk scores using the shared ID

combined = (
    flood
    .merge(wildfire[["id", "wildfire_score_norm"]], on="id")
    .merge(heat[["id", "heat_score_norm"]], on="id")
)


#For each row, determines which risk score is highest and labels it "Flood", "Wildfire", or "Heat" in a new column.


def get_dominant_risk(row):
    """Return the risk category (Flood/Wildfire/Heat) with the highest score."""
    risks = {
        "Flood": row["flood_score_norm"],
        "Wildfire": row["wildfire_score_norm"],
        "Heat": row["heat_score_norm"],
    }
    return max(risks, key=risks.get)

combined["dominant_risk"] = combined.apply(get_dominant_risk, axis=1)


# Build the interactive map

#Initializes a folium map centered on the first polygon. Uses a nice terrain-style background.
center_point = combined.geometry.iloc[0].centroid
m = folium.Map(location=[center_point.y, center_point.x], zoom_start=9, tiles="Stadia StamenTerrain")


# Individual risk layers

#Flood
flood_fg = folium.FeatureGroup(name="Flood Risk")
folium.GeoJson(
    flood,
    name="Flood Risk",
    style_function=lambda x: {
        "fillColor": "blue",
        "color": "blue",
        "weight": 1,
        "fillOpacity": 0.4,
    },
    tooltip=folium.GeoJsonTooltip(fields=["flood_score_norm"], aliases=["Flood score:"], localize=True),
).add_to(flood_fg)
flood_fg.add_to(m)

#Wildfire
wildfire_fg = folium.FeatureGroup(name="Wildfire Risk")
folium.GeoJson(
    wildfire,
    name="Wildfire Risk",
    style_function=lambda x: {
        "fillColor": "red",
        "color": "red",
        "weight": 1,
        "fillOpacity": 0.4,
    },
    tooltip=folium.GeoJsonTooltip(fields=["wildfire_score_norm"], aliases=["Wildfire score:"], localize=True),
).add_to(wildfire_fg)
wildfire_fg.add_to(m)

#Heat
heat_fg = folium.FeatureGroup(name="Heat Risk")
folium.GeoJson(
    heat,
    name="Heat Risk",
    style_function=lambda x: {
        "fillColor": "orange",
        "color": "orange",
        "weight": 1,
        "fillOpacity": 0.4,
    },
    tooltip=folium.GeoJsonTooltip(fields=["heat_score_norm"], aliases=["Heat score:"], localize=True),
).add_to(heat_fg)
heat_fg.add_to(m)


#loops through merged polygons, colors each of them, shows the dominate category.

combined_fg = folium.FeatureGroup(name="Dominant Risk Category")

risk_colors = {"Flood": "blue", "Wildfire": "red", "Heat": "orange"}

for _, row in combined.iterrows():
    dominant = row["dominant_risk"]
    color = risk_colors.get(dominant, "gray")

    folium.GeoJson(
        row["geometry"],
        style_function=lambda x, color=color: {
            "fillColor": color,
            "color": color,
            "weight": 1,
            "fillOpacity": 0.5,
        },
        tooltip=f"Dominant Risk: {dominant}",
    ).add_to(combined_fg)

combined_fg.add_to(m)


#creates a fixed position html legend box. shows what the colors mean. 

legend_html = """
<div style='position: fixed; bottom: 50px; left: 50px; width: 160px; height: 120px; 
     background-color: white; border:2px solid grey; z-index:9999; font-size:14px; padding: 10px;'>
<b>Legend</b><br>
<i style="background:blue;color:blue">__</i> Flood<br>
<i style="background:red;color:red">__</i> Wildfire<br>
<i style="background:orange;color:orange">__</i> Heat<br>
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

# layer control for toggling
folium.LayerControl().add_to(m)


#streamlit display

st.set_page_config(page_title="Climate Risk Map", layout="wide")
st.title("Climate Risk Map - With Dominant Risk")

st_folium(m, width=1000, height=600)
