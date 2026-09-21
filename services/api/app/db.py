from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings

settings = get_settings()
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)

parts = urlsplit(database_url)
query_params = dict(parse_qsl(parts.query, keep_blank_values=True))
ssl_mode = query_params.pop("sslmode", None)
database_url = urlunsplit(
    (parts.scheme, parts.netloc, parts.path, urlencode(query_params), parts.fragment)
)
connect_args = {}
if ssl_mode and ssl_mode.lower() not in {"disable", "allow", "prefer"}:
    connect_args["ssl"] = True

engine = create_async_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
