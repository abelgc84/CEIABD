import os
import sys
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# =========================
# CONFIGURACIÓN
# =========================

LOCAL_FILE = "billboard_winners.csv"

BUCKET_NAME = "datalake-agijonc-2026"

S3_KEY = "raw/billboard/billboard_winners.csv"

# =========================
# FUNCIÓN DE SUBIDA
# =========================

def upload_to_s3(local_file, bucket, key):

    if not os.path.isfile(local_file):
        raise FileNotFoundError(f"No se encontró el archivo: {local_file}")

    s3 = boto3.client("s3")

    try:
        size_mb = os.path.getsize(local_file) / (1024 * 1024)

        print(f"[INFO] Archivo local: {local_file}")
        print(f"[INFO] Tamaño: {size_mb:.2f} MB")
        print(f"[INFO] Subiendo a: s3://{bucket}/{key}")

        s3.upload_file(local_file, bucket, key)

        print("[OK] Subida completada correctamente.")

    except NoCredentialsError:
        print("[ERROR] No se encontraron credenciales AWS configuradas.")
        sys.exit(1)

    except PartialCredentialsError:
        print("[ERROR] Credenciales AWS incompletas.")
        sys.exit(1)

    except ClientError as e:
        print(f"[ERROR] Error al subir el archivo: {e}")
        sys.exit(1)

# =========================
# EJECUCIÓN
# =========================

if __name__ == "__main__":

    try:
        upload_to_s3(LOCAL_FILE, BUCKET_NAME, S3_KEY)

        print("\n[OK] Archivo disponible en:")
        print(f"s3://{BUCKET_NAME}/{S3_KEY}")

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)