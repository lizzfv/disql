from abc import ABC, abstractmethod

class ControladorSistema(ABC):
    """
    Clase abstracta que define la interfaz del componente intermedio
    entre el Ejecutor y cada SGBD individual.
    
    Cada SGBD concreto implementa esta clase de forma distinta porque:
    - obtener_esquema() consulta catálogos locales diferentes en cada SGBD
    - verificar_consulta() usa mecanismos distintos en cada SGBD
    
    El ControladorSistema recibe un Conector en el constructor
    porque lo necesita para comunicarse físicamente con el SGBD.
    """

    def __init__(self, conector):
        """
        conector = instancia de ConectorMariaDB, ConectorPostgres
                   o ConectorOracle según el SGBD
        """
        self.conector = conector

    def iniciar(self):
        """
        Abre la conexión con el SGBD usando el Conector.
        Usa conectar_con_reintento para gestionar fallos de red.
        """
        self.conector.conectar_con_reintento()

    def detener(self):
        """
        Cierra la conexión con el SGBD limpiamente.
        """
        self.conector.desconectar()

    def ejecutar_consulta(self, sql):
        """
        Recibe el SQL ya traducido al dialecto del SGBD,
        lo pasa al Conector y devuelve los resultados normalizados.
        sql = consulta SQL ya traducida al dialecto del SGBD
        """
        return self.conector.ejecutar(sql)
    
    def ejecutar_consulta_cursor(self, sql):
        """
        Recibe el SQL ya traducido al dialecto del SGBD y devuelve
        el cursor abierto sin cerrarlo.
        El Ejecutor es responsable de cerrarlo cuando termine.
        sql = consulta SQL ya traducida al dialecto del SGBD
        """
        return self.conector.ejecutar_cursor(sql)

    def obtener_fila(self, cursor):
        """
        Lee la siguiente fila del cursor y la devuelve normalizada
        como diccionario Python.
        Devuelve None si no quedan más filas.
        """
        fila = cursor.fetchone()
        if fila is None:
            return None
        return self.conector.normalizar_resultados(cursor, [fila])[0]

    @abstractmethod
    def verificar_consulta(self, sql):
        """
        Comprueba si el SQL es válido antes de ejecutarlo.
        Cada SGBD lo implementa de forma distinta:
        - Oracle    → usa el paquete DBMS_SQL
        - PostgreSQL → usa EXPLAIN
        - MariaDB   → usa information_schema
        sql = consulta SQL ya traducida al dialecto del SGBD
        """
        pass

    @abstractmethod
    def obtener_esquema(self, tabla):
        """
        Consulta el catálogo local del SGBD para obtener
        las columnas y tipos de datos de una tabla.
        El Analizador lo usa durante la fase semántica.
        Cada SGBD lo implementa de forma distinta:
        - Oracle     → consulta ALL_COLUMNS
        - PostgreSQL → consulta information_schema.columns
        - MariaDB    → consulta information_schema.columns
        tabla = nombre de la tabla a consultar
        """
        pass