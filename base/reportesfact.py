from flask import Blueprint, render_template, request, redirect, url_for
from models import Factura, Contrato, Centro, Empresa

reportesfact_bp = Blueprint('reportesfact', __name__, template_folder='../templates')


# ---------- Reporte general de facturas ----------
@reportesfact_bp.route('/reporte_facturas', methods=['GET', 'POST'])
def reporte_facturas():
    estados = ['Pendiente', 'Pagada', 'Cancelada']
    centros = Centro.query.all()
    empresas = Empresa.query.all()

    estado_filtro = request.form.get('estado') if request.method == 'POST' else None
    centro_id = request.form.get('centro_id', type=int) if request.method == 'POST' else None

    datos_por_empresa = []

    for empresa in empresas:
        query = Factura.query.join(Contrato).filter(Factura.empresa_id == empresa.id)

        if estado_filtro:
            query = query.filter(Factura.estado == estado_filtro)

        if centro_id:
            query = query.filter(Contrato.centro_id == centro_id)

        facturas = query.order_by(Factura.fecha_emision.desc()).all()

        datos = []
        for factura in facturas:
            total_pagado = sum(p.monto for p in factura.pagos)
            saldo = factura.total - total_pagado
            ultimo_pago = max(factura.pagos, key=lambda p: p.fecha_pago) if factura.pagos else None
            datos.append({
                "factura": factura,
                "total_pagado": total_pagado,
                "saldo": saldo,
                "ultima_parcialidad": ultimo_pago.parcialidad if ultimo_pago else None,
                "fecha_ultimo_pago": ultimo_pago.fecha_pago if ultimo_pago else None
            })

        datos_por_empresa.append({
            "empresa": empresa.nombre,
            "datos": datos
        })

    return render_template(
        'facturacion/reporte_facturas.html',
        datos_por_empresa=datos_por_empresa,
        estados=estados,
        centros=centros,
        estado_filtro=estado_filtro,
        centro_id=centro_id
    )


# ---------- Opciones para reportes de pagos ----------
@reportesfact_bp.route('/reporte_pagos_opciones', methods=['GET', 'POST'])
def reporte_pagos_opciones():
    centros = Centro.query.all()
    empresas = Empresa.query.all()
    facturas = Factura.query.all()

    if request.method == 'POST':
        opcion = request.form['opcion']

        empresa_id_raw = request.form.get('empresa_id')
        empresa_id = int(empresa_id_raw) if empresa_id_raw and empresa_id_raw.isdigit() else None

        if opcion == 'todas':
            return redirect(url_for('reportesfact.reporte_pagos_todas', empresa_id=empresa_id))
        elif opcion == 'pagadas':
            return redirect(url_for('reportesfact.reporte_pagos_pagadas', empresa_id=empresa_id))
        elif opcion == 'pendientes':
            return redirect(url_for('reportesfact.reporte_pagos_pendientes', empresa_id=empresa_id))
        elif opcion == 'por_centro':
            centro_id = request.form['centro_id']
            return redirect(url_for('reportesfact.reporte_pagos_centro', centro_id=centro_id, empresa_id=empresa_id))
        elif opcion == 'una':
            factura_id = request.form['factura_id']
            return redirect(url_for('reportesfact.reporte_pagos_factura', factura_id=factura_id))

    return render_template(
        'facturacion/reporte_pagos_opciones.html',
        centros=centros,
        empresas=empresas,
        facturas=facturas
    )
# ---------- Reporte de todas las facturas con pagos ----------
@reportesfact_bp.route('/reporte_pagos_todas')
def reporte_pagos_todas():
    empresa_id = request.args.get('empresa_id', type=int)

    query = Factura.query
    if empresa_id:
        query = query.filter(Factura.empresa_id == empresa_id)

    facturas = query.all()

    return render_template(
        'facturacion/reporte_pagos_resultado.html',
        datos_por_empresa=agrupar_datos_por_empresa(facturas),
        titulo="Todas las facturas"
    )

# ---------- Función auxiliar para agrupar datos por empresa ----------
def agrupar_datos_por_empresa(facturas):
    datos_por_empresa = {}

    for factura in facturas:
        empresa = factura.empresa.nombre if factura.empresa else "Sin Empresa"
        if empresa not in datos_por_empresa:
            datos_por_empresa[empresa] = []

        total_pagado = sum(p.monto for p in factura.pagos)
        saldo = factura.total - total_pagado
        datos_por_empresa[empresa].append({
            'factura': factura,
            'pagos': factura.pagos,
            'total_pagado': total_pagado,
            'saldo': saldo
        })

    return [{'empresa': empresa, 'datos': datos} for empresa, datos in datos_por_empresa.items()]

# ---------- Reporte de facturas pagadas ----------
@reportesfact_bp.route('/reporte_pagos_pagadas')
def reporte_pagos_pagadas():
    empresa_id = request.args.get('empresa_id', type=int)

    query = Factura.query.filter(Factura.estado == 'Pagada')
    if empresa_id:
        query = query.filter(Factura.empresa_id == empresa_id)

    facturas = query.all()

    return render_template(
        'facturacion/reporte_pagos_resultado.html',
        datos_por_empresa=agrupar_datos_por_empresa(facturas),
        titulo="Facturas Pagadas"
    )

# ---------- Reporte de facturas pendientes ----------
@reportesfact_bp.route('/reporte_pagos_pendientes')
def reporte_pagos_pendientes():
    empresa_id = request.args.get('empresa_id', type=int)

    query = Factura.query.filter(Factura.estado == 'Pendiente')
    if empresa_id:
        query = query.filter(Factura.empresa_id == empresa_id)

    facturas = query.all()

    return render_template(
        'facturacion/reporte_pagos_resultado.html',
        datos_por_empresa=agrupar_datos_por_empresa(facturas),
        titulo="Facturas Pendientes"
    )

# ---------- Reporte de pagos por centro ----------
@reportesfact_bp.route('/reporte_pagos_centro/<int:centro_id>')
def reporte_pagos_centro(centro_id):
    empresa_id = request.args.get('empresa_id', type=int)
    centro = Centro.query.get_or_404(centro_id)

    query = Factura.query.join(Contrato).filter(Contrato.centro_id == centro_id)
    if empresa_id:
        query = query.filter(Factura.empresa_id == empresa_id)

    facturas = query.all()
    titulo = f"Facturas del Centro: {centro.codigo_centro}"

    return render_template(
        'facturacion/reporte_pagos_resultado.html',
        datos_por_empresa=agrupar_datos_por_empresa(facturas),
        titulo=titulo
    )

# ---------- Reporte de pagos de una sola factura ----------
@reportesfact_bp.route('/reporte_pagos_factura/<int:factura_id>')
def reporte_pagos_factura(factura_id):
    factura = Factura.query.get_or_404(factura_id)

    total_pagado = sum(p.monto for p in factura.pagos)
    saldo = factura.total - total_pagado

    datos_por_empresa = [{
        "empresa": factura.empresa.nombre if factura.empresa else "Sin Empresa",
        "datos": [{
            "factura": factura,
            "pagos": factura.pagos,
            "total_pagado": total_pagado,
            "saldo": saldo
        }]
    }]

    return render_template(
        'facturacion/reporte_pagos_resultado.html',
        datos_por_empresa=datos_por_empresa,
        titulo=f"Factura #{factura.numero_factura}"
    )
# ---------- Historial de pagos de una factura ----------
@reportesfact_bp.route('/historial_factura/<int:factura_id>')
def historial_factura(factura_id):
    factura = Factura.query.get_or_404(factura_id)
    pagos = sorted(factura.pagos, key=lambda p: p.fecha_pago)

    historial = []
    saldo_actual = factura.total
    for pago in pagos:
        saldo_actual -= pago.monto
        historial.append({
            'fecha': pago.fecha_pago,
            'monto': pago.monto,
            'metodo': pago.metodo_pago,
            'referencia': pago.referencia,
            'parcialidad': pago.parcialidad,
            'saldo_pendiente': max(saldo_actual, 0)
        })

    return render_template(
        'facturacion/historial_factura.html',
        factura=factura,
        historial=historial,
        saldo_final=max(saldo_actual, 0)
    )