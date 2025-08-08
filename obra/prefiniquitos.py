from flask import Blueprint, render_template
from models import Contrato, Prefiniquito, DetallePrefiniquito

prefiniquitos_bp = Blueprint('prefiniquitos', __name__, url_prefix='/prefiniquitos')

# ---------- Historial de Prefiniquitos ----------
@prefiniquitos_bp.route('/<int:contrato_id>')
def historial_prefiniquitos(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    prefiniquitos = Prefiniquito.query \
        .filter_by(contrato_id=contrato.id) \
        .order_by(Prefiniquito.fecha_generacion.desc()) \
        .all()

    return render_template(
        'obra/historial_prefiniquitos.html',
        contrato_id=contrato.id,
        prefiniquitos=prefiniquitos
    )

# ---------- Detalle del Prefiniquito ----------
@prefiniquitos_bp.route('/detalle/<int:prefiniquito_id>')
def detalle_prefiniquito(prefiniquito_id):
    prefiniquito = Prefiniquito.query.get_or_404(prefiniquito_id)
    contrato = prefiniquito.contrato
    detalles = prefiniquito.detalles

    return render_template(
        'obra/prefiniquito_detalle.html',
        contrato=contrato,
        prefiniquito=prefiniquito,
        detalles=detalles
    )
