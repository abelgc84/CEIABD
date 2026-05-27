import os
import sys
import re
import unicodedata
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# =========================
# CONFIGURACIÓN
# =========================

BUCKET_NAME = "datalake-agijonc-2026"

RAW_S3_KEY = "raw/grammys/Grammy Award Nominees and Winners 1958-2024.csv"
CLEAN_S3_KEY = "clean/grammys/grammys_clean.parquet"

LOCAL_OUTPUT_FILE = "grammys_clean.parquet"

# =========================
# FUNCIONES AUXILIARES
# =========================

def normalize_column_name(name: str) -> str:
    name = str(name).strip().lower()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("utf-8")
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def clean_basic_text(text):
    if pd.isna(text):
        return None

    text = str(text).lower().strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def clean_artist_name(text):
    """
    Limpieza para usar en joins por artista.
    """
    if pd.isna(text):
        return None

    text = clean_basic_text(text)
    text = re.sub(r"\(.*?\)", " ", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s\-'/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def clean_track_name(text):
    """
    Limpieza para usar en joins por canción/obra.
    """
    if pd.isna(text):
        return None

    text = clean_basic_text(text)

    # elimina contenido entre paréntesis y corchetes
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"\[.*?\]", " ", text)

    # elimina feat/ft/featuring y lo que venga después
    text = re.sub(r"\b(feat\.?|ft\.?|featuring)\b.*$", " ", text)

    # elimina palabras típicas de ruido
    patterns = [
        r"\balbum\b",
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

    text = re.sub(r"[^a-z0-9\s\-'/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def parse_winner(value):
    if pd.isna(value):
        return 0

    value_str = str(value).strip().lower()

    if value_str in {"true", "1", "yes", "y"}:
        return 1
    if value_str in {"false", "0", "no", "n"}:
        return 0

    return 0


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

def clean_grammys_dataset(df: pd.DataFrame, output_file: str) -> pd.DataFrame:
    print("[INFO] Procesando dataset...")
    print(f"[INFO] Registros iniciales: {len(df)}")
    print(f"[INFO] Columnas originales: {df.columns.tolist()}")

    # Normalizar nombres de columnas
    df.columns = [normalize_column_name(col) for col in df.columns]

    print(f"[INFO] Columnas normalizadas: {df.columns.tolist()}")

    # Renombrar columnas clave a nombres estándar
    rename_map = {
        "year": "year",
        "ceremony": "ceremony",
        "award_id": "award_id",
        "award_type": "award_type",
        "award_name": "award_name",
        "work": "track_name",
        "nominee": "artist_name",
        "winner": "winner"
    }

    df = df.rename(columns=rename_map)

    # Eliminar columna índice vacía del CSV si existe
    columns_to_drop_initial = ["unnamed_0", ""]
    existing_drop_initial = [c for c in columns_to_drop_initial if c in df.columns]
    if existing_drop_initial:
        df = df.drop(columns=existing_drop_initial)

    # Limpieza básica de columnas principales
    df["artist_name"] = df["artist_name"].apply(clean_basic_text)
    df["track_name"] = df["track_name"].apply(clean_basic_text)
    df["award_name"] = df["award_name"].apply(clean_basic_text)
    df["award_type"] = df["award_type"].apply(clean_basic_text)

    # Crear columnas limpias para joins
    df["artist_clean"] = df["artist_name"].apply(clean_artist_name)
    df["track_clean"] = df["track_name"].apply(clean_track_name)
    df["award_name_clean"] = df["award_name"].apply(clean_basic_text)

    # Convertir year a numérico
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    # Convertir winner a 0/1
    df["winner"] = df["winner"].apply(parse_winner).astype(int)

    # Eliminar registros sin información mínima útil
    df = df.dropna(subset=["year", "artist_name", "award_name", "artist_clean"])

    # Year entero
    df["year"] = df["year"].astype(int)

    # Eliminar duplicados
    dedupe_subset = ["year", "artist_clean", "track_clean", "award_name_clean", "winner"]
    df = df.drop_duplicates(subset=dedupe_subset)

    # Eliminar columnas poco útiles para el análisis final
    columns_to_drop_final = ["award_id"]
    existing_drop_final = [c for c in columns_to_drop_final if c in df.columns]
    if existing_drop_final:
        df = df.drop(columns=existing_drop_final)

    print(f"[INFO] Registros tras limpieza: {len(df)}")

    print("\n[INFO] Columnas finales:")
    print(df.columns.tolist())

    print("\n[INFO] Nulos por columna principal:")
    cols_to_check = [
        "year", "artist_name", "track_name",
        "award_name", "winner", "artist_clean", "track_clean"
    ]
    existing_check = [c for c in cols_to_check if c in df.columns]
    print(df[existing_check].isna().sum())

    print(f"\n[INFO] Guardando parquet local: {output_file}")
    df.to_parquet(output_file, index=False)

    return df


# =========================
# MAIN
# =========================

def main():
    try:
        df_raw = download_csv_from_s3(BUCKET_NAME, RAW_S3_KEY)
        clean_grammys_dataset(df_raw, LOCAL_OUTPUT_FILE)
        upload_file_to_s3(LOCAL_OUTPUT_FILE, BUCKET_NAME, CLEAN_S3_KEY)

        print(f"\n[OK] Proceso completado.")
        print(f"[OK] Archivo final en S3: s3://{BUCKET_NAME}/{CLEAN_S3_KEY}")

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()