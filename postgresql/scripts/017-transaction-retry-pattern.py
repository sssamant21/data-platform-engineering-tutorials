"""Teaching example: retry whole serializable transactions, never individual SQL.

connect() must return a fresh, unused Psycopg 3-compatible connection with
autocommit=False. No pooled transaction may already be open.
work(cursor) must reread decision data, never commit/rollback, and perform only
transactional database work. No email/API/file side effects.
Attempts are bounded; this is not a hard end-to-end application deadline.
Driver installation, credentials and actual PostgreSQL execution are separate.
"""
import math
import random
import time

RETRYABLE_SQLSTATES = frozenset({"40001", "40P01"})


def run_serializable(connect, work, *, max_attempts=3, base_delay=0.05,
                     max_delay=0.5, sleep=time.sleep, random_value=random.random):
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
        raise ValueError("Teaching helper accepts 1..10 total attempts")
    if not math.isfinite(base_delay) or not math.isfinite(max_delay) or not 0 <= base_delay <= max_delay:
        raise ValueError("Require finite 0 <= base_delay <= max_delay")
    for attempt in range(1, max_attempts + 1):
        connection = connect()  # Connection failures are not automatically retried.
        try:
            if connection.autocommit:
                raise ValueError("Require a fresh connection with autocommit=False")
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute("SET LOCAL lock_timeout = '1s'")
                result = work(cursor)
            connection.commit()  # Commit can itself raise 40001.
            return result
        except Exception as error:
            try:
                connection.rollback()
            except Exception:
                raise RuntimeError("Rollback failed; stop and reconcile connection state") from error
            if getattr(error, "sqlstate", None) not in RETRYABLE_SQLSTATES or attempt == max_attempts:
                raise
        finally:
            connection.close()  # Caller adapter must handle cleanup errors; do not retry them.
        fraction = random_value()
        if not 0 <= fraction <= 1:
            raise ValueError("Jitter source must return 0..1")
        sleep(min(max_delay, base_delay * 2 ** (attempt - 1)) * fraction)
