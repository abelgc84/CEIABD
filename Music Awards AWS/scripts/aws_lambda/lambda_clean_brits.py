import os
import re
import unicodedata
import json
import urllib.parse
import pandas as pd
import boto3

s3 = boto3.client("s3")

BUCKET_NAME = "datalake-agijonc-2026"
OUTPUT_PREFIX = "clean/brits/"
OUTPUT_FILE = "/tmp/brits_clean.parquet"


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
    if pd.isna(text):
        return None

    text = clean_basic_text(text)
    text = re.sub(r"\(.*?\)", " ", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s\\-'/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def parse_bool_to_int(value):
    if pd.isna(value):
        return 0

    value_str = str(value).strip().lower()

    if value_str in {"true", "1", "yes", "y"}:
        return 1
    if value_str in {"false", "0", "no", "n"}:
        return 0

    return 0


def clean_brits_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [normalize_column_name(col) for col in df.columns]

    rename_map = {
        "winner": "artist_name",
        "details": "award_name",
        "year": "year",
        "date": "award_date",
        "location": "location",
        "host": "host",
        "is_person": "is_person",
        "is_album_or_single": "is_album_or_single",
        "url": "url"
    }

    df = df.rename(columns=rename_map)

    df["artist_name"] = df["artist_name"].apply(clean_basic_text)
    df["award_name"] = df["award_name"].apply(clean_basic_text)

    if "location" in df.columns:
        df["location"] = df["location"].apply(clean_basic_text)

    if "host" in df.columns:
        df["host"] = df["host"].apply(clean_basic_text)

    df["artist_clean"] = df["artist_name"].apply(clean_artist_name)
    df["award_name_clean"] = df["award_name"].apply(clean_basic_text)

    df["track_name"] = None
    df["track_clean"] = None

    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    if "is_person" in df.columns:
        df["is_person"] = df["is_person"].apply(parse_bool_to_int).astype(int)

    if "is_album_or_single" in df.columns:
        df["is_album_or_single"] = df["is_album_or_single"].apply(parse_bool_to_int).astype(int)

    df = df.dropna(subset=["year", "award_name"])
    df = df.dropna(subset=["artist_name", "artist_clean"])

    df["year"] = df["year"].astype(int)

    dedupe_subset = ["year", "artist_clean", "award_name_clean"]
    df = df.drop_duplicates(subset=dedupe_subset)

    columns_to_drop_final = ["url", "award_date"]
    existing_drop_final = [c for c in columns_to_drop_final if c in df.columns]
    if existing_drop_final:
        df = df.drop(columns=existing_drop_final)

    return df


def lambda_handler(event, context):
    try:
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        print(f"[INFO] Archivo recibido: s3://{bucket}/{key}")

        if not key.startswith("raw/brits/") or not key.endswith(".csv"):
            return {
                "statusCode": 200,
                "body": f"Archivo ignorado: {key}"
            }

        response = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(response["Body"])

        print(f"[INFO] Registros iniciales: {len(df)}")

        df_clean = clean_brits_dataframe(df)

        print(f"[INFO] Registros tras limpieza: {len(df_clean)}")

        df_clean.to_parquet(OUTPUT_FILE, index=False)

        output_key = OUTPUT_PREFIX + "brits_clean.parquet"

        s3.upload_file(OUTPUT_FILE, BUCKET_NAME, output_key)

        print(f"[OK] Archivo limpio subido a s3://{BUCKET_NAME}/{output_key}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Proceso completado correctamente",
                "input": f"s3://{bucket}/{key}",
                "output": f"s3://{BUCKET_NAME}/{output_key}",
                "rows_clean": len(df_clean)
            })
        }

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise