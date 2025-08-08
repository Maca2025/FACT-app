from app import app
from services.prefiniquitos import generar_prefiniquito

with app.app_context():
    nuevo_id = generar_prefiniquito(
        contrato_id=1,
        version_original_id=1,
        version_actualizada_id=2
    )
    print(f"\n✅ Prefiniquito generado con ID: {nuevo_id}")