from src.abstracto.controlador_sistema import ControladorSistema

class ControladorSistemaPostgres(ControladorSistema):
    """
    Implementación concreta del ControladorSistema para PostgreSQL.
    
    Usa information_schema para obtener esquemas de tablas
    y EXPLAIN para verificar consultas antes de ejecutarlas.
    
    Diferencias con ControladorSistemaMariaDB:
    - obtener_esquema filtra por table_schema = 'public' en vez
      de TABLE_SCHEMA = DATABASE()
    - Los nombres de columna vienen en minúsculas (igual que MariaDB)
    """
    
    TABLAS_SISTEMA = ['information_schema', 'pg_catalog']

    def __init__(self, conector):
        """
        conector = instancia de ConectorPostgres
        """
        super().__init__(conector)

    def obtener_esquema(self, tabla):
        """
        Consulta information_schema.columns de PostgreSQL para obtener
        las columnas y tipos de datos de una tabla.
        
        Devuelve una lista de diccionarios con esta estructura:
        [
            {'columna': 'id',     'tipo': 'integer'},
            {'columna': 'nombre', 'tipo': 'character varying'},
            {'columna': 'salario','tipo': 'numeric'},
            ...
        ]
        
        tabla = nombre de la tabla a consultar
        """
        sql = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = '{tabla}'
            ORDER BY ordinal_position
        """
        filas = self.conector.ejecutar(sql)
        return [{'columna': fila['column_name'],
                 'tipo': fila['data_type']} for fila in filas]

    def verificar_consulta(self, sql):
        """
        Usa EXPLAIN para verificar si el SQL es válido en PostgreSQL
        sin ejecutarlo realmente.
        
        Devuelve True si la consulta es válida, False si no lo es.
        sql = consulta SQL ya traducida al dialecto PostgreSQL
        """
        try:
            self.conector.ejecutar(f"EXPLAIN {sql}")
            return True
        except Exception as e:
            print(f"Consulta inválida en PostgreSQL: {e}")
            return False

    def obtener_tablas_usuario(self):
        """
        Devuelve las tablas de usuario filtrando las del sistema.
        Se usa para el autodescubrimiento al registrar un SGBD nuevo.
        """
        filas = self.conector.ejecutar("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        return [
            fila['table_name']
            for fila in filas
            if fila['table_name'] not in self.TABLAS_SISTEMA
        ]