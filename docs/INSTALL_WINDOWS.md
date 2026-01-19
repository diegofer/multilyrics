# 🪟 Guía de Instalación para Windows

**Guía paso a paso para usuarios de Windows 10/11**

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener:

- ✅ **Windows 10 o Windows 11** (64 bits)
- ✅ **4 GB de RAM mínimo** (8 GB recomendado)
- ✅ **500 MB de espacio libre** en disco
- ✅ **Conexión a internet** (para descargar dependencias)

---

## 🚀 Instalación Paso a Paso

### Paso 1: Instalar Python

1. **Descarga Python 3.11 o superior**:
   - Ve a [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - Haz clic en "Download Python 3.11.x" (o la versión más reciente)

2. **Ejecuta el instalador**:
   - ⚠️ **MUY IMPORTANTE**: Marca la casilla **"Add Python to PATH"** en la primera pantalla
   - Haz clic en "Install Now"
   - Espera a que termine la instalación
   - Haz clic en "Close" cuando finalice

3. **Verifica la instalación**:
   - Abre **PowerShell** (presiona `Win + X` y selecciona "Windows PowerShell")
   - Escribe: `python --version`
   - Deberías ver algo como: `Python 3.11.x`

---

### Paso 2: Instalar FFmpeg

FFmpeg es necesario para procesar audio y video.

1. **Descarga FFmpeg**:
   - Ve a [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
   - Descarga: **ffmpeg-release-essentials.zip**

2. **Extrae el archivo**:
   - Haz clic derecho en el archivo ZIP → "Extraer todo"
   - Extrae a una carpeta simple como: `C:\ffmpeg`

3. **Agrega FFmpeg al PATH**:
   - Presiona `Win + S` y busca "variables de entorno"
   - Haz clic en "Editar las variables de entorno del sistema"
   - Haz clic en "Variables de entorno..."
   - En "Variables del sistema", busca "Path" y haz clic en "Editar..."
   - Haz clic en "Nuevo" y agrega: `C:\ffmpeg\bin` (o donde lo hayas extraído)
   - Haz clic en "Aceptar" en todas las ventanas

4. **Verifica la instalación**:
   - **Cierra y abre PowerShell nuevamente** (importante para recargar el PATH)
   - Escribe: `ffmpeg -version`
   - Deberías ver información de la versión de FFmpeg

---

### Paso 3: Descargar Multi Lyrics

1. **Descarga el código**:
   - Si tienes Git instalado:
     ```powershell
     git clone https://github.com/tu-usuario/multilyrics.git
     cd multilyrics
     ```
   
   - Si **NO** tienes Git:
     - Ve a la página del proyecto en GitHub
     - Haz clic en el botón verde "Code" → "Download ZIP"
     - Extrae el ZIP a una carpeta como `C:\Users\TuUsuario\multilyrics`
     - Abre PowerShell y navega a esa carpeta:
       ```powershell
       cd C:\Users\TuUsuario\multilyrics
       ```

---

### Paso 4: Crear Entorno Virtual

Un entorno virtual mantiene las dependencias organizadas y separadas.

1. **Crea el entorno virtual**:
   ```powershell
   python -m venv env
   ```
   (Esto tomará unos segundos)

2. **Activa el entorno virtual**:
   ```powershell
   .\env\Scripts\Activate.ps1
   ```

   **⚠️ Si aparece un error de permisos**:
   - Ejecuta: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
   - Di "Sí" y vuelve a intentar el comando anterior

   Cuando esté activo, verás `(env)` al inicio de tu línea de comandos:
   ```
   (env) PS C:\Users\TuUsuario\multilyrics>
   ```

---

### Paso 5: Instalar Dependencias

Con el entorno virtual activo:

```powershell
pip install -r requirements.txt
```

Esto descargará e instalará todas las bibliotecas necesarias (puede tomar 5-10 minutos).

---

### Paso 6: ¡Ejecutar Multi Lyrics!

```powershell
python main.py
```

La aplicación debería abrirse. 🎉

---

## 🎛️ Configuración de Audio

Multi Lyrics **auto-detecta tu hardware** y configura el audio automáticamente. No necesitas hacer nada adicional.

Cuando inicies, verás en los logs:
```
INFO [core.audio_profiles] 🖥️  Detected OS: windows
INFO [core.audio_profiles] 🎯 Auto-selected profile: Balanced Performance
```

**Perfiles disponibles**:
- **Legacy Hardware** (2008-2012): PCs antiguas con 4 GB RAM
- **Balanced Performance** (2013-2018): ⭐ Mayoría de usuarios
- **Modern Hardware** (2019+): PCs modernas con 16+ GB RAM

Para más detalles, consulta: [`SETUP_AUDIO_WINDOWS.md`](SETUP_AUDIO_WINDOWS.md)

---

## 🔄 Uso Diario

### Iniciar la aplicación

Cada vez que quieras usar Multi Lyrics:

1. Abre PowerShell
2. Navega a la carpeta del proyecto:
   ```powershell
   cd C:\Users\TuUsuario\multilyrics
   ```
3. Activa el entorno virtual:
   ```powershell
   .\env\Scripts\Activate.ps1
   ```
4. Ejecuta la aplicación:
   ```powershell
   python main.py
   ```

### Crear un acceso directo (Opcional)

Para no escribir comandos cada vez, crea un archivo `MultiLyrics.bat` con este contenido:

```batch
@echo off
cd C:\Users\TuUsuario\multilyrics
call env\Scripts\activate.bat
python main.py
```

Luego solo haz doble clic en el archivo `.bat` para iniciar.

---

## ❓ Problemas Comunes

### "Python no se reconoce como comando"

**Solución**: No agregaste Python al PATH durante la instalación.
- Desinstala Python
- Reinstala marcando la casilla "Add Python to PATH"

### "ffmpeg no se reconoce como comando"

**Solución**: No agregaste FFmpeg al PATH correctamente.
- Verifica que la carpeta `bin` de FFmpeg esté en el PATH
- Cierra y abre PowerShell nuevamente después de modificar el PATH

### "No se puede ejecutar scripts en este sistema"

**Solución**: Política de ejecución de PowerShell muy restrictiva.
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Audio con glitches o cortes"

**Solución**: Tu PC puede necesitar un perfil de audio diferente.
- Prueba forzando el perfil "legacy":
  ```powershell
  $env:MULTILYRICS_AUDIO_PROFILE="legacy"
  python main.py
  ```

### "Ventana negra o error al iniciar"

**Solución**: Verifica que todas las dependencias se instalaron correctamente.
```powershell
pip install -r requirements.txt --force-reinstall
```

---

## 🆘 ¿Necesitas Ayuda?

Si encuentras problemas:

1. **Revisa los logs**: La aplicación muestra mensajes en PowerShell que pueden ayudar
2. **Consulta la documentación avanzada**: [`docs/`](../docs/)
3. **Reporta el problema**: Abre un issue en GitHub con:
   - Tu versión de Windows (`Win + Pause` para verla)
   - El mensaje de error completo
   - Los pasos que seguiste

---

## 📚 Documentación Adicional

- **[SETUP_AUDIO_WINDOWS.md](SETUP_AUDIO_WINDOWS.md)** - Configuración avanzada de audio
- **[README.md](../README.md)** - Características y documentación general
- **[development.md](development.md)** - Para desarrolladores

---

**¡Disfruta usando Multi Lyrics! 🎵**
