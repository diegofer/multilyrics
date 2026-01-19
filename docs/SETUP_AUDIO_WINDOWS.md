# 🪟 MultiLyrics - Audio Setup Guide for Windows

**Última Actualización**: 2026-01-18  
**Versión**: 1.0

---

## 🎯 Selección Automática de Perfiles

MultiLyrics **auto-detecta tu hardware** al iniciar y selecciona el perfil óptimo automáticamente usando **WASAPI** (Windows Audio Session API) nativo.

```
INFO [core.audio_profiles] 🖥️  Detected OS: windows
INFO [core.audio_profiles] 💻 Detected hardware: ~2018 CPU, 16 GB RAM, 4 cores
INFO [core.audio_profiles] 🎯 Auto-selected profile: Balanced Performance
```

---

## 🎛️ Perfiles de Audio Disponibles

### 1️⃣ Legacy Hardware (2008-2012)

**Para**: Intel Core 2 Duo, Sandy Bridge, AMD Phenom  
**Configuración**: Blocksize 4096, GC deshabilitado, latencia ~85ms

✅ **Usa este perfil si**:
- Tu CPU es de 2008-2012
- Tienes 2-4 cores y 4-8 GB RAM
- Experimentas glitches o crackling
- Windows 7/8/10 en hardware antiguo

❌ **No usar si**:
- Tu hardware es más moderno
- Tienes Windows 11 (requiere CPU 2017+)

---

### 2️⃣ Balanced Performance (2013-2018) ⭐ **RECOMENDADO**

**Para**: Intel i5 4th-8th Gen, Ryzen 1000-2000  
**Configuración**: Blocksize 2048, GC deshabilitado, latencia ~43ms

✅ **Usa este perfil si**:
- Tu CPU es de 2013-2018 (mayoría de usuarios)
- Tienes 4+ cores y 8+ GB RAM
- Windows 10/11
- Quieres equilibrio entre estabilidad y latencia

**Este es el perfil por defecto - cubre el 90% de casos de uso.**

---

### 3️⃣ Modern Hardware (2019+)

**Para**: Intel 9th Gen+, Ryzen 3000+  
**Configuración**: Blocksize 1024, GC habilitado, latencia ~21ms

✅ **Usa este perfil si**:
- Tu CPU es de 2019 o posterior
- Tienes 6+ cores y 16+ GB RAM
- Windows 10/11 actualizado
- Priorizas baja latencia

**Ideal para Windows 11 con drivers de audio actualizados.**

---

## 🛠️ Override Manual (Opcional)

Si la selección automática no es óptima, puedes forzar un perfil:

**PowerShell**:
```powershell
$env:MULTILYRICS_AUDIO_PROFILE="modern"
python main.py
```

**CMD**:
```cmd
set MULTILYRICS_AUDIO_PROFILE=modern
python main.py
```

**Nombres válidos**: `legacy`, `balanced`, `modern`

---

## ⚙️ Configuración del Sistema

### WASAPI (Windows Audio Session API)

MultiLyrics usa **WASAPI** automáticamente - no requiere configuración adicional.

**WASAPI es nativo en**:
- ✅ Windows 10 (todas las versiones)
- ✅ Windows 11 (todas las versiones)
- ✅ Windows 8.1
- ⚠️ Windows 7 (requiere Service Pack 1)

### Optimizar Audio en Windows

#### 1. Deshabilitar Mejoras de Audio

**Mejoras de audio pueden causar latencia adicional**:

1. Click derecho en el ícono de volumen → "Sonidos"
2. Pestaña "Reproducción" → Tu dispositivo → "Propiedades"
3. Pestaña "Mejoras" → ✅ "Deshabilitar todas las mejoras"
4. Aplicar → OK

#### 2. Configurar Frecuencia de Muestreo

**Para evitar resampling interno**:

1. Propiedades del dispositivo → Pestaña "Opciones avanzadas"
2. Formato predeterminado: **16 bits, 48000 Hz (Calidad de DVD)**
3. Aplicar → OK

**Nota**: Si tus multis son 44100 Hz, configura esa frecuencia.

#### 3. Deshabilitar Modo Exclusivo (Opcional)

**Para compartir audio con otras apps**:

1. Propiedades del dispositivo → Pestaña "Opciones avanzadas"
2. ❌ Desmarcar "Permitir que las aplicaciones tomen el control exclusivo"
3. Aplicar → OK

---

## 📊 Monitoreo de Performance

Habilita **Audio Monitor** en Settings:

```
Settings → Audio → ✓ Show Latency Monitor
```

**Interpretación de métricas**:
- 🟢 Usage < 50%: Excelente, headroom disponible
- 🟠 Usage 50-80%: Aceptable, monitorear
- 🔴 Usage > 80%: Crítico - cambiar a perfil más conservador
- **Xruns = 0** es ideal (audio sin glitches)

---

## 🔍 Troubleshooting

### Audio entrecortado (crackling, pops)

**Soluciones**:
1. Cambiar a perfil más conservador (`balanced` o `legacy`)
2. Deshabilitar "Mejoras de audio" en propiedades del dispositivo
3. Cerrar aplicaciones pesadas (Chrome, Discord, OBS)
4. Actualizar drivers de audio desde el sitio del fabricante

### Latencia muy alta

**Soluciones**:
1. Verificar que WASAPI está activo (no DirectSound legacy)
2. Actualizar a perfil superior si tu hardware lo soporta
3. Actualizar drivers de audio
4. Deshabilitar efectos en Windows Sonic

### "Could not open audio device"

**Soluciones**:
1. Verificar que el dispositivo no está en uso por otra app
2. Reiniciar servicio de audio:
   ```powershell
   # Ejecutar como Administrador
   Restart-Service -Name Audiosrv
   ```
3. Verificar dispositivo predeterminado:
   - Configuración → Sistema → Sonido → Salida

### Drivers de Audio

**Drivers recomendados**:
- **Realtek**: Descargar desde sitio oficial (no usar Windows Update)
- **NVIDIA HDMI Audio**: Actualizar con GeForce Experience
- **AMD HD Audio**: Actualizar con Radeon Software
- **USB Audio**: Drivers del fabricante (Focusrite, PreSonus, etc.)

---

## 💡 Tips para Windows

1. **Usa "Balanced" por defecto** - funciona en 90% de casos
2. **Desactiva mejoras de audio** - reducen latencia
3. **Configura 48000 Hz** - evita resampling si tus multis son 48kHz
4. **Actualiza drivers** - drivers viejos causan glitches
5. **Cierra apps innecesarias** - Chrome y Discord consumen mucho CPU
6. **Windows 11 es mejor** - WASAPI más optimizado que Windows 10

---

## 🎮 Gaming y Audio

**Si usas MultiLyrics en una PC gaming**:

1. **Deshabilita Game Mode** durante uso:
   - Configuración → Gaming → Modo de juego → OFF
   
2. **Deshabilita Game Bar**:
   - Configuración → Gaming → Barra de juego de Xbox → OFF

3. **Prioridad de proceso** (opcional, solo si hay problemas):
   ```powershell
   # Ejecutar MultiLyrics con prioridad alta
   Start-Process python -ArgumentList "main.py" -Verb RunAs -Priority High
   ```

---

## 🔊 Dispositivos de Audio Recomendados

**Tarjetas integradas** (suficiente para uso en iglesias):
- ✅ Realtek ALC1220 o superior
- ✅ Intel Smart Sound Technology
- ⚠️ Realtek ALC662 (hardware antiguo, usar perfil Legacy)

**Tarjetas externas** (opcional, mejor calidad):
- ✅ Focusrite Scarlett (2i2, 4i4)
- ✅ PreSonus AudioBox
- ✅ Behringer UMC series
- ✅ M-Audio M-Track

---

**¿Problemas?** Abre un issue en GitHub con:
- Output de inicio (primeras 20 líneas)
- Modelo de CPU: `systeminfo | findstr /C:"Processor"`
- RAM total: `systeminfo | findstr /C:"Total Physical Memory"`
- Perfil activo (ver logs al iniciar)
