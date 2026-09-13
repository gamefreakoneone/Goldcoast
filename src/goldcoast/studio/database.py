import time
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def identifier():
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "studio_tenants"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255))
    issuer: Mapped[str] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="business")
    campaign_grants: Mapped[int] = mapped_column(Integer, default=0)
    brand_grants: Mapped[int] = mapped_column(Integer, default=0)
    active_job: Mapped[str | None] = mapped_column(String(64), nullable=True)
    __table_args__ = (UniqueConstraint("issuer", "subject"),)


class Resource(Base):
    __tablename__ = "studio_resources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("studio_tenants.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


class Job(Base):
    __tablename__ = "studio_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("studio_tenants.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    mode: Mapped[str] = mapped_column(String(20))
    request_key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    counters: Mapped[dict] = mapped_column(JSON, default=dict)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    next_sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    finished_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    __table_args__ = (UniqueConstraint("tenant_id", "request_key"),)


class Event(Base):
    __tablename__ = "studio_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("studio_jobs.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("studio_tenants.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[float] = mapped_column(Float, default=time.time)
    __table_args__ = (UniqueConstraint("job_id", "sequence"),)


class Controls(Base):
    __tablename__ = "studio_controls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    live_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    campaign_grants: Mapped[int] = mapped_column(Integer, default=3)
    brand_grants: Mapped[int] = mapped_column(Integer, default=3)


def session_factory(url: str):
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    return engine, sessionmaker(engine, expire_on_commit=False)
