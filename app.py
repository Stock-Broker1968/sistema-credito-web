#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Análisis Crediticio
Aplicación Flask completa y funcional
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from functools import wraps
import json
import os
import random
import string

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

# ===== FUNCIONES AUXILIARES =====

def cargar_analistas():
    """Cargar analistas desde la base de datos"""
    try:
        if os.path.exists('analistas.json'):
            with open('analistas.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Crear archivo con analistas por defecto
            analistas_default = [
                {
                    'codigo': 'RAG123',
                    'nombre': 'Administrador',
                    'apellido_paterno': 'Sistema',
                    'apellido_materno': '',
                    'rfc': 'ADMIN123456RF',
                    'telefono': '5555555555',
                    'nip': 'admin123',
                    'estado': 'aprobado',
                    'rol': 'admin',
                    'fecha_registro': datetime.now().isoformat()
                },
                {
                    'codigo': 'E001',
                    'nombre': 'Juan',
                    'apellido_paterno': 'Pérez',
                    'apellido_materno': 'López',
                    'rfc': 'PELJ850101ABC',
                    'telefono': '5551234567',
                    'nip': '1234',
                    'estado': 'aprobado',
                    'rol': 'analista',
                    'fecha_registro': datetime.now().isoformat()
                }
            ]
            
            with open('analistas.json', 'w', encoding='utf-8') as f:
                json.dump(analistas_default, f, ensure_ascii=False, indent=2)
            
            return analistas_default
    except Exception as e:
        print(f"Error cargando analistas: {e}")
        return []

def guardar_analista(analista_data):
    """Guardar analista en la base de datos"""
    try:
        analistas = cargar_analistas()
        analistas.append(analista_data)
        
        with open('analistas.json', 'w', encoding='utf-8') as f:
            json.dump(analistas, f, ensure_ascii=False, indent=2, default=str)
        
        return True
    except Exception as e:
        print(f"Error guardando analista: {e}")
        return False

def actualizar_analista(codigo, nuevos_datos):
    """Actualizar datos de un analista"""
    try:
        analistas = cargar_analistas()
        for i, analista in enumerate(analistas):
            if analista.get('codigo') == codigo:
                analistas[i].update(nuevos_datos)
                break
        
        with open('analistas.json', 'w', encoding='utf-8') as f:
            json.dump(analistas, f, ensure_ascii=False, indent=2, default=str)
        
        return True
    except Exception as e:
        print(f"Error actualizando analista: {e}")
        return False

def analista_existe(rfc):
    """Verificar si ya existe un analista con ese RFC"""
    try:
        analistas = cargar_analistas()
        return any(analista.get('rfc') == rfc for analista in analistas)
    except:
        return False

def generar_codigo_analista():
    """Generar código único de analista"""
    # Generar código alfanumérico
    codigo = 'E' + ''.join(random.choices(string.digits, k=3))
    
    # Verificar que no exista
    analistas = cargar_analistas()
    while any(analista.get('codigo') == codigo for analista in analistas):
        codigo = 'E' + ''.join(random.choices(string.digits, k=3))
    
    return codigo

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
            codigo = request.form.get('codigo', '').strip()
            nip = request.form.get('nip', '').strip()
            
            if not codigo or not nip:
                flash('Ingrese código y NIP', 'error')
                return render_template('login_analista.html')
            
            # Buscar analista
            analistas = cargar_analistas()
            analista = next((a for a in analistas if a.get('codigo') == codigo), None)
            
            if not analista:
                flash('Código de analista no encontrado', 'error')
                return render_template('login_analista.html')
            
            if analista.get('estado') != 'aprobado':
                flash('Su cuenta está pendiente de aprobación', 'warning')
                return render_template('login_analista.html')
            
            if analista.get('nip') != nip:
                flash('NIP incorrecto', 'error')
                return render_template('login_analista.html')
            
            # Login exitoso
            session['analista_id'] = analista.get('codigo')
            session['analista_nombre'] = analista.get('nombre')
            session['analista_rol'] = analista.get('rol', 'analista')
            
            flash(f'Bienvenido, {analista.get("nombre")}', 'success')
            
            # Redirigir según el rol
            if analista.get('rol') == 'admin':
                return redirect(url_for('panel_admin'))
            else:
                return redirect(url_for('captura_analista'))
                
        except Exception as e:
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
            
            # Verificar clave de administrador
            if clave == 'admin123':
                session['admin_activo'] = True
                session['analista_id'] = 'RAG123'
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

@app.route('/enregistro_analista', methods=['GET', 'POST'])
def enregistro_analista():
    """Registro de nuevo analista"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario de forma segura
            nombre_completo = request.form.get('nombre_completo', '').strip()
            rfc = request.form.get('rfc', '').strip().upper()
            telefono = request.form.get('telefono', '').strip()
            nip = request.form.get('nip', '').strip()
            
            # Validaciones básicas
            if not all([nombre_completo, rfc, telefono, nip]):
                flash('Todos los campos son obligatorios', 'error')
                return render_template('registro_analista.html')
            
            # Dividir nombre completo
            partes_nombre = nombre_completo.split()
            if len(partes_nombre) < 2:
                flash('Ingrese nombre y apellido completos', 'error')
                return render_template('registro_analista.html')
            
            nombre = partes_nombre[0]
            apellido_paterno = partes_nombre[1] if len(partes_nombre) > 1 else ''
            apellido_materno = ' '.join(partes_nombre[2:]) if len(partes_nombre) > 2 else ''
            
            # Validar RFC
            if len(rfc) != 13:
                flash('RFC debe tener 13 caracteres', 'error')
                return render_template('registro_analista.html')
            
            # Validar NIP
            if len(nip) != 4 or not nip.isdigit():
                flash('NIP debe ser de 4 dígitos numéricos', 'error')
                return render_template('registro_analista.html')
            
            # Verificar si ya existe
            if analista_existe(rfc):
                flash('Ya existe un analista con ese RFC', 'error')
                return render_template('registro_analista.html')
            
            # Generar código de analista
            codigo_analista = generar_codigo_analista()
            
            # Crear nuevo analista
            nuevo_analista = {
                'codigo': codigo_analista,
                'nombre': nombre,
                'apellido_paterno': apellido_paterno,
                'apellido_materno': apellido_materno,
                'rfc': rfc,
                'telefono': telefono,
                'nip': nip,
                'estado': 'pendiente',
                'rol': 'analista',
                'fecha_registro': datetime.now().isoformat()
            }
            
            # Guardar en la base de datos
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
    # Cargar estadísticas del analista
    analista_codigo = session.get('analista_id')
    
    # Aquí cargarías las solicitudes del analista desde la base de datos
    # Por ahora, datos de ejemplo
    estadisticas = {
        'solicitudes_totales': 15,
        'solicitudes_pendientes': 3,
        'solicitudes_aprobadas': 8,
        'solicitudes_rechazadas': 4,
        'monto_total_aprobado': 2500000
    }
    
    return render_template('captura_analista.html', stats=estadisticas)

@app.route('/panel_admin')
@login_required
def panel_admin():
    """Panel administrativo"""
    if session.get('analista_rol') != 'admin':
        flash('Acceso denegado. Solo administradores.', 'error')
        return redirect(url_for('captura_analista'))
    
    # Cargar analistas pendientes de aprobación
    analistas = cargar_analistas()
    pendientes = [a for a in analistas if a.get('estado') == 'pendiente']
    aprobados = [a for a in analistas if a.get('estado') == 'aprobado' and a.get('rol') != 'admin']
    
    estadisticas = {
        'total_analistas': len(analistas),
        'pendientes': len(pendientes),
        'aprobados': len(aprobados),
        'solicitudes_totales': 45,  # Esto vendría de la base de datos
        'solicitudes_hoy': 8
    }
    
    return render_template('panel_admin.html', 
                         analistas_pendientes=pendientes,
                         analistas_aprobados=aprobados,
                         stats=estadisticas)

@app.route('/aprobar_analista/<codigo>')
@login_required
def aprobar_analista(codigo):
    """Aprobar un analista pendiente"""
    if session.get('analista_rol') != 'admin':
        flash('Acceso denegado', 'error')
        return redirect(url_for('captura_analista'))
    
    if actualizar_analista(codigo, {'estado': 'aprobado'}):
        flash(f'Analista {codigo} aprobado exitosamente', 'success')
    else:
        flash('Error al aprobar el analista', 'error')
    
    return redirect(url_for('panel_admin'))

@app.route('/rechazar_analista/<codigo>')
@login_required
def rechazar_analista(codigo):
    """Rechazar un analista pendiente"""
    if session.get('analista_rol') != 'admin':
        flash('Acceso denegado', 'error')
        return redirect(url_for('captura_analista'))
    
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

# ===== RUTAS ADICIONALES PARA DESARROLLO FUTURO =====

@app.route('/nueva_solicitud')
@login_required
def nueva_solicitud():
    """Formulario para nueva solicitud de crédito"""
    return render_template('nueva_solicitud.html')

@app.route('/mis_solicitudes')
@login_required
def mis_solicitudes():
    """Ver solicitudes del analista"""
    return render_template('mis_solicitudes.html')

@app.route('/todas_solicitudes')
@login_required
def todas_solicitudes():
    """Ver todas las solicitudes (solo admin)"""
    if session.get('analista_rol') != 'admin':
        flash('Acceso denegado', 'error')
        return redirect(url_for('captura_analista'))
    
    return render_template('todas_solicitudes.html')

# ===== MANEJO DE ERRORES =====

@app.errorhandler(404)
def page_not_found(e):
    """Página no encontrada"""
    return render_template('error.html', error_code=404, error_message="Página no encontrada"), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Error interno del servidor"""
    return render_template('error.html', error_code=500, error_message="Error interno del servidor"), 500

# ===== INICIALIZACIÓN DE LA APLICACIÓN =====

if __name__ == '__main__':
    print("🚀 Iniciando Sistema de Análisis Crediticio...")
    print("📊 Usuarios por defecto:")
    print("   - Admin: RAG123 / admin123")
    print("   - Analista: E001 / 1234")
    print("🌐 Aplicación ejecutándose en: http://localhost:5000")
    
    # Crear archivos de datos si no existen
    cargar_analistas()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
