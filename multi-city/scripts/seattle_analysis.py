"""Seattle: landmark exposure to the Building Emissions Performance Standard (BEPS).

Inputs (multi-city/seattle/):
  Building_Energy_Benchmarking_Data__2015-Present.csv   (data.seattle.gov, teqw-tu6e)
  Landmarks_*.geojson                                    (SeattleCityGIS "Landmarks", points with parcel PIN)
  Zoning_Overlays-Historic-Special_Review_Districts_*.geojson
Rules: OSE "BEPS GHGI Targets & Emissions Factors" (Jan 2026; Director's Rule 2025-01 Tables 4-5).
"""
import glob, json, math, re, sys
from pathlib import Path
import pandas as pd
from shapely.geometry import shape, Point

BASE = Path(__file__).resolve().parents[1]
D = BASE / "seattle"
OUT = BASE / "outputs"
YEAR = 2024

# 2031-2035 and 2036-2040 GHGITs (kgCO2e/sf/yr)
GHGIT = {
 "College/University": (2.69, 1.57), "Data Center": (1.43, 0.83), "Entertainment/Public Assembly": (1.18, 0.69),
 "Fire/Police Station": (2.23, 1.30), "Hospital": (4.68, 2.73), "Hotel": (2.06, 1.20), "K-12 School": (0.95, 0.56),
 "Laboratory": (6.30, 3.68), "Medical Office": (2.11, 1.23), "Multifamily Housing": (0.89, 0.63), "Museum": (2.11, 1.23),
 "Non-Refrigerated Warehouse": (0.77, 0.45), "Office": (0.81, 0.47), "Other": (2.48, 1.45), "Recreation": (3.22, 1.88),
 "Refrigerated Warehouse": (0.98, 0.57), "Residence Hall/Dormitory": (1.16, 0.68), "Restaurant": (5.73, 3.34),
 "Retail Store": (1.03, 0.60), "Self-Storage Facility": (0.31, 0.18), "Senior Living Community": (2.11, 1.23),
 "Services": (1.36, 0.79), "Supermarket/Grocery Store": (3.42, 2.00), "Worship Facility": (1.20, 0.70),
}
# Provisional 2031-2035 emission factors (kgCO2e/kBtu); also used for 2036-2040 as a placeholder (not yet set by rule)
EF = {"elec": 0.0029, "gas": 0.053, "steam": 0.081}
ALIAS = {
 "Distribution Center": "Non-Refrigerated Warehouse", "Senior Care Community": "Senior Living Community",
 "Residential Care Facility": "Senior Living Community", "Performing Arts": "Entertainment/Public Assembly",
 "Social/Meeting Hall": "Entertainment/Public Assembly", "Other - Entertainment/Public Assembly": "Entertainment/Public Assembly",
 "Movie Theater": "Entertainment/Public Assembly", "Library": "Entertainment/Public Assembly", "Convention Center": "Entertainment/Public Assembly",
 "Fitness Center/Health Club/Gym": "Recreation", "Other - Recreation": "Recreation", "Swimming Pool": "Recreation", "Ice/Curling Rink": "Recreation",
 "Strip Mall": "Retail Store", "Other - Mall": "Retail Store", "Enclosed Mall": "Retail Store", "Wholesale Club/Supercenter": "Retail Store",
 "Automobile Dealership": "Retail Store", "Food Sales": "Supermarket/Grocery Store", "Courthouse": "Office", "Bank Branch": "Office",
 "Financial Office": "Office", "Adult Education": "College/University", "Vocational School": "College/University",
 "Pre-school/Daycare": "K-12 School", "Other - Education": "K-12 School", "Outpatient Rehabilitation/Physical Therapy": "Medical Office",
 "Urgent Care/Clinic/Other Outpatient": "Medical Office", "Hospital (General Medical & Surgical)": "Hospital",
 "Other/Specialty Hospital": "Hospital", "Other - Restaurant/Bar": "Restaurant", "Fast Food Restaurant": "Restaurant",
 "Bar/Nightclub": "Restaurant", "Police Station": "Fire/Police Station", "Fire Station": "Fire/Police Station",
 "Personal Services (Health/Beauty, Dry Cleaning, etc)": "Services", "Repair Services (Vehicle, Shoe, Locksmith, etc)": "Services",
 "Other - Services": "Services", "Other - Public Services": "Services", "Other - Lodging/Residential": "Residence Hall/Dormitory",
 "Other - Technology/Science": "Laboratory",
}
NON_BUILDING = re.compile(r"clock|bell|mural|vessel|ship|tug|ferry|lightship|sign\b|statue|fountain|totem|pole|tree|bridge|"
                          r"carousel|boat|schooner|fireboat|steam plant|car\b|trolley|monorail|pergola|bench|horiuchi", re.I)

def pad(p):
    p = re.sub(r"\D", "", str(p or ""))
    return p.zfill(10) if p else ""

def metres(x1, y1, x2, y2):
    t = math.pi / 180
    return 6371000 * math.hypot((x2 - x1) * t * math.cos((y1 + y2) / 2 * t), (y2 - y1) * t)

def activity(u):
    if not isinstance(u, str) or not u.strip():
        return None
    u = u.strip()
    return u if u in GHGIT else ALIAS.get(u, "Other")

def main():
    df = pd.read_csv(D / "Building_Energy_Benchmarking_Data__2015-Present.csv", low_memory=False)
    num = lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["elec"], df["gas"], df["steam"] = num("Electricity(kBtu)"), num("NaturalGas(kBtu)"), num("SteamUse(kBtu)")
    df["year"] = pd.to_numeric(df["DataYear"], errors="coerce")

    prior = df[df["year"].isin([YEAR - 2, YEAR - 1])]
    had_fossil = set(prior.loc[(prior.gas > 0) | (prior.steam > 0), "OSEBuildingID"])

    b = df[df["year"] == YEAR].copy()
    b = b[~b["Demolished"].astype(str).str.lower().isin(["true", "1", "yes"])]

    lm = json.load(open(glob.glob(str(D / "Landmarks_*.geojson"))[0]))["features"]
    by_pin = {}
    for f in lm:
        p = f["properties"]
        if not f.get("geometry") or NON_BUILDING.search(p.get("NAME") or ""):
            continue
        k = pad(p.get("PIN"))
        if k:
            x, y = f["geometry"]["coordinates"][:2]
            by_pin.setdefault(k, []).append((x, y, p.get("NAME")))
    dist_polys = [(f["properties"]["DESCRIPTION"], shape(f["geometry"]))
                  for f in json.load(open(glob.glob(str(D / "Zoning_Overlays-Historic-*.geojson"))[0]))["features"]]

    rows = []
    for _, r in b.iterrows():
        x, y = pd.to_numeric(r["Longitude"], errors="coerce"), pd.to_numeric(r["Latitude"], errors="coerce")
        has_xy = pd.notna(x) and pd.notna(y)
        lm_name, lm_m = None, None
        cand = by_pin.get(pad(r["TaxParcelIdentificationNumber"]))
        if cand and has_xy:
            d, name = min((metres(x, y, cx, cy), n) for cx, cy, n in cand)
            if d <= 100:
                lm_name, lm_m = name, round(d)
        district = next((n for n, g in dist_polys if has_xy and g.contains(Point(x, y))), None)
        fuel = ("steam" if r.steam > 0 else "gas" if r.gas > 0 else
                "incomplete" if r["OSEBuildingID"] in had_fossil else "all-electric")
        gfa = pd.to_numeric(r["PropertyGFABuildings"], errors="coerce")
        if not gfa or pd.isna(gfa) or gfa <= 0:
            gfa = pd.to_numeric(r["PropertyGFATotal"], errors="coerce")
        at = activity(r["LargestPropertyUseType"])
        tot = r.elec + r.gas + r.steam
        valid = bool(gfa and gfa > 0 and tot > 0 and at)
        ghgi = (r.elec * EF["elec"] + r.gas * EF["gas"] + r.steam * EF["steam"]) / gfa if valid else None
        ghgi_ded = (r.elec * EF["elec"] + r.gas * EF["gas"]) / gfa if valid else None
        exempt = fuel == "all-electric"
        t31, t36 = GHGIT[at] if at else (None, None)
        rows.append(dict(
            id=r["OSEBuildingID"], name=r["BuildingName"], address=r["Address"], lat=y if has_xy else None, lon=x if has_xy else None, building_type=r["BuildingType"], use=r["LargestPropertyUseType"],
            activity=at, gfa=gfa, year_built=r["YearBuilt"], landmark=lm_name, landmark_dist_m=lm_m, district=district,
            group="landmark" if lm_name else "district" if district else "other", fuel=fuel, valid=valid,
            ghgi=ghgi, ghgi_steam_deducted=ghgi_ded, target_2031=t31, target_2036=t36,
            over_2031=(False if exempt else ghgi > t31) if valid else None,
            over_2031_steam_deducted=(False if exempt else ghgi_ded > t31) if valid else None,
            over_2036=(False if exempt else ghgi > t36) if valid else None))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "seattle_buildings_2024.csv", index=False)

    v = res[res.valid & (res.fuel != "incomplete")]
    def summ(g):
        n = len(g)
        return pd.Series({"n": n,
            "steam_%": 100 * (g.fuel == "steam").mean(), "gas_%": 100 * (g.fuel == "gas").mean(),
            "all_electric_%": 100 * (g.fuel == "all-electric").mean(),
            "over_2031_%": 100 * g.over_2031.mean(), "over_2031_steam_deducted_%": 100 * g.over_2031_steam_deducted.mean(),
            "over_2036_%": 100 * g.over_2036.mean()}).round(1)
    by_group = v.groupby("group")[["fuel","over_2031","over_2031_steam_deducted","over_2036"]].apply(summ)
    by_fuel = v.groupby("fuel")[["fuel","over_2031","over_2031_steam_deducted","over_2036"]].apply(summ)
    by_group_nonres = v[v.building_type == "NonResidential"].groupby("group")[["fuel","over_2031","over_2031_steam_deducted","over_2036"]].apply(summ)
    with open(OUT / "seattle_summary.txt", "w") as fh:
        fh.write(f"Seattle BEPS exposure, benchmarking data year {YEAR}\n")
        fh.write(f"rows {len(res)}, analysed (valid, fuel known) {len(v)}, incomplete fuel {int((res.fuel=='incomplete').sum())}\n\n")
        fh.write("By group\n" + by_group.to_string() + "\n\nBy fuel\n" + by_fuel.to_string() +
                 "\n\nNonresidential only, by group\n" + by_group_nonres.to_string() + "\n")
    print(open(OUT / "seattle_summary.txt").read())

if __name__ == "__main__":
    main()
