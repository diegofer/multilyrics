# 🧪 Guía de Testing - Ventana de Video Linux

## Pre-requisitos
- Sistema Linux (probado en Ubuntu 22.04+, Fedora 37+, Debian 12+)
- Dos pantallas conectadas (o pantalla virtual para testing)
- MultiLyrics compilado y con dependencias instaladas

## Plan de Testing

### Test 1: Detección de Pantallas ✓
**Objetivo**: Verificar que el sistema detecta correctamente todas las pantallas

**Pasos**:
1. Abrir MultiLyrics
2. En los logs, buscar línea que dice `📺 Pantallas detectadas`
3. Verificar que aparecen todas tus pantallas

**Logs esperados**:
```
INFO [video.video] 📺 Pantallas detectadas: 2
INFO [video.video]   [0] HDMI-1 - Resolución: 1920x1080 @ 96 DPI
INFO [video.video]   [1] DP-2 - Resolución: 2560x1440 @ 96 DPI
```

**¿Qué puede salir mal?**
- Si solo aparece 1 pantalla pero tienes 2 conectadas, verificar que están ambas activadas en settings de pantalla del SO
- Si ves `❌ Pantalla 1 no existe`, significa que solo hay 1 pantalla

---

### Test 2: Mostrar Ventana de Video ✓
**Objetivo**: Verificar que la ventana aparece correctamente en pantalla secundaria

**Pasos**:
1. Cargar una canción que tenga video
2. Hacer click en el botón de **video** (chromecast icon)
3. La ventana debería aparecer en la pantalla secundaria en fullscreen

**Logs esperados**:
```
INFO [video.video] Inicializando ventana de video por primera vez
INFO [video.video] ✓ Moviendo ventana a pantalla 1: 1920,0 2560x1440
INFO [video.video] ✓ XWindow ID obtenido: 123456789
INFO [video.video] ✓ VLC adjuntado correctamente a ventana X11
INFO [video.video] ✓ Ventana en fullscreen
```

**¿Qué puede salir mal?**
- Si aparece `❌ winId() retornó 0`, la ventana no se inicializó correctamente
  - **Solución**: Esperar 5 segundos y volver a intentar
- Si aparece `⚠ Ventana no visible antes de set_xwindow()`, el WM está interfiriendo
  - **Solución**: Verificar que el sistema usa X11 (no Wayland)

---

### Test 3: Reproducción de Video ✓
**Objetivo**: Verificar que el video se reproduce en la ventana

**Pasos**:
1. Ventana de video visible
2. Presionar play en MultiLyrics
3. El video debe reproducirse en la pantalla secundaria
4. El audio debe estar silenciado en esa pantalla (sale por altavoces principales)

**¿Qué puede salir mal?**
- Video aparece pero no se ve nada: 
  - Verificar que el archivo de video existe en `library/multis/{song}/video.mp4`
  - Verificar que VLC puede reproducir ese formato (prueba con `vlc --version`)
  
- Video aparece pero está "congelado":
  - Hacer click en MainWindow para restaurar foco
  - Presionar espaciador para reproducir

---

### Test 4: Cerrar Ventana con Doble Click ✓
**Objetivo**: Verificar que el doble click en el botón de video cierra la ventana

**Pasos**:
1. Ventana de video visible
2. En MainWindow, hacer **doble click** en el botón de video
3. La ventana debe ocultarse
4. El botón debe cambiar de ícono a versión inactiva (gris)

**Logs esperados**:
```
INFO [main] Ocultando ventana de video
```

**¿Qué puede salir mal?**
- Doble click no funciona: 
  - Verificar que el botón tiene `installEventFilter(self)` en controls_widget.py
  - Prueba con single click (debe activarse)
  - Luego doble click en MainWindow para cerrar

---

### Test 5: Show/Hide Múltiples Veces ✓
**Objetivo**: Verificar que el sistema es robusto con múltiples show/hide

**Pasos**:
1. Click en video (mostrar)
2. Esperar 2 segundos
3. Doble click en video (ocultar)
4. Repetir 5 veces

**Logs esperados** (después de la primera vez):
```
INFO [video.video] Mostrando ventana de video
INFO [video.video] Ocultando ventana de video
```

**Observación**: Después de la primera inicialización, show/hide debería ser muy rápido

---

### Test 6: Cambiar de Canción ✓
**Objetivo**: Verificar que cambiar de canción con video visible no causa crashes

**Pasos**:
1. Mostrar video de canción A
2. Cambiar a canción B (que tenga otro video)
3. El video debe cambiar a canción B
4. Reproducción debe funcionar

**¿Qué puede salir mal?**
- Crash cuando se carga nuevo video:
  - Verificar que `set_media()` está siendo llamado correctamente
  - Revisar que el nuevo video existe

---

## Debugging Avanzado

### Habilitar logs muy detallados
En `core/constants.py`:
```python
LOG_LEVEL = "DEBUG"  # Cambiar a DEBUG para ver más detalles
```

### Verificar pantallas desde terminal
```bash
# En X11:
xrandr

# En Wayland:
wlr-randr
```

### Verificar que VLC funciona directamente
```bash
# Reemplaza con tu archivo de video
vlc /home/user/archivo.mp4
```

### Logs de VLC
Si necesitas ver logs internos de VLC:
```python
# En video/video.py, cambiar:
vlc_args = ['--quiet', '--log-verbose=2']
# A:
vlc_args = ['--log-verbose=3']
```

---

## Reporte de Bugs

Si algo no funciona, incluir en el reporte:

1. **SO y versión**
   ```bash
   uname -a
   ```

2. **Pantallas detectadas**
   ```bash
   xrandr  # o wlr-randr si usas Wayland
   ```

3. **Logs completos** (desde inicio de app hasta momento del error)
   ```bash
   # Ejecutar con logs a archivo:
   python main.py 2>&1 | tee debug.log
   ```

4. **Versión de PySide6 y VLC**
   ```bash
   python3 -c "from PySide6 import __version__; print(__version__)"
   python3 -c "import vlc; print(vlc.__version__)"
   ```

5. **Detalles del problema**:
   - ¿Aparece la ventana pero está negra?
   - ¿No aparece la ventana en la segunda pantalla?
   - ¿Error específico en logs?

---

## Problemas Conocidos

### ⚠️ VA-API Errors
```
libva error: vaGetDriverNameByIndex() failed with unknown libva error
```
**Causa**: Configuración de NVIDIA VideoAccel  
**Impacto**: Ninguno (solo warning)  
**Solución**: Opcional - desactivar VA-API en VLC

### ⚠️ Wayland No Soportado
MultiLyrics actualmente solo soporta X11 en Linux.

**Para verificar tu display server**:
```bash
echo $XDG_SESSION_TYPE  # Debería mostrar "x11"
```

Si muestra "wayland", necesitarás usar X11 o esperar a una actualización de PySide6/VLC con soporte nativo de Wayland.

---

## Testing Exitoso ✓

Si pasaste todos los tests, entonces:
- ✅ La ventana aparece en la segunda pantalla
- ✅ El video se reproduce correctamente
- ✅ El doble click cierra la ventana
- ✅ El sistema es robusto con múltiples show/hide

¡Puedes reportar que el fix es exitoso!
