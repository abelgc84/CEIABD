# Whisper ASR Fine-Tuning for Speech Impairment Recognition

Proyecto orientado al entrenamiento, evaluación y mejora de modelos Whisper para reconocimiento automático de voz (ASR) aplicado a personas con dificultades del habla.

El objetivo principal del proyecto es experimentar con técnicas de preparación de datasets, limpieza de audio y ajuste de modelos Transformer para mejorar el reconocimiento de voz en escenarios no estándar, utilizando infraestructura GPU y herramientas modernas del ecosistema de inteligencia artificial.

---

# Objetivos del proyecto

* Preparar y limpiar datasets de audio y transcripciones.
* Entrenar modelos Whisper utilizando Hugging Face Transformers.
* Evaluar el rendimiento mediante métricas WER y CER.
* Comparar diferentes configuraciones de entrenamiento.
* Analizar el impacto de la calidad del dataset sobre el rendimiento del modelo.
* Experimentar con modelos ASR orientados a voz con dificultades de pronunciación.

---

# Tecnologías utilizadas

* Python
* OpenAI Whisper
* Hugging Face Transformers
* PyTorch
* librosa
* Hugging Face Datasets
* NumPy
* pandas
* Jupyter Notebook
* GPU CUDA

---

# Contenido del repositorio

## Cuadernos principales

| Notebook | Descripción |
|---|---|
| `01_Creacion_Dataset.ipynb` | Creación inicial del dataset a partir de los datos disponibles, recopilando audios, transcripciones y estructura base para el entrenamiento. |
| `02_Entrenamiento_Inicial.ipynb` | Primer entrenamiento del modelo Whisper, estableciendo una línea base de resultados y configurando el flujo de fine-tuning. |
| `03_Mejora_Modelo.ipynb` | Ajuste del modelo y mejora del entrenamiento mediante cambios en hiperparámetros, configuración de evaluación y selección del mejor modelo. |
| `04_Analisis.ipynb` | Análisis de resultados, revisión de métricas, detección de errores y estudio del comportamiento del modelo sobre el conjunto de prueba. |
| `05_Limpieza_Dataset.ipynb` | Limpieza y validación del dataset, incluyendo revisión de audios, transcripciones, archivos corruptos o datos problemáticos. |
| `06_Reentrenamiento.ipynb` | Reentrenamiento del modelo utilizando el dataset limpio y una configuración más ajustada tras el análisis inicial. |
| `07_entrenamiento_whisper_small_original.ipynb` | Entrenamiento del modelo Whisper Small partiendo del modelo original, con el objetivo de comparar resultados frente a Whisper Base. |
| `08_Entrenamiento_Usuarios.ipynb` | Entrenamiento orientado a usuarios concretos, explorando la adaptación del modelo a voces o grupos específicos dentro del dataset. |

---

# Flujo de trabajo

## 1. Preparación del dataset

* Extracción de audios y transcripciones.
* Validación de archivos corruptos o vacíos.
* Conversión y normalización de audio.
* Creación de datasets compatibles con Hugging Face.

## 2. Entrenamiento

* Fine-tuning de modelos Whisper.
* Entrenamiento sobre GPU CUDA.
* Uso de `Seq2SeqTrainer`.
* Ajuste de hiperparámetros.
* Guardado automático de checkpoints.

## 3. Evaluación

Evaluación del modelo mediante:

* WER (Word Error Rate)
* CER (Character Error Rate)

Además de:

* comparación entre modelos,
* análisis de errores,
* pruebas de inferencia reales.

---

# Arquitectura utilizada

El proyecto utiliza una arquitectura basada en:

* Hugging Face Transformers
* PyTorch
* Whisper
* Datasets
* Entrenamiento acelerado por GPU

El flujo completo incluye:

* procesamiento de audio,
* tokenización,
* generación de features,
* entrenamiento seq2seq,
* evaluación automática.

---

# Resultados y conclusiones

Durante el proyecto se realizaron múltiples experimentos de entrenamiento y ajuste del modelo.

Las pruebas mostraron la importancia crítica de:

* la calidad del dataset,
* la limpieza de audio,
* la precisión de las transcripciones,
* y la homogeneidad de los datos de entrenamiento.

También se comprobó que modelos ASR generalistas como Whisper presentan dificultades adicionales cuando trabajan con voces afectadas por problemas de pronunciación o habla no estándar.

---

# Posibles mejoras futuras

* Aumentar el tamaño y calidad del dataset.
* Aplicar técnicas avanzadas de data augmentation.
* Experimentar con modelos Whisper Small/Medium.
* Incorporar evaluación automática más avanzada.
* Implementar pipelines MLOps.
* Desplegar el modelo mediante API o interfaz web.
