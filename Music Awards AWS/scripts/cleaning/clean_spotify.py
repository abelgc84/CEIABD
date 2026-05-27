import os
import sys
import re
import ast
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# =========================
# CONFIGURACIÓN
# =========================

BUCKET_NAME = "datalake-agijonc-2026"

RAW_S3_KEY = "raw/spotify/tracks_features.csv"
CLEAN_S3_KEY = "clean/spotify/spotify_clean.parquet"

LOCAL_OUTPUT_FILE = "spotify_clean.parquet"

# =========================
# FUNCIONES DE LIMPIEZA
# =========================

def clean_basic_text(text):
    """
    Limpieza básica:
    - minúsculas
    - trim
    - espacios duplicados
    """
    if pd.isna(text):
        return None

    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_main_artist(value):
    """
    Convierte columnas tipo lista serializada:
    "['Rage Against The Machine']" -> "rage against the machine"
    Se queda con el primer artista.
    """
    if pd.isna(value):
        return None

    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list) and len(parsed) > 0:
            return clean_basic_text(parsed[0])
        return clean_basic_text(value)
    except Exception:
        return clean_basic_text(value)


def clean_track_name(text):
    """
    Limpia títulos de canciones para mejorar joins:
    - minúsculas
    - elimina feat/ft/featuring y lo que venga después
    - elimina remaster/live/version/edit/mix/deluxe/acoustic...
    - elimina contenido entre paréntesis y corchetes
    - elimina caracteres especiales innecesarios
    """
    if pd.isna(text):
        return None

    text = str(text).lower().strip()

    # Elimina contenido entre paréntesis y corchetes
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"\[.*?\]", " ", text)

    # Elimina colaboraciones tipo feat / ft / featuring y lo que venga después
    text = re.sub(r"\b(feat\.?|ft\.?|featuring)\b.*$", " ", text)

    # Elimina términos frecuentes de versiones
    patterns = [
        r"\bremaster(ed)?\b",
        r"\blive\b",
        r"\bversion\b",
        r"\bedit\b",
        r"\bmix\b",
        r"\bdeluxe\b",
        r"\bmono\b",
        r"\bstereo\b",
        r"\bacoustic\b",
        r"\brecord(ed|ing)?\b",
        r"\bbonus track\b"
    ]

    for pattern in patterns:
        text = re.sub(pattern, " ", text)

    # Mantiene letras, números, espacios, guiones y apóstrofes
    text = re.sub(r"[^a-z0-9\s\-']", " ", text)

    # Normaliza espacios
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def clean_artist_name(text):
    """
    Limpieza para artista de cruce:
    - minúsculas
    - elimina caracteres raros
    - normaliza espacios
    """
    if pd.isna(text):
        return None

    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s&\-']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


# =========================
# S3
# =========================

def download_csv_from_s3(bucket_name: str, s3_key: str) -> pd.DataFrame:
    s3_client = boto3.client("s3")

    try:
        print(f"[INFO] Descargando CSV desde s3://{bucket_name}/{s3_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        df = pd.read_csv(response["Body"])
        print("[OK] CSV descargado correctamente desde S3.")
        return df

    except NoCredentialsError:
        raise RuntimeError("No se encontraron credenciales de AWS configuradas.")
    except PartialCredentialsError:
        raise RuntimeError("Las credenciales de AWS están incompletas.")
    except ClientError as e:
        raise RuntimeError(f"Error al descargar el archivo desde S3: {e}")


def upload_file_to_s3(local_file_path: str, bucket_name: str, s3_key: str) -> None:
    if not os.path.isfile(local_file_path):
        raise FileNotFoundError(f"No se encontró el archivo local: {local_file_path}")

    s3_client = boto3.client("s3")

    try:
        file_size = os.path.getsize(local_file_path)
        print(f"[INFO] Subiendo '{local_file_path}'")
        print(f"[INFO] Tamaño: {file_size / (1024 * 1024):.2f} MB")
        print(f"[INFO] Destino: s3://{bucket_name}/{s3_key}")

        s3_client.upload_file(local_file_path, bucket_name, s3_key)

        print("[OK] Archivo subido correctamente a S3.")

    except NoCredentialsError:
        raise RuntimeError("No se encontraron credenciales de AWS configuradas.")
    except PartialCredentialsError:
        raise RuntimeError("Las credenciales de AWS están incompletas.")
    except ClientError as e:
        raise RuntimeError(f"Error al subir el archivo a S3: {e}")


# =========================
# LIMPIEZA DEL DATASET
# =========================

def clean_spotify_dataset(df: pd.DataFrame, output_file: str) -> pd.DataFrame:
    print("[INFO] Procesando dataset...")
    print(f"[INFO] Registros iniciales: {len(df)}")

    # 1. Eliminar duplicados por id
    if "id" in df.columns:
        df = df.drop_duplicates(subset=["id"])

    # 2. Limpiar columnas base
    df["name"] = df["name"].apply(clean_basic_text)
    df["artists"] = df["artists"].apply(extract_main_artist)

    # 3. Crear columnas limpias para joins
    df["track_clean"] = df["name"].apply(clean_track_name)
    df["artist_clean"] = df["artists"].apply(clean_artist_name)

    # 4. Booleano explicit -> entero
    if "explicit" in df.columns:
        df["explicit"] = (
            df["explicit"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": 1, "false": 0, "1": 1, "0": 0})
        )

    # 5. Asegurar year numérico
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

    # 6. Convertir columnas numéricas y rellenar nulos con la media
    numeric_columns = [
        "danceability",
        "energy",
        "key",
        "loudness",
        "mode",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
        "duration_ms",
        "time_signature",
        "year"
    ]

    existing_numeric_columns = [col for col in numeric_columns if col in df.columns]

    for col in existing_numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().sum() > 0:
            media_columna = df[col].mean()
            df[col] = df[col].fillna(media_columna)
            print(f"[INFO] Nulos rellenados en '{col}' con la media: {media_columna}")

    # Rellenar nulos de explicit con la moda si los hubiera
    if "explicit" in df.columns and df["explicit"].isna().sum() > 0:
        moda_explicit = df["explicit"].mode(dropna=True)
        valor_relleno = int(moda_explicit.iloc[0]) if not moda_explicit.empty else 0
        df["explicit"] = df["explicit"].fillna(valor_relleno)
        df["explicit"] = df["explicit"].astype(int)
        print(f"[INFO] Nulos rellenados en 'explicit' con la moda: {valor_relleno}")

    # 7. Eliminar registros sin claves mínimas para análisis/join
    df = df.dropna(subset=["name", "artists", "track_clean", "artist_clean", "year"])

    # 8. Eliminar columnas que no necesitas al final
    columns_to_drop = ["id", "album_id", "artist_ids", "release_date"]
    existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    df = df.drop(columns=existing_columns_to_drop)

    print(f"[INFO] Registros tras limpieza: {len(df)}")

    # 9. Comprobación final
    print("\n[INFO] Comprobación de nulos en columnas numéricas:")
    if existing_numeric_columns:
        print(df[existing_numeric_columns].isna().sum())

    print("\n[INFO] Columnas finales:")
    print(df.columns.tolist())

    print(f"\n[INFO] Guardando parquet local: {output_file}")
    df.to_parquet(output_file, index=False)

    return df


# =========================
# EJECUCIÓN PRINCIPAL
# =========================

def main():
    try:
        df_raw = download_csv_from_s3(BUCKET_NAME, RAW_S3_KEY)
        clean_spotify_dataset(df_raw, LOCAL_OUTPUT_FILE)
        upload_file_to_s3(LOCAL_OUTPUT_FILE, BUCKET_NAME, CLEAN_S3_KEY)

        print(f"\n[OK] Proceso completado.")
        print(f"[OK] Archivo final en S3: s3://{BUCKET_NAME}/{CLEAN_S3_KEY}")

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()