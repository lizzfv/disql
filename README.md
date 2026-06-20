# DiSQL

Sistema de consulta SQL distribuida que actua como punto de acceso
unico a multiples sistemas gestores de bases de datos relacionales
heterogeneos. Traduce automaticamente las consultas SQL al dialecto
de cada SGBD participante, las enruta al servidor correspondiente y
unifica los resultados.
----------------------------------------------------------------------

## Que es DiSQL

DiSQL permite ejecutar una unica consulta SQL sobre datos repartidos
entre varios SGBD distintos, sin que el usuario tenga que conocer en
que sistema se encuentra cada dato ni adaptar la sintaxis al dialecto
de cada motor.

El sistema soporta:

    proyeccion        SELECT
    filtrado          WHERE
    ordenacion        ORDER BY
    agregacion        COUNT, SUM, AVG, MAX, MIN
    agrupacion        GROUP BY

Sistemas gestores soportados actualmente: MariaDB, PostgreSQL y Oracle.

----------------------------------------------------------------------

## Arquitectura

    Usuario
       |
    Controlador
       |
    Analizador
       |
    Ejecutor de Consulta Distribuida
       |
    Traductores de Dialecto
       |
    Controladores de Sistema
       |
    Conectores
       |
    SGBD remotos (MariaDB / PostgreSQL / Oracle)

El catalogo DiSQL, una base de datos SQLite local, registra que
tablas estan disponibles y en que sistemas residen.

----------------------------------------------------------------------

## Requisitos

    Python 3.10 o superior
    pip

Dependencias del proyecto, instalables con pip:

    Flask
    cryptography
    matplotlib
    numpy
    oracledb
    psycopg2-binary
    PyMySQL
    sqlglot

----------------------------------------------------------------------

## Instalacion

    git clone https://github.com/lizzfv/disql.git
    cd disql
    pip install -r requirements.txt
    python3 app.py

La aplicacion queda disponible en:

    http://localhost:5000

----------------------------------------------------------------------

## Configuracion de los SGBD

Al arrancar por primera vez, DiSQL genera automaticamente:

    catalogo.db     catalogo interno del sistema (SQLite)
    clave.key       clave de cifrado de credenciales (Fernet)

Ninguno de estos archivos se distribuye en el repositorio: cada
instalacion genera los suyos propios.

Desde el panel de administracion, accesible en /admin, se registran
los SGBD a conectar indicando host, puerto, usuario y contrasena.
DiSQL descubre automaticamente las tablas disponibles en cada sistema
registrado.

----------------------------------------------------------------------

## Estructura del repositorio

    app.py                      punto de entrada de la aplicacion
    gestor_catalogo.py          gestor de linea de comandos del catalogo
    requirements.txt            dependencias del proyecto
    src/
        abstracto/               clases base del sistema
        mariadb/                 implementacion especifica de MariaDB
        postgres/                implementacion especifica de PostgreSQL
        oracle/                  implementacion especifica de Oracle
    templates/                  plantillas HTML de la interfaz web
    pruebas/
        generar_datos.py         generacion de datos de prueba
        medir_rendimiento.py     estudios de tiempo de respuesta

----------------------------------------------------------------------

## Anadir soporte para un nuevo SGBD

La arquitectura modular permite incorporar un nuevo sistema gestor
sin modificar el resto del codigo. Es necesario implementar tres
componentes dentro de una nueva carpeta en src/:

    traductor_nuevo.py              hereda de Traductor
    conector_nuevo.py               hereda de Conector
    controlador_sistema_nuevo.py    hereda de ControladorSistema

y registrar el tipo correspondiente en el diccionario de tipos del
Controlador.

----------------------------------------------------------------------

## Reproducir los estudios de tiempo

Los scripts de pruebas/ requieren las credenciales reales de los
SGBD, proporcionadas como variables de entorno:

    export MARIADB_PASSWORD="..."
    export POSTGRES_PASSWORD="..."
    export ORACLE_PASSWORD="..."

    python3 pruebas/generar_datos.py
    python3 pruebas/medir_rendimiento.py

----------------------------------------------------------------------

## Licencia

Proyecto academico desarrollado como Trabajo de Fin de Grado.
Universidad de Granada, 2026.
