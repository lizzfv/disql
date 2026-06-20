"""
Script de medición de rendimiento para DiSQL.
Genera cinco estudios de eficiencia:
1. Tiempo de respuesta por tipo de consulta (10 repeticiones)
2. Rendimiento por SGBD individual sin tiempo de conexión (10 repeticiones)
3. Tamaño en memoria: streaming vs materialización
4. Escalabilidad: tiempo según volumen de datos (9000, 18000, 27000, 36000 filas)
5. Efecto del arraysize en Oracle (10 repeticiones)

Antes de ejecutar este script, exporta las credenciales reales como
variables de entorno:
    export MARIADB_PASSWORD="..."
    export POSTGRES_PASSWORD="..."
    export ORACLE_PASSWORD="..."
"""

import time
import os
import sys
import pymysql
import psycopg2
import oracledb
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.abstracto.controlador import Controlador

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

REPETICIONES = 10
ORACLE_ARRAYSIZE = 3000  # mismo valor que el aplicado en ConectorOracle

MARIADB_CONN = {
    'host': '127.0.0.1', 'port': 10301,
    'user': 'root', 'password': os.environ.get('MARIADB_PASSWORD', ''),
    'database': 'disql', 'autocommit': True
}

POSTGRES_CONN = {
    'host': '127.0.0.1', 'port': 10303,
    'user': 'disql', 'password': os.environ.get('POSTGRES_PASSWORD', ''),
    'database': 'disql'
}

ORACLE_CONN = {
    'user': 'disql', 'password': os.environ.get('ORACLE_PASSWORD', ''),
    'dsn': '127.0.0.1:10302/poradba.pclab.localdomain'
}

COLORES = {
    'mariadb':     '#4CAF50',
    'postgres':    '#2196F3',
    'oracle':      '#FF9800',
    'disql':       '#9C27B0',
    'streaming':   '#4CAF50',
    'tradicional': '#F44336',
}

# ─── UTILIDADES ───────────────────────────────────────────────────────────────

def medir_tiempos_repetidos(funcion, repeticiones, *args, **kwargs):
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion(*args, **kwargs)
        fin = time.perf_counter()
        tiempos.append((fin - inicio) * 1000)
    return np.mean(tiempos), np.std(tiempos)


def tamanio_objeto_bytes(obj):
    total = sys.getsizeof(obj)
    for fila in obj:
        total += sys.getsizeof(fila)
        for k, v in fila.items():
            total += sys.getsizeof(k)
            total += sys.getsizeof(v)
    return total


# ─── ESTUDIO 1: TIEMPO POR TIPO DE CONSULTA ───────────────────────────────────

def ejecutar_consulta_disql(controlador, sql):
    list(controlador.procesar_consulta(sql))


def estudio_1_tipos_consulta(controlador):
    print(f"\n=== ESTUDIO 1: Tiempo por tipo de consulta ({REPETICIONES} repeticiones) ===")

    consultas = [
        ("SELECT simple",  "SELECT * FROM empleados"),
        ("WHERE",          "SELECT * FROM empleados WHERE salario > 3000"),
        ("ORDER BY ASC",   "SELECT * FROM empleados ORDER BY salario ASC"),
        ("ORDER BY DESC",  "SELECT * FROM empleados ORDER BY salario DESC"),
        ("COUNT",          "SELECT COUNT(*) FROM empleados"),
        ("SUM",            "SELECT SUM(salario) FROM empleados"),
        ("AVG",            "SELECT AVG(salario) FROM empleados"),
        ("MAX",            "SELECT MAX(salario) FROM empleados"),
        ("MIN",            "SELECT MIN(salario) FROM empleados"),
        ("GROUP BY",       "SELECT departamento, COUNT(*) FROM empleados GROUP BY departamento"),
    ]

    etiquetas, medias, desviaciones = [], [], []

    for nombre, sql in consultas:
        media, std = medir_tiempos_repetidos(ejecutar_consulta_disql, REPETICIONES, controlador, sql)
        etiquetas.append(nombre)
        medias.append(media)
        desviaciones.append(std)
        print(f"  {nombre:20s}: {media:.1f} ms +- {std:.1f} ms")

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(etiquetas))
    barras = ax.bar(x, medias, color=COLORES['disql'], alpha=0.85,
                    edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Tipo de consulta', fontsize=12)
    ax.set_ylabel('Tiempo de respuesta (ms)', fontsize=12)
    ax.set_title(
        f'Estudio de eficiencia 1: Tiempo de respuesta por tipo de consulta\n'
        f'(media de {REPETICIONES} ejecuciones, 9000 filas distribuidas en 3 SGBDs)', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=30, ha='right', fontsize=10)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    for barra, media in zip(barras, medias):
        ax.text(barra.get_x() + barra.get_width() / 2, barra.get_height() + 5,
                f'{media:.0f}ms', ha='center', va='bottom', fontsize=9)
    plt.tight_layout()
    plt.savefig('estudio1_tipos_consulta.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Guardada: estudio1_tipos_consulta.png")


# ─── ESTUDIO 2: RENDIMIENTO POR SGBD SIN TIEMPO DE CONEXION ──────────────────

def estudio_2_por_sgbd():
    print(f"\n=== ESTUDIO 2: Rendimiento por SGBD ({REPETICIONES} repeticiones) ===")
    print("  Conexiones abiertas antes de medir — tiempo de conexion excluido")
    print(f"  Oracle usa arraysize={ORACLE_ARRAYSIZE} (igual que ConectorOracle)")

    # Abrimos las conexiones UNA SOLA VEZ
    print("  Abriendo conexiones...")
    conn_mariadb = pymysql.connect(**MARIADB_CONN)
    conn_postgres = psycopg2.connect(**POSTGRES_CONN)
    conn_postgres.autocommit = True
    conn_oracle = oracledb.connect(**ORACLE_CONN)
    print("  Conexiones abiertas.\n")

    def ejecutar_mariadb(sql):
        cursor = conn_mariadb.cursor()
        cursor.execute(sql)
        cursor.fetchall()
        cursor.close()

    def ejecutar_postgres(sql):
        cursor = conn_postgres.cursor()
        cursor.execute(sql)
        cursor.fetchall()
        cursor.close()

    def ejecutar_oracle(sql):
        cursor = conn_oracle.cursor()
        cursor.arraysize = ORACLE_ARRAYSIZE
        cursor.execute(sql)
        cursor.fetchall()
        cursor.close()

    consultas = [
        ("SELECT simple", "SELECT * FROM empleados"),
        ("ORDER BY",      "SELECT * FROM empleados ORDER BY salario ASC"),
        ("COUNT",         "SELECT COUNT(*) FROM empleados"),
        ("AVG",           "SELECT AVG(salario) FROM empleados"),
        ("GROUP BY",      "SELECT departamento, COUNT(*) FROM empleados GROUP BY departamento"),
    ]

    sgbds = [
        ("MariaDB",    ejecutar_mariadb,  COLORES['mariadb']),
        ("PostgreSQL", ejecutar_postgres, COLORES['postgres']),
        ("Oracle",     ejecutar_oracle,   COLORES['oracle']),
    ]

    resultados = {nombre: {'medias': [], 'stds': []} for nombre, _, _ in sgbds}
    etiquetas_consultas = [nombre for nombre, _ in consultas]

    for nombre_sgbd, funcion, _ in sgbds:
        print(f"  {nombre_sgbd}:")
        for nombre_consulta, sql in consultas:
            media, std = medir_tiempos_repetidos(funcion, REPETICIONES, sql)
            resultados[nombre_sgbd]['medias'].append(media)
            resultados[nombre_sgbd]['stds'].append(std)
            print(f"    {nombre_consulta:20s}: {media:.1f} ms +- {std:.1f} ms")

    # Cerramos conexiones al final
    conn_mariadb.close()
    conn_postgres.close()
    conn_oracle.close()
    print("\n  Conexiones cerradas.")

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(etiquetas_consultas))
    ancho = 0.25
    offsets = [-ancho, 0, ancho]
    for i, (nombre_sgbd, _, color) in enumerate(sgbds):
        ax.bar(x + offsets[i], resultados[nombre_sgbd]['medias'], ancho,
               label=nombre_sgbd, color=color, alpha=0.85, edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Tipo de consulta', fontsize=12)
    ax.set_ylabel('Tiempo de respuesta (ms)', fontsize=12)
    ax.set_title(
        f'Estudio de eficiencia 2: Rendimiento por SGBD individual\n'
        f'(media de {REPETICIONES} ejecuciones, 3000 filas por SGBD, sin tiempo de conexion)',
        fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas_consultas, fontsize=10)
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig('estudio2_por_sgbd.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Guardada: estudio2_por_sgbd.png")


# ─── ESTUDIO 5: EFECTO DEL ARRAYSIZE EN ORACLE ───────────────────────────────

def estudio_5_arraysize():
    print(f"\n=== ESTUDIO 5: Efecto del arraysize en Oracle ({REPETICIONES} repeticiones) ===")

    conn_oracle = oracledb.connect(**ORACLE_CONN)

    sql = "SELECT * FROM empleados"
    tamanos = [100, 1000, 3000]
    medias = []

    for tamano in tamanos:
        def ejecutar_con_arraysize(sql, tamano=tamano):
            cursor = conn_oracle.cursor()
            cursor.arraysize = tamano
            cursor.execute(sql)
            cursor.fetchall()
            cursor.close()

        media, std = medir_tiempos_repetidos(ejecutar_con_arraysize, REPETICIONES, sql)
        medias.append(media)
        print(f"  arraysize={tamano:5d}: {media:.1f} ms +- {std:.1f} ms")

    conn_oracle.close()

    fig, ax = plt.subplots(figsize=(9, 6))
    etiquetas = [f'arraysize={t}' for t in tamanos]
    barras = ax.bar(etiquetas, medias, color=COLORES['oracle'], alpha=0.85,
                    edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Configuracion del driver', fontsize=12)
    ax.set_ylabel('Tiempo de respuesta (ms)', fontsize=12)
    ax.set_title(
        f'Estudio de eficiencia 5: Efecto del arraysize en Oracle\n'
        f'(media de {REPETICIONES} ejecuciones, SELECT simple, 3000 filas)', fontsize=13)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    for barra, media in zip(barras, medias):
        ax.text(barra.get_x() + barra.get_width() / 2, barra.get_height() + 5,
                f'{media:.0f}ms', ha='center', va='bottom', fontsize=10, fontweight='bold')
    plt.tight_layout()
    plt.savefig('estudio5_arraysize.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Guardada: estudio5_arraysize.png")


# ─── ESTUDIO 3: MEMORIA STREAMING VS MATERIALIZACION ─────────────────────────

def estudio_3_memoria(controlador):
    print("\n=== ESTUDIO 3: Memoria streaming vs materializacion ===")

    limites = [500, 1000, 2000, 3000, 6000, 9000]
    tamanios_streaming = []
    tamanios_tradicional = []

    for limite in limites:
        sql = "SELECT * FROM empleados ORDER BY salario ASC"
        lista = list(controlador.procesar_consulta(sql))[:limite]
        tam_tradicional = tamanio_objeto_bytes(lista) / 1024
        del lista
        gen = controlador.procesar_consulta(sql)
        fila_actual = next(gen)
        tam_streaming = sys.getsizeof(fila_actual) / 1024
        gen.close()
        tamanios_streaming.append(tam_streaming)
        tamanios_tradicional.append(tam_tradicional)
        print(f"  {limite:5d} filas → streaming: {tam_streaming:.1f} KB, "
              f"materializacion: {tam_tradicional:.1f} KB")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(limites, tamanios_tradicional, 'o-', color=COLORES['tradicional'],
            linewidth=2.5, markersize=7, label='Materializacion (enfoque tradicional)')
    ax.plot(limites, tamanios_streaming, 's-', color=COLORES['streaming'],
            linewidth=2.5, markersize=7, label='Streaming (DiSQL)')
    ax.fill_between(limites, tamanios_streaming, tamanios_tradicional,
                    alpha=0.1, color=COLORES['tradicional'])
    ax.set_xlabel('Numero de filas procesadas', fontsize=12)
    ax.set_ylabel('Memoria utilizada (KB)', fontsize=12)
    ax.set_title('Estudio de eficiencia 3: Memoria utilizada\n'
                 'streaming vs materializacion segun volumen de datos', fontsize=13)
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_xticks(limites)
    ax.set_xticklabels([str(l) for l in limites])
    ax.annotate(f'{tamanios_tradicional[-1]:.0f} KB',
                xy=(limites[-1], tamanios_tradicional[-1]),
                xytext=(-60, 10), textcoords='offset points',
                fontsize=10, color=COLORES['tradicional'], fontweight='bold')
    ax.annotate(f'{tamanios_streaming[-1]:.1f} KB',
                xy=(limites[-1], tamanios_streaming[-1]),
                xytext=(-60, -20), textcoords='offset points',
                fontsize=10, color=COLORES['streaming'], fontweight='bold')
    plt.tight_layout()
    plt.savefig('estudio3_memoria.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Guardada: estudio3_memoria.png")


# ─── ESTUDIO 4: ESCALABILIDAD SEGUN VOLUMEN DE DATOS ─────────────────────────

def estudio_4_escalabilidad(controlador):
    """
    Ejecuta las mismas consultas sobre tablas con distintos volumenes de datos.
    Las tablas deben existir previamente en el catalogo DiSQL:
    tabla9 (9000 filas), tabla18 (18000), tabla27 (27000), tabla36 (36000)
    """
    print(f"\n=== ESTUDIO 4: Escalabilidad segun volumen ({REPETICIONES} repeticiones) ===")

    tablas = [
        (9000,  "tabla9"),
        (18000, "tabla18"),
        (27000, "tabla27"),
        (36000, "tabla36"),
    ]

    consultas = [
        ("SELECT simple", "SELECT * FROM {tabla}"),
        ("WHERE",         "SELECT * FROM {tabla} WHERE salario > 3000"),
        ("ORDER BY",      "SELECT * FROM {tabla} ORDER BY salario ASC"),
        ("COUNT",         "SELECT COUNT(*) FROM {tabla}"),
        ("AVG",           "SELECT AVG(salario) FROM {tabla}"),
    ]

    resultados = {nombre: [] for nombre, _ in consultas}
    volumenes = [v for v, _ in tablas]

    for volumen, tabla in tablas:
        print(f"\n  Tabla: {tabla} ({volumen} filas)")
        for nombre_consulta, sql_template in consultas:
            sql = sql_template.format(tabla=tabla)
            media, std = medir_tiempos_repetidos(
                ejecutar_consulta_disql, REPETICIONES, controlador, sql)
            resultados[nombre_consulta].append(media)
            print(f"    {nombre_consulta:20s}: {media:.1f} ms +- {std:.1f} ms")

    fig, ax = plt.subplots(figsize=(11, 6))
    colores_lineas = ['#9C27B0', '#2196F3', '#4CAF50', '#FF9800', '#F44336']
    for i, (nombre_consulta, _) in enumerate(consultas):
        ax.plot(volumenes, resultados[nombre_consulta], 'o-',
                linewidth=2.5, markersize=7,
                color=colores_lineas[i], label=nombre_consulta)
    ax.set_xlabel('Numero de filas en la tabla', fontsize=12)
    ax.set_ylabel('Tiempo de respuesta (ms)', fontsize=12)
    ax.set_title(
        f'Estudio de eficiencia 4: Escalabilidad segun volumen de datos\n'
        f'(media de {REPETICIONES} ejecuciones por punto)', fontsize=13)
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_xticks(volumenes)
    ax.set_xticklabels([f'{v:,}' for v in volumenes])
    plt.tight_layout()
    plt.savefig('estudio4_escalabilidad.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Guardada: estudio4_escalabilidad.png")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Estudio de eficiencia DiSQL ===")
    print(f"Cada consulta se repite {REPETICIONES} veces\n")

    print("Iniciando sistema DiSQL...")
    controlador = Controlador()
    controlador.iniciar_sistema()
    print("Sistema iniciado.\n")

    estudio_1_tipos_consulta(controlador)
    estudio_2_por_sgbd()
    estudio_5_arraysize()
    estudio_3_memoria(controlador)
    estudio_4_escalabilidad(controlador)

    controlador.detener_sistema()

    print("\n=== Mediciones completadas ===")
    print("Archivos generados:")
    print("  estudio1_tipos_consulta.png")
    print("  estudio2_por_sgbd.png")
    print("  estudio5_arraysize.png")
    print("  estudio3_memoria.png")
    print("  estudio4_escalabilidad.png")