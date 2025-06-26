import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import pandas as pd

#Load Inputs 
print("Loading data.")
county_all = gpd.read_file("data/county/tl_2022_us_county.shp").to_crs("EPSG:3857")
county = county_all[(county_all["STATEFP"] == "53") & (county_all["COUNTYFP"] == "015")]
zcta = gpd.read_file("data/zcta/tl_2020_us_zcta520.shp").to_crs("EPSG:3857")
flood = gpd.read_file("data/flood/S_FLD_HAZ_AR.shp", layer="S_Fld_Haz_Ar").to_crs("EPSG:3857")

#Diagnostics 
print(f"Flood features: {flood.shape[0]}")
print(f"County features: {county.shape[0]}")
print(f"Flood CRS: {flood.crs}")
print(f"County CRS: {county.crs}")
print("Flood valid geometries:", flood.is_valid.value_counts())


#remove invalid geometries and clip to Cowlitz County 
flood = flood[flood.is_valid]
county = county[county.is_valid]

#filter flood by bounding box to speed up clip
county_bounds = county.total_bounds
flood = flood.cx[county_bounds[0]:county_bounds[2], county_bounds[1]:county_bounds[3]]

print("Clipping to Cowlitz County.")
zcta_clip = gpd.clip(zcta, county)
flood_clip = gpd.clip(flood, county)

#Calculate Flood Risk (% coverage) 
print("Calculating flood coverage.")

#Fix mixed geometry types
zcta_clip = zcta_clip[zcta_clip.geometry.notnull()]
zcta_clip["geometry"] = zcta_clip["geometry"].buffer(0)  # repair invalid geoms
zcta_clip["geometry"] = zcta_clip["geometry"].apply(lambda geom: geom if geom.geom_type == "Polygon" else geom.convex_hull)

flood_clip = flood_clip[flood_clip.geometry.notnull()]
flood_clip["geometry"] = flood_clip["geometry"].buffer(0)
flood_clip["geometry"] = flood_clip["geometry"].apply(lambda geom: geom if geom.geom_type == "Polygon" else geom.convex_hull)

flood_join = gpd.overlay(zcta_clip, flood_clip, how="intersection")
flood_join["flood_area"] = flood_join.geometry.area
zcta_clip["zcta_area"] = zcta_clip.geometry.area

flood_sum = flood_join.groupby("ZCTA5CE20")["flood_area"].sum().reset_index()
zcta_clip = zcta_clip.merge(flood_sum, on="ZCTA5CE20", how="left")
zcta_clip["flood_area"] = zcta_clip["flood_area"].fillna(0)
zcta_clip["flood_score_norm"] = zcta_clip["flood_area"] / zcta_clip["zcta_area"]

#Calculate Wildfire Score (normalized mean) 
print("Calculating wildfire risk.")

zcta_clip = zcta_clip.to_crs("EPSG:5070")
zcta_clip = zcta_clip[zcta_clip.geometry.notnull()]
zcta_clip = zcta_clip[zcta_clip.is_valid]
zcta_clip = zcta_clip[~zcta_clip.geometry.is_empty]
zcta_clip["wildfire_score"] = [
    s["mean"] for s in zonal_stats(zcta_clip, "data/wildfire/WHP_WA.tif", stats="mean", nodata=255)
]
zcta_clip["wildfire_score_norm"] = zcta_clip["wildfire_score"] / 5.0  # WHP range 0–5

#Calculate Heat Score (lst in Celsius, normalized) 
print("Calculating heat risk.")
zcta_clip = zcta_clip.to_crs("EPSG:32610")  # typical Landsat UTM zone for WA
lst_stats = zonal_stats(zcta_clip, "data/heat/lst_longview.tif", stats="mean", nodata=0)
zcta_clip["lst"] = [s["mean"] for s in lst_stats]
zcta_clip["lst_c"] = zcta_clip["lst"] - 273.15  # Kelvin to Celsius

min_temp = zcta_clip["lst_c"].min()
max_temp = zcta_clip["lst_c"].max()
zcta_clip["heat_score_norm"] = (zcta_clip["lst_c"] - min_temp) / (max_temp - min_temp)

#combine scores
print("Computing combined climate risk index...")
zcta_clip["climate_risk_index"] = (
    zcta_clip["flood_score_norm"] * 0.4 +
    zcta_clip["wildfire_score_norm"] * 0.3 +
    zcta_clip["heat_score_norm"] * 0.3
)

#Export Results 
print("Saving results...")
zcta_clip.to_file("outputs/longview_climate_risk.geojson", driver="GeoJSON")
zcta_clip[["ZCTA5CE20", "climate_risk_index"]].to_csv("outputs/risk_summary.csv", index=False)

print("Climate risk index complete and saved!")