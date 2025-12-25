"""Add semantic analysis columns to video_analyses.

Revision ID: 20251225_001
Revises:
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251225_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new columns for complete semantic analysis."""
    # Add performance_elements column (JSONB)
    op.add_column(
        "video_analyses",
        sa.Column("performance_elements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Add replication_guide column (JSONB)
    op.add_column(
        "video_analyses",
        sa.Column("replication_guide", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Add script_suggestion column (Text)
    op.add_column(
        "video_analyses",
        sa.Column("script_suggestion", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove semantic analysis columns."""
    op.drop_column("video_analyses", "script_suggestion")
    op.drop_column("video_analyses", "replication_guide")
    op.drop_column("video_analyses", "performance_elements")
