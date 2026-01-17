# Problemas Conocidos (Known Issues)

## AddDialog - Múltiples Instancias Visuales en Intel HD 3000

**Hardware Afectado:** Intel HD Graphics 3000 (Sandy Bridge 2011) + Ubuntu 22.04  
**Gravedad:** Visual (no afecta funcionalidad)  
**Estado:** Sin resolver - pendiente investigación profunda

### Descripción del Problema
Al abrir el diálogo AddDialog (botón "+" en main window), aparecen múltiples instancias visuales de la ventana o el fondo se ve transparente/con artefactos. Al mover la ventana, el problema se hace más evidente.

### Síntomas Observados
- Múltiples ventanas superpuestas con el mismo contenido
- Fondo transparente o semi-transparente
- Artefactos visuales al mover la ventana
- Problema persiste incluso cerrando y reabriendo el diálogo

### Contexto Técnico
- **Compositor:** Compositor débil/básico en Intel HD 3000
- **Display Server:** X11 (no testado en Wayland)
- **Qt Version:** 6.10.0
- **PySide6:** 6.10.0

### Tentativas de Solución (Todas Fallidas)

#### Intento 1: Window Attributes
```python
self.setAttribute(Qt.WA_NativeWindow, True)
self.setAttribute(Qt.WA_OpaquePaintEvent, True)
```
**Resultado:** Sin cambios

#### Intento 2: On-Demand Creation
Crear nueva instancia de AddDialog cada vez en lugar de reutilizar singleton.
**Resultado:** Sin cambios

#### Intento 3: Deferred Compositor Sync (Patrón VideoLyrics)
```python
QTimer.singleShot(50, self._force_compositor_sync)
```
**Resultado:** Sin cambios

#### Intento 4: QWidget en lugar de QDialog
Cambiar clase base de QDialog a QWidget con window flags para emular modal.
**Resultado:** Sin cambios

### Hipótesis de Causa Raíz
El compositor débil de Intel HD 3000 puede estar creando múltiples backing stores para ventanas modales de Qt. Posibles causas:
1. Bug en driver Intel i915 con compositor básico
2. Conflicto entre Qt y X11 compositor al crear ventanas modales
3. Problema específico de QDialog en hardware legacy con Ubuntu 22.04

### Workarounds Conocidos
Ninguno efectivo hasta el momento. El diálogo funciona correctamente (captura clicks, muestra contenido), solo el renderizado visual es problemático.

### Próximos Pasos de Investigación
1. Testear en Wayland (en lugar de X11)
2. Testear con compositor más robusto (Compiz, KWin)
3. Crear diálogo nativo con PyQt5 (en lugar de PySide6) para descartar bug de binding
4. Usar `xwininfo` y `xprop` para inspeccionar propiedades de ventana en X11
5. Capturar logs de compositor durante apertura del diálogo
6. Testear con variables de entorno Qt:
   ```bash
   QT_XCB_GL_INTEGRATION=xcb_egl
   QT_LOGGING_RULES="qt.qpa.*=true"
   ```

### Referencias
- Timeline flicker fix (commit 10dc49b): Dirty flag pattern resolvió problema similar
- VideoLyrics fix (commit 314fab0): QTimer.singleShot resolvió múltiples ventanas
- Audio stuttering fix (commit 93635d7): Hardware detection efectivo para otros problemas

### Logs de Sesión de Debugging
```
Fecha: 2026-01-17
Hardware: i5-2410M, Intel HD 3000, 8GB RAM, Ubuntu 22.04.5 LTS
Qt: 6.10.0, PySide6: 6.10.0
Display: X11 con compositor básico

Intentos: 4
Tiempo invertido: ~30 minutos
Resultado: Problema persiste, abortar para investigación futura
```

---

## Otros Issues

*(Agregar futuros issues aquí)*
