# 📜 MultiLyrics: Blueprint Maestro de Desarrollo

## 1. Visión y Propósito
**MultiLyrics** es una estación de trabajo de audio y video multiplataforma (Windows/Linux/macOS) diseñada específicamente para iglesias con recursos limitados.
- **Misión:** Democratizar el uso de multitracks profesionales mediante una herramienta gratuita y ligera.
- **Ética:** Código abierto bajo **GNU GPLv3**.
- **Atribución:** Mantener un archivo `CREDITS.md` con citas académicas (Madmom, Demucs, etc.) y una ventana "About" en la UI que lo renderice dinámicamente.

## 2. Estructura de Proyecto y Persistencia
La aplicación utiliza un sistema de carpetas por canción para garantizar la portabilidad y facilidad de backup.

- **Raíz de Librería:** `library/multis/{song_id}/` (Descomprimido para acceso instantáneo).
- **Estructura de Carpeta de Canción:**
    - `meta.json`: Metadatos técnicos (BPM, Key, Compass, Duration).
    - `master.wav`: Audio de referencia para dibujo de waveforms.
    - `video.mp4`: (Opcional) Videolyric original para proyección.
    - `lyrics.lrc`: Letras sincronizadas en formato LRC (UTF-8).
    - `/tracks/`: Carpeta con stems individuales (`drums.wav`, `bass.wav`, etc.).
- **Estado Global:** Singleton `ConfigManager` que gestiona `settings.json` (ID de tarjeta de audio, rutas, volumen maestro).

## 3. Capa de Datos y Análisis (Models)
- **Matriz de Beats:** Almacenada como `[[timestamp, beat_pos], ...]`.
    - `beat_pos == 1.0` identifica el **Downbeat** (Tiempo 1).
    - Propósito: Dibujo de grid en Timeline, disparador de Metrónomo y cálculo de Cues.
- **Matriz de Acordes:** Estructura `[[start, end, label], ...]`.
- **Lazy Loading Estricto:** Prohibido importar librerías pesadas (`torch`, `demucs`, `madmom`) en el scope global. Se cargan bajo demanda y en subprocesos aislados para proteger la estabilidad de la UI y el audio.

## 4. Motor de Audio y Sincronización (Core)
- **Tecnología:** `sounddevice` + `NumPy` (Uso de arrays `float32`).
- **Audio Callback:** Hilo de alta prioridad. Prohibido realizar I/O, prints o cálculos pesados dentro del callback.
- **Regla de Sincronización:** El `AudioEngine` emitirá un evento `TIME_CHANGED`. El componente de letras escuchará ese tiempo y usará `LrcParser.find_line_at()` para actualizar el texto en pantalla. Nunca uses un timer independiente para las letras; siempre deben ser "esclavas" del tiempo del audio.
- **Ruteo de Salida (Split Mode):**
    - **Canal Izquierdo (L):** Mezcla Mono de la instrumentación.
    - **Canal Derecho (R):** Metrónomo (Click) + Guía de Voz (Cues).
- **Guía de Voz (Cues):** Disparo de muestras `.wav` pre-grabadas exactamente **4 beats antes** del inicio de una sección.
- **Pitch Shifting:** Procesamiento offline mediante `pyrubberband` antes de iniciar la reproducción.

### 4.1 Patrón de Callback de Audio (CRÍTICO)
- **PROHIBIDO dentro del callback:**
  - ❌ Locks, mutexes, semáforos (`threading.Lock`, `multiprocessing.Lock`)
  - ❌ I/O de archivos (`open()`, `read()`, `write()`)
  - ❌ Prints o logging (`print()`, `logging.info()`)
  - ❌ Llamadas a APIs de Qt (`Signal.emit()` con threading puede causar deadlocks)
  - ❌ Allocación dinámica de memoria (`list.append()`, `dict[key] = value`)
- **PERMITIDO dentro del callback:**
  - ✅ Operaciones sobre arrays NumPy pre-cargados en memoria
  - ✅ Aritmética básica (`+`, `-`, `*`, `/`, `np.clip()`)

### 5.1 Widget Lifecycle
- **Creación:** `__init__()` solo debe inicializar atributos básicos y llamar a `init_ui()`.
- **Configuración UI:** `init_ui()` construye la jerarquía de widgets y aplica estilos.
- **Conexión:** `connect_signals()` debe ser un método separado llamado después de la construcción completa.
- **Destrucción:** Siempre desconectar signals en `closeEvent()` para evitar memory leaks:
  ```python
  def closeEvent(self, event):
      self.engine.positionChanged.disconnect(self.update_position)
      super().closeEvent(event)
  ```
  - ✅ Lectura de variables atómicas simples (`bool`, `int`, `float`)
- **Comunicación UI → Callback:**
  - Usar `queue.Queue` thread-safe para enviar comandos (volumen, mute, etc.)
  - El callback consulta la cola al inicio de cada ciclo sin bloquear:
    ```python
    try:
        command = self.command_queue.get_nowait()
        self.process_command(command)
    except queue.Empty:
        pass
    ```
- **Comunicación Callback → UI:**
  - Actualizar contadores atómicos (`self.playback_frame += frames`)
  - Emitir signals desde un thread separado que lee esos contadores

## 5. Interfaz de Usuario y Estética (PySide6)
- **Framework:** `PySide6` (Qt6) para gestión robusta de ventanas y multimedia.
- **Estética "Deep Tech Blue":**
    - Fondo Base: `#0B0E14`
    - Superficies: `#161B22`
    - Acento Neón Cian: `#00E5FF`
    - Acento Neón Púrpura: `#7C4DFF`
- **Efectos:** Brillos neón con `QGraphicsDropShadowEffect` y uso de iconos SVG dinámicos.
- **Doble Pantalla:** Ventana secundaria dedicada para proyección en proyector/pantalla externa (`Qt.FramelessWindowHint`).
- **Lógica de Video:** Uso de `QMediaPlayer` nativo. Si no hay video original, usar loops abstractos de `assets/loops/` con texto superpuesto.

## 6. Control Remoto y Conectividad
- **Backend:** `FastAPI` embebido en un `QThread` independiente.
- **Comunicación:** WebSockets para sincronización de baja latencia.
- **Protocolo:** JSON estructurado: `{"event": "EVENT_NAME", "payload": {...}}`.
- **Emparejamiento:** Generación de código QR con la IP local para acceso rápido desde dispositivos móviles (Frontend en Vue.js ligero).

## 7. Convenciones de Desarrollo
- **Rutas:** Uso estricto de `pathlib.Path`.
- **Estilo de Código:** PEP 8 + Type Hinting obligatorio.
- **Documentación:** Docstrings en formato Google Style para generación automática con MkDocs.
- **Constantes:** Centralizadas en `core/constants.py` en `SCREAMING_SNAKE_CASE`.

## 8. Arquitectura y Patrones de Diseño

### 8.1 Patrones Obligatorios
- **Singleton:** `AudioEngine` debe tener una única instancia gestionada por `MainWindow`. Evitar múltiples streams de audio.
- **Observer (Signal-Slot):** Toda comunicación entre componentes debe usar `QObject.Signal`. Prohibido polling o timers independientes.
  - ✅ Correcto: `engine.positionChanged.connect(waveform.update_position)`
  - ❌ Incorrecto: `QTimer` en el widget para consultar el tiempo del engine
- **Facade:** Clases utilitarias (`LrcParser`, `StyleManager`, `ConfigManager`) deben exponer interfaces simples y ocultar complejidad interna.
- **DTO (Data Transfer Objects):** Usar `@dataclass` para estructuras de datos inmutables. Ejemplo: `Song`, `LyricLine`, `TrackMetadata`.

### 8.2 Separación de Responsabilidades (Capas)
```
┌─────────────────────────────────────────┐
│  UI Layer (PySide6)                     │  ← Solo renderizado y eventos
│  • MainWindow, TrackStripWidget         │
└──────────────┬──────────────────────────┘
               │ Signals/Slots
┌──────────────▼──────────────────────────┐
│  Core Layer (Lógica de Negocio)        │  ← Motor de audio, sincronización
│  • AudioEngine, TimeSync                │
└──────────────┬──────────────────────────┘
               │ Carga de datos
┌──────────────▼──────────────────────────┐
│  Models Layer (Datos)                   │  ← DTOs inmutables
│  • Song, Track, LyricLine               │
└──────────────┬──────────────────────────┘
               │ Persistencia
┌──────────────▼──────────────────────────┐
│  Utils Layer (Helpers)                  │  ← Parsers, Config, Análisis
│  • LrcParser, ConfigManager             │
└─────────────────────────────────────────┘
```

### 8.3 Reglas de Comunicación
1. **UI → Core:** Solo mediante llamadas directas a métodos públicos del engine.
2. **Core → UI:** Solo mediante `Signal` emissions. Nunca referencias directas a widgets.
3. **Models → Todo:** Los modelos son leídos por todas las capas, pero nunca modifican otras capas.
4. **Utils → Nadie:** Las utilidades son pasivas, nunca inician comunicación.

### 8.4 Gestión de Estado
- **Estado Global:** `ConfigManager` (Singleton) para `settings.json`.
- **Estado de Sesión:** `MainWindow` mantiene referencia al `Song` activo y al `AudioEngine`.
- **Estado de Reproducción:** Exclusivamente en `AudioEngine` (`is_playing`, `playback_frame`).
- **Estado de UI:** Cada widget gestiona su propio estado visual (ej. `TrackStripWidget.mute_btn.checked`).

### 8.5 Factory Methods y Loaders
- Toda construcción compleja de objetos debe hacerse mediante métodos `@classmethod` estáticos:
  ```python
  @classmethod
  def load(cls, path: str) -> 'Song':
      # Lógica compleja de carga
      return cls(...)
  ```
- Prohibido lógica de I/O en `__init__()`. Los constructores deben ser triviales.

### 8.6 Lazy Loading y Carga Asíncrona
- **Regla de Oro:** Las librerías pesadas (`torch`, `demucs`, `madmom`) solo se importan cuando el usuario activa la función correspondiente.
- **Implementación:** Usar `QThread` para operaciones largas (separación de stems, análisis de beats).
  ```python
  # ❌ PROHIBIDO en el scope global
  import torch
  import demucs
  
  # ✅ CORRECTO: Carga bajo demanda
  def separate_stems(audio_path):
      import torch  # Import local
      import demucs
      # ...
  ```

### 8.7 Testing y Mocks
- **Principio:** Toda lógica de negocio debe ser testeable sin inicializar Qt.
- **Strategy:** Inyectar dependencias opcionales para facilitar mocks:
  ```python
  class AudioEngine(QObject):
      def __init__(self, audio_backend=None):
          self.backend = audio_backend or sounddevice
  ```
- **Fixtures:** Usar `pytest.fixture` para crear objetos `Song` de prueba sin I/O real.

### 17. Verificación de Dependencias de Sistema
- El módulo `installer.py` debe verificar la presencia de `libportaudio` al inicio.
- En Linux, si no existe, debe sugerir al usuario ejecutar: `sudo apt install libportaudio2`.