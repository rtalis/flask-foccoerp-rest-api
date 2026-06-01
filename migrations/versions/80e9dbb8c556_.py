"""empty message

Revision ID: 80e9dbb8c556
Revises: 5f6d12ea57cd, add_search_term
Create Date: 2026-05-31 22:12:17.419921

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '80e9dbb8c556'
down_revision = ('5f6d12ea57cd', 'add_search_term')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
