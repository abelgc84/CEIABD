import sys
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql import types as T
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions

# ==========================================
# PARÁMETROS
# ==========================================

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# ==========================================
# RUTAS S3
# ==========================================

SPOTIFY_PATH   = "s3://datalake-agijonc-2026/clean/spotify/"
GRAMMYS_PATH   = "s3://datalake-agijonc-2026/clean/grammys/"
BRITS_PATH     = "s3://datalake-agijonc-2026/clean/brits/"
BILLBOARD_PATH = "s3://datalake-agijonc-2026/clean/billboard/"
OUTPUT_PATH    = "s3://datalake-agijonc-2026/processed/"

# ==========================================
# LECTURA
# ==========================================

spotify_df = spark.read.parquet(SPOTIFY_PATH)
grammys_df = spark.read.parquet(GRAMMYS_PATH)
brits_df = spark.read.parquet(BRITS_PATH)
billboard_df = spark.read.parquet(BILLBOARD_PATH)

# ==========================================
# NORMALIZACIÓN EXTRA DE SEGURIDAD
# ==========================================

def normalize_key(col_name):
    return F.lower(F.trim(F.col(col_name)))

spotify_df = (
    spotify_df
    .withColumn("artist_clean", normalize_key("artist_clean"))
    .withColumn("track_clean", normalize_key("track_clean"))
    .withColumn("year", F.col("year").cast("int"))
)

grammys_df = (
    grammys_df
    .withColumn("artist_clean", normalize_key("artist_clean"))
    .withColumn("track_clean", normalize_key("track_clean"))
    .withColumn("year", F.col("year").cast("int"))
    .withColumn("winner", F.col("winner").cast("int"))
)

brits_df = (
    brits_df
    .withColumn("artist_clean", normalize_key("artist_clean"))
    .withColumn("year", F.col("year").cast("int"))
)

billboard_df = (
    billboard_df
    .withColumn("artist_clean", normalize_key("artist_clean"))
    .withColumn("track_clean", normalize_key("track_clean"))
    .withColumn("year", F.col("year").cast("int"))
)

# ==========================================
# AGREGACIONES DE PREMIOS
# ==========================================

# ---------
# GRAMMYS
# Join principal por artista + track + year
# ---------

grammys_track = (
    grammys_df
    .filter(F.col("track_clean").isNotNull())
    .groupBy("artist_clean", "track_clean", "year")
    .agg(
        F.count("*").alias("grammy_nominations_track"),
        F.max("winner").alias("grammy_winner_track")
    )
)

grammys_artist = (
    grammys_df
    .groupBy("artist_clean", "year")
    .agg(
        F.count("*").alias("grammy_nominations_artist"),
        F.max("winner").alias("grammy_winner_artist")
    )
)

# ---------
# BRITS
# Dataset más orientado a artista + año
# ---------

brits_artist = (
    brits_df
    .groupBy("artist_clean", "year")
    .agg(
        F.count("*").alias("brit_awards_count"),
        F.lit(1).alias("has_brit_award")
    )
)

# ---------
# BILLBOARD
# Puede tener nivel artista y nivel track
# ---------

billboard_track = (
    billboard_df
    .filter(F.col("track_clean").isNotNull())
    .groupBy("artist_clean", "track_clean", "year")
    .agg(
        F.count("*").alias("billboard_awards_track"),
        F.lit(1).alias("has_billboard_track_award")
    )
)

billboard_artist = (
    billboard_df
    .groupBy("artist_clean", "year")
    .agg(
        F.count("*").alias("billboard_awards_artist"),
        F.lit(1).alias("has_billboard_artist_award")
    )
)

# ==========================================
# JOINS CONTRA SPOTIFY
# ==========================================

final_df = (
    spotify_df.alias("s")
    .join(
        grammys_track.alias("gt"),
        on=[
            F.col("s.artist_clean") == F.col("gt.artist_clean"),
            F.col("s.track_clean") == F.col("gt.track_clean"),
            F.col("s.year") == F.col("gt.year")
        ],
        how="left"
    )
    .join(
        grammys_artist.alias("ga"),
        on=[
            F.col("s.artist_clean") == F.col("ga.artist_clean"),
            F.col("s.year") == F.col("ga.year")
        ],
        how="left"
    )
    .join(
        brits_artist.alias("ba"),
        on=[
            F.col("s.artist_clean") == F.col("ba.artist_clean"),
            F.col("s.year") == F.col("ba.year")
        ],
        how="left"
    )
    .join(
        billboard_track.alias("bt"),
        on=[
            F.col("s.artist_clean") == F.col("bt.artist_clean"),
            F.col("s.track_clean") == F.col("bt.track_clean"),
            F.col("s.year") == F.col("bt.year")
        ],
        how="left"
    )
    .join(
        billboard_artist.alias("bar"),
        on=[
            F.col("s.artist_clean") == F.col("bar.artist_clean"),
            F.col("s.year") == F.col("bar.year")
        ],
        how="left"
    )
)

# ==========================================
# SELECCIÓN Y COLUMNAS FINALES
# ==========================================

final_df = final_df.select(
    # columnas base de spotify
    F.col("s.name").alias("track_name"),
    F.col("s.artists").alias("artist_name"),
    F.col("s.album"),
    F.col("s.track_number"),
    F.col("s.disc_number"),
    F.col("s.explicit"),
    F.col("s.danceability"),
    F.col("s.energy"),
    F.col("s.key"),
    F.col("s.loudness"),
    F.col("s.mode"),
    F.col("s.speechiness"),
    F.col("s.acousticness"),
    F.col("s.instrumentalness"),
    F.col("s.liveness"),
    F.col("s.valence"),
    F.col("s.tempo"),
    F.col("s.duration_ms"),
    F.col("s.time_signature"),
    F.col("s.year"),
    F.col("s.artist_clean"),
    F.col("s.track_clean"),

    # métricas Grammy
    F.coalesce(F.col("gt.grammy_nominations_track"), F.lit(0)).alias("grammy_nominations_track"),
    F.coalesce(F.col("gt.grammy_winner_track"), F.lit(0)).alias("grammy_winner_track"),
    F.coalesce(F.col("ga.grammy_nominations_artist"), F.lit(0)).alias("grammy_nominations_artist"),
    F.coalesce(F.col("ga.grammy_winner_artist"), F.lit(0)).alias("grammy_winner_artist"),

    # métricas BRIT
    F.coalesce(F.col("ba.brit_awards_count"), F.lit(0)).alias("brit_awards_count"),
    F.coalesce(F.col("ba.has_brit_award"), F.lit(0)).alias("has_brit_award"),

    # métricas Billboard
    F.coalesce(F.col("bt.billboard_awards_track"), F.lit(0)).alias("billboard_awards_track"),
    F.coalesce(F.col("bt.has_billboard_track_award"), F.lit(0)).alias("has_billboard_track_award"),
    F.coalesce(F.col("bar.billboard_awards_artist"), F.lit(0)).alias("billboard_awards_artist"),
    F.coalesce(F.col("bar.has_billboard_artist_award"), F.lit(0)).alias("has_billboard_artist_award")
)

# Flags globales útiles para Athena
final_df = (
    final_df
    .withColumn(
        "has_any_grammy",
        F.when(
            (F.col("grammy_nominations_track") > 0) | (F.col("grammy_nominations_artist") > 0),
            1
        ).otherwise(0)
    )
    .withColumn(
        "has_any_billboard_award",
        F.when(
            (F.col("billboard_awards_track") > 0) | (F.col("billboard_awards_artist") > 0),
            1
        ).otherwise(0)
    )
    .withColumn(
        "has_any_major_award",
        F.when(
            (F.col("has_any_grammy") > 0) |
            (F.col("has_brit_award") > 0) |
            (F.col("has_any_billboard_award") > 0),
            1
        ).otherwise(0)
    )
)

# ==========================================
# ESCRITURA EN S3 PARTICIONADA POR YEAR
# ==========================================

(
    final_df
    .repartition("year")
    .write
    .mode("overwrite")
    .partitionBy("year")
    .parquet(OUTPUT_PATH)
)

job.commit()