"""add_cascade_delete_to_purchase_item_nfe_matches

Revision ID: 3d5efbd777e6
Revises: 613d19744f10
Create Date: 2025-12-01 09:30:56.762899

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d5efbd777e6'
down_revision = '613d19744f10'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing foreign key constraint
    op.drop_constraint('purchase_item_nfe_matches_purchase_item_id_fkey', 'purchase_item_nfe_matches', type_='foreignkey')
    
    # Re-create the foreign key constraint with ON DELETE CASCADE
    op.create_foreign_key(
        'purchase_item_nfe_matches_purchase_item_id_fkey',
        'purchase_item_nfe_matches',
        'purchase_items',
        ['purchase_item_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Drop the cascade foreign key constraint
    op.drop_constraint('purchase_item_nfe_matches_purchase_item_id_fkey', 'purchase_item_nfe_matches', type_='foreignkey')
    
    # Re-create the original foreign key constraint without CASCADE
    op.create_foreign_key(
        'purchase_item_nfe_matches_purchase_item_id_fkey',
        'purchase_item_nfe_matches',
        'purchase_items',
        ['purchase_item_id'],
        ['id']
    )
