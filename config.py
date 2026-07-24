import os
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Config:

    # =====================================================
    # MySQL
    # =====================================================

    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "root"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", os.getenv("MYSQL_PWD", "Qu@ngnvd123")))
    database: str = field(default_factory=lambda: os.getenv("DB_NAME", "cdss"))

    # =====================================================
    # Batch
    # =====================================================

    fetch_size: int = 5000

    update_batch_size: int = 5000


config = Config()

