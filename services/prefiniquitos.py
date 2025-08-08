from datetime import date
from models import db, Contrato, Prefiniquito, DetallePrefiniquito, ConceptoCatalogo, CatalogoVersion
from sqlalchemy.orm import joinedload

def generar_prefiniquito(contrato_id, version_original_id, version_actualizada_id):
    contrato = Contrato.query.get(contrato_id)
    if not contrato:
        raise ValueError("Contrato no encontrado")

    original = CatalogoVersion.query.options(joinedload(CatalogoVersion.conceptos)).get(version_original_id)
    actualizada = CatalogoVersion.query.options(joinedload(CatalogoVersion.conceptos)).get(version_actualizada_id)

    conceptos_original = {c.clave_concepto: c for c in original.conceptos}
    conceptos_actualizados = {c.clave_concepto: c for c in actualizada.conceptos}

    nuevo = Prefiniquito(
        contrato_id=contrato_id,
        version_original_id=version_original_id,
        version_actualizada_id=version_actualizada_id,
        fecha_generacion=date.today(),
        total_original=0,
        total_actualizado=0,
        diferencia_total=0
    )
    db.session.add(nuevo)
    db.session.flush()

    total_original = 0
    total_actualizado = 0

    claves_combinadas = set(conceptos_original.keys()) | set(conceptos_actualizados.keys())

    for clave in sorted(claves_combinadas):
        print(f"🛠 Procesando concepto: {clave}")  # 👈 Línea añadida para depuración

        orig = conceptos_original.get(clave)
        act = conceptos_actualizados.get(clave)

        precio_unitario_original = orig.precio_unitario if orig else 0
        cantidad_original = orig.cantidad if orig else 0
        subtotal_original = orig.subtotal if orig else 0

        precio_unitario_actualizado = act.precio_unitario if act else 0
        cantidad_actualizada = act.cantidad if act else 0
        subtotal_actualizado = act.subtotal if act else 0

        total_original += subtotal_original
        total_actualizado += subtotal_actualizado

        diferencia_cantidad = cantidad_actualizada - cantidad_original
        diferencia_subtotal = subtotal_actualizado - subtotal_original

        if orig and act:
            tipo_cambio = 'modificado' if (
                precio_unitario_original != precio_unitario_actualizado or
                cantidad_original != cantidad_actualizada
            ) else 'sin cambio'
        elif act and not orig:
            tipo_cambio = 'nuevo'
        else:
            tipo_cambio = 'sin cambio'

        detalle = DetallePrefiniquito(
            prefiniquito_id=nuevo.id,
            concepto_id=act.id if act else (orig.id if orig else None),
            partida=act.partida if act else (orig.partida if orig else ''),
            nombre_partida=act.nombre_partida if act else (orig.nombre_partida if orig else ''),
            clave_concepto=clave,
            descripcion=act.descripcion if act else (orig.descripcion if orig else ''),
            unidad=act.unidad if act else (orig.unidad if orig else ''),
            precio_unitario_original=precio_unitario_original,
            cantidad_original=cantidad_original,
            subtotal_original=subtotal_original,
            precio_unitario_actualizado=precio_unitario_actualizado,
            cantidad_actualizada=cantidad_actualizada,
            subtotal_actualizado=subtotal_actualizado,
            diferencia_cantidad=diferencia_cantidad,
            diferencia_subtotal=diferencia_subtotal,
            tipo_cambio=tipo_cambio
        )
        db.session.add(detalle)

    nuevo.total_original = total_original
    nuevo.total_actualizado = total_actualizado
    nuevo.diferencia_total = total_actualizado - total_original

    db.session.commit()
    return nuevo.id