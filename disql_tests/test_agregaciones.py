import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import sqlglot

# ast = sqlglot.parse_one("SELECT COUNT(*) FROM empleados")
# print("--- COUNT(*) ---")
# print(ast.find(sqlglot.exp.AggFunc))
# print(type(ast.find(sqlglot.exp.AggFunc)))

# ast2 = sqlglot.parse_one("SELECT SUM(salario) FROM empleados")
# print("\n--- SUM(salario) ---")
# print(ast2.find(sqlglot.exp.AggFunc))

# ast3 = sqlglot.parse_one("SELECT AVG(salario) FROM empleados")
# print("\n--- AVG(salario) ---")
# print(ast3.find(sqlglot.exp.AggFunc))

# ast4 = sqlglot.parse_one("SELECT departamento, COUNT(*) FROM empleados GROUP BY departamento")
# print("\n--- GROUP BY ---")
# print(list(ast4.find_all(sqlglot.exp.AggFunc)))
# print(ast4.find(sqlglot.exp.Group))

# ast5 = sqlglot.parse_one("SELECT COUNT(*) FROM empleados")
# select = ast5.find(sqlglot.exp.Select)
# for expr in select.expressions:
#     print(f"tipo: {type(expr).__name__}, alias: {expr.alias}, sql: {expr}")

# ast6 = sqlglot.parse_one("SELECT SUM(salario) FROM empleados")
# select = ast6.find(sqlglot.exp.Select)
# for expr in select.expressions:
#     print(f"tipo: {type(expr).__name__}, alias: {expr.alias}, sql: {expr}")

# ast7 = sqlglot.parse_one("SELECT departamento, COUNT(*) FROM empleados GROUP BY departamento")
# select = ast7.find(sqlglot.exp.Select)
# for expr in select.expressions:
#     print(f"tipo: {type(expr).__name__}, alias: {expr.alias}, sql: {expr}"
from src.abstracto.controlador import Controlador

controlador = Controlador()
controlador.iniciar_sistema()

print("\n--- Nombres de columna reales por SGBD ---")
for tipo, ctrl in controlador.controladores_sistema.items():
    cursor = ctrl.ejecutar_consulta_cursor("SELECT COUNT(*) FROM empleados")
    fila = ctrl.obtener_fila(cursor)
    cursor.close()
    print(f"{tipo}: {fila}")

controlador.detener_sistema()