import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import pandas as pd
import os

#  Configuration and creates an output directory if it doesn't exist. 
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading shapefiles and raster data...")

# Loads all us counties and coverts them to web mercator EPSG:3857 
# clips Cowlitz County, washington fips 53015
county_all = gpd.read_file("data/county/tl_2022_us_county.shp").to_crs("EPSG:3857")
county = county_all[(county_all["STATEFP"] == "53") & (county_all["COUNTYFP"] == "015")]

# Loads ZIP Code Tabulation Areas (ZCTAs) and flood hazard zones, reprojected to EPSG:3857.
zcta = gpd.read_file("data/zcta/tl_2020_us_zcta520.shp").to_crs("EPSG:3857")
flood = gpd.read_file("data/flood/S_FLD_HAZ_AR.shp", layer="S_Fld_Haz_Ar").to_crs("EPSG:3857")

# Clean geometries and clip/ removes invalid geometries
county = county[county.is_valid]
flood = flood[flood.is_valid]

# clips both flood and zcta layers to the bounding box of cowlitz county
minx, miny, maxx, maxy = county.total_bounds
flood = flood.cx[minx:maxx, miny:maxy]
zcta_clip = gpd.clip(zcta, county)
flood_clip = gpd.clip(flood, county)

#  Flood Risk (% Area Overlap) 
print("Calculating flood risk...")
#cleans ZCTA geometries to ensure they are usable for spatial operations.
zcta_clip = zcta_clip[~zcta_clip.geometry.is_empty & zcta_clip.geometry.notna()]
zcta_clip["geometry"] = zcta_clip["geometry"].buffer(0)
zcta_clip["geometry"] = zcta_clip["geometry"].apply(lambda g: g if g.geom_type == "Polygon" else g.convex_hull)

#Same cleaning, but for flood zones.
flood_clip = flood_clip[~flood_clip.geometry.is_empty & flood_clip.geometry.notna()]
flood_clip["geometry"] = flood_clip["geometry"].buffer(0)
flood_clip["geometry"] = flood_clip["geometry"].apply(lambda g: g if g.geom_type == "Polygon" else g.convex_hull)

#calculates intersected areas between zips and flood zone
flood_join = gpd.overlay(zcta_clip, flood_clip, how="intersection")

#computes area of intersected flood zones and the full zcta
flood_join["flood_area"] = flood_join.geometry.area
zcta_clip["zcta_area"] = zcta_clip.geometry.area

#aggregates flood area per zcta and normalizes it, this gives a flood risk score 0-1
flood_sum = flood_join.groupby("ZCTA5CE20")["flood_area"].sum().reset_index()
zcta_clip = zcta_clip.merge(flood_sum, on="ZCTA5CE20", how="left")
zcta_clip["flood_area"] = zcta_clip["flood_area"].fillna(0)
zcta_clip["flood_score_norm"] = zcta_clip["flood_area"] / zcta_clip["zcta_area"]

#  Wildfire Risk 
print("Calculating wildfire risk...")

#reprojects to albers equal area (epsg5070) for area based analysis
zcta_clip = zcta_clip.to_crs("EPSG:5070")

#additional geomertry cleanup
zcta_clip = zcta_clip[zcta_clip.is_valid & zcta_clip.geometry.notnull()]
zcta_clip = zcta_clip[~zcta_clip.geometry.is_empty]

#uses zonal statistics to compute the mean wildfire hazard potential per zcta
zcta_clip["wildfire_score"] = [
    s["mean"] for s in zonal_stats(zcta_clip, "data/wildfire/WHP_WA.tif", stats="mean", nodata=255)
]

#normalizes scores from a known 0-5 scale
zcta_clip["wildfire_score_norm"] = zcta_clip["wildfire_score"] / 5.0

#  Heat Risk 
print("Calculating heat risk (LST)...")

#reprojects to utm zone 10n for accurate rasters alignments
zcta_clip = zcta_clip.to_crs("EPSG:32610")

#extracts average land surface temperature per zctra (in kelvin) and covers to C
lst_stats = zonal_stats(zcta_clip, "data/heat/lst_longview.tif", stats="mean", nodata=0)
zcta_clip["lst"] = [s["mean"] for s in lst_stats]
zcta_clip["lst_c"] = zcta_clip["lst"] - 273.15

#Normalizes temperature to 0–1 across the county.
min_temp, max_temp = zcta_clip["lst_c"].min(), zcta_clip["lst_c"].max()
zcta_clip["heat_score_norm"] = (zcta_clip["lst_c"] - min_temp) / (max_temp - min_temp)

#  Combined Climate Risk 
#Weighted average of all three risks: 40% flood, 30% wildfire, 30% heat.
print("Calculating combined climate risk index...")
zcta_clip["climate_risk_index"] = (
    zcta_clip["flood_score_norm"] * 0.4 +
    zcta_clip["wildfire_score_norm"] * 0.3 +
    zcta_clip["heat_score_norm"] * 0.3
)

#  Export Each Layer 
print("Saving GeoJSON layers for visualization...")

# Reproject to WGS84 for Folium
zcta_clip = zcta_clip.to_crs("EPSG:4326")

# Save each layer individually
zcta_clip[["geometry", "flood_score_norm"]].to_file(f"{OUTPUT_DIR}/flood_risk.geojson", driver="GeoJSON")
zcta_clip[["geometry", "wildfire_score_norm"]].to_file(f"{OUTPUT_DIR}/wildfire_risk.geojson", driver="GeoJSON")
zcta_clip[["geometry", "heat_score_norm"]].to_file(f"{OUTPUT_DIR}/heat_risk.geojson", driver="GeoJSON")
zcta_clip[["geometry", "climate_risk_index"]].to_file(f"{OUTPUT_DIR}/combined_risk.geojson", driver="GeoJSON")

# Save summary CSV (optional)
zcta_clip[["ZCTA5CE20", "climate_risk_index"]].to_csv("outputs/risk_summary.csv", index=False)

#lets everyone know its done.
print("Climate risk layers and index exported!")