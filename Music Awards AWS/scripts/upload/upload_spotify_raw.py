import os
import sys
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# =========================
# CONFIGURACIÓN
# =========================
LOCAL_FILE_PATH = r"tracks_features.csv"
BUCKET_NAME = "datalake-agijonc-2026"
S3_KEY = "raw/spotify/tracks_features.csv"

# =========================
# FUNCIÓN DE SUBIDA
# =========================
def upload_file_to_s3(local_file_path: str, bucket_name: str, s3_key: str) -> None:
    """
    Sube un archivo local a un bucket S3.

    Args:
        local_file_path: Ruta local del archivo.
        bucket_name: Nombre del bucket destino.
        s3_key: Ruta/clave dentro del bucket.
    """
    if not os.path.isfile(local_file_path):
        raise FileNotFoundError(f"No se encontró el archivo local: {local_file_path}")

    s3_client = boto3.client("s3")

    try:
        file_size = os.path.getsize(local_file_path)
        print(f"[INFO] Iniciando subida de '{local_file_path}'")
        print(f"[INFO] Tamaño del archivo: {file_size / (1024 * 1024):.2f} MB")
        print(f"[INFO] Destino: s3://{bucket_name}/{s3_key}")

        s3_client.upload_file(local_file_path, bucket_name, s3_key)

        print("[OK] Archivo subido correctamente.")
        print(f"[OK] Ruta final: s3://{bucket_name}/{s3_key}")

    except FileNotFoundError:
        raise
    except NoCredentialsError:
        raise RuntimeError("No se encontraron credenciales de AWS configuradas.")
    except PartialCredentialsError:
        raise RuntimeError("Las credenciales de AWS están incompletas.")
    except ClientError as e:
        raise RuntimeError(f"Error al subir el archivo a S3: {e}")

# =========================
# EJECUCIÓN
# =========================
if __name__ == "__main__":
    try:
        upload_file_to_s3(
            local_file_path=LOCAL_FILE_PATH,
            bucket_name=BUCKET_NAME,
            s3_key=S3_KEY
        )
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)