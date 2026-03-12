# Guía de Inicio Rápido - Ginnet Audio Analyzer API

## 🚀 Inicio Rápido en 3 Pasos

### 1️⃣ Instalación
Ejecute el script de instalación:
```powershell
.\install.ps1
```

Este script:
- Crea el entorno virtual Python
- Instala todas las dependencias
- Verifica que todo esté correctamente configurado

### 2️⃣ Iniciar el Servidor
Ejecute el script de inicio:
```powershell
.\start_server.ps1
```

El servidor estará disponible en:
- **API:** http://localhost:8000
- **Documentación:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### 3️⃣ Probar la API
Abra su navegador y vaya a:
```
http://localhost:8000/docs
```

Ahí encontrará una interfaz interactiva para probar todos los endpoints.

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrese de tener instalado:

1. **Python 3.8+**
   - Descargar desde: https://www.python.org/downloads/
   - Verificar: `python --version`

2. **FFmpeg** (para procesamiento de audio)
   - Windows: https://ffmpeg.org/download.html
   - Verificar: `ffmpeg -version`

3. **Modelos YOLO**
   - Los modelos ya están copiados en `models/normal/` y `models/grayscale/`
   - Si faltan, copiar `best.pt` del proyecto original

---

## 🔧 Instalación Manual

Si prefiere instalar manualmente:

```powershell
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno virtual
venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar servidor
python main.py
```

---

## 💻 Uso desde .NET

### Ejemplo Mínimo en C#

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.IO;
using System.Threading.Tasks;

class Program
{
    static async Task Main()
    {
        var client = new HttpClient { BaseAddress = new Uri("http://localhost:8000") };
        
        // Subir y generar espectrogramas
        using var form = new MultipartFormDataContent();
        var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync("audio.wav"));
        fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
        form.Add(fileContent, "files", "audio.wav");
        form.Add(new StringContent("3"), "segment_length");
        
        var response = await client.PostAsync("/api/spectrograms/generate", form);
        var result = await response.Content.ReadAsStringAsync();
        
        Console.WriteLine(result);
    }
}
```

### Cliente Completo

Consulte el archivo `DotNetClientExample.cs` para ver un cliente completo con todos los métodos.

---

## 📚 Documentación

- **README.md** - Documentación completa del proyecto
- **API_ENDPOINTS.md** - Lista detallada de todos los endpoints
- **DotNetClientExample.cs** - Cliente de ejemplo en C#
- **/docs** - Documentación interactiva Swagger (cuando el servidor está corriendo)

---

## 🔄 Flujo de Trabajo Típico

1. **Generar Espectrogramas**
   ```
   POST /api/spectrograms/generate
   ```
   Sube archivos de audio y genera espectrogramas

2. **Analizar con YOLO**
   ```
   POST /api/analysis/run-yolo
   ```
   Detecta cortes y anomalías en los espectrogramas

3. **Generar Reporte**
   ```
   POST /api/reports/generate-consolidated
   ```
   Crea un reporte Word con los resultados

4. **Descargar Resultado**
   ```
   GET /api/reports/download/{report_name}
   ```
   Descarga el reporte generado

---

## 🐛 Solución de Problemas

### Error: "Python no encontrado"
Instale Python 3.8+ desde https://www.python.org/downloads/
Asegúrese de marcar "Add Python to PATH" durante la instalación.

### Error: "FFmpeg no encontrado"
Descargue FFmpeg desde https://ffmpeg.org/download.html
Agregue la carpeta `bin` de FFmpeg a la variable PATH del sistema.

### Error: "Modelo YOLO no encontrado"
Copie los archivos `best.pt` a:
- `models/normal/best.pt`
- `models/grayscale/best.pt`

### Error: "Puerto 8000 en uso"
Edite `main.py` y cambie el puerto:
```python
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

### Error: "Module not found"
Asegúrese de activar el entorno virtual:
```powershell
venv\Scripts\Activate.ps1
```

---

## 🌐 Configuración para Producción

Para usar en producción:

1. **Desactivar modo reload**
   En `main.py`:
   ```python
   uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
   ```

2. **Configurar CORS**
   En `config.py`, especificar solo los dominios permitidos:
   ```python
   CORS_ORIGINS = [
       "https://tu-dominio.com",
       "https://www.tu-dominio.com"
   ]
   ```

3. **Usar HTTPS**
   Configure un reverse proxy (nginx, IIS) con certificado SSL

4. **Variables de entorno**
   Cree archivo `.env` para configuración sensible

---

## 📞 Soporte

Para problemas o preguntas:
1. Revise la documentación en `README.md`
2. Consulte `API_ENDPOINTS.md` para detalles de endpoints
3. Verifique los logs del servidor para mensajes de error
4. Contacte al equipo de desarrollo

---

## ✅ Checklist de Verificación

Antes de empezar, verifique que tiene:

- [ ] Python 3.8+ instalado
- [ ] FFmpeg instalado
- [ ] Modelos YOLO copiados
- [ ] Dependencias instaladas (`pip list` muestra fastapi, uvicorn, etc.)
- [ ] Servidor corriendo en http://localhost:8000
- [ ] Documentación accesible en http://localhost:8000/docs

---

¡Listo! Si todos los puntos están marcados, puede comenzar a usar la API.
