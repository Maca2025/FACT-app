from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Pago, Factura
from datetime import date

pagos_bp = Blueprint('pagos', __name__, template_folder='../templates')

@pagos_bp.route('/pagos', methods=['GET', 'POST'])
def pagos():
    facturas = Factura.query.all()

    if request.method == 'POST':
        pagos_previos = Pago.query.filter_by(factura_id=request.form['factura_id']).count()
        parcialidad = pagos_previos + 1

        nuevo_pago = Pago(
            factura_id=request.form['factura_id'],
            fecha_pago=date.fromisoformat(request.form['fecha_pago']),
            monto=float(request.form['monto']),
            metodo_pago=request.form.get('metodo_pago', ''),
            referencia=request.form['referencia'],
            parcialidad=parcialidad
        )
        db.session.add(nuevo_pago)
        db.session.commit()
        return redirect(url_for('pagos.pagos'))

    pagos = Pago.query.all()
    return render_template('facturacion/pagos.html', pagos=pagos, facturas=facturas)