# ============================================================
# GASTRIC CANCER HOSPITAL DISCHARGES — CHILE 2018–2022
# Peer-review ready analysis pipeline
#
# Outputs:
#   Table A  — Descriptive counts (quinquennium × sex × year)
#   Table 1  — Crude discharge rates (World Bank denominators)
#   Table 2  — Age-adjusted rates + Stang A, Gianicolo E. (2025) SE
#              (direct standardisation; 2024 Census reference)
#   Table 3  → computed in Joinpoint v6.0.1 (NCI, 2026)
#              input: {prefix}_table2_for_joinpoint.txt
#
# Methodological notes:
#   · Decennial DEIS codes split into 2 quinquennia (WEIGHT=0.5)
#     following PAHO/WHO harmonisation standard.
#   · ALL numerators use WEIGHT.sum() — correctly handles
#     fractional case counts from decennial-coded records.
#   · Direct standardisation: Σ_g(crude_g × W_g) / Σ_g W_g
#     where W_g = 2024 Census sex-specific stratum population.
#   · Variance: Stang A, Gianicolo E. (2025) Poisson approximation.
#     Var(R_adj) = 100,000² × Σ_g[(W_g/W_tot)² × cases_g/pop_g²]
#   · '2018–2022' summary = arithmetic mean of annual rates
#     (consistent with Joinpoint input series).
#
# Data sources:
#   · DEIS-MINSAL   : hospital discharge microdata (ICD-10 C16)
#   · INE Chile     : 2024 Population & Housing Census
#   · World Bank    : population estimates 2018–2022
#
# Google Colab usage:
#   1. Mount Google Drive (Section 0).
#   2. Place DEIS CSV files in the working directory.
#   3. Runtime → Run all.
#
# References:
#   Stang A, Gianicolo E. Dtsch Arztebl Int. 2025;122(14):387-92. doi:10.3238/arztebl.m2025.0072
#   Kim HJ et al. Permutation tests for joinpoint regression.
#   Stat Med. 2000;19(3):335-51.
#
# Authors : [pending]
# Study   : "Stagnation of Hospital Burden from Gastric Cancer
#            in Chile (2018–2022): Joinpoint Regression Analysis
#            with Demographic Adjustment to the 2024 Census"
# ============================================================


# ─────────────────────────────────────────────────────────────
# SECTION 0 — GOOGLE COLAB SETUP
# ─────────────────────────────────────────────────────────────
# Uncomment when running in Google Colab:
#
# from google.colab import drive
# drive.mount('/content/drive')
# import os; os.chdir('/content/drive/MyDrive/YOUR/DATA/FOLDER')
#
# Working directory must contain:
#   EGRE_DATOS_ABIERTOS_2018.csv
#   EGRE_DATOS_ABIERTOS_2019.csv
#   EGRE_DATOS_ABIERTOS_2020.csv
#   EGR_DATOS_ABIERTO_2021.csv
#   EGRE_DATOS_ABIERTOS_2022.csv


# ─────────────────────────────────────────────────────────────
# SECTION 1 — IMPORTS
# ─────────────────────────────────────────────────────────────
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


# ─────────────────────────────────────────────────────────────
# SECTION 2 — GLOBAL CONSTANTS
# ─────────────────────────────────────────────────────────────
YEARS      = [2018, 2019, 2020, 2021, 2022]
AGE_GROUPS = ['0-14', '15-64', '65+']

ICD10_C16 = [
    'C160', 'C161', 'C162', 'C163', 'C164',
    'C165', 'C166', 'C168', 'C169',
]

QUINQUENNIA_ORDER = [
    '00-04 years', '05-09 years', '10-14 years',
    '15-19 years', '20-24 years', '25-29 years',
    '30-34 years', '35-39 years', '40-44 years', '45-49 years',
    '50-54 years', '55-59 years', '60-64 years',
    '65-69 years', '70-74 years', '75-79 years',
    '80-84 years', '85+ years', 'Not reported',
]


# ─────────────────────────────────────────────────────────────
# SECTION 3 — POPULATION DATA (HARDCODED)
# ─────────────────────────────────────────────────────────────

# ── World Bank population denominators (Chile) ───────────────
# Source: World Bank. Population estimates and projections —
#         Chile. Washington D.C.: World Bank Group; 2024.
# Keys: (sex_key, age_group) → {year: int}
#   sex_key   : 'total' | 'male' | 'female'
#   age_group : 'total' | '0-14' | '15-64' | '65+'

WORLD_BANK_POP = {
    # ── TOTAL ────────────────────────────────────────────────
    ('total', 'total')  : {2018: 18_893_191, 2019: 19_197_744,
                           2020: 19_370_624, 2021: 19_456_334,
                           2022: 19_553_036},
    ('total', '0-14')   : {2018:  3_591_265, 2019:  3_590_541,
                           2020:  3_566_677, 2021:  3_520_932,
                           2022:  3_472_141},
    ('total', '15-64')  : {2018: 13_022_716, 2019: 13_240_877,
                           2020: 13_358_054, 2021: 13_414_555,
                           2022: 13_480_325},
    ('total', '65+')    : {2018:  2_279_210, 2019:  2_366_326,
                           2020:  2_445_893, 2021:  2_520_847,
                           2022:  2_600_569},
    # ── MALE ─────────────────────────────────────────────────
    ('male', 'total')   : {2018:  9_397_629, 2019:  9_549_157,
                           2020:  9_633_238, 2021:  9_672_367,
                           2022:  9_717_972},
    ('male', '0-14')    : {2018:  1_831_026, 2019:  1_830_172,
                           2020:  1_817_603, 2021:  1_794_009,
                           2022:  1_768_982},
    ('male', '15-64')   : {2018:  6_535_545, 2019:  6_645_743,
                           2020:  6_705_296, 2021:  6_733_999,
                           2022:  6_766_988},
    ('male', '65+')     : {2018:  1_031_057, 2019:  1_073_242,
                           2020:  1_110_339, 2021:  1_144_359,
                           2022:  1_182_002},
    # ── FEMALE ───────────────────────────────────────────────
    ('female', 'total') : {2018:  9_495_562, 2019:  9_648_587,
                           2020:  9_737_386, 2021:  9_783_967,
                           2022:  9_835_064},
    ('female', '0-14')  : {2018:  1_760_239, 2019:  1_760_369,
                           2020:  1_749_074, 2021:  1_726_923,
                           2022:  1_703_159},
    ('female', '15-64') : {2018:  6_487_171, 2019:  6_595_134,
                           2020:  6_652_758, 2021:  6_680_557,
                           2022:  6_713_337},
    ('female', '65+')   : {2018:  1_248_153, 2019:  1_293_084,
                           2020:  1_335_554, 2021:  1_376_488,
                           2022:  1_418_567},
}

# ── 2024 Census reference population (direct standardisation) ─
# Source: INE Chile. Síntesis de resultados Censo de Población
#         y Vivienda 2024. Santiago: INE; 2025.
# Keys: (sex_key, age_group) → int

CENSUS_2024 = {
    # Males
    ('male',   '0-14') : 1_668_530,
    ('male',  '15-64') : 6_171_457,
    ('male',    '65+') : 1_127_046,
    # Females
    ('female', '0-14') : 1_606_118,
    ('female','15-64') : 6_447_089,
    ('female',  '65+') : 1_460_192,
}
# Derived totals — sex-specific and overall
for _sex in ('male', 'female'):
    CENSUS_2024[(_sex, 'total')] = sum(
        CENSUS_2024[(_sex, g)] for g in AGE_GROUPS)
CENSUS_2024[('total', '0-14')]  = (CENSUS_2024[('male', '0-14')]
                                   + CENSUS_2024[('female', '0-14')])
CENSUS_2024[('total', '15-64')] = (CENSUS_2024[('male', '15-64')]
                                   + CENSUS_2024[('female', '15-64')])
CENSUS_2024[('total', '65+')]   = (CENSUS_2024[('male', '65+')]
                                   + CENSUS_2024[('female', '65+')]  )
CENSUS_2024[('total', 'total')] = (CENSUS_2024[('male', 'total')]
                                   + CENSUS_2024[('female', 'total')])


# ─────────────────────────────────────────────────────────────
# SECTION 4 — AGE-GROUP MAPPINGS
# ─────────────────────────────────────────────────────────────
# 4A. DEIS GRUPO_EDAD → list of quinquennia
#     Decennial codes  → 2 quinquennia, WEIGHT = 0.5 each
#     Quinquennial     → 1 quinquennium, WEIGHT = 1.0

DEIS_TO_QUINQUENNIUM = {
    # ── Paediatric (<1 year and 1–4 years) → 00-04 ──────────
    'menor a 7 días'           : ['00-04 years'],
    'MENOR DE 7 DIAS'          : ['00-04 years'],
    '7 A 27 DÍAS'              : ['00-04 years'],
    '28 DIAS A 2 MES'          : ['00-04 years'],
    '2 MESES A MENOS DE 1 AÑO' : ['00-04 years'],
    '2 MESES A MENOS DE 1 AÑO' : ['00-04 years'],
    'menor de un año'          : ['00-04 years'],
    'MENOR DE 1 AÑO'           : ['00-04 years'],
    '1 a 4 AÑOS'               : ['00-04 years'],
    '1 A 4 AÑOS'               : ['00-04 years'],
    # ── Direct quinquennia (new DEIS coding, 2015+) ──────────
    '5 A 9 AÑOS'    : ['05-09 years'],
    '10 A 14 AÑOS'  : ['10-14 years'],
    '15 A 19 AÑOS'  : ['15-19 years'],
    '20 A 24 AÑOS'  : ['20-24 years'],
    '25 A 29 AÑOS'  : ['25-29 years'],
    '30 A 34 AÑOS'  : ['30-34 years'],
    '35 A 39 AÑOS'  : ['35-39 years'],
    '40 A 44 AÑOS'  : ['40-44 years'],
    '45 A 49 AÑOS'  : ['45-49 years'],
    '50 A 54 AÑOS'  : ['50-54 years'],
    '55 A 59 AÑOS'  : ['55-59 years'],
    '60 A 64 AÑOS'  : ['60-64 years'],
    '65 A 69 AÑOS'  : ['65-69 years'],
    '70 A 74 AÑOS'  : ['70-74 years'],
    '75 A 79 AÑOS'  : ['75-79 years'],
    '80 A 84 AÑOS'  : ['80-84 years'],
    '85 A MAS'      : ['85+ years'],
    '85 Y MAS'      : ['85+ years'],
    # ── Decades (legacy coding) → 2 quinquennia, w=0.5 each ─
    '1 a 9'   : ['05-09 years'],
    '1 A 9'   : ['05-09 years'],
    '10 a 19' : ['10-14 years', '15-19 years'],
    '10 A 19' : ['10-14 years', '15-19 years'],
    '20 a 29' : ['20-24 years', '25-29 years'],
    '20 A 29' : ['20-24 years', '25-29 years'],
    '30 a 39' : ['30-34 years', '35-39 years'],
    '30 A 39' : ['30-34 years', '35-39 years'],
    '40 a 49' : ['40-44 years', '45-49 years'],
    '40 A 49' : ['40-44 years', '45-49 years'],
    '50 a 59' : ['50-54 years', '55-59 years'],
    '50 A 59' : ['50-54 years', '55-59 years'],
    '60 a 69' : ['60-64 years', '65-69 years'],
    '60 A 69' : ['60-64 years', '65-69 years'],
    '70 a 79' : ['70-74 years', '75-79 years'],
    '70 A 79' : ['70-74 years', '75-79 years'],
    '80 a 89' : ['80-84 years', '85+ years'],
    '80 A 89' : ['80-84 years', '85+ years'],
    '90 y más': ['85+ years'],
    '90 Y MÁS': ['85+ years'],
    '90 Y MAS': ['85+ years'],
}

# 4B. Quinquennium → analytical age group
QUINQUENNIUM_TO_AGEGROUP = {
    '00-04 years' : '0-14',
    '05-09 years' : '0-14',
    '10-14 years' : '0-14',
    '15-19 years' : '15-64',
    '20-24 years' : '15-64',
    '25-29 years' : '15-64',
    '30-34 years' : '15-64',
    '35-39 years' : '15-64',
    '40-44 years' : '15-64',
    '45-49 years' : '15-64',
    '50-54 years' : '15-64',
    '55-59 years' : '15-64',
    '60-64 years' : '15-64',
    '65-69 years' : '65+',
    '70-74 years' : '65+',
    '75-79 years' : '65+',
    '80-84 years' : '65+',
    '85+ years'   : '65+',
    'Not reported': 'Not reported',
}


# ─────────────────────────────────────────────────────────────
# SECTION 5 — DATA LOADING (DEIS-MINSAL)
# ─────────────────────────────────────────────────────────────

def _load_csv(filepath: Path) -> pd.DataFrame | None:
    """Load a DEIS CSV with encoding fallback (latin1 → utf-8)."""
    for enc in ('latin1', 'iso-8859-1', 'utf-8'):
        try:
            return pd.read_csv(
                filepath, sep=';', encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"    ✗ Cannot load {filepath.name}: {e}")
            return None
    print(f"    ✗ Encoding unresolved for {filepath.name}")
    return None


def load_deis_microdata(directory: str = '.') -> pd.DataFrame:
    """
    Load and concatenate the five annual DEIS CSV files,
    filtered to ICD-10 C16 principal diagnoses.

    Parameters
    ----------
    directory : str
        Path to folder containing the DEIS CSV files.

    Returns
    -------
    pd.DataFrame
        Standardised microdata (SEXO, GRUPO_EDAD, YEAR, ...).
    """
    ruta     = Path(directory)
    archivos = list(ruta.glob('*.csv'))
    loaded   = {}

    for filepath in archivos:
        name_up = filepath.name.upper()
        if any(t in name_up for t in [
                'TABLA', 'ANALISIS', 'CANCER_GASTRICO',
                'BANCOMUNDIAL', 'CENSO2024', 'CENSO']):
            continue
        for year in YEARS:
            if str(year) in name_up and (
                    'EGRE' in name_up or 'EGR' in name_up):
                df = _load_csv(filepath)
                if df is not None:
                    df['YEAR'] = year
                    loaded[year] = df
                    print(f"    ✓  {filepath.name:<45}  "
                          f"{len(df):>9,} records")
                break

    if not loaded:
        raise FileNotFoundError(
            "No DEIS discharge files found. Ensure the five annual "
            "CSVs (2018–2022) are in the working directory.")

    missing = [y for y in YEARS if y not in loaded]
    if missing:
        print(f"\\n    ⚠  Missing years: {missing}")

    df_all = pd.concat(loaded.values(), ignore_index=True)
    df_c16 = df_all[df_all['DIAG1'].isin(ICD10_C16)].copy()

    print(f"\\n    Total C16 records : {len(df_c16):,}")
    print(df_c16['YEAR'].value_counts().sort_index().to_string())

    for col in ['SEXO', 'GRUPO_EDAD',
                'GLOSA_REGION_RESIDENCIA', 'CONDICION_EGRESO']:
        if col in df_c16.columns:
            df_c16[col] = (df_c16[col]
                           .replace('*', 'Not reported')
                           .fillna('Not reported'))

    df_c16['SEXO'] = (
        df_c16['SEXO']
        .astype(str).str.upper().str.strip()
        .replace({'1': 'MALE', '2': 'FEMALE',
                  'HOMBRE': 'MALE', 'MUJER': 'FEMALE'})
    )

    if 'DIAS_ESTADA' in df_c16.columns:
        df_c16['DIAS_ESTADA'] = pd.to_numeric(
            df_c16['DIAS_ESTADA'], errors='coerce')

    return df_c16


# ─────────────────────────────────────────────────────────────
# SECTION 6 — QUINQUENNIUM EXPANSION
# ─────────────────────────────────────────────────────────────

def expand_to_quinquennia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand each microdata record to one row per quinquennium.

    · Decennial codes (e.g. '60 A 69')  → 2 rows, WEIGHT = 0.5
    · Quinquennial codes                 → 1 row,  WEIGHT = 1.0
    · Unrecognised codes                 → 1 row,  WEIGHT = 1.0,
                                           QUINQUENNIUM = 'Not reported'

    The fractional weight (0.5) ensures that a single discharge
    record contributes exactly 1.0 case in total across the two
    quinquennia it spans, preserving rate integrity when
    WEIGHT.sum() is used as numerator.

    Parameters
    ----------
    df : pd.DataFrame  C16 microdata with GRUPO_EDAD column.

    Returns
    -------
    pd.DataFrame
        Expanded frame with QUINQUENNIUM, WEIGHT, AGE_GROUP.
    """
    rows       = []
    age_series = df['GRUPO_EDAD'].astype(str).str.strip()

    for idx, row in df.iterrows():
        raw         = age_series[idx]
        quinquennia = DEIS_TO_QUINQUENNIUM.get(raw)
        if quinquennia is None:
            quinquennia = DEIS_TO_QUINQUENNIUM.get(
                raw.upper(), ['Not reported'])
        weight = 1.0 / len(quinquennia)
        for q in quinquennia:
            new_row               = row.copy()
            new_row['QUINQUENNIUM'] = q
            new_row['WEIGHT']       = weight
            rows.append(new_row)

    df_exp = pd.DataFrame(rows)
    df_exp['AGE_GROUP'] = (df_exp['QUINQUENNIUM']
                           .map(QUINQUENNIUM_TO_AGEGROUP))
    return df_exp


# ─────────────────────────────────────────────────────────────
# SECTION 7 — TABLE A: DESCRIPTIVE COUNTS MATRIX
# ─────────────────────────────────────────────────────────────

def _segment_counts(df_seg: pd.DataFrame,
                    sex_label: str,
                    year_label: str) -> list[dict]:
    """Compute count rows for one sex × year segment."""
    results = []
    n_total = round(df_seg['WEIGHT'].sum())

    results.append({
        'SEX': sex_label, 'VARIABLE': 'GRAND_TOTAL',
        'CATEGORY': 'GRAND_TOTAL',
        'N': n_total, 'YEAR': year_label,
    })

    # Quinquennia (weighted sums)
    cq = df_seg.groupby('QUINQUENNIUM')['WEIGHT'].sum()
    cq = cq.reindex(
        [q for q in QUINQUENNIA_ORDER if q in cq.index],
        fill_value=0)
    for cat, n in cq.items():
        results.append({
            'SEX': sex_label, 'VARIABLE': 'AGE_GROUP_QUINQUENNIUM',
            'CATEGORY': cat, 'N': n, 'YEAR': year_label,
        })
    results.append({
        'SEX': sex_label, 'VARIABLE': 'AGE_GROUP_QUINQUENNIUM',
        'CATEGORY': 'SUBTOTAL_AGE',
        'N': n_total, 'YEAR': year_label,
    })

    # Analytical age groups (weighted sums)
    for ag in AGE_GROUPS + ['Not reported']:
        n_ag = round(
            df_seg[df_seg['AGE_GROUP'] == ag]['WEIGHT'].sum())
        results.append({
            'SEX': sex_label, 'VARIABLE': 'ANALYTICAL_AGE_GROUP',
            'CATEGORY': ag, 'N': n_ag, 'YEAR': year_label,
        })
    results.append({
        'SEX': sex_label, 'VARIABLE': 'ANALYTICAL_AGE_GROUP',
        'CATEGORY': 'SUBTOTAL_AGE',
        'N': n_total, 'YEAR': year_label,
    })

    # Region of residence (row counts)
    for cat, n in (df_seg['GLOSA_REGION_RESIDENCIA']
                   .value_counts().items()):
        results.append({
            'SEX': sex_label, 'VARIABLE': 'REGION_OF_RESIDENCE',
            'CATEGORY': str(cat), 'N': n, 'YEAR': year_label,
        })
    results.append({
        'SEX': sex_label, 'VARIABLE': 'REGION_OF_RESIDENCE',
        'CATEGORY': 'SUBTOTAL_REGION',
        'N': n_total, 'YEAR': year_label,
    })

    # Discharge condition (row counts)
    for cat, n in (df_seg['CONDICION_EGRESO']
                   .value_counts().items()):
        results.append({
            'SEX': sex_label, 'VARIABLE': 'DISCHARGE_CONDITION',
            'CATEGORY': str(cat), 'N': n, 'YEAR': year_label,
        })
    results.append({
        'SEX': sex_label, 'VARIABLE': 'DISCHARGE_CONDITION',
        'CATEGORY': 'SUBTOTAL_DISCHARGE',
        'N': n_total, 'YEAR': year_label,
    })

    return results


def build_counts_table(df_exp: pd.DataFrame) -> pd.DataFrame:
    """
    Table A — Descriptive counts matrix (wide format).

    Dimensions : sex × variable × category × year.
    Age counts : WEIGHT.sum() — handles fractional cases.
    Non-age    : row counts (region, discharge condition).

    Returns
    -------
    pd.DataFrame  columns: SEX, VARIABLE, CATEGORY,
                           2018, 2019, 2020, 2021, 2022, TOTAL_5Y
    """
    all_rows = []
    for year in YEARS + [None]:
        year_label = str(year) if year else 'TOTAL_5Y'
        df_yr = df_exp[df_exp['YEAR'] == year] if year else df_exp
        for sex_label in ['GENERAL', 'MALE', 'FEMALE']:
            df_seg = (df_yr if sex_label == 'GENERAL'
                      else df_yr[df_yr['SEXO'] == sex_label])
            all_rows += _segment_counts(df_seg, sex_label, year_label)

    df_long = pd.DataFrame(all_rows)
    df_wide = (
        df_long
        .pivot_table(index=['SEX', 'VARIABLE', 'CATEGORY'],
                     columns='YEAR', values='N', aggfunc='first')
        .reset_index()
    )

    year_cols = [str(y) for y in YEARS] + ['TOTAL_5Y']
    present   = [c for c in year_cols if c in df_wide.columns]
    df_wide   = df_wide[['SEX', 'VARIABLE', 'CATEGORY'] + present]

    sex_ord = {'GENERAL': 0, 'MALE': 1, 'FEMALE': 2}
    var_ord = {
        'GRAND_TOTAL': 0, 'AGE_GROUP_QUINQUENNIUM': 1,
        'ANALYTICAL_AGE_GROUP': 2,
        'REGION_OF_RESIDENCE': 3, 'DISCHARGE_CONDITION': 4,
    }
    q_ord = {q: i for i, q in enumerate(QUINQUENNIA_ORDER)}

    df_wide['_s'] = df_wide['SEX'].map(sex_ord)
    df_wide['_v'] = df_wide['VARIABLE'].map(var_ord)
    df_wide['_c'] = df_wide.apply(
        lambda r: q_ord.get(r['CATEGORY'], 999)
        if r['VARIABLE'] == 'AGE_GROUP_QUINQUENNIUM'
        else r['CATEGORY'], axis=1)
    df_wide = (df_wide
               .sort_values(['_s', '_v', '_c'])
               .drop(columns=['_s', '_v', '_c'])
               .reset_index(drop=True))
    return df_wide


# ─────────────────────────────────────────────────────────────
# SECTION 8 — TABLE 1: CRUDE RATES
# ─────────────────────────────────────────────────────────────

def _weighted_cases_by_year(df_exp: pd.DataFrame,
                             sex_filter: str | None,
                             age_group: str) -> pd.Series:
    """
    WEIGHT.sum() per year for one sex/age stratum.

    Using WEIGHT.sum() instead of .size() is critical:
    decennial-coded records expand to 2 rows (WEIGHT=0.5 each),
    so .size() would double-count them.
    """
    df_f = df_exp.copy()
    if sex_filter:
        df_f = df_f[df_f['SEXO'] == sex_filter]
    df_f = df_f[df_f['AGE_GROUP'] == age_group]
    return (df_f.groupby('YEAR')['WEIGHT']
                .sum()
                .reindex(YEARS, fill_value=0))


def build_crude_rates_table(df_exp: pd.DataFrame) -> pd.DataFrame:
    """
    Table 1 — Crude hospital discharge rates for ICD-10 C16
    by sex, age group, and year. Chile, 2018–2022
    (per 100,000 inhabitants).

    Numerator  : WEIGHT.sum() per stratum.
    Denominator: WORLD_BANK_POP (hardcoded, Section 3).
    '2018–2022': arithmetic mean of the five annual crude rates.

    Returns
    -------
    pd.DataFrame
    """
    config = [
        ('General', None,     'total'),
        ('Male',    'MALE',   'male'),
        ('Female',  'FEMALE', 'female'),
    ]
    age_label = {'0-14': '0–14', '15-64': '15–64', '65+': '≥65'}

    rows = []
    for disp_sex, sex_filter, wb_sex in config:
        for ag in AGE_GROUPS:
            cases = _weighted_cases_by_year(df_exp, sex_filter, ag)
            pops  = {y: WORLD_BANK_POP[(wb_sex, ag)][y] for y in YEARS}
            rates = {y: round(cases[y] / pops[y] * 100_000, 2)
                     for y in YEARS}
            mean_rate = round(sum(rates.values()) / len(YEARS), 2)

            row = {
                'Sex'              : disp_sex,
                'Age group (years)': age_label[ag],
                '2018–2022'        : mean_rate,
            }
            row.update({str(y): rates[y] for y in YEARS})
            rows.append(row)

    cols = (['Sex', 'Age group (years)', '2018–2022']
            + [str(y) for y in YEARS])
    return pd.DataFrame(rows)[cols]


# ─────────────────────────────────────────────────────────────
# SECTION 9 — TABLE 2: AGE-ADJUSTED RATES + STANG & GIANICOLO (2025) SE
# ─────────────────────────────────────────────────────────────

def _direct_standardisation_with_variance(
        df_exp: pd.DataFrame,
        sex_filter: str | None,
        wb_sex_key: str,
        census_sex_key: str,
        year: int) -> tuple[float, float]:
    """
    Directly age-standardised rate + Stang & Gianicolo (2025) SE.

    Formula — adjusted rate
    -----------------------
    R_adj = Σ_g (crude_g × W_g) / Σ_g W_g

    Formula — variance (Stang & Gianicolo 2025,
                        Dtsch Arztebl Int 122(14):387-92)
    ------------------------------------------------------------
    Var(R_adj) = 100,000² × Σ_g [(W_g / W_tot)² × cases_g / pop_g²]

    Poisson assumption: Var(cases_g) ≈ E[cases_g] ≈ cases_g.
    Numerator uses WEIGHT.sum() — handles fractional case counts.
    Strata with cases_g = 0 contribute 0 to variance (safe
    division; avoids zero-case issue in 0–14 stratum).

    Parameters
    ----------
    df_exp         : expanded microdata
    sex_filter     : 'MALE' | 'FEMALE' | None  (None = all)
    wb_sex_key     : 'male' | 'female' | 'total'
    census_sex_key : 'male' | 'female' | 'total'
    year           : 2018–2022

    Returns
    -------
    tuple (adjusted_rate, standard_error)
        Both per 100,000 inhabitants, rounded to 4 dp.
    """
    df_yr = df_exp[df_exp['YEAR'] == year].copy()
    if sex_filter:
        df_yr = df_yr[df_yr['SEXO'] == sex_filter]

    W_total      = CENSUS_2024[(census_sex_key, 'total')]
    weighted_sum = 0.0
    variance     = 0.0

    for ag in AGE_GROUPS:
        cases_g = df_yr[df_yr['AGE_GROUP'] == ag]['WEIGHT'].sum()
        pop_g   = WORLD_BANK_POP[(wb_sex_key, ag)][year]
        W_g     = CENSUS_2024[(census_sex_key, ag)]

        crude_g       = cases_g / pop_g * 100_000
        weighted_sum += crude_g * W_g

        # Stang & Gianicolo (2025): variance contribution of stratum g
        if cases_g > 0:
            variance += (W_g / W_total) ** 2 * (cases_g / pop_g ** 2)

    variance  *= (100_000 ** 2)
    adj_rate   = round(weighted_sum / W_total, 4)
    std_error  = round(np.sqrt(variance), 4)
    return adj_rate, std_error


def build_adjusted_rates_table(df_exp: pd.DataFrame) -> pd.DataFrame:
    """
    Table 2 — Age-adjusted discharge rates + Stang & Gianicolo (2025) SE
    by sex and year. Chile, 2018–2022 (per 100,000 inhabitants).

    Standardisation : direct method
    Reference pop.  : CENSUS_2024 (hardcoded, Section 3)
    Age strata      : 0–14, 15–64, ≥65 years
    SE              : Stang & Gianicolo (2025) Poisson approximation

    Returns
    -------
    pd.DataFrame  columns: Sex | Year | Adjusted rate* |
                           SE (Stang & Gianicolo 2025)
    """
    config = [
        ('General', None,     'total',  'total'),
        ('Male',    'MALE',   'male',   'male'),
        ('Female',  'FEMALE', 'female', 'female'),
    ]
    rows = []
    for disp_sex, sex_filter, wb_key, census_key in config:
        for year in YEARS:
            rate, se = _direct_standardisation_with_variance(
                df_exp, sex_filter, wb_key, census_key, year)
            rows.append({
                'Sex'                          : disp_sex,
                'Year'                         : year,
                'Adjusted rate*'               : round(rate, 2),
                'SE (Stang & Gianicolo 2025)'  : round(se,   4),
            })

    return pd.DataFrame(rows)[
        ['Sex', 'Year', 'Adjusted rate*', 'SE (Stang & Gianicolo 2025)']]


# ─────────────────────────────────────────────────────────────
# SECTION 10 — VALIDATION REPORT
# ─────────────────────────────────────────────────────────────

def run_validation(df_c16: pd.DataFrame,
                   df_exp: pd.DataFrame,
                   t1: pd.DataFrame,
                   t2: pd.DataFrame) -> None:
    """
    Structured validation report for peer-review reproducibility.

    Checks:
      1. Record counts and expansion ratio
      2. Age-code mapping completeness
      3. Sex internal consistency (General ≈ Male + Female)
      4. Printed Tables 1 & 2 for manual audit
      5. Male/Female crude rate ratios (≥65 years)
    """
    SEP = '─' * 62

    print(f"\\n{'═'*62}")
    print("  VALIDATION REPORT")
    print(f"{'═'*62}")

    # ── 1. Record counts ─────────────────────────────────────
    print(f"\\n  1. RECORD COUNTS")
    print(SEP)
    n_orig = len(df_c16)
    n_exp  = len(df_exp)
    print(f"     Original C16 records (excl. unknown age) : "
          f"{n_orig:>8,}")
    print(f"     Expanded records                          : "
          f"{n_exp:>8,}")
    print(f"     Expansion ratio                           : "
          f"{n_exp/n_orig:>8.4f}")
    print(f"\\n     Records by year:")
    for yr, n in df_c16['YEAR'].value_counts().sort_index().items():
        print(f"       {yr}: {n:,}")

    # ── 2. Age-code mapping ───────────────────────────────────
    print(f"\\n  2. AGE-CODE MAPPING")
    print(SEP)
    nr = df_exp[df_exp['QUINQUENNIUM'] == 'Not reported']
    if len(nr) == 0:
        print("     ✓ All age codes successfully mapped.")
    else:
        pct = len(nr) / len(df_exp) * 100
        print(f"     ⚠  Unmapped: {len(nr):,} rows ({pct:.2f}%)")
        for code, cnt in nr['GRUPO_EDAD'].value_counts().items():
            print(f"       '{code}': {cnt}")

    # ── 3. Sex consistency ────────────────────────────────────
    print(f"\\n  3. SEX CONSISTENCY  (General ≈ Male + Female)")
    print(SEP)
    for yr in YEARS:
        gen = round(df_exp[df_exp['YEAR'] == yr]['WEIGHT'].sum())
        mal = round(df_exp[(df_exp['YEAR'] == yr) &
                           (df_exp['SEXO'] == 'MALE')]['WEIGHT'].sum())
        fem = round(df_exp[(df_exp['YEAR'] == yr) &
                           (df_exp['SEXO'] == 'FEMALE')]['WEIGHT'].sum())
        diff = gen - mal - fem
        flag = '✓' if abs(diff) <= 2 else '⚠'
        print(f"     {flag}  {yr}  General={gen:,}  "
              f"Male={mal:,}  Female={fem:,}  Δ={diff}")

    # ── 4. Table summaries ────────────────────────────────────
    print(f"\\n  4. TABLE 1 — CRUDE RATES (computed values)")
    print(SEP)
    print(t1.to_string(index=False))

    print(f"\\n  5. TABLE 2 — ADJUSTED RATES + SE (computed values)")
    print(SEP)
    print(t2.to_string(index=False))
    print(f"\\n     → Update article Tables 1 & 2 and all")
    print(f"       in-text figures with the values above.")

    # ── 5. M/F rate ratios ────────────────────────────────────
    print(f"\\n  6. MALE/FEMALE CRUDE RATE RATIO (≥65, per year)")
    print(SEP)
    for yr in YEARS:
        m = t1[(t1['Sex'] == 'Male') &
               (t1['Age group (years)'] == '≥65')][str(yr)].values
        f = t1[(t1['Sex'] == 'Female') &
               (t1['Age group (years)'] == '≥65')][str(yr)].values
        if m.size and f.size and f[0] > 0:
            print(f"     {yr}:  M={m[0]:>7.2f}  "
                  f"F={f[0]:>6.2f}  M/F ratio={m[0]/f[0]:.2f}")

    print(f"\\n{'═'*62}\\n")


# ─────────────────────────────────────────────────────────────
# SECTION 11 — EXPORT
# ─────────────────────────────────────────────────────────────

def export_results(counts_table: pd.DataFrame,
                   crude_table: pd.DataFrame,
                   adjusted_table: pd.DataFrame,
                   prefix: str = 'gastric_cancer_chile') -> None:
    """
    Export all tables to CSV, Excel, and Joinpoint-ready TXT.

    Output files
    ------------
    {prefix}_tableA_counts.csv
    {prefix}_table1_crude_rates.csv
    {prefix}_table2_adjusted_rates.csv
    {prefix}_all_tables.xlsx            (3 sheets)
    {prefix}_table2_for_joinpoint.txt   (tab-sep; Rate + SE)

    Joinpoint v6.0.1 settings for TXT import
    -----------------------------------------
    Input data type : Rates with Standard Errors
    Rate column     : Rate
    SE column       : Standard_Error
    Variance method : External (Stang & Gianicolo 2025)
    Max joinpoints  : 0
    Test method     : Permutation (Kim et al., Stat Med 2000)
    """
    counts_table.to_csv(
        f'{prefix}_tableA_counts.csv', index=False, sep=';')
    crude_table.to_csv(
        f'{prefix}_table1_crude_rates.csv', index=False, sep=';')
    adjusted_table.to_csv(
        f'{prefix}_table2_adjusted_rates.csv', index=False, sep=';')

    xlsx_path = f'{prefix}_all_tables.xlsx'
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        counts_table.to_excel(
            writer, sheet_name='TableA_Counts', index=False)
        crude_table.to_excel(
            writer, sheet_name='Table1_CrudeRates', index=False)
        adjusted_table.to_excel(
            writer, sheet_name='Table2_AdjustedRates', index=False)

    # Joinpoint-ready: Sex | Year | Rate | Standard_Error
    jp_path = f'{prefix}_table2_for_joinpoint.txt'
    jp_df   = adjusted_table[['Sex', 'Year',
                               'Adjusted rate*',
                               'SE (Stang & Gianicolo 2025)']].copy()
    jp_df.columns = ['Sex', 'Year', 'Rate', 'Standard_Error']
    jp_df.to_csv(jp_path, index=False, sep='\t')

    print("\\n  Exported files:")
    for fname in [
        f'{prefix}_tableA_counts.csv',
        f'{prefix}_table1_crude_rates.csv',
        f'{prefix}_table2_adjusted_rates.csv',
        xlsx_path,
        f'{jp_path}  ← Joinpoint v6.0.1 input (Rate + SE)',
    ]:
        print(f"    · {fname}")


# ─────────────────────────────────────────────────────────────
# SECTION 12 — MAIN
# ─────────────────────────────────────────────────────────────

def main(data_directory: str = '.') -> None:
    """
    Full analysis pipeline.

    Parameters
    ----------
    data_directory : str
        Path to folder containing DEIS CSV files.
        Default '.' = current working directory.
    """
    HDR = '═' * 62

    print(HDR)
    print("  GASTRIC CANCER — HOSPITAL DISCHARGES CHILE 2018–2022")
    print("  Direct Standardisation | 2024 Census | Joinpoint")
    print(HDR)

    # ── Population data summary ───────────────────────────────
    print(f"\\n[0/6] Population data (hardcoded constants)")
    print(f"    ✓  World Bank denominators  : 2018–2022, 3 strata × 3 sex")
    print(f"    ✓  2024 Census reference    : "
          f"{CENSUS_2024[('total','total')]:,} inhabitants")

    # ── STEP 1: Load DEIS microdata ───────────────────────────
    print(f"\\n[1/6] Loading DEIS-MINSAL microdata (ICD-10 C16)...")
    df_c16 = load_deis_microdata(data_directory)

    n_before = len(df_c16)
    df_c16   = df_c16[df_c16['GRUPO_EDAD'] != 'Not reported'].copy()
    n_after  = len(df_c16)
    print(f"\\n    Removed {n_before - n_after:,} records with "
          f"unknown age ({(n_before-n_after)/n_before*100:.2f}%)")
    print(f"    Retained for analysis: {n_after:,} records")

    # ── STEP 2: Expand to quinquennia ─────────────────────────
    print(f"\\n[2/6] Expanding records to quinquennia...")
    df_exp = expand_to_quinquennia(df_c16)
    print(f"    Original : {len(df_c16):,} records")
    print(f"    Expanded : {len(df_exp):,} rows  "
          f"(ratio: {len(df_exp)/len(df_c16):.4f})")

    unmapped = df_exp[df_exp['QUINQUENNIUM'] == 'Not reported']
    if len(unmapped):
        print(f"    ⚠  Unmapped: {len(unmapped):,} rows "
              f"({len(unmapped)/len(df_exp)*100:.2f}%)")
    else:
        print("    ✓  All age codes mapped.")

    # ── STEP 3: Table A — Counts ──────────────────────────────
    print(f"\\n[3/6] Building Table A (descriptive counts)...")
    table_A = build_counts_table(df_exp)
    print(f"    Shape: {table_A.shape}")

    # ── STEP 4: Table 1 — Crude rates ────────────────────────
    print(f"\\n[4/6] Computing Table 1 — Crude rates...")
    table_1 = build_crude_rates_table(df_exp)

    # ── STEP 5: Table 2 — Adjusted rates + Stang & Gianicolo SE ──
    print(f"\\n[5/6] Computing Table 2 — Age-adjusted rates "
          f"(Stang & Gianicolo 2025 SE)...")
    table_2 = build_adjusted_rates_table(df_exp)

    # ── STEP 6: Validate & export ─────────────────────────────
    print(f"\\n[6/6] Running validation and exporting...")
    run_validation(df_c16, df_exp, table_1, table_2)
    export_results(table_A, table_1, table_2)

    print(f"\\n{HDR}")
    print("  PIPELINE COMPLETE")
    print(HDR)
    print("""
  METHODOLOGICAL NOTES
  ─────────────────────────────────────────────────────────
  CRUDE RATES (Table 1)
    Numerator  : WEIGHT.sum() per stratum — fractional weights
                 (0.5) correctly handle decennial DEIS codes.
    Denominator: World Bank sex- and age-stratified population
                 estimates, Chile 2018–2022.
    Unit       : per 100,000 inhabitants.
    '2018–2022': arithmetic mean of the five annual crude rates.

  ADJUSTED RATES (Table 2)
    Method     : direct age standardisation.
    Formula    : Σ_g (crude_g × W_g) / Σ_g W_g
    Reference  : 2024 Census age distribution (INE Chile, 2025).
    Age strata : 0–14, 15–64, ≥65 years.
    Unit       : per 100,000 inhabitants.

  STANDARD ERROR — STANG & GIANICOLO (2025)
    Formula    : SE = sqrt(100,000² × Σ_g[(W_g/W_tot)² × n_g/P_g²])
    Assumption : Poisson variance for discharge counts.
    Reference  : Stang A, Gianicolo E. Age standardization of
                 epidemiological frequency measures.
                 Dtsch Arztebl Int. 2025;122(14):387-92.
                 doi:10.3238/arztebl.m2025.0072
    Use        : Standard_Error column in Joinpoint v6.0.1 input.

  AGE-GROUP HARMONISATION
    Decennial codes (legacy DEIS system) split into two
    quinquennia with WEIGHT = 0.5 per quinquennium.
    Standard: PAHO/WHO temporal series harmonisation.
    All rate numerators use WEIGHT.sum(), not row counts.

  TABLE 3 (APC / Joinpoint regression)
    Input file : gastric_cancer_chile_table2_for_joinpoint.txt
    Software   : Joinpoint Regression Program v6.0.1 (NCI, 2026).
    Settings   : max 0 joinpoints (n=5 observations);
                 External SE (Stang & Gianicolo 2025);
                 permutation test (Kim et al., Stat Med 2000).
  ─────────────────────────────────────────────────────────
""")


# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    main('.')
