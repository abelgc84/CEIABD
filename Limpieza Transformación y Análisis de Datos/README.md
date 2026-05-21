# Análisis climático con PySpark y Databricks

Proyecto práctico de análisis y procesamiento de datos meteorológicos utilizando **PySpark** en un entorno de **Databricks**.

El objetivo del proyecto es trabajar con el dataset **Jena Climate**, aplicando un flujo completo de carga, limpieza, transformación, análisis exploratorio, consultas con Spark SQL y exportación del dataset limpio en formato Parquet.

## Objetivo

Desarrollar un proceso de análisis de datos climáticos utilizando herramientas del ecosistema Big Data, simulando un flujo de trabajo habitual en ingeniería de datos:

- Carga de datos en Databricks.
- Inspección inicial del dataset.
- Limpieza y validación de calidad.
- Transformación de columnas.
- Creación de variables temporales y meteorológicas.
- Análisis exploratorio con Spark DataFrames.
- Consultas analíticas con Spark SQL.
- Detección básica de anomalías.
- Exportación de datos limpios en formato Parquet.

## Dataset

El proyecto utiliza el **Jena Climate Dataset**, un conjunto de datos meteorológicos con registros temporales de distintas variables climáticas.

Entre las variables trabajadas se incluyen:

- Fecha y hora de medición.
- Temperatura.
- Presión atmosférica.
- Humedad.
- Velocidad del viento.
- Dirección del viento.
- Variables meteorológicas adicionales incluidas en el dataset original.

## Tecnologías utilizadas

- Python
- PySpark
- Spark DataFrames
- Spark SQL
- Databricks
- Parquet
- Jupyter Notebook / Databricks Notebook

## Conceptos trabajados

- Carga de datasets en Databricks.
- Lectura y procesamiento de datos con PySpark.
- Inspección de estructura, tipos de datos y valores nulos.
- Renombrado de columnas.
- Corrección de tipos de datos.
- Validación de reglas de calidad.
- Limpieza de valores incoherentes.
- Creación de columnas derivadas.
- Transformaciones temporales.
- Análisis agregado por año, mes, estación y franja horaria.
- Consultas con Spark SQL.
- Cálculo de correlaciones entre variables.
- Detección básica de anomalías mediante percentiles.
- Exportación del dataset procesado a Parquet.

