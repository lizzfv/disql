import importlib
import copy
import sqlglot
import random

class Ejecutor:
    """
    Ejecutor de Consulta Distribuida.

    Recibe la representacion intermedia del Analizador y coordina
    su ejecucion en los SGBDs participantes.

    Tanto con ORDER BY como sin él, devuelve las filas de una en una
    mediante un generador — sin acumular el resultado completo en memoria.
    """

    NOMBRES_CLASES = {
        'mariadb': 'MariaDB',
        'postgres': 'Postgres',
        'oracle': 'Oracle'
    }

    def __init__(self, controladores_sistema, sgbds_disponibles, catalogo):
        self.controladores_sistema = controladores_sistema
        self.sgbds_disponibles = sgbds_disponibles
        self.catalogo = catalogo  # para consultar los factores de cada agregador
        self.traductores = self._cargar_traductores()

    def _cargar_traductores(self):
        traductores = {}
        for tipo, nombre in self.NOMBRES_CLASES.items():
            try:
                modulo = importlib.import_module(f"src.{tipo}.traductor_{tipo}")
                clase = getattr(modulo, f"Traductor{nombre}")
                traductores[tipo] = clase()
            except Exception as e:
                print(f"No se pudo cargar el Traductor de {tipo}: {e}")
        return traductores

    def ejecutar(self, repr_intermedia):
        """
        Metodo principal. Determina los SGBDs necesarios, comprueba
        disponibilidad y bifurca segun haya ORDER BY, agregaciones o ninguno.
        """
        sgbds_necesarios = set()
        for sgbds in repr_intermedia['sgbds_por_tabla'].values():
            for tipo in sgbds:
                sgbds_necesarios.add(tipo)

        for tipo in sgbds_necesarios:
            if not self.sgbds_disponibles.get(tipo, False):
                raise RuntimeError(
                    f"El SGBD '{tipo}' no esta disponible. "
                    f"No se puede ejecutar la consulta."
                )

        # Bifurcamos segun el tipo de consulta
        if repr_intermedia.get('agregaciones'):
            # Hay funciones de agregacion: COUNT, SUM, AVG, MAX, MIN
            yield from self._ejecutar_con_agregaciones(repr_intermedia, sgbds_necesarios)
        elif repr_intermedia['orden']:
            # Hay ORDER BY  merge sort con cursores
            yield from self._ejecutar_con_merge(repr_intermedia, sgbds_necesarios)
        else:
            # Consulta simple sin orden ni agregaciones
            yield from self._ejecutar_sin_orden(repr_intermedia, sgbds_necesarios)
    
    
    def _ejecutar_sin_orden(self, repr_intermedia, sgbds_necesarios):
        """
        Sin ORDER BY: abre un cursor por SGBD y emite filas de una en una
        entrelazándolas de forma aleatoria. Simula el comportamiento asíncrono
        y no determinista del modelo relacional puro.
        """
        
        vistos = set()
        cursores = {}
        filas_actuales = {}

        # 1. Abrimos un cursor por cada SGBD y cargamos la primera fila de cada uno
        for tipo in sgbds_necesarios:
            try:
                sql = self.traductores[tipo].traducir(repr_intermedia)
                cursores[tipo] = self.controladores_sistema[tipo].ejecutar_consulta_cursor(sql)
                filas_actuales[tipo] = self.controladores_sistema[tipo].obtener_fila(cursores[tipo])
            except Exception as e:
                raise RuntimeError(f"Error al abrir cursor en {tipo}: {e}")

        try:
            while True:
                # SGBDs que aún tienen filas disponibles
                tipos_con_filas = [t for t, f in filas_actuales.items() if f is not None]
                if not tipos_con_filas:
                    break

                # 2. Aplicamos la fórmula exacta sugerida por el profesor para elegir SGBD
                # El '% len(...)' adapta la fórmula si participan 1, 2 o 3 SGBDs dinámicamente
                indice_aleatorio = random.randint(1, 500000) % len(tipos_con_filas)
                tipo_elegido = tipos_con_filas[indice_aleatorio]
                
                fila = filas_actuales[tipo_elegido]

                # 3. Filtro de duplicados y emisión distribuida (yield)
                fila_tupla = tuple(sorted(fila.items()))
                if fila_tupla not in vistos:
                    vistos.add(fila_tupla)
                    # Añadimos metainformación de origen para la interfaz visual
                    yield {**fila, '_sgbd': tipo_elegido}

                # 4. Avanzamos única y exclusivamente el cursor del SGBD elegido
                filas_actuales[tipo_elegido] = self.controladores_sistema[tipo_elegido].obtener_fila(
                    cursores[tipo_elegido]
                )

        finally:
            # Aseguramos el cierre de todos los cursores abiertos
            for cursor in cursores.values():
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def _ejecutar_con_merge(self, repr_intermedia, sgbds_necesarios):
        """
        Con ORDER BY: merge sort sobre cursores abiertos.
        Cada SGBD ya devuelve sus filas ordenadas localmente.
        El Ejecutor fusiona comparando una fila por SGBD a la vez
        y emite cada fila de una en una sin acumular en memoria.
        """
        criterios = self._parsear_orden(repr_intermedia['orden'])
        cursores = {}
        filas_actuales = {}

        try:
            for tipo in sgbds_necesarios:
                sql = self.traductores[tipo].traducir(repr_intermedia)
                cursores[tipo] = self.controladores_sistema[tipo].ejecutar_consulta_cursor(sql)
                filas_actuales[tipo] = self.controladores_sistema[tipo].obtener_fila(cursores[tipo])

            vistos = set()

            while True:
                tipos_con_filas = [t for t, f in filas_actuales.items() if f is not None]
                if not tipos_con_filas:
                    break

                ganador = self._elegir_ganador(filas_actuales, tipos_con_filas, criterios)
                fila = filas_actuales[ganador]

                fila_tupla = tuple(sorted(fila.items()))
                if fila_tupla not in vistos:
                    vistos.add(fila_tupla)
                    fila_con_origen = {**fila, '_sgbd': ganador}
                    yield fila_con_origen    
                         
                filas_actuales[ganador] = self.controladores_sistema[ganador].obtener_fila(
                    cursores[ganador]
                )

        finally:
            for cursor in cursores.values():
                try:
                    cursor.close()
                except Exception:
                    pass
                
    def _ejecutar_con_group_by(self, repr_intermedia, sgbds_necesarios):
        """
        Ejecuta consultas con GROUP BY aplicando factorización de agregadores.

        Recoge los resultados parciales de todos los SGBDs agrupados por la
        clave de agrupación y los combina usando las fórmulas del catálogo.
        Garantiza resultados correctos incluso cuando un grupo tiene filas
        distribuidas entre múltiples SGBDs.
        """
        agregaciones = repr_intermedia.get('agregaciones', [])

        # Limpiamos el group por si viene con "GROUP BY" incluido
        group_raw = repr_intermedia.get('group', '').strip()
        columna_group = group_raw.upper().replace('GROUP BY', '').strip().lower()

        # 1. Consultamos el catálogo igual que en _ejecutar_con_agregaciones()
        factores_por_agregador = {}
        for agr in agregaciones:
            funcion = agr['funcion'].upper()
            factores = self.catalogo.obtener_factores_agregador(funcion)
            if factores:
                factores_por_agregador[funcion] = factores
            else:
                factores_por_agregador[funcion] = {'internos': [funcion], 'formula': funcion}

        # 2. Factorizamos igual que en agregaciones globales
        #    _factorizar_consulta genera los alias DI_SUM_0, DI_COUNT_1, etc.
        repr_modificada, mapa_alias = self._factorizar_consulta(
            repr_intermedia, factores_por_agregador
        )

        # 3. Reconstruimos el SQL poniendo primero la columna de agrupación,
        #    luego los alias generados, y añadiendo GROUP BY al final.
        #    Filtramos columna_group de las columnas modificadas para no duplicar.
        alias_columnas = [
            col for col in repr_modificada['columnas']
            if col.upper() != columna_group.upper()
        ]
        sql_base = (
            f"SELECT {columna_group}, {', '.join(alias_columnas)}"
            f" FROM {repr_intermedia['tablas'][0]}"
        )
        condicion = repr_intermedia.get('condicion', '')
        if condicion:
            sql_base += f" {condicion}"
        sql_base += f" GROUP BY {columna_group}"

        repr_modificada['ast'] = sqlglot.parse_one(sql_base)

        # 4. Recogemos parciales de cada SGBD organizados por valor de grupo.
        #    Guardamos también el SGBD de origen de cada grupo para la metainformación.
        #    { valor_grupo -> { alias_seguro -> [val_sgbd1, ...], '_sgbd': tipo } }
        parciales_por_grupo = {}

        for tipo in sgbds_necesarios:
            try:
                sql = self.traductores[tipo].traducir(repr_modificada)
                resultados = self.controladores_sistema[tipo].ejecutar_consulta(sql)

                for fila in resultados:
                    fila_upper = {k.upper(): v for k, v in fila.items()}
                    valor_grupo = fila_upper.get(columna_group.upper())

                    if valor_grupo not in parciales_por_grupo:
                        parciales_por_grupo[valor_grupo] = {}
                        # Guardamos el SGBD de origen la primera vez que vemos el grupo
                        parciales_por_grupo[valor_grupo]['_sgbd'] = tipo

                    for alias_dict in mapa_alias.values():
                        for alias_seguro in alias_dict.values():
                            alias_upper = alias_seguro.upper()
                            if alias_upper in fila_upper and fila_upper[alias_upper] is not None:
                                if alias_upper not in parciales_por_grupo[valor_grupo]:
                                    parciales_por_grupo[valor_grupo][alias_upper] = []
                                parciales_por_grupo[valor_grupo][alias_upper].append(
                                    float(fila_upper[alias_upper])
                                )

            except Exception as e:
                raise RuntimeError(f"Error al ejecutar GROUP BY en {tipo}: {e}")

        # 5. Para cada grupo combinamos parciales y emitimos una fila final
        for valor_grupo, parciales in parciales_por_grupo.items():
            fila_resultado = {columna_group: valor_grupo}
            fila_resultado['_sgbd'] = parciales.get('_sgbd', 'unknown')

            for agr in agregaciones:
                funcion = agr['funcion'].upper()
                factores = factores_por_agregador.get(funcion, {})
                formula = factores.get('formula', funcion)
                internos = factores.get('internos', [funcion])

                valores_por_interno = {}
                for interno in internos:
                    alias_seguro = mapa_alias[agr['sql']][interno].upper()
                    valores_por_interno[interno] = parciales.get(alias_seguro, [])

                fila_resultado[agr['sql']] = self._aplicar_formula(
                    formula, valores_por_interno
                )

            yield fila_resultado
             
    def _parsear_orden(self, orden_str):
        criterios = []
        parte = orden_str.replace('ORDER BY', '').strip()
        for fragmento in parte.split(','):
            tokens = fragmento.strip().split()
            columna = tokens[0]
            direccion = tokens[1].upper() if len(tokens) > 1 else 'ASC'
            criterios.append((columna, direccion))
        return criterios

    def _elegir_ganador(self, filas_actuales, tipos_con_filas, criterios):
        ganador = tipos_con_filas[0]
        for tipo in tipos_con_filas[1:]:
            for columna, direccion in criterios:
                val_ganador = filas_actuales[ganador][columna]
                val_candidato = filas_actuales[tipo][columna]
                if val_ganador == val_candidato:
                    continue
                if direccion == 'ASC':
                    if val_candidato < val_ganador:
                        ganador = tipo
                else:
                    if val_candidato > val_ganador:
                        ganador = tipo
                break
        return ganador

    def _ejecutar_con_agregaciones(self, repr_intermedia, sgbds_necesarios):
        """
        Ejecuta consultas con funciones de agregacion (COUNT, SUM, AVG, MAX, MIN).
        Consulta el catalogo para saber como factorizar cada agregador.
        """
        agregaciones = repr_intermedia['agregaciones']
        hay_group = repr_intermedia.get('group')

        if hay_group:
            yield from self._ejecutar_con_group_by(repr_intermedia, sgbds_necesarios)
            return

        # 1. Consultamos el catálogo para saber los factores de cada función
        factores_por_agregador = {}
        for agr in agregaciones:
            funcion = agr['funcion'].upper()
            factores = self.catalogo.obtener_factores_agregador(funcion)
            if factores:
                factores_por_agregador[funcion] = factores
            else:
                factores_por_agregador[funcion] = {'internos': [funcion], 'formula': funcion}

        # 2. Modificamos la consulta para usar alias seguros (ej: DI_SUM_0)
        repr_modificada, mapa_alias = self._factorizar_consulta(repr_intermedia, factores_por_agregador)

        # 3. Recogemos los resultados parciales de cada SGBD
        parciales = []
        for tipo in sgbds_necesarios:
            try:
                sql = self.traductores[tipo].traducir(repr_modificada)
                resultados = self.controladores_sistema[tipo].ejecutar_consulta(sql)
                if resultados and resultados[0]:
                    # Convertimos las claves a mayúsculas para evitar diferencias entre SGBDs
                    res_mayusculas = {k.upper(): v for k, v in resultados[0].items()}
                    parciales.append(res_mayusculas)
            except Exception as e:
                raise RuntimeError(f"Error al ejecutar agregacion en {tipo}: {e}")

        # 4. Combinamos los parciales usando las fórmulas matemáticas
        resultado_final = {}
        for agr in agregaciones:
            funcion = agr['funcion'].upper()
            factores = factores_por_agregador.get(funcion, {})
            formula = factores.get('formula', funcion)
            internos = factores.get('internos', [funcion])

            # Buscamos los datos en las "cajas seguras" usando el mapa de alias
            valores_por_interno = {}
            for interno in internos:
                alias_seguro = mapa_alias[agr['sql']][interno]
                
                valores = []
                for parcial in parciales:
                    if alias_seguro in parcial and parcial[alias_seguro] is not None:
                        valores.append(float(parcial[alias_seguro]))
                
                valores_por_interno[interno] = valores

            # Guardamos el resultado usando el string original para mantener las cabeceras de la interfaz
            resultado_final[agr['sql']] = self._aplicar_formula(formula, valores_por_interno)

        yield resultado_final

    def _factorizar_consulta(self, repr_intermedia, factores_por_agregador):
        """
        Sustituye los agregadores externos por alias internos controlados.
        Evita colisiones si hay columnas con nombres parecidos.
        """

        repr_modificada = copy.deepcopy(repr_intermedia)
        select_partes = []

        for col in repr_intermedia.get('columnas', []):
            select_partes.append(col)

        mapa_alias = {}
        contador = 0

        for agr in repr_intermedia['agregaciones']:
            funcion = agr['funcion'].upper()
            col = agr.get('columna', '*')
            factores = factores_por_agregador.get(funcion, {'internos': [funcion]})
            internos = factores.get('internos', [funcion])

            mapa_alias[agr['sql']] = {}

            for interno in internos:
                alias_seguro = f"DI_{interno}_{contador}".upper()
                mapa_alias[agr['sql']][interno] = alias_seguro
                contador += 1

                if interno == 'COUNT':
                    select_partes.append(f"COUNT(*) AS {alias_seguro}")
                else:
                    select_partes.append(f"{interno}({col}) AS {alias_seguro}")

        # Reconstruimos el AST de SQLGlot
        tabla = repr_intermedia['tablas'][0]
        condicion = repr_intermedia.get('condicion', '')
        
        sql_modificado = f"SELECT {', '.join(select_partes)} FROM {tabla}"
        if condicion:
            sql_modificado += f" {condicion}"

        repr_modificada['ast'] = sqlglot.parse_one(sql_modificado)
        repr_modificada['agregaciones'] = [] 
        repr_modificada['columnas'] = select_partes 

        return repr_modificada, mapa_alias

    def _aplicar_formula(self, formula, valores_por_interno):
        """
        Suma, busca máximos o mínimos según corresponda y aplica la fórmula del catálogo.
        """
        totales = {}
        for interno, valores in valores_por_interno.items():
            if not valores:
                totales[interno] = 0.0
                continue
            
            if interno == 'COUNT' or interno == 'SUM':
                totales[interno] = sum(valores)
            elif interno == 'MAX':
                totales[interno] = max(valores)
            elif interno == 'MIN':
                totales[interno] = min(valores)
            else:
                totales[interno] = sum(valores)

        formula_evaluable = formula.upper()
        
        if 'COUNT' in totales and totales['COUNT'] == 0:
            return 0.0

        for interno, total in totales.items():
            formula_evaluable = formula_evaluable.replace(interno, str(total))

        try:
            return eval(formula_evaluable)
        except ZeroDivisionError:
            return 0.0
        except Exception as e:
            raise RuntimeError(f"Error al evaluar formula '{formula}': {e}")