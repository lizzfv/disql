import sys
import os

# Añadimos la raíz del proyecto al path para poder importar src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.oracle.conector_oracle import ConectorOracle

# Creamos el conector
conector = ConectorOracle()

print("🔌 Intentando conectar a Oracle...")

# Usamos conectar_con_reintento para probar también esa lógica
conector.conectar_con_reintento()

print("Conexión establecida")

# Ejecutamos una consulta
# Nota: en Oracle las tablas están en el esquema sys
print("\nConsultando tabla empleados...")
resultados = conector.ejecutar("SELECT * FROM disql.empleados")

# Mostramos los resultados
for fila in resultados:
    print(" ", fila)

# Cerramos la conexión
conector.desconectar()
print("\nConexión cerrada correctamente")