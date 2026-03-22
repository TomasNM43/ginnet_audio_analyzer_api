# Configuración de Base de Datos Oracle

## Requisitos

La API ahora incluye integración con base de datos Oracle SQL para actualizar automáticamente las rutas de los reportes generados en la tabla `PAQUETE_PROCESO`.

## Instalación de Dependencias

Las dependencias ya están incluidas en `requirements.txt`. Si aún no las has instalado:

```powershell
pip install oracledb python-dotenv
```

## Configuración

### 1. Crear archivo .env

Copia el archivo `.env.example` a `.env` en la raíz del proyecto:

```powershell
Copy-Item .env.example .env
```

### 2. Editar configuración de base de datos

Abre el archivo `.env` y configura los datos de conexión:

```env
DB_USER=system
DB_PASSWORD=tu_password_aqui
DB_DSN=localhost:1521/XEPDB1
```

**Nota sobre DSN:**
- Formato: `host:port/service_name`
- Ejemplos:
  - `localhost:1521/XE` (Oracle XE local)
  - `192.168.1.100:1521/ORCL` (Oracle remoto)
  - `dbserver.company.com:1521/PRODDB` (Producción)

### 3. Estructura de la tabla

La API espera que exista una tabla llamada `PAQUETE_PROCESO` con las siguientes columnas:

```sql
CREATE TABLE PAQUETE_PROCESO (
    ID_PAQUETE_PROCESO NUMBER PRIMARY KEY,
    NOMBRE_ARCHIVO_INFORME_1 VARCHAR2(500),  -- Ruta del reporte de análisis
    NOMBRE_ARCHIVO_INFORME_3 VARCHAR2(500),  -- Ruta del reporte de transcripción
    -- ... otras columnas
);
```

## Uso de los Endpoints

### Análisis de Audio

Cuando llamas al endpoint `/api/pipeline/analyze`, puedes pasar el parámetro opcional `paquete_id`:

```bash
POST /api/pipeline/analyze
Content-Type: multipart/form-data

file_path: "C:/path/to/audio.wav"
segment_length: 3
paquete_id: 123  # <- Opcional
```

Si se proporciona `paquete_id`, la API actualizará automáticamente la columna `NOMBRE_ARCHIVO_INFORME_1` con la ruta completa del reporte generado.

### Transcripción

Cuando llamas al endpoint `/api/pipeline/transcribe`, puedes pasar el parámetro opcional `paquete_id`:

```bash
POST /api/pipeline/transcribe
Content-Type: multipart/form-data

file_path: "C:/path/to/audio.wav"
paquete_id: 123  # <- Opcional
```

Si se proporciona `paquete_id`, la API actualizará automáticamente la columna `NOMBRE_ARCHIVO_INFORME_3` con la ruta completa del reporte de transcripción generado.

## Respuesta de la API

La respuesta incluirá información sobre la actualización de la base de datos:

```json
{
  "success": true,
  "message": "Pipeline de análisis completo ejecutado correctamente",
  "file_directory": "C:/path/to/audio",
  "analysis_directory": "C:/path/to/audio/Analisis_Audio",
  "pipeline_steps": {
    "1_spectrograms": { ... },
    "2_yolo_analysis": { ... },
    "3_report": {
      "report_name": "Reporte_Consolidado_20260321_153045.docx",
      "report_path": "C:/path/to/audio/Analisis_Audio/reports/Reporte_Consolidado_20260321_153045.docx",
      ...
    }
  },
  "database_update": {
    "success": true,
    "message": "Ruta actualizada en PAQUETE_PROCESO.NOMBRE_ARCHIVO_INFORME_1",
    "rows_affected": 1
  }
}
```

## Manejo de Errores

Si hay un error en la actualización de la base de datos, la API continuará funcionando normalmente pero devolverá información sobre el error:

```json
{
  ...
  "database_update": {
    "success": false,
    "message": "Error actualizando base de datos: [descripción del error]"
  }
}
```

## Modo Sin Base de Datos

Si no proporcionas el parámetro `paquete_id`, la API funcionará normalmente sin intentar actualizar la base de datos. Esto permite usar la API de forma independiente sin necesidad de una base de datos.

## Troubleshooting

### Error: No module named 'oracledb'
```powershell
pip install oracledb
```

### Error: No se pudo conectar a la base de datos
- Verifica que Oracle Database esté ejecutándose
- Verifica las credenciales en el archivo `.env`
- Verifica el formato del DSN (host:port/service_name)
- Prueba la conexión con SQL Developer o SQLPlus
- Verifica los permisos del usuario

### Error: Table 'PAQUETE_PROCESO' doesn't exist
- Crea la tabla usando el script SQL proporcionado arriba
- Verifica el nombre del esquema/usuario
- Asegúrate de tener permisos en la tabla

### Error: ORA-12154: TNS:could not resolve the connect identifier
- Verifica el formato del DSN
- Asegúrate de usar `host:port/service_name` y no un TNS name
- Ejemplo correcto: `localhost:1521/XE`

### Error: ORA-12505: TNS:listener does not currently know of SID
- Verifica que el service_name sea correcto
- Usa `service_name` en lugar de `SID`
- Consulta con tu DBA el service_name correcto

### Verificar conexión Oracle manualmente

Puedes probar la conexión usando Python:

```python
import oracledb

try:
    connection = oracledb.connect(
        user="system",
        password="tu_password",
        dsn="localhost:1521/XEPDB1"
    )
    print("Conexión exitosa!")
    connection.close()
except Exception as e:
    print(f"Error: {e}")
```
