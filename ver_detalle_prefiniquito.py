# ver_detalle_prefiniquito.py

from app import app
from models import Prefiniquito, DetallePrefiniquito

with app.app_context():
    pref = Prefiniquito.query.get(3)

    if not pref:
        print("❌ Prefiniquito no encontrado.")
    else:
        print(f"\n📄 Prefiniquito ID {pref.id}")
        print(f"Total Original: {pref.total_original}")
        print(f"Total Actualizado: {pref.total_actualizado}")
        print(f"Diferencia Total: {pref.diferencia_total}")
        print("\n📋 Detalles:")

        detalles = DetallePrefiniquito.query.filter_by(prefiniquito_id=pref.id).all()
        for d in detalles:
            print(f"- Clave: {d.clave_concepto} | Desc: {d.descripcion} | "
                  f"Original: {d.subtotal_original} | Actualizado: {d.subtotal_actualizado} | "
                  f"Diferencia: {d.diferencia_subtotal} | Tipo: {d.tipo_cambio}")