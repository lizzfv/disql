import sqlite3
import os

RUTA_CATALOGO = os.path.join(os.path.dirname(__file__), '..', 'catalogo.db')

class Catalogo:
    """
    Gestiona el catálogo de metadatos de DiSQL.
    
    Almacena en SQLite:
    - Los SGBDs registrados con sus credenciales de conexión
    - Las tablas disponibles en cada SGBD
    
    El Controlador lo consulta al arrancar para saber qué SGBDs hay.
    El Analizador lo consulta para saber en qué SGBDs está cada tabla.
    """

    def __init__(self):
        self.conexion = sqlite3.connect(RUTA_CATALOGO, check_same_thread=False)
        self.conexion.row_factory = sqlite3.Row
        self._crear_tablas()

    def _crear_tablas(self):
        """
        Crea las tablas del catálogo si no existen.
        Se ejecuta siempre al iniciar — si ya existen no hace nada.
        """
        cursor = self.conexion.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sgbd (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo       TEXT NOT NULL,
                host       TEXT NOT NULL,
                puerto_bd  INTEGER NOT NULL,
                usuario    TEXT NOT NULL,
                contrasena TEXT NOT NULL,
                base_datos TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tabla (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre  TEXT NOT NULL,
                sgbd_id INTEGER NOT NULL,
                FOREIGN KEY (sgbd_id) REFERENCES sgbd(id)
            )
        """)

        # Agregadores externos — los que el usuario puede usar en sus consultas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agregador_externo (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre  TEXT NOT NULL UNIQUE,
                formula TEXT NOT NULL
            )
        """)

        # Agregadores internos — los que se mandan a los SGBDs
        # AVG no aparece aqui porque nunca se manda directamente a un SGBD
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agregador_interno (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
        """)

        # Tabla intermedia — que internos necesita cada externo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agregador_externo_interno (
                agregador_externo_id INTEGER NOT NULL,
                agregador_interno_id INTEGER NOT NULL,
                PRIMARY KEY (agregador_externo_id, agregador_interno_id),
                FOREIGN KEY (agregador_externo_id) REFERENCES agregador_externo(id),
                FOREIGN KEY (agregador_interno_id) REFERENCES agregador_interno(id)
            )
        """)

        self.conexion.commit()
        cursor.close()
        
        # Insertamos los datos iniciales si no existen
        self._inicializar_agregadores()
        
    def _inicializar_agregadores(self):
        """
        Inserta los agregadores por defecto si no existen.
        Solo se ejecuta la primera vez — si ya hay datos no hace nada.
        """
        cursor = self.conexion.cursor()
        
        # Comprobamos si ya hay datos
        cursor.execute("SELECT COUNT(*) FROM agregador_externo")
        if cursor.fetchone()[0] > 0:
            cursor.close()
            return

        # Insertamos los agregadores internos — los que van a los SGBDs
        internos = ['COUNT', 'SUM', 'MAX', 'MIN']
        for nombre in internos:
            cursor.execute(
                "INSERT INTO agregador_interno (nombre) VALUES (?)", (nombre,))

        # Insertamos los agregadores externos con su formula
        # La formula indica como combinar los resultados parciales de cada SGBD
        externos = [
            ('COUNT', 'COUNT'),           # suma los COUNT parciales
            ('SUM',   'SUM'),             # suma los SUM parciales
            ('MAX',   'MAX'),             # maximo de los MAX parciales
            ('MIN',   'MIN'),             # minimo de los MIN parciales
            ('AVG',   'SUM/COUNT'),       # suma de SUMs dividido entre suma de COUNTs
        ]
        for nombre, formula in externos:
            cursor.execute(
                "INSERT INTO agregador_externo (nombre, formula) VALUES (?, ?)",
                (nombre, formula))

        self.conexion.commit()

        # Insertamos las dependencias — que internos necesita cada externo
        dependencias = [
            ('COUNT', ['COUNT']),
            ('SUM',   ['SUM']),
            ('MAX',   ['MAX']),
            ('MIN',   ['MIN']),
            ('AVG',   ['SUM', 'COUNT']),  # AVG necesita SUM y COUNT internamente
        ]
        for nombre_externo, internos_necesarios in dependencias:
            cursor.execute(
                "SELECT id FROM agregador_externo WHERE nombre = ?", (nombre_externo,))
            ext_id = cursor.fetchone()[0]
            for nombre_interno in internos_necesarios:
                cursor.execute(
                    "SELECT id FROM agregador_interno WHERE nombre = ?", (nombre_interno,))
                int_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO agregador_externo_interno 
                    (agregador_externo_id, agregador_interno_id) VALUES (?, ?)
                """, (ext_id, int_id))

        self.conexion.commit()
        cursor.close()

    def insertar_sgbd(self, tipo, host, puerto_bd, usuario, contrasena, base_datos):
        """
        Registra un nuevo SGBD en el catálogo.
        Devuelve el id del SGBD insertado.
        """
        cursor = self.conexion.cursor()
        cursor.execute("""
            INSERT INTO sgbd (tipo, host, puerto_bd, usuario, contrasena, base_datos)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tipo, host, puerto_bd, usuario, contrasena, base_datos))
        self.conexion.commit()
        sgbd_id = cursor.lastrowid
        cursor.close()
        return sgbd_id

    def eliminar_sgbd(self, sgbd_id):
        """Elimina un SGBD y todas sus tablas asociadas."""
        cursor = self.conexion.cursor()
        cursor.execute("DELETE FROM tabla WHERE sgbd_id = ?", (sgbd_id,))
        cursor.execute("DELETE FROM sgbd WHERE id = ?", (sgbd_id,))
        self.conexion.commit()
        cursor.close()

    def insertar_tabla(self, nombre, sgbd_id):
        """Registra una tabla en un SGBD concreto."""
        cursor = self.conexion.cursor()
        cursor.execute("""
            INSERT INTO tabla (nombre, sgbd_id)
            VALUES (?, ?)
        """, (nombre, sgbd_id))
        self.conexion.commit()
        cursor.close()

    def eliminar_tabla(self, tabla_id):
        """Elimina una tabla del catálogo."""
        cursor = self.conexion.cursor()
        cursor.execute("DELETE FROM tabla WHERE id = ?", (tabla_id,))
        self.conexion.commit()
        cursor.close()

    def obtener_sgbds(self):
        """
        Devuelve todos los SGBDs registrados.
        El Controlador lo usa al arrancar para conectarse a todos.
        """
        cursor = self.conexion.cursor()
        cursor.execute("SELECT * FROM sgbd")
        filas = cursor.fetchall()
        cursor.close()
        return [dict(fila) for fila in filas]

    def obtener_sgbds_de_tabla(self, nombre_tabla):
        """
        Devuelve los SGBDs donde está una tabla concreta.
        El Analizador lo usa para saber en qué SGBDs está cada tabla.
        """
        cursor = self.conexion.cursor()
        cursor.execute("""
            SELECT sgbd.*
            FROM sgbd
            JOIN tabla ON sgbd.id = tabla.sgbd_id
            WHERE tabla.nombre = ?
        """, (nombre_tabla,))
        filas = cursor.fetchall()
        cursor.close()
        return [dict(fila) for fila in filas]

    def obtener_sgbd_por_tipo(self, tipo):
        """
        Devuelve las credenciales de un SGBD concreto.
        El Controlador lo usa para crear los Conectores.
        """
        cursor = self.conexion.cursor()
        cursor.execute("SELECT * FROM sgbd WHERE tipo = ?", (tipo,))
        fila = cursor.fetchone()
        cursor.close()
        if fila:
            return dict(fila)
        return None

    def cerrar(self):
        """Cierra la conexión con el catálogo."""
        self.conexion.close()
        
    def obtener_factores_agregador(self, nombre_externo):
        """
        Devuelve los agregadores internos que necesita un agregador externo
        y la formula para combinar sus resultados.
        Por ejemplo para AVG devuelve:
        - internos: ['SUM', 'COUNT']
        - formula: 'SUM/COUNT'
        """
        cursor = self.conexion.cursor()
        
        # Obtenemos la formula del externo
        cursor.execute(
            "SELECT formula FROM agregador_externo WHERE nombre = ?", (nombre_externo,))
        fila = cursor.fetchone()
        if not fila:
            cursor.close()
            return None
        formula = fila[0]
        
        # Obtenemos los internos que necesita
        cursor.execute("""
            SELECT agregador_interno.nombre
            FROM agregador_interno
            JOIN agregador_externo_interno 
                ON agregador_interno.id = agregador_externo_interno.agregador_interno_id
            JOIN agregador_externo 
                ON agregador_externo.id = agregador_externo_interno.agregador_externo_id
            WHERE agregador_externo.nombre = ?
        """, (nombre_externo,))
        internos = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        return {'formula': formula, 'internos': internos}