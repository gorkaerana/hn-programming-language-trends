# /// script
# dependencies = ["altair", "polars", "vl-convert-python"]
# ///
import altair as alt
import polars as pl


languages = {"C++": "cpp", "Python": "python", "Rust": "rust"}
df = (
    pl.scan_ndjson("scraped.ndjson")
    # First, find mentions to `languages`
    .with_columns(
        *(
            (
                pl.col("comment_text")
                .str.to_lowercase()
                .str.contains(language.lower(), literal=True)
                .alias(label)
            )
            for language, label in languages.items()
        )
    )
    # Second, extract the month and year
    .with_columns(
        month=(
            pl.col("story_title")
            .str.extract("\\(([a-zA-Z]+) ([0-9]+).*\\)", 1)
            .str.to_titlecase()
            # Couldn't make `pl.Expr.str.to_date` work with date specifier `%B`
            .str.slice(offset=0, length=3)
        ),
        year=(pl.col("story_title").str.extract("\\(([a-zA-Z]+) ([0-9]+).*\\)", 2)),
    )
    .with_columns(
        date=pl.concat_str(
            [pl.col("month"), pl.col("year")], separator=" "
        ).str.to_date("%b %Y")
    )
    # TODO: do not drop nulls. Only 0.05% of observations are dropped though
    .filter(pl.col("date").is_not_null())
    .sort("date")
    # And create a rolling average over every six months
    .rolling(index_column="date", period="6mo")
    # Finally, manipulate the table for pretty plotting
    .agg([pl.col(label).mean() for label in languages.values()])
    .unpivot(list(languages.values()), index="date")
    .with_columns(
        variable=pl.col("variable").replace({v: k for k, v in languages.items()})
    )
    .collect()
    .plot.line(
        x=alt.X("date", title="Date"),
        y=alt.Y("value", title="Percentage of comments mentioning a language"),
        color=alt.Color("variable", title="Programming language"),
    )
    .properties(width=800, height=800)
    .save("chart.png")
)
