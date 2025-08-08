from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Contrato, CatalogoVersion, ConceptoCatalogo, AvanceObra, DetalleAvance
from datetime import date
from sqlalchemy import func
from services.catalogo_base import generar_catalogo_base

avances_bp = Blueprint('avances', __name__, url_prefix='/avances', template_folder='../templates')

@avances_bp.route('/test')
def test():
    return "Avances funcionando"

#------subir avances------
@avances_bp.route('/subir_avance', methods=['GET', 'POST'])
def subir_avance():
    contratos = Contrato.query.filter_by(estado='abierto').all()

    if request.method == 'POST':
        contrato_id = int(request.form.get('contrato_id'))
        fecha = request.form.get('fecha')
        conceptos_ids = request.form.getlist('concepto_id')
        contrato = Contrato.query.get_or_404(contrato_id)

        numero_version = AvanceObra.query.filter_by(contrato_id=contrato_id).count() + 1

        avance = AvanceObra(
            contrato_id=contrato_id,
            fecha=date.fromisoformat(fecha),
            version_catalogo_id=None,  # Se mantiene nulo al usar catálogo base acumulado
            numero_version=numero_version
        )
        db.session.add(avance)
        db.session.flush()

        total_registrado = 0

        for concepto_id in conceptos_ids:
            concepto = ConceptoCatalogo.query.get(concepto_id)
            valor = request.form.get(f'cantidad_{concepto_id}', '0')
            cantidad = float(valor) if valor.strip() else 0.0

            if cantidad <= 0:
                continue

            subtotal = cantidad * concepto.precio_unitario
            detalle = DetalleAvance(
                avance_id=avance.id,
                concepto_id=concepto.id,
                cantidad_avance=cantidad,
                subtotal_avance=subtotal
            )
            db.session.add(detalle)
            total_registrado += 1

        if total_registrado == 0:
            db.session.rollback()
            return redirect(request.referrer + "?error=No+se+ingresaron+datos+de+avance")

        db.session.commit()
        return render_template(
            'obra/mensaje_subida.html',
            mensaje="Avance registrado correctamente.",
            contrato_id=contrato_id
        )

    return render_template('obra/subir_avance.html', contratos=contratos)

# ============================
# HISTORIAL DE AVANCES
# ============================

@avances_bp.route('/historial/<int:contrato_id>')
def historial_avances(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    avances = AvanceObra.query \
        .filter_by(contrato_id=contrato_id) \
        .order_by(AvanceObra.fecha.desc()) \
        .all()

    return render_template(
        'obra/historial_avances.html',
        contrato=contrato,
        avances=avances
    )

# ============================
# SELECCIONAR CONCEPTOS PARA AVANCE
# ============================
@avances_bp.route('/seleccionar/<int:contrato_id>', methods=['GET', 'POST'])
def seleccionar_conceptos(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    catalogo_base = generar_catalogo_base(contrato_id)

    if not catalogo_base:
        return "Este contrato no tiene catálogos registrados.", 400

    if request.method == 'POST':
        conceptos_ids = request.form.getlist('concepto_id[]')
        if not conceptos_ids:
            return render_template(
                'obra/seleccionar_conceptos.html',
                contrato=contrato,
                conceptos_por_partida=agrupar_por_partida(catalogo_base),
                mensaje_error="Debes seleccionar al menos un concepto antes de continuar."
            )

        conceptos_seleccionados = [c for c in catalogo_base if c['clave'] in conceptos_ids]
        acumulados = calcular_acumulados([c['id'] for c in conceptos_seleccionados], contrato.id)

        return render_template(
            'obra/subir_avance.html',
            contrato=contrato,
            conceptos=conceptos_seleccionados,
            acumulados=acumulados,
            version_numero=AvanceObra.query.filter_by(contrato_id=contrato.id).count() + 1
        )

    conceptos_filtrados = [c for c in catalogo_base if c['cantidad'] > 0]
    conceptos_por_partida = agrupar_por_partida(conceptos_filtrados)

    return render_template(
        'obra/seleccionar_conceptos.html',
        contrato=contrato,
        conceptos_por_partida=conceptos_por_partida
    )
# ============================
# GUARDAR AVANCE FILTRADO
# ============================

@avances_bp.route('/guardar/<int:contrato_id>', methods=['POST'])
def guardar_avance_filtrado(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    fecha = request.form.get('fecha')
    conceptos_ids = request.form.getlist('concepto_id[]')
    print("Conceptos recibidos:", conceptos_ids)

    if not fecha or not conceptos_ids:
        return render_template(
            'obra/mensaje_subida.html',
            mensaje="Debes seleccionar una fecha y al menos un concepto para registrar el avance.",
            contrato_id=contrato_id
        )

    numero_version = AvanceObra.query.filter_by(contrato_id=contrato_id).count() + 1

    avance = AvanceObra(
        contrato_id=contrato_id,
        fecha=date.fromisoformat(fecha),
        version_catalogo_id=None,
        numero_version=numero_version
    )
    db.session.add(avance)
    db.session.flush()

    total_registrado = 0
    for concepto_id in conceptos_ids:
        valor = request.form.get(f'cantidad_{concepto_id}', '').strip()
        cantidad = float(valor) if valor else 0.0
        if cantidad <= 0:
            continue

        concepto = ConceptoCatalogo.query.get(concepto_id)
        subtotal = cantidad * concepto.precio_unitario

        detalle = DetalleAvance(
            avance_id=avance.id,
            concepto_id=concepto.id,
            cantidad_avance=cantidad,
            subtotal_avance=subtotal
        )
        db.session.add(detalle)
        total_registrado += 1

    if total_registrado == 0:
        db.session.rollback()
        return redirect(request.referrer + "?error=No+se+ingresaron+datos+de+avance")
    print(f"Total conceptos registrados: {total_registrado}")
    db.session.commit()
    return render_template(
        'obra/mensaje_subida.html',
        mensaje="Avance registrado correctamente.",
        contrato_id=contrato_id
    )

# ============================
# PANEL DE AVANCES CON SCROLL HORIZONTAL
# ============================

@avances_bp.route('/panel/<int:contrato_id>')
def panel_avances(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    catalogo_base = [c for c in generar_catalogo_base(contrato_id) if c['cantidad'] > 0]

    if not catalogo_base:
        return "Este contrato no tiene un catálogo base disponible.", 400

    # Obtener todas las fechas de avance en orden ascendente
    fechas = db.session.query(AvanceObra.fecha) \
        .filter_by(contrato_id=contrato_id) \
        .order_by(AvanceObra.fecha.asc()) \
        .distinct().all()
    fechas = [f[0] for f in fechas]

    # Construir avance_data por concepto
    avance_data = {}
    totales_por_fecha = {f: 0 for f in fechas}
    totales_cantidades = {f: 0 for f in fechas}

    for concepto in catalogo_base:
        concepto_id = concepto['id']

        acumulado = db.session.query(func.sum(DetalleAvance.cantidad_avance)) \
            .join(AvanceObra) \
            .filter(
                DetalleAvance.concepto_id == concepto_id,
                AvanceObra.contrato_id == contrato_id
            ).scalar() or 0

        subtotal_catalogo = concepto['precio_unitario'] * concepto['cantidad']
        subtotal_avanzado = concepto['precio_unitario'] * acumulado
        subtotal_pendiente = subtotal_catalogo - subtotal_avanzado

        cantidades_por_fecha = {}
        subtotales_por_fecha = {}

        for f in fechas:
            cantidad = db.session.query(func.sum(DetalleAvance.cantidad_avance)) \
                .join(AvanceObra) \
                .filter(
                    DetalleAvance.concepto_id == concepto_id,
                    AvanceObra.contrato_id == contrato_id,
                    AvanceObra.fecha == f
                ).scalar() or 0

            subtotal_fecha = cantidad * concepto['precio_unitario']
            cantidades_por_fecha[f] = cantidad
            subtotales_por_fecha[f] = subtotal_fecha

            totales_por_fecha[f] += subtotal_fecha
            totales_cantidades[f] += cantidad

        avance_data[concepto_id] = {
            'concepto': concepto,
            'acumulado': acumulado,
            'subtotal_catalogo': subtotal_catalogo,
            'subtotal_avanzado': subtotal_avanzado,
            'subtotal_pendiente': subtotal_pendiente,
            'cantidades_por_fecha': cantidades_por_fecha,
            'subtotales_por_fecha': subtotales_por_fecha,
        }

    # Ahora agrupar avance_data por partida
    from collections import defaultdict

    partidas = defaultdict(lambda: {
        'nombre_partida': '',
        'conceptos': [],
        'subtotal_partida_catalogo': 0.0,
        'subtotal_partida_avanzado': 0.0,
        'subtotal_partida_pendiente': 0.0,
    })

    for info in avance_data.values():
        partida = info['concepto']['partida']
        partidas[partida]['nombre_partida'] = info['concepto']['nombre_partida']
        partidas[partida]['conceptos'].append(info)
        partidas[partida]['subtotal_partida_catalogo'] += info['subtotal_catalogo']
        partidas[partida]['subtotal_partida_avanzado'] += info['subtotal_avanzado']
        partidas[partida]['subtotal_partida_pendiente'] += info['subtotal_pendiente']

    # Ordenar partidas por clave
    partidas = dict(sorted(partidas.items()))

    return render_template(
        'obra/panel_avances.html',
        contrato=contrato,
        fechas=fechas,
        partidas=partidas,
        totales_por_fecha=totales_por_fecha,
        totales_cantidades=totales_cantidades
    )

# ============================
# FUNCIÓN AUXILIAR: CALCULAR ACUMULADOS
# ============================

def calcular_acumulados(conceptos_ids, contrato_id):
    acumulados = {}
    for concepto_id in conceptos_ids:
        total = db.session.query(func.sum(DetalleAvance.cantidad_avance)) \
            .join(AvanceObra) \
            .filter(DetalleAvance.concepto_id == concepto_id) \
            .filter(AvanceObra.contrato_id == contrato_id) \
            .scalar() or 0
        acumulados[int(concepto_id)] = total
    return acumulados


# ============================
# FUNCIÓN AUXILIAR: CALCULAR ACUMULADOS
# ============================

def calcular_acumulados(conceptos_ids, contrato_id):
    acumulados = {}
    for concepto_id in conceptos_ids:
        total = db.session.query(func.sum(DetalleAvance.cantidad_avance)) \
            .join(AvanceObra) \
            .filter(DetalleAvance.concepto_id == concepto_id) \
            .filter(AvanceObra.contrato_id == contrato_id) \
            .scalar() or 0
        acumulados[int(concepto_id)] = total
    return acumulados

def agrupar_por_partida(lista_conceptos):
    from collections import defaultdict
    agrupado = defaultdict(list)
    for c in lista_conceptos:
        partida = c.get('nombre_partida', 'SIN PARTIDA')
        agrupado[partida].append(c)
    return dict(agrupado)

# ============================
# DETALLE DE UN AVANCE
# ============================
@avances_bp.route('/detalle/<int:avance_id>', endpoint='detalle_avance')
def detalle_avance(avance_id):
    avance = AvanceObra.query.get_or_404(avance_id)
    contrato = avance.contrato
    detalles_raw = avance.detalles

    # Obtener catálogo base acumulado
    catalogo_base = {c['id']: c for c in generar_catalogo_base(contrato.id)}

    # Preparar los detalles enriquecidos
    detalles = []
    for d in detalles_raw:
        concepto_info = catalogo_base.get(d.concepto_id)
        if concepto_info:
            detalles.append({
                'partida': concepto_info['partida'],
                'nombre_partida': concepto_info['nombre_partida'],
                'clave': concepto_info['clave'],
                'descripcion': concepto_info['descripcion'],
                'unidad': concepto_info['unidad'],
                'cantidad': d.cantidad_avance,
                'precio_unitario': concepto_info['precio_unitario'],
                'subtotal': d.subtotal_avance
            })

    return render_template('obra/detalle_avance.html', avance=avance, contrato=contrato, detalles=detalles)

# ---------- Eliminar Avance ----------
@avances_bp.route('/eliminar_avance/<int:avance_id>', methods=['POST'])
def eliminar_avance(avance_id):
    avance = AvanceObra.query.get_or_404(avance_id)
    contrato_id = avance.contrato_id

    try:
        # Eliminar primero los detalles vinculados
        DetalleAvance.query.filter_by(avance_id=avance.id).delete()
        db.session.delete(avance)
        db.session.commit()
        mensaje = "Avance eliminado correctamente."
    except Exception as e:
        db.session.rollback()
        mensaje = f"Error al eliminar avance: {e}"

    return redirect(url_for('avances.historial_avances', contrato_id=contrato_id))