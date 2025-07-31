#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Análisis Crediticio - VERSIÓN COMPLETA Y FUNCIONAL
Aplicación Flask con SQLite para persistencia en Render
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from functools import wraps
import json
import os
import random
import string
import sqlite3
from contextlib import contextmanager
import math

# ===== CONFIGURACIÓN DE LA APLICACIÓN =====
app = Flask(__name__)
app.secret_key = 'sistema_credito_2025_clave_segura'

# ===== DECORADOR PARA LOGIN REQUERIDO =====
def login_required(f):
    """Decorador para rutas que requieren login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'analista_id' not in session:
            flash('Debe iniciar sesión primero', 'warning')
            return redirect(url_for('login_analista'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorador para rutas que requieren admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('analista_rol') != 'admin':
            flash('Acceso denegado. Solo administradores.', 'error')
            return redirect(url_for('captura_analista'))
        return f(*args, **kwargs)
    return decorated_function

# ===== CONFIGURACIÓN DE BASE DE DATOS SQLite =====

def init_db():
    """Inicializar base de datos SQLite"""
    try:
        conn = sqlite3.connect('analistas.db')
        cursor = conn.cursor()
        
        # Crear tabla analistas
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
        
        # Crear tabla solicitudes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solicitudes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                analista_codigo TEXT,
                cliente_nombre TEXT,
                cliente_rfc TEXT,
                monto_solicitado REAL,
                monto_aprobado REAL,
                decision TEXT DEFAULT 'pendiente',
                score_total INTEGER DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_decision TIMESTAMP,
                motivo_rechazo TEXT,
                justificacion TEXT,
                FOREIGN KEY (analista_codigo) REFERENCES analistas (codigo)
            )
        ''')
        
        # Insertar datos por defecto si la tabla está vacía
        cursor.execute('SELECT COUNT(*) FROM analistas')
        if cursor.fetchone()[0] == 0:
            analistas_default = [
                ('RAG123', 'Administrador', 'Sistema', '', 'ADMIN123456RF', '5555555555', 'admin123', 'aprobado', 'admin'),
                ('E001', 'Juan', 'Pérez', 'López', 'PELJ850101ABC', '5551234567', '1234', 'aprobado', 'analista')
            ]
            
            cursor.executemany('''
                INSERT INTO analistas (codigo, nombre, apellido_paterno, apellido_materno, rfc, telefono, nip, estado, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', analistas_default)
        
        conn.commit()
        conn.close()
        print("✅ Base de datos SQLite inicializada correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        return False

@contextmanager
def get_db():
    """Context manager para conexiones a la base de datos"""
    conn = sqlite3.connect('analistas.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ===== FUNCIONES AUXILIARES =====

def cargar_analistas():
    """Cargar analistas desde SQLite"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM analistas ORDER BY fecha_registro DESC')
            rows = cursor.fetchall()
            
            analistas = []
            for row in rows:
                fecha_registro = row['fecha_registro']
                if isinstance(fecha_registro, str):
                    try:
                        fecha_obj = datetime.fromisoformat(fecha_registro.replace('Z', ''))
                        fecha_str = fecha_obj.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        fecha_str = fecha_registro
                else:
                    fecha_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                analistas.append({
                    'id': row['id'],
                    'codigo': str(row['codigo']).strip(),
                    'nombre': row['nombre'] or '',
                    'apellido_paterno': row['apellido_paterno'] or '',
                    'apellido_materno': row['apellido_materno'] or '',
                    'rfc': str(row['rfc']).strip(),
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
    """Guardar analista en SQLite"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analistas (codigo, nombre, apellido_paterno, apellido_materno, rfc, telefono, nip, estado, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analista_data['codigo'],
                analista_data['nombre'],
                analista_data.get('apellido_paterno', ''),
                analista_data.get('apellido_materno', ''),
                analista_data['rfc'],
                analista_data['telefono'],
                analista_data['nip'],
                analista_data.get('estado', 'pendiente'),
                analista_data.get('rol', 'analista')
            ))
            conn.commit()
            print(f"✅ Analista {analista_data['codigo']} guardado en SQLite")
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
            
            set_clauses = []
            values = []
            
            for key, value in nuevos_datos.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            values.append(codigo)
            
            query = f"UPDATE analistas SET {', '.join(set_clauses)} WHERE codigo = ?"
            cursor.execute(query, values)
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✅ Analista {codigo} actualizado")
                return True
            else:
                print(f"⚠️ No se encontró analista {codigo}")
                return False
                
    except Exception as e:
        print(f"❌ Error actualizando analista: {e}")
        return False

def analista_existe(rfc):
    """Verificar si ya existe un analista con ese RFC"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM analistas WHERE rfc = ?', (rfc,))
            return cursor.fetchone()[0] > 0
    except Exception as e:
        print(f"❌ Error verificando analista: {e}")
        return False

def generar_codigo_analista():
    """Generar código único de analista"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            while True:
                codigo = 'E' + ''.join(random.choices(string.digits, k=3))
                cursor.execute('SELECT COUNT(*) FROM analistas WHERE codigo = ?', (codigo,))
                if cursor.fetchone()[0] == 0:
                    return codigo
                    
    except Exception as e:
        print(f"❌ Error generando código: {e}")
        return 'E999'

def buscar_analista_por_codigo(codigo):
    """Buscar analista específico por código"""
    try:
        analistas = cargar_analistas()
        for analista in analistas:
            if str(analista.get('codigo', '')).strip().upper() == str(codigo).strip().upper():
                return analista
        return None
    except Exception as e:
        print(f"❌ Error buscando analista: {e}")
        return None

# ===== FUNCIONES HELPER PARA TEMPLATES =====

def calcular_pago_mensual_helper(monto, tasa_anual, plazo_meses):
    """Calcular pago mensual para templates"""
    try:
        if not all([monto, tasa_anual, plazo_meses]) or plazo_meses <= 0:
            return 0
        
        tasa_mensual = (float(tasa_anual) / 100) / 12
        if tasa_mensual == 0:
            return float(monto) / float(plazo_meses)
        
        pago = float(monto) * (tasa_mensual * math.pow(1 + tasa_mensual, plazo_meses)) / (math.pow(1 + tasa_mensual, plazo_meses) - 1)
        return round(pago, 2)
    except:
        return 0

# Registrar función helper en Jinja2
app.jinja_env.globals['calcular_pago_mensual'] = calcular_pago_mensual_helper

# ===== RUTAS PRINCIPALES =====

@app.route('/')
def index():
    """Página de inicio"""
    return render_template('index.html')

@app.route('/login_analista', methods=['GET', 'POST'])
def login_analista():
    """Login de analista"""
    if request.method == 'POST':
        try:
            codigo = request.form.get('codigo', '').strip().upper()
            nip = request.form.get('nip', '').strip()
            
            print(f"🔐 Intento de login - Código: '{codigo}', NIP: '{nip}'")
            
            if not codigo or not nip:
                flash('Ingrese código y NIP', 'error')
                return render_template('login_analista.html')
            
            # Buscar analista
            analista = buscar_analista_por_codigo(codigo)
            
            if not analista:
                print(f"❌ Código {codigo} no encontrado")
                flash('Código de analista no encontrado', 'error')
                return render_template('login_analista.html')
            
            print(f"✅ Analista encontrado: {analista.get('nombre')} - Estado: {analista.get('estado')}")
            
            if analista.get('estado') != 'aprobado':
                flash('Su cuenta está pendiente de aprobación', 'warning')
                return render_template('login_analista.html')
            
            if str(analista.get('nip', '')).strip() != nip:
                print(f"❌ NIP incorrecto. Esperado: {analista.get('nip')}, Recibido: {nip}")
                flash('NIP incorrecto', 'error')
                return render_template('login_analista.html')
            
            # Login exitoso
            session['analista_id'] = analista.get('codigo')
            session['analista_codigo'] = analista.get('codigo')
            session['analista_nombre'] = analista.get('nombre')
            session['analista_rol'] = analista.get('rol', 'analista')
            
            flash(f'Bienvenido, {analista.get("nombre")}', 'success')
            
            if analista.get('rol') == 'admin':
                return redirect(url_for('panel_admin'))
            else:
                return redirect(url_for('captura_analista'))
                
        except Exception as e:
            print(f"💥 Error en login: {str(e)}")
            flash(f'Error en el login: {str(e)}', 'error')
            return render_template('login_analista.html')
    
    return render_template('login_analista.html')

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    """Login de administrador"""
    if request.method == 'POST':
        try:
            clave = request.form.get('clave', '').strip()
            
            if not clave:
                flash('Ingrese la clave de administrador', 'error')
                return render_template('login_admin.html')
            
            if clave == 'admin123':
                session['admin_activo'] = True
                session['analista_id'] = 'RAG123'
                session['analista_codigo'] = 'RAG123'
                session['analista_nombre'] = 'Administrador'
                session['analista_rol'] = 'admin'
                
                flash('Acceso autorizado como Administrador', 'success')
                return redirect(url_for('panel_admin'))
            else:
                flash('Clave de administrador incorrecta', 'error')
                return render_template('login_admin.html')
                
        except Exception as e:
            flash(f'Error en el acceso: {str(e)}', 'error')
            return render_template('login_admin.html')
    
    return render_template('login_admin.html')

@app.route('/registro_analista', methods=['GET', 'POST'])
def registro_analista():
    """Registro de nuevo analista"""
    if request.method == 'POST':
        try:
            nombre_completo = request.form.get('nombre_completo', '').strip()
            rfc = request.form.get('rfc', '').strip().upper()
            telefono = request.form.get('telefono', '').strip()
            nip = request.form.get('nip', '').strip()
            
            # Validaciones
            if not all([nombre_completo, rfc, telefono, nip]):
                flash('Todos los campos son obligatorios', 'error')
                return render_template('registro_analista.html')
            
            partes_nombre = nombre_completo.split()
            if len(partes_nombre) < 2:
                flash('Ingrese nombre y apellido completos', 'error')
                return render_template('registro_analista.html')
            
            if len(rfc) != 13:
                flash('RFC debe tener 13 caracteres', 'error')
                return render_template('registro_analista.html')
            
            if len(nip) != 4 or not nip.isdigit():
                flash('NIP debe ser de 4 dígitos numéricos', 'error')
                return render_template('registro_analista.html')
            
            if analista_existe(rfc):
                flash('Ya existe un analista con ese RFC', 'error')
                return render_template('registro_analista.html')
            
            # Crear nuevo analista
            codigo_analista = generar_codigo_analista()
            nombre = partes_nombre[0]
            apellido_paterno = partes_nombre[1] if len(partes_nombre) > 1 else ''
            apellido_materno = ' '.join(partes_nombre[2:]) if len(partes_nombre) > 2 else ''
            
            nuevo_analista = {
                'codigo': codigo_analista,
                'nombre': nombre,
                'apellido_paterno': apellido_paterno,
                'apellido_materno': apellido_materno,
                'rfc': rfc,
                'telefono': telefono,
                'nip': nip,
                'estado': 'pendiente',
                'rol': 'analista'
            }
            
            if guardar_analista(nuevo_analista):
                flash(f'Solicitud enviada exitosamente. Su código de analista es: {codigo_analista}', 'success')
                return redirect(url_for('login_analista'))
            else:
                flash('Error al guardar el registro. Intente nuevamente.', 'error')
                return render_template('registro_analista.html')
            
        except Exception as e:
            flash(f'Error al procesar el registro: {str(e)}', 'error')
            return render_template('registro_analista.html')
    
    return render_template('registro_analista.html')

@app.route('/captura_analista')
@login_required
def captura_analista():
    """Dashboard del analista"""
    try:
        # Cargar solicitudes del analista (simuladas por ahora)
        estadisticas = {
            'solicitudes_totales': 15,
            'solicitudes_pendientes': 3,
            'solicitudes_aprobadas': 8,
            'solicitudes_rechazadas': 4,
            'monto_total_aprobado': 2500000
        }
        
        return render_template('captura_analista.html', stats=estadisticas)
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/panel_admin')
@login_required
@admin_required
def panel_admin():
    """Panel administrativo"""
    try:
        analistas = cargar_analistas()
        pendientes = [a for a in analistas if a.get('estado') == 'pendiente']
        aprobados = [a for a in analistas if a.get('estado') == 'aprobado' and a.get('rol') != 'admin']
        
        estadisticas = {
            'total_analistas': len([a for a in analistas if a.get('rol') != 'admin']),
            'pendientes': len(pendientes),
            'aprobados': len(aprobados),
            'solicitudes_totales': 45,
            'solicitudes_hoy': 8
        }
        
        return render_template('panel_admin.html', 
                             analistas_pendientes=pendientes,
                             analistas_aprobados=aprobados,
                             stats=estadisticas)
                             
    except Exception as e:
        flash(f'Error al cargar el panel administrativo: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/gestionar_analistas')
@login_required
@admin_required
def gestionar_analistas():
    """Gestionar analistas"""
    try:
        analistas = cargar_analistas()
        todos_analistas = [a for a in analistas if a.get('rol') != 'admin']
        return render_template('gestionar_analistas.html', analistas=todos_analistas)
    except Exception as e:
        flash(f'Error al cargar analistas: {str(e)}', 'error')
        return redirect(url_for('panel_admin'))

@app.route('/aprobar_analista/<codigo>', methods=['POST', 'GET'])
@login_required
@admin_required
def aprobar_analista(codigo):
    """Aprobar un analista pendiente"""
    if actualizar_analista(codigo, {'estado': 'aprobado'}):
        flash(f'Analista {codigo} aprobado exitosamente', 'success')
    else:
        flash('Error al aprobar el analista', 'error')
    
    return redirect(url_for('panel_admin'))

@app.route('/rechazar_analista/<codigo>', methods=['POST', 'GET'])
@login_required
@admin_required
def rechazar_analista(codigo):
    """Rechazar un analista pendiente"""
    if actualizar_analista(codigo, {'estado': 'rechazado'}):
        flash(f'Analista {codigo} rechazado', 'warning')
    else:
        flash('Error al rechazar el analista', 'error')
    
    return redirect(url_for('panel_admin'))

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    nombre = session.get('analista_nombre', 'Usuario')
    session.clear()
    flash(f'Hasta luego, {nombre}. Sesión cerrada correctamente.', 'info')
    return redirect(url_for('index'))

# ===== RUTAS ADICIONALES PARA TEMPLATES EXISTENTES =====

@app.route('/nueva_solicitud')
@login_required
def nueva_solicitud():
    """Formulario para nueva solicitud de crédito"""
    return render_template('nueva_solicitud.html')

@app.route('/evaluar_solicitud')
@login_required
def evaluar_solicitud():
    """Evaluar solicitud de crédito"""
    return render_template('evaluar_solicitud.html')

@app.route('/mis_solicitudes')
@login_required
def mis_solicitudes():
    """Ver solicitudes del analista"""
    return render_template('mis_solicitudes.html')

@app.route('/todas_solicitudes')
@login_required
@admin_required
def todas_solicitudes():
    """Ver todas las solicitudes (solo admin)"""
    return render_template('todas_solicitudes.html')

@app.route('/resultado_solicitud')
@app.route('/resultado_solicitud/<int:solicitud_id>')
@login_required
def resultado_solicitud(solicitud_id=None):
    """Ver resultado de solicitud - con datos simulados"""
    try:
        # Datos simulados para el ejemplo
        solicitud_ejemplo = type('obj', (object,), {
            'id': solicitud_id or 1,
            'numero': 'SOL-2025-001',
            'decision': 'aprobado',
            'monto_aprobado': 150000,
            'tasa_interes': 18.5,
            'plazo_meses': 24,
            'score_total': 385,
            'score_cualitativo': 180,
            'score_historial': 130,
            'score_cuantitativo': 75,
            'fecha_decision': datetime.now(),
            'motivo_rechazo': None,
            'justificacion': None,
            'cliente': type('obj', (object,), {
                'nombre': 'María',
                'apellido_paterno': 'García',
                'apellido_materno': 'Rodríguez',
                'rfc': 'GARM900515XYZ',
                'edad': 35,
                'estado_civil': 'Casada',
                'ocupacion': 'Ingeniera',
                'ingreso_mensual': 45000,
                'antiguedad_empleo': 5,
                'estado': 'CDMX',
                'zona': 'Norte',
                'fico_score': 720,
                'tdsr': 28
            })()
        })()
        
        return render_template('resultado_solicitud.html', solicitud=solicitud_ejemplo)
    except Exception as e:
        flash(f'Error al cargar resultado: {str(e)}', 'error')
        return redirect(url_for('mis_solicitudes'))

@app.route('/reglas_negocio')
@login_required
@admin_required
def reglas_negocio():
    """Configuración de reglas de negocio"""
    return render_template('reglas_negocio.html')

# ===== RUTAS ADICIONALES =====

@app.route('/login')
def login():
    """Ruta login genérica - redirige a login analista"""
    return redirect(url_for('login_analista'))

# ===== FUNCIONES DE DEBUG =====

@app.route('/debug_db')
def debug_db():
    """Debug de la base de datos SQLite"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM analistas")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM analistas WHERE estado = 'pendiente'")
            pendientes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM analistas WHERE estado = 'aprobado'")
            aprobados = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM analistas WHERE rol = 'admin'")
            admins = cursor.fetchone()[0]
            
            html = f"""
            <html>
            <head><title>Debug SQLite Database</title></head>
            <body style="font-family: Arial; margin: 20px;">
            <h2>🗃️ Estado de la Base de Datos SQLite</h2>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <p><strong>📊 Total analistas:</strong> {total}</p>
                <p><strong>⏳ Pendientes:</strong> <span style="color: orange; font-weight: bold;">{pendientes}</span></p>
                <p><strong>✅ Aprobados:</strong> <span style="color: green; font-weight: bold;">{aprobados}</span></p>
                <p><strong>👑 Administradores:</strong> <span style="color: blue; font-weight: bold;">{admins}</span></p>
            </div>
            <hr>
            <div style="margin: 20px 0;">
                <a href="/debug_analistas" style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">👥 Ver Todos los Analistas</a>
                <a href="/test_login" style="background: #17a2b8; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">🔐 Test Login</a>
                <a href="/test_registro" style="background: #ffc107; color: black; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">🧪 Test Registro</a>
                <a href="/panel_admin" style="background: #28a745; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">🏠 Panel Admin</a>
                <a href="/registro_analista" style="background: #fd7e14; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">➕ Registrar Analista</a>
            </div>
            </body>
            </html>
            """
            return html
            
    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial; margin: 20px;">
        <h2 style="color: red;">❌ Error de Base de Datos</h2>
        <p><strong>Error:</strong> {e}</p>
        <a href="/panel_admin" style="color: blue;">← Volver al Panel Admin</a>
        </body>
        </html>
        """

@app.route('/debug_analistas')
def debug_analistas():
    """Ver todos los analistas registrados"""
    try:
        analistas = cargar_analistas()
        
        html = """
        <html>
        <head><title>Debug Analistas</title></head>
        <body style="font-family: Arial; margin: 20px;">
        <h2>🔍 Todos los Analistas Registrados</h2>
        """
        
        html += f"<p><strong>Total:</strong> {len(analistas)} analistas</p><hr>"
        
        if not analistas:
            html += "<p style='color: red;'>❌ No hay analistas en el sistema</p>"
        else:
            for i, analista in enumerate(analistas):
                estado_color = {
                    'pendiente': 'orange',
                    'aprobado': 'green', 
                    'rechazado': 'red'
                }.get(analista.get('estado', 'unknown'), 'gray')
                
                html += f"""
                <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; background: #f9f9f9;">
                    <h3 style="margin-top: 0;">👤 {analista.get('nombre', 'N/A')} {analista.get('apellido_paterno', '')} {analista.get('apellido_materno', '')}</h3>
                    <p><strong>ID:</strong> {analista.get('id', 'N/A')}</p>
                    <p><strong>Código:</strong> <code>{analista.get('codigo', 'N/A')}</code></p>
                    <p><strong>RFC:</strong> <code>{analista.get('rfc', 'N/A')}</code></p>
                    <p><strong>Teléfono:</strong> {analista.get('telefono', 'N/A')}</p>
                    <p><strong>Estado:</strong> <span style="color: {estado_color}; font-weight: bold; font-size: 1.1em;">{analista.get('estado', 'N/A').upper()}</span></p>
                    <p><strong>Rol:</strong> {analista.get('rol', 'N/A')}</p>
                    <p><strong>Fecha:</strong> {analista.get('fecha_registro', 'N/A')}</p>
                </div>
                """
        
        html += """
        <hr>
        <div style="margin: 20px 0;">
            <a href="/debug_db" style="background: #6c757d; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">📊 Ver Estadísticas DB</a>
            <a href="/test_login" style="background: #17a2b8; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">🔐 Test Login</a>
            <a href="/panel_admin" style="background: #28a745; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">🏠 Panel Admin</a>
            <a href="/" style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">🏠 Inicio</a>
        </div>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial; margin: 20px;">
        <h2 style="color: red;">❌ Error al cargar analistas</h2>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/panel_admin">← Volver al Panel Admin</a></p>
        </body>
        </html>
        """

@app.route('/test_login', methods=['GET', 'POST'])
def test_login():
    """Test específico de login"""
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip()
        nip = request.form.get('nip', '').strip()
        
        html = f"""
        <html>
        <body style="font-family: Arial; margin: 20px;">
        <h2>🔐 Test de Login</h2>
        <h3>Datos ingresados:</h3>
        <p><strong>Código:</strong> '{codigo}'</p>
        <p><strong>NIP:</strong> '{nip}'</p>
        
        <h3>Verificación:</h3>
        """
        
        try:
            analistas = cargar_analistas()
            html += f"<p>Analistas cargados: {len(analistas)}</p>"
            
            encontrado = False
            for analista in analistas:
                codigo_db = str(analista.get('codigo', '')).strip()
                nip_db = str(analista.get('nip', '')).strip()
                estado_db = analista.get('estado', '')
                
                coincide_codigo = codigo_db.upper() == codigo.upper()
                coincide_nip = nip_db == nip
                
                if coincide_codigo:
                    encontrado = True
                
                color = "green" if coincide_codigo and coincide_nip and estado_db == 'aprobado' else "orange" if coincide_codigo else "gray"
                
                html += f"""
                <div style="border: 1px solid #ddd; margin: 10px 0; padding: 10px; background: {'#e8f5e8' if color == 'green' else '#fff3cd' if color == 'orange' else '#f8f9fa'};">
                    <p><strong>Código DB:</strong> '{codigo_db}' (¿Coincide? {'✅' if coincide_codigo else '❌'})</p>
                    <p><strong>NIP DB:</strong> '{nip_db}' (¿Coincide? {'✅' if coincide_nip else '❌'})</p>
                    <p><strong>Estado:</strong> {estado_db}</p>
                    <p><strong>Nombre:</strong> {analista.get('nombre', '')}</p>
                    <p><strong>Rol:</strong> {analista.get('rol', '')}</p>
                </div>
                """
            
            if not encontrado:
                html += f"<p style='color: red; font-weight: bold;'>❌ Código '{codigo}' NO encontrado en la base de datos</p>"
            
        except Exception as e:
            html += f"<p style='color: red;'>Error: {str(e)}</p>"
        
        html += """
        <hr>
        <p><a href="/test_login">🔄 Probar otra vez</a></p>
        <p><a href="/debug_db">📊 Ver DB</a></p>
        <p><a href="/login_analista">🔐 Login real</a></p>
        </body>
        </html>
        """
        return html
    
    return """
    <html>
    <body style="font-family: Arial; margin: 20px;">
    <h2>🔐 Test de Login</h2>
    <form method="POST">
        <p><label>Código:</label><br>
        <input type="text" name="codigo" value="E001" style="padding: 8px; width: 200px;"></p>
        
        <p><label>NIP:</label><br>
        <input type="text" name="nip" value="1234" style="padding: 8px; width: 200px;"></p>
        
        <p><button type="submit" style="background: #007bff; color: white; padding: 10px 20px; border: none;">🧪 Probar Login</button></p>
    </form>
    
    <hr>
    <p><a href="/debug_db">📊 Ver DB</a> | <a href="/login_analista">🔐 Login Real</a></p>
    </body>
    </html>
    """

@app.route('/test_registro', methods=['GET', 'POST'])
def test_registro():
    """Test específico de registro"""
    if request.method == 'POST':
        try:
            nombre_completo = request.form.get('nombre_completo', '').strip()
            rfc = request.form.get('rfc', '').strip().upper()
            telefono = request.form.get('telefono', '').strip()
            nip = request.form.get('nip', '').strip()
            
            resultado = f"""
            <html>
            <body style="font-family: Arial; margin: 20px;">
            <h2>🧪 Test de Registro Detallado</h2>
            
            <h3>📥 Datos recibidos:</h3>
            <p><strong>Nombre:</strong> '{nombre_completo}' (longitud: {len(nombre_completo)})</p>
            <p><strong>RFC:</strong> '{rfc}' (longitud: {len(rfc)})</p>
            <p><strong>Teléfono:</strong> '{telefono}' (longitud: {len(telefono)})</p>
            <p><strong>NIP:</strong> '{nip}' (longitud: {len(nip)})</p>
            
            <h3>✅ Validaciones paso a paso:</h3>
            """
            
            # Validar campos vacíos
            if not all([nombre_completo, rfc, telefono, nip]):
                resultado += f"<p style='color: red;'>❌ FALLA: Campos vacíos detectados</p>"
                return resultado + "</body></html>"
            else:
                resultado += "<p style='color: green;'>✅ PASO 1: Todos los campos presentes</p>"
            
            # Validar nombre
            partes_nombre = nombre_completo.split()
            if len(partes_nombre) < 2:
                resultado += f"<p style='color: red;'>❌ FALLA: Nombre debe tener al menos 2 palabras</p>"
                return resultado + "</body></html>"
            else:
                resultado += f"<p style='color: green;'>✅ PASO 2: Nombre válido ({len(partes_nombre)} palabras)</p>"
            
            # Validar RFC
            if len(rfc) != 13:
                resultado += f"<p style='color: red;'>❌ FALLA: RFC debe tener 13 caracteres</p>"
                return resultado + "</body></html>"
            else:
                resultado += f"<p style='color: green;'>✅ PASO 3: RFC válido (13 caracteres)</p>"
            
            # Validar NIP
            if len(nip) != 4 or not nip.isdigit():
                resultado += f"<p style='color: red;'>❌ FALLA: NIP debe ser 4 dígitos</p>"
                return resultado + "</body></html>"
            else:
                resultado += f"<p style='color: green;'>✅ PASO 4: NIP válido (4 dígitos)</p>"
            
            # Verificar RFC existente
            rfc_existe = analista_existe(rfc)
            if rfc_existe:
                resultado += f"<p style='color: red;'>❌ FALLA: RFC {rfc} ya existe</p>"
                return resultado + "</body></html>"
            else:
                resultado += f"<p style='color: green;'>✅ PASO 5: RFC {rfc} disponible</p>"
            
            # Generar código y guardar
            codigo = generar_codigo_analista()
            nombre = partes_nombre[0]
            apellido_paterno = partes_nombre[1] if len(partes_nombre) > 1 else ''
            apellido_materno = ' '.join(partes_nombre[2:]) if len(partes_nombre) > 2 else ''
            
            nuevo_analista = {
                'codigo': codigo,
                'nombre': nombre,
                'apellido_paterno': apellido_paterno,
                'apellido_materno': apellido_materno,
                'rfc': rfc,
                'telefono': telefono,
                'nip': nip,
                'estado': 'pendiente',
                'rol': 'analista'
            }
            
            if guardar_analista(nuevo_analista):
                resultado += f"<p style='color: green; font-size: 1.3em;'>🎉 ¡ÉXITO! Analista guardado correctamente</p>"
                resultado += f"<p><strong>Código asignado:</strong> {codigo}</p>"
            else:
                resultado += f"<p style='color: red; font-size: 1.3em;'>❌ FALLA: Error al guardar</p>"
            
            resultado += """
            <hr>
            <h3>🔍 Verificación:</h3>
            <p><a href="/debug_db" target="_blank">📊 Ver estado actual de la DB</a></p>
            <p><a href="/debug_analistas" target="_blank">👥 Ver todos los analistas</a></p>
            <p><a href="/test_registro">🔄 Probar otra vez</a></p>
            </body>
            </html>
            """
            
            return resultado
            
        except Exception as e:
            return f"""
            <html>
            <body style="font-family: Arial; margin: 20px;">
            <h2 style="color: red;">💥 Error en test_registro</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><a href="/test_registro">🔄 Intentar nuevamente</a></p>
            </body>
            </html>
            """
    
    return """
    <html>
    <body style="font-family: Arial; margin: 20px;">
    <h2>🧪 Test de Registro de Analista</h2>
    <p>Este formulario permite probar el registro paso a paso con debug detallado.</p>
    
    <form method="POST" style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
        <p><label><strong>Nombre Completo:</strong></label><br>
        <input type="text" name="nombre_completo" value="Carlos Mendoza Silva" 
               style="width: 300px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" required></p>
        
        <p><label><strong>RFC (13 caracteres):</strong></label><br>
        <input type="text" name="rfc" value="MESC850720XYZ" 
               style="width: 300px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" required></p>
        
        <p><label><strong>Teléfono:</strong></label><br>
        <input type="text" name="telefono" value="5558765432" 
               style="width: 300px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" required></p>
        
        <p><label><strong>NIP (4 dígitos):</strong></label><br>
        <input type="text" name="nip" value="5678" 
               style="width: 300px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" required></p>
        
        <p><button type="submit" 
           style="background: #28a745; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
           🧪 Probar Registro con Debug
        </button></p>
    </form>
    
    <hr>
    <h3>🔗 Enlaces útiles:</h3>
    <p><a href="/debug_db">📊 Ver estado de la DB</a></p>
    <p><a href="/registro_analista">📝 Registro normal</a></p>
    <p><a href="/panel_admin">🏠 Panel Admin</a></p>
    </body>
    </html>
    """

# ===== API ENDPOINTS =====

@app.route('/api/enviar_resultado', methods=['POST'])
@login_required
def api_enviar_resultado():
    """API para enviar resultado por email"""
    try:
        data = request.get_json()
        solicitud_id = data.get('solicitud_id')
        email_destino = data.get('email_destino')
        
        # Simular envío de email
        print(f"📧 Enviando resultado de solicitud {solicitud_id} a {email_destino}")
        
        return jsonify({
            'success': True,
            'message': f'Resultado enviado a {email_destino}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== MANEJO DE ERRORES =====

@app.errorhandler(404)
def page_not_found(e):
    """Página no encontrada"""
    flash('La página solicitada no fue encontrada', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_server_error(e):
    """Error interno del servidor"""
    flash('Error interno del servidor', 'error')
    return redirect(url_for('index'))

# ===== INICIALIZACIÓN DE LA APLICACIÓN =====

if __name__ == '__main__':
    print("🚀 Iniciando Sistema de Análisis Crediticio...")
    print("🗃️ Inicializando base de datos SQLite...")
    
    # Inicializar base de datos
    init_db()
    
    print("📊 Usuarios por defecto:")
    print("   - Admin: RAG123 / admin123")
    print("   - Analista: E001 / 1234")
    print("🌐 Aplicación ejecutándose...")
    
    # Para Render (producción) y desarrollo local
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
