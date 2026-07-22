"""
config.py

Application configuration.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:

    # =====================================================
    # MySQL
    # =====================================================

    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "Password"
    database: str = "Database"

    # =====================================================
    # Batch
    # =====================================================

    fetch_size: int = 5000

    update_batch_size: int = 5000


config = Config()
