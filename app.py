# ========================================
# SISTEMA DE ANÁLISIS DE CRÉDITO WEB
# Aplicación Flask para Hotmart
# ========================================

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'RAG123_SECRET_KEY_CREDITO'

# ========================================
# CONFIGURACIÓN DE BASE DE DATOS
# ========================================

def init_db():
    """Inicializar base de datos"""
    conn = sqlite3.connect('credito.db')
    c = conn.cursor()
    
    # Tabla de analistas
    c.execute('''CREATE TABLE IF NOT EXISTS analistas
                 (id INTEGER PRIMARY KEY,
                  numero_analista INTEGER UNIQUE,
                  nombre TEXT NOT NULL,
                  apellido_paterno TEXT NOT NULL,
                  apellido_materno TEXT NOT NULL,
                  nip TEXT NOT NULL,
                  fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  ultimo_acceso TIMESTAMP,
                  estado TEXT DEFAULT 'ACTIVO',
                  intentos_fallidos INTEGER DEFAULT 0)''')
    
    # Tabla de solicitudes
    c.execute('''CREATE TABLE IF NOT EXISTS solicitudes
                 (id INTEGER PRIMARY KEY,
                  numero_solicitud TEXT UNIQUE,
                  numero_analista INTEGER,
                  fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  nombre_cliente TEXT,
                  rfc TEXT,
                  fecha_nacimiento DATE,
                  edad INTEGER,
                  ingreso_mensual REAL,
                  fico_score INTEGER,
                  tdsr REAL,
                  pagos_minimos REAL,
                  codigo_postal TEXT,
                  estado TEXT,
                  municipio TEXT,
                  zona TEXT,
                  estado_civil TEXT,
                  ocupacion TEXT,
                  antiguedad_empleo INTEGER,
                  antiguedad_domicilio INTEGER,
                  dependientes INTEGER,
                  nivel_estudios TEXT,
                  validacion_id TEXT,
                  comprobante_ingresos TEXT,
                  calificacion_sic TEXT,
                  consultas_sic INTEGER,
                  score_cualitativo INTEGER,
                  score_historico INTEGER,
                  score_cuantitativo INTEGER,
                  score_total INTEGER,
                  dictamen TEXT,
                  monto_aprobado REAL,
                  tasa REAL,
                  plazo INTEGER,
                  observaciones TEXT,
                  FOREIGN KEY (numero_analista) REFERENCES analistas (numero_analista))''')
    
    # Tabla de reglas de negocio
    c.execute('''CREATE TABLE IF NOT EXISTS reglas_negocio
                 (id INTEGER PRIMARY KEY,
                  parametro TEXT UNIQUE,
                  valor REAL,
                  descripcion TEXT,
                  ultima_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Insertar analistas por defecto
    analistas_default = [
        (1, 'Juan', 'Pérez', 'García', hash_nip('1234')),
        (2, 'María', 'López', 'Silva', hash_nip('5678')),
        (3, 'Carlos', 'Rodríguez', 'Muñoz', hash_nip('9012'))
    ]
    
    for analista in analistas_default:
        c.execute('''INSERT OR IGNORE INTO analistas 
                     (numero_analista, nombre, apellido_paterno, apellido_materno, nip)
                     VALUES (?, ?, ?, ?, ?)''', analista)
    
    # Insertar reglas de negocio por defecto
    reglas_default = [
        ('fico_minimo', 650, 'FICO Score mínimo para aprobación'),
        ('tasa_minima', 22, 'Tasa anual mínima (%)'),
        ('tasa_maxima', 36, 'Tasa anual máxima (%)'),
        ('tdsr_maximo', 40, 'TDSR máximo permitido (%)'),
        ('monto_minimo', 5000, 'Monto mínimo de crédito'),
        ('monto_maximo', 250000, 'Monto máximo de crédito'),
        ('plazo_maximo', 18, 'Plazo máximo en meses')
    ]
    
    for regla in reglas_default:
        c.execute('''INSERT OR IGNORE INTO reglas_negocio 
                     (parametro, valor, descripcion) VALUES (?, ?, ?)''', regla)
    
    conn.commit()
    conn.close()

# ========================================
# FUNCIONES AUXILIARES
# ========================================

def hash_nip(nip):
    """Hashear NIP para seguridad"""
    return hashlib.sha256(nip.encode()).hexdigest()

def validar_analista(numero_analista, nip):
    """Validar credenciales de analista"""
    conn = sqlite3.connect('credito.db')
    c = conn.cursor()
    
    c.execute('''SELECT id, nombre, apellido_paterno, apellido_materno, estado, intentos_fallidos
                 FROM analistas WHERE numero_analista = ? AND nip = ?''', 
              (numero_analista, hash_nip(nip)))
    
    resultado = c.fetchone()
    
    if resultado:
        if resultado[4] == 'ACTIVO':
            # Reset intentos fallidos y actualizar último acceso
            c.execute('''UPDATE analistas SET intentos_fallidos = 0, ultimo_acceso = ?
                         WHERE numero_analista = ?''', (datetime.now(), numero_analista))
            conn.commit()
            conn.close()
            return {
                'valido': True,
                'nombre_completo': f"{resultado[2]} {resultado[3]} {resultado[1]}",
                'numero_analista': numero_analista
            }
        else:
            conn.close()
            return {'valido': False, 'mensaje': 'Cuenta bloqueada'}
    else:
        # Incrementar intentos fallidos
        c.execute('''UPDATE analistas SET intentos_fallidos = intentos_fallidos + 1
                     WHERE numero_analista = ?''', (numero_analista,))
        
        # Verificar si debe bloquearse
        c.execute('''SELECT intentos_fallidos FROM analistas WHERE numero_analista = ?''', 
                  (numero_analista,))
        intentos = c.fetchone()
        
        if intentos and intentos[0] >= 5:
            c.execute('''UPDATE analistas SET estado = 'BLOQUEADO'
                         WHERE numero_analista = ?''', (numero_analista,))
        
        conn.commit()
        conn.close()
        return {'valido': False, 'mensaje': 'Credenciales incorrectas'}

def generar_numero_solicitud():
    """Generar siguiente número de solicitud"""
    conn = sqlite3.connect('credito.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM solicitudes')
    count = c.fetchone()[0]
    
    conn.close()
    return f"S-{count + 1:05d}"

def calcular_scoring(data):
    """Calcular scoring completo"""
    score_cualitativo = 0
    score_historico = 0
    score_cuantitativo = 0
    
    # Scoring Cualitativo (210 puntos máximo)
    if int(data.get('antiguedad_domicilio', 0)) >= 6:
        score_cualitativo += 30
    if data.get('zona', '').upper() == 'URBANA':
        score_cualitativo += 15
    if data.get('estado_civil', '').upper() == 'CASADO':
        score_cualitativo += 20
    if int(data.get('dependientes', 0)) <= 2:
        score_cualitativo += 15
    if data.get('nivel_estudios', '').upper() == 'UNIVERSIDAD':
        score_cualitativo += 20
    if data.get('ocupacion', '').upper() == 'EMPLEADO PÚBLICO':
        score_cualitativo += 25
    if int(data.get('antiguedad_empleo', 0)) >= 3:
        score_cualitativo += 20
    if data.get('validacion_id', '') == 'SI':
        score_cualitativo += 10
    if int(data.get('edad', 0)) > 45:
        score_cualitativo += 30
    
    # Scoring Histórico (150 puntos máximo)
    if data.get('calificacion_sic', '') == '1':
        score_historico += 100
    if int(data.get('consultas_sic', 0)) <= 5:
        score_historico += 30
    if int(data.get('fico_score', 0)) >= 700:
        score_historico += 20
    
    # Scoring Cuantitativo (90 puntos máximo)
    if data.get('comprobante_ingresos', '') == 'SI':
        score_cuantitativo += 35
    ocupacion = data.get('ocupacion', '').upper()
    if ocupacion in ['EMPLEADO PÚBLICO', 'EMPLEADO PRIVADO']:
        score_cuantitativo += 25
    if float(data.get('tdsr', 0)) < 30:
        score_cuantitativo += 30
    
    return score_cualitativo, score_historico, score_cuantitativo

def dictaminar_credito(data, score_total):
    """Dictaminar crédito basado en reglas"""
    conn = sqlite3.connect('credito.db')
    c = conn.cursor()
    
    # Obtener reglas de negocio
    c.execute('SELECT parametro, valor FROM reglas_negocio')
    reglas = dict(c.fetchall())
    conn.close()
    
    fico_score = int(data.get('fico_score', 0))
    tdsr = float(data.get('tdsr', 0))
    ingreso_mensual = float(data.get('ingreso_mensual', 0))
    
    observaciones = []
    
    # Criterios de rechazo
    if fico_score < reglas['fico_minimo']:
        observaciones.append(f"FICO Score insuficiente ({fico_score} < {reglas['fico_minimo']})")
    
    if tdsr > 42.5:
        observaciones.append(f"TDSR excesivo ({tdsr}%)")
    
    if data.get('calificacion_sic', '') in ['96', '97', '98', '99']:
        observaciones.append("Historial crediticio negativo")
    
    # Dictaminación
    if observaciones:
        return {
            'dictamen': 'RECHAZADO',
            'monto': 0,
            'tasa': 0,
            'plazo': 0,
            'observaciones': '; '.join(observaciones)
        }
    
    elif tdsr >= 35 and tdsr <= 42.5:
        return {
            'dictamen': 'ZONA_GRIS',
            'monto': 0,
            'tasa': 0,
            'plazo': 0,
            'observaciones': f"Requiere aprobación gerencial (TDSR: {tdsr}%, Score: {score_total})"
        }
    
    else:
        # Calcular condiciones crediticias
        score_percentage = score_total / 450
        
        monto = min(ingreso_mensual * 10 * score_percentage, reglas['monto_maximo'])
        monto = max(monto, reglas['monto_minimo'])
        
        tasa = reglas['tasa_maxima'] - (score_percentage * (reglas['tasa_maxima'] - reglas['tasa_minima']))
        
        capacidad_pago = ingreso_mensual * (1 - tdsr/100)
        plazo = min(int(monto / (capacidad_pago * 0.8)), reglas['plazo_maximo'])
        plazo = max(plazo, 3)
        
        return {
            'dictamen': 'APROBADO',
            'monto': round(monto, 2),
            'tasa': round(tasa, 2),
            'plazo': plazo,
            'observaciones': f"Crédito aprobado. Score: {score_total}/450 ({score_percentage:.1%})"
        }

# ========================================
# RUTAS WEB
# ========================================

@app.route('/')
def index():
    """Página principal - Login"""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """Procesar login"""
    if request.form.get('tipo_usuario') == 'admin':
        if request.form.get('password') == 'RAG123':
            session['user_type'] = 'admin'
            session['user_name'] = 'Administrador'
            return redirect(url_for('panel_admin'))
        else:
            flash('Contraseña de administrador incorrecta', 'error')
            return redirect(url_for('index'))
    
    else:  # Analista
        numero_analista = request.form.get('numero_analista')
        nip = request.form.get('nip')
        
        resultado = validar_analista(numero_analista, nip)
        
        if resultado['valido']:
            session['user_type'] = 'analista'
            session['user_name'] = resultado['nombre_completo']
            session['numero_analista'] = resultado['numero_analista']
            return redirect(url_for('captura_analista'))
        else:
            flash(resultado['mensaje'], 'error')
            return redirect(url_for('index'))

@app.route('/captura_analista')
def captura_analista():
    """Interfaz de captura para analistas"""
    if session.get('user_type') != 'analista':
        return redirect(url_for('index'))
    
    numero_solicitud = generar_numero_solicitud()
    return render_template('captura_analista.html', 
                         numero_solicitud=numero_solicitud,
                         analista=session.get('user_name'),
                         numero_analista=session.get('numero_analista'))

@app.route('/procesar_solicitud', methods=['POST'])
def procesar_solicitud():
    """Procesar solicitud de crédito"""
    if session.get('user_type') != 'analista':
        return redirect(url_for('index'))
    
    data = request.form.to_dict()
    
    # Calcular scoring
    score_q, score_h, score_c = calcular_scoring(data)
    score_total = score_q + score_h + score_c
    
    # Dictaminar
    resultado = dictaminar_credito(data, score_total)
    
    # Guardar en base de datos
    conn = sqlite3.connect('credito.db')
    c = conn.cursor()
    
    valores = (
        data['numero_solicitud'], session['numero_analista'], data['nombre_cliente'],
        data['rfc'], data['fecha_nacimiento'], data['edad'], data['ingreso_mensual'],
        data['fico_score'], data['tdsr'], data['pagos_minimos'], data['codigo_postal'],
        data['estado'], data['municipio'], data['zona'], data['estado_civil'],
        data['ocupacion'], data['antiguedad_empleo'], data['antiguedad_domicilio'],
        data['dependientes'], data['nivel_estudios'], data['validacion_id'],
        data['comprobante_ingresos'], data['calificacion_sic'], data['consultas_sic'],
        score_q, score_h, score_c, score_total, resultado['dictamen'],
        resultado['monto'], resultado['tasa'], resultado['plazo'], resultado['observaciones']
    )
    
    c.execute('''INSERT INTO solicitudes 
                 (numero_solicitud, numero_analista, nombre_cliente, rfc, fecha_nacimiento,
                  edad, ingreso_mensual, fico_score, tdsr, pagos_minimos, codigo_postal,
                  estado, municipio, zona, estado_civil, ocupacion, antiguedad_empleo,
                  antiguedad_domicilio, dependientes, nivel_estudios, validacion_id,
                  comprobante_ingresos, calificacion_sic, consultas_sic, score_cualitativo,
                  score_historico, score_cuantitativo, score_total, dictamen, monto_aprobado,
                  tasa, plazo, observaciones)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', valores)
    
    conn.commit()
    conn.close()
    
    return render_template('resultado.html', 
                         resultado=resultado, 
                         score_q=score_q, 
                         score_h=score_h, 
                         score_c=score_c, 
                         score_total=score_total,
                         numero_solicitud=data['numero_solicitud'])

@app.route('/panel_admin')
def panel_admin():
    """Panel de administración"""
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('credito.db')
    c = conn.cursor()
    
    # Estadísticas generales
    c.execute('SELECT COUNT(*) FROM solicitudes')
    total_solicitudes = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM solicitudes WHERE dictamen = 'APROBADO'")
    aprobadas = c.fetchone()[0]
    
    c.execute("SELECT AVG(monto_aprobado) FROM solicitudes WHERE dictamen = 'APROBADO'")
    monto_promedio = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM solicitudes WHERE dictamen = 'ZONA_GRIS'")
    zona_gris = c.fetchone()[0]
    
    # Solicitudes recientes
    c.execute('''SELECT numero_solicitud, nombre_cliente, dictamen, monto_aprobado, fecha_captura
                 FROM solicitudes ORDER BY fecha_captura DESC LIMIT 10''')
    solicitudes_recientes = c.fetchall()
    
    conn.close()
    
    porcentaje_aprobacion = (aprobadas / total_solicitudes * 100) if total_solicitudes > 0 else 0
    
    estadisticas = {
        'total_solicitudes': total_solicitudes,
        'aprobadas': aprobadas,
        'porcentaje_aprobacion': round(porcentaje_aprobacion, 1),
        'monto_promedio': round(monto_promedio, 2),
        'zona_gris': zona_gris,
        'solicitudes_recientes': solicitudes_recientes
    }
    
    return render_template('panel_admin.html', estadisticas=estadisticas)

@app.route('/todas_solicitudes')
def todas_solicitudes():
    """Ver todas las solicitudes"""
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('credito.db')
    c = conn.cursor()
    
    c.execute('''SELECT s.numero_solicitud, s.fecha_captura, a.numero_analista,
                        s.nombre_cliente, s.dictamen, s.monto_aprobado, s.score_total
                 FROM solicitudes s
                 JOIN analistas a ON s.numero_analista = a.numero_analista
                 ORDER BY s.fecha_captura DESC''')
    
    solicitudes = c.fetchall()
    conn.close()
    
    return render_template('todas_solicitudes.html', solicitudes=solicitudes)

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    return redirect(url_for('index'))

# ========================================
# TEMPLATES HTML
# ========================================

# Los templates se guardarán en la carpeta 'templates'

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)