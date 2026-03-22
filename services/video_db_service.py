import os
import oracledb


def _get_connection():
    user = os.environ.get('ORACLE_USER')
    password = os.environ.get('ORACLE_PASSWORD')
    dsn = os.environ.get('ORACLE_DSN')  # Formato: "host:puerto/servicio"
    if not all([user, password, dsn]):
        raise RuntimeError(
            "Faltan variables de entorno: ORACLE_USER, ORACLE_PASSWORD y ORACLE_DSN son requeridas."
        )
    return oracledb.connect(user=user, password=password, dsn=dsn)


def actualizar_proceso_video(
    id_paquete_proceso_video: str,
    estado: str,
    tipo_analisis: str = None,
    nombre_informe_1: str = None,
    nombre_informe_2: str = None,
    nombre_informe_3: str = None,
    brillo: int = None
) -> int:
    """
    Actualiza el estado y datos de un registro en PAQUETE_PROCESO_VIDEO.
    Retorna el número de filas afectadas.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        sets = ["ESTADO = :estado", "FECHA_PROCESO = SYSDATE"]
        params = {"estado": estado, "id": id_paquete_proceso_video}

        if tipo_analisis is not None:
            sets.append("TIPO_ANALISIS = :tipo_analisis")
            params["tipo_analisis"] = tipo_analisis
        if nombre_informe_1 is not None:
            sets.append("NOMBRE_ARCHIVO_INFORME_1 = :inf1")
            params["inf1"] = nombre_informe_1
        if nombre_informe_2 is not None:
            sets.append("NOMBRE_ARCHIVO_INFORME_2 = :inf2")
            params["inf2"] = nombre_informe_2
        if nombre_informe_3 is not None:
            sets.append("NOMBRE_ARCHIVO_INFORME_3 = :inf3")
            params["inf3"] = nombre_informe_3
        if brillo is not None:
            sets.append("BRILLO = :brillo")
            params["brillo"] = brillo

        sql = (
            f"UPDATE GINNET_AUDIO.PAQUETE_PROCESO_VIDEO "
            f"SET {', '.join(sets)} "
            f"WHERE ID_PAQUETE_PROCESO_VIDEO = :id"
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
