"""Renombrar contenido a conceptos_json en CatalogoBaseAcumulado

Revision ID: b0b331c32bfb
Revises: 92741f160250
Create Date: 2025-06-09 12:00:06.812868
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# Identificadores de revisión
revision = 'b0b331c32bfb'
down_revision = '92741f160250'
branch_labels = None
depends_on = None

def upgrade():
    # Verificar si la columna ya existe (evita errores por duplicado)
    conn = op.get_bind()
    result = conn.execute(text("PRAGMA table_info(catalogo_base_acumulado);"))
    columns = [row[1] for row in result]

    if 'conceptos_json' not in columns:
        with op.batch_alter_table('catalogo_base_acumulado') as batch_op:
            batch_op.add_column(sa.Column('conceptos_json', sa.Text(), nullable=True))

    op.execute(text("""
        UPDATE catalogo_base_acumulado
        SET conceptos_json = COALESCE(contenido, '[]')
    """))

    with op.batch_alter_table('catalogo_base_acumulado') as batch_op:
        if 'contenido' in columns:
            batch_op.drop_column('contenido')
        batch_op.alter_column('conceptos_json', nullable=False)

def downgrade():
    with op.batch_alter_table('catalogo_base_acumulado') as batch_op:
        batch_op.add_column(sa.Column('contenido', sa.Text(), nullable=True))
        batch_op.drop_column('conceptos_json')