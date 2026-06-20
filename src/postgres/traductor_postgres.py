import sqlglot
from src.abstracto.traductor import Traductor

class TraductorPostgres(Traductor):
    """
    Traductor para el dialecto SQL de PostgreSQL.
    
    Usa sqlglot para convertir el AST al dialecto postgres.
    Particularidades de PostgreSQL:
    - Paginacion con LIMIT/OFFSET
    - Concatenacion con ||
    - Nombres de columna y tabla en minusculas por defecto
    """

    def traducir(self, repr_intermedia):
        """
        Convierte la representacion intermedia al SQL de PostgreSQL.
        repr_intermedia = diccionario con tablas, columnas, condicion, orden y ast
        Devuelve una cadena de texto SQL lista para ejecutar en PostgreSQL.
        """
        # Usamos el AST que genero sqlglot durante el analisis
        # y le pedimos que lo genere en dialecto postgres
        ast = repr_intermedia['ast']
        return ast.sql(dialect='postgres')