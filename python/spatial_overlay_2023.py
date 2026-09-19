import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from config import (
    BUFFER_RADIUS_M,
    OBIS_SPATIAL_2023_FILTERED,
    OUTPUT_DIR,
    RASTER_CRS,
    raster_path,
)

YEAR = 2023

def sample_point_value(src, x, y, nodata):
    value = next(src.sample([(x, y)]))[0]
    return np.nan if value == nodata else float(value)

def sample_buffer_mean(src, x, y, buffer_m, nodata):
    window = src.window(x - buffer_m, y - buffer_m, x + buffer_m, y + buffer_m)
    window = window.round_offsets().round_lengths()
    data = src.read(1, window=window)
    valid = data[data != nodata]
    return np.nan if valid.size == 0 else float(valid.mean())

def main():
    df = pd.read_csv(OBIS_SPATIAL_2023_FILTERED)

    # Build GeoDataFrame in WGS84 (lat/lon), then reproject to match the raster
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["decimalLongitude"], df["decimalLatitude"]),
        crs="EPSG:4326",
    )
    gdf_proj = gdf.to_crs(RASTER_CRS)

    raster_file = raster_path(YEAR)
    with rasterio.open(raster_file) as src:
        nodata = src.nodata
        point_values = []
        buffer_values = []

        for geom in gdf_proj.geometry:
            x, y = geom.x, geom.y
            point_values.append(sample_point_value(src, x, y, nodata))
            buffer_values.append(sample_buffer_mean(src, x, y, BUFFER_RADIUS_M, nodata))

    gdf_proj["traffic_at_point"] = point_values
    gdf_proj["traffic_buffer_mean"] = buffer_values

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUTPUT_DIR / "spatial_overlay_2023.csv"
    out_geojson = OUTPUT_DIR / "spatial_overlay_2023.geojson"

    gdf_proj.drop(columns="geometry").to_csv(out_csv, index=False)
    gdf_proj.to_file(out_geojson, driver="GeoJSON")

    print(f"Saved: {out_csv}")
    print(f"Saved: {out_geojson}")
    print()
    print("Mean traffic (buffer) by species:")
    print(gdf_proj.groupby("especie_normalizada")["traffic_buffer_mean"].agg(["count", "mean", "median"]))

if __name__ == "__main__":
    main()