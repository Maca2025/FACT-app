from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from models import db, Contrato, CatalogoVersion, ConceptoCatalogo
import os
import pandas as pd
from datetime import date
from sqlalchemy.orm import joinedload
from services.prefiniquitos import generar_prefiniquito
from collections import defaultdict
from flask import flash
from models import AprobacionConcepto, RevisionConcepto


catalogos_bp = Blueprint('catalogos', __name__, template_folder='../templates')

#----SUBIR CATALOGO-----
@catalogos_bp.route('/subir_catalogo', methods=['GET', 'POST'])
def subir_catalogo():
    contratos = Contrato.query.all()
    contrato_id_param = request.args.get('contrato_id')

    if request.method == 'POST':
        contrato_id = request.form.get('contrato_id')
        archivo = request.files.get('archivo')
        comentario = request.form.get('comentario', '').strip()

        if not contrato_id or not archivo:
            return "Faltan datos", 400

        contrato = Contrato.query.get(contrato_id)
        if not contrato:
            return "Contrato no encontrado", 404

        filename = secure_filename(archivo.filename)
        filepath = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        archivo.save(filepath)

        try:
            df = pd.read_excel(filepath)
        except Exception as e:
            return f"Error al leer el archivo: {e}", 400

        columnas_requeridas = [
            'numero partida',
            'nombre partida',
            'clave concepto',
            'descripcion concepto',
            'unidad',
            'precio unitario',
            'cantidad',
            'subtotal'
        ]

        if not all(col in df.columns for col in columnas_requeridas):
            return "El archivo debe tener las siguientes columnas: " + ", ".join(columnas_requeridas), 400

        original_existente = CatalogoVersion.query.filter_by(contrato_id=contrato_id, tipo='original').first()
        tipo = 'actualizado' if original_existente else 'original'
        nombre = f"Catálogo {tipo.capitalize()}"

        nueva_version = CatalogoVersion(
            contrato_id=contrato_id,
            tipo=tipo,
            fecha_subida=date.today(),
            nombre=nombre,
            comentario=comentario
        )
        db.session.add(nueva_version)
        db.session.flush()

        for _, fila in df.iterrows():
            try:
                precio_unitario = float(str(fila['precio unitario']).replace('$', '').replace(',', '').strip())
                cantidad = float(fila['cantidad'])

                if 'subtotal' in fila and pd.notnull(fila['subtotal']):
                    subtotal = float(str(fila['subtotal']).replace('$', '').replace(',', '').strip())
                else:
                    subtotal = precio_unitario * cantidad
            except (ValueError, TypeError):
                return "Error al convertir valores numéricos. Revisa que los precios, cantidades y subtotales sean válidos.", 400

            clave_concepto = str(fila['clave concepto']).strip()

            concepto = ConceptoCatalogo(
                version_id=nueva_version.id,
                clave_concepto=clave_concepto,
                partida=str(fila['numero partida']).strip(),
                nombre_partida=str(fila['nombre partida']).strip(),
                descripcion=str(fila['descripcion concepto']).strip(),
                unidad=str(fila['unidad']).strip(),
                precio_unitario=precio_unitario,
                cantidad=cantidad,
                subtotal=subtotal
            )
            db.session.add(concepto)

        db.session.commit()

        # =======================
        # CREAR APROBACIÓN Y PRIMERA REVISIÓN PARA EXTRAORDINARIOS NUEVOS
        # =======================
        for _, fila in df.iterrows():
            clave = str(fila['clave concepto']).strip()

            if clave.lower().startswith('e'):
                descripcion = str(fila['descripcion concepto']).strip()
                precio_unitario = float(str(fila['precio unitario']).replace('$', '').replace(',', '').strip())

                aprobacion = AprobacionConcepto.query.filter_by(
                    contrato_id=contrato_id,
                    clave_concepto=clave
                ).first()

                if not aprobacion:
                    # Crear nueva aprobación
                    aprobacion = AprobacionConcepto(
                        contrato_id=contrato_id,
                        clave_concepto=clave,
                        estado='elaboracion',
                        precio_unitario=precio_unitario,
                        descripcion=descripcion
                    )
                    db.session.add(aprobacion)
                    db.session.flush()

                    # Crear primera revisión en estado E
                    primera = RevisionConcepto(
                        aprobacion_id=aprobacion.id,
                        numero_revision=1,
                        fecha=date.today(),
                        precio_unitario=precio_unitario,
                        comentario='Registro inicial desde catálogo',
                        estado='elaboracion'
                    )
                    db.session.add(primera)

        db.session.commit()

        if nueva_version.tipo == 'actualizado':
            version_original = CatalogoVersion.query \
                .filter_by(contrato_id=contrato_id, tipo='original') \
                .order_by(CatalogoVersion.id.asc()) \
                .first()

            if version_original:
                generar_prefiniquito(
                    contrato_id=contrato_id,
                    version_original_id=version_original.id,
                    version_actualizada_id=nueva_version.id
                )

        return render_template('obra/mensaje_subida.html', mensaje="Catálogo cargado correctamente.", contrato_id=contrato_id)

    return render_template('obra/subir_catalogo.html', contratos=contratos, contrato_id_param=contrato_id_param)


# ---------- Vista de catálogos por contrato ----------
@catalogos_bp.route('/catalogos_por_contrato/<int:contrato_id>')
def catalogos_por_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    versiones = CatalogoVersion.query \
        .options(joinedload(CatalogoVersion.conceptos)) \
        .filter_by(contrato_id=contrato_id) \
        .order_by(CatalogoVersion.fecha_subida.desc(), CatalogoVersion.id.desc()) \
        .all()

    return render_template(
        'obra/catalogos_por_contrato.html',
        contrato=contrato,
        versiones=versiones
    )

# ---------- Ver todos los contratos con catálogo ----------
@catalogos_bp.route('/catalogos')
def ver_catalogos():
    contratos = Contrato.query.options(
        joinedload(Contrato.catalogos)
    ).all()
    return render_template('obra/catalogos.html', contratos=contratos)

# ---------- Ver conceptos de una versión específica ----------
@catalogos_bp.route('/catalogo_conceptos/<int:version_id>')
def ver_catalogo_conceptos(version_id):
    version = CatalogoVersion.query.get_or_404(version_id)
    contrato = version.contrato
    conceptos = ConceptoCatalogo.query.filter_by(version_id=version_id).all()

    return render_template(
        'obra/catalogo_conceptos.html',
        contrato=contrato,
        version=version,
        conceptos=conceptos
    )

# ---------- Ver conceptos por versión específica con agrupación ----------
@catalogos_bp.route('/catalogo_conceptos_version/<int:version_id>')
def ver_conceptos_version(version_id):
    version = CatalogoVersion.query.get_or_404(version_id)
    contrato = version.contrato
    conceptos = ConceptoCatalogo.query \
        .filter_by(version_id=version_id) \
        .order_by(ConceptoCatalogo.partida, ConceptoCatalogo.concepto).all()

    from collections import defaultdict

    partidas_dict = defaultdict(lambda: {
        'nombre_partida': '',
        'conceptos': [],
        'subtotal_partida': 0.0
    })

    total_catalogo = 0.0

    for c in conceptos:
        key = c.partida
        partidas_dict[key]['nombre_partida'] = c.nombre_partida
        partidas_dict[key]['conceptos'].append(c)
        partidas_dict[key]['subtotal_partida'] += c.subtotal or 0.0
        total_catalogo += c.subtotal or 0.0

    partidas = []
    for key, data in partidas_dict.items():
        partidas.append({
            'partida': key,
            'nombre_partida': data['nombre_partida'],
            'conceptos': data['conceptos'],
            'subtotal_partida': data['subtotal_partida']
        })

    partidas = sorted(partidas, key=lambda p: p['partida'])

    iva = total_catalogo * 0.16
    total_con_iva = total_catalogo + iva

    return render_template(
        'obra/catalogo_conceptos_version.html',
        contrato=contrato,
        version=version,
        partidas=partidas,
        total_catalogo=total_catalogo,
        iva=iva,
        total_con_iva=total_con_iva
    )

# ---------- Prefiniquitos por contrato ----------
@catalogos_bp.route('/prefiniquitos/<int:contrato_id>')
def ver_prefiniquitos(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    prefiniquitos = contrato.prefiniquitos
    prefiniquitos = sorted(prefiniquitos, key=lambda p: p.fecha_generacion, reverse=True)

    return render_template(
        'obra/historial_prefiniquitos.html',
        contrato=contrato,
        prefiniquitos=prefiniquitos
    )

# ---------- Detalle de un prefiniquito ----------
@catalogos_bp.route('/prefiniquito_detalle/<int:prefiniquito_id>')
def ver_prefiniquito_detalle(prefiniquito_id):
    from models import Prefiniquito, DetallePrefiniquito

    prefiniquito = Prefiniquito.query.get_or_404(prefiniquito_id)
    detalles = DetallePrefiniquito.query.filter_by(prefiniquito_id=prefiniquito.id).all()

    return render_template(
        'obra/prefiniquito_detalle.html',
        prefiniquito=prefiniquito,
        detalles=detalles
    )

# ---------- Vista del Catálogo Base acumulado ----------
@catalogos_bp.route('/catalogo_base/<int:contrato_id>')
def ver_catalogo_base(contrato_id):
    from datetime import date
    from types import SimpleNamespace
    from collections import defaultdict
    from models import CatalogoBaseAcumulado
    from services.catalogo_base import guardar_catalogo_base_si_nuevo
    import json

    # 🔍 Obtener el contrato
    contrato = Contrato.query.get_or_404(contrato_id)

    # 📦 Obtener la versión guardada del catálogo (o crear una nueva si ha cambiado)
    catalogo_guardado = guardar_catalogo_base_si_nuevo(contrato_id)

    # ⚠️ Si no hay contenido guardado, mostramos error
    if not catalogo_guardado or not catalogo_guardado.conceptos_json:
        return "No se pudo generar el Catálogo Base.", 400

    # 🔄 Convertimos el JSON guardado a lista de diccionarios
    conceptos = json.loads(catalogo_guardado.conceptos_json)

    # ========================
    # Agrupar conceptos por partida
    # ========================
    partidas = defaultdict(lambda: {
        'nombre_partida': '',
        'conceptos': [],
        'subtotal_partida': 0.0
    })

    total_catalogo = 0.0
    for c in conceptos:
        key = (c['partida'], c['nombre_partida'])
        partidas[key]['nombre_partida'] = c['nombre_partida']
        partidas[key]['conceptos'].append(SimpleNamespace(**c))  # Convertimos a objeto para usar en plantilla
        partidas[key]['subtotal_partida'] += c['subtotal']
        total_catalogo += c['subtotal']

    # 🧮 Convertimos el diccionario de partidas a lista ordenada
    partidas_list = []
    for key, data in partidas.items():
        partidas_list.append({
            'partida': key[0],
            'nombre_partida': data['nombre_partida'],
            'conceptos': data['conceptos'],
            'subtotal_partida': data['subtotal_partida']
        })
    partidas_list = sorted(partidas_list, key=lambda x: x['partida'])

    # ========================
    # Calcular IVA y total con IVA
    # ========================
    iva = total_catalogo * 0.16
    total_con_iva = total_catalogo + iva

    # ========================
    # Renderizar plantilla HTML
    # ========================
    return render_template(
        'obra/catalogo_base.html',
        contrato=contrato,
        partidas=partidas_list,
        total_catalogo=total_catalogo,
        iva=iva,
        total_con_iva=total_con_iva,
        fecha_generacion=catalogo_guardado.fecha_generacion,
        version_catalogo=catalogo_guardado.version
    )

# ---------- Actualizar comentario de versión ----------
@catalogos_bp.route('/actualizar_comentario/<int:version_id>', methods=['POST'])
def actualizar_comentario(version_id):
    nueva_nota = request.form.get('comentario', '').strip()

    version = CatalogoVersion.query.get_or_404(version_id)
    version.comentario = nueva_nota

    db.session.commit()
    return redirect(request.referrer or url_for('catalogos.ver_catalogos'))

@catalogos_bp.route('/eliminar_catalogo/<int:version_id>', methods=['POST'])
def eliminar_catalogo(version_id):
    version = CatalogoVersion.query.get_or_404(version_id)

    # Eliminar prefiniquitos relacionados (y sus detalles)
    from models import Prefiniquito, DetallePrefiniquito

    prefiniquitos = Prefiniquito.query.filter(
        (Prefiniquito.version_original_id == version.id) |
        (Prefiniquito.version_actualizada_id == version.id)
    ).all()

    for pref in prefiniquitos:
        DetallePrefiniquito.query.filter_by(prefiniquito_id=pref.id).delete()
        db.session.delete(pref)

    # Eliminar conceptos del catálogo
    ConceptoCatalogo.query.filter_by(version_id=version.id).delete()

    # Eliminar el catálogo
    db.session.delete(version)
    db.session.commit()

    flash("Catálogo y prefiniquito relacionado eliminados correctamente.", "success")
    return redirect(url_for('catalogos.catalogos_por_contrato', contrato_id=version.contrato_id))