import sys
import os
import importlib
import csv  # <- Añadido para la gestión del archivo
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, session, Response, stream_with_context # <- Añadidos Response y stream_with_context
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.abstracto.controlador import Controlador
from src.catalogo import Catalogo
from src.encriptacion import Encriptacion

app = Flask(__name__)
# Clave secreta para gestionar la sesion del admin
app.secret_key = 'disql_admin_secret_key'
app.permanent_session_lifetime = timedelta(hours=2)

# Credenciales de administrador
ADMIN_USUARIO = 'admin'
ADMIN_CONTRASENA = 'admin'

# Tipos de SGBD soportados
NOMBRES_CLASES = {
    'mariadb': 'MariaDB',
    'postgres': 'Postgres',
    'oracle': 'Oracle'
}

# Iniciamos el controlador al arrancar la app
controlador = Controlador()
controlador.iniciar_sistema()

# Catalogo y encriptacion para el panel admin
catalogo = Catalogo()
encriptacion = Encriptacion()

def serializar_fila(fila):
    """
    Convierte los tipos especiales de Python (Decimal, etc.) a strings
    para que Flask pueda serializarlos correctamente.
    """
    resultado = {}
    for clave, valor in fila.items():
        if isinstance(valor, Decimal):
            resultado[clave] = str(valor)
        else:
            resultado[clave] = valor
    return resultado

def admin_requerido(f):
    """
    Decorador que redirige al login si el admin no está autenticado.
    """
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

def obtener_tablas_catalogo():
    """
    Devuelve todas las tablas del catálogo con su SGBD asociado.
    """
    cursor = catalogo.conexion.cursor()
    cursor.execute("""
        SELECT tabla.id, tabla.nombre, sgbd.tipo, sgbd.id as sgbd_id
        FROM tabla
        JOIN sgbd ON tabla.sgbd_id = sgbd.id
        ORDER BY tabla.nombre, sgbd.tipo
    """)
    filas = cursor.fetchall()
    cursor.close()
    return [{'id': f[0], 'nombre': f[1], 'tipo': f[2], 'sgbd_id': f[3]} for f in filas]

# ─── RUTA PRINCIPAL ───────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Ruta principal. GET muestra el formulario vacío.
    POST ejecuta la consulta y devuelve los resultados.
    """
    resultados = []
    columnas = []
    error = None
    sql = ''

    if request.method == 'POST':
        sql = request.form.get('sql', '').strip()
        if sql:
            try:
                filas = [serializar_fila(fila) for fila in controlador.procesar_consulta(sql)]
                if filas:
                    columnas = [col for col in filas[0].keys() if col != '_sgbd']
                    resultados = filas
            except Exception as e:
                error = str(e)

    return render_template('index.html',
                           resultados=resultados,
                           columnas=columnas,
                           error=error,
                           sql=sql)


# ─── NUEVA RUTA: DESCARGA EN STREAMING SIN METAINFORMACIÓN ────────────────────

@app.route('/descargar_csv', methods=['POST'])
def descargar_csv():
    """
    Genera un archivo CSV al vuelo (streaming) con el resultado de la consulta.
    Elimina la columna de control '_sgbd' para cumplir con la transparencia.
    """
    sql = request.form.get('sql', '').strip()
    if not sql:
        return redirect(url_for('index'))

    try:
        # Obtenemos el generador puro del motor distribuido sin acumular en una lista
        generador_filas = controlador.procesar_consulta(sql)

        def generar_contenido_csv():
            # Clase auxiliar para escribir en texto plano a través del buffer de Flask
            class Echo:
                def write(self, value): return value
            
            escritor = csv.writer(Echo())
            cabecera_escrita = False

            for fila in generador_filas:
                # Copiamos la fila para no mutar los datos originales
                fila_limpia = fila.copy()
                
                # ¡TRUCO DEL TUTOR!: Eliminamos por completo la procedencia del SGBD
                if '_sgbd' in fila_limpia:
                    del fila_limpia['_sgbd']
                
                # Si es el primer registro, volcamos los nombres reales de las columnas en la cabecera del archivo
                if not cabecera_escrita:
                    yield escritor.writerow(fila_limpia.keys())
                    cabecera_escrita = True
                
                # Volcamos los valores del registro
                yield escritor.writerow(fila_limpia.values())

        # Devolvemos la respuesta en streaming directo al navegador
        return Response(
            stream_with_context(generar_contenido_csv()),
            mimetype='text/csv',
            headers={"Content-disposition": f"attachment; filename=resultado_disql.csv"}
        )

    except Exception as e:
        return f"Error al generar la descarga: {e}", 500


# ─── ADMIN LOGIN ──────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Página de login del panel de administración.
    """
    error = None
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        contrasena = request.form.get('contrasena', '').strip()
        if usuario == ADMIN_USUARIO and contrasena == ADMIN_CONTRASENA:
            session['admin'] = True
            session.permanent = True
            return redirect(url_for('admin_panel'))
        else:
            error = 'Credenciales incorrectas.'
    return render_template('admin_login.html', error=error)


# ─── ADMIN PANEL ──────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_requerido
def admin_panel():
    """
    Panel principal de administración.
    Muestra los SGBDs y tablas registrados.
    """
    sgbds = catalogo.obtener_sgbds()
    tablas = obtener_tablas_catalogo()
    mensaje = request.args.get('mensaje')
    error = request.args.get('error')
    return render_template('admin.html', sgbds=sgbds, tablas=tablas,
                           mensaje=mensaje, error=error)

# ─── AÑADIR SGBD ──────────────────────────────────────────────────────────────

@app.route('/admin/anadir', methods=['GET', 'POST'])
@admin_requerido
def admin_anadir():
    """
    Formulario para añadir un nuevo SGBD al catálogo.
    Al guardar, autodescubre las tablas del SGBD.
    """
    error = None
    if request.method == 'POST':
        tipo = request.form.get('tipo', '').strip().lower()
        host = request.form.get('host', '').strip()
        puerto = request.form.get('puerto', '').strip()
        usuario = request.form.get('usuario', '').strip()
        contrasena = request.form.get('contrasena', '').strip()
        base_datos = request.form.get('base_datos', '').strip()

        if tipo not in NOMBRES_CLASES:
            error = f"Tipo '{tipo}' no soportado. Tipos válidos: {', '.join(NOMBRES_CLASES.keys())}"
        else:
            try:
                puerto_bd = int(puerto)
                contrasena_enc = encriptacion.encriptar(contrasena)
                sgbd_id = catalogo.insertar_sgbd(tipo, host, puerto_bd, usuario,
                                                  contrasena_enc, base_datos)

                # Autodescubrimiento de tablas
                nombre = NOMBRES_CLASES[tipo]
                modulo_conector = importlib.import_module(f"src.{tipo}.conector_{tipo}")
                clase_conector = getattr(modulo_conector, f"Conector{nombre}")
                conector = clase_conector(host=host, puerto=puerto_bd, usuario=usuario,
                                          contrasena=contrasena, base_datos=base_datos)

                modulo_ctrl = importlib.import_module(f"src.{tipo}.controlador_sistema_{tipo}")
                clase_ctrl = getattr(modulo_ctrl, f"ControladorSistema{nombre}")
                ctrl_sistema = clase_ctrl(conector)
                ctrl_sistema.iniciar()
                tablas = ctrl_sistema.obtener_tablas_usuario()
                for tabla in tablas:
                    catalogo.insertar_tabla(tabla, sgbd_id)
                ctrl_sistema.detener()

                return redirect(url_for('admin_panel',
                    mensaje=f"SGBD '{tipo}' añadido correctamente con {len(tablas)} tabla(s)."))
            except Exception as e:
                error = str(e)

    return render_template('admin_anadir.html', tipos=list(NOMBRES_CLASES.keys()), error=error)

# ─── ELIMINAR SGBD ────────────────────────────────────────────────────────────

@app.route('/admin/eliminar_sgbd/<int:sgbd_id>', methods=['POST'])
@admin_requerido
def admin_eliminar_sgbd(sgbd_id):
    """Elimina un SGBD y todas sus tablas del catálogo."""
    try:
        catalogo.eliminar_sgbd(sgbd_id)
        return redirect(url_for('admin_panel', mensaje='SGBD eliminado correctamente.'))
    except Exception as e:
        return redirect(url_for('admin_panel', error=str(e)))

# ─── ELIMINAR TABLA ───────────────────────────────────────────────────────────

@app.route('/admin/eliminar_tabla/<int:tabla_id>', methods=['POST'])
@admin_requerido
def admin_eliminar_tabla(tabla_id):
    """Elimina una tabla del catálogo."""
    try:
        catalogo.eliminar_tabla(tabla_id)
        return redirect(url_for('admin_panel', mensaje='Tabla eliminada correctamente.'))
    except Exception as e:
        return redirect(url_for('admin_panel', error=str(e)))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)