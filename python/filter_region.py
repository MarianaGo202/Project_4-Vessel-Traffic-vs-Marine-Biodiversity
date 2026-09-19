import pandas as pd

from config import (
    LAT_NORTH_LIMIT,
    OBIS_SPATIAL_2023_CSV,
    OBIS_SPATIAL_2023_FILTERED,
    OBIS_TEMPORAL_CSV,
    OBIS_TEMPORAL_FILTERED,
    PROCESSED_DIR,
)

def filter_by_latitude(input_path, output_path, lat_limit):
    df = pd.read_csv(input_path)
    n_before = len(df)

    df_filtered = df[df["decimalLatitude"] <= lat_limit].copy()
    n_after = len(df_filtered)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_filtered.to_csv(output_path, index=False)

    print(f"{input_path.name}: {n_before} -> {n_after} records "
          f"({n_before - n_after} dropped, above {lat_limit}N)")
    print(df_filtered["especie_normalizada"].value_counts())
    print()

    return df_filtered

def main():
    filter_by_latitude(OBIS_SPATIAL_2023_CSV, OBIS_SPATIAL_2023_FILTERED, LAT_NORTH_LIMIT)
    filter_by_latitude(OBIS_TEMPORAL_CSV, OBIS_TEMPORAL_FILTERED, LAT_NORTH_LIMIT)

if __name__ == "__main__":
    main()