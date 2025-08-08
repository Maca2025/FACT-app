from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Contrato, Cliente, Centro, Empresa
from datetime import datetime, timedelta

contratos_obra_bp = Blueprint('contratos_obra', __name__, template_folder='../templates')


@contratos_obra_bp.route('/obras_abiertas')
def obras_abiertas():
    contratos = Contrato.query.filter_by(estado='abierto').order_by(Contrato.empresa_id, Contrato.nombre).all()

    contratos_por_empresa = {}
    for contrato in contratos:
        empresa = contrato.empresa.nombre
        if empresa not in contratos_por_empresa:
            contratos_por_empresa[empresa] = []
        contratos_por_empresa[empresa].append(contrato)

    return render_template(
        'obra/lista_contratos.html',
        contratos_por_empresa=contratos_por_empresa,
        titulo="Obras Abiertas"
    )


@contratos_obra_bp.route('/obras_cerradas')
def obras_cerradas():
    contratos = Contrato.query.filter_by(estado='cerrado').order_by(Contrato.empresa_id, Contrato.nombre).all()

    contratos_por_empresa = {}
    for contrato in contratos:
        empresa = contrato.empresa.nombre
        if empresa not in contratos_por_empresa:
            contratos_por_empresa[empresa] = []
        contratos_por_empresa[empresa].append(contrato)

    return render_template(
        'obra/lista_contratos.html',
        contratos_por_empresa=contratos_por_empresa,
        titulo="Obras Cerradas"
    )


@contratos_obra_bp.route('/cerrar_contrato/<int:contrato_id>', methods=['POST'])
def cerrar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    contrato.estado = 'cerrado'
    db.session.commit()
    return redirect(request.referrer or url_for('contratos_obra.obras_abiertas'))


@contratos_obra_bp.route('/abrir_contrato/<int:contrato_id>', methods=['POST'])
def abrir_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    contrato.estado = 'abierto'
    db.session.commit()
    return redirect(request.referrer or url_for('contratos_obra.obras_cerradas'))


@contratos_obra_bp.route('/panel_contrato/<int:contrato_id>')
def panel_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    subtotal_contrato = contrato.monto_sin_iva or 0
    total_contrato = contrato.monto_total or 0
    iva_contrato = total_contrato - subtotal_contrato

    porcentaje = contrato.porcentaje_anticipo or 0
    anticipo_sin_iva = subtotal_contrato * (porcentaje / 100)
    iva_anticipo = iva_contrato * (porcentaje / 100)
    total_anticipo = anticipo_sin_iva + iva_anticipo

    totales = {
        'subtotal_contrato': subtotal_contrato,
        'iva_contrato': iva_contrato,
        'total_contrato': total_contrato,
        'anticipo_sin_iva': anticipo_sin_iva,
        'iva_anticipo': iva_anticipo,
        'total_anticipo': total_anticipo
    }

    return render_template('obra/panel_contrato.html', contrato=contrato, totales=totales)


@contratos_obra_bp.route('/editar/<int:contrato_id>', methods=['GET', 'POST'])
def editar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    if request.method == 'POST':
        contrato.nombre = request.form.get('nombre', contrato.nombre)
        contrato.contrato = request.form.get('contrato', contrato.contrato)
        contrato.descripcion = request.form.get('descripcion', contrato.descripcion)
        contrato.cliente_id = int(request.form.get('cliente_id', contrato.cliente_id))
        contrato.centro_id = int(request.form.get('centro_id', contrato.centro_id))
        contrato.empresa_id = int(request.form.get('empresa_id', contrato.empresa_id))

        fecha_inicio_str = request.form.get('fecha_inicio')
        if fecha_inicio_str:
            contrato.fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        else:
            contrato.fecha_inicio = None

        duracion_str = request.form.get('duracion')
        try:
            contrato.duracion = int(duracion_str) if duracion_str else None
        except ValueError:
            contrato.duracion = None

        if contrato.fecha_inicio and contrato.duracion is not None:
            contrato.fecha_fin = contrato.fecha_inicio + timedelta(days=contrato.duracion)
        else:
            contrato.fecha_fin = None

        try:
            contrato.monto_sin_iva = float(request.form.get('monto_sin_iva', contrato.monto_sin_iva or 0))
        except ValueError:
            pass

        try:
            contrato.iva = float(request.form.get('iva', contrato.iva or 0))
        except ValueError:
            pass

        try:
            contrato.monto_total = float(request.form.get('monto_total', contrato.monto_total or 0))
        except ValueError:
            pass

        try:
            contrato.porcentaje_anticipo = float(request.form.get('porcentaje_anticipo', contrato.porcentaje_anticipo or 0))
        except ValueError:
            pass

        db.session.commit()
        return redirect(url_for('contratos_obra.panel_contrato', contrato_id=contrato.id))

    # Para GET
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    centros = Centro.query.order_by(Centro.codigo_centro).all()
    empresas = Empresa.query.order_by(Empresa.nombre).all()

    contratos = Contrato.query.order_by(Contrato.empresa_id, Contrato.nombre).all()
    contratos_por_empresa = {}
    for c in contratos:
        empresa_nombre = c.empresa.nombre
        contratos_por_empresa.setdefault(empresa_nombre, []).append(c)

    return render_template(
        'obra/editar_contrato.html',
        contrato=contrato,
        clientes=clientes,
        centros=centros,
        empresas=empresas,
        contratos_por_empresa=[{'empresa': k, 'contratos': v} for k, v in contratos_por_empresa.items()]
    )
