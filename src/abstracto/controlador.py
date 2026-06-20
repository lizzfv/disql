import importlib
from src.catalogo import Catalogo
from src.encriptacion import Encriptacion
from src.abstracto.analizador import Analizador

class Controlador:
    """
    Orquestador principal del sistema DiSQL.
    
    Al arrancar:
    - Lee el Catalogo DiSQL para saber que SGBDs hay
    - Desencripta las credenciales
    - Crea un Conector y un ControladorSistema por cada SGBD
    - Intenta conectarse a todos marca como no disponible los que fallen
    - Crea el Analizador pasandole el catalogo y los ControladorSistema
    
    Durante el procesamiento:
    - Recibe el SQL del usuario
    - Comprueba que los SGBDs necesarios estan disponibles
    - Pasa el SQL al Analizador
    - Recibe los resultados finales del Analizador (que los obtiene del Ejecutor)
    - Devuelve los resultados al usuario
    - Convierte errores tecnicos en mensajes comprensibles
    """

    # Mapeo de tipos a nombres de clase.
    # Para anadir un nuevo SGBD solo hay que anadir su nombre aqui
    # y crear los tres archivos correspondientes en src/nuevo_sgbd/
    NOMBRES_CLASES = {
        'mariadb': 'MariaDB',
        'postgres': 'Postgres',
        'oracle': 'Oracle'
    }

    def __init__(self):
        self.catalogo = Catalogo()
        self.encriptacion = Encriptacion()
        self.controladores_sistema = {}  # tipo -> ControladorSistema
        self.sgbds_disponibles = {}      # tipo -> True/False
        self.analizador = None           # se crea en iniciar_sistema()

    def iniciar_sistema(self):
        """
        Lee el catalogo, crea los componentes de cada SGBD
        e intenta conectarse a todos.
        Usa importlib para cargar las clases dinamicamente 
        para anadir un nuevo SGBD solo hay que anadir su nombre
        en NOMBRES_CLASES y crear los tres archivos correspondientes.
        Al final crea el Analizador con el catalogo y los ControladorSistema.
        """
        print("Iniciando DiSQL...")
        sgbds = self.catalogo.obtener_sgbds()

        for sgbd in sgbds:
            tipo = sgbd['tipo']
            try:
                if tipo not in self.NOMBRES_CLASES:
                    print(f"Tipo de SGBD no soportado: {tipo}")
                    print(f"Aniade '{tipo}' a NOMBRES_CLASES en controlador.py")
                    continue

                nombre = self.NOMBRES_CLASES[tipo]
                contrasena = self.encriptacion.desencriptar(sgbd['contrasena'])

                # Cargamos el Conector dinamicamente segun el tipo de SGBD
                modulo_conector = importlib.import_module(f"src.{tipo}.conector_{tipo}")
                clase_conector = getattr(modulo_conector, f"Conector{nombre}")
                conector = clase_conector(
                    host=sgbd['host'],
                    puerto=sgbd['puerto_bd'],
                    usuario=sgbd['usuario'],
                    contrasena=contrasena,
                    base_datos=sgbd['base_datos']
                )

                # Cargamos el ControladorSistema dinamicamente
                modulo_ctrl = importlib.import_module(f"src.{tipo}.controlador_sistema_{tipo}")
                clase_ctrl = getattr(modulo_ctrl, f"ControladorSistema{nombre}")
                ctrl_sistema = clase_ctrl(conector)

                # Intentamos conectarnos si falla marcamos como no disponible
                ctrl_sistema.iniciar()
                self.controladores_sistema[tipo] = ctrl_sistema
                self.sgbds_disponibles[tipo] = True
                print(f"{tipo} conectado correctamente")

            except Exception as e:
                # El sistema sigue arrancando con los SGBDs que si responden
                self.sgbds_disponibles[tipo] = False
                print(f"{tipo} no disponible: {e}")

        # Creamos el Analizador con el catalogo y los ControladorSistema disponibles
        # El Analizador los usara para validar tablas y esquemas durante el analisis
        self.analizador = Analizador(self.catalogo, self.controladores_sistema, self.sgbds_disponibles)
        print("Sistema iniciado")

    def procesar_consulta(self, sql):
        """
        Punto de entrada para el usuario.
        Recibe el SQL y lo pasa al Analizador.
        El Analizador valida y genera la representacion intermedia,
        que pasa al Ejecutor. El Ejecutor devuelve los resultados
        al Controlador, que los entrega al usuario.
        sql = consulta SQL escrita por el usuario
        """
        if self.analizador is None:
            self.manejar_error("El sistema no esta iniciado. Llama a iniciar_sistema() primero.")
            return None

        try:
            for fila in self.analizador.analizar(sql):
                yield fila
        except ValueError as e:
            self.manejar_error(e)
            raise  # relanza la excepcion para que app.py la capture
        except Exception as e:
            self.manejar_error(e)
            raise  # relanza la excepcion para que app.py la capture
        
    def manejar_error(self, error):
        """
        Convierte errores tecnicos en mensajes comprensibles para el usuario.
        En vez de propagar excepciones del driver, muestra que SGBD fallo
        y que tablas estan afectadas.
        """
        print(f"Error en DiSQL: {error}")

    def detener_sistema(self):
        """
        Cierra todas las conexiones limpiamente al apagar el sistema.
        Se llama siempre al terminar — tanto en cierre normal como en error.
        """
        # Cerramos cada ControladorSistema — que internamente cierra su Conector
        for tipo, ctrl in self.controladores_sistema.items():
            try:
                ctrl.detener()
                print(f"{tipo} desconectado correctamente")
            except Exception as e:
                print(f"{tipo} error al desconectar: {e}")

        # Cerramos el catalogo SQLite
        self.catalogo.cerrar()
        print("Catalogo cerrado")