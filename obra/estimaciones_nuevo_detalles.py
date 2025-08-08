from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Contrato, AprobacionConcepto, Estimacion, DetalleEstimacion
from services.catalogo_base import generar_catalogo_base
from datetime import date

estimaciones_nuevo_bp = Blueprint('estimaciones_nuevo', __name__, url_prefix='/estimaciones')

@estimaciones_nuevo_bp.route('/crear/<int:contrato_id>', methods=['GET', 'POST'])
def crear_estimacion(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    conceptos = generar_catalogo_base(contrato_id)

    conceptos_validos = []
    for c in conceptos:
        clave = c.get('clave')
        if clave.lower().startswith('e'):
            aprobado = AprobacionConcepto.query.filter_by(
                contrato_id=contrato_id,
                clave_concepto=clave,
                estado='aprobado'
            ).first()
            if aprobado:
                conceptos_validos.append(c)
        else:
            conceptos_validos.append(c)

    if request.method == 'POST':
        claves_seleccionadas = request.form.getlist('concepto_id')
        return redirect(
            url_for('estimaciones_nuevo.capturar_cantidades') +
            f"?claves={','.join(claves_seleccionadas)}&contrato_id={contrato_id}"
        )

    return render_template('estimaciones_nuevo/crear_estimacion.html',
                           contrato=contrato,
                           conceptos=conceptos_validos)

@estimaciones_nuevo_bp.route('/capturar', methods=['GET', 'POST'])
def capturar_cantidades():
    contrato_id = request.args.get('contrato_id', type=int)
    claves = request.args.get('claves', '')
    claves_seleccionadas = claves.split(',')

    contrato = Contrato.query.get_or_404(contrato_id)
    conceptos = generar_catalogo_base(contrato_id)

    conceptos_filtrados = [c for c in conceptos if c['clave'] in claves_seleccionadas]

    if request.method == 'POST':
        cantidades = {}
        for c in conceptos_filtrados:
            clave = c['clave']
            cantidad_str = request.form.get(f'cantidad_{clave}')
            try:
                cantidades[clave] = float(cantidad_str)
            except (TypeError, ValueError):
                cantidades[clave] = 0.0

        return f"✅ Cantidades capturadas: {cantidades}"

    return render_template('estimaciones_nuevo/capturar_cantidades.html',
                           contrato=contrato,
                           conceptos=conceptos_filtrados)

@estimaciones_nuevo_bp.route('/suma_conceptos', methods=['POST'])
def suma_conceptos():
    contrato_id = int(request.args.get("contrato_id"))
    contrato = Contrato.query.get_or_404(contrato_id)
    conceptos = generar_catalogo_base(contrato_id)

    resumen = []
    subtotal_total = 0.0

    numero_estimacion = Estimacion.query.filter_by(contrato_id=contrato_id).count() + 1
    nueva = Estimacion(
        contrato_id=contrato_id,
        fecha=date.today(),
        numero_estimacion=numero_estimacion,
        clave_contrato=contrato.contrato,
        nombre_contrato=contrato.nombre
    )
    db.session.add(nueva)
    db.session.commit()

    for concepto in conceptos:
        clave = concepto['clave']
        cantidad_str = request.form.get(f'cantidad_{clave}')
        if cantidad_str:
            try:
                cantidad = float(cantidad_str)
                subtotal = cantidad * concepto['precio_unitario']

                detalle = DetalleEstimacion(
                    estimacion_id=nueva.id,
                    clave_concepto=clave,
                    descripcion=concepto['descripcion'],
                    unidad=concepto['unidad'],
                    cantidad_estimacion=cantidad,
                    precio_unitario=concepto['precio_unitario'],
                    subtotal=subtotal,
                    nombre_partida=concepto.get('nombre_partida', '')
                )
                db.session.add(detalle)

                resumen.append({
                    'clave': clave,
                    'descripcion': concepto['descripcion'],
                    'unidad': concepto['unidad'],
                    'precio_unitario': concepto['precio_unitario'],
                    'cantidad': cantidad,
                    'subtotal': subtotal
                })

                subtotal_total += subtotal
            except ValueError:
                continue

    nueva.subtotal = subtotal_total
    nueva.iva = round(subtotal_total * 0.16, 2)
    nueva.total_con_iva = nueva.subtotal + nueva.iva

    db.session.commit()

    return render_template('estimaciones_nuevo/suma_conceptos.html',
                           contrato=contrato,
                           conceptos=resumen,
                           subtotal=nueva.subtotal,
                           iva=nueva.iva,
                           total=nueva.total_con_iva,
                           estimacion=nueva)