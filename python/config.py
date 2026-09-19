from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


DATA_DIR = PROJECT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_DIR / "outputs"

OBIS_SPATIAL_2023_CSV = DATA_DIR / "spatial" / "obis_espacial_2023.csv"
OBIS_TEMPORAL_CSV = DATA_DIR / "raw" / "biodiversity" / "obis_temporal_2017_2024.csv"

OBIS_SPATIAL_2023_FILTERED = PROCESSED_DIR / "obis_espacial_2023_filtered.csv"
OBIS_TEMPORAL_FILTERED = PROCESSED_DIR / "obis_temporal_2017_2024_filtered.csv"

RAW_RASTER_DIR = (
    DATA_DIR
    / "raw"
    / "AIS"
    / "EMODnet_HA_Vessel_Density_allAvg"
    / "EMODnet_HA_Vessel_Density_allAvg"
)

RASTER_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]

RASTER_CRS = "EPSG:3035"

def raster_path(year: int) -> Path:
    return RAW_RASTER_DIR / f"vesseldensity_all_{year}.tif"

LAT_NORTH_LIMIT = 68.0

BUFFER_RADIUS_M = 10_000

GRID_CELL_SIZE_M = 25_000

SPECIES_LIST = [
    "Balaenoptera musculus",
    "Balaenoptera physalus",
    "Physeter macrocephalus",
    "Fratercula arctica",
    "Rissa tridactyla",
    "Dermochelys coriacea",
]

LOW_SAMPLE_SPECIES_2023 = [
    "Balaenoptera physalus",
    "Physeter macrocephalus",
]

IUCN_STATUS = {
    "Balaenoptera musculus": "EN",
    "Balaenoptera physalus": "VU",
    "Physeter macrocephalus": "VU",
    "Fratercula arctica": "VU",
    "Rissa tridactyla": "VU",
    "Dermochelys coriacea": "VU",
}

IUCN_WEIGHT = {
    "CR": 4,
    "EN": 3,
    "VU": 2,
    "NT": 1,
}

GFW_CSV = DATA_DIR / "raw" / "AIS" / "vessel_activity_2023.csv"

GFW_COLUMN_MAP_CANDIDATES = {
    "lat": ["cell_ll_lat", "lat_bin", "latitude", "lat"],
    "lon": ["cell_ll_lon", "lon_bin", "longitude", "lon"],
    "hours": ["fishing_hours", "hours", "apparent_fishing_hours"],
}

MPA_PATH = DATA_DIR / "raw" / "mpa" / "WDPA_scandinavia.gpkg"