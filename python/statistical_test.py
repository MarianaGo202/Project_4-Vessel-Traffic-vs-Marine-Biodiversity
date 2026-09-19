import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from scipy import stats
from shapely.geometry import box

from config import GRID_CELL_SIZE_M, OUTPUT_DIR, RASTER_CRS, raster_path

YEAR = 2023

INPUT_FILE = OUTPUT_DIR / "tables" / "spatial_overlay_2023.csv"

def build_grid(bounds, cell_size):
    minx, miny, maxx, maxy = bounds

    xs = np.arange(minx, maxx, cell_size)
    ys = np.arange(miny, maxy, cell_size)

    cells = [
        box(x, y, x + cell_size, y + cell_size)
        for x in xs
        for y in ys
    ]

    return gpd.GeoDataFrame(
        {"geometry": cells},
        crs=RASTER_CRS
    )

def mean_traffic_per_cell(grid, raster_file):
    means = []

    with rasterio.open(raster_file) as src:
        nodata = src.nodata

        for geom in grid.geometry:
            window = src.window(*geom.bounds)
            window = window.round_offsets().round_lengths()

            data = src.read(1, window=window)

            if nodata is not None:
                valid = data[data != nodata]
            else:
                valid = data

            valid = valid[np.isfinite(valid)]

            if valid.size > 0:
                means.append(float(valid.mean()))
            else:
                means.append(np.nan)

    grid = grid.copy()
    grid["mean_traffic"] = means

    return grid

def occurrences_per_cell(grid, points_gdf):
    grid_with_id = grid.copy()
    grid_with_id["cell_id"] = grid_with_id.index

    joined = gpd.sjoin(
        points_gdf,
        grid_with_id[["cell_id", "geometry"]],
        how="left",
        predicate="within"
    )

    counts = joined.groupby("cell_id").size()

    grid = grid.copy()

    grid["n_occurrences"] = (
        grid.index.map(counts)
        .fillna(0)
        .astype(int)
    )

    return grid


def main():
    print("Input file:")
    print(INPUT_FILE)
    print()

    if not INPUT_FILE.exists():
        print("ERROR: spatial_overlay_2023.csv was not found.")
        print()
        print("Expected location:")
        print(INPUT_FILE)
        return

    points = pd.read_csv(INPUT_FILE)

    print(f"Occurrences loaded: {len(points)}")

    points_gdf = gpd.GeoDataFrame(
        points,
        geometry=gpd.points_from_xy(
            points["decimalLongitude"],
            points["decimalLatitude"]
        ),
        crs="EPSG:4326"
    ).to_crs(RASTER_CRS)

    print("Building grid...")

    grid = build_grid(
        points_gdf.total_bounds,
        GRID_CELL_SIZE_M
    )

    print(f"Grid cells created: {len(grid)}")

    print("Calculating mean vessel traffic...")

    grid = mean_traffic_per_cell(
        grid,
        raster_path(YEAR)
    )

    print("Counting species occurrences...")

    grid = occurrences_per_cell(
        grid,
        points_gdf
    )

    grid_valid = grid.dropna(
        subset=["mean_traffic"]
    ).copy()

    if len(grid_valid) < 2:
        print("ERROR: Not enough valid grid cells for statistical analysis.")
        return

    rho, p_value = stats.spearmanr(
        grid_valid["mean_traffic"],
        grid_valid["n_occurrences"]
    )

    print()
    print(
        f"Grid cells analyzed: {len(grid_valid)} "
        f"({GRID_CELL_SIZE_M / 1000:.0f} km cells)"
    )

    print(
        f"Spearman correlation: "
        f"rho = {rho:.3f}, "
        f"p = {p_value:.4f}"
    )

    if p_value < 0.05:
        direction = "positive" if rho > 0 else "negative"

        print(
            f"Statistically significant {direction} relationship "
            f"(alpha = 0.05)."
        )
    else:
        print("Not statistically significant at alpha = 0.05.")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    tables_dir = OUTPUT_DIR / "tables"
    tables_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    csv_output = (
        tables_dir /
        "grid_traffic_vs_occurrences.csv"
    )

    grid_valid.drop(
        columns="geometry"
    ).to_csv(
        csv_output,
        index=False
    )

    print()
    print(f"Saved data: {csv_output}")

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.scatter(
        grid_valid["mean_traffic"],
        grid_valid["n_occurrences"],
        alpha=0.5
    )

    if len(grid_valid) > 1:

        slope, intercept, r_value, p_regression, std_err = (
            stats.linregress(
                grid_valid["mean_traffic"],
                grid_valid["n_occurrences"]
            )
        )

        x_min = grid_valid["mean_traffic"].min()
        x_max = grid_valid["mean_traffic"].max()

        x_line = np.linspace(
            x_min,
            x_max,
            100
        )

        y_line = (
            slope * x_line +
            intercept
        )

        ax.plot(
            x_line,
            y_line,
            color="red",
            linestyle="--"
        )

    ax.set_xlabel(
        "Mean vessel traffic density per grid cell"
    )

    ax.set_ylabel(
        "Species occurrences per grid cell"
    )

    ax.set_title(
        f"Vessel Traffic vs Marine Species Occurrences ({YEAR})\n"
        f"Spearman rho = {rho:.3f}, p = {p_value:.4f}"
    )

    fig.tight_layout()

    figures_dir = OUTPUT_DIR / "figures"
    figures_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    plot_output = (
        figures_dir /
        "traffic_vs_occurrences_scatter.png"
    )

    fig.savefig(
        plot_output,
        dpi=150
    )

    plt.close()

    print(
        f"Saved plot: {plot_output}"
    )


if __name__ == "__main__":
    main()