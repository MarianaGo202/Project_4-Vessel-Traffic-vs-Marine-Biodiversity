import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.plot import show

from config import IUCN_WEIGHT, IUCN_STATUS, OUTPUT_DIR, RASTER_CRS, raster_path

YEAR = 2023
TOP_N_CRITICAL = 15

def compute_criticality(df):
    # Normalize traffic to 0-1 so it's comparable across species regardless
    # of the raw traffic units.
    traffic = df["traffic_buffer_mean"]
    traffic_norm = (traffic - traffic.min()) / (traffic.max() - traffic.min())

    weight = df["especie_normalizada"].map(IUCN_STATUS).map(IUCN_WEIGHT)

    df = df.copy()
    df["iucn_status"] = df["especie_normalizada"].map(IUCN_STATUS)
    df["traffic_normalized"] = traffic_norm
    df["criticality_score"] = traffic_norm * weight
    return df

def main():
    df = pd.read_csv(OUTPUT_DIR / "spatial_overlay_2023.csv")
    df = df.dropna(subset=["traffic_buffer_mean"])
    df = compute_criticality(df)

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["decimalLongitude"], df["decimalLatitude"]),
        crs="EPSG:4326",
    ).to_crs(RASTER_CRS)

    gdf = gdf.sort_values("criticality_score", ascending=False)
    gdf["is_critical"] = False
    gdf.iloc[:TOP_N_CRITICAL, gdf.columns.get_loc("is_critical")] = True

    print(f"Top {TOP_N_CRITICAL} most critical points (high traffic + high conservation concern):")
    print(gdf[gdf["is_critical"]][
        ["especie_normalizada", "iucn_status", "traffic_buffer_mean", "criticality_score"]
    ].to_string(index=False))

    raster_file = raster_path(YEAR)
    with rasterio.open(raster_file) as src:
        fig, ax = plt.subplots(figsize=(12, 10))

        # Background: traffic density raster, log-scaled for visibility
        # (traffic density is extremely skewed: mostly near-zero, with a
        # few very high-traffic shipping lanes).
        data = src.read(1)
        data_masked = np.ma.masked_equal(data, src.nodata)
        show(np.log1p(data_masked), transform=src.transform, ax=ax, cmap="Blues")

        # Non-critical points, colored by species
        species_list = gdf["especie_normalizada"].unique()
        cmap = plt.get_cmap("tab10")
        for i, species in enumerate(species_list):
            subset = gdf[(gdf["especie_normalizada"] == species) & (~gdf["is_critical"])]
            subset.plot(ax=ax, markersize=10, color=cmap(i), alpha=0.4, label=species)

        # Critical points: highlighted regardless of species, sized by score
        critical = gdf[gdf["is_critical"]]
        ax.scatter(
            critical.geometry.x, critical.geometry.y,
            s=80 + 200 * critical["criticality_score"],
            facecolors="none", edgecolors="red", linewidths=2,
            label=f"Critical (top {TOP_N_CRITICAL})", zorder=5,
        )

        ax.set_title(
            f"Threatened/vulnerable species vs. shipping traffic ({YEAR})\n"
            "Red circles = highest traffic x conservation-risk combination"
        )
        ax.legend(fontsize=8, loc="upper left")
        ax.set_axis_off()

    out_path = OUTPUT_DIR / "critical_points_map.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    print(f"\nSaved map: {out_path}")

    gdf[gdf["is_critical"]].drop(columns="geometry").to_csv(
        OUTPUT_DIR / "critical_points.csv", index=False
    )

if __name__ == "__main__":
    main()