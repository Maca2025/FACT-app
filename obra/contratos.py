from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Contrato, Cliente, Centro, Empresa, Prefiniquito, DeduccionContrato
from datetime import datetime, timedelta
from services.catalogo_base import generar_catalogo_base  # ✅ se agrega para obtener conceptos base

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

    porcentaje = (contrato.porcentaje_anticipo or 0) / 100
    monto_total = contrato.monto_total or 0

    subtotal = monto_total / 1.16
    iva = monto_total - subtotal

    anticipo_sin_iva = subtotal * porcentaje
    iva_anticipo = anticipo_sin_iva * 0.16
    total_anticipo = anticipo_sin_iva + iva_anticipo

    totales = {
        'subtotal_contrato': subtotal,
        'iva_contrato': iva,
        'total_contrato': monto_total,
        'anticipo_sin_iva': anticipo_sin_iva,
        'iva_anticipo': iva_anticipo,
        'total_anticipo': total_anticipo,
    }

    prefiniquito = Prefiniquito.query.filter_by(contrato_id=contrato.id).order_by(Prefiniquito.id.desc()).first()

    return render_template('obra/panel_contrato.html', contrato=contrato, totales=totales, prefiniquito=prefiniquito)


@contratos_obra_bp.route('/registrar_contrato', methods=['GET', 'POST'])
def registrar_contrato():
    if request.method == 'POST':
        nuevo = Contrato(
            nombre=request.form['nombre'],
            contrato=request.form['contrato'],
            descripcion=request.form['descripcion'],
            cliente_id=request.form['cliente_id'],
            centro_id=request.form['centro_id'],
            empresa_id=request.form['empresa_id'],
            porcentaje_anticipo=request.form.get('porcentaje_anticipo') or 0.0
        )

        try:
            nuevo.fecha_inicio = datetime.strptime(request.form['fecha_inicio'], '%Y-%m-%d').date()
        except:
            nuevo.fecha_inicio = None

        try:
            nuevo.duracion = int(request.form.get('duracion') or 0)
        except:
            nuevo.duracion = None

        if nuevo.fecha_inicio and nuevo.duracion:
            nuevo.fecha_fin = nuevo.fecha_inicio + timedelta(days=nuevo.duracion)

        try:
            nuevo.monto_sin_iva = float(request.form['monto_sin_iva'])
            nuevo.iva = float(request.form['iva'])
            nuevo.monto_total = float(request.form['monto_total'])
        except:
            pass

        # Calcular y guardar anticipos una sola vez
        if nuevo.monto_sin_iva is not None and nuevo.porcentaje_anticipo is not None:
         nuevo.anticipo_sin_iva = round(nuevo.monto_sin_iva * (nuevo.porcentaje_anticipo / 100), 2)
         nuevo.iva_anticipo = round(nuevo.anticipo_sin_iva * 0.16, 2)
         nuevo.total_anticipo = round(nuevo.anticipo_sin_iva + nuevo.iva_anticipo, 2)
        else:
         nuevo.anticipo_sin_iva = None
         nuevo.iva_anticipo = None
         nuevo.total_anticipo = None

        db.session.add(nuevo)
        db.session.flush()

        # Guardar deducciones recurrentes si vienen en el formulario
        nombres = request.form.getlist('deduccion_nombre[]')
        porcentajes = request.form.getlist('deduccion_porcentaje[]')
        for nombre, porcentaje in zip(nombres, porcentajes):
            if nombre.strip():
                try:
                    porcentaje_val = float(porcentaje)
                    db.session.add(DeduccionContrato(
                        contrato_id=nuevo.id,
                        nombre=nombre.strip(),
                        porcentaje=porcentaje_val
                    ))
                except:
                    continue

        db.session.commit()
        return redirect(url_for('contratos_obra.panel_contrato', contrato_id=nuevo.id))

    clientes = Cliente.query.order_by(Cliente.nombre).all()
    centros = Centro.query.order_by(Centro.codigo_centro).all()
    empresas = Empresa.query.order_by(Empresa.nombre).all()

    contratos = Contrato.query.order_by(Contrato.empresa_id, Contrato.nombre).all()
    contratos_por_empresa = {}
    for c in contratos:
        empresa_nombre = c.empresa.nombre
        contratos_por_empresa.setdefault(empresa_nombre, []).append(c)

    return render_template(
        'obra/contratos.html',
        contrato=None,
        clientes=clientes,
        centros=centros,
        empresas=empresas,
        contratos_por_empresa=[{'empresa': k, 'contratos': v} for k, v in contratos_por_empresa.items()]
    )


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


   # Recalcular anticipos si se modifica el contrato
        if contrato.monto_sin_iva is not None and contrato.porcentaje_anticipo is not None:
         contrato.anticipo_sin_iva = round(contrato.monto_sin_iva * (contrato.porcentaje_anticipo / 100), 2)
         contrato.iva_anticipo = round(contrato.anticipo_sin_iva * 0.16, 2)
         contrato.total_anticipo = round(contrato.anticipo_sin_iva + contrato.iva_anticipo, 2)
        else:
         contrato.anticipo_sin_iva = None
         contrato.iva_anticipo = None
         contrato.total_anticipo = None
        db.session.commit()
        return redirect(url_for('contratos_obra.panel_contrato', contrato_id=contrato.id))

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