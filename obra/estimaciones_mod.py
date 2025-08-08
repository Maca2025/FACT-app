from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Contrato, Estimacion, DetalleEstimacion, AprobacionConcepto, ImportePartidaEstimacion
from services.catalogo_base import generar_catalogo_base
from datetime import date
from collections import defaultdict

estimaciones_mod_bp = Blueprint('estimaciones_mod', __name__, url_prefix='/estimaciones', template_folder='../templates')

# -------- Crear nueva estimación (pantalla 1) --------
@estimaciones_mod_bp.route('/nueva/<int:contrato_id>', methods=['GET', 'POST'])
def nueva_estimacion(contrato_id):
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
        numero_estimacion = Estimacion.query.filter_by(contrato_id=contrato_id).count() + 1
        hoy = date.today()

        estimacion = Estimacion(
            contrato_id=contrato_id,
            fecha=hoy,
            folio='PENDIENTE',
            comentario='',
            fecha_inicio_trab_est=hoy,
            fecha_fin_trab_est=hoy,
            numero_estimacion=numero_estimacion,
            clave_contrato=contrato.contrato,
            nombre_contrato=contrato.nombre
        )
        db.session.add(estimacion)
        db.session.commit()

        claves_seleccionadas = request.form.getlist('concepto_id')
        return redirect(
            url_for('estimaciones_mod.detalle_estimacion', estimacion_id=estimacion.id) +
            f"?claves={','.join(claves_seleccionadas)}"
        )

    return render_template('estimaciones/nueva_estimacion.html',
                           contrato=contrato,
                           conceptos=conceptos_validos)

# -------- Protección contra acceso sin contrato_id --------
@estimaciones_mod_bp.route('/nueva/')
def redireccionar_a_obras():
    return redirect(url_for('contratos_obra.obras_abiertas'))

# -------- Mostrar y guardar detalle del cuerpo de una estimación --------
@estimaciones_mod_bp.route('/<int:estimacion_id>/detalle', methods=['GET', 'POST'])
def detalle_estimacion(estimacion_id):
    print(f"⚙️ Entrando a detalle_estimacion con ID {estimacion_id}")

    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato = estimacion.contrato
    conceptos = generar_catalogo_base(contrato.id)

    claves_param = request.args.get('claves', '')
    claves_seleccionadas = claves_param.split(',')

    conceptos_filtrados = [c for c in conceptos if c.get('clave') in claves_seleccionadas]

    if request.method == 'POST':
        subtotal_total = 0.0
        partidas_importes = defaultdict(lambda: {'original': 0.0, 'actual': 0.0, 'anterior': 0.0})

        for concepto in conceptos_filtrados:
            clave = concepto['clave']
            partida = concepto['nombre_partida']
            subtotal_original = concepto.get('subtotal_original', 0.0)

            cantidad_str = request.form.get(f'cantidad_{clave}')
            if cantidad_str:
                try:
                    cantidad = float(cantidad_str)
                    subtotal = cantidad * concepto['precio_unitario']
                except ValueError:
                    continue

                subtotal_total += subtotal

                detalle = DetalleEstimacion(
                    estimacion_id=estimacion.id,
                    clave_concepto=clave,
                    descripcion=concepto['descripcion'],
                    unidad=concepto['unidad'],
                    cantidad_estimacion=cantidad,
                    precio_unitario=concepto['precio_unitario'],
                    subtotal=subtotal,
                    nombre_partida=partida
                )
                db.session.add(detalle)

                partidas_importes[partida]['original'] += subtotal_original
                partidas_importes[partida]['actual'] += subtotal

        estimacion_anterior = Estimacion.query.filter(
            Estimacion.contrato_id == contrato.id,
            Estimacion.id < estimacion.id
        ).order_by(Estimacion.numero_estimacion.desc()).first()

        if estimacion_anterior:
            anteriores = ImportePartidaEstimacion.query.filter_by(estimacion_id=estimacion_anterior.id).all()
            for anterior in anteriores:
                partidas_importes[anterior.nombre_partida]['anterior'] = anterior.importe_estimacion

        for partida, valores in partidas_importes.items():
            registro = ImportePartidaEstimacion(
                estimacion_id=estimacion.id,
                nombre_partida=partida,
                importe_original=valores['original'],
                importe_estimacion=valores['actual'],
                importe_anterior=valores['anterior'],
                importe_acumulado=valores['actual'] + valores['anterior']
            )
            db.session.add(registro)

        estimacion.subtotal = subtotal_total
        estimacion.iva = round(subtotal_total * 0.16, 2)
        estimacion.total_con_iva = estimacion.subtotal + estimacion.iva

        anticipo = contrato.porcentaje_anticipo or 0
        estimacion.amortizacion = round(estimacion.subtotal * (anticipo / 100), 2)

        db.session.commit()

        return redirect(url_for('estimaciones_mod.caratula_estimacion', estimacion_id=estimacion.id))

    try:
        return render_template('estimaciones/detalle_estimacion.html',
                               estimacion=estimacion,
                               contrato=contrato,
                               conceptos=conceptos_filtrados)
    except Exception as e:
        return f"❌ Error al renderizar la plantilla: {e}", 500

# -------- Mostrar carátula de una estimación --------
@estimaciones_mod_bp.route('/<int:estimacion_id>/caratula')
def caratula_estimacion(estimacion_id):
    estimacion = Estimacion.query.get_or_404(estimacion_id)
    contrato = estimacion.contrato

    partidas = ImportePartidaEstimacion.query.filter_by(estimacion_id=estimacion.id).all()

    presupuesto = sum(p.importe_original for p in partidas)
    anterior = sum(p.importe_anterior for p in partidas)
    actual = sum(p.importe_estimacion for p in partidas)
    acumulado = sum(p.importe_acumulado for p in partidas)

    totales = {
        'presupuesto': presupuesto,
        'anterior': anterior,
        'actual': actual,
        'acumulado': acumulado,
        'amortizacion': estimacion.amortizacion or 0
    }

    return render_template('estimaciones/caratula_estimacion.html',
                           estimacion=estimacion,
                           contrato=contrato,
                           partidas=partidas,
                           totales=totales)

# -------- Guardar ajustes manuales en la carátula --------
@estimaciones_mod_bp.route('/<int:estimacion_id>/caratula', methods=['POST'])
def guardar_caratula_estimacion(estimacion_id):
    estimacion = Estimacion.query.get_or_404(estimacion_id)
    partidas = ImportePartidaEstimacion.query.filter_by(estimacion_id=estimacion.id).all()

    for partida in partidas:
        try:
            partida.importe_original = float(request.form.get(f"presupuesto_{partida.id}", partida.importe_original))
            partida.importe_anterior = float(request.form.get(f"anterior_{partida.id}", partida.importe_anterior))
            partida.importe_estimacion = float(request.form.get(f"actual_{partida.id}", partida.importe_estimacion))
            partida.importe_acumulado = float(request.form.get(f"acumulado_{partida.id}", partida.importe_acumulado))
        except ValueError:
            continue

    try:
        estimacion.subtotal = float(request.form.get("estimacion_actual", estimacion.subtotal))
        estimacion.iva = float(request.form.get("iva", estimacion.iva))
        estimacion.total_con_iva = float(request.form.get("total_con_iva", estimacion.total_con_iva))
        estimacion.amortizacion = float(request.form.get("amortizacion", estimacion.amortizacion or 0))
    except ValueError:
        pass

    db.session.commit()
    return redirect(url_for('estimaciones_mod.caratula_estimacion', estimacion_id=estimacion.id))

# -------- Ver lista de estimaciones por contrato --------
@estimaciones_mod_bp.route('/lista/<int:contrato_id>')
def lista_estimaciones(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    estimaciones = Estimacion.query.filter_by(contrato_id=contrato_id).order_by(Estimacion.numero_estimacion).all()
    return render_template('estimaciones/lista_estimaciones.html',
                           contrato=contrato,
                           estimaciones=estimaciones)

# -------- Ruta de prueba --------
@estimaciones_mod_bp.route('/test')
def test_estimaciones():
    return "Ruta estimaciones funcionando"

@estimaciones_mod_bp.route('/debug')
def debug_estimaciones():
    return "✅ Ruta /debug del blueprint estimaciones_mod_bp está funcionando correctamente"