library(robis)
library(sf)
library(dplyr)

getwd()
file.exists("output/tables/spatial_overlay_2023.csv")

# Study region: Scandinavia (Norway, Iceland, Denmark)

# WKT polygon, lon/lat order. Note: this is wider than the final study area
# used in Python (raster coverage caps at 68N; that filtering happens later)
region_wkt <- "POLYGON((-25 60, -25 82, 32 82, 32 55, -25 60))"

# Target species: threatened / vulnerable (IUCN status in comments)
target_species <- c(
  "Balaenoptera physalus", 
  "Balaenoptera musculus",
  "Physeter macrocephalus",
  "Fratercula arctica",
  "Rissa tridactyla",
  "Dermochelys coriacea"
)

# Pull occurrences from OBIS
occurrences <- occurrence(
  scientificname = target_species,
  geometry = region_wkt,
  fields = c("scientificName", "decimalLongitude", "decimalLatitude",
             "eventDate", "date_year", "basisOfRecord", "individualCount")
)

# Normalize subspecies names into their parent species

# OBIS returns some records under subspecies-level names
# (e.g. "Balaenoptera physalus physalus"); merge these for species-level counts.
occurrences <- occurrences %>%
  mutate(especie_normalizada = case_when(
    grepl("^Balaenoptera musculus", scientificName) ~ "Balaenoptera musculus",
    grepl("^Balaenoptera physalus", scientificName) ~ "Balaenoptera physalus",
    grepl("^Rissa tridactyla", scientificName) ~ "Rissa tridactyla",
    TRUE ~ scientificName
  ))

print(table(occurrences$especie_normalizada))
print(range(occurrences$date_year, na.rm = TRUE))

# Decade breakdown (useful for sanity-checking coverage/bias)
occurrences <- occurrences %>%
  mutate(decada = floor(date_year / 10) * 10)
print(table(occurrences$especie_normalizada, occurrences$decada))

# Export: full dataset
write.csv(occurrences, "obis_especies_escandinavia.csv", row.names = FALSE)

# Export: 2023 subset (spatial analysis)
obis_2023 <- occurrences %>% filter(date_year == 2023)
write.csv(obis_2023, "obis_espacial_2023.csv", row.names = FALSE)
print(table(obis_2023$especie_normalizada))

# Export: 2017-2024 subset (temporal analysis)
obis_temporal <- occurrences %>% filter(date_year >= 2017 & date_year <= 2024)
write.csv(obis_temporal, "obis_temporal_2017_2024.csv", row.names = FALSE)
print(table(obis_temporal$especie_normalizada, obis_temporal$date_year))