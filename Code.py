# ============================================================
# GASTRIC CANCER HOSPITAL DISCHARGES — CHILE 2018–2022
# Final analysis script for Google Colab
#
# Produces:
#   [A] Table of interest variables  (counts by quinquennium,
#       region, discharge condition × sex × year)
#   [B] Table 1 — Crude discharge rates by sex, age group
#       and year (World Bank denominators)
#   [C] Table 2 — Age-adjusted discharge rates by sex and year
#       (direct standardization; 2024 Census as reference)
#
#   Table 3 (APC / Joinpoint) → computed externally in
#   Joinpoint Regression Program v6.0.1 (NCI, 2026)
#   using tabla2_tasas_ajustadas.csv as input.
#
# Data sources:
#   · DEIS-MINSAL: hospital discharge microdata (ICD-10 C16)
#   · 2024 Population & Housing Census (INE Chile)
#   · World Bank: population estimates 2018–2022
#
# How to run in Google Colab:
#   1. Mount Google Drive (see Section 0).
#   2. Set WORKING_DIR to the folder containing the 5 DEIS CSVs.
#   3. Run all cells (Runtime → Run all).
#
# Authors: [pending]
# Study: "Stagnation of Hospital Burden from Gastric Cancer in
#         Chile (2018–2022): Joinpoint Regression Analysis with
#         Demographic Adjustment to the 2024 Census"
# ============================================================


# ─────────────────────────────────────────────────────────────
# SECTION 0 — GOOGLE COLAB SETUP
# ─────────────────────────────────────────────────────────────
# Uncomment the three lines below when running in Google Colab:
#
# from google.colab import drive
# drive.mount('/content/drive')
# import os; os.chdir('/content/drive/MyDrive/YOUR/DATA/FOLDER')
#
# The working directory must contain:
#   EGRE_DATOS_ABIERTOS_2018.csv
#   EGRE_DATOS_ABIERTOS_2019.csv
#   EGRE_DATOS_ABIERTOS_2020.csv
#   EGR_DATOS_ABIERTO_2021.csv
#   EGRE_DATOS_ABIERTOS_2022.csv
# ─────────────────────────────────────────────────────────────


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

YEARS = [2018, 2019, 2020, 2021, 2022]

# ICD-10 C16.x codes present in DEIS files
ICD10_C16 = [
    'C160', 'C161', 'C162', 'C163', 'C164',
    'C165', 'C166', 'C168', 'C169'
]

# Analytical age groups (matching article strata)
AGE_GROUPS = ['0-14', '15-64', '65+']

# Canonical quinquennium order (for output table)
QUINQUENNIA_ORDER = [
    '00-04 years', '05-09 years', '10-14 years',
    '15-19 years', '20-24 years', '25-29 years',
    '30-34 years', '35-39 years', '40-44 years', '45-49 years',
    '50-54 years', '55-59 years', '60-64 years',
    '65-69 years', '70-74 years', '75-79 years',
    '80-84 years', '85+ years', 'Not reported',
]

# ── World Bank population denominators (Chile) ───────────────
# Source: World Bank, Population estimates and projections —
#         Chile. Washington D.C.: World Bank Group; 2024.
# Keys: (sex_key, age_group_key)
# sex_key    : 'total' | 'male' | 'female'
# age_group  : '0-14' | '15-64' | '65+' | 'total'

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

# ── 2024 Census reference population (direct standardization) ─
# Source: INE Chile. Síntesis de resultados Censo de Población
#         y Vivienda 2024. Santiago: INE; 2025.

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
# Derived totals (sex-specific and overall)
for sex in ('male', 'female'):
    CENSUS_2024[(sex, 'total')] = sum(
        CENSUS_2024[(sex, g)] for g in AGE_GROUPS
    )
CENSUS_2024[('total', '0-14')]  = CENSUS_2024[('male','0-14')]  + CENSUS_2024[('female','0-14')]
CENSUS_2024[('total', '15-64')] = CENSUS_2024[('male','15-64')] + CENSUS_2024[('female','15-64')]
CENSUS_2024[('total', '65+')]   = CENSUS_2024[('male','65+')]   + CENSUS_2024[('female','65+')]
CENSUS_2024[('total', 'total')] = CENSUS_2024[('male','total')] + CENSUS_2024[('female','total')]


# ─────────────────────────────────────────────────────────────
# SECTION 3 — AGE-GROUP MAPPINGS
# ─────────────────────────────────────────────────────────────
# Maps each DEIS GRUPO_EDAD label → quinquennium or quinquennia.
# Decades (legacy coding) are split into two equal quinquennia
# (weight = 0.5 each), following PAHO/WHO harmonisation standard.

# 3A. DEIS label → list of quinquennia (for Table A counts)
DEIS_TO_QUINQUENNIUM = {
    # ── Paediatric groups → 00-04 years ──────────────────────
    'menor a 7 días'           : ['00-04 years'],
    'MENOR DE 7 DIAS'          : ['00-04 years'],
    '7 A 27 DÍAS'              : ['00-04 years'],
    '28 DIAS A 2 MES'          : ['00-04 years'],
    '2 ,ESES A MENOS DE 1 AÑO' : ['00-04 years'],   # typo in source
    '2 MESES A MENOS DE 1 AÑO' : ['00-04 years'],
    'menor de un año'          : ['00-04 years'],
    'MENOR DE 1 AÑO'           : ['00-04 years'],
    '1 a 4 AÑOS'               : ['00-04 years'],
    '1 A 4 AÑOS'               : ['00-04 years'],
    # ── Direct quinquennia (new coding system) ────────────────
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
    # ── Decades (legacy coding) → two quinquennia, w=0.5 each ─
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

# 3B. Quinquennium → analytical age group (for rate calculations)
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
# SECTION 4 — DATA LOADING AND CLEANING
# ─────────────────────────────────────────────────────────────

def _load_csv(filepath: Path) -> pd.DataFrame | None:
    """Load a single DEIS CSV with robust encoding handling."""
    for enc in ('latin1', 'iso-8859-1', 'utf-8'):
        try:
            df = pd.read_csv(filepath, sep=';', encoding=enc, low_memory=False)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"    ✗ Cannot load {filepath.name}: {e}")
            return None
    print(f"    ✗ Encoding not resolved for {filepath.name}")
    return None


def load_deis_microdata(directory: str = '.') -> pd.DataFrame:
    """
    Load and concatenate the five annual DEIS CSV files.

    Expected filenames must contain the year (2018–2022) and
    'EGRE' or 'EGR' anywhere in the name (case-insensitive).

    Parameters
    ----------
    directory : str
        Path to folder containing the DEIS CSV files.

    Returns
    -------
    pd.DataFrame
        Filtered dataframe with ICD-10 C16.x records only,
        with standardised column values.
    """
    ruta = Path(directory)
    archivos = list(ruta.glob('*.csv'))
    loaded = {}

    for filepath in archivos:
        name_upper = filepath.name.upper()
        # Skip our own output files
        if any(tag in name_upper for tag in
               ['TABLA', 'ANALISIS', 'CANCER_GASTRICO', 'CENSO', 'BANCO']):
            continue
        for year in YEARS:
            if str(year) in name_upper and (
                    'EGRE' in name_upper or 'EGR' in name_upper):
                df = _load_csv(filepath)
                if df is not None:
                    df['YEAR'] = year
                    loaded[year] = df
                    print(f"    ✓  {filepath.name:<45}  {len(df):>9,} records")
                break

    if not loaded:
        raise FileNotFoundError(
            "\n  No DEIS discharge files found in the working directory.\n"
            "  Make sure the five annual CSV files from DEIS-MINSAL are\n"
            "  in the same folder as this script and contain the year\n"
            "  in their filename (e.g. EGRE_DATOS_ABIERTOS_2018.csv)."
        )

    missing = [y for y in YEARS if y not in loaded]
    if missing:
        print(f"\n    ⚠  Missing years: {missing}")

    df_all = pd.concat(loaded.values(), ignore_index=True)

    # ── Filter C16 ────────────────────────────────────────────
    df_c16 = df_all[df_all['DIAG1'].isin(ICD10_C16)].copy()
    print(f"\n    Total C16 records : {len(df_c16):,}")
    print(f"    By year:\n"
          f"{df_c16['YEAR'].value_counts().sort_index().to_string()}")

    # ── Standardise columns ───────────────────────────────────
    for col in ['SEXO', 'GRUPO_EDAD', 'GLOSA_REGION_RESIDENCIA',
                'CONDICION_EGRESO']:
        if col in df_c16.columns:
            df_c16[col] = (df_c16[col]
                           .replace('*', 'Not reported')
                           .fillna('Not reported'))

    df_c16['SEXO'] = (df_c16['SEXO']
                      .astype(str).str.upper().str.strip()
                      .replace({'1': 'MALE', '2': 'FEMALE',
                                'HOMBRE': 'MALE', 'MUJER': 'FEMALE'}))

    if 'DIAS_ESTADA' in df_c16.columns:
        df_c16['DIAS_ESTADA'] = pd.to_numeric(
            df_c16['DIAS_ESTADA'], errors='coerce')

    return df_c16


# ─────────────────────────────────────────────────────────────
# SECTION 5 — QUINQUENNIUM EXPANSION
# ─────────────────────────────────────────────────────────────

def expand_to_quinquennia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand records with decennial age coding into two rows
    (weight = 0.5 per quinquennium).  Direct quinquennial
    coding: weight = 1.0.  Unrecognised codes: 'Not reported'.

    This follows the PAHO/WHO standard for harmonising time
    series affected by changes in age-group coding.

    Parameters
    ----------
    df : pd.DataFrame
        C16 microdata with GRUPO_EDAD column.

    Returns
    -------
    pd.DataFrame
        Expanded dataframe with QUINQUENNIUM and WEIGHT columns.
    """
    rows = []
    age_series = df['GRUPO_EDAD'].astype(str).str.strip()

    for idx, row in df.iterrows():
        raw = age_series[idx]
        quinquennia = DEIS_TO_QUINQUENNIUM.get(raw)
        if quinquennia is None:
            quinquennia = DEIS_TO_QUINQUENNIUM.get(raw.upper(),
                                                    ['Not reported'])
        weight = 1.0 / len(quinquennia)
        for q in quinquennia:
            new_row = row.copy()
            new_row['QUINQUENNIUM'] = q
            new_row['WEIGHT']       = weight
            rows.append(new_row)

    df_exp = pd.DataFrame(rows)
    df_exp['AGE_GROUP'] = (df_exp['QUINQUENNIUM']
                           .map(QUINQUENNIUM_TO_AGEGROUP))
    return df_exp


# ─────────────────────────────────────────────────────────────
# SECTION 6 — TABLE A: COUNTS (interest variables matrix)
# ─────────────────────────────────────────────────────────────

def _process_segment(df_seg: pd.DataFrame,
                     sex_label: str,
                     year_label: str) -> list[dict]:
    """Build count rows for one sex × year segment."""
    results = []
    n_total = len(df_seg)

    # Grand total
    results.append({'SEX': sex_label, 'VARIABLE': 'GRAND_TOTAL',
                    'CATEGORY': 'GRAND_TOTAL',
                    'N': n_total, 'YEAR': year_label})

    # ── Quinquennia (weighted) ────────────────────────────────
    counts_q = (df_seg.groupby('QUINQUENNIUM')['WEIGHT']
                .sum().round(0).astype(int))
    counts_q = counts_q.reindex(
        [q for q in QUINQUENNIA_ORDER if q in counts_q.index],
        fill_value=0)
    for cat, n in counts_q.items():
        results.append({'SEX': sex_label,
                        'VARIABLE': 'AGE_GROUP_QUINQUENNIUM',
                        'CATEGORY': cat, 'N': n, 'YEAR': year_label})
    results.append({'SEX': sex_label,
                    'VARIABLE': 'AGE_GROUP_QUINQUENNIUM',
                    'CATEGORY': 'SUBTOTAL_AGE',
                    'N': n_total, 'YEAR': year_label})

    # ── Analytical age groups (weighted) ─────────────────────
    for ag in AGE_GROUPS + ['Not reported']:
        n_ag = int(df_seg[df_seg['AGE_GROUP'] == ag]['WEIGHT']
                   .sum().round())
        results.append({'SEX': sex_label,
                        'VARIABLE': 'ANALYTICAL_AGE_GROUP',
                        'CATEGORY': ag, 'N': n_ag, 'YEAR': year_label})
    results.append({'SEX': sex_label,
                    'VARIABLE': 'ANALYTICAL_AGE_GROUP',
                    'CATEGORY': 'SUBTOTAL_AGE',
                    'N': n_total, 'YEAR': year_label})

    # ── Region of residence ───────────────────────────────────
    for cat, n in (df_seg['GLOSA_REGION_RESIDENCIA']
                   .value_counts().items()):
        results.append({'SEX': sex_label,
                        'VARIABLE': 'REGION_OF_RESIDENCE',
                        'CATEGORY': str(cat), 'N': n,
                        'YEAR': year_label})
    results.append({'SEX': sex_label,
                    'VARIABLE': 'REGION_OF_RESIDENCE',
                    'CATEGORY': 'SUBTOTAL_REGION',
                    'N': n_total, 'YEAR': year_label})

    # ── Discharge condition (in-hospital mortality proxy) ─────
    for cat, n in df_seg['CONDICION_EGRESO'].value_counts().items():
        results.append({'SEX': sex_label,
                        'VARIABLE': 'DISCHARGE_CONDITION',
                        'CATEGORY': str(cat), 'N': n,
                        'YEAR': year_label})
    results.append({'SEX': sex_label,
                    'VARIABLE': 'DISCHARGE_CONDITION',
                    'CATEGORY': 'SUBTOTAL_DISCHARGE',
                    'N': n_total, 'YEAR': year_label})

    return results


def build_counts_table(df_exp: pd.DataFrame) -> pd.DataFrame:
    """
    Build the hierarchical counts matrix
    (sex × variable × category × year), pivoted wide by year.

    Returns
    -------
    pd.DataFrame
        Wide-format table with one column per year + TOTAL_5Y.
    """
    all_rows = []

    for year in YEARS + [None]:
        year_label = str(year) if year else 'TOTAL_5Y'
        df_yr = (df_exp[df_exp['YEAR'] == year]
                 if year else df_exp)

        for sex_label in ['GENERAL', 'MALE', 'FEMALE']:
            df_seg = (df_yr if sex_label == 'GENERAL'
                      else df_yr[df_yr['SEXO'] == sex_label])
            all_rows += _process_segment(df_seg, sex_label, year_label)

    df_long = pd.DataFrame(all_rows)
    df_wide = df_long.pivot_table(
        index=['SEX', 'VARIABLE', 'CATEGORY'],
        columns='YEAR', values='N', aggfunc='first'
    ).reset_index()

    # Column order
    year_cols = [str(y) for y in YEARS] + ['TOTAL_5Y']
    present   = [c for c in year_cols if c in df_wide.columns]
    df_wide   = df_wide[['SEX', 'VARIABLE', 'CATEGORY'] + present]

    # Row order
    sex_ord = {'GENERAL': 0, 'MALE': 1, 'FEMALE': 2}
    var_ord = {'GRAND_TOTAL': 0, 'AGE_GROUP_QUINQUENNIUM': 1,
               'ANALYTICAL_AGE_GROUP': 2,
               'REGION_OF_RESIDENCE': 3, 'DISCHARGE_CONDITION': 4}
    q_ord   = {q: i for i, q in enumerate(QUINQUENNIA_ORDER)}

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
# SECTION 7 — TABLE 1: CRUDE RATES
# ─────────────────────────────────────────────────────────────

def _get_cases(df_exp: pd.DataFrame,
               sex_filter: str | None,
               age_group: str | None) -> pd.Series:
    """
    Return weighted case counts by year for a given
    sex × age-group stratum.

    Parameters
    ----------
    sex_filter  : 'MALE' | 'FEMALE' | None (= all)
    age_group   : '0-14' | '15-64' | '65+' | None (= all)
    """
    df = df_exp.copy()
    if sex_filter:
        df = df[df['SEXO'] == sex_filter]
    if age_group:
        df = df[df['AGE_GROUP'] == age_group]
    return (df.groupby('YEAR')['WEIGHT']
              .sum()
              .reindex(YEARS, fill_value=0))


def build_crude_rates_table(df_exp: pd.DataFrame) -> pd.DataFrame:
    """
    Table 1 — Crude hospital discharge rates for gastric cancer
    (ICD-10 C16) by sex, age group, and year.
    Chile, 2018–2022 (per 100,000 inhabitants).

    Denominator: World Bank population estimates by sex and
    age group.
    Column '2018–2022': arithmetic mean of the five annual rates.

    Returns
    -------
    pd.DataFrame
    """
    config = [
        # (display_sex, sex_filter, wb_sex_key)
        ('General', None,     'total'),
        ('Male',    'MALE',   'male'),
        ('Female',  'FEMALE', 'female'),
    ]
    age_label = {'0-14': '0–14', '15-64': '15–64', '65+': '≥65'}

    rows = []
    for disp_sex, sex_filter, wb_sex in config:
        for ag in AGE_GROUPS:
            cases = _get_cases(df_exp, sex_filter, ag)
            pops  = {y: WORLD_BANK_POP[(wb_sex, ag)][y] for y in YEARS}
            rates = {y: round(cases[y] / pops[y] * 100_000, 2)
                     for y in YEARS}
            mean_rate = round(float(np.mean(list(rates.values()))), 2)

            row = {
                'Sex'               : disp_sex,
                'Age group (years)' : age_label[ag],
                '2018–2022'         : mean_rate,
            }
            row.update({str(y): rates[y] for y in YEARS})
            rows.append(row)

    cols = ['Sex', 'Age group (years)', '2018–2022'] + [str(y) for y in YEARS]
    return pd.DataFrame(rows)[cols]


# ─────────────────────────────────────────────────────────────
# SECTION 8 — TABLE 2: AGE-ADJUSTED RATES (direct method)
# ─────────────────────────────────────────────────────────────

def _direct_standardisation(df_exp: pd.DataFrame,
                             sex_filter: str | None,
                             wb_sex_key: str,
                             census_sex_key: str,
                             year: int) -> float:
    """
    Compute the directly age-standardised discharge rate for
    a given sex and year.

    Formula
    -------
    Adjusted rate = Σ_g (crude_rate_g × W_g) / Σ_g W_g

    where:
        g             = age group (0-14, 15-64, 65+)
        crude_rate_g  = cases_g / WB_pop_g × 100,000
        W_g           = 2024 Census population for group g
                        (same sex stratum as sex_filter)

    Variance is approximated following Flanders (1984) as
    implemented in Joinpoint v6.0.1 (Poisson assumption).
    This function returns point estimates only; CI are
    calculated in Joinpoint from the exported table.

    Parameters
    ----------
    df_exp          : expanded microdata
    sex_filter      : 'MALE' | 'FEMALE' | None  (None = all)
    wb_sex_key      : key for WORLD_BANK_POP  ('male'|'female'|'total')
    census_sex_key  : key for CENSUS_2024     ('male'|'female'|'total')
    year            : calendar year (2018–2022)

    Returns
    -------
    float : adjusted rate per 100,000 inhabitants, rounded to 2 dp.
    """
    df_yr = df_exp[df_exp['YEAR'] == year]
    if sex_filter:
        df_yr = df_yr[df_yr['SEXO'] == sex_filter]

    W_total        = CENSUS_2024[(census_sex_key, 'total')]
    weighted_sum   = 0.0

    for ag in AGE_GROUPS:
        # Numerator: weighted case count
        cases_g = df_yr[df_yr['AGE_GROUP'] == ag]['WEIGHT'].sum()
        # Denominator: World Bank population for that stratum × year
        wb_pop_g = WORLD_BANK_POP[(wb_sex_key, ag)][year]
        # Stratum-specific crude rate (per 100,000)
        crude_g  = cases_g / wb_pop_g * 100_000
        # 2024 Census weight for stratum g
        W_g = CENSUS_2024[(census_sex_key, ag)]
        weighted_sum += crude_g * W_g

    return round(weighted_sum / W_total, 2)


def build_adjusted_rates_table(df_exp: pd.DataFrame) -> pd.DataFrame:
    """
    Table 2 — Age-adjusted hospital discharge rates for gastric
    cancer by sex and year.  Chile, 2018–2022
    (per 100,000 inhabitants).

    Standardisation method : direct
    Reference population   : age distribution of the 2024 Census
                             (INE Chile, 2025)
    Age groups used        : 0–14, 15–64, ≥65 years

    Returns
    -------
    pd.DataFrame with columns [Sex, Year, Adjusted rate*]
    """
    config = [
        # (display_sex, sex_filter, wb_sex_key, census_sex_key)
        ('General', None,     'total',  'total'),
        ('Male',    'MALE',   'male',   'male'),
        ('Female',  'FEMALE', 'female', 'female'),
    ]
    rows = []
    for disp_sex, sex_filter, wb_key, census_key in config:
        for year in YEARS:
            rate = _direct_standardisation(
                df_exp, sex_filter, wb_key, census_key, year)
            rows.append({
                'Sex'           : disp_sex,
                'Year'          : year,
                'Adjusted rate*': rate,
            })

    return pd.DataFrame(rows)[['Sex', 'Year', 'Adjusted rate*']]


# ─────────────────────────────────────────────────────────────
# SECTION 9 — VALIDATION CHECKS
# ─────────────────────────────────────────────────────────────

def run_validation(df_c16: pd.DataFrame,
                   df_exp: pd.DataFrame,
                   t1: pd.DataFrame,
                   t2: pd.DataFrame) -> None:
    """
    Print a structured validation report comparing key figures
    against the published article values.

    Expected values from the article
    (Tables 1 & 2, manuscript accepted version):

    Table 1 — Crude rates (per 100,000)
        General, ≥65, 2018–2022 mean : ~90.09
        Male,    ≥65, 2018–2022 mean : ~134.13
        Female,  ≥65, 2018–2022 mean : ~53.52

    Table 2 — Adjusted rates (per 100,000)
        General, 2018 : 29.79   General, 2020 : 25.42
        General, 2022 : 28.77
        Male,    2018 : 40.24   Male,    2020 : 34.88
        Male,    2022 : 38.25
        Female,  2018 : 19.28   Female,  2020 : 15.88
        Female,  2022 : 19.19
    """
    SEP = '─' * 62

    print(f"\n{'═'*62}")
    print("  VALIDATION REPORT")
    print(f"{'═'*62}")

    # ── 1. Record counts ──────────────────────────────────────
    print(f"\n  1. RECORD COUNTS")
    print(SEP)
    total_original = len(df_c16)
    total_expanded = len(df_exp)
    print(f"     Original C16 records   : {total_original:>10,}")
    print(f"     Expanded records        : {total_expanded:>10,}")
    print(f"     Expansion ratio         : {total_expanded/total_original:>10.4f}")

    by_yr = df_c16['YEAR'].value_counts().sort_index()
    print(f"\n     Records by year (original):")
    for yr, n in by_yr.items():
        print(f"       {yr}: {n:,}")

    # ── 2. Unmapped age codes ─────────────────────────────────
    print(f"\n  2. AGE-GROUP MAPPING")
    print(SEP)
    not_rep = df_exp[df_exp['QUINQUENNIUM'] == 'Not reported']
    print(f"     Unmapped records ('Not reported'): {len(not_rep):,}")
    if len(not_rep) > 0:
        print(f"     Source codes:")
        for code, cnt in (not_rep['GRUPO_EDAD']
                          .value_counts().items()):
            print(f"       '{code}': {cnt}")
    else:
        print("     ✓ All age codes successfully mapped.")

    # ── 3. Table 1 vs article ─────────────────────────────────
    print(f"\n  3. TABLE 1 — CRUDE RATES (vs. published article)")
    print(SEP)
    EXPECTED_CRUDE = {
        ('General', '≥65') : 90.09,
        ('Male',    '≥65') : 134.13,
        ('Female',  '≥65') : 53.52,
        ('General', '0–14'): 0.12,
        ('Male',    '15–64'): 29.95,
        ('Female',  '15–64'): 14.70,
    }
    for (sex, ag), expected in EXPECTED_CRUDE.items():
        row = t1[(t1['Sex'] == sex) &
                 (t1['Age group (years)'] == ag)]
        if row.empty:
            print(f"     ✗  {sex:<8} {ag:<6} — row not found")
            continue
        computed = row['2018–2022'].values[0]
        diff     = abs(computed - expected)
        flag     = '✓' if diff <= 1.0 else '⚠'
        print(f"     {flag}  {sex:<8} {ag:<6}  "
              f"expected={expected:>7.2f}  "
              f"computed={computed:>7.2f}  "
              f"Δ={diff:>5.2f}")

    # ── 4. Table 2 vs article ─────────────────────────────────
    print(f"\n  4. TABLE 2 — ADJUSTED RATES (vs. published article)")
    print(SEP)
    EXPECTED_ADJ = {
        ('General', 2018): 29.79, ('General', 2019): 29.92,
        ('General', 2020): 25.42, ('General', 2021): 25.66,
        ('General', 2022): 28.77,
        ('Male',    2018): 40.24, ('Male',    2019): 40.45,
        ('Male',    2020): 34.88, ('Male',    2021): 33.83,
        ('Male',    2022): 38.25,
        ('Female',  2018): 19.28, ('Female',  2019): 19.29,
        ('Female',  2020): 15.88, ('Female',  2021): 17.32,
        ('Female',  2022): 19.19,
    }
    all_pass = True
    for (sex, yr), expected in sorted(EXPECTED_ADJ.items(),
                                       key=lambda x: (x[0][0], x[0][1])):
        row = t2[(t2['Sex'] == sex) & (t2['Year'] == yr)]
        if row.empty:
            print(f"     ✗  {sex:<8} {yr} — row not found")
            all_pass = False
            continue
        computed = row['Adjusted rate*'].values[0]
        diff     = abs(computed - expected)
        flag     = '✓' if diff <= 0.5 else '⚠'
        if flag == '⚠':
            all_pass = False
        print(f"     {flag}  {sex:<8} {yr}  "
              f"expected={expected:>6.2f}  "
              f"computed={computed:>6.2f}  "
              f"Δ={diff:>5.2f}")

    if all_pass:
        print(f"\n     ✓ All adjusted rates within acceptable tolerance.")
    else:
        print(f"\n     ⚠  Some values deviate > 0.50 from article.")
        print(f"        Review age-group mapping or population denominators.")

    # ── 5. Sex-specific crude rate ratios (≥65) ───────────────
    print(f"\n  5. MALE/FEMALE CRUDE RATE RATIO (≥65 years, 2018–2022)")
    print(SEP)
    for yr in YEARS:
        m = t1[(t1['Sex'] == 'Male') &
               (t1['Age group (years)'] == '≥65')][str(yr)].values
        f = t1[(t1['Sex'] == 'Female') &
               (t1['Age group (years)'] == '≥65')][str(yr)].values
        if m.size and f.size and f[0] > 0:
            print(f"     {yr}: M={m[0]:>7.2f}  "
                  f"F={f[0]:>6.2f}  ratio={m[0]/f[0]:.2f}")

    print(f"\n{'═'*62}\n")


# ─────────────────────────────────────────────────────────────
# SECTION 10 — EXPORT
# ─────────────────────────────────────────────────────────────

def export_results(counts_table: pd.DataFrame,
                   crude_table: pd.DataFrame,
                   adjusted_table: pd.DataFrame,
                   prefix: str = 'gastric_cancer_chile') -> None:
    """
    Export all three tables to CSV and to a multi-sheet Excel workbook.

    Output files
    ------------
    {prefix}_tableA_counts.csv
    {prefix}_table1_crude_rates.csv
    {prefix}_table2_adjusted_rates.csv
    {prefix}_all_tables.xlsx   (3 sheets)
    """
    # ── CSV ───────────────────────────────────────────────────
    counts_table.to_csv(
        f'{prefix}_tableA_counts.csv', index=False, sep=';')
    crude_table.to_csv(
        f'{prefix}_table1_crude_rates.csv', index=False, sep=';')
    adjusted_table.to_csv(
        f'{prefix}_table2_adjusted_rates.csv', index=False, sep=';')

    # ── Excel ─────────────────────────────────────────────────
    xlsx_path = f'{prefix}_all_tables.xlsx'
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        counts_table.to_excel(
            writer, sheet_name='TableA_Counts', index=False)
        crude_table.to_excel(
            writer, sheet_name='Table1_CrudeRates', index=False)
        adjusted_table.to_excel(
            writer, sheet_name='Table2_AdjustedRates', index=False)

    print("\n  Exported files:")
    for fname in [
        f'{prefix}_tableA_counts.csv',
        f'{prefix}_table1_crude_rates.csv',
        f'{prefix}_table2_adjusted_rates.csv',
        xlsx_path,
    ]:
        print(f"    · {fname}")

    # ── Joinpoint-ready export ────────────────────────────────
    # Joinpoint v6.0.1 expects a plain tab-separated file:
    # columns: Sex, Year, Rate   (no header row by default,
    # but the GUI accepts headers when configured accordingly)
    jp_path = f'{prefix}_table2_for_joinpoint.txt'
    adjusted_table.to_csv(jp_path, index=False, sep='\t')
    print(f"    · {jp_path}  ← ready for Joinpoint v6.0.1 input")


# ─────────────────────────────────────────────────────────────
# SECTION 11 — MAIN
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
    print("  Joinpoint Regression with 2024 Census Adjustment")
    print(HDR)

    # ── STEP 1: Load microdata ────────────────────────────────
    print(f"\n[1/6] Loading DEIS-MINSAL microdata...")
    df_c16 = load_deis_microdata(data_directory)

    # ── STEP 2: Expand to quinquennia ────────────────────────
    print(f"\n[2/6] Expanding records to quinquennia...")
    df_exp = expand_to_quinquennia(df_c16)
    print(f"    Original : {len(df_c16):,} records")
    print(f"    Expanded : {len(df_exp):,} records")

    unmapped = df_exp[df_exp['QUINQUENNIUM'] == 'Not reported']
    if len(unmapped):
        pct = len(unmapped) / len(df_exp) * 100
        print(f"    ⚠  Not reported: {len(unmapped):,} records "
              f"({pct:.1f}%) — kept as explicit category")
    else:
        print("    ✓ All age codes mapped.")

    # ── STEP 3: Table A — Counts matrix ──────────────────────
    print(f"\n[3/6] Building Table A (counts matrix)...")
    table_A = build_counts_table(df_exp)
    print(f"    Shape: {table_A.shape}")

    # ── STEP 4: Table 1 — Crude rates ────────────────────────
    print(f"\n[4/6] Computing Table 1 — Crude rates...")
    table_1 = build_crude_rates_table(df_exp)
    print(f"\n    TABLE 1 — Crude hospital discharge rates "
          f"(per 100,000)\n")
    print(table_1.to_string(index=False))

    # ── STEP 5: Table 2 — Adjusted rates ─────────────────────
    print(f"\n[5/6] Computing Table 2 — Adjusted rates "
          f"(direct standardisation)...")
    table_2 = build_adjusted_rates_table(df_exp)
    print(f"\n    TABLE 2 — Age-adjusted discharge rates "
          f"(per 100,000)\n"
          f"    * Direct standardisation; reference: "
          f"2024 Census (INE Chile)\n")
    print(table_2.to_string(index=False))

    # ── STEP 6: Validate & export ─────────────────────────────
    print(f"\n[6/6] Running validation and exporting...")
    run_validation(df_c16, df_exp, table_1, table_2)
    export_results(table_A, table_1, table_2)

    print(f"\n{HDR}")
    print("  PIPELINE COMPLETE")
    print(HDR)
    print("""
  METHODOLOGICAL NOTES
  ─────────────────────────────────────────────────────────
  CRUDE RATES (Table 1)
    Numerator  : ICD-10 C16 discharges — DEIS-MINSAL microdata.
    Denominator: World Bank population estimates (sex × age).
    Unit       : per 100,000 inhabitants.
    '2018–2022': arithmetic mean of the five annual rates.

  ADJUSTED RATES (Table 2)
    Method     : direct age standardisation.
    Standard   : 2024 Census age distribution (INE Chile, 2025).
    Age strata : 0–14, 15–64, ≥65 years.
    Formula    : Σ(crude_g × W_g) / Σ W_g
    Unit       : per 100,000 inhabitants.
    Variance   : Flanders (1984) approximation, computed
                 in Joinpoint v6.0.1 (NCI, 2026).

  AGE-GROUP HARMONISATION
    Decennial codes (legacy DEIS system) were split into two
    quinquennia assuming uniform intra-group distribution
    (weight = 0.5 per quinquennium), following PAHO/WHO
    standard for temporal series harmonisation.

  TABLE 3 (APC / Joinpoint regression)
    Use file: gastric_cancer_chile_table2_for_joinpoint.txt
    Software : Joinpoint Regression Program v6.0.1 (NCI, 2026).
    Settings : max 1 joinpoint (n=5 observations);
               Poisson variance; permutation test (Kim et al.,
               Stat Med 2000); Flanders CI approximation.
  ─────────────────────────────────────────────────────────
""")


# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    main('.')
