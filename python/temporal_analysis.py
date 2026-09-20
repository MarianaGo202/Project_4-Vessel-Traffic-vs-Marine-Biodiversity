import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

from config import (
    OBIS_TEMPORAL_FILTERED,
    OUTPUT_DIR,
    RASTER_CRS,
    RASTER_YEARS,
    raster_path,
)

# Study region bounding box in lon/lat (WGS84), matching the OBIS query area,
# capped at 68N to match raster coverage.
STUDY_BBOX_WGS84 = dict(lon_min=-25, lon_max=32, lat_min=55, lat_max=68)

def regional_mean_traffic(raster_file, bbox_wgs84):
    with rasterio.open(raster_file) as src:
        transformer = Transformer.from_crs("EPSG:4326", RASTER_CRS, always_xy=True)
        x_min, y_min = transformer.transform(bbox_wgs84["lon_min"], bbox_wgs84["lat_min"])
        x_max, y_max = transformer.transform(bbox_wgs84["lon_max"], bbox_wgs84["lat_max"])

        window = from_bounds(x_min, y_min, x_max, y_max, transform=src.transform)
        data = src.read(1, window=window)
        valid = data[data != src.nodata]
        return float(valid.mean()) if valid.size else np.nan

def sample_point_value(src, x, y, nodata):
    value = next(src.sample([(x, y)]))[0]
    return np.nan if value == nodata else float(value)

def main():
    df = pd.read_csv(OBIS_TEMPORAL_FILTERED)

    species_year_rows = []
    regional_rows = []

    for year in RASTER_YEARS:
        raster_file = raster_path(year)
        
        # regional mean traffic for this year
        regional_rows.append({
            "year": year,
            "regional_mean_traffic": regional_mean_traffic(raster_file, STUDY_BBOX_WGS84),
        })

        # traffic at occurrence points for this year
        df_year = df[df["date_year"] == year]
        if df_year.empty:
            continue

        gdf_year = gpd.GeoDataFrame(
            df_year,
            geometry=gpd.points_from_xy(df_year["decimalLongitude"], df_year["decimalLatitude"]),
            crs="EPSG:4326",
        ).to_crs(RASTER_CRS)

        with rasterio.open(raster_file) as src:
            nodata = src.nodata
            gdf_year = gdf_year.copy()
            gdf_year["traffic_at_point"] = [
                sample_point_value(src, geom.x, geom.y, nodata) for geom in gdf_year.geometry
            ]

        summary = (
            gdf_year.groupby("especie_normalizada")
            .agg(n_occurrences=("id", "count"), mean_traffic_at_point=("traffic_at_point", "mean"))
            .reset_index()
        )
        summary["year"] = year
        species_year_rows.append(summary)

    species_year_df = pd.concat(species_year_rows, ignore_index=True)
    regional_df = pd.DataFrame(regional_rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    species_year_df.to_csv(OUTPUT_DIR / "temporal_species_by_year.csv", index=False)
    regional_df.to_csv(OUTPUT_DIR / "temporal_regional_traffic.csv", index=False)

    print("Species x year summary:")
    print(species_year_df)
    print()
    print("Regional traffic by year:")
    print(regional_df)

    plot_trends(species_year_df, regional_df)

def plot_trends(species_year_df, regional_df):
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    for species, group in species_year_df.groupby("especie_normalizada"):
        axes[0].plot(group["year"], group["n_occurrences"], marker="o", label=species)
    axes[0].set_ylabel("OBIS occurrences per year")
    axes[0].set_title("Species occurrences vs. regional shipping traffic (2017-2024)")
    axes[0].legend(fontsize=8)

    axes[1].plot(regional_df["year"], regional_df["regional_mean_traffic"], marker="o", color="black")
    axes[1].set_ylabel("Mean traffic density\n(hours/km2/year)")
    axes[1].set_xlabel("Year")

    fig.tight_layout()
    out_path = OUTPUT_DIR / "temporal_trends.png"
    fig.savefig(out_path, dpi=150)
    print(f"\nSaved plot: {out_path}")

if __name__ == "__main__":
    main()
