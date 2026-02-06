import geopandas as gpd
import pandas as pd

# ======================
# PATHS
# ======================
in_path = r"C:\Users\leguy\OneDrive\Documents\SEM\3A SEM\projet zaz\file\quartier.shp"
out_path = r"C:\Users\leguy\OneDrive\Documents\SEM\3A SEM\projet zaz\file\electricite29.shp" #changer les paths 

# ======================
# PARAMS
# ======================
TARGET_NEIGHBORHOOD = "29"  #mettre le quartier voulu
MIN_HPF = 3.3  # minimum height per floor (m)

# ======================
# LOAD
# ======================
gdf = gpd.read_file(in_path)

# ======================
# FILTER: neighborhood 
# ======================
if "neighborho" not in gdf.columns:
    raise ValueError("❌ La colonne 'neighborho' est introuvable.")

gdf = gdf[gdf["neighborho"].astype(str).str.contains(TARGET_NEIGHBORHOOD, na=False)].copy()

# ======================
# CHECK REQUIRED SOURCE COLUMNS
# ======================
required = ["nb_niveaux", "BDNB_haute", "ONB_id", "constructi", "usage_main"]
missing = [c for c in required if c not in gdf.columns]
if missing:
    raise ValueError(f"❌ Colonnes source manquantes : {missing}")

gdf = gdf[gdf["heating_en"] == "electricite"]

# ======================
# CREATE / FILL TARGET COLUMNS
# ======================
gdf["floors_bg"] = 0
gdf["floors_ag"] = gdf["nb_niveaux"]

gdf["height_bg"] = gdf["BDNB_haute"]
gdf["height_ag"] = 0

gdf["void_deck"] = 0
gdf["year"] = gdf["constructi"]
year = pd.to_numeric(gdf["year"], errors="coerce")

gdf["const_type"] = None

gdf.loc[(year >= 1000) & (year <= 1920), "const_type"] = "STANDARD1"
gdf.loc[(year >= 1921) & (year <= 1970), "const_type"] = "STANDARD2"
gdf.loc[(year >= 1971) & (year <= 1980), "const_type"] = "STANDARD3"
gdf.loc[(year >= 1981) & (year <= 2000), "const_type"] = "STANDARD4"
gdf.loc[year >= 2001, "const_type"] = "STANDARD5"
#cette partie est à améliorer soit grâce au dpe ou/et en recréant des standards dans CEA


# usage mapping
gdf["use_type1"] = gdf["usage_main"].astype(str).str.strip()
gdf["use_type1"] = gdf["use_type1"].map({
    "Résidentiel collectif": "MULTI_RES",
    "Résidentiel individuel": "SINGLE_RES",
}).fillna("OFFICE")
#tous les autres que Résidentiel collectif et Résidentiel individuel sont attribué à office par defaut (point d'amélioration)

gdf["use_type1r"] = 1
gdf["use_type2"] = "NONE"
gdf["use_type2r"] = 0
gdf["use_type3"] = "NONE"
gdf["use_type3r"] = 0  


# ======================
# ENFORCE MIN HEIGHT PER FLOOR (fix only bad buildings)
# ======================
h = pd.to_numeric(gdf["height_ag"], errors="coerce")
f = pd.to_numeric(gdf["floors_ag"], errors="coerce")

# Avoid division by zero / invalid floors
f = f.where(f > 0)

gdf["height_ag"] = h.where((h / f) >= MIN_HPF, f * MIN_HPF)
gdf["height_bg"] = gdf["height_ag"]

# ======================
# KEEP ONLY FINAL COLUMNS (+ geometry)
# ======================
keep_cols = [
    "floors_bg", "floors_ag",
    "height_bg", "height_ag",
    "void_deck", "year",
    "const_type",
    "use_type1", "use_type1r",
    "use_type2", "use_type2r",
    "use_type3", "use_type3r",  
    gdf.geometry.name
]
gdf = gdf[keep_cols].copy()

# ======================
# DROP ROWS WITH MISSING VALUES
# ======================
print("NA par colonne (avant dropna):")
print(gdf.isna().sum())

before = len(gdf)
gdf = gdf.dropna().copy()
after = len(gdf)

print(f"Lignes avant dropna: {before} | après dropna: {after} | supprimées: {before - after}")

# ======================
# UNIQUE BUILDING NAMES FOR CEA
# ======================
gdf = gdf.reset_index(drop=True)
gdf["name"] = "B_" + gdf.index.astype(str)

gdf = gdf[["name"] + [c for c in gdf.columns if c != "name"]]

gdf = gdf[gdf["name"] != "B_232"]
#ligne exemple pour supprimer les immeuble à la main qui ne fonctionne pas, souvent ce sont ceux à qui on a changer la taille (point de vigilance si on veut complètement automatiser le process)


# ======================
# EXPORT
# ======================
gdf.to_file(out_path)
print("✅ Export terminé :", out_path)
print(gdf.shape)