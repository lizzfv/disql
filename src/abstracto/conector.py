from abc import ABC, abstractmethod
import time

class Conector(ABC):
    """
    Clase abstracta que define la interfaz de comunicación física
    con un SGBD remoto. Cada SGBD concreto implementa esta clase.
    
    La lógica de reintentos con espera exponencial está implementada
    aquí directamente porque es idéntica para todos los SGBDs.
    Cada subclase solo implementa cómo conectarse a su BD concreta.
    """

    def __init__(self, tamano_lote=1000, max_reintentos=4):
        self.tamano_lote = tamano_lote # Número de filas a recuperar por lote
        self.max_reintentos = max_reintentos # Máximo número de reintentos antes de fallar
        self.conexion = None  # La conexión empieza cerrada


    def conectar_con_reintento(self):
        """
        Intenta establecer la conexión con espera exponencial.
        1er reintento → espera 1s
        2º reintento  → espera 2s
        3er reintento → espera 4s
        4º reintento  → espera 8s
        Si agota los reintentos, lanza una excepción con detalle del fallo.
        """
        espera = 1
        ultimo_error = None

        for intento in range(1, self.max_reintentos + 1): 
            try:
                self.conectar()
                return  # Conexión exitosa, salimos
            except Exception as e:
                ultimo_error = e
                print(f"Intento {intento}/{self.max_reintentos} fallido: {e}") 
                if intento < self.max_reintentos:
                    print(f"Reintentando en {espera} segundos...")
                    time.sleep(espera)
                    espera *= 2  # Espera exponencial

        raise ConnectionError(
            f"No se pudo conectar tras {self.max_reintentos} intentos. "
            f"Último error: {ultimo_error}"
        )

    @abstractmethod
    def conectar(self):
        """Abre la conexión física con el SGBD."""
        pass

    @abstractmethod
    def desconectar(self):
        """Cierra la conexión limpiamente."""
        pass

    @abstractmethod
    def ejecutar(self, sql):
        """
        Envía el SQL al SGBD y devuelve los resultados normalizados.
        Recupera las filas en lotes de self.tamano_lote para no
        materializar el conjunto completo en memoria.
        """
        pass

    @abstractmethod
    def normalizar_resultados(self, cursor, filas):
        """
        Convierte las filas del cursor al formato común de DiSQL:
        lista de diccionarios Python donde cada clave es el nombre
        de la columna y cada valor es un tipo estándar Python
        (str, int, float, Decimal, datetime, bool).
        """
        pass
    
    @abstractmethod
    def ejecutar_sin_resultado(self, sql):
        """
        Ejecuta una sentencia SQL que no devuelve filas."""
        pass
    
    @abstractmethod
    def ejecutar_cursor(self, sql):
        """
        Envía el SQL al SGBD y devuelve el cursor abierto sin cerrarlo.
        El llamador (Ejecutor) es responsable de cerrar el cursor
        cuando termine de leer las filas.
        A diferencia de ejecutar(), no materializa los resultados —
        deja el cursor abierto para que el Ejecutor lea fila a fila.
        """
        pass