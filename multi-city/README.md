# Seattle and Boston

Extends the New York analysis to Seattle's Building Emissions Performance Standard (BEPS) and Boston's BERDO 2.0, using 2024 energy data in both cities.

## Data (download into `multi-city/seattle/` and `multi-city/boston/`)

Seattle
- Building Energy Benchmarking Data, 2015–Present (CSV): https://data.seattle.gov/api/views/teqw-tu6e/rows.csv?accessType=DOWNLOAD
- Landmarks (GeoJSON): https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::landmarks-1
- Historic and Special Review Districts (GeoJSON): https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::historic-and-special-review-districts
- BEPS GHGI targets and emission factors (PDF): https://www.seattle.gov/documents/departments/ose/building%20energy/beps-ghgi-targets.pdf

Boston
- BERDO disclosure files (XLSX: 2024-reported, 2025-reported, 2026 disclosure): https://data.boston.gov/dataset/building-emissions-reduction-and-disclosure-ordinance
- Boston Landmarks Commission landmarks (GeoJSON): https://data.boston.gov/dataset/boston-landmarks-commission-blc-landmarks
- Boston Landmarks Commission historic districts (GeoJSON): https://data.boston.gov/dataset/boston-landmarks-commission-blc-historic-districts
- Parcels 2025 (GeoJSON zip): https://data.boston.gov/dataset/d0fe512c-80bd-4ed7-8582-c6ec38aedfa0
- BERDO Policies and Procedures (PDF; Appendix A use classes, Appendix B grid factors): https://www.boston.gov/sites/default/files/file/2026/09/BERDO%20Policies%20and%20Procedures_1.pdf

## Run

```bash
pip install pandas openpyxl shapely
python multi-city/scripts/seattle_analysis.py
python multi-city/scripts/boston_analysis.py
python multi-city/scripts/export_maps.py
python multi-city/scripts/build_city_pages.py
```

## Outputs

| File | Contents |
|---|---|
| `outputs/seattle_summary.txt` | Fuel mix and share over the 2031–35 and 2036–40 targets, by group and by fuel |
| `outputs/boston_summary.txt` | Fuel mix and share over the 2025–29 and 2030–34 standards, by group and by fuel |
| `outputs/seattle_landmark_matches.csv`, `outputs/boston_landmark_matches.csv` | Every benchmarking record matched to a landmark, for checking |

Exposure figures assume 2024 energy use does not change. Seattle uses provisional 2031–35 factors, the largest use only and non-weather-normalized energy; Boston's 2030 electricity emissions are scaled by the projected grid factor (259/249 kg/MWh). Only 43 Boston landmarks have usable data.
