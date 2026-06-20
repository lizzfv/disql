import oracledb
from decimal import Decimal
from src.abstracto.conector import Conector

class ConectorOracle(Conector):
    """
    Implementación concreta del Conector para Oracle 21c.
    Usa oracledb en modo thin (sin necesidad de instalar Oracle Client).

    Diferencias con ConectorMariaDB y ConectorPostgres:
    - Usa oracledb en vez de pymysql o psycopg2
    - La conexión usa dsn en vez de host+port+database por separado
    - Los datos de tipo LOB requieren conversión explícita llamando a .read()
    - Los números con decimales vienen como float → se convierten a Decimal
    """

    def __init__(self, host, puerto, usuario, contrasena, base_datos, tamano_lote=1000, max_reintentos=4):
        super().__init__(tamano_lote, max_reintentos)
        self.user = usuario
        self.password = contrasena
        self.dsn = base_datos

    def conectar(self):
        """
        Abre la conexión física con Oracle usando oracledb en modo thin.
        Este método es llamado internamente por conectar_con_reintento().
        """
        self.conexion = oracledb.connect(
            user=self.user,
            password=self.password,
            dsn=self.dsn
        )
    
    def desconectar(self):
        """Cierra la conexión limpiamente si está abierta."""
        if self.conexion:
            self.conexion.close()
            self.conexion = None

    def ejecutar(self, sql):
        """
        Envía el SQL a ORACLE y devuelve los resultados normalizados.
        Recupera las filas en lotes de self.tamano_lote para no
        materializar el conjunto completo en memoria.
        El bloque try/finally garantiza que el cursor se cierra
        siempre, incluso si ocurre un error durante la ejecución.
        """
        cursor = self.conexion.cursor()
        cursor.arraysize = 1000
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
        Envía el SQL a Oracle y devuelve el cursor abierto sin cerrarlo.
        El Ejecutor es responsable de cerrar el cursor cuando termine.
        Nota: Oracle devuelve nombres de columna en mayúsculas — el Ejecutor
        debe llamar a normalizar_resultados() al leer cada fila.
        """
        cursor = self.conexion.cursor()
        cursor.arraysize = 1000
        cursor.execute(sql)
        return cursor
        
    def normalizar_resultados(self, cursor, filas):
        """
        Convierte cada fila a un diccionario Python con tipos estándar.
        Los nombres de columna se obtienen de cursor.description.

        Conversiones aplicadas:
        - oracledb.LOB  → str o bytes según sea CLOB o BLOB
        - int           → int (ya es estándar Python, se mantiene)
        - float         → Decimal para consistencia con MariaDB y PostgreSQL
        - str           → str (ya es estándar Python, se mantiene)
        - datetime      → datetime (ya es estándar Python, se mantiene)
        - None          → None (valores nulos se mantienen como None)
        """
        # cursor.description = [('ID', ...), ('NOMBRE', ...), ...]
        # Nota: Oracle devuelve los nombres de columna en MAYÚSCULAS
        # Los convertimos a minúsculas para que sea coherente con
        # MariaDB y PostgreSQL que los devuelven en minúsculas
        nombres = [col[0].lower() for col in cursor.description]

        resultados = []
        for fila in filas:
            fila_dict = {}
            for nombre, valor in zip(nombres, fila):
                # Los LOB son objetos especiales de Oracle para
                # textos (CLOB) y binarios (BLOB) grandes.
                # Hay que llamar a .read() para obtener el contenido real.
                if isinstance(valor, oracledb.LOB):
                    valor = valor.read()
                elif isinstance(valor, float):
                    valor = Decimal(str(valor))
                fila_dict[nombre] = valor
            resultados.append(fila_dict)

        return resultados
    
    def ejecutar_sin_resultado(self, sql):
        """
        Ejecuta una sentencia SQL que no devuelve filas.
        Usado por verificar_consulta del ControladorSistemaOracle.
        """
        cursor = self.conexion.cursor()
        try:
            cursor.execute(sql)
        finally:
            cursor.close()