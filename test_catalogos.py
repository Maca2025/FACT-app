from app import app
from models import CatalogoVersion, ConceptoCatalogo

with app.app_context():
    version_original = CatalogoVersion.query.get(1)
    version_actualizada = CatalogoVersion.query.get(2)

    print(f"\n✅ Catalogo Original: {version_original}")
    print(f"Conceptos encontrados en original: {ConceptoCatalogo.query.filter_by(version_id=1).count()}")

    print(f"\n✅ Catalogo Actualizado: {version_actualizada}")
    print(f"Conceptos encontrados en actualizado: {ConceptoCatalogo.query.filter_by(version_id=2).count()}")