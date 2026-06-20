import sqlglot
from src.abstracto.traductor import Traductor

class TraductorMariaDB(Traductor):
    """
    Traductor para el dialecto SQL de MariaDB.
    
    Usa sqlglot para convertir el AST al dialecto mysql.
    Particularidades de MariaDB:
    - Paginacion con LIMIT/OFFSET
    - Concatenacion con CONCAT()
    - Identificadores con palabras reservadas entre comillas invertidas
    """

    def traducir(self, repr_intermedia):
        """
        Convierte la representacion intermedia al SQL de MariaDB.
        repr_intermedia = diccionario con tablas, columnas, condicion, orden y ast
        Devuelve una cadena de texto SQL lista para ejecutar en MariaDB.
        """
        # Usamos el AST que genero sqlglot durante el analisis
        # y le pedimos que lo genere en dialecto mysql (MariaDB)
        ast = repr_intermedia['ast']
        return ast.sql(dialect='mysql')