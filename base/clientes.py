from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Cliente

clientes_bp = Blueprint('clientes', __name__, template_folder='../templates')

@clientes_bp.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if request.method == 'POST':
        nuevo_cliente = Cliente(
            nombre=request.form['nombre'],
            razon_social=request.form['razon_social'],
            rfc=request.form['rfc'],
            email=request.form['email'],
            telefono=request.form['telefono'],
            direccion=request.form['direccion']
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return redirect(url_for('clientes.clientes'))

    clientes = Cliente.query.all()
    return render_template('facturacion/clientes.html', clientes=clientes)