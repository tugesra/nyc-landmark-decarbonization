"""Boston: landmark exposure to BERDO 2.0 emissions standards.

Inputs (multi-city/boston/):
  2026-berdo-data-disclosure-9.30.26.xlsx   (BERDO Disclosure 2026 = 2025 energy data; sheet "Buildings & Campuses")
  2025-reported-energy-and-water-metrics.xlsx, 2024-reported-energy-and-water-metrics-1.xlsx (missing-fuel check)
  boston_landmarks_commission_blc_landmarks.json, boston_landmarks_commission_blc_historic_districts.json
  parcels_2025_geojson.zip
  BERDO Policies and Procedures_1.pdf (Appendix A use classes, Appendix B projected grid factors)
"""
import json, re, zipfile
from pathlib import Path
import pandas as pd
from shapely.geometry import shape
from shapely import STRtree

BASE = Path(__file__).resolve().parents[1]
D = BASE / "boston"
OUT = BASE / "outputs"

STD = {  # kgCO2e/sf/yr: 2025-2029, 2030-2034 (BERDO 2.0 ordinance Table)
 "Assembly": (7.8, 4.6), "College/University": (10.2, 5.3), "Education": (3.9, 2.4), "Food Sales & Service": (17.4, 10.9),
 "Healthcare": (15.4, 10.0), "Lodging": (5.8, 3.7), "Manufacturing/Industrial": (23.9, 15.3), "Multifamily housing": (4.1, 2.4),
 "Office": (5.3, 3.2), "Retail": (7.1, 3.4), "Services": (7.5, 4.5), "Storage": (5.4, 2.8), "Technology/Science": (19.2, 11.1)}
# Appendix A (ENERGY STAR property type -> BERDO building use)
APPX_A = {
 "Assembly": ["Aquarium","Convention Center","Fitness Center/Health Club/Gym","Heated Swimming Pool","Indoor Arena","Ice/Curling Rink",
   "Museum","Movie Theater","Other - Entertainment/Public Assembly","Other - Recreation","Other - Stadium","Performing Arts","Race Track",
   "Social/Meeting Hall","Stadium (Open)","Stadium (Closed)","Swimming Pool","Worship Facility","Bowling Alley","Casino","Roller Rink","Zoo"],
 "College/University": ["College/University"],
 "Education": ["Adult Education","K-12 School","Other - Education","Pre-school/Daycare","Vocational School"],
 "Food Sales & Service": ["Bar/Nightclub","Fast Food Restaurant","Food Sales","Food Service","Other - Restaurant/Bar","Restaurant","Supermarket/Grocery Store"],
 "Healthcare": ["Ambulatory Surgical Center","Hospital (General Medical & Surgical)","Medical Office","Other - Specialty Hospital","Other/Specialty Hospital",
   "Outpatient Rehabilitation/Physical Therapy","Urgent Care/Clinic/Other Outpatient","Veterinary Office","Residential Care Facility","Senior Living Community","Senior Care Community"],
 "Lodging": ["Barracks","Hotel","Other - Lodging/Residential","Residence Hall/Dormitory","Single Family Home","Prison/Incarceration"],
 "Manufacturing/Industrial": ["Manufacturing/Industrial Plant"],
 "Multifamily housing": ["Multifamily Housing"],
 "Office": ["Financial Office","Office"],
 "Retail": ["Automobile Dealership","Bank Branch","Enclosed Mall","Lifestyle Center","Other - Mall","Retail Store","Strip Mall","Wholesale Club/Supercenter"],
 "Services": ["Convenience Store without Gas Station","Courthouse","Energy/Power Station","Fire Station","Library","Other - Public Services","Other - Services",
   "Other - Utility","Personal Services (Health/Beauty, Dry Cleaning, etc)","Police Station","Repair Services (Vehicle, Shoe, Locksmith, etc)",
   "Vehicle Repair Services","Drinking Water Treatment & Distribution","Mailing Center/Post Office","Transportation Terminal/Station","Wastewater Treatment Plant"],
 "Storage": ["Distribution Center","Non-Refrigerated Warehouse","Parking","Refrigerated Warehouse","Self-Storage Facility"],
 "Technology/Science": ["Data Center","Laboratory","Other - Technology/Science"]}
def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())
USE = {norm(t): u for u, ts in APPX_A.items() for t in ts}
GRID = {2025: 249, 2030: 259}  # kg/MWh, Appendix B projected grid factors
NON_BUILDING = re.compile(r"fens|park\b|street network|common|garden|cemetery|burying|square\b|mall\b|arboretum|parkway|esplanade|"
                          r"clock|fountain|statue|monument|bridge", re.I)

def pad(p):
    p = re.sub(r"\D", "", str(p or "").split(".")[0])
    return p.zfill(10) if p else ""

def blended(types_gfa, period):
    """Blend standard over 'Type (gfa),Type (gfa)'. Unmapped uses are dropped; returns None if nothing maps."""
    tot, acc = 0.0, 0.0
    for name, g in re.findall(r"([^,(]+?)\s*\(([\d.]+)\)", str(types_gfa or "")):
        u = USE.get(norm(name))
        if u:
            g = float(g); tot += g; acc += g * STD[u][period]
    return acc / tot if tot > 0 else None

def main():
    # Main year: BERDO "2025 reported" disclosure = calendar-year 2024 energy data (same data year as NYC and Seattle).
    # The 2026 disclosure (2025 data) is still incomplete (many 'Pending Reporting' / portfolio-level rows).
    df = pd.read_excel(D / "2025-reported-energy-and-water-metrics.xlsx", sheet_name="Data Disclosure", header=1)
    df = df[pd.to_numeric(df["BERDO ID"], errors="coerce").notna()].copy()
    n = lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["gfa"] = n("BERDO Emissions Gross Floor Area (Sq Ft)").where(n("BERDO Emissions Gross Floor Area (Sq Ft)") > 0, n("Reported Gross Floor Area (Sq Ft)"))
    df["tot"] = n("Estimated Total GHG Emissions (kgCO2e)")
    df["elec_kwh"] = n("Electricity Usage (kWh)"); df["elec_e"] = n("Electricity Emissions (kgCO2e)")
    df["steam"] = n("District Steam Usage (kBtu)") + n("District Hot Water Usage (kBtu)")
    df["oil"] = sum(n(f"{k} Usage (kBtu)") for k in ["Fuel Oil 1","Fuel Oil 2","Fuel Oil 4","Fuel Oil 5 and 6","Kerosene","Propane"])
    df["gas"] = n("Natural Gas Usage (kBtu)")

    # earlier years: did the building report fossil fuel?
    prior_fossil = set()
    for f, sheet, hdr in [("2024-reported-energy-and-water-metrics-1.xlsx", 0, 0), ("2026-berdo-data-disclosure-9.30.26.xlsx", "Buildings & Campuses", 0)]:
        p = pd.read_excel(D / f, sheet_name=sheet, header=hdr)
        cols = [c for c in p.columns if re.search(r"(Natural Gas|District Steam|District Hot Water|Fuel Oil|Kerosene|Propane) Usage", str(c))]
        fossil = p[cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1) > 0
        prior_fossil |= set(pd.to_numeric(p.loc[fossil, "BERDO ID"], errors="coerce").dropna().astype(int))

    # geometry: parcel centroid
    with zipfile.ZipFile(D / "parcels_2025_geojson.zip") as z:
        parcels = json.load(z.open(z.namelist()[0]))["features"]
    cent = {}
    for f in parcels:
        pid = f["properties"].get("MAP_PAR_ID")
        if pid and f.get("geometry"):
            try: cent[pid] = shape(f["geometry"]).representative_point()
            except Exception: pass
    lm = [f for f in json.load(open(D / "boston_landmarks_commission_blc_landmarks.json"))["features"]
          if f["properties"].get("Status") == "Approved Landmark" and not str(f["properties"].get("Demolished") or "").lower().startswith("yes")
          and not NON_BUILDING.search(f["properties"].get("Common_Name") or "") and f.get("geometry")]
    lm_geo = [shape(f["geometry"]).buffer(0) for f in lm]; lm_tree = STRtree(lm_geo)
    hd = [f for f in json.load(open(D / "boston_landmarks_commission_blc_historic_districts.json"))["features"]
          if not re.search(r"protection|^PA$", str(f["properties"].get("TYPE")), re.I) and f.get("geometry")]
    hd_geo = [shape(f["geometry"]).buffer(0) for f in hd]

    rows = []
    for _, r in df.iterrows():
        pid = pad(r["Tax Parcel ID"]); pt = cent.get(pid) or cent.get(pid[:7] + "000")
        lm_name = dist = None
        if pt is not None:
            hits = [i for i in lm_tree.query(pt) if lm_geo[i].contains(pt)]
            if hits: lm_name = lm[hits[0]]["properties"]["Common_Name"]
            dist = next((hd[i]["properties"]["HIST_NAME"] for i, g in enumerate(hd_geo) if g.contains(pt)), None)
        bid = pd.to_numeric(r["BERDO ID"], errors="coerce")
        fuel = ("steam" if r.steam > 0 else "oil" if r.oil > 0 else "gas" if r.gas > 0 else
                "incomplete" if (pd.notna(bid) and int(bid) in prior_fossil) else "all-electric")
        valid = r.gfa > 0 and r.tot > 0 and pt is not None
        s25 = blended(r["All Property Types and GFAs"], 0); s30 = blended(r["All Property Types and GFAs"], 1)
        # 2030: scale reported electricity emissions by the projected grid-factor change (Appendix B, 2030 vs 2025);
        # other fuels held at today's use. Keeps BERDO's own accounting basis (RECs, community choice) intact.
        implied = r.elec_e / (r.elec_kwh / 1000) if r.elec_kwh > 0 else None
        e30 = r.tot - r.elec_e + r.elec_e * GRID[2030] / GRID[2025]
        rows.append(dict(berdo_id=r["BERDO ID"], address=r["Parcel Address"], lat=pt.y if pt is not None else None, lon=pt.x if pt is not None else None,
            year_built=None, use=r["Largest Property Type"], gfa=r.gfa,
            landmark=lm_name, district=dist, group="landmark" if lm_name else "district" if dist else "other", fuel=fuel, valid=valid,
            ei_2025=r.tot / r.gfa if r.gfa > 0 else None, std_2025=s25, std_2030=s30,
            implied_grid_kg_mwh=implied, ei_2030=e30 / r.gfa if r.gfa > 0 else None,
            official_status=r["Reporting Compliance Status"], first_year=r["First Emissions Compliance Year (Projected)"]))
    res = pd.DataFrame(rows)
    res["over_2025"] = res.ei_2025 > res.std_2025
    res["over_2030"] = res.ei_2030 > res.std_2030
    res = res.astype({"over_2025": object, "over_2030": object}); res.loc[res.std_2025.isna(), "over_2025"] = None; res.loc[res.std_2030.isna(), "over_2030"] = None
    res.to_csv(OUT / "boston_buildings_2024data.csv", index=False)

    v = res[res.valid & (res.fuel != "incomplete") & res.std_2030.notna()].copy()
    v["over_2025"] = v.over_2025.astype(bool); v["over_2030"] = v.over_2030.astype(bool)
    def summ(g):
        return pd.Series({"n": len(g), "steam_%": 100*(g.fuel=="steam").mean(), "oil_%": 100*(g.fuel=="oil").mean(),
            "steam_or_oil_%": 100*g.fuel.isin(["steam","oil"]).mean(), "gas_%": 100*(g.fuel=="gas").mean(),
            "all_electric_%": 100*(g.fuel=="all-electric").mean(),
            "over_2025_%": 100*g.over_2025.mean(), "over_2030_%": 100*g.over_2030.mean()}).round(1)
    by_group = v.groupby("group")[["fuel","over_2025","over_2030"]].apply(summ)
    by_fuel = v.groupby("fuel")[["fuel","over_2025","over_2030"]].apply(summ)
    stat = res[res.valid].groupby("group")["official_status"].value_counts(normalize=True).mul(100).round(1).unstack(fill_value=0)
    lm_list = res[res.group == "landmark"][["address","landmark","use","fuel","ei_2025","std_2025","ei_2030","std_2030","official_status"]]
    lm_list.to_csv(OUT / "boston_landmark_matches.csv", index=False)
    with open(OUT / "boston_summary.txt", "w") as fh:
        fh.write("Boston BERDO exposure, BERDO 2025-reported disclosure (2024 energy data)\n")
        fh.write(f"rows {len(res)}, located {int(res.valid.sum())}, analysed {len(v)}, incomplete fuel {int((res.fuel=='incomplete').sum())}\n")
        med = res.implied_grid_kg_mwh.median()
        fh.write(f"median implied electricity factor in data: {med:.0f} kg/MWh; 2030 electricity emissions scaled by {GRID[2030]}/{GRID[2025]} (Appendix B)\n\n")
        fh.write("By group\n" + by_group.to_string() + "\n\nBy fuel\n" + by_fuel.to_string() +
                 "\n\nReporting compliance status by group (% of located buildings)\n" + stat.to_string() + "\n")
    print(open(OUT / "boston_summary.txt").read())

if __name__ == "__main__":
    main()
