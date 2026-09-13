from alembic import context
from sqlalchemy import create_engine

from goldcoast.studio.config import StudioSettings
from goldcoast.studio.database import Base

engine = create_engine(StudioSettings.from_env().database_url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
