from models import ConceptoCatalogo, db
from sqlalchemy import and_

def actualizar_estatus_revision():
    """
    Revisa todos los conceptos extraordinarios con estatus 'R' y les asigna un sufijo numérico
    como R1, R2, R3... según su orden dentro del contrato (por clave_concepto).
    """
    conceptos = ConceptoCatalogo.query.filter(ConceptoCatalogo.estatus.like("R%")).order_by(ConceptoCatalogo.clave_concepto.asc(), ConceptoCatalogo.id.asc()).all()

    conteo_por_clave = {}

    for concepto in conceptos:
        clave = concepto.clave_concepto

        if clave not in conteo_por_clave:
            conteo_por_clave[clave] = 1
        else:
            conteo_por_clave[clave] += 1

        nuevo_estatus = f"R{conteo_por_clave[clave]}"
        concepto.estatus = nuevo_estatus

    db.session.commit()
    print("✅ Estatus actualizados correctamente.")