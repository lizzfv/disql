from src.abstracto.controlador_sistema import ControladorSistema

class ControladorSistemaOracle(ControladorSistema):
    """
    Implementación concreta del ControladorSistema para Oracle 21c.
    
    Diferencias con MariaDB y PostgreSQL:
    - obtener_esquema consulta ALL_COLUMNS en vez de information_schema
    - Los nombres de tabla y columna en Oracle son MAYÚSCULAS por defecto
      así que los convertimos a minúsculas para coherencia con el resto
    - verificar_consulta usa EXPLAIN PLAN FOR en vez de EXPLAIN
    """
    
    TABLAS_SISTEMA = []  

    def __init__(self, conector):
        """
        conector = instancia de ConectorOracle
        """
        super().__init__(conector)

    def obtener_esquema(self, tabla):
        """
        Consulta ALL_COLUMNS de Oracle para obtener las columnas
        y tipos de datos de una tabla.
        
        ALL_COLUMNS es una vista del sistema de Oracle equivalente
        a information_schema.columns de MariaDB y PostgreSQL.
        
        Devuelve una lista de diccionarios con esta estructura:
        [
            {'columna': 'id',      'tipo': 'number'},
            {'columna': 'nombre',  'tipo': 'varchar2'},
            {'columna': 'salario', 'tipo': 'number'},
            ...
        ]
        
        tabla = nombre de la tabla a consultar (se convierte a
                mayúsculas porque Oracle almacena los nombres así)
        """
        sql = f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM ALL_TAB_COLUMNS
            WHERE TABLE_NAME = '{tabla.upper()}'
            AND OWNER = 'DISQL'
            ORDER BY COLUMN_ID
        """
        filas = self.conector.ejecutar(sql)
        return [{'columna': fila['column_name'].lower(),
                 'tipo': fila['data_type'].lower()} for fila in filas]

    def verificar_consulta(self, sql):
        try:
            self.conector.ejecutar_sin_resultado(f"EXPLAIN PLAN FOR {sql}")
            return True
        except Exception as e:
            print(f"Consulta inválida en Oracle: {e}")
            return False
        
    def obtener_tablas_usuario(self):
        filas = self.conector.ejecutar("""
            SELECT TABLE_NAME
            FROM ALL_TABLES
            WHERE OWNER = 'DISQL'
        """)
        return [fila['table_name'].lower() for fila in filas]