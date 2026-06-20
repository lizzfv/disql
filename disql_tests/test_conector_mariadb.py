import sys
import os

# Añadimos la raíz del proyecto al path para poder importar src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mariadb.conector_mariadb import ConectorMariaDB

# Creamos el conector
conector = ConectorMariaDB()

print("Intentando conectar a MariaDB...")

# Usamos conectar_con_reintento para probar también esa lógica
conector.conectar_con_reintento()

print("Conexión establecida")

# Ejecutamos una consulta
print("\nConsultando tabla empleados...")
resultados = conector.ejecutar("SELECT * FROM empleados")

# Mostramos los resultados
for fila in resultados:
    print(" ", fila)

# Cerramos la conexión
conector.desconectar()
print("\nConexión cerrada correctamente")