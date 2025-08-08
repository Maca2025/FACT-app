from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Factura, Cliente, Empresa, Contrato

from datetime import date

facturas_bp = Blueprint('facturas', __name__, template_folder='../templates')

@facturas_bp.route('/facturas', methods=['GET', 'POST'])
def facturas():
    clientes = Cliente.query.all()
    empresas = Empresa.query.all()
    empresa_id = request.args.get('empresa_id', type=int)

    if request.method == 'POST':
        empresa_id = int(request.form['empresa_id'])
        empresa = Empresa.query.get(empresa_id)

        # Prefijo por empresa
        if empresa.nombre == 'Terminus':
            prefijo = 'T-'
        elif empresa.nombre == 'Laprida':
            prefijo = 'L-'
        else:
            prefijo = 'X-'

        facturas_prefijo = Factura.query.filter(
            Factura.empresa_id == empresa_id,
            Factura.numero_factura.like(f"{prefijo}%")
        ).all()

        numeros_existentes = []
        for f in facturas_prefijo:
            try:
                numero = int(f.numero_factura.replace(prefijo, ''))
                numeros_existentes.append(numero)
            except ValueError:
                continue

        siguiente_num = max(numeros_existentes) + 1 if numeros_existentes else 1
        numero_factura = f"{prefijo}{siguiente_num:03d}"

        contrato = Contrato.query.get(int(request.form['contrato_id']))
        subtotal = float(request.form['monto_sin_iva'] or 0)
        iva = float(request.form['iva'] or round(subtotal * 0.16, 2))
        monto_total = float(request.form['monto_total'] or subtotal + iva)

        nueva_factura = Factura(
            empresa_id=empresa_id,
            cliente_id=int(request.form['cliente_id']),
            contrato_id=int(request.form['contrato_id']),
            numero_factura=numero_factura,
            fecha_emision=date.fromisoformat(request.form['fecha_emision']),
            tipo_documento=request.form['tipo_documento'],
            uuid=request.form['uuid'],
            estado=request.form['estado'],
            monto_sin_iva=subtotal,
            iva=iva,
            monto_total=monto_total,
            total=monto_total
        )
        db.session.add(nueva_factura)
        db.session.commit()
        return redirect(url_for('facturas.facturas'))

    contratos = Contrato.query.filter_by(empresa_id=empresa_id).all() if empresa_id else Contrato.query.all()

    if empresa_id:
        empresa = Empresa.query.get(empresa_id)
        if empresa:
            if empresa.nombre == 'Terminus':
                prefijo = 'T-'
            elif empresa.nombre == 'Laprida':
                prefijo = 'L-'
            else:
                prefijo = 'X-'

            facturas_prefijo = Factura.query.filter(
                Factura.empresa_id == empresa_id,
                Factura.numero_factura.like(f"{prefijo}%")
            ).all()

            numeros_existentes = []
            for f in facturas_prefijo:
                try:
                    numero = int(f.numero_factura.replace(prefijo, ''))
                    numeros_existentes.append(numero)
                except ValueError:
                    continue

            siguiente_numero = f"{prefijo}{(max(numeros_existentes) + 1) if numeros_existentes else 1:03d}"
        else:
            siguiente_numero = "001"
    else:
        siguiente_numero = "001"

    contratos_serializados = [
        {
            'id': c.id,
            'nombre': c.nombre,
            'cliente': c.cliente.nombre,
            'monto_sin_iva': c.monto_sin_iva,
            'iva': c.iva,
            'monto_total': c.monto_total,
            'empresa_id': c.empresa_id
        }
        for c in contratos
    ]

    facturas = Factura.query.filter_by(empresa_id=empresa_id).all() if empresa_id else Factura.query.all()

    return render_template(
        'facturacion/facturas.html',
        facturas=facturas,
        clientes=clientes,
        contratos=contratos,
        contratos_serializados=contratos_serializados,
        empresas=empresas,
        siguiente_numero=siguiente_numero
    )