from flask_sqlalchemy import SQLAlchemy
from datetime import date

# Inicializar SQLAlchemy
db = SQLAlchemy()

# ---------- Modelo Cliente ----------
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    razon_social = db.Column(db.String(100), nullable=False)
    rfc = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    telefono = db.Column(db.String(50))
    direccion = db.Column(db.Text)
    facturas = db.relationship('Factura', backref='cliente', lazy=True)
    contratos = db.relationship('Contrato', backref='cliente', lazy=True)

# ---------- Modelo Centro ----------
class Centro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    centro = db.Column(db.String(100), nullable=False)
    codigo_centro = db.Column(db.String(50), nullable=False)
    direccion = db.Column(db.Text)
    telefono = db.Column(db.String(50))
    correo_electronico = db.Column(db.String(100))
    contratos = db.relationship('Contrato', backref='centro', lazy=True)

# ---------- Modelo Empresa ----------
class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

# ---------- Modelo Contrato ----------
class Contrato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    contrato = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    centro_id = db.Column(db.Integer, db.ForeignKey('centro.id'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    monto_sin_iva = db.Column(db.Float)
    iva = db.Column(db.Float)
    monto_total = db.Column(db.Float)
    porcentaje_anticipo = db.Column(db.Float)
    anticipo_sin_iva = db.Column(db.Float, nullable=True)
    iva_anticipo = db.Column(db.Float, nullable=True)
    total_anticipo = db.Column(db.Float, nullable=True)

    anticipo_total = db.Column(db.Float)
    duracion = db.Column(db.Integer)
    estado = db.Column(db.String(20), default='abierto')
    ubicacion_trabajos = db.Column(db.String(255))
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)

    empresa = db.relationship('Empresa', backref='contratos')
    catalogos = db.relationship('CatalogoVersion', backref='contrato', lazy=True)

#----------MODELO DEDUCCIONES CONTRATO--------
class DeduccionContrato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)  # Ejemplo: "Fondo de Garantía"
    porcentaje = db.Column(db.Float, nullable=False)     # Ejemplo: 5.0 para 5%

    contrato = db.relationship('Contrato', backref='deducciones_recurrentes')

# ---------- Modelo Factura ----------
class Factura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa = db.relationship('Empresa', backref='facturas')
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    contrato = db.relationship('Contrato', backref='facturas')
    numero_factura = db.Column(db.String(50), nullable=False)
    fecha_emision = db.Column(db.Date)
    tipo_documento = db.Column(db.String(20))
    uuid = db.Column(db.String(50))
    estado = db.Column(db.String(20))
    cantidad = db.Column(db.Integer)
    precio_unitario = db.Column(db.Float)
    monto_sin_iva = db.Column(db.Float)
    iva = db.Column(db.Float)
    monto_total = db.Column(db.Float)
    total = db.Column(db.Float)
    pagos = db.relationship('Pago', backref='factura', lazy=True)

# ---------- Modelo Pago ----------
class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(db.Integer, db.ForeignKey('factura.id'), nullable=False)
    fecha_pago = db.Column(db.Date)
    monto = db.Column(db.Float)
    metodo_pago = db.Column(db.String(50))
    referencia = db.Column(db.String(100))
    parcialidad = db.Column(db.Integer)
    # ---------- Modelo Partida ----------
class Partida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    numero = db.Column(db.String(20))
    nombre = db.Column(db.String(100))
    conceptos = db.relationship('Concepto', backref='partida', lazy=True)

# ---------- Modelo Concepto ----------
class Concepto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    partida_id = db.Column(db.Integer, db.ForeignKey('partida.id'), nullable=False)
    concepto = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    precio_unitario = db.Column(db.Float)
    cantidad = db.Column(db.Float)
    subtotal = db.Column(db.Float)

# ---------- Modelo Catálogo ----------
class CatalogoVersion(db.Model):
    __tablename__ = 'catalogo_version'

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    tipo = db.Column(db.String(50))  # original o actualizado
    fecha_subida = db.Column(db.Date)
    nombre = db.Column(db.String(100))
    comentario = db.Column(db.Text)

    conceptos = db.relationship('ConceptoCatalogo', backref='version', lazy=True)

    # Relaciones con Prefiniquito
    prefiniquitos_originales = db.relationship(
        'Prefiniquito',
        backref='version_original',
        foreign_keys='Prefiniquito.version_original_id',
        lazy=True
    )

    prefiniquitos_actualizados = db.relationship(
        'Prefiniquito',
        backref='version_actualizada',
        foreign_keys='Prefiniquito.version_actualizada_id',
        lazy=True
    )

# ---------- Conceptos del Catálogo ----------
class ConceptoCatalogo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('catalogo_version.id'), nullable=False)
    partida = db.Column(db.String(100))
    nombre_partida = db.Column(db.String(100))
    clave_concepto = db.Column(db.String(50))  # 👈 Clave única del concepto
    concepto = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    unidad = db.Column(db.String(50))
    precio_unitario = db.Column(db.Float)
    cantidad = db.Column(db.Float)
    subtotal = db.Column(db.Float)
    estatus = db.Column(db.String(10), default='E')  # E = Elaboración, R1/R2... = Revisión, A = Aprobado


    # ========== AVANCES DE OBRA ========== #

class AvanceObra(db.Model):
    __tablename__ = 'avance_obra'

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    numero_version = db.Column(db.Integer, nullable=False)
    version_catalogo_id = db.Column(db.Integer, db.ForeignKey('catalogo_version.id'), nullable=True)

    contrato = db.relationship('Contrato', backref='avances')
    version_catalogo = db.relationship('CatalogoVersion', backref='avances')
    detalles = db.relationship('DetalleAvance', backref='avance', lazy=True)

class DetalleAvance(db.Model):
    __tablename__ = 'detalle_avance'

    id = db.Column(db.Integer, primary_key=True)
    avance_id = db.Column(db.Integer, db.ForeignKey('avance_obra.id'), nullable=False)
    concepto_id = db.Column(db.Integer, db.ForeignKey('concepto_catalogo.id'), nullable=False)
    cantidad_avance = db.Column(db.Float, nullable=False)
    subtotal_avance = db.Column(db.Float, nullable=False)

    concepto = db.relationship('ConceptoCatalogo')


# ========== PREFINIQUITOS ========== #

# Este modelo representa un prefiniquito generado al comparar
# un catálogo original con una versión actualizada de un contrato.
class Prefiniquito(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    version_original_id = db.Column(db.Integer, db.ForeignKey('catalogo_version.id'), nullable=False)
    version_actualizada_id = db.Column(db.Integer, db.ForeignKey('catalogo_version.id'), nullable=False)

    fecha_generacion = db.Column(db.Date, default=date.today, nullable=False)
    total_original = db.Column(db.Float)
    total_actualizado = db.Column(db.Float)
    diferencia_total = db.Column(db.Float)

    contrato = db.relationship('Contrato', backref='prefiniquitos')
    detalles = db.relationship('DetallePrefiniquito', backref='prefiniquito', lazy=True)


# Este modelo representa el detalle por concepto dentro del prefiniquito.
# Se guarda cada concepto comparado, incluyendo aquellos sin cambios.
class DetallePrefiniquito(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    prefiniquito_id = db.Column(db.Integer, db.ForeignKey('prefiniquito.id'), nullable=False)

    concepto_id = db.Column(db.Integer, db.ForeignKey('concepto_catalogo.id'))  # 🔧 Nuevo campo agregado

    partida = db.Column(db.String(20))
    nombre_partida = db.Column(db.String(100))
    clave_concepto = db.Column(db.String(20))
    descripcion = db.Column(db.Text)
    unidad = db.Column(db.String(20))

    precio_unitario_original = db.Column(db.Float)
    cantidad_original = db.Column(db.Float)
    subtotal_original = db.Column(db.Float)

    precio_unitario_actualizado = db.Column(db.Float)
    cantidad_actualizada = db.Column(db.Float)
    subtotal_actualizado = db.Column(db.Float)

    diferencia_cantidad = db.Column(db.Float)
    diferencia_subtotal = db.Column(db.Float)

    tipo_cambio = db.Column(db.String(20))  # "sin cambio", "modificado", "nuevo", "eliminado"

    # ---------- Modelo Tarea para módulo Kanban ----------
class Tarea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(50), nullable=False, default='Pendiente')
    fecha_creacion = db.Column(db.Date, default=date.today)
    prioridad = db.Column(db.String(20), default='Media')

    # ===================== MODELOS PARA ESTIMACIONES =====================

# ---------- Modelo de Estimación ----------
class Estimacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID único de la estimación

    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)  # FK al contrato
    contrato = db.relationship('Contrato', backref='estimaciones')  # Relación con el modelo Contrato

    fecha = db.Column(db.Date, nullable=True)  # Fecha de emisión de la estimación
    folio = db.Column(db.String(50), nullable=True)  # Número de folio o referencia
    comentario = db.Column(db.Text)  # Comentario adicional

    # Fechas del periodo de trabajos de la estimación
    fecha_inicio_trab_est = db.Column(db.Date, nullable=True)  # Inicio de trabajos
    fecha_fin_trab_est = db.Column(db.Date, nullable=True)  # Fin de trabajos

    # Datos financieros
    subtotal = db.Column(db.Float, default=0.0)  # Total antes de IVA
    iva = db.Column(db.Float, default=0.0)  # IVA calculado (16%)
    total_con_iva = db.Column(db.Float, default=0.0)  # Total con IVA incluido
    amortizacion = db.Column(db.Float, default=0.0)  # Descuento aplicado por anticipo

    # Datos del contrato
    nombre_contrato = db.Column(db.String(255))  # Nombre completo del contrato
    clave_contrato = db.Column(db.String(100))  # Clave o abreviatura del contrato

    # Relación con el detalle de la estimación
    detalles = db.relationship('DetalleEstimacion', backref='estimacion', lazy=True)

    # En el modelo Estimacion
    numero_estimacion = db.Column(db.Integer)

# Detalle por cada concepto dentro de la estimación
class DetalleEstimacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    estimacion_id = db.Column(db.Integer, db.ForeignKey('estimacion.id'), nullable=False)
    partida_id = db.Column(db.Integer, db.ForeignKey('partida.id'), nullable=False)  # NUEVO CAMPO
    clave_concepto = db.Column(db.String(20), nullable=False)
    nombre_partida = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    unidad = db.Column(db.String(20), nullable=False)
    cantidad_estimacion = db.Column(db.Float, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    partida = db.relationship('Partida')  # RELACIÓN PARA ACCESO FÁCIL (opcional)

  
    # ===================== MODELOS DE CONTROL DE EXTRAORDINARIOS =====================

class AprobacionConcepto(db.Model):
    __tablename__ = 'aprobacion_concepto'

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    clave_concepto = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), default='elaboracion')  # E, R1, R2, A
    precio_unitario = db.Column(db.Float, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    nombre_archivo_pdf = db.Column(db.String(255), nullable=True)  # PDF descriptivo base
    comentario = db.Column(db.Text, nullable=True)

    contrato = db.relationship('Contrato', backref='aprobaciones')
    revisiones = db.relationship('RevisionConcepto', back_populates='aprobacion', cascade='all, delete-orphan')


class RevisionConcepto(db.Model):
    __tablename__ = 'revision_concepto'

    id = db.Column(db.Integer, primary_key=True)
    aprobacion_id = db.Column(db.Integer, db.ForeignKey('aprobacion_concepto.id'), nullable=False)
    numero_revision = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)  # Descripción del concepto en esa revisión
    comentario = db.Column(db.Text, nullable=True)
    archivo_pdf = db.Column(db.String(255), nullable=True)
    acuse_pdf = db.Column(db.String(255), nullable=True)
    estado = db.Column(db.String(2), nullable=False, default='E')  # E, R, A
    fecha_registro = db.Column(db.Date, default=date.today)

    # ✅ Nuevo campo para guardar el PU que tenía este concepto al momento de la revisión
    precio_unitario = db.Column(db.Float, nullable=True)

    aprobacion = db.relationship('AprobacionConcepto', back_populates='revisiones')

# ========== HISTORIAL DE IMPORTES POR PARTIDA EN ESTIMACIONES ==========
class ImportePartidaEstimacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID único del registro

    estimacion_id = db.Column(db.Integer, db.ForeignKey('estimacion.id'), nullable=False)
    estimacion = db.relationship('Estimacion', backref='importes_partidas')  # Relación con estimación

    partida_id = db.Column(db.Integer, db.ForeignKey('partida.id'), nullable=False)  # NUEVO CAMPO
    numero_partida = db.Column(db.String(20), nullable=False)  # Clave de la partida (ej: 1, P01)
    nombre_partida = db.Column(db.String(255), nullable=False)  # Nombre descriptivo de la partida

    importe_original = db.Column(db.Float, nullable=False, default=0.0)  # Total del contrato original
    importe_estimacion = db.Column(db.Float, nullable=False, default=0.0)  # Esta estimación
    importe_anterior = db.Column(db.Float, nullable=False, default=0.0)  # Estimaciones previas
    importe_acumulado = db.Column(db.Float, nullable=False, default=0.0)  # Total acumulado

    partida = db.relationship('Partida')  # RELACIÓN PARA ACCESO FÁCIL (opcional)

# ========== CATÁLOGO BASE ACUMULADO ==========
class CatalogoBaseAcumulado(db.Model):
    __tablename__ = 'catalogo_base_acumulado'

    id = db.Column(db.Integer, primary_key=True)

    # Relación con contrato
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)

    # Fecha en que se generó esta versión del catálogo acumulado
    fecha_generacion = db.Column(db.Date, default=date.today)

    # Número de versión incremental por contrato (1, 2, 3…)
    version = db.Column(db.Integer)

    # Hash SHA-256 del contenido para detectar duplicados o cambios
    hash_contenido = db.Column(db.String(64))

    # ✅ Contenido del catálogo acumulado como JSON serializado
    conceptos_json = db.Column(db.Text, nullable=False)

    # Relación inversa para acceso desde el contrato
    contrato = db.relationship('Contrato', backref='catalogos_base_acumulados')

    #----estatus concepto extraordinario E R1 R2 etc----
class EstatusConcepto(db.Model):
    __tablename__ = 'estatus_concepto'

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    clave_concepto = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    tipo_evento = db.Column(db.String(20), nullable=False)  # 'elaboracion', 'revision', etc.
    descripcion = db.Column(db.Text, nullable=True)
    archivo_pdf = db.Column(db.String(200), nullable=True)
    archivo_acuse = db.Column(db.String(200), nullable=True)
    precio_unitario = db.Column(db.Float, nullable=False)

    contrato = db.relationship('Contrato', backref='estatus_conceptos')

    class DeduccionEstimacion(db.Model):
     id = db.Column(db.Integer, primary_key=True)
     estimacion_id = db.Column(db.Integer, db.ForeignKey('estimacion.id'), nullable=False)
     nombre = db.Column(db.String(100), nullable=False)
     tipo = db.Column(db.String(20))  # 'recurrente' o 'manual'
     porcentaje = db.Column(db.Float, nullable=True)  # solo si aplica
     monto = db.Column(db.Float, nullable=False)
     fecha = db.Column(db.Date, default=date.today)

     estimacion = db.relationship('Estimacion', backref='deducciones')