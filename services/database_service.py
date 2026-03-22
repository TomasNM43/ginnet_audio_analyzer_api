"""
Servicio para operaciones de base de datos
"""
import oracledb
from typing import Optional, Dict, Any
from config import DB_CONFIG


class DatabaseService:
    """Servicio para manejar operaciones de base de datos"""
    
    @staticmethod
    def get_connection():
        """
        Obtiene una conexión a la base de datos Oracle
        
        Returns:
            Conexión oracledb
        """
        try:
            connection = oracledb.connect(
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                dsn=DB_CONFIG['dsn']  # format: "host:port/service_name"
            )
            return connection
        except Exception as e:
            print(f"Error conectando a la base de datos Oracle: {e}")
            return None
    
    @staticmethod
    def update_report_path(table: str, column: str, report_path: str, 
                          id_column: str, id_value: Any) -> Dict[str, Any]:
        """
        Actualiza la ruta del reporte en una tabla específica
        
        Args:
            table: Nombre de la tabla
            column: Nombre de la columna a actualizar
            report_path: Ruta completa del reporte
            id_column: Nombre de la columna ID para el WHERE
            id_value: Valor del ID para identificar el registro
            
        Returns:
            Diccionario con el resultado de la operación
        """
        connection = None
        try:
            connection = DatabaseService.get_connection()
            if connection is None:
                return {
                    "success": False,
                    "message": "No se pudo conectar a la base de datos"
                }
            
            with connection.cursor() as cursor:
                # Oracle SQL usa :1, :2 para parámetros
                sql = f"UPDATE {table} SET {column} = :1 WHERE {id_column} = :2"
                cursor.execute(sql, [report_path, id_value])
                connection.commit()
                
                return {
                    "success": True,
                    "message": f"Ruta actualizada en {table}.{column}",
                    "rows_affected": cursor.rowcount
                }
                
        except Exception as e:
            if connection:
                connection.rollback()
            return {
                "success": False,
                "message": f"Error actualizando base de datos: {str(e)}"
            }
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def update_paquete_proceso_informe_1(report_path: str, paquete_id: int) -> Dict[str, Any]:
        """
        Actualiza NOMBRE_ARCHIVO_INFORME_1 en la tabla PAQUETE_PROCESO
        
        Args:
            report_path: Ruta completa del reporte de análisis
            paquete_id: ID del paquete
            
        Returns:
            Diccionario con el resultado de la operación
        """
        return DatabaseService.update_report_path(
            table='GINNET_AUDIO.PAQUETE_PROCESO',
            column='NOMBRE_ARCHIVO_INFORME_1',
            report_path=report_path,
            id_column='ID_PAQUETE_PROCESO',
            id_value=paquete_id
        )
    
    @staticmethod
    def update_paquete_proceso_informe_3(report_path: str, paquete_id: int) -> Dict[str, Any]:
        """
        Actualiza NOMBRE_ARCHIVO_INFORME_3 en la tabla PAQUETE_PROCESO
        
        Args:
            report_path: Ruta completa del reporte de transcripción
            paquete_id: ID del paquete
            
        Returns:
            Diccionario con el resultado de la operación
        """
        return DatabaseService.update_report_path(
            table='GINNET_AUDIO.PAQUETE_PROCESO',
            column='NOMBRE_ARCHIVO_INFORME_3',
            report_path=report_path,
            id_column='ID_PAQUETE_PROCESO',
            id_value=paquete_id
        )
