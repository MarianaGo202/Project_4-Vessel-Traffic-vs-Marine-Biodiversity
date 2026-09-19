import rasterio
from pyproj import Transformer

path = r"data\raw\AIS\EMODnet_HA_Vessel_Density_allAvg\EMODnet_HA_Vessel_Density_allAvg\vesseldensity_all_2023.tif"

with rasterio.open(path) as src:
    print("Bounding box (EPSG:3035):", src.bounds)

    transformer = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)
    lon_min, lat_min = transformer.transform(src.bounds.left, src.bounds.bottom)
    lon_max, lat_max = transformer.transform(src.bounds.right, src.bounds.top)
    print(f"Bounding box (lat/lon): lon {lon_min:.2f} to {lon_max:.2f}, lat {lat_min:.2f} to {lat_max:.2f}")

    x, y = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform(-21.94, 64.15)
    row, col = src.index(x, y)
    print(f"Does Reykjavik fall inside the raster? row={row}, col={col}, dimensions={src.height}x{src.width}")
    if 0 <= row < src.height and 0 <= col < src.width:
        value = src.read(1)[row, col]
        print(f"Value at Reykjavik's pixel: {value}")
    else:
        print("Reykjavik is OUTSIDE the raster.")