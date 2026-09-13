import sqlalchemy as sa
from alembic import op

revision = "0019_discovery_allowances"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("studio_tenants", "studio_controls"):
        for column in ("feed_grants", "testimonial_grants"):
            op.add_column(
                table, sa.Column(column, sa.Integer(), nullable=False, server_default="0")
            )


def downgrade():
    for table in ("studio_tenants", "studio_controls"):
        for column in ("feed_grants", "testimonial_grants"):
            op.drop_column(table, column)
