from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401  (registers all models on Base.metadata)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # One transaction per revision, not one transaction for the whole
        # run: e7b3f2a91c05 adds 'SUPER_ADMIN' to the user_role enum, and a
        # later migration uses that value in an INSERT. Postgres forbids
        # using a freshly added enum value in the same transaction that
        # added it, so a fresh install applying several pending revisions in
        # one `alembic upgrade head` needs each to commit separately.
        context.configure(connection=connection, target_metadata=target_metadata, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
