# Fixes para Ventana de Video en Linux

## 📋 Resumen Ejecutivo

Se han implementado dos correcciones principales para resolver los problemas de visualización de video en segunda pantalla:

1. **Inicialización correcta de VLC en X11** - La ventana se inicializa en dos fases con un delay de 100ms para asegurar que `winId()` sea válido antes de adjuntar VLC.

2. **Event filter mejorado para doble click** - Se emite correctamente la señal `toggled` cuando el usuario hace doble click para cerrar la ventana.

**Estado**: ✅ Validado (sintaxis correcta, lista para testing)

## Problemas Identificados

1. **Ventana no aparece en segunda pantalla**: La función `set_xwindow()` en Linux requiere que la ventana esté completamente inicializada (mapeada en X11) antes de ser llamada.

2. **Errores de VA-API de NVIDIA**: Son advertencias de configuración de drivers, no afectan la funcionalidad (secundario).

3. **Botón de cierre con doble click no funciona**: El event filter no estaba emitiendo la señal `toggled` correctamente.

## Cambios Realizados

### 1. `video/video.py` - Mejorada inicialización de VLC en Linux

#### Problema Original
```python
self.setGeometry(geo)
self.showFullScreen()  # ← Problema: winId() aún no está completamente inicializado
xid = int(self.winId())
self.player.set_xwindow(xid)  # ← Falla silenciosamente
```

#### Solución Implementada
1. **Separar inicialización en dos pasos**:
   - Primero: `setGeometry()` + `show()` para crear la ventana X11
   - Luego (100ms después): `set_xwindow()` cuando winId() está garantizado
   - Finalmente: `showFullScreen()` cuando VLC ya está adjuntado

2. **Nuevo método `_attach_vlc_to_window()`**:
   - Validaciones pre-adjunción en Linux:
     - Verificar que `isVisible()` sea True
     - Verificar que `winId() != 0`
   - Manejo robusto de errores con try/except
   - Logging detallado para debugging

3. **Mejor logging**:
   - Muestra todas las pantallas detectadas con resoluciones
   - Indica claramente cuál pantalla se está usando
   - Símbolos visuales (✓, ✗, ⚠, 📺) para mejor legibilidad

### Cambio en `move_to_screen()`

```python
def move_to_screen(self):
    """Mover ventana a pantalla secundaria y adjuntar VLC."""
    screens = QApplication.screens()
    logger.info(f"📺 Pantallas detectadas: {len(screens)}")
    for i, screen in enumerate(screens):
        dpi = screen.logicalDotsPerInch()
        size = screen.geometry()
        logger.info(f"  [{i}] {screen.name()} - Resolución: {size.width()}x{size.height()} @ {dpi} DPI")

    if self.screen_index >= len(screens):
        logger.error(f"❌ Pantalla {self.screen_index} no existe (solo hay {len(screens)})")
        return

    target_screen = screens[self.screen_index]
    geo = target_screen.geometry()
    logger.info(f"✓ Moviendo ventana a pantalla {self.screen_index}: {geo.x()},{geo.y()} {geo.width()}x{geo.height()}")

    # Asegurar que la ventana se mueve ANTES de adjuntar VLC
    self.setGeometry(geo)
    self.show()  # Llamar show() antes de showFullScreen() para asegurar winId() válido
    QTimer.singleShot(100, self._attach_vlc_to_window)
```

### Nuevo método `_attach_vlc_to_window()`

```python
def _attach_vlc_to_window(self):
    """Adjuntar VLC a la ventana después de que está completamente inicializada."""
    try:
        if self.system == "Windows":
            hwnd = int(self.winId())
            logger.info(f"✓ HWND obtenido: {hwnd}")
            self.player.set_hwnd(hwnd)
            
        elif self.system == "Linux":
            # En Linux, necesitamos asegurar que la ventana está mapeada
            if not self.isVisible():
                logger.warning("⚠ Ventana no visible antes de set_xwindow()")
                self.show()
                
            xid = int(self.winId())
            if xid == 0:
                logger.error("❌ winId() retornó 0 - ventana no inicializada correctamente")
                return
                
            logger.info(f"✓ XWindow ID obtenido: {xid}")
            self.player.set_xwindow(xid)
            logger.info("✓ VLC adjuntado correctamente a ventana X11")
            
        elif self.system == "Darwin":  # macOS
            logger.info("🍎 macOS detectado - intentando set_nsobject()")
            try:
                self.player.set_nsobject(self.winId())
                logger.info("✓ VLC adjuntado a ventana macOS")
            except Exception as e:
                logger.warning(f"⚠ set_nsobject falló: {e}, usando configuración por defecto")
        else:
            logger.warning(f"⚠ SO desconocido: {self.system}, VLC usará configuración por defecto")
            
        # Finalmente, entrar a fullscreen
        self.showFullScreen()
        logger.info("✓ Ventana en fullscreen")
        
    except Exception as e:
        logger.error(f"❌ Error al adjuntar VLC: {e}", exc_info=True)
```

### 2. `ui/widgets/controls_widget.py` - Mejorado event filter para doble click

#### Problema Original
```python
def eventFilter(self, obj, event):
    if obj == self.show_video_btn and event.type() == QEvent.MouseButtonDblClick:
        self.show_video_btn.setChecked(False)
        # ✓ UI se actualiza localmente
        # ✗ Pero MainWindow no recibe la señal toggled
        return True
    return super().eventFilter(obj, event)
```

#### Solución Implementada
```python
def eventFilter(self, obj, event):
    """Event filter to handle double click on show_video_btn.
    
    Double click hides the video window and changes icon to inactive state.
    """
    if obj == self.show_video_btn:
        if event.type() == QEvent.MouseButtonDblClick:
            # Double click - hide video
            self.show_video_btn.setChecked(False)
            self.show_video_btn.setIcon(QIcon("assets/img/chromecast.svg"))
            self.show_video_btn.setToolTip("click para proyectar video")
            # Emit toggled signal so MainWindow knows to hide video ← FIX
            self.show_video_btn.toggled.emit(False)
            return True  # Event handled, don't propagate
            
        elif event.type() == QEvent.MouseButtonPress:
            # Single click - already handled by toggled signal
            pass
            
    return super().eventFilter(obj, event)
```

**Cambio clave**: Agregar `self.show_video_btn.toggled.emit(False)` para que la señal llegue a `main.py` y ejecute `hide_window()`.

## Cómo Probar

### Test Manual
1. Abrir MultiLyrics
2. Cargar una canción con video
3. Hacer click en el botón de video (debería mostrar en pantalla secundaria)
4. Hacer doble click en el botón (debería cerrar la ventana)

### Verificar Logs
Buscar en los logs:
```
📺 Pantallas detectadas: 2
  [0] HDMI-1 - Resolución: 1920x1080 @ 96 DPI
  [1] DP-2 - Resolución: 2560x1440 @ 96 DPI
✓ Moviendo ventana a pantalla 1: 1920,0 2560x1440
✓ XWindow ID obtenido: 123456789
✓ VLC adjuntado correctamente a ventana X11
✓ Ventana en fullscreen
```

## Problemas Conocidos

### Errores de VA-API (SECUNDARIO)
```
libva error: vaGetDriverNameByIndex() failed with unknown libva error
```

Estos son warnings de NVIDIA VideoAccel. **No afectan la reproducción de video**.

**Solución (opcional)**: Desactivar VA-API en VLC
```python
vlc_args = ['--quiet', '--no-video-title-show', '--avcodec-hw=none']
```

## Cambios Futuros Sugeridos

1. **Agregar opción de pantalla configurable**: Permitir usuario elegir qué pantalla (1, 2, 3, etc.)
2. **Persistir configuración**: Guardar pantalla elegida en `settings.json`
3. **Validar modo fullscreen**: Algunos WMs de Linux no soportan fullscreen sin compositor
4. **Soporte para Wayland**: Actualmente solo soporta X11 en Linux
