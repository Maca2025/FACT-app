# ============================================================
# FACT-app - Sistema de Facturación y Admin de Obra
# Autor: Macarena Mendoza
# Descripción: Aplicación Flask con múltiples empresas, contratos,
#              facturas, pagos y catálogos de conceptos.
# ============================================================

# ======================= IMPORTACIONES =======================

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from datetime import date
import os
import pandas as pd
import locale

from models import (
    db, Cliente, Centro, Empresa, Contrato, Factura, Pago,
    Partida, Concepto, CatalogoVersion, ConceptoCatalogo,
    AvanceObra, DetalleAvance
)

from base.clientes import clientes_bp
from base.contratos import contratos_bp
from base.facturas import facturas_bp
from base.pagos import pagos_bp
from base.centros import centros_bp
from base.reportesfact import reportesfact_bp

from obra.catalogos import catalogos_bp
from obra.contratos import contratos_obra_bp
from obra.avances import avances_bp
from obra.comparativos import comparativos_bp
from obra.prefiniquitos import prefiniquitos_bp
from desarrollo.kanban import kanban_bp
from obra.extraordinarios import extraordinarios_bp
from obra.estimaciones_nuevo import estimaciones_nuevo_bp


# ======================= CONFIGURACIÓN =======================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-fact'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'fact.db')}"

db.init_app(app)
migrate = Migrate(app, db)

# ======================= BLUEPRINTS =======================

app.register_blueprint(clientes_bp)
app.register_blueprint(contratos_bp)
app.register_blueprint(facturas_bp)
app.register_blueprint(pagos_bp)
app.register_blueprint(centros_bp)
app.register_blueprint(reportesfact_bp)
app.register_blueprint(catalogos_bp)
app.register_blueprint(contratos_obra_bp)
app.register_blueprint(avances_bp)
app.register_blueprint(comparativos_bp)
app.register_blueprint(kanban_bp, url_prefix='/kanban')
app.register_blueprint(prefiniquitos_bp)
app.register_blueprint(extraordinarios_bp)
app.register_blueprint(estimaciones_nuevo_bp)


# ======================= RUTAS =======================

@app.route('/')
def index():
    contratos = Contrato.query.order_by(Contrato.empresa_id, Contrato.nombre).all()
    
    contratos_por_empresa = {}
    for contrato in contratos:
        empresa = contrato.empresa.nombre
        if empresa not in contratos_por_empresa:
            contratos_por_empresa[empresa] = []
        contratos_por_empresa[empresa].append(contrato)

    return render_template('index.html', contratos_por_empresa=contratos_por_empresa)


@app.route('/api/siguiente_numero')
def api_siguiente_numero():
    empresa_id = request.args.get('empresa_id', type=int)
    if not empresa_id:
        return {'siguiente_numero': "1"}

    empresa = Empresa.query.get(empresa_id)
    if not empresa:
        return {'siguiente_numero': "1"}

    prefijo = {
        'Terminus': 'T-',
        'Laprida': 'L-'
    }.get(empresa.nombre, 'X-')

    ultima_factura = Factura.query \
        .filter(Factura.empresa_id == empresa_id, Factura.numero_factura.like(f"{prefijo}%")) \
        .order_by(Factura.id.desc()) \
        .first()

    if ultima_factura:
        try:
            ultimo_num = int(ultima_factura.numero_factura.replace(prefijo, ''))
            siguiente_num = f"{prefijo}{ultimo_num + 1:03d}"
        except ValueError:
            siguiente_num = f"{prefijo}001"
    else:
        siguiente_num = f"{prefijo}001"

    return {'siguiente_numero': siguiente_num}


@app.route('/rutas')
def listar_rutas():
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        route = f"{rule.rule:50s} [{methods}] → {rule.endpoint}"
        output.append(route)
    return "<pre>" + "\n".join(sorted(output)) + "</pre>"

# ======================= FILTROS =======================

# Establecer configuración regional para moneda mexicana
try:
    locale.setlocale(locale.LC_ALL, 'es_MX.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')  # fallback

@app.template_filter('moneda')
def moneda(value):
    try:
        return locale.currency(value, grouping=True)
    except Exception:
        return "${:,.2f}".format(value)

# ======================= INICIAR LA APLICACIÓN =======================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Empresa.query.filter_by(nombre="Terminus").first():
            db.session.add(Empresa(nombre="Terminus"))
        if not Empresa.query.filter_by(nombre="Laprida").first():
            db.session.add(Empresa(nombre="Laprida"))
        db.session.commit()
        print("✅ Empresas cargadas correctamente")

    app.run(debug=True, host='127.0.0.1', port=5055)