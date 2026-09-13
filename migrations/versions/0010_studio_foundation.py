import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "studio_controls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("live_enabled", sa.Boolean(), nullable=False),
        sa.Column("campaign_grants", sa.Integer(), nullable=False),
        sa.Column("brand_grants", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "studio_tenants",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("issuer", sa.String(length=512), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("campaign_grants", sa.Integer(), nullable=False),
        sa.Column("brand_grants", sa.Integer(), nullable=False),
        sa.Column("active_job", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issuer", "subject"),
    )
    op.create_table(
        "studio_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("request_key", sa.String(length=128), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
        sa.Column("counters", sa.JSON(), nullable=False),
        sa.Column("lease_owner", sa.String(length=64), nullable=True),
        sa.Column("lease_until", sa.Float(), nullable=False),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("finished_at", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["studio_tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "request_key"),
    )
    op.create_index(op.f("ix_studio_jobs_state"), "studio_jobs", ["state"], unique=False)
    op.create_index(op.f("ix_studio_jobs_tenant_id"), "studio_jobs", ["tenant_id"], unique=False)
    op.create_table(
        "studio_resources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["studio_tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_studio_resources_kind"), "studio_resources", ["kind"], unique=False)
    op.create_index(
        op.f("ix_studio_resources_tenant_id"), "studio_resources", ["tenant_id"], unique=False
    )
    op.create_table(
        "studio_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["studio_jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["studio_tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "sequence"),
    )
    op.create_index(op.f("ix_studio_events_job_id"), "studio_events", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_studio_events_tenant_id"), "studio_events", ["tenant_id"], unique=False
    )
    op.execute(
        "INSERT INTO studio_controls (id, live_enabled, campaign_grants, brand_grants) "
        "VALUES (1, false, 3, 3)"
    )


def downgrade():
    op.drop_table("studio_events")
    op.drop_table("studio_resources")
    op.drop_table("studio_jobs")
    op.drop_table("studio_tenants")
    op.drop_table("studio_controls")
