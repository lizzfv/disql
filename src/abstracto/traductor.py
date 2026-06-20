from abc import ABC, abstractmethod

class Traductor(ABC):
    """
    Clase abstracta que define la interfaz de los Traductores.
    
    Cada Traductor convierte la representacion intermedia generada
    por el Analizador al SQL concreto del dialecto de su SGBD.
    
    Hay tres implementaciones:
    - TraductorMariaDB  → genera SQL en dialecto MariaDB
    - TraductorPostgres → genera SQL en dialecto PostgreSQL
    - TraductorOracle   → genera SQL en dialecto Oracle
    
    El Ejecutor invoca al Traductor correspondiente sin conocer
    sus detalles internos — solo llama a traducir() y recibe SQL.
    """

    @abstractmethod
    def traducir(self, repr_intermedia):
        """
        Convierte la representacion intermedia al SQL del dialecto concreto.
        repr_intermedia = diccionario con tablas, columnas, condicion, orden y ast
        Devuelve una cadena de texto SQL lista para ejecutar.
        """
        pass