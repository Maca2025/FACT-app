from models import CatalogoVersion, CatalogoBaseAcumulado, db
from sqlalchemy.orm import joinedload
from datetime import date
import hashlib
import json

# ===============================
# Generar catálogo base acumulado
# ===============================
def generar_catalogo_base(contrato_id):
    """
    Combina el catálogo original y todos los actualizados para formar un catálogo base consolidado,
    útil como referencia para avances o comparativos.
    Se incluye la versión más reciente de cada concepto, pero si un extraordinario ya fue aprobado ('A'),
    no se sobrescribe con una versión posterior en estado 'E' o 'R'.
    """
    versiones = CatalogoVersion.query.options(joinedload(CatalogoVersion.conceptos)) \
        .filter_by(contrato_id=contrato_id).order_by(CatalogoVersion.id.asc()).all()

    if not versiones:
        return []

    conceptos_base = {}

    for version in versiones:
        for c in version.conceptos:
            clave = c.clave_concepto
            estatus = getattr(c, 'estatus', 'A')  # Default a 'A' si no está definido

            if not clave:
                continue

            if clave not in conceptos_base:
                conceptos_base[clave] = {
                    'id': c.id,
                    'partida': c.partida,
                    'nombre_partida': c.nombre_partida,
                    'clave': clave,
                    'concepto': c.concepto,
                    'descripcion': c.descripcion,
                    'unidad': c.unidad,
                    'precio_unitario': c.precio_unitario,
                    'cantidad': c.cantidad,
                    'subtotal': c.cantidad * c.precio_unitario,
                    'estatus': estatus
                }
            else:
                # Si es extraordinario ya aprobado, no sobrescribir con estado E o R
                if clave.startswith('E'):
                    if conceptos_base[clave]['estatus'] == 'A' and estatus in ['E', 'R']:
                        continue  # mantenemos la versión aprobada

                # Si no está aprobado o no es extraordinario, sobrescribimos
                conceptos_base[clave] = {
                    'id': c.id,
                    'partida': c.partida,
                    'nombre_partida': c.nombre_partida,
                    'clave': clave,
                    'concepto': c.concepto,
                    'descripcion': c.descripcion,
                    'unidad': c.unidad,
                    'precio_unitario': c.precio_unitario,
                    'cantidad': c.cantidad,
                    'subtotal': c.cantidad * c.precio_unitario,
                    'estatus': estatus
                }

    return list(conceptos_base.values())


# ============================================
# Guardar nueva versión del Catálogo Base Acumulado (si cambia el contenido)
# ============================================
def guardar_catalogo_base_si_nuevo(contrato_id, forzar=False):
    """
    Guarda una nueva versión del Catálogo Base Acumulado si su contenido es diferente
    al de la última versión registrada para el contrato dado.
    Si `forzar=True`, guarda la versión aunque no haya diferencias.
    """
    conceptos = generar_catalogo_base(contrato_id)

    if not conceptos:
        return None

    contenido_json = json.dumps(sorted(conceptos, key=lambda c: c['clave']), sort_keys=True)
    hash_actual = hashlib.sha256(contenido_json.encode('utf-8')).hexdigest()

    ultima_version = CatalogoBaseAcumulado.query.filter_by(contrato_id=contrato_id) \
        .order_by(CatalogoBaseAcumulado.version.desc()).first()

    if not forzar and ultima_version and ultima_version.hash_contenido == hash_actual:
        return ultima_version

    nueva_version = (ultima_version.version + 1) if ultima_version else 1

    nuevo_catalogo = CatalogoBaseAcumulado(
        contrato_id=contrato_id,
        version=nueva_version,
        hash_contenido=hash_actual,
        conceptos_json=contenido_json
    )
    db.session.add(nuevo_catalogo)
    db.session.commit()

    return nuevo_catalogo