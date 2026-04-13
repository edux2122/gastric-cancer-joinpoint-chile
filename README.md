# Hospital Discharges for Gastric Cancer in Chile (2018–2022)

Pre‑processing code and construction of the analytical matrix for the study:

> **"Stagnation of Hospital Burden from Gastric Cancer in Chile (2018–2022): Joinpoint Regression Analysis with Demographic Adjustment to the 2024 Census"**

---

## Description

This repository contains a **reproducible Python pipeline** to:

- Consolidate hospital discharge microdata from DEIS-MINSAL (ICD-10 C16).  
- Harmonise age groups (decades → quinquennia) using fractional weights.  
- Build the analytical tables used in the manuscript:

- **Table A** — Descriptive counts (quinquennium × sex × year).  
- **Table 1** — Crude discharge rates per 100,000 inhabitants (World Bank denominators).  
- **Table 2** — Age-adjusted rates + Flanders (1984) standard error using the 2024 Census as reference population.  
- **Joinpoint file** — Input for the Joinpoint Regression Program v6.0.1 (NCI, 2026).

The script **does not perform inferential analysis** (Joinpoint regression); it only prepares the inputs for R/Joinpoint.

---

## Data source

Data come from the public hospital discharge records of the **Department of Health Statistics and Information (DEIS), Ministry of Health of Chile (MINSAL)**:

- `EGRE_DATOS_ABIERTOS_2018.csv`
- `EGRE_DATOS_ABIERTOS_2019.csv`
- `EGRE_DATOS_ABIERTOS_2020.csv`
- `EGR_DATOS_ABIERTO_2021.csv`
- `EGRE_DATOS_ABIERTOS_2022.csv`

Available at: <https://deis.minsal.cl>

> The raw data files are **not included** in this repository due to their size. They must be downloaded directly from the DEIS website and placed in the same working directory as the script.

---

## Variables in the output matrix

| Variable                   | Description                                                       | Original coding                     |
|---------------------------|-------------------------------------------------------------------|-------------------------------------|
| `GRUPO_EDAD`              | Patient age group, recoded into standard quinquennia             | Categorical (see methods note)      |
| `GLOSA_REGION_RESIDENCIA` | Region of residence                                               | Text                                |
| `CONDICION_EGRESO`        | Condition at discharge (in‑hospital lethality)                   | 1 = Alive, 2 = Dead                 |
| `SEXO`                    | Patient sex                                                       | HOMBRE / MUJER                      |

The final table presents these variables stratified by **sex** (GENERAL, MALE, FEMALE) and **year** (2018, 2019, 2020, 2021, 2022, `TOTAL_5Y`), with counts per category.

---

## Methods note: age‑group recoding

DEIS files use two different age‑coding systems depending on the year:

- **New system** (quinquennia): directly mapped to the corresponding quinquennium.  
- **Legacy system** (decades: `"20 a 29"`, `"30 a 39"`, etc.): redistributed into **two quinquennia** assuming a **uniform within‑decade distribution** (weight = 0.5 per quinquennium), following the PAHO/WHO standard for harmonising time series with coding changes.

Paediatric groups (younger than 7 days, 28 days to 2 months, 2 months to 1 year, 1–4 years) are collapsed into `00–04 years`. Records without a valid age group are kept as `Not reported`.

---

## Repository structure

```text
.
├── README.md
├── Code.py                                    # Main pipeline script
└── outputs/
    ├── gastric_cancer_chile_tableA_counts.csv
    ├── gastric_cancer_chile_table1_crude_rates.csv
    ├── gastric_cancer_chile_table2_adjusted_rates.csv
    ├── gastric_cancer_chile_all_tables.xlsx
    └── gastric_cancer_chile_table2_for_joinpoint.txt
```

---

## Requirements

- Python 3.x (Google Colab or local environment).  
- Libraries: `pandas`, `numpy`, `pathlib`, `openpyxl`.

```bash
pip install pandas numpy openpyxl
```

---

## Usage

### 1. Prepare DEIS data

1. Download the CSV files from <https://deis.minsal.cl>.  
2. Place the five files (`EGRE...2018`–`EGRE...2022`) in the working directory.

### 2. Run the pipeline

**Local environment:**

```bash
python Code.py
```

**Google Colab:**

1. Upload `Code.py` or mount it from Google Drive.  
2. Adjust the path in `main('.')` if needed.  
3. Run:

```python
!python Code.py
```

The script will:

- Load microdata filtered to ICD-10 C16 principal diagnosis.  
- Expand records into quinquennia (weights 0.5 for decennial codes).  
- Compute crude rates (Table 1) using World Bank denominators (2018–2022).  
- Compute age‑adjusted rates and standard errors (Table 2) using the 2024 Census.  
- Generate a `.txt` file ready to import into **Joinpoint v6.0.1** as “Rates with Standard Errors”.

All outputs are written to `./outputs/` (or the current directory, depending on configuration).

---

## Pipeline details (`Code.py`)

The main script is organised into the following sections:

- **Section 3 — Population data (hardcoded)**  
  - **World Bank** denominators (Chile, 2018–2022) by sex and age group.  
  - **2024 Census** (INE Chile) reference population by sex and age group.

- **Section 4 — Age mapping**  
  - `DEIS_TO_QUINQUENNIUM`: maps `GRUPO_EDAD` categories to one or two quinquennia (`WEIGHT = 1.0` or `0.5`).  
  - `QUINQUENNIUM_TO_AGEGROUP`: maps each quinquennium to an analytical group (`0–14`, `15–64`, `65+`).

- **Section 7 — Table A (descriptive counts)**  
  - Builds a matrix of counts by sex, variable, and category (age, region, discharge condition).

- **Section 8 — Table 1 (crude rates)**  
  - Numerator: `WEIGHT.sum()` per stratum.  
  - Denominator: World Bank population.  
  - Unit: **per 100,000 inhabitants**.  
  - `2018–2022` column: arithmetic mean of the five annual crude rates.

- **Section 9 — Table 2 (age‑adjusted rates + SE)**  
  - Method: **direct age standardisation** against the 2024 Census age distribution.  
  - Variance: Flanders (1984) formula under a Poisson assumption.  
  - Returns adjusted rate and standard error by sex and year.

- **Section 10 — Validation**  
  - Report with:  
    - Record counts and expansion ratio.  
    - Proportion of unmapped age codes.  
    - Consistency check General ≈ Male + Female by year.  
    - Printed crude and adjusted rates for manual auditing.  
    - Male/Female crude rate ratio in the ≥65 group.

- **Section 11 — Export**  
  - Exports all tables to `.csv` and `.xlsx`.  
  - Generates `*_table2_for_joinpoint.txt` with columns `Sex`, `Year`, `Rate`, `Standard_Error`.

---

## Citation

If you use this code, please cite the associated article and the repository:

> [Authors]. Stagnation of Hospital Burden from Gastric Cancer in Chile (2018–2022): Joinpoint Regression Analysis with Demographic Adjustment to the 2024 Census. [Journal, year]. DOI: [pending]. Code available at: <https://doi.org/10.5281/zenodo.19322588>

---

## License

This repository is distributed under the **MIT** license.  
DEIS-MINSAL data are publicly available under Chilean transparency regulations.
