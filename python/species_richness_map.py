import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.plot import show
from shapely.geometry import box

from config import (
    GRID_CELL_SIZE_M,
    OBIS_TEMPORAL_FILTERED,
    OUTPUT_DIR,
    RASTER_CRS,
    raster_path,
)

YEAR_FOR_BACKGROUND = 2023  # just for the map background, not the data

def build_grid(bounds, cell_size):
    minx, miny, maxx, maxy = bounds
    xs = np.arange(minx, maxx, cell_size)
    ys = np.arange(miny, maxy, cell_size)
    cells = [box(x, y, x + cell_size, y + cell_size) for x in xs for y in ys]
    return gpd.GeoDataFrame({"geometry": cells}, crs=RASTER_CRS)

def main():
    df = pd.read_csv(OBIS_TEMPORAL_FILTERED)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["decimalLongitude"], df["decimalLatitude"]),
        crs="EPSG:4326",
    ).to_crs(RASTER_CRS)

    grid = build_grid(gdf.total_bounds, GRID_CELL_SIZE_M)
    grid = grid.reset_index().rename(columns={"index": "cell_id"})

    joined = gpd.sjoin(gdf, grid, how="left", predicate="within")
    richness = joined.groupby("cell_id")["especie_normalizada"].nunique()

    grid["richness"] = grid["cell_id"].map(richness).fillna(0).astype(int)
    grid_with_data = grid[grid["richness"] > 0]

    print(f"Grid cells with at least one species: {len(grid_with_data)}")
    print(f"Max richness in a single cell: {grid_with_data['richness'].max()}")
    print(grid_with_data.sort_values("richness", ascending=False).head(10)[["cell_id", "richness"]])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    grid_with_data.drop(columns="geometry").to_csv(
        OUTPUT_DIR / "species_richness_grid.csv", index=False
    )

    plot_richness(grid_with_data)

def plot_richness(grid_with_data):
    raster_file = raster_path(YEAR_FOR_BACKGROUND)
    with rasterio.open(raster_file) as src:
        fig, ax = plt.subplots(figsize=(12, 10))
        data = src.read(1)
        data_masked = np.ma.masked_equal(data, src.nodata)
        show(np.log1p(data_masked), transform=src.transform, ax=ax, cmap="Greys")

        grid_with_data.plot(
            column="richness", ax=ax, cmap="YlOrRd", alpha=0.75,
            edgecolor="black", linewidth=0.2, legend=True,
            legend_kwds={"label": "Species richness (count)"},
        )
        ax.set_title("Species richness (2017-2024) over shipping traffic background")
        ax.set_axis_off()

    out_path = OUTPUT_DIR / "species_richness_map.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    print(f"\nSaved map: {out_path}")


if __name__ == "__main__":
    main()
