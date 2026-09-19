import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import distance_transform_edt

from config import OUTPUT_DIR, RASTER_CRS, raster_path

YEAR = 2023

TABLES_DIR = OUTPUT_DIR / "tables"
INPUT_FILE = TABLES_DIR / "spatial_overlay_2023.csv"

# Renamed to match the filename mpa_comparison.py looks for first
# (OCCURRENCE_CANDIDATES[0]). Previously this was
# "occurrences_distance_to_shipping_lanes.csv", a name mpa_comparison.py
# never checked for, so it always fell through to looking for
# "..._with_gfw.csv" or the plain "spatial_overlay_2023.csv" instead,
# silently skipping the distance column entirely.
OUTPUT_FILE = TABLES_DIR / "spatial_overlay_2023_with_distance.csv"

BUSY_LANE_PERCENTILE = 90

def compute_busy_mask(data: np.ndarray, nodata) -> np.ndarray:
    """Flags pixels in the top BUSY_LANE_PERCENTILE of traffic density."""
    valid_mask = np.isfinite(data)
    if nodata is not None:
        valid_mask &= data != nodata

    threshold = np.percentile(data[valid_mask], BUSY_LANE_PERCENTILE)
    print(f"Busy-lane threshold (top {100 - BUSY_LANE_PERCENTILE}%): "
          f"{threshold}")

    busy_mask = valid_mask & (data >= threshold)
    print(f"Busy-lane pixels: {busy_mask.sum():,} of "
          f"{valid_mask.sum():,} valid pixels")

    return busy_mask

def compute_pixel_size_m(transform) -> float:
    """Approximate pixel size in meters, averaging width and height."""
    pixel_height = abs(transform.e)
    pixel_width = abs(transform.a)
    pixel_size_m = (pixel_width + pixel_height) / 2

    print(f"Approximate pixel size: {pixel_size_m:.2f} meters")
    return pixel_size_m

def compute_distance_surface(busy_mask: np.ndarray, pixel_size_m: float) -> np.ndarray:
    """Distance (in meters) from every pixel to the nearest busy-lane pixel."""
    print("\nCalculating distance to busy shipping lanes...")
    distance_pixels = distance_transform_edt(~busy_mask)
    return distance_pixels * pixel_size_m

def load_occurrences() -> gpd.GeoDataFrame | None:
    """Loads the species occurrences CSV and converts it to a GeoDataFrame."""
    print(f"\nReading species occurrences: {INPUT_FILE}")

    if not INPUT_FILE.exists():
        print(f"\nERROR: spatial_overlay_2023.csv not found at {INPUT_FILE}")
        return None

    df = pd.read_csv(INPUT_FILE)
    print(f"Occurrences loaded: {len(df)}")

    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(
            df["decimalLongitude"], df["decimalLatitude"]
        ),
        crs="EPSG:4326",
    ).to_crs(RASTER_CRS)

def sample_distances(
    gdf: gpd.GeoDataFrame,
    distance_meters: np.ndarray,
    src: rasterio.DatasetReader,
) -> list[float]:
    """Samples the distance surface at each occurrence's pixel location."""
    print("\nCalculating distance for each occurrence...")

    distances = []
    for geom in gdf.geometry:
        try:
            row, col = src.index(geom.x, geom.y)
            if 0 <= row < src.height and 0 <= col < src.width:
                distances.append(float(distance_meters[row, col]))
            else:
                distances.append(np.nan)
        except Exception:
            distances.append(np.nan)

    return distances

def save_results(gdf: gpd.GeoDataFrame) -> None:
    """Saves the final table and prints summary stats by species."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    gdf.drop(columns="geometry").to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved data: {OUTPUT_FILE}")

    print("\nDistance to busy shipping lanes by species (km):")
    print(
        gdf.groupby("especie_normalizada")["distance_to_busy_shipping_km"]
        .agg(["count", "mean", "median", "min", "max"])
    )

def main() -> None:
    print("Reading vessel traffic raster...")
    raster_file = raster_path(YEAR)
    print(raster_file)

    if not raster_file.exists():
        print("ERROR: Raster file not found.")
        return

    gdf = load_occurrences()
    if gdf is None:
        return

    with rasterio.open(raster_file) as src:
        data = src.read(1)

        busy_mask = compute_busy_mask(data, src.nodata)
        pixel_size_m = compute_pixel_size_m(src.transform)
        distance_meters = compute_distance_surface(busy_mask, pixel_size_m)

        gdf["distance_to_busy_shipping_m"] = sample_distances(
            gdf, distance_meters, src
        )

    gdf["distance_to_busy_shipping_km"] = (
        gdf["distance_to_busy_shipping_m"] / 1000
    )

    save_results(gdf)

if __name__ == "__main__":
    main()