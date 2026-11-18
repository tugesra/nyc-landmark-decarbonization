"""Extract the columns we need from the LL84 benchmarking file into a smaller CSV."""
import sys
import pandas as pd

SRC = sys.argv[1]
OUT = sys.argv[2]
COLS = [
    'Calendar Year', 'Property ID', 'Property Name', 'Parent Property ID',
    'NYC Borough, Block and Lot (BBL)', 'NYC Building Identification Number (BIN)',
    'Address 1', 'Primary Property Type - Self Selected',
    'Primary Property Type - Portfolio Manager-Calculated',
    'List of All Property Use Types (GFA) (ft²)', 'Largest Property Use Type',
    'Largest Property Use Type - Gross Floor Area (ft²)', 'Year Built', 'Number of Buildings',
    'ENERGY STAR Score', 'Site EUI (kBtu/ft²)', 'Weather Normalized Site EUI (kBtu/ft²)',
    'Site Energy Use (kBtu)', 'Source EUI (kBtu/ft²)',
    'Fuel Oil #1 Use (kBtu)', 'Fuel Oil #2 Use (kBtu)', 'Fuel Oil #4 Use (kBtu)',
    'Fuel Oil #5 & 6 Use (kBtu)', 'Diesel #2 Use (kBtu)', 'Propane Use (kBtu)', 'Kerosene Use (kBtu)',
    'District Steam Use (kBtu)', 'District Hot Water Use (kBtu)', 'District Chilled Water Use (kBtu)',
    'Natural Gas Use (kBtu)', 'Electricity Use - Grid Purchase (kWh)',
    'Electricity Use - Grid Purchase and Generated from Onsite Renewable Systems (kWh)',
    'Total (Location-Based) GHG Emissions (Metric Tons CO2e)',
    'Total (Location-Based) GHG Emissions Intensity (kgCO2e/ft²)',
    'Direct GHG Emissions (Metric Tons CO2e)', 'Indirect (Location-Based) GHG Emissions (Metric Tons CO2e)',
    'Default Values', 'Estimated Values - Energy',
    'Alert - Energy Meter has less than 12 full calendar months of data',
    'Alert - Gross Floor Area is 0 ft2',
    'Property GFA - Self-Reported (ft²)', 'Property GFA - Calculated (Buildings) (ft²)',
    'Borough', 'Latitude', 'Longitude', 'Census Tract (2020)', 'Neighborhood Tabulation Area (NTA) (2020)',
]
df = pd.read_csv(SRC, usecols=COLS, low_memory=False)
df.to_csv(OUT, index=False)
print(df.shape)
print(df['Calendar Year'].value_counts().sort_index())
