from __future__ import annotations

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    asset_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(24), default="active")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True)
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Cable(Base):
    __tablename__ = "cables"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    cable_type: Mapped[str] = mapped_column(String(40), index=True)
    start_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    end_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    length_ft: Mapped[float] = mapped_column(Float)
    fiber_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="active")
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True)
    )
    coordinates: Mapped[list[list[float]]] = mapped_column(JSON)

    strands: Mapped[list[FiberStrand]] = relationship(
        back_populates="cable", cascade="all, delete-orphan"
    )


class FiberStrand(Base):
    __tablename__ = "fiber_strands"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    cable_id: Mapped[str] = mapped_column(ForeignKey("cables.id"), index=True)
    strand_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="available")

    cable: Mapped[Cable] = relationship(back_populates="strands")


class ServiceLocation(Base):
    __tablename__ = "service_locations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(String(240), index=True)
    account_type: Mapped[str] = mapped_column(String(24), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class Circuit(Base):
    __tablename__ = "circuits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    service_location_id: Mapped[str] = mapped_column(ForeignKey("service_locations.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="active")
    alternate_path_available: Mapped[bool] = mapped_column(Boolean, default=False)

    path_segments: Mapped[list[CircuitPathSegment]] = relationship(
        back_populates="circuit",
        cascade="all, delete-orphan",
        order_by="CircuitPathSegment.sequence",
    )


class CircuitPathSegment(Base):
    __tablename__ = "circuit_path_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circuit_id: Mapped[str] = mapped_column(ForeignKey("circuits.id"), index=True)
    cable_id: Mapped[str] = mapped_column(ForeignKey("cables.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    start_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    end_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    length_ft: Mapped[float] = mapped_column(Float)
    strand_number: Mapped[int] = mapped_column(Integer)

    circuit: Mapped[Circuit] = relationship(back_populates="path_segments")


class OTDRTest(Base):
    __tablename__ = "otdr_tests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    circuit_id: Mapped[str] = mapped_column(ForeignKey("circuits.id"), index=True)
    launch_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    wavelength_nm: Mapped[int] = mapped_column(Integer, default=1550)
    pulse_width_ns: Mapped[int] = mapped_column(Integer, default=100)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class OTDREvent(Base):
    __tablename__ = "otdr_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    test_id: Mapped[str] = mapped_column(ForeignKey("otdr_tests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    distance_ft: Mapped[float] = mapped_column(Float)
    loss_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    reflectance_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    known_incident: Mapped[bool] = mapped_column(Boolean, default=False)
