"""
Script de generación de datos para DiSQL.

Genera dos conjuntos de datos:

1. TABLAS PRINCIPALES (empleados y departamentos):
   - MariaDB (Granada):    empleados 1-3000,    departamentos 1-10
   - PostgreSQL (Madrid):  empleados 3001-6000,  departamentos 11-20
   - Oracle (Sevilla):     empleados 6001-9000,  departamentos 21-30

2. TABLAS DE ESCALABILIDAD (tabla9, tabla18, tabla27, tabla36):
   - tabla9:  9000 filas  (3000 por SGBD)
   - tabla18: 18000 filas (6000 por SGBD)
   - tabla27: 27000 filas (9000 por SGBD)
   - tabla36: 36000 filas (12000 por SGBD)
   Estas tablas se usan en el estudio de escalabilidad (estudio 4).

Antes de ejecutar este script, exporta las credenciales reales como
variables de entorno:
    export MARIADB_PASSWORD="..."
    export POSTGRES_PASSWORD="..."
    export ORACLE_PASSWORD="..."
"""

import random
import os
import pymysql
import psycopg2
import oracledb

# ─── DATOS DE CONEXIÓN ────────────────────────────────────────────────────────

MARIADB = {
    'host': '127.0.0.1', 'port': 10301,
    'user': 'root', 'password': os.environ.get('MARIADB_PASSWORD', ''),
    'database': 'disql'
}

POSTGRES = {
    'host': '127.0.0.1', 'port': 10303,
    'user': 'disql', 'password': os.environ.get('POSTGRES_PASSWORD', ''),
    'database': 'disql'
}

ORACLE = {
    'user': 'disql', 'password': os.environ.get('ORACLE_PASSWORD', ''),
    'dsn': '127.0.0.1:10302/poradba.pclab.localdomain'
}

# ─── DATOS DE EJEMPLO ─────────────────────────────────────────────────────────

NOMBRES = [
    'Ana', 'Carlos', 'Maria', 'Juan', 'Laura', 'Pedro', 'Sofia', 'Miguel',
    'Elena', 'David', 'Carmen', 'Antonio', 'Isabel', 'Francisco', 'Rosa',
    'Manuel', 'Pilar', 'Jose', 'Lucia', 'Rafael', 'Teresa', 'Alejandro',
    'Marta', 'Fernando', 'Cristina', 'Jorge', 'Patricia', 'Sergio', 'Beatriz',
    'Pablo', 'Natalia', 'Alberto', 'Silvia', 'Roberto', 'Monica', 'Daniel',
    'Raquel', 'Javier', 'Alicia', 'Andres'
]

APELLIDOS = [
    'Garcia', 'Martinez', 'Lopez', 'Sanchez', 'Gonzalez', 'Perez', 'Rodriguez',
    'Fernandez', 'Jimenez', 'Ruiz', 'Hernandez', 'Diaz', 'Moreno', 'Alvarez',
    'Romero', 'Alonso', 'Gutierrez', 'Navarro', 'Torres', 'Dominguez',
    'Vazquez', 'Ramos', 'Gil', 'Serrano', 'Blanco', 'Molina', 'Morales',
    'Suarez', 'Ortega', 'Castro'
]

NOMBRES_DEPARTAMENTOS = [
    'Informatica', 'Recursos Humanos', 'Contabilidad', 'Marketing',
    'Ventas', 'Logistica', 'Legal', 'Direccion', 'Investigacion', 'Soporte'
]

CIUDADES_GRANADA = ['Granada', 'Motril', 'Guadix', 'Baza', 'Loja']
CIUDADES_MADRID = ['Madrid', 'Alcala', 'Getafe', 'Leganes', 'Mostoles']
CIUDADES_SEVILLA = ['Sevilla', 'Dos Hermanas', 'Ecija', 'Utrera', 'Carmona']


def nombre_aleatorio():
    return f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"


def salario_aleatorio():
    return round(random.uniform(1800, 6000), 2)


# ─── TABLAS PRINCIPALES ───────────────────────────────────────────────────────

def poblar_mariadb_principal():
    print("Conectando a MariaDB (tablas principales)...")
    conn = pymysql.connect(**MARIADB, autocommit=True)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM empleados")
    cursor.execute("DELETE FROM departamentos")
    print("  Tablas vaciadas.")

    for i in range(1, 11):
        nombre = NOMBRES_DEPARTAMENTOS[(i - 1) % len(NOMBRES_DEPARTAMENTOS)]
        ciudad = random.choice(CIUDADES_GRANADA)
        cursor.execute(
            "INSERT INTO departamentos (id, nombre, ciudad) VALUES (%s, %s, %s)",
            (i, nombre, ciudad))
    print("  Departamentos 1-10 insertados.")

    for i in range(1, 3001):
        dept = random.randint(1, 10)
        cursor.execute(
            "INSERT INTO empleados (id, nombre, salario, departamento) VALUES (%s, %s, %s, %s)",
            (i, nombre_aleatorio(), salario_aleatorio(), dept))
        if i % 500 == 0:
            print(f"  MariaDB: {i}/3000 empleados...")

    print("MariaDB principal completado: 3000 empleados, 10 departamentos.")
    cursor.close()
    conn.close()


def poblar_postgres_principal():
    print("Conectando a PostgreSQL (tablas principales)...")
    conn = psycopg2.connect(**POSTGRES)
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute("DELETE FROM empleados")
    cursor.execute("DELETE FROM departamentos")
    print("  Tablas vaciadas.")

    for i in range(11, 21):
        nombre = NOMBRES_DEPARTAMENTOS[(i - 1) % len(NOMBRES_DEPARTAMENTOS)]
        ciudad = random.choice(CIUDADES_MADRID)
        cursor.execute(
            "INSERT INTO departamentos (id, nombre, ciudad) VALUES (%s, %s, %s)",
            (i, nombre, ciudad))
    print("  Departamentos 11-20 insertados.")

    for i in range(3001, 6001):
        dept = random.randint(11, 20)
        cursor.execute(
            "INSERT INTO empleados (id, nombre, salario, departamento) VALUES (%s, %s, %s, %s)",
            (i, nombre_aleatorio(), salario_aleatorio(), dept))
        if i % 500 == 0:
            print(f"  PostgreSQL: {i-3000}/3000 empleados...")

    print("PostgreSQL principal completado: 3000 empleados, 10 departamentos.")
    cursor.close()
    conn.close()


def poblar_oracle_principal():
    print("Conectando a Oracle (tablas principales)...")
    conn = oracledb.connect(**ORACLE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM empleados")
    cursor.execute("DELETE FROM departamentos")
    conn.commit()
    print("  Tablas vaciadas.")

    for i in range(21, 31):
        nombre = NOMBRES_DEPARTAMENTOS[(i - 1) % len(NOMBRES_DEPARTAMENTOS)]
        ciudad = random.choice(CIUDADES_SEVILLA)
        cursor.execute(
            "INSERT INTO departamentos (id, nombre, ciudad) VALUES (:1, :2, :3)",
            (i, nombre, ciudad))
    conn.commit()
    print("  Departamentos 21-30 insertados.")

    for i in range(6001, 9001):
        dept = random.randint(21, 30)
        cursor.execute(
            "INSERT INTO empleados (id, nombre, salario, departamento) VALUES (:1, :2, :3, :4)",
            (i, nombre_aleatorio(), salario_aleatorio(), dept))
        if i % 500 == 0:
            conn.commit()
            print(f"  Oracle: {i-6000}/3000 empleados...")

    conn.commit()
    print("Oracle principal completado: 3000 empleados, 10 departamentos.")
    cursor.close()
    conn.close()


# ─── TABLAS DE ESCALABILIDAD ──────────────────────────────────────────────────

def crear_tabla_escalabilidad_mariadb(conn, nombre_tabla):
    """Crea la tabla de escalabilidad en MariaDB si no existe."""
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {nombre_tabla} (
            id      INT PRIMARY KEY,
            nombre  VARCHAR(100),
            salario DECIMAL(10,2),
            departamento INT
        )
    """)
    cursor.execute(f"DELETE FROM {nombre_tabla}")
    cursor.close()


def crear_tabla_escalabilidad_postgres(conn, nombre_tabla):
    """Crea la tabla de escalabilidad en PostgreSQL si no existe."""
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {nombre_tabla} (
            id      INTEGER PRIMARY KEY,
            nombre  VARCHAR(100),
            salario NUMERIC(10,2),
            departamento INTEGER
        )
    """)
    cursor.execute(f"DELETE FROM {nombre_tabla}")
    cursor.close()


def crear_tabla_escalabilidad_oracle(conn, nombre_tabla):
    """Crea la tabla de escalabilidad en Oracle si no existe."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            CREATE TABLE {nombre_tabla} (
                id      NUMBER PRIMARY KEY,
                nombre  VARCHAR2(100),
                salario NUMBER(10,2),
                departamento NUMBER
            )
        """)
    except Exception:
        # La tabla ya existe
        cursor.execute(f"DELETE FROM {nombre_tabla}")
    conn.commit()
    cursor.close()


def poblar_tabla_escalabilidad(nombre_tabla, filas_por_sgbd):
    """
    Inserta filas_por_sgbd filas en cada SGBD para la tabla de escalabilidad.
    Total: filas_por_sgbd * 3 filas distribuidas entre los tres SGBDs.
    """
    total = filas_por_sgbd * 3
    print(f"\nGenerando {nombre_tabla} ({total} filas totales, {filas_por_sgbd} por SGBD)...")

    # MariaDB
    conn_m = pymysql.connect(**MARIADB, autocommit=True)
    crear_tabla_escalabilidad_mariadb(conn_m, nombre_tabla)
    cursor_m = conn_m.cursor()
    inicio = 1
    for i in range(inicio, inicio + filas_por_sgbd):
        cursor_m.execute(
            f"INSERT INTO {nombre_tabla} (id, nombre, salario, departamento) VALUES (%s, %s, %s, %s)",
            (i, nombre_aleatorio(), salario_aleatorio(), random.randint(1, 10)))
        if i % 1000 == 0:
            print(f"  MariaDB {nombre_tabla}: {i}/{filas_por_sgbd}...")
    cursor_m.close()
    conn_m.close()
    print(f"  MariaDB {nombre_tabla}: {filas_por_sgbd} filas insertadas.")

    # PostgreSQL
    conn_p = psycopg2.connect(**POSTGRES)
    conn_p.autocommit = True
    crear_tabla_escalabilidad_postgres(conn_p, nombre_tabla)
    cursor_p = conn_p.cursor()
    inicio = filas_por_sgbd + 1
    for i in range(inicio, inicio + filas_por_sgbd):
        cursor_p.execute(
            f"INSERT INTO {nombre_tabla} (id, nombre, salario, departamento) VALUES (%s, %s, %s, %s)",
            (i, nombre_aleatorio(), salario_aleatorio(), random.randint(11, 20)))
        if i % 1000 == 0:
            print(f"  PostgreSQL {nombre_tabla}: {i-filas_por_sgbd}/{filas_por_sgbd}...")
    cursor_p.close()
    conn_p.close()
    print(f"  PostgreSQL {nombre_tabla}: {filas_por_sgbd} filas insertadas.")

    # Oracle
    conn_o = oracledb.connect(**ORACLE)
    crear_tabla_escalabilidad_oracle(conn_o, nombre_tabla)
    cursor_o = conn_o.cursor()
    inicio = filas_por_sgbd * 2 + 1
    for i in range(inicio, inicio + filas_por_sgbd):
        cursor_o.execute(
            f"INSERT INTO {nombre_tabla} (id, nombre, salario, departamento) VALUES (:1, :2, :3, :4)",
            (i, nombre_aleatorio(), salario_aleatorio(), random.randint(21, 30)))
        if i % 1000 == 0:
            conn_o.commit()
            print(f"  Oracle {nombre_tabla}: {i-filas_por_sgbd*2}/{filas_por_sgbd}...")
    conn_o.commit()
    cursor_o.close()
    conn_o.close()
    print(f"  Oracle {nombre_tabla}: {filas_por_sgbd} filas insertadas.")
    print(f"{nombre_tabla} completada: {total} filas totales.")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'

    if modo in ('todo', 'principal'):
        print("=" * 60)
        print("TABLAS PRINCIPALES (empleados y departamentos)")
        print("=" * 60)
        poblar_mariadb_principal()
        print()
        poblar_postgres_principal()
        print()
        poblar_oracle_principal()
        print("\nTablas principales completadas:")
        print("  MariaDB:    empleados 1-3000,    departamentos 1-10")
        print("  PostgreSQL: empleados 3001-6000, departamentos 11-20")
        print("  Oracle:     empleados 6001-9000, departamentos 21-30")

    if modo in ('todo', 'escalabilidad'):
        print("\n" + "=" * 60)
        print("TABLAS DE ESCALABILIDAD")
        print("=" * 60)
        # filas_por_sgbd = total / 3
        poblar_tabla_escalabilidad("tabla9",  3000)   # 9000  total
        poblar_tabla_escalabilidad("tabla18", 6000)   # 18000 total
        poblar_tabla_escalabilidad("tabla27", 9000)   # 27000 total
        poblar_tabla_escalabilidad("tabla36", 12000)  # 36000 total
        print("\nTablas de escalabilidad completadas:")
        print("  tabla9:  9000  filas (3000  por SGBD)")
        print("  tabla18: 18000 filas (6000  por SGBD)")
        print("  tabla27: 27000 filas (9000  por SGBD)")
        print("  tabla36: 36000 filas (12000 por SGBD)")

    print("\n=== Generacion completada ===")