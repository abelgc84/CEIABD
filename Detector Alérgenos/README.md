# Detector OCR de alérgenos en etiquetas alimentarias

Proyecto práctico de visión por computador y OCR orientado al análisis de etiquetas alimentarias.  
El objetivo es detectar automáticamente el bloque de ingredientes de una imagen, extraer el texto mediante OCR y comprobar si aparecen posibles alérgenos.

El proyecto combina preprocesamiento de imagen con OpenCV, reconocimiento óptico de caracteres con Tesseract y búsqueda de términos mediante coincidencias exactas y búsqueda difusa.

## Objetivo

Desarrollar una herramienta capaz de analizar una imagen de una etiqueta alimentaria y detectar posibles alérgenos presentes en el listado de ingredientes.

El sistema intenta:

- Preprocesar la imagen para mejorar la lectura OCR.
- Localizar el bloque de ingredientes.
- Extraer el texto mediante Tesseract OCR.
- Buscar alérgenos conocidos en el texto detectado.
- Aplicar búsqueda difusa para tolerar pequeños errores de OCR.
- Mostrar un resultado visual indicando si se han encontrado términos de riesgo.

## Tecnologías utilizadas

- Python
- OpenCV
- Tesseract OCR
- pytesseract
- NumPy
- PIL / Pillow
- Matplotlib
- Regex
- difflib

## Conceptos trabajados

- Procesamiento de imágenes.
- Conversión a escala de grises.
- Redimensionado de imágenes.
- Umbralización con Otsu.
- Operaciones morfológicas.
- Detección de regiones de interés.
- OCR con Tesseract.
- Limpieza y normalización de texto.
- Búsqueda exacta y búsqueda difusa.
- Validación contextual del texto detectado.
- Visualización de resultados con Matplotlib.

