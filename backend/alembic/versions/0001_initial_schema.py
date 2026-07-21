"""Initial PostGIS network schema.

Revision ID: 0001
Revises:
"""

import geoalchemy2
import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=True),
            nullable=False,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_assets_name", "assets", ["name"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])

    op.create_table(
        "service_locations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("asset_id", sa.String(length=64), sa.ForeignKey("assets.id"), unique=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("address", sa.String(length=240), nullable=False),
        sa.Column("account_type", sa.String(length=24), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
    )
    op.create_index("ix_service_locations_address", "service_locations", ["address"])
    op.create_index("ix_service_locations_account_type", "service_locations", ["account_type"])

    op.create_table(
        "cables",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("cable_type", sa.String(length=40), nullable=False),
        sa.Column(
            "start_asset_id", sa.String(length=64), sa.ForeignKey("assets.id"), nullable=False
        ),
        sa.Column("end_asset_id", sa.String(length=64), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("length_ft", sa.Float(), nullable=False),
        sa.Column("fiber_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry("LINESTRING", srid=4326, spatial_index=True),
            nullable=False,
        ),
        sa.Column("coordinates", sa.JSON(), nullable=False),
    )
    op.create_index("ix_cables_name", "cables", ["name"])
    op.create_index("ix_cables_cable_type", "cables", ["cable_type"])
    op.create_index("ix_cables_start_asset_id", "cables", ["start_asset_id"])
    op.create_index("ix_cables_end_asset_id", "cables", ["end_asset_id"])

    op.create_table(
        "fiber_strands",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column("cable_id", sa.String(length=64), sa.ForeignKey("cables.id"), nullable=False),
        sa.Column("strand_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
    )
    op.create_index("ix_fiber_strands_cable_id", "fiber_strands", ["cable_id"])

    op.create_table(
        "circuits",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "service_location_id",
            sa.String(length=64),
            sa.ForeignKey("service_locations.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("alternate_path_available", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_circuits_name", "circuits", ["name"])
    op.create_index("ix_circuits_service_location_id", "circuits", ["service_location_id"])

    op.create_table(
        "circuit_path_segments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("circuit_id", sa.String(length=64), sa.ForeignKey("circuits.id"), nullable=False),
        sa.Column("cable_id", sa.String(length=64), sa.ForeignKey("cables.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "start_asset_id", sa.String(length=64), sa.ForeignKey("assets.id"), nullable=False
        ),
        sa.Column("end_asset_id", sa.String(length=64), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("length_ft", sa.Float(), nullable=False),
        sa.Column("strand_number", sa.Integer(), nullable=False),
        sa.UniqueConstraint("circuit_id", "sequence", name="uq_circuit_segment_sequence"),
    )
    op.create_index("ix_circuit_path_segments_circuit_id", "circuit_path_segments", ["circuit_id"])
    op.create_index("ix_circuit_path_segments_cable_id", "circuit_path_segments", ["cable_id"])

    op.create_table(
        "otdr_tests",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("circuit_id", sa.String(length=64), sa.ForeignKey("circuits.id"), nullable=False),
        sa.Column(
            "launch_asset_id", sa.String(length=64), sa.ForeignKey("assets.id"), nullable=False
        ),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wavelength_nm", sa.Integer(), nullable=False),
        sa.Column("pulse_width_ns", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_otdr_tests_circuit_id", "otdr_tests", ["circuit_id"])

    op.create_table(
        "otdr_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("test_id", sa.String(length=64), sa.ForeignKey("otdr_tests.id"), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("distance_ft", sa.Float(), nullable=False),
        sa.Column("loss_db", sa.Float(), nullable=True),
        sa.Column("reflectance_db", sa.Float(), nullable=True),
        sa.Column("known_incident", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_otdr_events_test_id", "otdr_events", ["test_id"])


def downgrade() -> None:
    for table in (
        "otdr_events",
        "otdr_tests",
        "circuit_path_segments",
        "circuits",
        "fiber_strands",
        "cables",
        "service_locations",
        "assets",
    ):
        op.drop_table(table)
