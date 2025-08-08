from flask import Blueprint, render_template, request, redirect, url_for
from models import CatalogoVersion, CatalogoBaseAcumulado, db
from sqlalchemy.orm import joinedload
from datetime import date
import hashlib
import json
from models import Contrato, Estimacion

# Crear blueprint
estimaciones_nuevo_bp = Blueprint('estimaciones_nuevo', __name__, url_prefix='/estimaciones', template_folder='templates')

# ============================================
# Guardar nueva versión del Catálogo Base Acumulado (si cambia el contenido)
# ============================================
def guardar_catalogo_base_si_nuevo(contrato_id, forzar=False):
    from services.catalogo_base import generar_catalogo_base

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

# ============================================
# Crear estimación (pantalla inicial)
# ============================================
from services.catalogo_base import generar_catalogo_base

@estimaciones_nuevo_bp.route('/crear_estimacion/<int:contrato_id>', methods=['GET', 'POST'])
def crear_estimacion(contrato_id):
    conceptos = generar_catalogo_base(contrato_id)

    # Filtrar: ordinarios + extraordinarios con estatus A
    conceptos_filtrados = [
        c for c in conceptos
        if not c['clave'].startswith('E') or c.get('estatus') == 'A'
    ]

    # Agrupar por partida
    conceptos_por_partida = {}
    for c in conceptos_filtrados:
        nombre_partida = c.get('nombre_partida', 'SIN PARTIDA')
        if nombre_partida not in conceptos_por_partida:
            conceptos_por_partida[nombre_partida] = []
        conceptos_por_partida[nombre_partida].append(c)

    # Ordenar conceptos por clave
    for partida in conceptos_por_partida:
        conceptos_por_partida[partida].sort(key=lambda x: x['clave'])

    if request.method == 'POST':
        claves = request.form.getlist('clave[]')
        return redirect(url_for('estimaciones_nuevo.capturar_cantidades', contrato_id=contrato_id, claves=','.join(claves)))

    return render_template(
        'estimaciones_nuevo/seleccionar_conceptos_estim.html',
        contrato_id=contrato_id,
        conceptos_por_partida=conceptos_por_partida
    )

# ============================================
# Capturar cantidades para los conceptos seleccionados
# ============================================
@estimaciones_nuevo_bp.route('/capturar_cantidades')
def capturar_cantidades():
    from services.catalogo_base import generar_catalogo_base

    contrato_id = int(request.args.get('contrato_id'))
    claves_str = request.args.get('claves', '')
    claves = claves_str.split(',')

    todos_conceptos = generar_catalogo_base(contrato_id)
    conceptos_filtrados = [c for c in todos_conceptos if c['clave'] in claves]

    # Ordenar por clave
    conceptos_filtrados.sort(key=lambda x: x['clave'])

    return render_template(
        'estimaciones_nuevo/capturar_cantidades.html',
        contrato={'id': contrato_id},
        conceptos=conceptos_filtrados
    )

# ============================================
# Calcular y mostrar resumen con subtotales, IVA y total
# ============================================
@estimaciones_nuevo_bp.route('/suma_conceptos', methods=['POST'])
def suma_conceptos():
    from services.catalogo_base import generar_catalogo_base

    contrato_id = int(request.args.get('contrato_id'))
    cantidades = request.form.to_dict()
    claves = request.form.getlist('clave[]')

    # Obtener conceptos del catálogo base
    conceptos_base = generar_catalogo_base(contrato_id)
    conceptos_dict = {c['clave']: c for c in conceptos_base if c['clave'] in claves}

    conceptos_por_partida = {}
    subtotales_por_partida = {}

    for clave in claves:
        concepto = conceptos_dict.get(clave)
        if not concepto:
            continue

        cantidad_str = cantidades.get(f"cantidad_{clave}", "0")
        try:
            cantidad = float(cantidad_str)
        except ValueError:
            cantidad = 0.0

        concepto['cantidad_estimacion'] = cantidad
        concepto['subtotal_estimacion'] = cantidad * concepto['precio_unitario']

        partida = concepto.get('nombre_partida', 'SIN PARTIDA')
        if partida not in conceptos_por_partida:
            conceptos_por_partida[partida] = []
            subtotales_por_partida[partida] = 0

        conceptos_por_partida[partida].append(concepto)
        subtotales_por_partida[partida] += concepto['subtotal_estimacion']

    subtotal_general = sum(subtotales_por_partida.values())
    iva = subtotal_general * 0.16
    total_con_iva = subtotal_general + iva

    return render_template(
        'estimaciones_nuevo/suma_conceptos.html',
        contrato_id=contrato_id,
        conceptos_por_partida=conceptos_por_partida,
        subtotales_por_partida=subtotales_por_partida,
        subtotal_general=subtotal_general,
        iva=iva,
        total_con_iva=total_con_iva
    )

@estimaciones_nuevo_bp.route('/guardar_estimacion', methods=['POST'])
def guardar_estimacion():
    from services.catalogo_base import generar_catalogo_base
    from models import Estimacion, DetalleEstimacion, Partida

    contrato_id = int(request.form.get("contrato_id"))
    contrato = Contrato.query.get_or_404(contrato_id)
    cantidades = request.form.to_dict()
    claves = request.form.getlist('clave[]')

    conceptos = generar_catalogo_base(contrato_id)
    conceptos_dict = {c['clave']: c for c in conceptos if c['clave'] in claves}

    numero_estimacion = Estimacion.query.filter_by(contrato_id=contrato_id).count() + 1
    hoy = date.today()

    nueva_estimacion = Estimacion(
        contrato_id=contrato_id,
        fecha=hoy,
        numero_estimacion=numero_estimacion,
        clave_contrato=contrato.contrato,
        nombre_contrato=contrato.nombre
    )
    db.session.add(nueva_estimacion)
    db.session.flush()  # Obtener el ID antes del commit

    subtotal_total = 0.0

    for clave in claves:
        concepto = conceptos_dict.get(clave)
        if not concepto:
            continue

        cantidad_str = cantidades.get(f"cantidad_{clave}", "0")
        try:
            cantidad = float(cantidad_str)
        except ValueError:
            cantidad = 0.0

        subtotal = cantidad * concepto['precio_unitario']
        subtotal_total += subtotal

        nombre_partida = concepto.get('nombre_partida', 'SIN PARTIDA')
        partida = Partida.query.filter_by(nombre=nombre_partida, contrato_id=contrato_id).first()

        if not partida:
            partida = Partida(nombre=nombre_partida, contrato_id=contrato_id)
            db.session.add(partida)
            db.session.flush()

        detalle = DetalleEstimacion(
            estimacion_id=nueva_estimacion.id,
            partida_id=partida.id,
            clave_concepto=clave,
            descripcion=concepto['descripcion'],
            unidad=concepto['unidad'],
            cantidad_estimacion=cantidad,
            precio_unitario=concepto['precio_unitario'],
            subtotal=subtotal,
            nombre_partida=nombre_partida
        )
        db.session.add(detalle)

    nueva_estimacion.subtotal = subtotal_total
    nueva_estimacion.iva = round(subtotal_total * 0.16, 2)
    nueva_estimacion.total_con_iva = nueva_estimacion.subtotal + nueva_estimacion.iva

    db.session.commit()

    return redirect(url_for('estimaciones_nuevo.amortizacion_estimacion', estimacion_id=nueva_estimacion.id))

@estimaciones_nuevo_bp.route('/amortizacion/<int:estimacion_id>', methods=['GET', 'POST'])
def amortizacion_estimacion(estimacion_id):
    from models import Estimacion, Contrato
    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato = estimacion.contrato

    subtotal = estimacion.subtotal or 0.0
    porcentaje_anticipo = contrato.porcentaje_anticipo or 0.0

    # ✅ Usamos los valores correctos que ya están en el modelo Contrato
    anticipo_base = contrato.anticipo_sin_iva or 0.0
    iva_anticipo = contrato.iva_anticipo or 0.0
    total_anticipo = contrato.total_anticipo or 0.0

    # Ya amortizado en estimaciones anteriores
    amortizado_total = sum(
        e.amortizacion or 0 for e in Estimacion.query.filter(
            Estimacion.contrato_id == contrato.id,
            Estimacion.id < estimacion.id
        )
    )

    saldo_amortizar = max(0, round(anticipo_base - amortizado_total, 2))
    iva_saldo = round(saldo_amortizar * 0.16, 2)
    total_saldo = saldo_amortizar + iva_saldo

    # Monto editable (prellenado con amortización actual si existe)
    if request.method == 'POST':
        try:
            monto_amortizacion = float(request.form.get('amortizacion', 0))
        except ValueError:
            monto_amortizacion = 0.0

        estimacion.amortizacion = monto_amortizacion
        db.session.commit()
        return redirect(url_for('estimaciones_nuevo.lista_estimaciones', contrato_id=contrato.id))

    monto_amortizacion = estimacion.amortizacion if estimacion.amortizacion is not None else saldo_amortizar
    iva_amortizacion = round(monto_amortizacion * 0.16, 2)
    total_amortizacion = monto_amortizacion + iva_amortizacion

    return render_template('estimaciones_nuevo/amortizacion.html',
                           estimacion=estimacion,
                           porcentaje_anticipo=porcentaje_anticipo,
                           anticipo_base=anticipo_base,
                           iva_anticipo=iva_anticipo,
                           total_anticipo=total_anticipo,
                           monto_amortizacion=monto_amortizacion,
                           iva_amortizacion=iva_amortizacion,
                           total_amortizacion=total_amortizacion,
                           amortizado_total=amortizado_total,
                           saldo_amortizar=saldo_amortizar,
                           iva_saldo=iva_saldo,
                           total_saldo=total_saldo,
                           subtotal_estimacion=subtotal)

@estimaciones_nuevo_bp.route('/guardar_nuevos_conceptos/<int:estimacion_id>', methods=['POST'])
def guardar_nuevos_conceptos(estimacion_id):
    from models import DetalleEstimacion, Partida

    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato_id = estimacion.contrato_id
    claves = request.form.getlist('clave[]')
    cantidades = request.form.to_dict()

    conceptos_base = generar_catalogo_base(contrato_id)
    conceptos_dict = {c['clave']: c for c in conceptos_base if c['clave'] in claves}

    for clave in claves:
        concepto = conceptos_dict.get(clave)
        if not concepto:
            continue

        cantidad_str = cantidades.get(f"cantidad_{clave}", "0")
        try:
            cantidad = float(cantidad_str)
        except ValueError:
            cantidad = 0.0

        subtotal = cantidad * concepto['precio_unitario']

        nombre_partida = concepto.get('nombre_partida', 'SIN PARTIDA')
        partida = Partida.query.filter_by(nombre=nombre_partida, contrato_id=contrato_id).first()
        if not partida:
            partida = Partida(nombre=nombre_partida, contrato_id=contrato_id)
            db.session.add(partida)
            db.session.flush()

        nuevo = DetalleEstimacion(
            estimacion_id=estimacion_id,
            partida_id=partida.id,
            clave_concepto=clave,
            descripcion=concepto['descripcion'],
            unidad=concepto['unidad'],
            cantidad_estimacion=cantidad,
            precio_unitario=concepto['precio_unitario'],
            subtotal=subtotal,
            nombre_partida=nombre_partida
        )
        db.session.add(nuevo)

    db.session.commit()
    return redirect(url_for('estimaciones_nuevo.detalle_estimacion', estimacion_id=estimacion_id))

# Ruta: /estimaciones/<contrato_id>/listado
from flask import Blueprint, render_template
from models import Contrato, Estimacion, DetalleEstimacion
from sqlalchemy import func

estimaciones_bp = Blueprint('estimaciones', __name__, url_prefix='/estimaciones')

@estimaciones_nuevo_bp.route('/<int:contrato_id>/listado')
def listado_estimaciones(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    estimaciones = Estimacion.query.filter_by(contrato_id=contrato_id).order_by(Estimacion.id).all()

    resumen = []
    for est in estimaciones:
        detalles = DetalleEstimacion.query.filter_by(estimacion_id=est.id).all()
        tiene_conceptos = len(detalles) > 0
        tiene_cantidades = any(d.cantidad_estimacion is not None for d in detalles)
        tiene_totales = est.total_con_iva is not None

        if not tiene_conceptos:
            estado = 'Vacía'
            color = 'red'
        elif tiene_conceptos and not tiene_cantidades:
            estado = 'Sin cantidades'
            color = 'yellow'
        elif tiene_cantidades and not tiene_totales:
            estado = 'Con cantidades'
            color = 'blue'
        else:
            estado = 'Completa'
            color = 'green'

        resumen.append({
            'estimacion': est,
            'estado': estado,
            'color': color,
            'conceptos': len(detalles),
            'monto': est.total_con_iva or 0
        })

    return render_template('estimaciones_nuevo/listado_estimaciones.html',
                       contrato=contrato,
                       resumen=resumen)

@estimaciones_nuevo_bp.route('/detalle_estimacion/<int:estimacion_id>')
def detalle_estimacion(estimacion_id):
    from models import Estimacion, DetalleEstimacion

    estimacion = Estimacion.query.get_or_404(estimacion_id)
    detalles = DetalleEstimacion.query.filter_by(estimacion_id=estimacion_id).all()

    return render_template(
        'estimaciones_nuevo/detalle_estimacion.html',
        estimacion=estimacion,
        detalles=detalles
    )

@estimaciones_nuevo_bp.route('/estimacion/<int:estimacion_id>/eliminar/<string:clave_concepto>', methods=['GET'])
def eliminar_concepto_estimacion(estimacion_id, clave_concepto):
    from models import DetalleEstimacion

    concepto = DetalleEstimacion.query.filter_by(
        estimacion_id=estimacion_id,
        clave_concepto=clave_concepto
    ).first()

    if concepto:
        db.session.delete(concepto)
        db.session.commit()

    return redirect(url_for('estimaciones_nuevo.editar_conceptos_estimacion', estimacion_id=estimacion_id))



@estimaciones_nuevo_bp.route('/agregar_conceptos/<int:estimacion_id>', methods=['GET', 'POST'])
def agregar_conceptos_estimacion(estimacion_id):
    from services.catalogo_base import generar_catalogo_base
    from models import DetalleEstimacion

    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato_id = estimacion.contrato_id

    # Obtener claves ya registradas en esta estimación
    claves_registradas = {d.clave_concepto for d in DetalleEstimacion.query.filter_by(estimacion_id=estimacion_id).all()}

    # Obtener catálogo base
    conceptos_base = generar_catalogo_base(contrato_id)

    # ✅ Filtrar conceptos: ordinarios + extraordinarios solo si estatus == 'A'
    conceptos_disponibles = []
    for c in conceptos_base:
        clave = c.get('clave', '')
        estatus = c.get('estatus', 'A')
        if clave.startswith('E') and estatus != 'A':
            continue
        if clave not in claves_registradas:
            conceptos_disponibles.append(c)

    if request.method == 'POST':
        claves_nuevas = request.form.getlist('clave[]')
        return redirect(url_for('estimaciones_nuevo.capturar_nuevos_conceptos', estimacion_id=estimacion_id, claves=','.join(claves_nuevas)))
     # Al final, justo antes del render_template
    conceptos_disponibles = sorted(conceptos_disponibles, key=lambda c: c['clave']) 

    return render_template(
        'estimaciones_nuevo/agregar_conceptos.html',
        estimacion=estimacion,
        conceptos_disponibles=conceptos_disponibles
    )

@estimaciones_nuevo_bp.route('/estimacion/<int:estimacion_id>/capturar_nuevos', methods=['GET'])
def capturar_nuevos_conceptos(estimacion_id):
    from services.catalogo_base import generar_catalogo_base
    from models import Estimacion

    # Obtener claves desde la URL (GET)
    claves_nuevas = request.args.get('claves', '').split(',')

    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato_id = estimacion.contrato_id

    # Obtener todos los conceptos del catálogo base
    todos_conceptos = generar_catalogo_base(contrato_id)

    # Filtrar solo los seleccionados
    conceptos_filtrados = [c for c in todos_conceptos if c['clave'] in claves_nuevas]

    return render_template('estimaciones_nuevo/capturar_nuevos_conceptos.html',
                           estimacion=estimacion,
                           conceptos=conceptos_filtrados)

@estimaciones_nuevo_bp.route('/ver_amortizacion/<int:estimacion_id>', methods=['GET', 'POST'])
def ver_amortizacion(estimacion_id):
    from models import Estimacion, Contrato
    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato = estimacion.contrato

    subtotal = estimacion.subtotal or 0.0
    porcentaje_anticipo = contrato.porcentaje_anticipo or 0

    # Total del anticipo
    anticipo_base = round(subtotal * (porcentaje_anticipo / 100), 2)
    iva_anticipo = round(anticipo_base * 0.16, 2)
    total_anticipo = anticipo_base + iva_anticipo

    # Ya amortizado en estimaciones anteriores
    amortizado_total = sum(
        e.amortizacion or 0 for e in Estimacion.query.filter(
            Estimacion.contrato_id == contrato.id,
            Estimacion.id < estimacion.id
        )
    )

    # Saldo pendiente
    saldo_amortizar = max(0, round(anticipo_base - amortizado_total, 2))
    iva_saldo = round(saldo_amortizar * 0.16, 2)
    total_saldo = saldo_amortizar + iva_saldo

    if request.method == 'POST':
        try:
            monto_amortizacion = float(request.form.get('amortizacion', 0))
        except ValueError:
            monto_amortizacion = 0.0

        estimacion.amortizacion = monto_amortizacion
        db.session.commit()
        return redirect(url_for('estimaciones_nuevo.ver_otras_deducciones', estimacion_id=estimacion.id))

    monto_amortizacion = estimacion.amortizacion if estimacion.amortizacion is not None else anticipo_base
    iva_amortizacion = round(monto_amortizacion * 0.16, 2)
    total_amortizacion = monto_amortizacion + iva_amortizacion

    return render_template('estimaciones_nuevo/ver_amortizacion.html',
                           estimacion=estimacion,
                           porcentaje_anticipo=porcentaje_anticipo,
                           anticipo_base=anticipo_base,
                           iva_anticipo=iva_anticipo,
                           total_anticipo=total_anticipo,
                           amortizado_total=amortizado_total,
                           saldo_amortizar=saldo_amortizar,
                           iva_saldo=iva_saldo,
                           total_saldo=total_saldo,
                           monto_amortizacion=monto_amortizacion,
                           iva_amortizacion=iva_amortizacion,
                           total_amortizacion=total_amortizacion,
                           subtotal_estimacion=subtotal)

@estimaciones_nuevo_bp.route('/ver_deducciones/<int:estimacion_id>', methods=['GET', 'POST'])
def ver_deducciones(estimacion_id):
    from models import Estimacion, DeduccionContrato, DeduccionEstimacion
    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato = estimacion.contrato

    # Obtener deducciones recurrentes del contrato
    deducciones_recurrentes = DeduccionContrato.query.filter_by(contrato_id=contrato.id).all()

    deducciones_calculadas = []
    for d in deducciones_recurrentes:
        monto = round((estimacion.subtotal or 0) * (d.porcentaje / 100), 2)
        deducciones_calculadas.append({
            'nombre': d.nombre,
            'porcentaje': d.porcentaje,
            'monto': monto
        })

    # Obtener deducciones manuales ya registradas
    deducciones_manual = DeduccionEstimacion.query.filter_by(estimacion_id=estimacion_id).all()

    return render_template('estimaciones_nuevo/ver_deducciones.html',
                           estimacion=estimacion,
                           deducciones_recurrentes=deducciones_calculadas,
                           deducciones_manual=deducciones_manual)

@estimaciones_nuevo_bp.route('/estimacion/<int:estimacion_id>/eliminar', methods=['GET'])
def eliminar_estimacion(estimacion_id):
    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato_id = estimacion.contrato_id

    # Eliminar los detalles primero
    DetalleEstimacion.query.filter_by(estimacion_id=estimacion_id).delete()

    # Luego eliminar la estimación
    db.session.delete(estimacion)
    db.session.commit()

    return redirect(url_for('estimaciones_nuevo.listado_estimaciones', contrato_id=contrato_id))

@estimaciones_nuevo_bp.route('/editar_conceptos/<int:estimacion_id>', methods=['GET', 'POST'])
def editar_conceptos_estimacion(estimacion_id):
    from models import Estimacion, DetalleEstimacion
    estimacion = Estimacion.query.get_or_404(estimacion_id)
    detalles = DetalleEstimacion.query.filter_by(estimacion_id=estimacion_id).all()

    if request.method == 'POST':
        cantidades = request.form.to_dict()
        subtotal_total = 0.0

        for detalle in detalles:
            clave = detalle.clave_concepto
            cantidad_str = cantidades.get(f"cantidad_{clave}", "0")
            try:
                cantidad = float(cantidad_str)
            except ValueError:
                cantidad = 0.0

            detalle.cantidad_estimacion = cantidad
            detalle.subtotal = cantidad * detalle.precio_unitario
            subtotal_total += detalle.subtotal

        estimacion.subtotal = subtotal_total
        estimacion.iva = round(subtotal_total * 0.16, 2)
        estimacion.total_con_iva = estimacion.subtotal + estimacion.iva

        db.session.commit()
        return redirect(url_for('estimaciones_nuevo.amortizacion_estimacion', estimacion_id=estimacion_id))

    return render_template('estimaciones_nuevo/editar_conceptos.html',
                           estimacion=estimacion,
                           detalles=detalles)