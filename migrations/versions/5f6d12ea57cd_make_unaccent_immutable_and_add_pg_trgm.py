"""make unaccent immutable and add pg_trgm

Revision ID: 5f6d12ea57cd
Revises: 2eebc37c5fa0
Create Date: 2026-05-15 21:51:01.588412

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f6d12ea57cd'
down_revision = '2eebc37c5fa0'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    
    # Force the unaccent function to be IMMUTABLE so we can index it
    op.execute("ALTER FUNCTION unaccent(text) IMMUTABLE;")



def downgrade():
    op.execute("ALTER FUNCTION unaccent(text) STABLE;")

