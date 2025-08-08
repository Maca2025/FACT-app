"""Agregar clave_concepto a ConceptoCatalogo

Revision ID: 2f0de2e49641
Revises: 651afd408196
Create Date: 2025-05-26 16:16:33.447975

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f0de2e49641'
down_revision = '651afd408196'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columna directamente sin usar batch_alter_table
    op.add_column('concepto_catalogo', sa.Column('clave_concepto', sa.String(length=50), nullable=True))


def downgrade():
    # Eliminar la columna directamente
    op.drop_column('concepto_catalogo', 'clave_concepto')