# 🍎 MultiLyrics - Audio Setup Guide for macOS

**Última Actualización**: 2026-01-18  
**Versión**: 1.0

---

## 🎯 Selección Automática de Perfiles

MultiLyrics **auto-detecta tu hardware** al iniciar y selecciona el perfil óptimo automáticamente usando **CoreAudio** nativo.

```
INFO [core.audio_profiles] 🖥️  Detected OS: macos
INFO [core.audio_profiles] 💻 Detected hardware: ~2020 CPU, 16 GB RAM, 8 cores
INFO [core.audio_profiles] 🎯 Auto-selected profile: Modern Hardware
```

---

## 🎛️ Perfiles de Audio Disponibles

### 1️⃣ Legacy Hardware (2012-2015)

**Para**: MacBook Pro 2012-2015, iMac 2012-2015, Mac Mini 2012-2014  
**Configuración**: Blocksize 4096, GC deshabilitado, latencia ~85ms

✅ **Usa este perfil si**:
- Tu Mac es de 2012-2015 (pre-USB-C)
- MacBook Air con CPU Core i5 dual-core
- macOS High Sierra (10.13) o anterior
- Experimentas glitches o crackling

❌ **No usar si**:
- Tienes Mac con Apple Silicon (M1/M2/M3)
- macOS Monterey (12.0) o posterior

---

### 2️⃣ Balanced Performance (2016-2019) ⭐ **RECOMENDADO**

**Para**: MacBook Pro 2016-2019, iMac 2017-2019, Mac Mini 2018-2020  
**Configuración**: Blocksize 2048, GC deshabilitado, latencia ~43ms

✅ **Usa este perfil si**:
- Tu Mac es de 2016-2019 (Touch Bar era)
- Intel quad-core o superior
- macOS Catalina (10.15) - Big Sur (11.0)
- Quieres equilibrio entre estabilidad y latencia

**Este es el perfil por defecto para Intel Macs.**

---

### 3️⃣ Modern Hardware (2020+)

**Para**: Apple Silicon M1/M2/M3, Intel 2020+  
**Configuración**: Blocksize 1024, GC habilitado, latencia ~21ms

✅ **Usa este perfil si**:
- **Apple Silicon (M1, M1 Pro, M1 Max, M2, M3)**
- macOS Monterey (12.0) o posterior
- Priorizas baja latencia
- Uso en vivo o producción ligera

**Ideal para todos los Macs con Apple Silicon.**

#### Apple Silicon Performance

**CoreAudio en Apple Silicon es excepcional**:
- ⚡ Latencia ultra-baja (<10ms típico)
- 🔋 Eficiencia energética superior
- 🎵 Buffer switching más rápido que Intel
- ✅ Rosetta 2 tiene overhead mínimo en audio

**Si tienes M1/M2/M3, este perfil es automático y óptimo**.

---

## 🛠️ Override Manual (Opcional)

Si la selección automática no es óptima, puedes forzar un perfil:

```bash
# Forzar perfil específico
export MULTILYRICS_AUDIO_PROFILE="modern"
python main.py
```

**Nombres válidos**: `legacy`, `balanced`, `modern`

---

## ⚙️ Configuración del Sistema

### CoreAudio (Nativo)

MultiLyrics usa **CoreAudio** automáticamente - no requiere configuración adicional.

**CoreAudio es nativo en**:
- ✅ macOS Monterey 12.0+
- ✅ macOS Big Sur 11.0
- ✅ macOS Catalina 10.15
- ✅ macOS Mojave 10.14
- ⚠️ macOS High Sierra 10.13 (usar perfil Legacy)

### Optimizar Audio en macOS

#### 1. Configurar Frecuencia de Muestreo

**Para evitar resampling interno**:

1. Abrir **Audio MIDI Setup** (Utilidades → Audio MIDI Setup)
2. Seleccionar dispositivo de salida
3. Format: **48000.0 Hz** (o 44100.0 Hz si tus multis son 44.1k)
4. Cerrar

**Shortcut**: Cmd + Space → "Audio MIDI Setup"

#### 2. Deshabilitar Reducción de Ruido (AirPods/Bluetooth)

**Solo si usas AirPods u otros auriculares Bluetooth**:

1. System Preferences → Bluetooth
2. Dispositivo conectado → Options
3. ❌ Desactivar "Noise Cancellation" / "Ambient Noise Reduction"

**Nota**: Bluetooth tiene latencia inherente (~150-200ms). Para uso profesional, usar salida cableada.

#### 3. Verificar Output Device

```bash
# Ver dispositivo activo
system_profiler SPAudioDataType | grep "Default Output Device"

# O usar GUI
System Preferences → Sound → Output
```

---

## 📊 Monitoreo de Performance

Habilita **Audio Monitor** en Settings:

```
Settings → Audio → ✓ Show Latency Monitor
```

**Interpretación de métricas**:
- 🟢 Usage < 50%: Excelente (típico en M1/M2/M3)
- 🟠 Usage 50-80%: Aceptable
- 🔴 Usage > 80%: Crítico - cambiar a perfil más conservador
- **Xruns = 0** es ideal (audio sin glitches)

**En Apple Silicon, es común ver Usage < 20%** - el chip es muy eficiente.

---

## 🔍 Troubleshooting

### Audio entrecortado (glitches)

**Soluciones**:
1. Cambiar a perfil más conservador (`balanced` o `legacy`)
2. Cerrar aplicaciones pesadas (Chrome, Safari con muchas tabs)
3. Verificar Activity Monitor → CPU usage
4. Reiniciar CoreAudio:
   ```bash
   sudo killall coreaudiod
   ```

### Latencia muy alta

**Soluciones**:
1. Verificar que estás usando salida cableada (no Bluetooth)
2. Actualizar a perfil superior si tu hardware lo soporta
3. Verificar en Audio MIDI Setup que sample rate coincide con tus multis
4. Actualizar macOS a la última versión

### "Could not open audio device"

**Soluciones**:
1. Verificar que el dispositivo no está en uso por otra app
2. Reiniciar CoreAudio:
   ```bash
   sudo killall coreaudiod
   ```
3. Verificar dispositivo en System Preferences → Sound → Output
4. Verificar permisos de acceso al micrófono (aunque no lo uses):
   - System Preferences → Security & Privacy → Microphone

### Problemas con Rosetta 2 (Apple Silicon)

**Si usas Python x86_64 en Apple Silicon**:

```bash
# Verificar arquitectura de Python
file $(which python3)

# Si dice "x86_64", considera instalar Python nativo ARM:
arch -arm64 brew install python@3.11
```

**Nota**: Rosetta 2 funciona perfectamente para audio, pero ARM nativo es más eficiente.

---

## 💡 Tips para macOS

1. **Usa "Modern" en M1/M2/M3** - rendimiento excepcional
2. **Evita Bluetooth para audio profesional** - latencia muy alta
3. **Configura 48000 Hz en Audio MIDI** - evita resampling
4. **Cierra Safari/Chrome** - consumen mucha RAM
5. **Actualiza macOS** - mejoras constantes en CoreAudio
6. **Apple Silicon es superior** - si puedes, actualiza a M1+

---

## 🎧 Dispositivos de Audio Recomendados

### Integrados (Suficiente para uso en iglesias)

**Excelente calidad en todos los Macs modernos**:
- ✅ MacBook Pro 16" (2019+): Altavoces de 6 parlantes
- ✅ iMac 27" (2019+): Sistema de audio de alta fidelidad
- ✅ Mac Studio: DAC profesional integrado

### Interfaces Externas (Opcional, mejor calidad)

**USB-C (nativos para Mac moderno)**:
- ✅ Focusrite Scarlett Solo 3rd Gen (USB-C)
- ✅ Universal Audio Volt 2 (USB-C)
- ✅ Apogee Duet 3 (Thunderbolt)
- ✅ RME Babyface Pro FS (USB)

**Thunderbolt** (latencia ultra-baja):
- ✅ Universal Audio Apollo Twin (Thunderbolt)
- ✅ Antelope Audio Zen Tour (Thunderbolt)

---

## 🍎 Apple Silicon (M1/M2/M3) - Optimizaciones

### Unified Memory Architecture

**Apple Silicon usa memoria unificada** - ventajas para audio:
- ✅ Sin copia CPU ↔ GPU (latencia reducida)
- ✅ Bandwidth masivo (100+ GB/s vs 25 GB/s Intel)
- ✅ Acceso directo desde todos los cores

### Performance Cores vs Efficiency Cores

**CoreAudio usa performance cores automáticamente**:
- M1: 4 performance + 4 efficiency = 8 cores
- M1 Pro/Max: 8/10 performance cores
- M2: 4 performance + 4 efficiency = 8 cores
- M3: Similar a M2 con mejoras

**No requiere configuración manual**.

### Battery vs Plugged In

**En MacBook, conecta al power para mejor performance**:
- 🔌 Plugged in: Full performance cores
- 🔋 Battery: Puede throttlear para ahorrar energía

---

## 📊 Benchmark Típico

### Apple Silicon (M1/M2/M3)

```
Profile: Modern Hardware
Blocksize: 1024
Sample Rate: 48000 Hz
Buffer time: 21.33 ms
---
✅ Mean latency: 0.18 ms
✅ Peak latency: 0.45 ms
✅ Usage: 8.5% (excelente headroom)
✅ Xruns: 0
```

### Intel (2016-2019)

```
Profile: Balanced Performance
Blocksize: 2048
Sample Rate: 48000 Hz
Buffer time: 42.67 ms
---
✅ Mean latency: 0.82 ms
✅ Peak latency: 2.15 ms
✅ Usage: 32% (buen headroom)
✅ Xruns: 0
```

---

**¿Problemas?** Abre un issue en GitHub con:
- Output de inicio (primeras 20 líneas)
- Modelo de Mac: `system_profiler SPHardwareDataType | grep "Model"`
- macOS version: `sw_vers`
- Perfil activo (ver logs al iniciar)
