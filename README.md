# Egresos Hospitalarios por Cáncer Gástrico en Chile (2018–2022)

Código de preprocesamiento y construcción de matriz de variables de interés para el estudio:

> **"Dinámica Epidemiológica y Tendencias de la Carga Hospitalaria por Cáncer Gástrico en Chile (2018–2022): Un Análisis de Regresión Joinpoint Ajustado al Censo 2024"**

---

## Descripción

Este repositorio contiene el script de preprocesamiento en Python desarrollado en Google Colab para la consolidación de microdatos de egresos hospitalarios del DEIS-MINSAL y la construcción de una tabla jerárquica (matriz de variables de interés) utilizada como insumo para el análisis estadístico posterior en R y el software Joinpoint Regression Program v6.0.1 (NCI).

El script **no realiza análisis inferencial**. Su función es exclusivamente:

1. Cargar y consolidar los archivos de egresos hospitalarios anuales (2018–2022)
2. Filtrar los registros con diagnóstico principal de cáncer gástrico (CIE-10: C16.x)
3. Limpiar y estandarizar variables de interés
4. Recodificar grupos etarios a quinquenios estándar
5. Construir la matriz de variables de interés con conteos estratificados por sexo y año
6. Exportar la tabla en formato `.csv` y `.xlsx`

---

## Fuente de datos

Los datos provienen de los registros públicos de egresos hospitalarios del **Departamento de Estadísticas e Información en Salud (DEIS), Ministerio de Salud de Chile (MINSAL)**:

- `EGRE_DATOS_ABIERTOS_2018.csv`
- `EGRE_DATOS_ABIERTOS_2019.csv`
- `EGRE_DATOS_ABIERTOS_2020.csv`
- `EGR_DATOS_ABIERTO_2021.csv`
- `EGRE_DATOS_ABIERTOS_2022.csv`

Disponibles en: https://deis.minsal.cl

> Los archivos de datos **no están incluidos** en este repositorio por su tamaño. Deben descargarse directamente desde el sitio del DEIS y ubicarse en el mismo directorio de trabajo que el script.

---

## Variables de interés en la matriz de salida

| Variable | Descripción | Codificación original |
|---|---|---|
| `GRUPO_EDAD` | Grupo etario del paciente, recodificado a quinquenios estándar | Categórica (ver nota metodológica) |
| `GLOSA_REGION_RESIDENCIA` | Región de residencia del paciente | Texto |
| `CONDICION_EGRESO` | Condición al momento del egreso (letalidad intrahospitalaria) | 1 = Vivo, 2 = Fallecido |
| `SEXO` | Sexo del paciente | HOMBRE / MUJER |

La tabla de salida presenta estas variables estratificadas por **sexo** (GENERAL, HOMBRE, MUJER) y **año** (2018, 2019, 2020, 2021, 2022, TOTAL_5A), con conteos por categoría.

---

## Nota metodológica: recodificación de grupos etarios

Los archivos del DEIS presentan dos sistemas de codificación etaria según el año:

- **Sistema nuevo** (quinquenios): presente en años recientes — mapeo directo al quinquenio correspondiente.
- **Sistema antiguo** (décadas: "20 a 29", "30 a 39"...): presente en años anteriores — redistribuidos en dos quinquenios asumiendo **distribución uniforme intragrupo** (peso = 0,5 por quinquenio), siguiendo el estándar OPS/OMS para armonización de series temporales con cambios en codificación.

Los grupos pediátricos (menor de 7 días, 28 días a 2 meses, 2 meses a 1 año, 1–4 años) fueron consolidados en la categoría `00–04 años`. Los registros sin grupo etario válido se mantienen como categoría `No reportado`.

---

## Estructura del repositorio

```
.
├── README.md
├── preprocesamiento_egresos_cancer_gastrico.ipynb   # Notebook principal (Google Colab)
└── outputs/
    ├── tabla_egreso_cancer_gastrico_quinquenios.csv
    └── tabla_egreso_cancer_gastrico_quinquenios.xlsx
```

---

## Requisitos

- Python 3.x (Google Colab o entorno local)
- Bibliotecas: `pandas`, `numpy`, `pathlib`, `openpyxl`

```bash
pip install pandas numpy openpyxl
```

---

## Uso

1. Descargar los archivos CSV del DEIS y ubicarlos en el directorio de trabajo
2. Abrir el notebook en Google Colab o Jupyter
3. Ejecutar todas las celdas en orden
4. Los archivos de salida se generan en el mismo directorio

---

## Cita

Si utilizas este código, por favor cita el artículo asociado y el repositorio:

> [Autores]. Dinámica Epidemiológica y Tendencias de la Carga Hospitalaria por Cáncer Gástrico en Chile (2018–2022): Un Análisis de Regresión Joinpoint Ajustado al Censo 2024. [Revista, año]. DOI: [pendiente]

---

## Licencia

Este repositorio se distribuye bajo licencia MIT. Los datos del DEIS-MINSAL son de acceso público según la normativa de transparencia del Estado de Chile.
