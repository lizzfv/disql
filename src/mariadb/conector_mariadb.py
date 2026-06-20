import pymysql
from src.abstracto.conector import Conector

class ConectorMariaDB(Conector):
    """
    Implementación concreta del Conector para MariaDB.
    Usa pymysql como driver nativo.
    """

    def __init__(self, host, puerto, usuario, contrasena, base_datos, tamano_lote=1000, max_reintentos=4):
        super().__init__(tamano_lote, max_reintentos)
        self.host = host
        self.port = puerto
        self.user = usuario
        self.password = contrasena
        self.database = base_datos
      
    def conectar(self):
        """
        Abre la conexión física con MariaDB usando pymysql.
        Este método es llamado internamente por conectar_con_reintento().
        """
        self.conexion = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            autocommit=True #autocommit es importante para que cada consulta se ejecute 
            #sin necesidad de hacer commit explícito, ya que DiSQL solo hace lecturas y 
            # no necesita gestión de transacciones.
        )

    def desconectar(self):
        """Cierra la conexión limpiamente si está abierta."""
        if self.conexion:
            self.conexion.close()
            self.conexion = None

    def ejecutar(self, sql):
        """
        Envía el SQL a MariaDB y devuelve los resultados normalizados.
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
        Envía el SQL a MariaDB y devuelve el cursor abierto sin cerrarlo.
        El Ejecutor es responsable de cerrar el cursor cuando termine.
        """
        cursor = self.conexion.cursor() # El cursor se abre pero no se cierra aquí, el Ejecutor lo cerrará después de usarlo
        cursor.execute(sql) # Ejecutamos la consulta pero no recuperamos filas aquí, el Ejecutor lo hará iterando sobre el cursor
        return cursor # Devolvemos el cursor abierto para que el Ejecutor pueda iterar sobre él y luego cerrarlo
                
    def normalizar_resultados(self, cursor, filas):
        """
        Convierte cada fila a un diccionario Python con tipos estándar.
        Los nombres de columna se obtienen de cursor.description.
        
        Conversiones aplicadas:
        - bytearray → bytes
        - Decimal   → Decimal (ya es estándar Python, se mantiene)
        - datetime  → datetime (ya es estándar Python, se mantiene)
        - date      → date (ya es estándar Python, se mantiene)
        - None      → None (valores nulos se mantienen como None)
        """
        nombres = [col[0] for col in cursor.description] #nos quedamos solo con el primer elemento de cada tupla (el nombre), 
                                                         #el resto de elementos de la tupla (tipo, etc) no nos interesa para la normalización

        resultados = []
        for fila in filas:
            fila_dict = {}
            for nombre, valor in zip(nombres, fila): #combina los nombres de la columnas con los valores de la fila en un diccionario
              
                if isinstance(valor, bytearray): #si el valor es un bytearray, lo convertimos a bytes para que sea un tipo estándar Python
                    valor = bytes(valor)
                # El resto de tipos (Decimal, datetime, date, str, int,
                # float, bool, None) ya son tipos estándar Python
                # y no necesitan conversión
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