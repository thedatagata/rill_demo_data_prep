import dlt
from dlt.sources.filesystem import filesystem 
import polars as pl
import logging
from rich.console import Console
from rich.logging import RichHandler
import warnings
import json 
import ast
from typing import Dict, Iterator, Optional
from dlt.helpers.dbt import create_runner
import os

console = Console()

# Configure logging levels and silence warnings
for logger in ['botocore', 'boto3', 'urllib3', 's3transfer', 'fsspec', 'aiobotocore']:
    logging.getLogger(logger).setLevel(logging.WARNING)
warnings.filterwarnings('ignore', message='.*checksum.*')
warnings.filterwarnings('ignore', message='.*delimiter.*')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True),
        logging.FileHandler('pipeline.log')
    ]
)

logger = logging.getLogger(__name__)

def execute_pipeline(file_object):
    """Execute the data pipeline for a given file object."""
    try:
        pipeline = dlt.pipeline(
            pipeline_name="filter_data_swamp",
            destination=dlt.destinations.duckdb("./data_swamp_models/data_swamp.duckdb"),
            dataset_name="source_data",
            progress="log"
        )
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        raise

    @dlt.resource(max_table_nesting=3)
    def extract():
        """Extract stage: Reads data in chunks to manage memory."""
        try:
            logger.info(f"Starting data extraction from: {file_object['file_url']}")
            
            # Scan first to get total row count
            total_rows = pl.scan_parquet(file_object['file_url']).select(pl.count()).collect().item()
            logger.info(f"Total rows to process: {total_rows}")
            
            # Process in chunks of 100k rows
            for chunk_start in range(0, total_rows, 100_000):
                df = pl.scan_parquet(
                    file_object['file_url'],
                    parallel="row_groups",
                    low_memory=True,
                    use_statistics=True,
                    cache=False
                ).slice(chunk_start, 100_000).collect()
                
                logger.info(f"Processing chunk of {df.height} rows")
                yield df
                
        except Exception as e:
            logger.error(f"Extract error: {e}")
            raise

    @dlt.transformer(data_from=extract, parallelized=True)
    def transform(df: pl.DataFrame) -> Iterator[Dict]:
        def process_hits(hits):
            try:
                return ast.literal_eval(hits)
            except Exception as e:
                logger.error(f"Error processing hits: {e}")
                return None

        dates = df.select('date').unique().to_series().sort()
        logger.info(f"Processing {len(dates)} unique dates")
        
        # Process one date at a time instead of all at once
        for date in dates:
            date_df = df.filter(pl.col('date') == date)
            hits_chunk = date_df.select(['visit_id', 'full_visitor_id', 'hits']).to_pandas()
            hits_chunk['hits'] = hits_chunk['hits'].apply(process_hits)
            hits_chunk = hits_chunk.dropna(subset=['hits'])
                
            sessions_chunk = date_df.select([
                'visit_id', 'full_visitor_id', 'visit_number', 'visit_start_time', 'date',
                'device', 'geo_network', 'totals', 'traffic_source'
            ])
            chunk_df = sessions_chunk.join(pl.DataFrame(hits_chunk), on=['visit_id','full_visitor_id'], how='inner')
            yield chunk_df

    @dlt.transformer(data_from=transform)
    def load(df: pl.DataFrame) -> Iterator[Dict]:
        try:
            yield df.to_dicts()
        except Exception as e:
            logger.error(f"Load error: {e}")
            raise

    pipeline_info = pipeline.run(load)
    
    logger.info("Running dbt models...")
    dbt = dlt.dbt.package(
        pipeline, 
        "data_swamp_models"
    )
    models = dbt.run_all() 
    for m in models:
        print(
            f"Model {m.model_name} materialized" +
            f" in {m.time}" +
            f" with status {m.status}" +
            f" and message {m.message}"
        )
    return pipeline_info

if __name__ == '__main__':
    logger.info("Starting data pipeline...")
    os.makedirs("data", exist_ok=True)
    
    for file_object in filesystem():
        try:
            logger.info(f"Processing file: {file_object['file_url']}")
            info = execute_pipeline(file_object)
            logger.info(f"File processed: {info}")
        except Exception as e:
            logger.error(f"Failed to process file {file_object['file_url']}: {e}")
            continue