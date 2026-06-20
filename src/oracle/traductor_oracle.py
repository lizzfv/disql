import sqlglot
from src.abstracto.traductor import Traductor

class TraductorOracle(Traductor):
    """
    Traductor para el dialecto SQL de Oracle.
    
    Usa sqlglot para convertir el AST al dialecto oracle.
    Particularidades de Oracle:
    - Paginacion con OFFSET m ROWS FETCH NEXT n ROWS ONLY (Oracle 12c+)
    - Concatenacion con ||
    - Nombres de tabla y columna en MAYUSCULAS por defecto
    - Las tablas necesitan el prefijo del esquema: disql.empleados
    """

    # Esquema del usuario DiSQL en Oracle
    # Todas las tablas de DiSQL estan bajo este esquema en el PDB PORADBA
    ESQUEMA = 'disql'

    def traducir(self, repr_intermedia):
        
        # Hacemos una copia del AST para no modificar el original 
        # (es un objeto compartido y como lo modifique 
        # todo a disql.tabla ni maria ni postgres podrian traducirlo)
        ast = repr_intermedia['ast'].copy()

        # buscamos todas las tablas en el AST y les ponemos el prefijo del esquema si no lo tienen
        for tabla in ast.find_all(sqlglot.exp.Table):
            if not tabla.db:
                tabla.set('db', sqlglot.exp.Identifier(this=self.ESQUEMA))
                
        #generamos el SQL traducido al dialecto de Oracle usando sqlglot
        return ast.sql(dialect='oracle')