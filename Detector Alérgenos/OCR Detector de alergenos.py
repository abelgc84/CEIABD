import pytesseract
from pytesseract import Output  # Necesario para el ROI
from PIL import Image
import cv2
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
import difflib
import os
import sys
import matplotlib.pyplot as plt
import textwrap


# CONFIGURACIÓN DE TESSERACT (WINDOWS)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class DetectorAlergenos:
    """
    Detector inteligente de alérgenos con validación de seguridad y búsqueda difusa.
    """
    
    def __init__(self, perfil_usuario: Dict[str, List[str]] = None):
        # Alérgenos según Reglamento UE 1169/2011 (14 principales)
        self.alergenos = {
            'cereales_gluten': ['gluten', 'trigo', 'cebada', 'centeno', 'avena', 'espelta', 'kamut'],
            'crustaceos': ['marisco', 'gamba', 'langostino', 'cangrejo', 'langosta'],
            'huevos': ['huevo', 'huevos', 'albúmina', 'ovoalbúmina', 'lisozima', 'clara', 'yema'],
            'pescado': ['pescado', 'merluza', 'salmón', 'atún', 'bacalao', 'anchoa'],
            'cacahuetes': ['cacahuete', 'cacahuetes', 'maní', 'cacahuate', 'peanut'],
            'soja': ['soja', 'soya', 'lecitina', 'edamame'],
            'lacteos': ['leche', 'lactosa', 'suero', 'caseína', 'mantequilla', 'nata', 'queso', 'yogur', 'milk'],
            'frutos_cascara': ['almendra', 'avellana', 'nuez', 'anacardo', 'pistacho', 'macadamia'],
            'otros': ['apio', 'mostaza', 'sésamo', 'sulfitos', 'altramuces', 'moluscos']
        }
        
        if perfil_usuario:
            self.alergenos.update(perfil_usuario)
        
        # Configuración de parámetros de Tesseract
        self.config_tesseract = r'--oem 3 --psm 4 -l spa+eng'
        self.historial = []

    def preprocesar_imagen(self, imagen_path: str) -> np.ndarray:
        if not os.path.exists(imagen_path):
            raise FileNotFoundError(f"No se encuentra la imagen: {imagen_path}")

        img = cv2.imread(imagen_path)
        if img is None:
            raise ValueError(f"No se pudo cargar la imagen: {imagen_path}")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_pil = Image.fromarray(gray)
        factor = 2 
        new_size = tuple(int(x * factor) for x in img_pil.size)
        resized = img_pil.resize(new_size, Image.Resampling.LANCZOS)
        gray = np.array(resized)

        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return processed

    def detectar_area_ingredientes(self, imagen: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """
        A) Encuentra la línea "Ingredientes" con OCR (por líneas).
        B) Recorta desde ahí hasta antes de la siguiente "sección" (nutricional, conservación, etc.)
        C) Fallback: detecta bloques por contornos (layout) y elige el bloque con mejor score.
        Devuelve (roi_img, (x, y, w, h)) en coordenadas de la imagen 'imagen' (procesada).
        """
        def _norm_token(s: str) -> str:
            return re.sub(r'[^a-z0-9áéíóúüñ]+', '', s.lower().strip())

        def _similar(a: str, b: str) -> float:
            return difflib.SequenceMatcher(None, a, b).ratio()

        # Secciones típicas que NO son ingredientes (para cortar el ROI)
        stop_keywords = [
            "informacionnutricional", "valoresnutricionales", "nutricional", "nutrition", "nutritionfacts",
            "modoempleo", "mododeempleo", "preparacion", "preparation",
            "conservacion", "conservar", "storage",
            "lote", "caducidad", "consumopreferente",
            "fabricante", "distribuidor", "origen", "direccion",
        ]

        # --- A) ROI por líneas OCR ---
        try:
            d = pytesseract.image_to_data(imagen, output_type=Output.DICT, config=self.config_tesseract)
            n = len(d["text"])

            # Agrupamos palabras por línea (block/par/line)
            lines = {}
            for i in range(n):
                txt = d["text"][i]
                if not txt or not txt.strip():
                    continue

                conf_str = d["conf"][i]
                try:
                    conf = float(conf_str)
                except:
                    conf = -1

                # Filtro suave para no perder "INGREDIENTES" borroso
                if conf < 25:
                    continue

                key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])

                token = _norm_token(txt.replace(":", ""))
                if not token:
                    continue

                item = lines.setdefault(key, {
                    "tokens": [],
                    "lefts": [],
                    "tops": [],
                    "rights": [],
                    "bottoms": []
                })

                l, t, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
                item["tokens"].append(token)
                item["lefts"].append(l)
                item["tops"].append(t)
                item["rights"].append(l + w)
                item["bottoms"].append(t + h)

            # Ordenamos líneas por Y
            ordered = []
            for key, it in lines.items():
                y_top = min(it["tops"])
                y_bot = max(it["bottoms"])
                x_left = min(it["lefts"])
                x_right = max(it["rights"])
                text_line = " ".join(it["tokens"])
                ordered.append((y_top, y_bot, x_left, x_right, text_line, key))
            ordered.sort(key=lambda x: x[0])

            # Localizar la línea más probable de "ingredientes"
            best_idx = None
            best_score = 0.0
            for idx, (y_top, y_bot, x_left, x_right, text_line, key) in enumerate(ordered):
                s1 = _similar(text_line, "ingredientes")
                s2 = _similar(text_line, "ingredients")
                contains = 1.0 if ("ingredien" in text_line) else 0.0
                score = max(s1, s2, contains)
                if score > best_score:
                    best_score = score
                    best_idx = idx

            # Umbral de aceptación
            if best_idx is not None and best_score >= 0.72:
                y_top, y_bot, x_left, x_right, text_line, key_ing = ordered[best_idx]
                print(f"ROI: keyword-line='{text_line}' score={best_score:.2f}")

                # Inicio (margen para no cortar tildes/borde superior)
                margin_up = 12
                y_start = max(0, y_top - margin_up)

                # Recorte hasta el final, con corte inteligente
                y_end = imagen.shape[0]
                last_y_bot = y_bot

                # Referencias para heurísticas
                block_ing = key_ing[0]

                # --- gap típico entre líneas: umbral dinámico ---
                gaps = []
                for k in range(best_idx + 1, min(len(ordered), best_idx + 25)):
                    prev_bot = ordered[k - 1][1]
                    cur_top = ordered[k][0]
                    gap = cur_top - prev_bot
                    if gap > 0:
                        gaps.append(gap)

                median_gap = int(np.median(gaps)) if gaps else 18
                gap_cut = max(90, int(median_gap * 5.0))  # más tolerante que un fijo tipo 45px
                min_lines_after = 4                        # obliga a capturar mínimo N líneas bajo INGREDIENTES
                lines_taken = 0

                for j in range(best_idx + 1, len(ordered)):
                    y2_top, y2_bot, x2_left, x2_right, line2, key2 = ordered[j]

                    gap_now = (y2_top - last_y_bot)

                    # Corte por salto grande (solo si ya capturamos unas líneas mínimas)
                    if lines_taken >= min_lines_after and gap_now > gap_cut:
                        y_end = last_y_bot + 15
                        break

                    # Corte por cambio fuerte de bloque (menos agresivo; evita cortes prematuros)
                    if key2[0] != block_ing and (y2_top - y_bot) > 180 and lines_taken >= min_lines_after:
                        y_end = last_y_bot + 15
                        break

                    # Corte por encabezados típicos (stop keywords)
                    line2_compact = line2.replace(" ", "")
                    if any(sk in line2_compact for sk in stop_keywords):
                        # Excepción: si es "alergenos/contiene" MUY cerca, puede ser parte del bloque
                        if ("alergenos" in line2_compact or "contiene" in line2_compact) and (y2_top - y_bot) < 70:
                            lines_taken += 1
                            last_y_bot = y2_bot
                            continue

                        y_end = max(y_start + 60, y2_top - 8)
                        break

                    lines_taken += 1
                    last_y_bot = y2_bot

                # X: por seguridad, cogemos todo el ancho (evita perder columnas/indentaciones)
                x_start = 0
                x_end = imagen.shape[1]

                # Sanitizar límites
                y_end = min(imagen.shape[0], max(y_end, y_start + 80))
                roi_img = imagen[y_start:y_end, x_start:x_end]
                roi_coords = (x_start, y_start, x_end - x_start, y_end - y_start)
                return roi_img, roi_coords

        except Exception as e:
            print(f"ROI OCR-lines falló: {e}")

        # --- B) Fallback por layout (contornos) ---
        try:
            h, w = imagen.shape[:2]

            # Unimos texto en “bloques” (dilatación)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
            merged = cv2.dilate(imagen, kernel, iterations=2)

            contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            boxes = []
            for c in contours:
                x, y, bw, bh = cv2.boundingRect(c)
                area = bw * bh
                if area < (w * h) * 0.02:
                    continue
                if bh < 40 or bw < 150:
                    continue
                boxes.append((x, y, bw, bh))

            if not boxes:
                return None, None

            best = None
            best_score = -1

            for (x, y, bw, bh) in sorted(boxes, key=lambda b: b[1]):  # top-down
                roi = imagen[y:y+bh, x:x+bw]
                txt = pytesseract.image_to_string(roi, config=self.config_tesseract)
                tnorm = _norm_token(txt)
                score = 0

                if "ingredien" in tnorm:
                    score += 5
                if "ingredient" in tnorm:
                    score += 5

                score += min(3, txt.count(",") // 3)
                score += min(3, txt.count(";") // 3)
                score += min(4, len(txt.strip()) // 80)

                if score > best_score:
                    best_score = score
                    best = (x, y, bw, bh)

            if best and best_score >= 4:
                x, y, bw, bh = best
                margin = 10
                x0 = max(0, x - margin)
                y0 = max(0, y - margin)
                x1 = min(w, x + bw + margin)
                y1 = min(h, y + bh + margin)

                roi_img = imagen[y0:y1, x0:x1]
                roi_coords = (x0, y0, x1 - x0, y1 - y0)
                print(f"ROI: layout-fallback score={best_score}")
                return roi_img, roi_coords

        except Exception as e:
            print(f"ROI layout-fallback falló: {e}")

        return None, None


    def _es_similar(self, palabra_ocr: str, alergeno_target: str, umbral: float = 0.85) -> bool:
        if len(palabra_ocr) < 4: 
            return palabra_ocr == alergeno_target
        # Compara similitud entre lo leído y la base de alérgenos
        ratio = difflib.SequenceMatcher(None, palabra_ocr, alergeno_target).ratio()
        return ratio >= umbral

    def _validar_contexto_etiqueta(self, texto: str) -> bool:
        palabras_control = ['ingredientes', 'ingredients', 'contiene', 'valor', 'nutricional', 'energético', 'grasas', 'azúcares']
        texto_lower = texto.lower()
        matches = 0
        for palabra in palabras_control:
            if palabra in texto_lower:
                matches += 1
        return matches >= 1 or len(texto.split()) > 15

    def buscar_alergenos(self, texto: str) -> Dict[str, List[str]]:
        resultados = {}
        texto_limpio = re.sub(r'[^\w\s]', ' ', texto.lower())
        palabras_texto = texto_limpio.split()
        
        for categoria, lista_alergenos in self.alergenos.items():
            encontrados = []
            for alergeno in lista_alergenos:
                alergeno = alergeno.lower()
                
                # Búsqueda Exacta
                if f" {alergeno} " in f" {texto_limpio} ":
                    if alergeno not in encontrados:
                        encontrados.append(alergeno)
                    continue 
                
                # Búsqueda Difusa
                for palabra_ocr in palabras_texto:
                    if self._es_similar(palabra_ocr, alergeno):
                        if alergeno not in encontrados:
                            encontrados.append(f"{alergeno} (leído como '{palabra_ocr}')")
                            break
            if encontrados:
                resultados[categoria] = encontrados
        return resultados

    def analizar_etiqueta(self, imagen_path: str, nombre_producto: str = "Producto Escaneado") -> Dict:
        print(f"\n{'='*60}")
        print(f"ANALIZANDO: {nombre_producto}")
        print(f"{'='*60}")
        
        try:
            # 1. PROCESAMIENTO INICIAL
            img_original = cv2.imread(imagen_path)
            img_procesada = self.preprocesar_imagen(imagen_path)
            
            # 2. DETECCIÓN DE ROI INTELIGENTE
            print("Analizando estructura del documento...")
            roi_img, roi_coords = self.detectar_area_ingredientes(img_procesada)
            
            img_para_ocr = img_procesada # Fallback
            titulo_ocr = "Visión OCR (Completa)"
            
            if roi_img is not None:
                print("Bloque de ingredientes aislado exitosamente.")
                img_para_ocr = roi_img
                titulo_ocr = "Visión OCR (Bloque Aislado)"
            else:
                print("No se detectó estructura clara. Escaneando todo.")
            
            # 3. OCR
            texto = pytesseract.image_to_string(img_para_ocr, config=self.config_tesseract)
            print(f"Texto Crudo ({len(texto)} chars):\n'{texto[:100].replace(chr(10), ' ')}...'")
            
            # 4. ANÁLISIS LÓGICO
            alergenos_detectados = {}
            riesgo = 'DESCONOCIDO'
            mensaje_resultado = ""
            bg_color_resultado = "#f8f9fa"

            if not self._validar_contexto_etiqueta(texto):
                print("\nALERTA: Lectura no concluyente.")
                mensaje_resultado = "LECTURA NO CONCLUYENTE\n\nNo se detectaron ingredientes claros.\nRevise la iluminación de la foto."
                bg_color_resultado = "#fff3cd" # Amarillo
            else:
                alergenos_detectados = self.buscar_alergenos(texto)
                if alergenos_detectados:
                    riesgo = 'ALTO'
                    print("\n¡PELIGRO! ALÉRGENOS ENCONTRADOS.")
                    mensaje_resultado = "¡PELIGRO DETECTADO!\n\nALÉRGENOS ENCONTRADOS:\n\n"
                    for cat, items in alergenos_detectados.items():
                        linea = f" • {cat.upper()}: {', '.join(items)}"
                        mensaje_resultado += linea + "\n"
                        print(linea)
                    bg_color_resultado = "#f8d7da" # Rojo
                else:
                    riesgo = 'BAJO'
                    print("\n✅ PARECE SEGURO.")
                    mensaje_resultado = "PARECE SEGURO\n\nNo se detectaron términos de riesgo."
                    bg_color_resultado = "#d4edda" # Verde

            # 5. VISUALIZACIÓN EN DOS VENTANAS
            
            # --- VENTANA 1: RESULTADO ---
            fig1 = plt.figure("Resultado", figsize=(6, 4))
            fig1.patch.set_facecolor(bg_color_resultado)
            plt.axis('off')
            plt.figtext(
                0.5, 0.5, mensaje_resultado,
                ha="center", va="center", fontsize=12, weight='bold',
                bbox={"facecolor": "white", "alpha":0.9, "edgecolor":"#666666", "boxstyle":"round,pad=1"}
            )
            
            # --- VENTANA 2: DETALLES ---
            plt.figure("Evidencia Técnica", figsize=(12, 9))
            plt.subplots_adjust(bottom=0.35, hspace=0.3)
            
            plt.subplot(1, 2, 1)
            plt.title("Imagen Original (+ ROI)")
            img_original_rgb = cv2.cvtColor(img_original, cv2.COLOR_BGR2RGB)
            if roi_coords:
                # Dibujamos el recuadro detectado 
                x, y, w, h = [int(v/2) for v in roi_coords]
                cv2.rectangle(img_original_rgb, (x, y), (x+w, y+h), (0, 255, 0), 4)
                
            plt.imshow(img_original_rgb)
            plt.axis('off')
            
            plt.subplot(1, 2, 2)
            plt.title(titulo_ocr)
            plt.imshow(img_para_ocr, cmap='gray')
            plt.axis('off')
            
            texto_ocr_visual = " ".join(texto.split())
            if not texto_ocr_visual: texto_ocr_visual = "(Sin texto)"
            texto_ocr_wrap = textwrap.fill(texto_ocr_visual, width=110)
            
            plt.figtext(
                0.5, 0.05,
                f"📝 TEXTO ANALIZADO:\n{'-'*80}\n{texto_ocr_wrap}", 
                ha="center", va="bottom", fontsize=9, family='monospace',
                bbox={"facecolor":"#f0f0f0", "alpha":0.8, "edgecolor":"none"}
            )
            
            print("\n🖼️  Abriendo ventanas...")
            plt.show()

        except Exception as e:
            print(f"❌ Error: {e}")
            return {}

        return {'riesgo': riesgo, 'alergenos': alergenos_detectados}

# EJECUCIÓN
if __name__ == "__main__":
    detector = DetectorAlergenos()
    ARCHIVO_IMAGEN = "etiqueta4.jpg" 
    
    print(f"🚀 Iniciando sistema...")
    if os.path.exists(ARCHIVO_IMAGEN):
        detector.analizar_etiqueta(ARCHIVO_IMAGEN, "Mi Producto de Prueba")
    else:
        print(f"\n❌ FALTAN ARCHIVOS. Por favor, coloca una imagen llamada '{ARCHIVO_IMAGEN}'.")