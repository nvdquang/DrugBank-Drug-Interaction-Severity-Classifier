"""
database.py

MySQL database access layer.
"""

from __future__ import annotations

from typing import Iterator

import pymysql
from pymysql.cursors import SSDictCursor, DictCursor

from config import config
from models import Interaction, SeverityResult


class Database:
    """
    MySQL database helper.
    """

    def __init__(self) -> None:

        # -----------------------------------------
        # Read connection (streaming)
        # -----------------------------------------

        self.read_conn = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=SSDictCursor,
        )

        # -----------------------------------------
        # Write connection
        # -----------------------------------------

        self.write_conn = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=DictCursor,
        )

    # =====================================================
    # Read
    # =====================================================

    def load_interactions(
        self,
        limit: int | None = None,
    ) -> Iterator[list[Interaction]]:

        sql = """
            SELECT
                id,
                description
            FROM drug_interactions
            WHERE description IS NOT NULL
              AND description <> ''
        """

        if limit:
            sql += f"\nLIMIT {limit}"

        with self.read_conn.cursor() as cursor:

            cursor.execute(sql)

            while True:

                rows = cursor.fetchmany(
                    config.fetch_size
                )

                if not rows:
                    break

                yield [

                    Interaction(
                        id=row["id"],
                        description=row["description"],
                    )

                    for row in rows

                ]

    # =====================================================
    # Update
    # =====================================================

    def update_batch(
        self,
        results: list[SeverityResult],
    ) -> None:

        if not results:
            return

        sql = """
            UPDATE drug_interactions
            SET severity=%s,
                canonical_event=%s, # Remove if not needed
                pattern=%s,         # Remove if not needed
                confidence=%s       # Remove if not needed
            WHERE id=%s
        """

        data = [

            (
                result.severity,
                result.canonical_event, # Remove if not needed
                result.pattern,         # Remove if not needed
                result.confidence,      # Remove if not needed
                result.id,
            )

            for result in results

        ]

        with self.write_conn.cursor() as cursor:

            cursor.executemany(
                sql,
                data,
            )

        self.write_conn.commit()

    # =====================================================
    # Close
    # =====================================================

    def close(self) -> None:

        self.read_conn.close()

        self.write_conn.close()