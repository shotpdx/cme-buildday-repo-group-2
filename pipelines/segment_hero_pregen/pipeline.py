"""SDP: compute unique segment keys for hero pre-generation."""
import dlt
from pyspark.sql import functions as F


@dlt.table(
    name="segment_hero_keys",
    comment="Unique (primary_segment, value_segment, top_genre_1) combinations that need hero images.",
)
def segment_hero_keys():
    return (
        dlt.read("cme_outcomes_uswest.media_demo.gold_media_audience_segments")
        .groupBy("primary_segment", "value_segment", "top_genre_1")
        .agg(F.count("*").alias("customer_count"))
        .filter(F.col("customer_count") >= 3)  # only segments with enough customers to justify pre-gen
        .orderBy(F.col("customer_count").desc())
    )
