import sqlglot
from src.abstracto.ejecutor import Ejecutor

class Analizador:
    """
    Transforma el SQL del usuario en una representación intermedia
    basada en álgebra relacional que el Ejecutor puede procesar.
    
    Recibe del Controlador:
    - catalogo: para saber en qué SGBDs está cada tabla
    - controladores_sistema: para obtener los esquemas reales de cada tabla
    - sgbds_disponibles: para saber qué SGBDs están disponibles para ejecutar consultas
    
    El análisis se desarrolla en tres fases:
    1. Léxica y sintáctica → sqlglot parsea el SQL y construye el AST
    2. Semántica → valida tablas, columnas y tipos contra el catálogo y los SGBDs
    3. Representación intermedia → convierte el AST a álgebra relacional
    """

    def __init__(self, catalogo, controladores_sistema, sgbds_disponibles):
        self.catalogo = catalogo #para saber en qué SGBDs está cada tabla
        self.controladores_sistema = controladores_sistema #para obtener los esquemas reales de cada tabla
        # Creamos el Ejecutor pasandole los ControladorSistema y los SGBDs disponibles
        self.ejecutor = Ejecutor(controladores_sistema, sgbds_disponibles, catalogo)

    def analizar(self, sql):
        """
        Metodo principal. Ejecuta las tres fases en orden
        y pasa la representacion intermedia al Ejecutor.
        sql = consulta SQL escrita por el usuario
        """
        # Fase 1 — lexica y sintactica, parse_one devuelve un AST o lanza una excepcion si el SQL no es valido
        try:
            ast = sqlglot.parse_one(sql)
        except Exception as e:
            raise ValueError(f"Error sintactico en la consulta: {e}")

        # Comprobamos que la consulta no usa construcciones fuera del alcance de DiSQL
        if ast.find(sqlglot.exp.Join):
            raise ValueError(
                "DiSQL no soporta JOIN en esta version. "
                "Los joins distribuidos se identifican como trabajo futuro."
            )

        if ast.find(sqlglot.exp.Insert) or ast.find(sqlglot.exp.Update) or ast.find(sqlglot.exp.Delete):
            raise ValueError(
                "DiSQL no soporta operaciones de modificacion (INSERT, UPDATE, DELETE). "
                "El sistema es de solo lectura."
            )

        if ast.find(sqlglot.exp.Window):
            raise ValueError(
                "DiSQL no soporta funciones de ventana (ROW_NUMBER, RANK, LEAD...). "
                "Quedan fuera del alcance actual del sistema."
            )
    
        # Fase 2 — semantica
        # validar_semantica devuelve los SGBDs de cada tabla
        sgbds_por_tabla = self.validar_semantica(ast)

        # Fase 3 — representacion intermedia
        repr_intermedia = self.generar_representacion_intermedia(ast, sgbds_por_tabla)

        # Pasamos la representacion intermedia al Ejecutor
        yield from self.ejecutor.ejecutar(repr_intermedia)

    def validar_semantica(self, ast):
        """
        Consulta el catálogo para saber en qué SGBDs está cada tabla.
        Consulta los ControladorSistema para obtener los esquemas reales.
        Compara esquemas entre SGBDs y valida que son compatibles.
        Si detecta problemas lanza una excepción con el detalle del error.
        Devuelve un diccionario con los SGBDs de cada tabla para que
        generar_representacion_intermedia lo incluya en la repr intermedia.
        """
        tablas = [tabla.name for tabla in ast.find_all(sqlglot.exp.Table)]
        sgbds_por_tabla = {}

        for nombre_tabla in tablas:
            sgbds = self.catalogo.obtener_sgbds_de_tabla(nombre_tabla)
            
            if not sgbds:
                raise ValueError(f"La tabla '{nombre_tabla}' no esta registrada en el catalogo DiSQL")

            # Guardamos los tipos de SGBDs donde esta la tabla
            # El Ejecutor lo usara para saber que Traductores necesita
            # sgbds_por_tabla['empleados'] = ['mariadb', 'postgres', 'oracle']
            sgbds_por_tabla[nombre_tabla] = [sgbd['tipo'] for sgbd in sgbds] 

            # Obtenemos el esquema de cada SGBD y los comparamos
            esquemas = {}
            for sgbd in sgbds:
                tipo = sgbd['tipo']
                if tipo in self.controladores_sistema:
                    esquema = self.controladores_sistema[tipo].obtener_esquema(nombre_tabla)
                    esquemas[tipo] = {col['columna']: col['tipo'] for col in esquema}

            # Comparamos que las columnas sean las mismas en todos los SGBDs
            tipos_sgbd = list(esquemas.keys())
            if len(tipos_sgbd) > 1:
                columnas_base = set(esquemas[tipos_sgbd[0]].keys())
                for tipo in tipos_sgbd[1:]:
                    columnas_actual = set(esquemas[tipo].keys())
                    diferencia = columnas_base.symmetric_difference(columnas_actual)
                    if diferencia:
                        raise ValueError(
                            f"Esquemas incompatibles para la tabla '{nombre_tabla}': "
                            f"columnas que difieren: {diferencia}"
                        )

        return sgbds_por_tabla 

    def generar_representacion_intermedia(self, ast, sgbds_por_tabla):
        """
        Convierte el AST validado en una representacion intermedia
        que el Ejecutor puede procesar.
        """
        tablas = [t.name for t in ast.find_all(sqlglot.exp.Table)]

        # Buscamos el nodo SELECT en el árbol, es donde están las columnas que pidió el usuario
        select = ast.find(sqlglot.exp.Select)
        
        columnas = []      # columnas normales: nombre, salario, *
        agregaciones = []  # funciones de agregacion: COUNT(*), SUM(salario), etc.

        if select:
            # Recorremos cada cosa que hay después del SELECT
            # Por ejemplo en "SELECT nombre, COUNT(*)" tenemos dos expresiones: nombre y COUNT(*)
            for expr in select.expressions:
                
                if isinstance(expr, sqlglot.exp.Column):
                    # Es una columna normal — por ejemplo "nombre" o "salario"
                    columnas.append(expr.name)
                    
                elif isinstance(expr, sqlglot.exp.Star):
                    # Es el asterisco... SELECT *
                    columnas.append('*')
                    
                elif isinstance(expr, sqlglot.exp.Count):
                    # Es un COUNT(*) o COUNT(columna)
                    # Guardamos que hay un COUNT y el SQL tal cual para traducirlo luego
                    agregaciones.append({'funcion': 'COUNT', 'sql': str(expr)})
                    
                elif isinstance(expr, sqlglot.exp.Sum):
                    # Es un SUM(columna)... guardamos también sobre qué columna opera
                    col = expr.this.name if expr.this else None
                    agregaciones.append({'funcion': 'SUM', 'columna': col, 'sql': str(expr)})
                    
                elif isinstance(expr, sqlglot.exp.Avg):
                    # Es un AVG(columna), el Ejecutor lo descompondrá en SUM y COUNT
                    col = expr.this.name if expr.this else None
                    agregaciones.append({'funcion': 'AVG', 'columna': col, 'sql': str(expr)})
                    
                elif isinstance(expr, sqlglot.exp.Max):
                    # Es un MAX(columna)
                    col = expr.this.name if expr.this else None
                    agregaciones.append({'funcion': 'MAX', 'columna': col, 'sql': str(expr)})
                    
                elif isinstance(expr, sqlglot.exp.Min):
                    # Es un MIN(columna)
                    col = expr.this.name if expr.this else None
                    agregaciones.append({'funcion': 'MIN', 'columna': col, 'sql': str(expr)})

        # Condicion WHERE 
        condicion = ast.find(sqlglot.exp.Where)

        # ORDER BY
        orden = ast.find(sqlglot.exp.Order)

        # GROUP BY 
        group = ast.find(sqlglot.exp.Group)

        # Devolvemos todo junto en un diccionario para que el Ejecutor lo use
        return {
            'tablas': tablas,
            'columnas': columnas,
            'condicion': str(condicion) if condicion else None, #condicion si es que existe
            'orden': str(orden) if orden else None, #orden si es que existe
            'sgbds_por_tabla': sgbds_por_tabla,
            'ast': ast,
            'agregaciones': agregaciones,  # lista de funciones de agregacion detectadas
            'group': str(group) if group else None  # GROUP BY si existe
        }