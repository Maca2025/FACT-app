from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Contrato, Cliente, Centro, Empresa

contratos_bp = Blueprint('contratos', __name__, template_folder='../templates')

@contratos_bp.route('/contratos', methods=['GET', 'POST'])
def contratos():
    clientes = Cliente.query.all()
    centros = Centro.query.all()
    empresas = Empresa.query.all()

    if request.method == 'POST':
        monto_sin_iva = float(request.form['monto_sin_iva'] or 0)
        iva = float(request.form['iva']) if request.form['iva'] else round(monto_sin_iva * 0.16, 2)
        monto_total = float(request.form['monto_total']) if request.form['monto_total'] else round(monto_sin_iva + iva, 2)
        porcentaje_anticipo = float(request.form['porcentaje_anticipo'] or 0)
        anticipo_total = round(monto_total * (porcentaje_anticipo / 100), 2)

        nuevo_contrato = Contrato(
            nombre=request.form['nombre'],
            contrato=request.form['contrato'],
            descripcion=request.form['descripcion'],
            cliente_id=int(request.form['cliente_id']),
            centro_id=int(request.form['centro_id']),
            empresa_id=int(request.form['empresa_id']),
            monto_sin_iva=monto_sin_iva,
            iva=iva,
            monto_total=monto_total,
            porcentaje_anticipo=porcentaje_anticipo,
            anticipo_total=anticipo_total,
            duracion=int(request.form['duracion'] or 0)
        )
        db.session.add(nuevo_contrato)
        db.session.commit()
        return redirect(url_for('contratos.contratos'))

    contratos_por_empresa = []
    for empresa in empresas:
        contratos = Contrato.query.filter_by(empresa_id=empresa.id).all()
        contratos_por_empresa.append({
            'empresa': empresa.nombre,
            'contratos': contratos
        })

    return render_template(
        'facturacion/contratos.html',
        contratos_por_empresa=contratos_por_empresa,
        clientes=clientes,
        centros=centros,
        empresas=empresas
    )