"""DocuMind AI — Database initialization script.

Creates all tables defined in the ORM models. Run this on application startup
or as a standalone script to set up the database schema.
"""

import asyncio
import logging

from utils.database import engine, Base

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Create all database tables if they do not already exist.

    Uses the SQLAlchemy async engine to issue CREATE TABLE statements for
    every model registered on the declarative Base.
    """
    logger.info("Initializing database — creating tables if they do not exist")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialization complete")


async def drop_database() -> None:
    """Drop all database tables. Use with caution — destroys all data.

    Intended for development and testing only.
    """
    logger.warning("Dropping all database tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All tables dropped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_database())
