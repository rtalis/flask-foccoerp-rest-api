"""remove_cascade_delete_from_purchase_item_nfe_matches

Revision ID: 5db6f21eeb2c
Revises: 3d5efbd777e6
Create Date: 2025-12-01 13:26:56.567206

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5db6f21eeb2c'
down_revision = '3d5efbd777e6'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the CASCADE foreign key constraint
    op.drop_constraint('purchase_item_nfe_matches_purchase_item_id_fkey', 'purchase_item_nfe_matches', type_='foreignkey')
    
    # Re-create the foreign key constraint without ON DELETE CASCADE
    op.create_foreign_key(
        'purchase_item_nfe_matches_purchase_item_id_fkey',
        'purchase_item_nfe_matches',
        'purchase_items',
        ['purchase_item_id'],
        ['id']
    )


def downgrade():
    # Drop the regular foreign key constraint
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
