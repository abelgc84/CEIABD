# Music Awards Data Lake on AWS

Proyecto de Big Data orientado al diseño e implementación de un pipeline de datos completo sobre AWS utilizando arquitectura Data Lake.

El proyecto integra múltiples datasets musicales (Spotify, Grammys, BRIT Awards y Billboard) para construir un entorno analítico capaz de relacionar características musicales con reconocimiento en premios de la industria.

---

# Objetivos del proyecto

* Diseñar un pipeline ETL completo sobre AWS.
* Construir una arquitectura Data Lake en Amazon S3.
* Integrar datasets heterogéneos mediante procesos de limpieza y normalización.
* Optimizar datos para análisis mediante formato Parquet.
* Automatizar procesamiento con Python, Boto3 y AWS Glue.
* Ejecutar consultas analíticas mediante Amazon Athena.

---

# Arquitectura del proyecto

El pipeline sigue una arquitectura basada en Data Lake con múltiples capas:

```text
RAW  ->  CLEAN  ->  PROCESSED  ->  ANALYTICS
```

## Flujo general

1. Carga de datasets CSV a Amazon S3.
2. Limpieza y normalización de datos.
3. Conversión a formato Parquet.
4. Integración de datasets mediante AWS Glue.
5. Catalogación automática con AWS Glue Crawler.
6. Consulta analítica mediante Amazon Athena.

---

# Tecnologías utilizadas

## Cloud & Big Data

* Amazon S3
* AWS Glue
* AWS Glue Crawlers
* AWS Glue Data Catalog
* Amazon Athena
* Amazon EMR

## Procesamiento de datos

* Python
* PySpark
* Spark SQL
* pandas
* boto3

## Formatos de datos

* CSV
* Parquet

---

# Datasets utilizados

## Dataset principal

### Spotify 1.2M Songs

Dataset con más de 1,2 millones de canciones y características musicales obtenidas desde Spotify.

Incluye:

* danceability
* energy
* valence
* tempo
* acousticness
* duración
* popularidad

## Datasets secundarios

* Grammy Awards
* BRIT Awards
* Billboard Winners

Estos datasets aportan:

* premios
* nominaciones
* categorías
* artistas ganadores

# Scripts principales

## Carga de datasets a S3

Scripts para automatizar la subida de datasets a la capa RAW del Data Lake:

* `upload_spotify_raw.py`
* `upload_grammys_raw.py`
* `upload_brits_raw.py`
* `upload_billboard_raw.py`

## Limpieza y normalización

Scripts encargados de:

* limpieza de texto,
* normalización de artistas y canciones,
* eliminación de duplicados,
* tratamiento de nulos,
* generación de claves de integración.

Scripts:

* `clean_spotify.py`
* `clean_grammys.py`
* `clean_brits.py`
* `clean_billboard.py`

## AWS Glue Job

Glue Job encargado de:

* integrar datasets,
* realizar joins,
* generar métricas de premios,
* crear dataset analítico final,
* particionar por año.

Script:

* `script_processed_glue_job.py`

---

# Estructura del Data Lake

## RAW

```text
s3://datalake-agijonc-2026/raw/
```

Datos originales en CSV.

## CLEAN

```text
s3://datalake-agijonc-2026/clean/
```

Datos limpios y normalizados en Parquet.

## PROCESSED

```text
s3://datalake-agijonc-2026/processed/
```

Dataset analítico final particionado por año.

---

# Consultas analíticas

El proyecto incluye consultas en Amazon Athena para analizar:

* canciones premiadas vs no premiadas,
* evolución musical temporal,
* relación entre energía y premios,
* duración media de canciones,
* tendencias musicales históricas.

---

# Características técnicas destacadas

* Arquitectura Data Lake por capas.
* Procesamiento distribuido con Spark/PySpark.
* Integración de múltiples fuentes de datos.
* Optimización mediante Parquet.
* Particionado por year.
* Automatización con Python y Boto3.
* Procesamiento serverless con AWS Glue y Athena.

---

# Posibles mejoras futuras

* Automatización completa mediante Step Functions.
* Incorporación de Kafka para streaming.
* Dashboard analítico con Power BI o QuickSight.
* Fuzzy matching avanzado para joins.
* Integración CI/CD y MLOps.

---

# Documentación

El repositorio incluye la memoria completa del proyecto:

* `docs/Abel_Gijon_BDA_UT3_ProyectoFinal.pdf`
