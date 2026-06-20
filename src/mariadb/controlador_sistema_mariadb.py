from src.abstracto.controlador_sistema import ControladorSistema

class ControladorSistemaMariaDB(ControladorSistema):
    """
    Implementación concreta del ControladorSistema para MariaDB.
    
    Usa information_schema para obtener esquemas de tablas
    y EXPLAIN para verificar consultas antes de ejecutarlas.
    """
    
    TABLAS_SISTEMA = ['information_schema', 'mysql', 'performance_schema', 'sys']


    def __init__(self, conector):
        """
        conector = instancia de ConectorMariaDB
        """
        super().__init__(conector)

    def obtener_esquema(self, tabla):
        """
        Consulta information_schema.columns de MariaDB para obtener
        las columnas y tipos de datos de una tabla.
        
        Devuelve una lista de diccionarios con esta estructura:
        [
            {'columna': 'id',     'tipo': 'int'},
            {'columna': 'nombre', 'tipo': 'varchar'},
            {'columna': 'salario','tipo': 'decimal'},
            ...
        ]
        
        El Analizador usa esto durante la fase semántica para
        verificar que las columnas de la consulta existen y que
        los tipos son compatibles entre los distintos SGBDs.
        
        tabla = nombre de la tabla a consultar
        """
        sql = f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{tabla}'
            ORDER BY ORDINAL_POSITION
        """
        filas = self.conector.ejecutar(sql)
        return [{'columna': fila['COLUMN_NAME'], 
                 'tipo': fila['DATA_TYPE']} for fila in filas]

    def verificar_consulta(self, sql):
        """
        Usa EXPLAIN para verificar si el SQL es válido en MariaDB
        sin ejecutarlo realmente.
        
        EXPLAIN le pide a MariaDB que nos explique cómo ejecutaría
        la consulta — si el SQL tiene errores sintácticos o semánticos
        MariaDB lanza una excepción antes de ejecutar nada.
        
        Devuelve True si la consulta es válida, False si no lo es.
        sql = consulta SQL ya traducida al dialecto MariaDB
        """
        try:
            self.conector.ejecutar(f"EXPLAIN {sql}")
            return True
        except Exception as e:
            print(f"Consulta inválida en MariaDB: {e}")
            return False
        
    def obtener_tablas_usuario(self):
        """
        Devuelve las tablas de usuario filtrando las del sistema.
        Se usa para el autodescubrimiento al registrar un SGBD nuevo.
        """
        filas = self.conector.ejecutar("""
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
        """)
        return [
            fila['TABLE_NAME'] 
            for fila in filas 
            if fila['TABLE_NAME'] not in self.TABLAS_SISTEMA
        ]