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

        try:
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
        except pymysql.Error as err:
            print("\n[ERROR] Could not connect to MySQL database!")
            print(f"Details: {err}")
            print(f"\nCurrent Database Config:")
            print(f"  - Host:     {config.host}:{config.port}")
            print(f"  - User:     {config.user}")
            print(f"  - Database: {config.database}")
            print("\n[HINT] How to fix:")
            print("  1. Update credentials directly in config.py")
            print("  2. Or set Environment Variables before running: DB_USER, DB_PASSWORD, DB_NAME, DB_HOST, DB_PORT")
            raise err



    # =====================================================
    # Read
    # =====================================================

    def load_interactions(
        self,
        limit: int | None = None,
        offset: int | None = None,
        start_id: int | None = None,
        end_id: int | None = None,
        only_unknown: bool = False,
    ) -> Iterator[list[Interaction]]:

        sql = """
            SELECT
                id,
                description
            FROM drug_interactions
            WHERE description IS NOT NULL
              AND description <> ''
        """

        if only_unknown:
            sql += "\n              AND (severity IS NULL OR severity = '' OR severity = 'unknown')"

        if start_id is not None:
            sql += f"\n              AND id >= {start_id}"

        if end_id is not None:
            sql += f"\n              AND id <= {end_id}"

        if limit is not None:
            sql += f"\nLIMIT {limit}"
            if offset is not None:
                sql += f" OFFSET {offset}"

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