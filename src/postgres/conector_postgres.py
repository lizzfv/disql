import psycopg2
from src.abstracto.conector import Conector

class ConectorPostgres(Conector):
    """
    Implementación concreta del Conector para PostgreSQL.
    Usa psycopg2 como driver nativo.
    
    Diferencias con ConectorMariaDB:
    - Usa psycopg2 en vez de pymysql
    - El parámetro de la BD se llama dbname en vez de database
    - Los datos binarios vienen como memoryview en vez de bytearray
    """

    def __init__(self, host, puerto, usuario, contrasena, base_datos, tamano_lote=1000, max_reintentos=4):
        super().__init__(tamano_lote, max_reintentos)
        self.host = host
        self.port = puerto
        self.user = usuario
        self.password = contrasena
        self.dbname = base_datos

    def conectar(self):
        """
        Abre la conexión física con PostgreSQL usando psycopg2.
        Este método es llamado internamente por conectar_con_reintento().
        autocommit=True porque DiSQL solo hace lecturas.
        """
        self.conexion = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.dbname
        )
        self.conexion.autocommit = True
    
    def desconectar(self):
        """Cierra la conexión limpiamente si está abierta."""
        if self.conexion:
            self.conexion.close()
            self.conexion = None

    def ejecutar(self, sql):
        """
        Envía el SQL a PostgreSQL y devuelve los resultados normalizados.
        Recupera las filas en lotes de self.tamano_lote para no
        materializar el conjunto completo en memoria.
        El bloque try/finally garantiza que el cursor se cierra
        siempre, incluso si ocurre un error durante la ejecución.
        """
        cursor = self.conexion.cursor()
        try:
            cursor.execute(sql)
            resultados = []
            while True:
                filas = cursor.fetchmany(self.tamano_lote)
                if not filas:
                    break
                resultados.extend(self.normalizar_resultados(cursor, filas))
            return resultados
        finally:
            cursor.close()
            
    def ejecutar_cursor(self, sql):
        """
        Envía el SQL a PostgreSQL y devuelve el cursor abierto sin cerrarlo.
        El Ejecutor es responsable de cerrar el cursor cuando termine.
        """
        cursor = self.conexion.cursor()
        cursor.execute(sql)
        return cursor
            
    def normalizar_resultados(self, cursor, filas):
        """
        Convierte cada fila a un diccionario Python con tipos estándar.
        Los nombres de columna se obtienen de cursor.description.

        Conversiones aplicadas:
        - memoryview → bytes
        - Decimal    → Decimal (ya es estándar Python, se mantiene)
        - datetime   → datetime (ya es estándar Python, se mantiene)
        - date       → date (ya es estándar Python, se mantiene)
        - bool       → bool (ya es estándar Python, se mantiene)
        - None       → None (valores nulos se mantienen como None)
        """
        # cursor.description = [('id', ...), ('nombre', ...), ...]
        # Nos quedamos solo con el primer elemento de cada tupla (el nombre)
        nombres = [col[0] for col in cursor.description]

        resultados = []
        for fila in filas:
            fila_dict = {}
            for nombre, valor in zip(nombres, fila):
                # memoryview es el tipo que usa psycopg2 para datos binarios
                # lo convertimos a bytes que es el tipo estándar Python
                if isinstance(valor, memoryview):
                    valor = bytes(valor)
                fila_dict[nombre] = valor
            resultados.append(fila_dict)

        return resultados
    
    def ejecutar_sin_resultado(self, sql):
        """
        Ejecuta una sentencia SQL que no devuelve filas.
        En MariaDB/PostgreSQL no se usa — EXPLAIN devuelve filas.
        Se implementa para cumplir con la interfaz abstracta.
        """
        cursor = self.conexion.cursor()
        try:
            cursor.execute(sql)
        finally:
            cursor.close()