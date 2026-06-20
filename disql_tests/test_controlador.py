import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.abstracto.controlador import Controlador

def mostrar_resultados(resultados):
    if resultados is None:
        print("  Sin resultados o error.")
        return
    count = 0
    for fila in resultados:
        print(f"    {fila}")
        count += 1
    if count == 0:
        print("  Sin resultados o error.")
    else:
        print(f"  {count} filas obtenidas")

controlador = Controlador()
controlador.iniciar_sistema()

print("\n--- Test 1: SELECT con WHERE y ORDER BY DESC ---")
resultados = controlador.procesar_consulta(
    "SELECT nombre, salario FROM empleados WHERE salario > 3500 ORDER BY salario DESC"
)
mostrar_resultados(resultados)

print("\n--- Test 2: SELECT con WHERE y ORDER BY ASC ---")
resultados = controlador.procesar_consulta(
    "SELECT nombre, salario FROM empleados WHERE salario > 3500 ORDER BY salario ASC"
)
mostrar_resultados(resultados)

print("\n--- Test 3: SELECT sin WHERE ni ORDER BY ---")
resultados = controlador.procesar_consulta(
    "SELECT nombre, salario FROM empleados"
)
mostrar_resultados(resultados)

print("\n--- Test 4: SELECT * ---")
resultados = controlador.procesar_consulta(
    "SELECT * FROM empleados"
)
mostrar_resultados(resultados)

print("\n--- Test 5: SELECT de departamentos ---")
resultados = controlador.procesar_consulta(
    "SELECT * FROM departamentos"
)
mostrar_resultados(resultados)

print("\n--- Test 6: Tabla que no existe ---")
resultados = controlador.procesar_consulta(
    "SELECT * FROM tabla_inventada"
)
mostrar_resultados(resultados)

import sqlglot
ast = sqlglot.parse_one("SELECT * FROM empleados ORDER BY salario DESC, nombre ASC")
orden = ast.find(sqlglot.exp.Order)
print(str(orden))

controlador.detener_sistema()
