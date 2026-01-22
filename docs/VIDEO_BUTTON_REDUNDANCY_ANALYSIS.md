# 🔍 Análisis de Redundancia: video_enable_toggle_btn vs show_video_btn

**Fecha**: 2026-01-22  
**Estado**: Análisis completo - Esperando decisión del usuario

---

## 📊 Situación Actual

### Botones Existentes

#### 1. `video_enable_toggle_btn` (frame_7)
- **Ubicación**: `ui/widgets/controls_widget.py` líneas 124-131
- **Función**: Habilitar/deshabilitar video manualmente
- **Signal**: `video_enabled_changed(bool)`
- **Handler**: `_on_video_enabled_changed()` en `main.py` línea 408
- **Acción**: Llama a `video_player.enable_video(enabled)`
- **Icono**: `play.svg` (genérico)
- **Estado default**: `checked=True` (ON por defecto)
- **Tooltip**: "📹 Video habilitado (click para deshabilitar)"

**Implementación actual**:
```python
def _on_video_enabled_changed(self, enabled: bool):
    """Handle video enable/disable toggle from UI."""
    logger.info(f"Usuario {'habilitó' if enabled else 'deshabilitó'} video manualmente")
    self.video_player.enable_video(enabled)
    
    # Si se deshabilitó video durante reproducción, detenerlo
    if not enabled and self.video_player.player.is_playing():
        self.video_player.stop()
        logger.debug("🔄 Video stopped (user disabled)")
```

**Método llamado** (`video/video.py` líneas 190-201):
```python
def enable_video(self, enable: bool = True):
    """Habilitar o deshabilitar video manualmente (backward compatibility)."""
    if enable:
        # Re-enable: restore to previous mode or use recommended
        if self._video_mode == "none":
            config = ConfigManager.get_instance()
            restored_mode = config.get("video.mode", "full")
            self.set_video_mode(restored_mode)
    else:
        # Disable: switch to 'none' mode
        self.set_video_mode("none")
```

---

#### 2. `show_video_btn` (frame_8)
- **Ubicación**: `ui/widgets/controls_widget.py` líneas 107-115
- **Función**: Mostrar/ocultar ventana de video (proyección)
- **Signal**: `toggled(bool)`
- **Handler**: `_on_show_video_toggled()` en `main.py` línea 394
- **Acción**: Llama a `video_player.show_window()` o `video_player.hide_window()`
- **Icono**: `chromecast.svg` / `chromecast-active.svg`
- **Estado default**: `checked=False` (OFF por defecto)
- **Tooltip**: "click para proyectar video" / "doble click para cerrar video"

**Implementación actual**:
```python
def _on_show_video_toggled(self, checked: bool):
    """Show or hide video window based on button state."""
    if checked:
        logger.debug("Mostrando ventana de video")
        self.video_player.show_window()
    else:
        logger.debug("Ocultando ventana de video")
        self.video_player.hide_window()
```

---

## 🎯 Sistema de Modos de Video (ConfigManager)

### Modos Disponibles
Definidos en `core/config_manager.py`:

```python
"video": {
    "mode": None,  # "full" | "loop" | "static" | "none"
    "loop_video_path": "assets/loops/default.mp4",
    "recommended_mode": None  # Auto-detectado en startup
}
```

### Detección Automática de Modo Recomendado

**Método**: `ConfigManager.detect_recommended_video_mode()` (líneas 135-163)

**Criterios**:
- **Hardware Legacy** (CPU < 2013 o RAM < 6GB) → `"static"` (evita decodificación de video)
- **Hardware Moderno** (CPU ≥ 2013, RAM ≥ 6GB) → `"full"` (video completo con sync)

**Inicialización** en `main.py` (líneas 88-104):
```python
# Detect recommended mode if not set
if config.get("video.recommended_mode") is None:
    recommended_mode = ConfigManager.detect_recommended_video_mode()
    config.set("video.recommended_mode", recommended_mode)

# Use recommended mode if user hasn't chosen one
video_mode = config.get("video.mode")
if video_mode is None:
    video_mode = config.get("video.recommended_mode", "full")
    config.set("video.mode", video_mode)
    logger.info(f"🎬 Active video mode initialized: {video_mode}")
```

### Settings Dialog (Control Global)

**Ubicación**: `ui/widgets/settings_dialog.py` líneas 95-147

**Características**:
- Combo box con 4 modos: Full Video, Loop Background, Static Frame, None (Audio Only)
- Muestra modo recomendado basado en hardware
- Warning visual si modo seleccionado ≠ recomendado
- Persiste cambios en `config/settings.json`

---

## 🔁 Flujo de Video Mode en VideoLyrics

### Inicialización
`video/video.py` línea 40:
```python
self._video_mode = config.get("video.mode", "full")  # Carga desde ConfigManager
```

### Sincronización al Cargar Canción
`video/video.py` líneas 206-210:
```python
def set_media(self, video_path):
    """Cargar un archivo de video respetando el modo configurado."""
    # STEP 6: Always sync mode from config before loading media
    current_mode = ConfigManager.get_instance().get("video.mode", "full")
    if current_mode and current_mode != self._video_mode:
        logger.info(f"📹 Updating video mode from settings: {self._video_mode} → {current_mode}")
        self._video_mode = current_mode
```

### Comportamiento por Modo
- **`"none"`**: No carga video, skip completo (línea 213)
- **`"loop"`**: Usa `assets/loops/default.mp4` (ignora video del multi) (línea 218)
- **`"static"`**: Usa video del multi, fallback a loop si no existe (línea 225)
- **`"full"`**: Usa video del multi, fallback a loop si no existe (línea 234)

---

## 🧩 Redundancia Detectada

### Overlap Funcional

| Feature | video_enable_toggle_btn | show_video_btn | ConfigManager video.mode |
|---------|------------------------|----------------|--------------------------|
| **Habilitar/Deshabilitar Video** | ✅ SÍ | ❌ NO | ✅ SÍ (mode="none") |
| **Mostrar/Ocultar Ventana** | ❌ NO | ✅ SÍ | ❌ NO |
| **Control Global Persistente** | ❌ NO (solo runtime) | ❌ NO (solo runtime) | ✅ SÍ (config/settings.json) |
| **Modos Avanzados** (loop/static) | ❌ NO | ❌ NO | ✅ SÍ |

### Problema Principal

**`video_enable_toggle_btn` duplica funcionalidad de ConfigManager**:
- ConfigManager ya gestiona `video.mode = "none"` para deshabilitar video
- Settings Dialog ya tiene UI para cambiar modo (incluyendo "None")
- `enable_video()` es un wrapper de `set_video_mode()` (backward compatibility)

**Flujo actual redundante**:
```
Usuario → video_enable_toggle_btn → _on_video_enabled_changed()
       → video_player.enable_video(False)
       → set_video_mode("none")
       → (NO persiste en ConfigManager)
```

**Flujo ideal**:
```
Usuario → Settings Dialog → video_mode_combo
       → ConfigManager.set("video.mode", "none")
       → (Persiste en config/settings.json)
       → (Se aplica al cargar siguiente canción)
```

---

## 💡 Propuestas de Solución

### Opción 1: Eliminar `video_enable_toggle_btn` completamente ✅ RECOMENDADO

**Razón**: Funcionalidad completamente cubierta por Settings Dialog

**Ventajas**:
- ✅ Elimina redundancia 100%
- ✅ UI más limpia (un botón menos)
- ✅ Single Source of Truth (ConfigManager)
- ✅ Cambios persistentes entre sesiones
- ✅ Acceso a todos los modos (full/loop/static/none)

**Desventajas**:
- ⚠️ Usuario debe abrir Settings para cambiar modo (1 click extra)
- ⚠️ No hay quick toggle en toolbar (pero Settings es igualmente rápido)

**Cambios requeridos**:
1. **Eliminar** `video_enable_toggle_btn` de `controls_widget.py`
2. **Eliminar** signal `video_enabled_changed` de `controls_widget.py`
3. **Eliminar** handler `_on_video_enabled_changed()` de `main.py`
4. **Eliminar** conexión en `main.py` línea 234
5. **Deprecar** método `enable_video()` en `video/video.py` (marcar con warning)

**Testing**:
- ✅ Cambiar modo en Settings → verificar que se respeta
- ✅ Reiniciar app → verificar persistencia
- ✅ Cargar canción → verificar sync de modo
- ✅ Todos los modos (full/loop/static/none) → verificar comportamiento

---

### Opción 2: Mantener `video_enable_toggle_btn` como quick toggle de Settings

**Razón**: Conveniencia para cambio rápido entre "current_mode" ↔ "none"

**Ventajas**:
- ✅ Quick toggle sin abrir Settings (1 click)
- ✅ Útil para presentaciones en vivo (rápido enable/disable)

**Desventajas**:
- ❌ Mantiene redundancia
- ❌ Dos lugares para cambiar video (confuso)
- ❌ No persiste cambios (solo runtime)
- ❌ No expone modos avanzados (loop/static)

**Cambios requeridos**:
1. **Refactor** `_on_video_enabled_changed()` para usar ConfigManager:
   ```python
   def _on_video_enabled_changed(self, enabled: bool):
       config = ConfigManager.get_instance()
       if enabled:
           # Restore to recommended or last non-none mode
           restored = config.get("video.mode_before_disable", config.get("video.recommended_mode", "full"))
           config.set("video.mode", restored)
       else:
           # Save current mode before disabling
           current = config.get("video.mode", "full")
           if current != "none":
               config.set("video.mode_before_disable", current)
           config.set("video.mode", "none")
       
       # Force reload video with new mode
       self.video_player.set_video_mode(config.get("video.mode"))
   ```

2. **Deprecar** método `enable_video()` (redirigir a `set_video_mode()`)

**Testing**:
- ✅ Toggle ON/OFF → verificar que ConfigManager se actualiza
- ✅ Persistencia entre sesiones → verificar que se guarda
- ✅ Interacción con Settings → verificar consistencia

---

### Opción 3: Convertir `video_enable_toggle_btn` en modo selector (multi-state)

**Razón**: Botón único para ciclar entre modos (full → loop → static → none → full)

**Ventajas**:
- ✅ Expone todos los modos en toolbar
- ✅ Quick access (no abrir Settings)
- ✅ Visual feedback del modo actual

**Desventajas**:
- ❌ Ciclar puede ser confuso (no intuitivo)
- ❌ Requiere 4 iconos distintos (diseño)
- ❌ More complex UX (mejor tener Settings)

**Cambios requeridos**:
1. **Cambiar** a botón no-checkable con `clicked` signal
2. **Implementar** ciclo de modos con tooltip dinámico
3. **Agregar** 4 iconos SVG (full/loop/static/none)
4. **Sincronizar** con ConfigManager en cada click

**Testing**:
- ✅ Ciclar modos → verificar iconos y tooltips
- ✅ Sincronización con Settings → verificar consistencia
- ✅ Persistencia → verificar que se guarda

---

## 🎯 Recomendación Final

**OPCIÓN 1: Eliminar `video_enable_toggle_btn`**

**Justificación**:
1. **ConfigManager es el Single Source of Truth** - ya gestiona modos de video
2. **Settings Dialog ya existe** - UI completa con warnings y recomendaciones
3. **Redundancia innecesaria** - no aporta valor que Settings no tenga
4. **UI más limpia** - menos botones = mejor UX
5. **Backward compatibility** - `enable_video()` puede marcarse deprecated sin romper nada

**Impacto**:
- ✅ **Zero risk**: `show_video_btn` permanece intacto (muestra/oculta ventana)
- ✅ **Functionality preserved**: Settings Dialog ya tiene control completo
- ✅ **Code cleanup**: Elimina 80 líneas de código redundante
- ✅ **Better UX**: Single place para configurar video (no confusión)

---

## 📋 Plan de Implementación (Opción 1)

### Paso 1: Eliminar video_enable_toggle_btn

**Archivos**:
- `ui/widgets/controls_widget.py`
  - ❌ Eliminar líneas 120-131 (instanciación del botón)
  - ❌ Eliminar línea 141 (agregar a layout)
  - ❌ Eliminar líneas 211-220 (handler `_on_video_enable_toggled`)
  - ❌ Eliminar línea 17 (signal `video_enabled_changed`)

- `main.py`
  - ❌ Eliminar líneas 228-234 (comentarios + conexión)
  - ❌ Eliminar líneas 408-421 (handler `_on_video_enabled_changed`)

### Paso 2: Marcar enable_video() como deprecated

**Archivo**: `video/video.py`
- ⚠️ Agregar warning en línea 190:
  ```python
  def enable_video(self, enable: bool = True):
      """DEPRECATED: Use set_video_mode() or ConfigManager instead.
      
      This method is kept for backward compatibility but will be removed
      in a future version. Use ConfigManager.set("video.mode", "none") 
      to disable video, or set_video_mode() for fine-grained control.
      """
      import warnings
      warnings.warn(
          "enable_video() is deprecated. Use set_video_mode() or ConfigManager instead.",
          DeprecationWarning,
          stacklevel=2
      )
      # ... rest of implementation
  ```

### Paso 3: Verificar Settings Dialog

**Archivo**: `ui/widgets/settings_dialog.py`
- ✅ Ya tiene video mode selector (líneas 95-147)
- ✅ Ya muestra modo recomendado
- ✅ Ya tiene warning visual
- ✅ Ya persiste en ConfigManager

**No se requieren cambios** - Settings Dialog ya es completo

### Paso 4: Testing

**Test Suite**:
1. ✅ Abrir Settings → cambiar modo a "None" → verificar que video no carga
2. ✅ Cambiar modo a "Loop" → verificar que usa loop background
3. ✅ Cambiar modo a "Full" → verificar que usa video del multi
4. ✅ Reiniciar app → verificar persistencia de modo
5. ✅ `show_video_btn` sigue funcionando → verificar show/hide window
6. ✅ No hay errores en logs → verificar que no hay referencias rotas

---

## ⚠️ Notas Importantes

### Separación de Responsabilidades

**`show_video_btn`** (MANTENER):
- **Propósito**: Control de visibilidad de ventana (proyección)
- **Alcance**: Runtime only (no persistente)
- **Función**: Show/hide window para proyector secundario
- **No toca**: Modo de video ni ConfigManager

**Settings Dialog video mode** (MANTENER):
- **Propósito**: Configuración global persistente de modo de video
- **Alcance**: Persistente (config/settings.json)
- **Función**: Seleccionar modo (full/loop/static/none)
- **No toca**: Visibilidad de ventana

**`video_enable_toggle_btn`** (ELIMINAR):
- **Propósito**: ~~Quick toggle on/off~~ **REDUNDANTE**
- **Problema**: Duplica Settings Dialog sin aportar valor
- **Razón eliminar**: ConfigManager ya gestiona enable/disable

---

## 🚀 Beneficios Esperados

Después de eliminar `video_enable_toggle_btn`:

1. **Código más limpio**: -80 líneas de código redundante
2. **UI más simple**: Un botón menos = menos confusión
3. **Single Source of Truth**: Solo ConfigManager gestiona modos
4. **Mejor mantenibilidad**: Un solo lugar para modificar lógica de video
5. **Consistencia**: Cambios siempre persistentes (no más "por qué se resetea?")
6. **Escalabilidad**: Futuros modos (e.g., "dual display") solo en Settings

---

**Última actualización**: 2026-01-22  
**Decisión pendiente**: Usuario debe elegir opción antes de proceder
