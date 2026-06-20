import os
from cryptography.fernet import Fernet

# Ruta al archivo de la clave secreta
# Está en la raíz del proyecto y NUNCA se sube a GitHub
RUTA_CLAVE = os.path.join(os.path.dirname(__file__), '..', 'clave.key')

class Encriptacion:
    """
    Gestiona la encriptación y desencriptación de credenciales.
    
    Usa Fernet, encriptación simétrica de la librería cryptography.
    Fernet garantiza que los datos encriptados no pueden leerse
    sin la clave secreta.
    
    La clave se guarda en clave.key — nunca se sube a GitHub.
    Si no existe se genera automáticamente la primera vez.
    """

    def __init__(self):
        self.clave = self._cargar_o_generar_clave()
        self.fernet = Fernet(self.clave)

    def _cargar_o_generar_clave(self):
        """
        Si existe clave.key la carga.
        Si no existe la genera y la guarda.
        Solo se genera una vez si se pierde las credenciales
        encriptadas quedan ilegib, es.
        """
        if os.path.exists(RUTA_CLAVE):
            with open(RUTA_CLAVE, 'rb') as f: #la clave es un binario
                return f.read()
        else:
            clave = Fernet.generate_key()
            with open(RUTA_CLAVE, 'wb') as f:
                f.write(clave)
            print(f"Clave generada y guardada en {RUTA_CLAVE}!!!")
            return clave

    def encriptar(self, texto):
        """
        Encripta un texto y devuelve los bytes encriptados.
        texto = credencial en texto plano (contraseña, usuario...)
        """
        return self.fernet.encrypt(texto.encode()).decode()

    def desencriptar(self, texto_encriptado):
        """
        Desencripta un texto encriptado y devuelve el original.
        texto_encriptado = credencial encriptada guardada en SQLite
        """
        return self.fernet.decrypt(texto_encriptado.encode()).decode()