"""add_maintenance_app

Revision ID: 2e274bd05eea
Revises: 1a18759fdad4
Create Date: 2013-11-22 09:39:03.935677

"""

# revision identifiers, used by Alembic.
revision = '2e274bd05eea'
down_revision = '1a18759fdad4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('app', sa.Column('maintenance', sa.Integer))

def downgrade():
    op.drop_column('app', 'maintenance')


