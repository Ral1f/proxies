from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, UniqueConstraint, func

from .db import Base
from .utils import build_proxy_url


class Proxy(Base):
    __tablename__ = "proxies"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "server",
            "username",
            "password",
            name="uq_proxy_identity",
        ),
    )

    id = Column(Integer, primary_key=True)
    provider = Column(String(64), index=True, nullable=False)
    server = Column(String(255), nullable=False)
    username = Column(String(255))
    password = Column(String(255))
    protocol = Column(String(32), default="http", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta = Column(JSON, default=dict)

    def as_url(self) -> str:
        return build_proxy_url(self.protocol, self.server, self.username, self.password)

    def touch(self):
        self.last_seen_at = datetime.now(timezone.utc)


ProxyModel = Proxy
