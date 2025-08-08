from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Centro

centros_bp = Blueprint('centros', __name__, template_folder='../templates')

@centros_bp.route('/centros', methods=['GET', 'POST'])
def centros():
    if request.method == 'POST':
        nuevo_centro = Centro(
            centro=request.form['centro'],
            codigo_centro=request.form['codigo_centro'],
            direccion=request.form['direccion'],
            telefono=request.form['telefono'],
            correo_electronico=request.form['correo_electronico']
        )
        db.session.add(nuevo_centro)
        db.session.commit()
        return redirect(url_for('centros.centros'))

    centros = Centro.query.all()
    return render_template('facturacion/centros.html', centros=centros)