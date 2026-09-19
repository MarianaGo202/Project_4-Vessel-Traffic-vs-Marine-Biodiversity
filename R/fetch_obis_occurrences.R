library(robis)
library(sf)
library(dplyr)

# Query OBIS
region_wkt <- "POLYGON((-25 60, -25 82, 32 82, 32 55, -25 60))"

target_species <- c(
  "Balaenoptera physalus",
  "Balaenoptera musculus",
  "Physeter macrocephalus",
  "Fratercula arctica",
  "Rissa tridactyla",
  "Dermochelys coriacea"
)

occurrences <- occurrence(
  scientificname = target_species,
  geometry = region_wkt,
  fields = c(
    "scientificName",
    "decimalLongitude",
    "decimalLatitude",
    "eventDate",
    "date_year",
    "basisOfRecord",
    "individualCount"
  )
)

print(table(occurrences$scientificName))
print(range(occurrences$date_year, na.rm = TRUE))

# Save full raw dataset (CSV + GeoJSON)
write.csv(
  occurrences,
  "obis_especies_escandinavia.csv",
  row.names = FALSE
)

st_write(
  st_as_sf(
    occurrences,
    coords = c("decimalLongitude", "decimalLatitude"),
    crs = 4326
  ),
  "obis_especies_escandinavia.geojson",
  delete_dsn = TRUE
)

# Normalize species names and tag by decade
occurrences <- occurrences %>%
  mutate(especie_normalizada = case_when(
    grepl("^Balaenoptera musculus", scientificName) ~ "Balaenoptera musculus",
    grepl("^Balaenoptera physalus", scientificName) ~ "Balaenoptera physalus",
    grepl("^Rissa tridactyla", scientificName) ~ "Rissa tridactyla",
    TRUE ~ scientificName
  ))

print(table(occurrences$especie_normalizada))

occurrences <- occurrences %>%
  mutate(decade = floor(date_year / 10) * 10)

print(table(occurrences$especie_normalizada, occurrences$decade))

# Re-save the full dataset now that it includes the normalized species
# and decade columns.
write.csv(occurrences, "obis_especies_escandinavia.csv", row.names = FALSE)

# 2023 subset (for the spatial overlay analysis)
obis_2023 <- occurrences %>%
  filter(date_year == 2023)

write.csv(obis_2023, "obis_espacial_2023.csv", row.names = FALSE)

st_write(
  st_as_sf(obis_2023, coords = c("decimalLongitude", "decimalLatitude"), crs = 4326),
  "obis_espacial_2023.geojson",
  delete_dsn = TRUE
)

print(table(obis_2023$especie_normalizada))

# 2017-2024 subset (for the temporal analysis)
obis_temporal <- occurrences %>%
  filter(date_year >= 2017 & date_year <= 2024)

write.csv(obis_temporal, "obis_temporal_2017_2024.csv", row.names = FALSE)

print(table(obis_temporal$especie_normalizada, obis_temporal$date_year))