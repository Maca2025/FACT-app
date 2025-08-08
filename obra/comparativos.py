from flask import Blueprint, render_template
from models import Contrato, Prefiniquito, DetalleAvance, AvanceObra, ConceptoCatalogo
from collections import defaultdict

comparativos_bp = Blueprint('comparativos', __name__, template_folder='../templates')


@comparativos_bp.route('/comparativo_prefiniquito_avances/<int:contrato_id>')
def comparativo_prefiniquito_avances(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    prefiniquito = Prefiniquito.query \
        .filter_by(contrato_id=contrato_id) \
        .order_by(Prefiniquito.id.desc()) \
        .first()

    if not prefiniquito:
        return render_template('obra/comparativo_prefiniquito_avances.html',
                               contrato=contrato,
                               filas_por_partida={},
                               totales_por_partida={},
                               subtotales_generales={},
                               monto_original_contrato=0,
                               diferencia_total=0)

    avances = DetalleAvance.query \
        .join(AvanceObra) \
        .filter(AvanceObra.contrato_id == contrato_id) \
        .all()

    avance_dict = defaultdict(float)

    for a in avances:
        if a.concepto:
            clave = a.concepto.clave_concepto
            avance_dict[clave] += a.cantidad_avance or 0

    filas_por_partida = defaultdict(list)
    totales_por_partida = defaultdict(lambda: {
        'catalogo': 0,
        'avance': 0,
        'pendiente': 0
    })

    subtotal_general_catalogo = 0
    subtotal_general_avance = 0
    subtotal_general_pendiente = 0

    for d in prefiniquito.detalles:
        clave = d.clave_concepto
        partida = d.nombre_partida or 'Sin Partida'
        precio_unitario = d.precio_unitario_actualizado or 0
        cantidad_catalogo = d.cantidad_actualizada or 0
        cantidad_avance = avance_dict.get(clave, 0)
        cantidad_pendiente = cantidad_catalogo - cantidad_avance

        subtotal_catalogo = cantidad_catalogo * precio_unitario
        subtotal_avance = cantidad_avance * precio_unitario
        subtotal_pendiente = cantidad_pendiente * precio_unitario

        concepto = ConceptoCatalogo.query.filter_by(clave_concepto=clave).order_by(ConceptoCatalogo.id.desc()).first()
        estatus = concepto.estatus if concepto else ''

        fila = {
            'clave': clave,
            'descripcion': d.descripcion,
            'unidad': d.unidad,
            'precio_unitario': precio_unitario,
            'cantidad_catalogo': cantidad_catalogo,
            'cantidad_avance': cantidad_avance,
            'cantidad_pendiente': cantidad_pendiente,
            'subtotal_catalogo': subtotal_catalogo,
            'subtotal_avance': subtotal_avance,
            'subtotal_pendiente': subtotal_pendiente,
            'estatus': estatus
        }

        filas_por_partida[partida].append(fila)

        totales_por_partida[partida]['catalogo'] += subtotal_catalogo
        totales_por_partida[partida]['avance'] += subtotal_avance
        totales_por_partida[partida]['pendiente'] += subtotal_pendiente

        subtotal_general_catalogo += subtotal_catalogo
        subtotal_general_avance += subtotal_avance
        subtotal_general_pendiente += subtotal_pendiente

    subtotales_generales = {
        'catalogo': subtotal_general_catalogo,
        'avance': subtotal_general_avance,
        'pendiente': subtotal_general_pendiente,
        'iva_catalogo': subtotal_general_catalogo * 0.16,
        'iva_avance': subtotal_general_avance * 0.16,
        'iva_pendiente': subtotal_general_pendiente * 0.16,
        'total_catalogo': subtotal_general_catalogo * 1.16,
        'total_avance': subtotal_general_avance * 1.16,
        'total_pendiente': subtotal_general_pendiente * 1.16
    }

    # ✅ Obtener monto original del contrato desde el objeto prefiniquito
    monto_original_contrato = sum(
        (d.cantidad_original or 0) * (d.precio_unitario_original or 0)
        for d in prefiniquito.detalles
        if not d.clave_concepto.startswith('E')
    )

    diferencia_total = monto_original_contrato - subtotal_general_catalogo

    return render_template('obra/comparativo_prefiniquito_avances.html',
                           contrato=contrato,
                           filas_por_partida=filas_por_partida,
                           totales_por_partida=totales_por_partida,
                           subtotales_generales=subtotales_generales,
                           monto_original_contrato=monto_original_contrato,
                           diferencia_total=diferencia_total)