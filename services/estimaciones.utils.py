from models import CatalogoVersion, ConceptoCatalogo
from sqlalchemy import func
from models import db

def obtener_importes_originales_por_partida(contrato_id):
    """
    Devuelve un diccionario con los importes del contrato original agrupados por partida.
    """
    version_original = CatalogoVersion.query.filter_by(
        contrato_id=contrato_id,
        tipo='original'
    ).first()

    if not version_original:
        return {}

    resultados = db.session.query(
        ConceptoCatalogo.nombre_partida,
        func.sum(ConceptoCatalogo.subtotal).label('importe_original')
    ).filter(
        ConceptoCatalogo.version_id == version_original.id
    ).group_by(
        ConceptoCatalogo.nombre_partida
    ).all()

    return {r.nombre_partida: r.importe_original for r in resultados}

from models import DetalleEstimacion

def obtener_importes_estimacion_actual_por_partida(estimacion_id):
    """
    Devuelve un diccionario con los importes de la estimación actual agrupados por partida.
    """
    detalles = db.session.query(
        DetalleEstimacion.nombre_partida,
        func.sum(DetalleEstimacion.subtotal).label('importe_actual')
    ).filter_by(
        estimacion_id=estimacion_id
    ).group_by(
        DetalleEstimacion.nombre_partida
    ).all()

    return {r.nombre_partida: r.importe_actual for r in detalles}

def obtener_totales_contrato_y_anticipo(contrato_id, porcentaje_anticipo):
    """
    Devuelve los importes totales del contrato original y del anticipo.
    """
    version_original = CatalogoVersion.query.filter_by(
        contrato_id=contrato_id,
        tipo='original'
    ).first()

    if not version_original:
        return {
            'subtotal': 0.0,
            'iva': 0.0,
            'total': 0.0,
            'anticipo_subtotal': 0.0,
            'anticipo_iva': 0.0,
            'anticipo_total': 0.0
        }

    subtotal = db.session.query(func.sum(ConceptoCatalogo.subtotal)).filter(
        ConceptoCatalogo.version_id == version_original.id
    ).scalar() or 0.0

    iva = round(subtotal * 0.16, 2)
    total = subtotal + iva

    anticipo_subtotal = round(subtotal * (porcentaje_anticipo / 100), 2)
    anticipo_iva = round(anticipo_subtotal * 0.16, 2)
    anticipo_total = anticipo_subtotal + anticipo_iva

    return {
        'subtotal': subtotal,
        'iva': iva,
        'total': total,
        'anticipo_subtotal': anticipo_subtotal,
        'anticipo_iva': anticipo_iva,
        'anticipo_total': anticipo_total
    }