# ver_claves.py

from app import app
from models import CatalogoVersion

with app.app_context():
    original = CatalogoVersion.query.get(1)
    actualizada = CatalogoVersion.query.get(2)

    print("\n📘 CATÁLOGO ORIGINAL:")
    for c in original.conceptos:
        print(f"ID: {c.id} | Clave: {c.clave_concepto} | Descripción: {c.descripcion}")

    print("\n📗 CATÁLOGO ACTUALIZADO:")
    for c in actualizada.conceptos:
        print(f"ID: {c.id} | Clave: {c.clave_concepto} | Descripción: {c.descripcion}")