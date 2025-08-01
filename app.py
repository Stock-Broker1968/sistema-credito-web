from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configuración de la base de datos
DATABASE = 'creditos.db'

def get_db():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializar la base de datos"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Tabla de analistas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analistas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    apellido_paterno TEXT,
                    apellido_materno TEXT,
                    rfc TEXT UNIQUE NOT NULL,
                    telefono TEXT,
                    nip TEXT NOT NULL,
                    estado TEXT DEFAULT 'pendiente',
                    rol TEXT DEFAULT 'analista',
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de administradores
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS administradores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de clientes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    apellido_paterno TEXT,
                    apellido_materno TEXT,
                    rfc TEXT UNIQUE NOT NULL,
                    telefono TEXT,
                    direccion TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analista_id INTEGER,
                    FOREIGN KEY (analista_id) REFERENCES analistas (id)
                )
            ''')
            
            # Tabla de créditos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS creditos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER NOT NULL,
                    analista_id INTEGER NOT NULL,
                    monto REAL NOT NULL,
                    plazo INTEGER NOT NULL,
                    tasa_interes REAL NOT NULL,
                    estado TEXT DEFAULT 'pendiente',
                    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_aprobacion TIMESTAMP,
                    observaciones TEXT,
                    FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                    FOREIGN KEY (analista_id) REFERENCES analistas (id)
                )
            ''')
            
            # Crear administrador por defecto si no existe
            cursor.execute("SELECT COUNT(*) FROM administradores")
            if cursor.fetchone()[0] == 0:
                crear_admin_default()
            
            conn.commit()
            print("✅ Base de datos inicializada correctamente")
            
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

def crear_admin_default():
    """Crear administrador por defecto"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Contraseña: admin123
            password_hash = generate_password_hash('admin123')
            cursor.execute('''
                INSERT INTO administradores (username, password, email)
                VALUES (?, ?, ?)
            ''', ('admin', password_hash, 'admin@sistema.com'))
            
            # También crear un administrador en la tabla de analistas
            cursor.execute('''
                INSERT INTO analistas (codigo, nombre, apellido_paterno, apellido_materno, 
                                     rfc, telefono, nip, estado, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('RAG123', 'Administrador', 'Sistema', '', 'ADMIN123456RF', 
                  '5555555555', '1234', 'aprobado', 'admin'))
            
            conn.commit()
            print("✅ Administrador por defecto creado")
    except Exception as e:
        print(f"❌ Error creando admin: {e}")

def cargar_analistas():
    """Cargar analistas desde SQLite - VERSIÓN CORREGIDA"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM analistas ORDER BY fecha_registro DESC')
            rows = cursor.fetchall()
            
            analistas = []
            for row in rows:
                # Manejo correcto de fecha_registro
                fecha_registro = row['fecha_registro']
                if fecha_registro:
                    # Si es string, dejarlo como está
                    if isinstance(fecha_registro, str):
                        fecha_str = fecha_registro
                    # Si es datetime, convertir a string
                    else:
                        try:
                            fecha_str = fecha_registro.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            fecha_str = str(fecha_registro)
                else:
                    # Si no hay fecha, usar la actual
                    fecha_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                analistas.append({
                    'id': row['id'],
                    'codigo': str(row['codigo']).strip().upper(),  # Normalizar código
                    'nombre': row['nombre'] or '',
                    'apellido_paterno': row['apellido_paterno'] or '',
                    'apellido_materno': row['apellido_materno'] or '',
                    'rfc': str(row['rfc']).strip().upper(),  # Normalizar RFC
                    'telefono': row['telefono'] or '',
                    'nip': str(row['nip']).strip(),
                    'estado': str(row['estado']).strip(),
                    'rol': str(row['rol']).strip(),
                    'fecha_registro': fecha_str
                })
            
            print(f"📊 Cargados {len(analistas)} analistas desde SQLite")
            return analistas

    except Exception as e:
        print(f"❌ Error cargando analistas: {e}")
        return []

def guardar_analista(analista_data):
    """Guardar analista en SQLite - VERSIÓN CORREGIDA"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Normalizar datos antes de guardar
            codigo = str(analista_data.get('codigo', '')).strip().upper()
            rfc = str(analista_data.get('rfc', '') or analista_data.get('RFC', '')).strip().upper()
            telefono = analista_data.get('telefono', '') or analista_data.get('teléfono', '')
            
            cursor.execute('''
                INSERT INTO analistas (codigo, nombre, apellido_paterno, apellido_materno, 
                                     rfc, telefono, nip, estado, rol, fecha_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                codigo,
                analista_data.get('nombre', ''),
                analista_data.get('apellido_paterno', ''),
                analista_data.get('apellido_materno', ''),
                rfc,
                telefono,
                analista_data.get('nip', ''),
                analista_data.get('estado', 'pendiente'),
                analista_data.get('rol', 'analista')
            ))
            
            conn.commit()
            print(f"✅ Analista {codigo} guardado en SQLite")
            return True

    except sqlite3.IntegrityError as e:
        print(f"⚠️ Error de integridad (RFC o código duplicado): {e}")
        return False
    except Exception as e:
        print(f"❌ Error guardando analista: {e}")
        return False

def actualizar_analista(codigo, nuevos_datos):
    """Actualizar datos de un analista en SQLite"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE analistas 
                SET nombre = ?, apellido_paterno = ?, apellido_materno = ?, 
                    rfc = ?, telefono = ?, estado = ?
                WHERE codigo = ?
            ''', (
                nuevos_datos.get('nombre'),
                nuevos_datos.get('apellido_paterno'),
                nuevos_datos.get('apellido_materno'),
                nuevos_datos.get('rfc'),
                nuevos_datos.get('telefono'),
                nuevos_datos.get('estado'),
                codigo
            ))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error actualizando analista: {e}")
        return False

def aprobar_todos_los_analistas():
    """Aprobar todos los analistas pendientes - útil para desarrollo"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Primero, ver cuántos están pendientes
            cursor.execute("SELECT COUNT(*) FROM analistas WHERE estado = 'pendiente'")
            pendientes = cursor.fetchone()[0]
            
            if pendientes > 0:
                # Aprobar todos los pendientes
                cursor.execute("""
                    UPDATE analistas 
                    SET estado = 'aprobado' 
                    WHERE estado = 'pendiente'
                """)
                conn.commit()
                print(f"✅ {pendientes} analistas aprobados")
            else:
                print("ℹ️ No hay analistas pendientes")
                
            # Mostrar estado actual
            cursor.execute("SELECT codigo, nombre, estado FROM analistas")
            for row in cursor.fetchall():
                print(f"Analista {row[0]} - {row[1]}: {row[2]}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

# RUTAS DE LA APLICACIÓN

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/registro_analista', methods=['GET', 'POST'])
def registro_analista():
    """Página de registro de analista - CORREGIDA"""
    if request.method == 'POST':
        # Generar código automático
        codigo = f"E{str(secrets.randbelow(900) + 100)}"
        
        # Obtener datos del formulario
        nombre_completo = request.form.get('nombre', '').strip()
        partes = nombre_completo.split(' ', 2)
        
        nombre = partes[0] if len(partes) > 0 else ''
        apellido_paterno = partes[1] if len(partes) > 1 else ''
        apellido_materno = partes[2] if len(partes) > 2 else ''
        
        analista_data = {
            'codigo': codigo,
            'nombre': nombre,
            'apellido_paterno': apellido_paterno,
            'apellido_materno': apellido_materno,
            'rfc': request.form.get('rfc'),
            'telefono': request.form.get('telefono'),
            'nip': request.form.get('nip'),
            'estado': 'pendiente'
        }
        
        if guardar_analista(analista_data):
            flash(f'Analista registrado con código: {codigo}. Por favor espere aprobación del administrador.', 'success')
            # Si existe registro_exitoso.html, úsalo; si no, redirige al index
            try:
                return render_template('registro_exitoso.html', codigo=codigo)
            except:
                return redirect(url_for('index'))
        else:
            flash('Error al registrar analista. RFC puede estar duplicado.', 'error')
    
    return render_template('registro_analista.html')

@app.route('/login_analista', methods=['GET', 'POST'])
def login_analista():
    """Login de analista - VERSIÓN CORREGIDA"""
    if request.method == 'POST':
        try:
            # Normalizar entrada: limpiar espacios y convertir a mayúsculas
            codigo = request.form.get('codigo', '').strip().upper()
            nip = request.form.get('nip', '').strip()

            print(f"🔐 Intento de login - Código: '{codigo}', NIP: '{nip}'")
            
            if not codigo or not nip:
                flash('Ingrese código y NIP', 'error')
                return render_template('login_analista.html')

            # Cargar analistas de la base de datos
            analistas = cargar_analistas()
            print(f"📋 Total analistas en BD: {len(analistas)}")
            print(f"📋 Códigos disponibles: {[a.get('codigo') for a in analistas]}")
            
            # Buscar analista con código exacto (comparación normalizada)
            analista = None
            for a in analistas:
                codigo_bd = str(a.get('codigo', '')).strip().upper()
                print(f"Comparando: '{codigo}' con '{codigo_bd}'")
                if codigo_bd == codigo:
                    analista = a
                    print(f"✅ Analista encontrado: {a.get('nombre')}")
                    break

            if not analista:
                print(f"❌ Código {codigo} no encontrado en la base de datos")
                flash('Código de analista no encontrado', 'error')
                return render_template('login_analista.html')

            # Verificar estado del analista
            estado = analista.get('estado', '').strip().lower()
            print(f"📊 Estado del analista: '{estado}'")
            
            if estado != 'aprobado':
                flash('Su cuenta está pendiente de aprobación', 'warning')
                return render_template('login_analista.html')

            # Verificar NIP
            nip_bd = str(analista.get('nip', '')).strip()
            if nip_bd != nip:
                print(f"❌ NIP incorrecto. Esperado: '{nip_bd}', Recibido: '{nip}'")
                flash('NIP incorrecto', 'error')
                return render_template('login_analista.html')

            # Login exitoso
            session['user_type'] = 'analista'
            session['user_id'] = analista.get('id')
            session['user_codigo'] = codigo
            session['user_nombre'] = analista.get('nombre', '')
            
            print(f"✅ Login exitoso para analista {codigo}")
            flash(f'Bienvenido {analista.get("nombre")}', 'success')
            
            # Redirigir al módulo de créditos
            return redirect(url_for('creditos'))

        except Exception as e:
            print(f"❌ Error en login: {e}")
            flash('Error al procesar el login', 'error')
            return render_template('login_analista.html')
    
    return render_template('login_analista.html')

@app.route('/captura_analista', methods=['GET', 'POST'])
def captura_analista():
    """Captura de nuevo analista"""
    if request.method == 'POST':
        # Generar código automático
        codigo = f"E{str(secrets.randbelow(900) + 100)}"
        
        analista_data = {
            'codigo': codigo,
            'nombre': request.form.get('nombre'),
            'apellido_paterno': request.form.get('apellido_paterno'),
            'apellido_materno': request.form.get('apellido_materno'),
            'rfc': request.form.get('rfc'),
            'telefono': request.form.get('telefono'),
            'nip': request.form.get('nip'),
            'estado': 'pendiente'
        }
        
        if guardar_analista(analista_data):
            flash(f'Analista registrado con código: {codigo}', 'success')
            return render_template('registro_exitoso.html', codigo=codigo)
        else:
            flash('Error al registrar analista. RFC o código puede estar duplicado.', 'error')
    
    return render_template('captura_analista.html')

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    """Login de administrador"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM administradores WHERE username = ?', (username,))
                admin = cursor.fetchone()
                
                if admin and check_password_hash(admin['password'], password):
                    session['user_type'] = 'admin'
                    session['admin_id'] = admin['id']
                    session['admin_username'] = admin['username']
                    flash('Login exitoso', 'success')
                    return redirect(url_for('panel_admin'))
                else:
                    flash('Usuario o contraseña incorrectos', 'error')
        except Exception as e:
            flash(f'Error en login: {e}', 'error')
    
    return render_template('login_admin.html')

@app.route('/panel_admin')
def panel_admin():
    """Panel de administración"""
    if session.get('user_type') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    return render_template('panel_admin.html')

@app.route('/admin_panel')
def admin_panel():
    """Panel de administración - alias para compatibilidad"""
    return panel_admin()

@app.route('/gestionar_analistas')
def gestionar_analistas():
    """Gestión de analistas"""
    if session.get('user_type') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    analistas = cargar_analistas()
    return render_template('gestionar_analistas.html', analistas=analistas)

@app.route('/admin/aprobar_analista/<codigo>')
def aprobar_analista(codigo):
    """Aprobar un analista específico"""
    if session.get('user_type') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE analistas SET estado = 'aprobado' WHERE codigo = ?", 
                (codigo,)
            )
            conn.commit()
            flash(f'Analista {codigo} aprobado', 'success')
    except Exception as e:
        flash(f'Error al aprobar analista: {e}', 'error')
    
    return redirect(url_for('gestionar_analistas'))

@app.route('/admin/rechazar_analista/<codigo>')
def rechazar_analista(codigo):
    """Rechazar un analista"""
    if session.get('user_type') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE analistas SET estado = 'rechazado' WHERE codigo = ?", 
                (codigo,)
            )
            conn.commit()
            flash(f'Analista {codigo} rechazado', 'warning')
    except Exception as e:
        flash(f'Error al rechazar analista: {e}', 'error')
    
    return redirect(url_for('gestionar_analistas'))

@app.route('/admin/aprobar_todos')
def aprobar_todos():
    """Ruta de administración para aprobar todos los analistas"""
    if session.get('user_type') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    aprobar_todos_los_analistas()
    flash('Todos los analistas han sido aprobados', 'success')
    return redirect(url_for('gestionar_analistas'))

@app.route('/creditos')
def creditos():
    """Módulo de créditos - requiere autenticación"""
    # Verificar si el usuario está autenticado
    if 'user_type' not in session:
        flash('Debe iniciar sesión primero', 'error')
        return redirect(url_for('login_analista'))
    
    # Verificar que sea un analista o admin
    if session.get('user_type') not in ['analista', 'admin']:
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    # Datos del usuario para mostrar en la página
    user_data = {
        'tipo': session.get('user_type'),
        'codigo': session.get('user_codigo'),
        'nombre': session.get('user_nombre'),
        'id': session.get('user_id')
    }
    
    return render_template('creditos.html', user=user_data)

@app.route('/nueva_solicitud')
def nueva_solicitud():
    """Nueva solicitud de crédito"""
    if 'user_type' not in session:
        flash('Debe iniciar sesión primero', 'error')
        return redirect(url_for('login_analista'))
    
    return render_template('nueva_solicitud.html')

@app.route('/mis_solicitudes')
def mis_solicitudes():
    """Mis solicitudes"""
    if 'user_type' not in session:
        flash('Debe iniciar sesión primero', 'error')
        return redirect(url_for('login_analista'))
    
    return render_template('mis_solicitudes.html')

@app.route('/evaluar_solicitud')
def evaluar_solicitud():
    """Evaluar solicitud"""
    if 'user_type' not in session:
        flash('Debe iniciar sesión primero', 'error')
        return redirect(url_for('login_analista'))
    
    return render_template('evaluar_solicitud.html')

@app.route('/reglas_negocio')
def reglas_negocio():
    """Configurar reglas de negocio"""
    if session.get('user_type') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    return render_template('reglas_negocio.html')

@app.route('/todas_solicitudes')
def todas_solicitudes():
    """Ver todas las solicitudes"""
    if session.get('user_type') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('index'))
    
    return render_template('todas_solicitudes.html')

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('index'))

# RUTAS DE DEBUG (solo para desarrollo)
@app.route('/debug_analistas')
def debug_analistas():
    """Ver todos los analistas (solo para debug)"""
    analistas = cargar_analistas()
    return f'''
    <h1>Total: {len(analistas)} analistas</h1>
    <pre>{analistas}</pre>
    <a href="{url_for('index')}">Volver</a>
    '''

@app.route('/test_registro', methods=['GET', 'POST'])
def test_registro():
    """Página de test para registro de analistas"""
    if request.method == 'POST':
        # Generar código automático
        import random
        codigo = f"E{random.randint(100, 999)}"
        
        # Separar el nombre completo
        nombre_completo = request.form.get('nombre', '').strip()
        partes = nombre_completo.split(' ', 2)
        
        nombre = partes[0] if len(partes) > 0 else ''
        apellido_paterno = partes[1] if len(partes) > 1 else ''
        apellido_materno = partes[2] if len(partes) > 2 else ''
        
        analista_data = {
            'codigo': codigo,
            'nombre': nombre,
            'apellido_paterno': apellido_paterno,
            'apellido_materno': apellido_materno,
            'rfc': request.form.get('rfc'),
            'telefono': request.form.get('telefono'),
            'nip': request.form.get('nip'),
            'estado': 'aprobado'  # Auto-aprobar para pruebas
        }
        
        # Debug info
        debug_info = f'''
        <h2>🔧 Test de Registro Detallado</h2>
        <h3>📥 Datos recibidos:</h3>
        <p><strong>Nombre:</strong> '{nombre_completo}' (longitud: {len(nombre_completo)})</p>
        <p><strong>RFC:</strong> '{request.form.get('rfc')}' (longitud: {len(request.form.get('rfc', ''))})</p>
        <p><strong>Teléfono:</strong> '{request.form.get('telefono')}' (longitud: {len(request.form.get('telefono', ''))})</p>
        <p><strong>NIP:</strong> '{request.form.get('nip')}' (longitud: {len(request.form.get('nip', ''))})</p>
        
        <h3>✅ Validaciones paso a paso:</h3>
        '''
        
        # Validaciones
        validaciones = []
        
        # 1. Campos presentes
        if all([nombre_completo, request.form.get('rfc'), request.form.get('telefono'), request.form.get('nip')]):
            validaciones.append("✅ PASO 1: Todos los campos presentes")
        else:
            validaciones.append("❌ PASO 1: Faltan campos obligatorios")
        
        # 2. Nombre válido
        if len(nombre.split()) <= 3 and len(nombre) >= 2:
            validaciones.append(f"✅ PASO 2: Nombre válido ({len(nombre.split())} palabras)")
        else:
            validaciones.append(f"❌ PASO 2: Nombre inválido")
        
        # 3. RFC válido
        rfc = request.form.get('rfc', '')
        if len(rfc) == 13 and rfc.isalnum():
            validaciones.append(f"✅ PASO 3: RFC válido ({len(rfc)} caracteres)")
        else:
            validaciones.append(f"❌ PASO 3: RFC inválido (se esperan 13 caracteres alfanuméricos)")
        
        # 4. NIP válido
        nip = request.form.get('nip', '')
        if len(nip) == 4 and nip.isdigit():
            validaciones.append(f"✅ PASO 4: NIP válido ({len(nip)} dígitos)")
        else:
            validaciones.append(f"❌ PASO 4: NIP inválido (se esperan 4 dígitos)")
        
        # 5. RFC no duplicado
        analistas = cargar_analistas()
        rfc_existe = any(a['rfc'] == rfc.upper() for a in analistas)
        if not rfc_existe:
            validaciones.append(f"✅ PASO 5: RFC {rfc} disponible")
        else:
            validaciones.append(f"❌ PASO 5: RFC {rfc} ya existe")
        
        debug_info += '<br>'.join(validaciones)
        
        # Generar código
        debug_info += f'''
        <br><br>
        <p style="color: blue;"><strong>🔢 Código generado: {codigo}</strong></p>
        
        <h3>💾 Intentando guardar:</h3>
        <pre>{analista_data}</pre>
        '''
        
        # Intentar guardar
        if guardar_analista(analista_data):
            resultado = f'''
            <h2 style="color: green;">🎉 ¡ÉXITO! Analista guardado correctamente</h2>
            <p><strong>Código asignado:</strong> {codigo}</p>
            <p>Ahora puedes iniciar sesión con:</p>
            <ul>
                <li><strong>Código:</strong> {codigo}</li>
                <li><strong>NIP:</strong> {nip}</li>
            </ul>
            '''
        else:
            resultado = '''
            <h2 style="color: red;">❌ Error al guardar el analista</h2>
            <p>Posibles causas: RFC duplicado o error en la base de datos</p>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resultado del Test</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                pre {{ background: #f0f0f0; padding: 10px; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
            </style>
        </head>
        <body>
            {debug_info}
            {resultado}
            <br><br>
            <a href="{url_for('test_registro')}">Hacer otro registro</a> | 
            <a href="{url_for('login_analista')}">Ir al login</a> |
            <a href="{url_for('debug_analistas')}">Ver todos los analistas</a>
        </body>
        </html>
        '''
    
    # Formulario de registro de prueba
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test de Registro</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            form { max-width: 400px; }
            input { width: 100%; margin: 5px 0; padding: 8px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        </style>
    </head>
    <body
