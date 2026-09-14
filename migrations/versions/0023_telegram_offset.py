import sqlalchemy as sa
from alembic import op

revision = "0023_telegram_offset"
down_revision = "0019_discovery_allowances"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "studio_controls",
        sa.Column("telegram_offset", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("studio_controls", "telegram_offset")
