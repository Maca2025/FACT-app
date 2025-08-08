from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import db, Tarea

kanban_bp = Blueprint('kanban', __name__, url_prefix='/kanban', template_folder='templates')

@kanban_bp.route('/', endpoint='tablero_kanban')
def tablero_kanban():
    prioridad = request.args.get('prioridad')

    tareas = Tarea.query.all()
    if prioridad:
        tareas = [t for t in tareas if t.prioridad == prioridad]

    pendientes = [t for t in tareas if t.estado == 'Pendiente']
    en_proceso = [t for t in tareas if t.estado == 'En proceso']
    completadas = [t for t in tareas if t.estado == 'Completado']

    return render_template('kanban/tablero.html',
                           pendientes=pendientes,
                           en_proceso=en_proceso,
                           completadas=completadas,
                           prioridad=prioridad)

@kanban_bp.route('/nueva', methods=['GET', 'POST'])
def nueva_tarea():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        estado = request.form['estado']
        prioridad = request.form['prioridad']

        nueva = Tarea(titulo=titulo, descripcion=descripcion, estado=estado, prioridad=prioridad)
        db.session.add(nueva)
        db.session.commit()
        return redirect(url_for('kanban.tablero_kanban'))

    return render_template('kanban/nueva_tarea.html')

@kanban_bp.route('/cambiar_estado/<int:tarea_id>', methods=['POST'])
def cambiar_estado(tarea_id):
    nueva_etapa = request.form['nuevo_estado']
    tarea = Tarea.query.get_or_404(tarea_id)
    tarea.estado = nueva_etapa
    db.session.commit()
    return redirect(url_for('kanban.tablero_kanban'))

@kanban_bp.route('/eliminar/<int:tarea_id>', methods=['POST'])
def eliminar_tarea(tarea_id):
    tarea = Tarea.query.get_or_404(tarea_id)
    db.session.delete(tarea)
    db.session.commit()
    return redirect(url_for('kanban.tablero_kanban'))

@kanban_bp.route('/arrastrar/<int:tarea_id>', methods=['POST'])
def arrastrar_tarea(tarea_id):
    data = request.get_json()
    nuevo_estado = data.get('nuevo_estado')
    tarea = Tarea.query.get_or_404(tarea_id)
    tarea.estado = nuevo_estado
    db.session.commit()
    return jsonify({'success': True})

@kanban_bp.route('/lista')
def lista_tareas():
    filtro_estado = request.args.get('estado')
    filtro_prioridad = request.args.get('prioridad')

    query = Tarea.query

    if filtro_estado:
        query = query.filter_by(estado=filtro_estado)
    if filtro_prioridad:
        query = query.filter_by(prioridad=filtro_prioridad)

    tareas = query.order_by(Tarea.fecha_creacion.desc()).all()
    return render_template('kanban/lista_tareas.html',
                           tareas=tareas,
                           filtro_estado=filtro_estado,
                           filtro_prioridad=filtro_prioridad)