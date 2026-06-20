import sys
import os
import importlib

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.catalogo import Catalogo
from src.encriptacion import Encriptacion

encriptacion = Encriptacion()
catalogo = Catalogo()

NOMBRES_CLASES = {
    'mariadb': 'MariaDB',
    'postgres': 'Postgres',
    'oracle': 'Oracle'
}

def menu():
    while True:
        print("\n=============================")
        print("   Gestor del Catalogo DiSQL")
        print("=============================")
        print("1. Anadir SGBD")
        print("2. Ver SGBDs registrados")
        print("3. Ver tablas registradas")
        print("4. Eliminar SGBD")
        print("5. Eliminar tabla")
        print("6. Salir")
        print("=============================")
        opcion = input("Elige una opcion (x para salir): ").strip()

        if opcion == '1':
            anadir_sgbd()
        elif opcion == '2':
            ver_sgbds()
        elif opcion == '3':
            ver_tablas()
        elif opcion == '4':
            eliminar_sgbd()
        elif opcion == '5':
            eliminar_tabla()
        elif opcion in ('6', 'x'):
            catalogo.cerrar()
            print("Hasta luego.")
            break
        else:
            print("Opcion no valida.")

def pedir_dato(campo, valor_actual=None):
    """
    Pide un dato mostrando el valor actual entre corchetes.
    Si pulsa Enter sin escribir nada mantiene el valor actual.
    Devuelve None si el usuario escribe x para cancelar.
    """
    if valor_actual is not None:
        entrada = input(f"{campo} [{valor_actual}] (x para cancelar): ").strip()
    else:
        entrada = input(f"{campo} (x para cancelar): ").strip()

    if entrada.lower() == 'x':
        return None
    return entrada if entrada else valor_actual

def confirmar_sgbd(datos):
    """
    Muestra los datos del SGBD y permite editar cualquier campo.
    Devuelve los datos corregidos o None si cancela.
    """
    while True:
        print("\n--- Confirmar datos del SGBD ---")
        print(f"  1. Tipo:       {datos['tipo']}")
        print(f"  2. Host:       {datos['host']}")
        print(f"  3. Puerto BD:  {datos['puerto_bd']}")
        print(f"  4. Usuario:    {datos['usuario']}")
        print(f"  5. Contrasena: {'*' * len(datos['contrasena'])}")
        print(f"  6. Base datos: {datos['base_datos']}")
        print("\n  c. Confirmar y guardar")
        print("  x. Cancelar")

        opcion = input("\nElige numero para editar, c para confirmar, x para cancelar: ").strip()

        if opcion == '1':
            tipos = ', '.join(NOMBRES_CLASES.keys())
            nuevo = pedir_dato(f"Tipo ({tipos})", datos['tipo'])
            if nuevo is None:
                continue
            if nuevo not in NOMBRES_CLASES:
                print(f"Tipo '{nuevo}' no soportado. Tipos validos: {tipos}")
                continue
            datos['tipo'] = nuevo
        elif opcion == '2':
            nuevo = pedir_dato("Host", datos['host'])
            if nuevo is not None:
                datos['host'] = nuevo
        elif opcion == '3':
            nuevo = pedir_dato("Puerto BD", str(datos['puerto_bd']))
            if nuevo is not None:
                try:
                    datos['puerto_bd'] = int(nuevo)
                except ValueError:
                    print("El puerto debe ser un numero.")
        elif opcion == '4':
            nuevo = pedir_dato("Usuario", datos['usuario'])
            if nuevo is not None:
                datos['usuario'] = nuevo
        elif opcion == '5':
            nuevo = pedir_dato("Contrasena")
            if nuevo is not None:
                datos['contrasena'] = nuevo
        elif opcion == '6':
            nuevo = pedir_dato("Base de datos / DSN", datos['base_datos'])
            if nuevo is not None:
                datos['base_datos'] = nuevo
        elif opcion == 'c':
            return datos
        elif opcion == 'x':
            return None
        else:
            print("Opcion no valida.")

def descubrir_y_registrar_tablas(sgbd_id, tipo, host, puerto_bd, usuario, contrasena, base_datos):
    """
    Se conecta al SGBD y descubre automaticamente las tablas de usuario.
    Las registra en el catalogo sin intervencion manual.
    """
    if tipo not in NOMBRES_CLASES:
        print(f"Tipo '{tipo}' no soportado — no se pueden descubrir tablas.")
        return

    try:
        nombre = NOMBRES_CLASES[tipo]

        modulo_conector = importlib.import_module(f"src.{tipo}.conector_{tipo}")
        clase_conector = getattr(modulo_conector, f"Conector{nombre}")
        conector = clase_conector(
            host=host,
            puerto=puerto_bd,
            usuario=usuario,
            contrasena=contrasena,
            base_datos=base_datos
        )

        modulo_ctrl = importlib.import_module(f"src.{tipo}.controlador_sistema_{tipo}")
        clase_ctrl = getattr(modulo_ctrl, f"ControladorSistema{nombre}")
        ctrl_sistema = clase_ctrl(conector)

        ctrl_sistema.iniciar()
        tablas = ctrl_sistema.obtener_tablas_usuario()

        if not tablas:
            print("No se encontraron tablas de usuario.")
        else:
            for tabla in tablas:
                catalogo.insertar_tabla(tabla, sgbd_id)
                print(f"  Tabla '{tabla}' registrada correctamente")

        ctrl_sistema.detener()

    except Exception as e:
        print(f"Error al descubrir tablas: {e}")

def anadir_sgbd():
    print("\n--- Anadir SGBD ---")
    tipos = ', '.join(NOMBRES_CLASES.keys())
    print(f"Tipos soportados: {tipos}")

    tipo = pedir_dato("Tipo")
    if tipo is None:
        print("Operacion cancelada.")
        return
    tipo = tipo.strip().lower()
    if tipo not in NOMBRES_CLASES:
        print(f"Tipo '{tipo}' no soportado. Tipos validos: {tipos}")
        return

    host = pedir_dato("Host")
    if host is None:
        print("Operacion cancelada.")
        return

    puerto_str = pedir_dato("Puerto BD")
    if puerto_str is None:
        print("Operacion cancelada.")
        return
    try:
        puerto_bd = int(puerto_str)
    except ValueError:
        print("El puerto debe ser un numero.")
        return

    usuario = pedir_dato("Usuario")
    if usuario is None:
        print("Operacion cancelada.")
        return

    contrasena = pedir_dato("Contrasena")
    if contrasena is None:
        print("Operacion cancelada.")
        return

    base_datos = pedir_dato("Base de datos / DSN")
    if base_datos is None:
        print("Operacion cancelada.")
        return

    datos = {
        'tipo': tipo,
        'host': host,
        'puerto_bd': puerto_bd,
        'usuario': usuario,
        'contrasena': contrasena,
        'base_datos': base_datos
    }

    datos = confirmar_sgbd(datos)
    if datos is None:
        print("Operacion cancelada.")
        return

    contrasena_enc = encriptacion.encriptar(datos['contrasena'])
    sgbd_id = catalogo.insertar_sgbd(
        datos['tipo'], datos['host'], datos['puerto_bd'],
        datos['usuario'], contrasena_enc, datos['base_datos']
    )
    print(f"SGBD registrado correctamente con id={sgbd_id}")

    print("\nDescubriendo tablas automaticamente...")
    descubrir_y_registrar_tablas(
        sgbd_id, datos['tipo'], datos['host'],
        datos['puerto_bd'], datos['usuario'],
        datos['contrasena'], datos['base_datos']
    )

def ver_sgbds():
    print("\n--- SGBDs registrados ---")
    sgbds = catalogo.obtener_sgbds()
    if not sgbds:
        print("No hay SGBDs registrados.")
        return sgbds
    for s in sgbds:
        print(f"  [{s['id']}] {s['tipo']} -> {s['host']}:{s['puerto_bd']} · usuario: {s['usuario']}")
    return sgbds

def ver_tablas():
    print("\n--- Tablas registradas ---")
    cursor = catalogo.conexion.cursor()
    cursor.execute("""
        SELECT tabla.id, tabla.nombre, sgbd.tipo
        FROM tabla
        JOIN sgbd ON tabla.sgbd_id = sgbd.id
        ORDER BY tabla.nombre, sgbd.tipo
    """)
    filas = cursor.fetchall()
    cursor.close()
    if not filas:
        print("No hay tablas registradas.")
        return filas
    for fila in filas:
        print(f"  [{fila[0]}] {fila[1]} -> {fila[2]}")
    return filas

def eliminar_sgbd():
    print("\n--- Eliminar SGBD ---")
    sgbds = ver_sgbds()
    if not sgbds:
        return

    ids_validos = [str(s['id']) for s in sgbds]

    sgbd_id_str = input("ID del SGBD a eliminar (x para cancelar): ").strip()
    if sgbd_id_str.lower() == 'x':
        print("Operacion cancelada.")
        return

    if sgbd_id_str not in ids_validos:
        print(f"ID '{sgbd_id_str}' no existe.")
        return

    sgbd_id = int(sgbd_id_str)
    confirmar = input(f"Seguro que quieres eliminar el SGBD {sgbd_id} y todas sus tablas? (s/n): ").strip()
    if confirmar.lower() == 's':
        catalogo.eliminar_sgbd(sgbd_id)
        print("SGBD eliminado correctamente")
    else:
        print("Operacion cancelada.")

def eliminar_tabla():
    print("\n--- Eliminar tabla ---")
    filas = ver_tablas()
    if not filas:
        return

    ids_validos = [str(fila[0]) for fila in filas]

    tabla_id_str = input("ID de la tabla a eliminar (x para cancelar): ").strip()
    if tabla_id_str.lower() == 'x':
        print("Operacion cancelada.")
        return

    if tabla_id_str not in ids_validos:
        print(f"ID '{tabla_id_str}' no existe.")
        return

    tabla_id = int(tabla_id_str)
    confirmar = input(f"Seguro que quieres eliminar la tabla {tabla_id}? (s/n): ").strip()
    if confirmar.lower() == 's':
        catalogo.eliminar_tabla(tabla_id)
        print("Tabla eliminada correctamente")
    else:
        print("Operacion cancelada.")

if __name__ == '__main__':
    menu()