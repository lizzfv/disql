import time
import oracledb

conexion = oracledb.connect(
    user="disql",
    password="LizFerUser,1",
    dsn="127.0.0.1:10302/poradba.pclab.localdomain"
)

sql = "SELECT * FROM empleados"

for tamano in [100, 1000, 3000]:
    tiempos = []
    for _ in range(5):
        cursor = conexion.cursor()
        cursor.arraysize = tamano
        inicio = time.time()
        cursor.execute(sql)
        filas = cursor.fetchall()
        fin = time.time()
        tiempos.append((fin - inicio) * 1000)
        cursor.close()
    media = sum(tiempos) / len(tiempos)
    print(f"arraysize={tamano}: {media:.2f} ms (filas: {len(filas)})")

conexion.close()