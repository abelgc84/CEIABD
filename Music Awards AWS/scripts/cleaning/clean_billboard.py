import os
import sys
import re
import unicodedata
from io import BytesIO
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# =========================
# CONFIGURACIÓN
# =========================

BUCKET_NAME = "datalake-agijonc-2026"

RAW_S3_KEY = "raw/billboard/billboard_winners.csv"
CLEAN_S3_KEY = "clean/billboard/billboard_clean.parquet"

LOCAL_OUTPUT_FILE = "billboard_clean.parquet"

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

    text = str(text).strip().lower()
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def clean_artist_name(text):
    if pd.isna(text):
        return None

    text = clean_basic_text(text)
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r'"[^"]*"', " ", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s\-'/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def clean_track_name(text):
    if pd.isna(text):
        return None

    text = clean_basic_text(text)
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"\[.*?\]", " ", text)
    text = re.sub(r"\b(feat\.?|ft\.?|featuring)\b.*$", " ", text)

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

    text = re.sub(r"[^a-z0-9\s\-'/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def extract_track_from_winner_if_missing(winner_text, song_text):
    if song_text is not None and str(song_text).strip() != "":
        return song_text

    if winner_text is None:
        return None

    winner_text = str(winner_text).replace("“", '"').replace("”", '"')
    match = re.search(r'"([^"]+)"', winner_text)
    if match:
        return match.group(1)

    return None


def clean_winner_artist_field(winner_text):
    if pd.isna(winner_text):
        return None

    text = str(winner_text).replace("“", '"').replace("”", '"')
    text = re.sub(r'"[^"]*"', " ", text)
    text = re.sub(r"\(.*?\)", " ", text)
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

def clean_billboard_dataset(df: pd.DataFrame, output_file: str) -> pd.DataFrame:
    print("[INFO] Procesando dataset...")
    print(f"[INFO] Registros iniciales: {len(df)}")
    print(f"[INFO] Columnas originales: {df.columns.tolist()}")

    df.columns = [normalize_column_name(col) for col in df.columns]

    print(f"[INFO] Columnas normalizadas: {df.columns.tolist()}")

    required_columns = ["year", "category", "winner", "song"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {missing}")

    df = df.rename(columns={
        "category": "award_name",
        "winner": "artist_name",
        "song": "track_name"
    })

    df["track_name"] = df.apply(
        lambda row: extract_track_from_winner_if_missing(row["artist_name"], row["track_name"]),
        axis=1
    )

    df["artist_name"] = df["artist_name"].apply(clean_winner_artist_field)

    df["artist_name"] = df["artist_name"].apply(clean_basic_text)
    df["track_name"] = df["track_name"].apply(clean_basic_text)
    df["award_name"] = df["award_name"].apply(clean_basic_text)

    df["artist_clean"] = df["artist_name"].apply(clean_artist_name)
    df["track_clean"] = df["track_name"].apply(clean_track_name)
    df["award_name_clean"] = df["award_name"].apply(clean_basic_text)

    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = df.dropna(subset=["year", "artist_name", "award_name", "artist_clean"])
    df["year"] = df["year"].astype(int)

    dedupe_subset = ["year", "artist_clean", "track_clean", "award_name_clean"]
    df = df.drop_duplicates(subset=dedupe_subset)

    print(f"[INFO] Registros tras limpieza: {len(df)}")

    print("\n[INFO] Columnas finales:")
    print(df.columns.tolist())

    print("\n[INFO] Nulos por columna principal:")
    cols_to_check = [
        "year", "artist_name", "track_name",
        "award_name", "artist_clean",
        "track_clean", "award_name_clean"
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
        clean_billboard_dataset(df_raw, LOCAL_OUTPUT_FILE)
        upload_file_to_s3(LOCAL_OUTPUT_FILE, BUCKET_NAME, CLEAN_S3_KEY)

        print(f"\n[OK] Proceso completado.")
        print(f"[OK] Archivo final en S3: s3://{BUCKET_NAME}/{CLEAN_S3_KEY}")

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()