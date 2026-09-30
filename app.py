from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os
import sys
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración de directorios para que funcione al convertirlo a .exe
if getattr(sys, 'frozen', False):
    # Si se está ejecutando como un .exe empaquetado
    base_dir = sys._MEIPASS
    db_dir = os.path.dirname(sys.executable)
else:
    # Si se ejecuta como un script de python normal
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = base_dir

if os.getenv('RAILWAY_VOLUME_MOUNT_PATH'):
    db_dir = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')

template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
db_path = os.path.join(db_dir, 'hotel_tienda.db')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'super_secret_key_villa_zaragoza'

import time
# Variable global para trackear la última actualización (útil para el tiempo real)
app.config['LAST_UPDATE'] = time.time()

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Crear tabla de habitaciones
    c.execute('''
        CREATE TABLE IF NOT EXISTS habitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            estado TEXT NOT NULL,
            seccion TEXT DEFAULT 'Torre'
        )
    ''')
    
    try:
        c.execute("ALTER TABLE habitaciones ADD COLUMN seccion TEXT DEFAULT 'Torre'")
        c.execute("UPDATE habitaciones SET seccion = 'Casona' WHERE numero LIKE 'C%'")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE habitaciones ADD COLUMN acomodacion TEXT DEFAULT 'Pareja'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE habitaciones ADD COLUMN cliente_nombre TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE habitaciones ADD COLUMN personas INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # Crear tabla de pasadias
    c.execute('''
        CREATE TABLE IF NOT EXISTS pasadias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT DEFAULT 'Pasadía',
            personas INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Activo',
            precio_persona REAL DEFAULT 0,
            cumpleanero INTEGER DEFAULT 0,
            total REAL DEFAULT 0,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN precio_persona REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN cumpleanero INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN total REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN tipo TEXT DEFAULT 'Pasadía'")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN metodo_pago TEXT DEFAULT 'Efectivo'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN cuenta_id TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN ninos INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN precio_nino REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # Crear tabla de productos de tienda
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT DEFAULT 'General',
            precio REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')
    
    # Intentar agregar la columna de categoría si la base de datos ya existía
    try:
        c.execute("ALTER TABLE productos ADD COLUMN categoria TEXT DEFAULT 'General'")
    except sqlite3.OperationalError:
        pass # La columna ya existe
    
    # NUEVA TABLA: Para registrar las ventas
    c.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id TEXT,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            total REAL NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(producto_id) REFERENCES productos(id)
        )
    ''')
    
    # Intentar agregar la columna cuenta_id si la tabla ventas ya existía
    try:
        c.execute("ALTER TABLE ventas ADD COLUMN cuenta_id TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE ventas ADD COLUMN metodo_pago TEXT DEFAULT 'Efectivo'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE pasadias ADD COLUMN metodo_pago TEXT DEFAULT 'Efectivo'")
    except sqlite3.OperationalError:
        pass
    
    # Crear tabla de usuarios (empleados/admin)
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    ''')

    # Crear tabla de configuracion para tiempo real
    c.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')
    c.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('last_update', '0')")
    
    # Crear tabla de clientes
    c.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cedula TEXT UNIQUE NOT NULL,
            telefono TEXT,
            correo TEXT
        )
    ''')
    
    # Crear tabla de base de caja
    c.execute('''
        CREATE TABLE IF NOT EXISTS base_caja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monto REAL NOT NULL,
            usuario_id INTEGER,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear tabla de gastos
    c.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            monto REAL NOT NULL,
            usuario_id INTEGER,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Crear tabla de turnos
    c.execute('''
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            base_caja REAL NOT NULL,
            fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_fin TIMESTAMP,
            estado TEXT DEFAULT 'Abierto'
        )
    ''')

    # Crear tabla de reservas
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_nombre TEXT NOT NULL,
            personas INTEGER NOT NULL,
            abono REAL DEFAULT 0,
            precio_total REAL NOT NULL,
            fecha_hora_evento TIMESTAMP NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            metodo_pago TEXT DEFAULT 'Efectivo',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Crear tabla de reservas_habitaciones
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservas_habitaciones (
            reserva_id INTEGER NOT NULL,
            habitacion_id INTEGER NOT NULL,
            FOREIGN KEY(reserva_id) REFERENCES reservas(id),
            FOREIGN KEY(habitacion_id) REFERENCES habitaciones(id)
        )
    ''')
    
    # Crear usuario administrador por defecto si no existe ninguno
    c.execute('SELECT COUNT(*) FROM usuarios')
    if c.fetchone()[0] == 0:
        default_password = generate_password_hash('admin')
        c.execute("INSERT INTO usuarios (cedula, nombre, password, rol) VALUES ('123456', 'Administrador', ?, 'Administrador')", (default_password,))
        
    # Inicializar algunas habitaciones si la tabla está vacía
    c.execute('SELECT COUNT(*) FROM habitaciones')
    if c.fetchone()[0] == 0:
        habitaciones_iniciales = [
            ('101', 'Disponible'), ('102', 'Disponible'), 
            ('201', 'Disponible'), ('202', 'En Uso')
        ]
        c.executemany('INSERT INTO habitaciones (numero, estado) VALUES (?, ?)', habitaciones_iniciales)
        
    c.execute("SELECT 1 FROM habitaciones WHERE numero='Restaurante'")
    if not c.fetchone():
        c.execute("INSERT INTO habitaciones (numero, seccion, estado, acomodacion) VALUES ('Restaurante', 'Áreas Comunes', 'Libre', 'Múltiple')")

    c.execute("SELECT 1 FROM habitaciones WHERE numero='Salón Social'")
    if not c.fetchone():
        c.execute("INSERT INTO habitaciones (numero, seccion, estado, acomodacion) VALUES ('Salón Social', 'Áreas Comunes', 'Libre', 'Múltiple')")
        
    conn.commit()
    conn.close()

init_db()
@app.route('/api/status')
def api_status():
    conn = get_db_connection()
    res = conn.execute("SELECT valor FROM configuracion WHERE clave = 'last_update'").fetchone()
    conn.close()
    last = float(res['valor']) if res else 0
    return jsonify({"last_update": last})

def parse_monto(val):
    if not val:
        return 0.0
    return float(str(val).replace('.', ''))


@app.before_request
def require_login():
    # Actualizar el timestamp global en BD si es una mutación (POST)
    if request.method == 'POST':
        conn = get_db_connection()
        conn.execute("UPDATE configuracion SET valor = ? WHERE clave = 'last_update'", (str(time.time()),))
        conn.commit()
        conn.close()
        
    # Rutas permitidas sin login
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'usuario_id' not in session:
        return redirect(url_for('login'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('usuario_rol') != 'Administrador':
            flash('Acceso denegado. Se requieren permisos de Administrador.')
            return redirect(url_for('hotel'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('hotel'))

# --- FUNCIONES DE AUTENTICACIÓN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cedula = request.form['cedula']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE cedula = ?', (cedula,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['usuario_id'] = user['id']
            session['usuario_nombre'] = user['nombre']
            session['usuario_rol'] = user['rol']
            return redirect(url_for('hotel'))
        else:
            flash('Credenciales incorrectas. Inténtalo de nuevo.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- GESTIÓN DE USUARIOS (Solo Admin) ---

@app.route('/usuarios')
@admin_required
def usuarios():
    conn = get_db_connection()
    usuarios_list = conn.execute('SELECT id, cedula, nombre, rol FROM usuarios ORDER BY rol, nombre').fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios_list)

@app.route('/agregar_usuario', methods=['POST'])
@admin_required
def agregar_usuario():
    nombre = request.form['nombre']
    cedula = request.form['cedula']
    password = generate_password_hash(request.form['password'])
    rol = request.form['rol']
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO usuarios (cedula, nombre, password, rol) VALUES (?, ?, ?, ?)', 
                     (cedula, nombre, password, rol))
        conn.commit()
        flash('Usuario agregado exitosamente.')
    except sqlite3.IntegrityError:
        flash('Error: Ya existe un usuario con esa cédula.')
    conn.close()
    return redirect(url_for('usuarios'))

@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
@admin_required
def eliminar_usuario(id):
    if id == session.get('usuario_id'):
        flash('No puedes eliminar tu propio usuario mientras estás en sesión.')
        return redirect(url_for('usuarios'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM usuarios WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Usuario eliminado.')
    return redirect(url_for('usuarios'))

# --- GESTIÓN DE TURNOS ---
@app.route('/abrir_turno', methods=['POST'])
def abrir_turno():
    monto = parse_monto(request.form.get('monto', 0))
    usuario_id = session.get('usuario_id')
    conn = get_db_connection()
    # Cerrar cualquier turno abierto previo por si acaso
    conn.execute("UPDATE turnos SET estado = 'Cerrado', fecha_fin = CURRENT_TIMESTAMP WHERE estado = 'Abierto'")
    # Abrir nuevo turno
    conn.execute('INSERT INTO turnos (base_caja, usuario_id) VALUES (?, ?)', (monto, usuario_id))
    conn.commit()
    conn.close()
    flash('Turno abierto exitosamente.')
    return redirect(request.referrer or url_for('hotel'))

@app.route('/cerrar_turno', methods=['POST'])
def cerrar_turno():
    conn = get_db_connection()
    conn.execute("UPDATE turnos SET estado = 'Cerrado', fecha_fin = CURRENT_TIMESTAMP WHERE estado = 'Abierto'")
    conn.commit()
    conn.close()
    flash('Turno cerrado. La caja ha sido entregada.')
    return redirect(request.referrer or url_for('hotel'))

# --- MÓDULO DE GASTOS ---
@app.route('/gastos')
def gastos():
    conn = get_db_connection()
    gastos_list = conn.execute('''
        SELECT g.id, g.descripcion, g.monto, datetime(g.fecha, 'localtime') as fecha, u.nombre 
        FROM gastos g 
        LEFT JOIN usuarios u ON g.usuario_id = u.id 
        ORDER BY g.fecha DESC LIMIT 100
    ''').fetchall()
    conn.close()
    return render_template('gastos.html', gastos=gastos_list)

@app.route('/agregar_gasto', methods=['POST'])
def agregar_gasto():
    descripcion = request.form['descripcion']
    monto = parse_monto(request.form.get('monto'))
    usuario_id = session.get('usuario_id')
    conn = get_db_connection()
    conn.execute('INSERT INTO gastos (descripcion, monto, usuario_id) VALUES (?, ?, ?)', 
                 (descripcion, monto, usuario_id))
    conn.commit()
    conn.close()
    flash('Gasto registrado exitosamente.')
    return redirect(url_for('gastos'))

@app.route('/eliminar_gasto/<int:id>', methods=['POST'])
@admin_required
def eliminar_gasto(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM gastos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Gasto eliminado.')
    return redirect(url_for('gastos'))

# --- MÓDULO DE RESERVAS FUTURAS ---
@app.route('/reservas')
def reservas():
    conn = get_db_connection()
    # Fetch reservas
    reservas_list = [dict(row) for row in conn.execute('''
        SELECT id, cliente_nombre, personas, abono, precio_total, datetime(fecha_hora_evento, 'localtime') as fecha_hora_evento, estado, metodo_pago 
        FROM reservas 
        ORDER BY fecha_hora_evento ASC
    ''').fetchall()]
    
    # Fetch rooms per reserva
    for r in reservas_list:
        habitaciones = conn.execute('''
            SELECT h.numero, h.seccion 
            FROM habitaciones h
            JOIN reservas_habitaciones rh ON h.id = rh.habitacion_id
            WHERE rh.reserva_id = ?
        ''', (r['id'],)).fetchall()
        r['habitaciones'] = [f"{h['seccion']} {h['numero']}" for h in habitaciones]
    
    todas_habitaciones = conn.execute('SELECT id, numero, seccion FROM habitaciones ORDER BY seccion, numero').fetchall()
    conn.close()
    
    return render_template('reservas.html', reservas=reservas_list, habitaciones=todas_habitaciones)

@app.route('/agregar_reserva', methods=['POST'])
def agregar_reserva():
    cliente_nombre = request.form['cliente_nombre']
    personas = request.form.get('personas', 1, type=int)
    abono = parse_monto(request.form.get('abono'))
    precio_total = parse_monto(request.form.get('precio_total'))
    fecha_hora_evento = request.form['fecha_hora_evento']
    metodo_pago = request.form.get('metodo_pago', 'Efectivo')
    habitaciones_ids = request.form.getlist('habitaciones')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO reservas (cliente_nombre, personas, abono, precio_total, fecha_hora_evento, metodo_pago, estado)
        VALUES (?, ?, ?, ?, ?, ?, 'Pendiente')
    ''', (cliente_nombre, personas, abono, precio_total, fecha_hora_evento, metodo_pago))
    
    reserva_id = c.lastrowid
    
    for h_id in habitaciones_ids:
        c.execute('INSERT INTO reservas_habitaciones (reserva_id, habitacion_id) VALUES (?, ?)', (reserva_id, h_id))
        
    conn.commit()
    conn.close()
    flash('Reserva programada exitosamente.')
    return redirect(url_for('reservas'))

@app.route('/eliminar_reserva/<int:id>', methods=['POST'])
@admin_required
def eliminar_reserva(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM reservas_habitaciones WHERE reserva_id = ?', (id,))
    conn.execute('DELETE FROM reservas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Reserva eliminada.')
    return redirect(url_for('reservas'))

# --- GESTIÓN DE CLIENTES ---

@app.route('/clientes')
def clientes():
    conn = get_db_connection()
    clientes_list = conn.execute('SELECT * FROM clientes ORDER BY nombre ASC').fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes_list)

@app.route('/agregar_cliente', methods=['POST'])
def agregar_cliente():
    nombre = request.form['nombre']
    cedula = request.form['cedula']
    telefono = request.form.get('telefono', '')
    correo = request.form.get('correo', '')
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO clientes (nombre, cedula, telefono, correo) VALUES (?, ?, ?, ?)', 
                     (nombre, cedula, telefono, correo))
        conn.commit()
        flash('Cliente registrado exitosamente.')
    except sqlite3.IntegrityError:
        flash('Error: Ya existe un cliente registrado con esa cédula.')
    conn.close()
    
    # Redirigir según desde dónde se envió el formulario (por si agregamos cliente rápido desde hotel)
    next_url = request.form.get('next', url_for('clientes'))
    return redirect(next_url)

@app.route('/editar_cliente/<int:id>', methods=['POST'])
def editar_cliente(id):
    nombre = request.form['nombre']
    cedula = request.form['cedula']
    telefono = request.form.get('telefono', '')
    correo = request.form.get('correo', '')
    
    conn = get_db_connection()
    try:
        conn.execute('UPDATE clientes SET nombre=?, cedula=?, telefono=?, correo=? WHERE id=?', 
                     (nombre, cedula, telefono, correo, id))
        conn.commit()
        flash('Datos del cliente actualizados.')
    except sqlite3.IntegrityError:
        flash('Error: La cédula ingresada ya pertenece a otro cliente.')
    conn.close()
    return redirect(url_for('clientes'))

@app.route('/eliminar_cliente/<int:id>', methods=['POST'])
def eliminar_cliente(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM clientes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Cliente eliminado de la base de datos.')
    return redirect(url_for('clientes'))

# --- FACTURACIÓN ---
@app.route('/factura_tienda/<cuenta_id>')
def factura_tienda(cuenta_id):
    conn = get_db_connection()
    filas = conn.execute('''
        SELECT COALESCE(p.nombre, 'Producto Eliminado') as nombre, v.cantidad, v.total, datetime(v.fecha, 'localtime') as fecha
        FROM ventas v LEFT JOIN productos p ON v.producto_id = p.id WHERE v.cuenta_id = ?
    ''', (cuenta_id,)).fetchall()
    
    pasadias = conn.execute('''
        SELECT nombre, tipo, personas, ninos, total, datetime(fecha, 'localtime') as fecha
        FROM pasadias WHERE cuenta_id = ?
    ''', (cuenta_id,)).fetchall()
    
    conn.close()
    
    if not filas and not pasadias: 
        return redirect(url_for('tienda'))
    
    items = []
    fecha_factura = ""
    if filas:
        fecha_factura = filas[0]['fecha']
        for f in filas:
            items.append({'cant': f['cantidad'], 'desc': f['nombre'], 'total': f['total']})
    
    if pasadias:
        if not fecha_factura:
            fecha_factura = pasadias[0]['fecha']
        for p in pasadias:
            desc = f"{p['tipo']}: {p['nombre']}"
            if p['personas'] > 0:
                desc += f" ({p['personas']} Ad)"
            if p['ninos'] > 0:
                desc += f" ({p['ninos']} Ni)"
            items.append({'cant': 1, 'desc': desc, 'total': p['total']})
            
    total_factura = sum(i['total'] for i in items)
    return render_template('factura.html', recibo_id=cuenta_id, fecha=fecha_factura, items=items, total=total_factura)

@app.route('/factura_pasadia/<int:id>')
def factura_pasadia(id):
    conn = get_db_connection()
    p = conn.execute('SELECT * FROM pasadias WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not p: 
        return redirect(url_for('hotel'))
        
    desc = f"{p['tipo']} - {p['nombre']}"
    if p['cumpleanero']:
        desc += " (Desc. Cumpleañero)"
        
    items = [{'cant': p['personas'], 'desc': desc, 'total': p['total']}]
    return render_template('factura.html', recibo_id=f"HTL-{p['id']}", fecha=p['fecha'], items=items, total=p['total'])

# --- FUNCIONES DEL HOTEL ---

@app.route('/hotel')
def hotel():
    conn = get_db_connection()
    habitaciones = [dict(row) for row in conn.execute('SELECT * FROM habitaciones ORDER BY seccion DESC, numero ASC').fetchall()]
    pasadias = conn.execute("SELECT * FROM pasadias WHERE estado != 'Finalizado' OR date(fecha, 'localtime') = date('now', 'localtime') ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('hotel.html', habitaciones=habitaciones, pasadias=pasadias)

@app.route('/agregar_pasadia', methods=['POST'])
def agregar_pasadia():
    nombre = request.form['nombre']
    tipo = request.form.get('tipo', 'Pasadía')
    personas = int(request.form.get('personas', 0))
    precio_persona = parse_monto(request.form.get('precio_persona', 0))
    ninos = int(request.form.get('ninos', 0))
    precio_nino = parse_monto(request.form.get('precio_nino', 0))
    cumpleanero = 1 if 'cumpleanero' in request.form else 0
    
    # El cumpleañero paga el 50% de la entrada (se cobra el 50% de 1 adulto)
    if cumpleanero and personas > 0:
        personas_a_cobrar = personas - 1
        total_adultos = (personas_a_cobrar * precio_persona) + (precio_persona * 0.5)
    else:
        total_adultos = personas * precio_persona
        
    total_ninos = ninos * precio_nino
    total = total_adultos + total_ninos
    
    carrito = session.get('carrito', {})
    
    # Generar un ID único virtual para el pasadía en el carrito
    import uuid
    pasadia_id = "pasadia_" + str(uuid.uuid4().hex[:8])
    
    carrito[pasadia_id] = {
        'id': pasadia_id,
        'tipo_item': 'pasadia',
        'nombre': f"{tipo}: {nombre} ({personas} Ad, {ninos} Ni)",
        'precio': total,
        'cantidad': 1,
        'subtotal': total,
        'datos': {
            'nombre': nombre,
            'tipo': tipo,
            'personas': personas,
            'precio_persona': precio_persona,
            'ninos': ninos,
            'precio_nino': precio_nino,
            'cumpleanero': cumpleanero
        }
    }
    
    session['carrito'] = carrito
    session.modified = True
    
    flash(f'Pasadía agregado al carrito. Ve a la Tienda para cobrarlo.')
    return redirect(url_for('tienda'))

@app.route('/actualizar_pasadia/<int:id>', methods=['POST'])
def actualizar_pasadia(id):
    nuevo_estado = request.form['estado']
    conn = get_db_connection()
    conn.execute('UPDATE pasadias SET estado = ? WHERE id = ?', (nuevo_estado, id))
    conn.commit()
    conn.close()
    flash(f'Estado de pasadía actualizado.')
    return redirect(url_for('hotel'))

@app.route('/eliminar_pasadia/<int:id>', methods=['POST'])
@admin_required
def eliminar_pasadia(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM pasadias WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Registro de pasadía eliminado.')
    return redirect(url_for('hotel'))

@app.route('/agregar_habitacion', methods=['POST'])
def agregar_habitacion():
    numero = request.form['numero']
    seccion = request.form.get('seccion', 'Torre')
    acomodacion = request.form.get('acomodacion', 'Pareja')
    conn = get_db_connection()
    conn.execute('INSERT INTO habitaciones (numero, estado, seccion, acomodacion) VALUES (?, ?, ?, ?)', (numero, 'Disponible', seccion, acomodacion))
    conn.commit()
    conn.close()
    flash('Habitación agregada correctamente.')
    return redirect(url_for('hotel'))

@app.route('/editar_habitacion/<int:id>', methods=['POST'])
def editar_habitacion(id):
    nuevo_numero = request.form['numero']
    acomodacion = request.form.get('acomodacion', 'Pareja')
    conn = get_db_connection()
    conn.execute('UPDATE habitaciones SET numero = ?, acomodacion = ? WHERE id = ?', (nuevo_numero, acomodacion, id))
    conn.commit()
    conn.close()
    flash('Habitación editada correctamente.')
    return redirect(url_for('hotel'))

@app.route('/eliminar_habitacion/<int:id>', methods=['POST'])
def eliminar_habitacion(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM habitaciones WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Habitación eliminada correctamente.')
    return redirect(url_for('hotel'))

@app.route('/actualizar_habitacion/<int:id>', methods=['POST'])
def actualizar_habitacion(id):
    nuevo_estado = request.form['estado']
    cliente_nombre = request.form.get('cliente_nombre', '')
    personas = request.form.get('personas', 0, type=int)
    conn = get_db_connection()
    if nuevo_estado == 'Disponible':
        conn.execute('UPDATE habitaciones SET estado = ?, cliente_nombre = NULL, personas = 0 WHERE id = ?', (nuevo_estado, id))
    else:
        conn.execute('UPDATE habitaciones SET estado = ?, cliente_nombre = ?, personas = ? WHERE id = ?', (nuevo_estado, cliente_nombre, personas, id))
    conn.commit()
    conn.close()
    flash(f'Estado de habitación actualizado a {nuevo_estado}.')
    return redirect(url_for('hotel'))

# --- FUNCIONES DE LA TIENDA ---

@app.route('/tienda')
def tienda():
    conn = get_db_connection()
    productos = [dict(row) for row in conn.execute('SELECT * FROM productos ORDER BY categoria, nombre').fetchall()]
    conn.close()
    
    carrito = session.get('carrito', {})
    total_carrito = sum(item['subtotal'] for item in carrito.values())
    
    return render_template('tienda.html', productos=productos, carrito=carrito, total_carrito=total_carrito)

@app.route('/agregar_producto', methods=['POST'])
@admin_required
def agregar_producto():
    nombre = request.form['nombre']
    categoria = request.form.get('categoria', 'General')
    precio = parse_monto(request.form.get('precio', 0))
    stock = int(request.form['stock'])
    
    conn = get_db_connection()
    conn.execute('INSERT INTO productos (nombre, categoria, precio, stock) VALUES (?, ?, ?, ?)', (nombre, categoria, precio, stock))
    conn.commit()
    conn.close()
    flash('Producto agregado correctamente.')
    return redirect(url_for('tienda'))

@app.route('/agregar_al_carrito/<int:id>', methods=['POST'])
def agregar_al_carrito(id):
    cantidad = int(request.form['cantidad'])
    
    conn = get_db_connection()
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not producto:
        flash('Producto no encontrado.')
        return redirect(url_for('tienda'))
        
    carrito = session.get('carrito', {})
    str_id = str(id)
    
    # Calcular cantidad total requerida
    cantidad_actual = carrito.get(str_id, {}).get('cantidad', 0)
    nueva_cantidad = cantidad_actual + cantidad
    
    if producto['stock'] < nueva_cantidad:
        flash(f'Stock insuficiente para {producto["nombre"]}. Solo quedan {producto["stock"]}.')
        return redirect(url_for('tienda'))
        
    if str_id in carrito:
        carrito[str_id]['cantidad'] = nueva_cantidad
        carrito[str_id]['subtotal'] = nueva_cantidad * producto['precio']
    else:
        carrito[str_id] = {
            'id': id,
            'nombre': producto['nombre'],
            'precio': producto['precio'],
            'cantidad': cantidad,
            'subtotal': cantidad * producto['precio']
        }
        
    session['carrito'] = carrito
    return redirect(url_for('tienda'))

@app.route('/eliminar_del_carrito/<id>', methods=['POST'])
def eliminar_del_carrito(id):
    carrito = session.get('carrito', {})
    if str(id) in carrito:
        del carrito[str(id)]
        session['carrito'] = carrito
    return redirect(url_for('tienda'))

@app.route('/vaciar_carrito', methods=['POST'])
def vaciar_carrito():
    session.pop('carrito', None)
    flash('El carrito ha sido vaciado.')
    return redirect(url_for('tienda'))

@app.route('/editar_precio/<int:id>', methods=['POST'])
@admin_required
def editar_precio(id):
    nuevo_precio = parse_monto(request.form.get('nuevo_precio'))
    if nuevo_precio is not None:
        conn = get_db_connection()
        conn.execute('UPDATE productos SET precio = ? WHERE id = ?', (nuevo_precio, id))
        conn.commit()
        conn.close()
        flash('Precio del producto actualizado exitosamente.')
    return redirect(url_for('tienda'))

@app.route('/procesar_venta', methods=['POST'])
def procesar_venta():
    carrito = session.get('carrito', {})
    if not carrito:
        flash('El carrito está vacío.')
        return redirect(url_for('tienda'))
        
    metodo_pago = request.form.get('metodo_pago', 'Efectivo')
    
    conn = get_db_connection()
    total_venta = 0
    # Generar un ID de cuenta único para esta compra usando la fecha y hora
    cuenta_id = datetime.now().strftime('TKT-%Y%m%d-%H%M%S')
    
    try:
        for str_id, item in carrito.items():
            cantidad = item['cantidad']
            subtotal = item['subtotal']
            
            if item.get('tipo_item') == 'pasadia':
                # Insertar en tabla pasadias
                d = item['datos']
                conn.execute('''
                    INSERT INTO pasadias (nombre, tipo, personas, estado, precio_persona, cumpleanero, total, metodo_pago, cuenta_id, ninos, precio_nino)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (d['nombre'], d['tipo'], d['personas'], 'Activo', d['precio_persona'], d['cumpleanero'], subtotal, metodo_pago, cuenta_id, d['ninos'], d['precio_nino']))
                total_venta += subtotal
            else:
                # Es un producto normal
                id_prod = item['id']
                producto = conn.execute('SELECT stock, nombre FROM productos WHERE id = ?', (id_prod,)).fetchone()
                if not producto or producto['stock'] < cantidad:
                    flash(f'Stock insuficiente para el producto {item["nombre"]}.')
                    conn.rollback()
                    return redirect(url_for('tienda'))
                    
                nuevo_stock = producto['stock'] - cantidad
                conn.execute('UPDATE productos SET stock = ? WHERE id = ?', (nuevo_stock, id_prod))
                conn.execute('INSERT INTO ventas (cuenta_id, producto_id, cantidad, total, metodo_pago) VALUES (?, ?, ?, ?, ?)', 
                             (cuenta_id, id_prod, cantidad, subtotal, metodo_pago))
                total_venta += subtotal
                
        conn.commit()
        session.pop('carrito', None)
        session['ultima_venta'] = cuenta_id
        flash(f'Venta cobrada con éxito ({metodo_pago}). Cuenta: {cuenta_id} - Total: $ {total_venta:,.0f}'.replace(',', '.'))
    except Exception as e:
        conn.rollback()
        flash('Error al procesar la venta.')
    finally:
        conn.close()
        
    return redirect(url_for('tienda'))

@app.route('/actualizar_stock/<int:id>', methods=['POST'])
def actualizar_stock(id):
    nuevo_stock = int(request.form['nuevo_stock'])
    conn = get_db_connection()
    conn.execute('UPDATE productos SET stock = ? WHERE id = ?', (nuevo_stock, id))
    conn.commit()
    conn.close()
    flash('Stock actualizado correctamente.')
    return redirect(url_for('tienda'))

@app.route('/eliminar_producto/<int:id>', methods=['POST'])
@admin_required
def eliminar_producto(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM productos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Producto eliminado correctamente.')
    return redirect(url_for('tienda'))

# --- REPORTE DEL DÍA ---
@app.route('/anular_factura/<cuenta_id>', methods=['POST'])
@admin_required
def anular_factura(cuenta_id):
    conn = get_db_connection()
    try:
        # 1. Recuperar los productos vendidos y devolver stock
        ventas_items = conn.execute('SELECT producto_id, cantidad FROM ventas WHERE cuenta_id = ?', (cuenta_id,)).fetchall()
        for item in ventas_items:
            if item['producto_id']:
                conn.execute('UPDATE productos SET stock = stock + ? WHERE id = ?', (item['cantidad'], item['producto_id']))
        
        # 2. Eliminar de ventas
        conn.execute('DELETE FROM ventas WHERE cuenta_id = ?', (cuenta_id,))
        
        # 3. Eliminar de pasadias asociados a esta cuenta (por el carrito unificado)
        conn.execute('DELETE FROM pasadias WHERE cuenta_id = ?', (cuenta_id,))
        
        conn.commit()
        flash('Factura anulada correctamente. El stock ha sido devuelto.')
    except Exception as e:
        conn.rollback()
        flash('Ocurrió un error al anular la factura.')
    finally:
        conn.close()
        
    return redirect(url_for('reporte_dia'))

@app.route('/reporte_dia')
@admin_required
def reporte_dia():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    # Defaults a hoy
    hoy = datetime.now().strftime('%Y-%m-%d')
    if not fecha_inicio:
        fecha_inicio = hoy
    if not fecha_fin:
        fecha_fin = hoy
        
    conn = get_db_connection()
    # 1. Ventas de tienda
    ventas = [dict(row) for row in conn.execute('''
        SELECT v.id, COALESCE(v.cuenta_id, 'Antigua-' || v.id) as cuenta_id, COALESCE(p.nombre, 'Producto Eliminado') as nombre, v.cantidad, v.total, datetime(v.fecha, 'localtime') as fecha, v.metodo_pago
        FROM ventas v
        LEFT JOIN productos p ON v.producto_id = p.id
        WHERE date(v.fecha, 'localtime') BETWEEN ? AND ?
        ORDER BY v.fecha DESC
    ''', (fecha_inicio, fecha_fin)).fetchall()]
    
    # 2. Ingresos por Pasadías e Ingresos de Hotel
    pasadias_reporte = [dict(row) for row in conn.execute('''
        SELECT id, nombre, tipo, personas, cumpleanero, total, datetime(fecha, 'localtime') as fecha, metodo_pago
        FROM pasadias
        WHERE date(fecha, 'localtime') BETWEEN ? AND ?
        ORDER BY fecha DESC
    ''', (fecha_inicio, fecha_fin)).fetchall()]
    
    # 3. Bases de caja registradas
    bases = [dict(row) for row in conn.execute('''
        SELECT b.monto, datetime(b.fecha, 'localtime') as fecha, u.nombre
        FROM base_caja b
        LEFT JOIN usuarios u ON b.usuario_id = u.id
        WHERE date(b.fecha, 'localtime') BETWEEN ? AND ?
        ORDER BY b.fecha ASC
    ''', (fecha_inicio, fecha_fin)).fetchall()]
    
    # 3.5. Turnos cerrados / abiertos (Nuevo sistema)
    turnos = [dict(row) for row in conn.execute('''
        SELECT t.id, t.base_caja, datetime(t.fecha_inicio, 'localtime') as fecha_inicio, datetime(t.fecha_fin, 'localtime') as fecha_fin, t.estado, u.nombre
        FROM turnos t
        LEFT JOIN usuarios u ON t.usuario_id = u.id
        WHERE date(t.fecha_inicio, 'localtime') BETWEEN ? AND ?
        ORDER BY t.id DESC
    ''', (fecha_inicio, fecha_fin)).fetchall()]
    
    # 4. Gastos
    gastos = [dict(row) for row in conn.execute('''
        SELECT g.descripcion, g.monto, datetime(g.fecha, 'localtime') as fecha, u.nombre
        FROM gastos g
        LEFT JOIN usuarios u ON g.usuario_id = u.id
        WHERE date(g.fecha, 'localtime') BETWEEN ? AND ?
        ORDER BY g.fecha ASC
    ''', (fecha_inicio, fecha_fin)).fetchall()]
    
    conn.close()
    
    # Calcular totales
    total_tienda = sum([venta['total'] for venta in ventas])
    total_pasadias = sum([p['total'] for p in pasadias_reporte])
    total_bases = sum([b['monto'] for b in bases])
    total_bases_turnos = sum([t['base_caja'] for t in turnos])
    
    total_bases_combinado = total_bases + total_bases_turnos
    total_gastos = sum([g['monto'] for g in gastos])
    gran_total = total_tienda + total_pasadias
    gran_total_neto = gran_total - total_gastos
    
    return render_template('reporte.html', 
                           ventas=ventas, 
                           pasadias=pasadias_reporte,
                           bases=bases,
                           turnos=turnos,
                           gastos=gastos,
                           total_tienda=total_tienda,
                           total_pasadias=total_pasadias,
                           total_bases=total_bases_combinado,
                           total_gastos=total_gastos,
                           gran_total=gran_total, 
                           gran_total_neto=gran_total_neto,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin)

@app.route('/reiniciar_dia', methods=['POST'])
@admin_required
def reiniciar_dia():
    conn = get_db_connection()
    conn.execute('DELETE FROM ventas')
    conn.execute('DELETE FROM base_caja')
    conn.execute('DELETE FROM gastos')
    conn.commit()
    conn.close()
    flash('Se ha reiniciado el día. El registro de ventas, gastos y base de caja están limpios para un nuevo turno.')
    return redirect(url_for('reporte_dia'))

@app.context_processor
def inject_totales():
    if 'usuario_id' in session:
        conn = get_db_connection()
        
        # Obtener turno abierto actual (independiente de si es empleado o admin)
        turno_abierto = conn.execute("SELECT * FROM turnos WHERE estado = 'Abierto' ORDER BY id DESC LIMIT 1").fetchone()
        
        base_caja_hoy = 0
        gran_total_hoy = 0
        turno_id = None
        
        if turno_abierto:
            turno_id = turno_abierto['id']
            base_caja_hoy = turno_abierto['base_caja']
            fecha_inicio = turno_abierto['fecha_inicio']
            
            # Totales acumulados en el turno actual
            t_tienda = conn.execute("SELECT sum(total) FROM ventas WHERE fecha >= ?", (fecha_inicio,)).fetchone()[0] or 0
            t_pasadias = conn.execute("SELECT sum(total) FROM pasadias WHERE fecha >= ?", (fecha_inicio,)).fetchone()[0] or 0
            t_gastos = conn.execute("SELECT sum(monto) FROM gastos WHERE fecha >= ?", (fecha_inicio,)).fetchone()[0] or 0
            
            gran_total_hoy = t_tienda + t_pasadias - t_gastos
            
        conn.close()
        return dict(gran_total_hoy=gran_total_hoy, base_caja_hoy=base_caja_hoy, turno_activo=turno_abierto is not None, turno_id=turno_id)
    return dict()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
