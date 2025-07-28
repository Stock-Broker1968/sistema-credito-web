from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Función para inicializar la base de datos
def init_db():
    conn = sqlite3.connect('credito.db')
    cursor = conn.cursor()
    
    # Tabla de analistas mejorada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analistas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_usuario TEXT UNIQUE NOT NULL,
            apellido_paterno TEXT NOT NULL,
            apellido_materno TEXT NOT NULL,
            nombre TEXT NOT NULL,
            registro_contribuyentes TEXT NOT NULL,
            nip TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'pendiente',
            evaluado_por TEXT,
            fecha_evaluacion TIMESTAMP
        )
    ''')
    
    # Tabla de administradores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS administradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            nip TEXT NOT NULL,
            nombre_completo TEXT NOT NULL
        )
    ''')
    
    # Crear administrador por defecto si no existe
    cursor.execute('SELECT COUNT(*) FROM administradores WHERE usuario = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        admin_nip = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO administradores (usuario, nip, nombre_completo) 
            VALUES (?, ?, ?)
        ''', ('admin', admin_nip, 'Administrador del Sistema'))
    
    conn.commit()
    conn.close()

# Función para generar el próximo número de usuario
def generar_numero_usuario():
    conn = sqlite3.connect('credito.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM analistas')
    count = cursor.fetchone()[0]
    
    conn.close()
    
    # Formato: E-001, E-002, etc.
    return f"E-{(count + 1):03d}"

# Función para encriptar NIP
def encriptar_nip(nip):
    return hashlib.sha256(nip.encode()).hexdigest()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tipo_usuario = request.form['tipo_usuario']
        
        if tipo_usuario == 'analista':
            return redirect(url_for('login_analista'))
        else:
            return redirect(url_for('login_admin'))
    
    return render_template('login.html')

@app.route('/login_analista', methods=['GET', 'POST'])
def login_analista():
    if request.method == 'POST':
        tiene_usuario = request.form.get('tiene_usuario')
        
        if tiene_usuario == 'si':
            # Usuario existente
            numero_usuario = f"E-{request.form['numero_usuario']}"
            nip = request.form['nip']
            
            conn = sqlite3.connect('credito.db')
            cursor = conn.cursor()
            
            nip_encriptado = encriptar_nip(nip)
            cursor.execute('''
                SELECT * FROM analistas 
                WHERE numero_usuario = ? AND nip = ? AND estado = 'aprobado'
            ''', (numero_usuario, nip_encriptado))
            
            analista = cursor.fetchone()
            conn.close()
            
            if analista:
                session['user_type'] = 'analista'
                session['user_id'] = analista[1]  # numero_usuario
                session['user_name'] = f"{analista[4]} {analista[2]} {analista[3]}"  # nombre + apellidos
                flash('Acceso exitoso', 'success')
                return redirect(url_for('panel_analista'))
            else:
                flash('Credenciales incorrectas o cuenta no aprobada', 'error')
                
        else:
            # Usuario nuevo - registro
            return redirect(url_for('registro_analista'))
    
    return render_template('login_analista.html')

@app.route('/registro_analista', methods=['GET', 'POST'])
def registro_analista():
    if request.method == 'POST':
        apellido_paterno = request.form['apellido_paterno'].strip().upper()
        apellido_materno = request.form['apellido_materno'].strip().upper()
        nombre = request.form['nombre'].strip().upper()
        registro_contribuyentes = request.form['registro_contribuyentes'].strip().upper()
        nip = request.form['nip']
        confirmar_nip = request.form['confirmar_nip']
        
        # Validaciones
        if not all([apellido_paterno, apellido_materno, nombre, registro_contribuyentes, nip]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('registro_analista.html')
        
        if nip != confirmar_nip:
            flash('Los NIPs no coinciden', 'error')
            return render_template('registro_analista.html')
        
        if len(nip) < 4:
            flash('El NIP debe tener al menos 4 caracteres', 'error')
            return render_template('registro_analista.html')
        
        # Verificar si ya existe el registro de contribuyentes
        conn = sqlite3.connect('credito.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM analistas WHERE registro_contribuyentes = ?', 
                      (registro_contribuyentes,))
        if cursor.fetchone()[0] > 0:
            flash('Este registro de contribuyentes ya está registrado', 'error')
            conn.close()
            return render_template('registro_analista.html')
        
        # Generar número de usuario y registrar
        numero_usuario = generar_numero_usuario()
        nip_encriptado = encriptar_nip(nip)
        
        try:
            cursor.execute('''
                INSERT INTO analistas (numero_usuario, apellido_paterno, apellido_materno, 
                                     nombre, registro_contribuyentes, nip, estado) 
                VALUES (?, ?, ?, ?, ?, ?, 'pendiente')
            ''', (numero_usuario, apellido_paterno, apellido_materno, nombre, 
                  registro_contribuyentes, nip_encriptado))
            
            conn.commit()
            conn.close()
            
            flash(f'Registro exitoso. Tu número de usuario es: {numero_usuario}. Tu cuenta está pendiente de aprobación.', 'success')
            return redirect(url_for('login_analista'))
            
        except Exception as e:
            conn.close()
            flash('Error al registrar. Intenta nuevamente.', 'error')
            return render_template('registro_analista.html')
    
    return render_template('registro_analista.html')

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        usuario = request.form['usuario']
        nip = request.form['nip']
        
        conn = sqlite3.connect('credito.db')
        cursor = conn.cursor()
        
        nip_encriptado = encriptar_nip(nip)
        cursor.execute('SELECT * FROM administradores WHERE usuario = ? AND nip = ?', 
                      (usuario, nip_encriptado))
        
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            session['user_type'] = 'admin'
            session['user_id'] = admin[1]  # usuario
            session['user_name'] = admin[3]  # nombre_completo
            return redirect(url_for('panel_admin'))
        else:
            flash('Credenciales incorrectas', 'error')
    
    return render_template('login_admin.html')

@app.route('/panel_analista')
def panel_analista():
    if 'user_type' not in session or session['user_type'] != 'analista':
        return redirect(url_for('login'))
    
    return render_template('captura_analista.html', 
                         user_name=session['user_name'],
                         user_id=session['user_id'])

@app.route('/panel_admin')
def panel_admin():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('credito.db')
    cursor = conn.cursor()
    
    # Obtener TODOS los datos de los analistas (corregido)
    cursor.execute('''
        SELECT numero_usuario, apellido_paterno, apellido_materno, nombre, 
               registro_contribuyentes, nip, fecha_registro, estado
        FROM analistas 
        ORDER BY fecha_registro DESC
    ''')
    
    analistas = cursor.fetchall()
    conn.close()
    
    return render_template('panel_admin.html', 
                         user_name=session['user_name'],
                         analistas=analistas)

@app.route('/evaluar_analista/<numero_usuario>/<accion>')
def evaluar_analista(numero_usuario, accion):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    if accion not in ['aprobar', 'rechazar']:
        flash('Acción no válida', 'error')
        return redirect(url_for('panel_admin'))
    
    conn = sqlite3.connect('credito.db')
    cursor = conn.cursor()
    
    nuevo_estado = 'aprobado' if accion == 'aprobar' else 'rechazado'
    
    cursor.execute('''
        UPDATE analistas 
        SET estado = ?, evaluado_por = ?, fecha_evaluacion = CURRENT_TIMESTAMP
        WHERE numero_usuario = ?
    ''', (nuevo_estado, session['user_id'], numero_usuario))
    
    conn.commit()
    conn.close()
    
    flash(f'Analista {numero_usuario} {nuevo_estado} exitosamente', 'success')
    return redirect(url_for('panel_admin'))

@app.route('/resetear_nip/<numero_usuario>', methods=['POST'])
def resetear_nip(numero_usuario):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        nuevo_nip = data.get('nuevo_nip')
        
        if not nuevo_nip or len(nuevo_nip) < 4:
            return jsonify({'success': False, 'message': 'NIP debe tener al menos 4 caracteres'})
        
        conn = sqlite3.connect('credito.db')
        cursor = conn.cursor()
        
        nip_encriptado = encriptar_nip(nuevo_nip)
        cursor.execute('''
            UPDATE analistas 
            SET nip = ?
            WHERE numero_usuario = ?
        ''', (nip_encriptado, numero_usuario))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            flash(f'NIP del analista {numero_usuario} actualizado exitosamente', 'success')
            return jsonify({'success': True, 'message': 'NIP actualizado'})
        else:
            conn.close()
            return jsonify({'success': False, 'message': 'Analista no encontrado'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
