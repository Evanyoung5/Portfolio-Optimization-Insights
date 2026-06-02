import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DataStoreSettings:
    database_url: str
    redis_url: str


def get_data_store_settings() -> DataStoreSettings:
    return DataStoreSettings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://portfolio:portfolio@localhost:5432/portfolio",
        ),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )
