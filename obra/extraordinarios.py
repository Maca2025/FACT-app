from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Contrato, AprobacionConcepto, RevisionConcepto, ConceptoCatalogo
from services.catalogo_base import generar_catalogo_base
from datetime import date, datetime
import os

extraordinarios_bp = Blueprint('extraordinarios', __name__, url_prefix='/extraordinarios', template_folder='../templates')
estimaciones_nuevo_bp = Blueprint('estimaciones_nuevo', __name__, template_folder='templates')

# -------- Vista principal: listado de extraordinarios --------
@extraordinarios_bp.route('/<int:contrato_id>')
def listado_extraordinarios(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    conceptos = generar_catalogo_base(contrato_id)

    extraordinarios = []

    for c in conceptos:
        clave = c.get('clave') or c.get('clave_concepto')

        if isinstance(clave, str) and clave.lower().startswith('e'):
            aprobacion = AprobacionConcepto.query.filter_by(
                contrato_id=contrato_id,
                clave_concepto=clave
            ).first()

            if aprobacion:
                revisiones = RevisionConcepto.query.filter_by(aprobacion_id=aprobacion.id).count()

                if aprobacion.estado != 'aprobado' and revisiones > 0:
                    estado = 'revision'
                else:
                    estado = aprobacion.estado

                comentario = aprobacion.comentario
                pu = aprobacion.precio_unitario or c['precio_unitario']
            else:
                estado = 'elaboracion'
                comentario = ''
                pu = c['precio_unitario']
                revisiones = 0

            extraordinarios.append({
                'clave': clave,
                'descripcion': c['descripcion'],
                'precio_unitario': pu,
                'estado': estado,
                'comentario': comentario,
                'revisiones': revisiones
            })

    return render_template('extraordinarios/listado_extraordinarios.html',
                           contrato=contrato,
                           extraordinarios=extraordinarios)

# -------- Ruta para nuevo registro de revisión en página separada --------
# -------- Ruta para nuevo registro de revisión en página separada --------
@extraordinarios_bp.route('/<int:contrato_id>/<clave>/nuevo', methods=['GET', 'POST'])
def nuevo_reg_extra(contrato_id, clave):
    from werkzeug.utils import secure_filename

    contrato = Contrato.query.get_or_404(contrato_id)

    aprobacion = AprobacionConcepto.query.filter_by(
        contrato_id=contrato_id,
        clave_concepto=clave
    ).first()

    if not aprobacion:
        aprobacion = AprobacionConcepto(
            contrato_id=contrato_id,
            clave_concepto=clave,
            estado='elaboracion'
        )
        db.session.add(aprobacion)
        db.session.commit()

    ultima_revision = RevisionConcepto.query.filter_by(aprobacion_id=aprobacion.id)
    ultima_revision = ultima_revision.order_by(RevisionConcepto.numero_revision.desc()).first()

    ultimo_pu = ultima_revision.precio_unitario if ultima_revision else aprobacion.precio_unitario or ''

    descripcion_existente = (ultima_revision.descripcion if ultima_revision and ultima_revision.descripcion
                             else aprobacion.descripcion)

    if request.method == 'POST':
        fecha_str = request.form.get('fecha') or date.today().strftime('%Y-%m-%d')
        precio_unitario = float(request.form.get('precio_unitario'))
        comentario = request.form.get('comentario')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado') or aprobacion.estado

        archivo_pdf = request.files.get('archivo_pdf')
        acuse_pdf = request.files.get('acuse_pdf')

        ruta_base = os.path.join('static', 'uploads', 'extraordinarios')
        os.makedirs(ruta_base, exist_ok=True)

        archivo_pdf_nombre = None
        if archivo_pdf and archivo_pdf.filename.endswith('.pdf'):
            archivo_pdf_nombre = f"{clave}_desc_{date.today()}_{int(datetime.now().timestamp())}.pdf"
            archivo_pdf.save(os.path.join(ruta_base, secure_filename(archivo_pdf_nombre)))

        acuse_pdf_nombre = None
        if acuse_pdf and acuse_pdf.filename.endswith('.pdf'):
            acuse_pdf_nombre = f"{clave}_acuse_{date.today()}_{int(datetime.now().timestamp())}.pdf"
            acuse_pdf.save(os.path.join(ruta_base, secure_filename(acuse_pdf_nombre)))

        num = RevisionConcepto.query.filter_by(aprobacion_id=aprobacion.id).count() + 1
        revision = RevisionConcepto(
            aprobacion_id=aprobacion.id,
            numero_revision=num,
            fecha_registro=datetime.strptime(fecha_str, '%Y-%m-%d'),
            precio_unitario=precio_unitario,
            comentario=comentario,
            descripcion=descripcion,
            estado=estado,
            archivo_pdf=archivo_pdf_nombre,
            acuse_pdf=acuse_pdf_nombre
        )
        db.session.add(revision)

        # ✅ Siempre actualizamos PU y estado, pero solo actualizamos comentario y descripción si no es A
        aprobacion.precio_unitario = precio_unitario
        aprobacion.estado = estado

        if estado != 'aprobado':
            aprobacion.comentario = comentario
            aprobacion.descripcion = descripcion

        if archivo_pdf_nombre:
            aprobacion.nombre_archivo_pdf = archivo_pdf_nombre

        concepto = ConceptoCatalogo.query.filter_by(clave_concepto=clave)\
            .order_by(ConceptoCatalogo.id.desc()).first()

        if concepto:
            if estado == 'revision':
                conteo = RevisionConcepto.query.filter_by(aprobacion_id=aprobacion.id, estado='revision').count()
                concepto.estatus = f'R{conteo}'
            elif estado == 'aprobado':
                concepto.estatus = 'A'
            else:
                concepto.estatus = 'E'
            db.session.add(concepto)

        db.session.commit()

        return redirect(url_for('extraordinarios.historial_revisiones', contrato_id=contrato_id, clave=clave))

    return render_template('extraordinarios/nuevo_reg_extra.html',
                           contrato=contrato,
                           clave=clave,
                           ultimo_pu=ultimo_pu,
                           estado_actual=aprobacion.estado,
                           descripcion=descripcion_existente or '')

# -------- Vista de historial de revisiones --------
@extraordinarios_bp.route('/revisiones/<int:contrato_id>/<path:clave>')
def historial_revisiones(contrato_id, clave):
    from types import SimpleNamespace

    aprobacion = AprobacionConcepto.query.filter_by(
        contrato_id=contrato_id,
        clave_concepto=clave
    ).first()

    if not aprobacion:
        return f"No se encontró aprobación para clave {clave} en contrato {contrato_id}", 404

    revisiones = RevisionConcepto.query.filter_by(
        aprobacion_id=aprobacion.id
    ).order_by(RevisionConcepto.numero_revision).all()

    revision_0 = SimpleNamespace(
        id=None,
        numero_revision=0,
        fecha_registro=getattr(aprobacion, 'fecha_creacion', date.today()),
        precio_unitario=aprobacion.precio_unitario or 0,
        comentario=aprobacion.comentario or '—',
        descripcion=aprobacion.descripcion or '',
        estado='elaboracion',
        archivo_pdf=None,
        acuse_pdf=None
    )

    revisiones_con_0 = [revision_0] + revisiones

    return render_template('extraordinarios/historial_revisiones.html',
                           contrato_id=contrato_id,
                           clave=clave,
                           revisiones=revisiones_con_0)

# -------- Ruta para subir PDF de acuse para una revisión existente --------
@extraordinarios_bp.route('/<int:contrato_id>/<clave>/acuse/<int:revision_id>', methods=['GET', 'POST'])
def subir_acuse_revision(contrato_id, clave, revision_id):
    from werkzeug.utils import secure_filename

    revision = RevisionConcepto.query.get_or_404(revision_id)
    ruta_base = os.path.join('static', 'uploads', 'extraordinarios')
    os.makedirs(ruta_base, exist_ok=True)

    if request.method == 'POST':
        acuse_pdf = request.files.get('acuse_pdf')
        if acuse_pdf and acuse_pdf.filename.endswith('.pdf'):
            acuse_pdf_nombre = f"{clave}_acuse_{date.today()}_{int(datetime.now().timestamp())}.pdf"
            acuse_pdf_path = os.path.join(ruta_base, secure_filename(acuse_pdf_nombre))
            acuse_pdf.save(acuse_pdf_path)

            revision.acuse_pdf = acuse_pdf_nombre
            db.session.commit()

            flash("Archivo de acuse guardado correctamente.", "success")
            return redirect(url_for('extraordinarios.historial_revisiones', contrato_id=contrato_id, clave=clave))
        else:
            flash("Archivo inválido o no seleccionado.", "danger")

    return render_template('extraordinarios/subir_acuse_revision.html',
                           contrato_id=contrato_id,
                           clave=clave,
                           revision_id=revision_id,
                           revision=revision)


@extraordinarios_bp.route('/<int:contrato_id>/<clave>/descripcion/<int:revision_id>', methods=['GET', 'POST'])
def subir_pdf_revision(contrato_id, clave, revision_id):
    from werkzeug.utils import secure_filename

    revision = RevisionConcepto.query.get_or_404(revision_id)
    ruta_base = os.path.join('static', 'uploads', 'extraordinarios')
    os.makedirs(ruta_base, exist_ok=True)

    if request.method == 'POST':
        archivo_pdf = request.files.get('archivo_pdf')
        if archivo_pdf and archivo_pdf.filename.endswith('.pdf'):
            pdf_nombre = f"{clave}_desc_{date.today()}_{int(datetime.now().timestamp())}.pdf"
            pdf_path = os.path.join(ruta_base, secure_filename(pdf_nombre))
            archivo_pdf.save(pdf_path)

            revision.archivo_pdf = pdf_nombre
            db.session.commit()

            flash("Archivo de descripción guardado correctamente.", "success")
            return redirect(url_for('extraordinarios.historial_revisiones', contrato_id=contrato_id, clave=clave))
        else:
            flash("Archivo inválido o no seleccionado.", "danger")

    return render_template('extraordinarios/subir_pdf_revision.html',
                           contrato_id=contrato_id,
                           clave=clave,
                           revision_id=revision_id,
                           revision=revision)

@estimaciones_nuevo_bp.route('/estimacion/<int:estimacion_id>/editar_conceptos', methods=['GET'])
def editar_conceptos_estimacion(estimacion_id):
    from models import Estimacion, DetalleEstimacion

    estimacion = Estimacion.query.get_or_404(estimacion_id)
    detalles = DetalleEstimacion.query.filter_by(estimacion_id=estimacion_id).all()

    conceptos = []
    for d in detalles:
        conceptos.append({
            'clave': d.clave_concepto,
            'descripcion': d.descripcion,
            'unidad': d.unidad,
            'precio_unitario': d.precio_unitario,
            'cantidad_estimacion': d.cantidad_estimacion,
            'subtotal': d.subtotal
        })

    return render_template('estimaciones_nuevo/editar_conceptos.html',
                           estimacion=estimacion,
                           contrato=estimacion.contrato,
                           conceptos=conceptos)