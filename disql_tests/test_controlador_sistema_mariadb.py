import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mariadb.conector_mariadb import ConectorMariaDB
from src.mariadb.controlador_sistema_mariadb import ControladorSistemaMariaDB

# Creamos el conector y el controlador de sistema
conector = ConectorMariaDB()
controlador = ControladorSistemaMariaDB(conector)

print("Iniciando conexión con MariaDB...")
controlador.iniciar()
print("Conexión establecida")

# Probamos obtener_esquema
print("\nEsquema de la tabla empleados:")
esquema = controlador.obtener_esquema('empleados')
for columna in esquema:
    print(" ", columna)

# Probamos verificar_consulta con una consulta válida
print("\nVerificando consulta válida:")
resultado = controlador.verificar_consulta("SELECT * FROM empleados")
print(f"  Resultado: {resultado}")

# Probamos verificar_consulta con una consulta inválida
print("\nVerificando consulta inválida:")
resultado = controlador.verificar_consulta("SELECT * FROM tabla_que_no_existe")
print(f"  Resultado: {resultado}")

# Probamos ejecutar_consulta
print("\nEjecutando consulta:")
resultados = controlador.ejecutar_consulta("SELECT * FROM empleados")
for fila in resultados:
    print(" ", fila)

# Cerramos la conexión
controlador.detener()
print("\nConexión cerrada correctamente")