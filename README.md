# Egresos Hospitalarios por Cáncer Gástrico en Chile (2018–2022)

Código de preprocesamiento y construcción de la matriz de variables de interés para el estudio:

> **"Stagnation of Hospital Burden from Gastric Cancer in Chile (2018–2022): Joinpoint Regression Analysis with Demographic Adjustment to the 2024 Census"**

---

## Descripción

Este repositorio contiene el **pipeline reproducible en Python** para:

- Consolidar microdatos de egresos hospitalarios del DEIS-MINSAL (ICD-10 C16).  
- Armonizar grupos de edad (décadas → quinquenios) mediante ponderadores.  
- Construir las tablas analíticas utilizadas en el manuscrito:

  - **Table A** — Conteos descriptivos (quinquenio × sexo × año).  
  - **Table 1** — Tasas crudas por 100.000 habitantes (Banco Mundial).  
  - **Table 2** — Tasas ajustadas por edad + error estándar de Flanders (1984) usando el Censo 2024 como población de referencia.  
  - **Archivo Joinpoint** — Entrada para el Joinpoint Regression Program v6.0.1 (NCI, 2026).

El script **no realiza análisis inferencial** (regresión Joinpoint); solo prepara los insumos para R/Joinpoint.

---

## Fuente de datos

Los datos provienen de los registros públicos de egresos hospitalarios del **Departamento de Estadísticas e Información en Salud (DEIS), Ministerio de Salud de Chile (MINSAL)**:

- `EGRE_DATOS_ABIERTOS_2018.csv`
- `EGRE_DATOS_ABIERTOS_2019.csv`
- `EGRE_DATOS_ABIERTOS_2020.csv`
- `EGR_DATOS_ABIERTO_2021.csv`
- `EGRE_DATOS_ABIERTOS_2022.csv`

Disponibles en: <https://deis.minsal.cl>

> Los archivos de datos **no están incluidos** en este repositorio por su tamaño. Deben descargarse directamente desde el sitio del DEIS y ubicarse en el mismo directorio de trabajo que el script.

---

## Variables de interés en la matriz de salida

| Variable                   | Descripción                                                       | Codificación original                |
|---------------------------|-------------------------------------------------------------------|--------------------------------------|
| `GRUPO_EDAD`              | Grupo etario del paciente, recodificado a quinquenios estándar   | Categórica (ver nota metodológica)   |
| `GLOSA_REGION_RESIDENCIA` | Región de residencia del paciente                                 | Texto                                |
| `CONDICION_EGRESO`        | Condición al momento del egreso (letalidad intrahospitalaria)    | 1 = Vivo, 2 = Fallecido              |
| `SEXO`                    | Sexo del paciente                                                | HOMBRE / MUJER                       |

La tabla de salida presenta estas variables estratificadas por **sexo** (GENERAL, HOMBRE, MUJER) y **año** (2018, 2019, 2020, 2021, 2022, `TOTAL_5Y`), con conteos por categoría.

---

## Nota metodológica: recodificación de grupos etarios

Los archivos del DEIS presentan dos sistemas de codificación etaria según el año:

- **Sistema nuevo** (quinquenios): mapeo directo al quinquenio correspondiente.  
- **Sistema antiguo** (décadas: `"20 a 29"`, `"30 a 39"`, etc.): redistribuidos en **dos quinquenios** asumiendo **distribución uniforme intragrupo** (peso = 0,5 por quinquenio), siguiendo el estándar OPS/OMS para armonización de series temporales.

Los grupos pediátricos (menor de 7 días, 28 días a 2 meses, 2 meses a 1 año, 1–4 años) se consolidan en la categoría `00–04 años`. Los registros sin grupo etario válido se mantienen como `Not reported`.

---

## Estructura del repositorio

```text
.
├── README.md
├── Code.py                                    # Pipeline principal (este repo)
└── outputs/
    ├── gastric_cancer_chile_tableA_counts.csv
    ├── gastric_cancer_chile_table1_crude_rates.csv
    ├── gastric_cancer_chile_table2_adjusted_rates.csv
    ├── gastric_cancer_chile_all_tables.xlsx
    └── gastric_cancer_chile_table2_for_joinpoint.txt
```

---

## Requisitos

- Python 3.x (Google Colab o entorno local).
- Bibliotecas: `pandas`, `numpy`, `pathlib`, `openpyxl`.

```bash
pip install pandas numpy openpyxl
```

---

## Uso

### 1. Preparar datos DEIS

1. Descargar los CSV desde <https://deis.minsal.cl>.  
2. Ubicar los cinco archivos (`EGRE...2018`–`EGRE...2022`) en el directorio de trabajo.

### 2. Ejecutar el pipeline

**En entorno local:**

```bash
python Code.py
```

**En Google Colab:**

1. Subir `Code.py` al entorno o montarlo desde Google Drive.  
2. Ajustar la ruta en `main('.')` si es necesario.  
3. Ejecutar todas las celdas o correr el script:

```python
!python Code.py
```

El script:

- Carga los microdatos filtrando por ICD-10 C16.  
- Expande los registros a quinquenios (ponderadores 0,5 en códigos decenales).  
- Calcula tasas crudas (Tabla 1) con denominadores del Banco Mundial (2018–2022).  
- Calcula tasas ajustadas por edad y error estándar (Tabla 2) usando el Censo 2024.  
- Genera un archivo `.txt` listo para importar en **Joinpoint v6.0.1** como “Rates with Standard Errors”.

Los archivos de salida se escriben en `./outputs/` (o en el directorio actual, según configuración).

---

## Detalles del pipeline (`Code.py`)

El script principal está organizado en secciones:

- **Sección 3 — Datos de población (hardcoded)**  
  - Denominadores del **Banco Mundial** (Chile, 2018–2022) por sexo y grupo etario.  
  - Población de referencia del **Censo 2024** (INE Chile) por sexo y grupo etario.

- **Sección 4 — Mapeo de edad**  
  - `DEIS_TO_QUINQUENNIUM`: mapea las categorías de `GRUPO_EDAD` a uno o dos quinquenios (`WEIGHT = 1.0` o `0.5`).  
  - `QUINQUENNIUM_TO_AGEGROUP`: asigna cada quinquenio a un grupo analítico (`0–14`, `15–64`, `65+`).

- **Sección 7 — Table A (conteos descriptivos)**  
  - Construye una matriz de conteos por sexo, variable y categoría (edad, región, condición de egreso).

- **Sección 8 — Table 1 (tasas crudas)**  
  - Numerador: `WEIGHT.sum()` por estrato.  
  - Denominador: población del Banco Mundial.  
  - Unidad: **por 100.000 habitantes**.  
  - Columna `2018–2022`: promedio aritmético de las cinco tasas anuales.

- **Sección 9 — Table 2 (tasas ajustadas + SE)**  
  - Método: **estandarización directa** sobre distribución etaria del Censo 2024.  
  - Fórmula de Flanders (1984) para la varianza del tasa ajustada (asumiendo Poisson).  
  - Devuelve tasa ajustada y error estándar por sexo y año.

- **Sección 10 — Validación**  
  - Informe con:  
    - Conteo de registros y razón de expansión.  
    - Proporción de códigos de edad no mapeados.  
    - Consistencia General ≈ Hombres + Mujeres por año.  
    - Tasas crudas y ajustadas impresas para auditoría manual.  
    - Razón de tasas M/F en ≥65 años.

- **Sección 11 — Exportación**  
  - Exporta todas las tablas a `.csv` y `.xlsx`.  
  - Genera el archivo `*_table2_for_joinpoint.txt` con columnas `Sex`, `Year`, `Rate`, `Standard_Error`.

---

## Cita

Si utilizas este código, por favor cita el artículo asociado y el repositorio:

> [Autores]. Stagnation of Hospital Burden from Gastric Cancer in Chile (2018–2022): Joinpoint Regression Analysis with Demographic Adjustment to the 2024 Census. [Revista, año]. DOI: [pendiente]. Código disponible en: <https://doi.org/10.5281/zenodo.19322588>

---

## Licencia

Este repositorio se distribuye bajo licencia **MIT**.  
Los datos del DEIS-MINSAL son de acceso público según la normativa de transparencia del Estado de Chile.
