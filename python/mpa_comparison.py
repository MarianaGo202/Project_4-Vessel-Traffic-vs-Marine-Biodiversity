from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

from config import DATA_DIR, OUTPUT_DIR, RASTER_CRS

TABLES_DIR = OUTPUT_DIR / "tables"
FIGURES_DIR = OUTPUT_DIR / "figures"

MPA_DIR = DATA_DIR / "raw" / "mpa"

# Folder extracted from the WDPA download (covers all of Europe).
WDPA_SHP_DIR = MPA_DIR / "WDPA_WDOECM_Sep2026_Public_EU_shp"

# Cached, already-filtered result (created on first run).
MPA_PATH = MPA_DIR / "WDPA_scandinavia.geojson"

TARGET_ISO3 = ["NOR", "DNK", "ISL"]

OCCURRENCE_CANDIDATES = [
    TABLES_DIR / "spatial_overlay_2023_with_distance.csv",
    TABLES_DIR / "spatial_overlay_2023_with_gfw.csv",
    TABLES_DIR / "spatial_overlay_2023.csv",
]

MIN_GROUP_SIZE_FOR_TEST = 5

def filter_by_country(gdf: gpd.GeoDataFrame, iso3_codes: list[str]) -> gpd.GeoDataFrame:
    if "ISO3" not in gdf.columns:
        print("WARNING: no ISO3 column found, skipping country filter.")
        return gdf

    target = set(iso3_codes)

    def matches(value) -> bool:
        codes = {code.strip() for code in str(value).split(";")}
        return bool(codes & target)

    mask = gdf["ISO3"].apply(matches)
    return gdf[mask]

def build_mpas_from_shapefiles() -> gpd.GeoDataFrame | None:
    if not WDPA_SHP_DIR.exists():
        print(f"\nERROR: WDPA shapefile folder not found at {WDPA_SHP_DIR}")
        return None

    shp_files = sorted(WDPA_SHP_DIR.rglob("*.shp"))
    if not shp_files:
        print(f"\nERROR: no .shp files found under {WDPA_SHP_DIR}")
        return None

    print(f"\nFound {len(shp_files)} shapefile(s) under {WDPA_SHP_DIR}:")
    for path in shp_files:
        print(f"  {path.relative_to(WDPA_SHP_DIR)}")

    pieces = []
    for path in shp_files:
        print(f"\nReading {path.name}...")
        gdf = gpd.read_file(path)
        print(f"  Features loaded: {len(gdf)}")

        filtered = filter_by_country(gdf, TARGET_ISO3)
        print(f"  Features after country filter: {len(filtered)}")

        if len(filtered) > 0:
            pieces.append(filtered)

    if not pieces:
        print("\nERROR: no features matched the target countries "
              f"({', '.join(TARGET_ISO3)}) in any shapefile.")
        return None

    mpas = gpd.GeoDataFrame(pd.concat(pieces, ignore_index=True))
    if mpas.crs is None:
        mpas = mpas.set_crs("EPSG:4326")

    print(f"\nTotal MPA features for {', '.join(TARGET_ISO3)}: {len(mpas)}")
    return mpas

def load_mpas() -> gpd.GeoDataFrame | None:
    if MPA_PATH.exists():
        print(f"\nReading cached MPA data: {MPA_PATH}")
        mpas = gpd.read_file(MPA_PATH)
    else:
        mpas = build_mpas_from_shapefiles()
        if mpas is None:
            return None

        MPA_DIR.mkdir(parents=True, exist_ok=True)
        mpas.to_file(MPA_PATH, driver="GeoJSON")
        print(f"Cached filtered MPA data to: {MPA_PATH}")

    mpas = mpas.to_crs(RASTER_CRS)

    # Fixing invalid geometries here avoids downstream errors/hangs in the
    # spatial join below (common with large, complex coastline polygons).
    mpas["geometry"] = mpas["geometry"].buffer(0)

    print(f"MPA features loaded: {len(mpas)}")
    return mpas

def get_occurrence_file() -> Path | None:
    return next((p for p in OCCURRENCE_CANDIDATES if p.exists()), None)

def load_occurrences() -> gpd.GeoDataFrame | None:
    occ_path = get_occurrence_file()

    if occ_path is None:
        print("\nERROR: No occurrence file found.\nExpected one of:")
        for path in OCCURRENCE_CANDIDATES:
            print(path)
        return None

    print(f"\nReading occurrences:\n{occ_path}")
    df = pd.read_csv(occ_path)
    print(f"Occurrences loaded: {len(df)}")

    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(
            df["decimalLongitude"], df["decimalLatitude"]
        ),
        crs="EPSG:4326",
    ).to_crs(RASTER_CRS)

def check_inside_mpas(
    occurrences: gpd.GeoDataFrame,
    mpas: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    print("\nChecking occurrences inside protected areas (spatial join)...")

    occurrences = occurrences.reset_index(drop=True)

    joined = gpd.sjoin(
        occurrences,
        mpas[["geometry"]],
        how="left",
        predicate="within",
    )

    # A point could technically fall inside more than one overlapping MPA,
    # which would duplicate rows in the join. Collapse back to one row per
    # occurrence, keeping the "inside" flag if it matched at least one MPA.
    inside_flag = joined.groupby(joined.index)["index_right"].apply(
        lambda s: s.notna().any()
    )

    occurrences["inside_mpa"] = inside_flag.reindex(occurrences.index, fill_value=False)

    return occurrences

def print_summary(gdf: gpd.GeoDataFrame) -> None:
    inside_count = int(gdf["inside_mpa"].sum())
    total = len(gdf)
    percentage = gdf["inside_mpa"].mean() * 100

    print(f"\nOccurrences inside MPAs: {inside_count} of {total} "
          f"({percentage:.1f}%)")

    summary = (
        gdf.groupby(["especie_normalizada", "inside_mpa"])
        .size()
        .unstack(fill_value=0)
    )
    print(f"\n{summary}")

def plot_traffic_comparison(inside: pd.Series, outside: pd.Series) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.boxplot([inside, outside], tick_labels=["Inside MPA", "Outside MPA"])
    ax.set_ylabel("Traffic density")
    ax.set_title("Vessel Traffic Exposure Inside vs Outside MPAs")
    fig.tight_layout()

    out_path = FIGURES_DIR / "mpa_traffic_comparison.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    print(f"\nSaved plot: {out_path}")

def compare_traffic_inside_outside(gdf: gpd.GeoDataFrame) -> None:
    if "traffic_buffer_mean" not in gdf.columns:
        print("\nNo traffic column found.")
        return

    inside = gdf[gdf["inside_mpa"]]["traffic_buffer_mean"].dropna()
    outside = gdf[~gdf["inside_mpa"]]["traffic_buffer_mean"].dropna()

    print(f"\nInside MPA records: {len(inside)}")
    print(f"Outside MPA records: {len(outside)}")

    if len(inside) == 0 or len(outside) == 0:
        print("\nCannot compare groups because one group has no observations.")
        return

    if len(inside) < MIN_GROUP_SIZE_FOR_TEST or len(outside) < MIN_GROUP_SIZE_FOR_TEST:
        print("\nWARNING: Too few points in one group for a reliable "
              "statistical comparison.")

    stat, p_value = stats.mannwhitneyu(inside, outside, alternative="two-sided")

    print(f"\nMean traffic inside MPAs: {inside.mean():.3f} (n={len(inside)})")
    print(f"Mean traffic outside MPAs: {outside.mean():.3f} (n={len(outside)})")
    print(f"Mann-Whitney U statistic: {stat:.3f}")
    print(f"p-value: {p_value:.4f}")

    if p_value < 0.05:
        print("Statistically significant difference between inside and "
              "outside MPAs.")
    else:
        print("No statistically significant difference detected.")

    plot_traffic_comparison(inside, outside)

def save_results(gdf: gpd.GeoDataFrame) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = TABLES_DIR / "spatial_overlay_2023_with_mpa.csv"
    gdf.drop(columns="geometry").to_csv(out_csv, index=False)

    print(f"\nSaved data: {out_csv}")

def main() -> None:
    print("MPA Comparison Analysis\n")

    mpas = load_mpas()
    if mpas is None:
        return

    occurrences = load_occurrences()
    if occurrences is None:
        return

    occurrences = check_inside_mpas(occurrences, mpas)

    print_summary(occurrences)
    compare_traffic_inside_outside(occurrences)
    save_results(occurrences)

if __name__ == "__main__":
    main()