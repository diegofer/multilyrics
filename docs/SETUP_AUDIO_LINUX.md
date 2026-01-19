# 🐧 MultiLyrics - Audio Setup Guide for Linux

**Última Actualización**: 2026-01-18  
**Versión**: 1.0

---

## 🎯 Selección Automática de Perfiles

MultiLyrics **auto-detecta tu hardware** al iniciar y selecciona el perfil óptimo automáticamente. No necesitas configurar nada manualmente.

```
INFO [core.audio_profiles] 🖥️  Detected OS: linux
INFO [core.audio_profiles] 💻 Detected hardware: ~2018 CPU, 31 GB RAM, 6 cores
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
- Experimentas glitches con otros perfiles

❌ **No usar si**:
- Tu hardware es más moderno
- Necesitas latencia baja

---

### 2️⃣ Balanced Performance (2013-2018) ⭐ **RECOMENDADO**

**Para**: Intel i5 4th-8th Gen, Ryzen 1000-2000  
**Configuración**: Blocksize 2048, GC deshabilitado, latencia ~43ms

✅ **Usa este perfil si**:
- Tu CPU es de 2013-2018 (mayoría de usuarios)
- Tienes 4+ cores y 8+ GB RAM
- Quieres equilibrio entre estabilidad y latencia

**Este es el perfil por defecto - cubre el 90% de casos de uso.**

---

### 3️⃣ Modern Hardware (2019+)

**Para**: Intel 9th Gen+, Ryzen 3000+  
**Configuración**: Blocksize 1024, GC habilitado, latencia ~21ms

✅ **Usa este perfil si**:
- Tu CPU es de 2019 o posterior
- Tienes 6+ cores y 16+ GB RAM
- Priorizas baja latencia

---

### 4️⃣ Low Latency (2020+) 🚀 **PROFESIONAL**

**Para**: Intel 11th Gen+, Ryzen 5000+  
**Configuración**: Blocksize 512, GC habilitado, latencia ~11ms  
**Requiere**: Kernel RT + PipeWire

✅ **Usa este perfil si**:
- Hardware de alta gama (2020+)
- Tienes 8+ cores y 16+ GB RAM
- Kernel RT instalado
- Uso profesional (grabación, producción)

#### Instalación Kernel RT:
```bash
# Ubuntu/Debian
sudo apt install linux-lowlatency

# Verificar
uname -a | grep rt
```

---

## 🛠️ Override Manual (Opcional)

Si la selección automática no es óptima, puedes forzar un perfil:

```bash
# Forzar perfil específico
export MULTILYRICS_AUDIO_PROFILE="modern"
python main.py
```

**Nombres válidos**: `legacy`, `balanced`, `modern`, `low_latency`

---

## ⚙️ Configuración del Sistema

### PipeWire (Recomendado)

```bash
# Instalar PipeWire (Ubuntu 22.04+)
sudo apt install pipewire pipewire-audio-client-libraries

# Habilitar
systemctl --user --now enable pipewire pipewire-pulse

# Verificar
pactl info | grep "Server Name"
# Debe mostrar: PulseAudio (on PipeWire)
```

### PulseAudio (Legacy)

```bash
# Ya viene instalado por defecto en Ubuntu
# Verificar estado
pulseaudio --check -v
```

---

## 📊 Monitoreo de Performance

Habilita **Audio Monitor** en Settings:

```
Settings → Audio → ✓ Show Latency Monitor
```

**Interpretación de métricas**:
- 🟢 Usage < 50%: Excelente
- 🟠 Usage 50-80%: Aceptable
- 🔴 Usage > 80%: Crítico - cambiar a perfil más conservador
- **Xruns = 0** es ideal (audio sin glitches)

---

## 🔍 Troubleshooting

### Audio entrecortado (xruns frecuentes)

**Soluciones**:
1. Cambiar a perfil más conservador (`balanced` o `legacy`)
2. Cerrar aplicaciones pesadas
3. Verificar uso de swap: `free -h` (debe ser 0)

### Latencia muy alta

**Soluciones**:
1. Actualizar a perfil superior si tu hardware lo soporta
2. Cambiar de PulseAudio a PipeWire
3. Deshabilitar effects en PulseAudio

### "Could not open audio device"

```bash
# Instalar dependencias
sudo apt install libportaudio2 portaudio19-dev

# Verificar dispositivos disponibles
python -c "import sounddevice as sd; print(sd.query_devices())"
```

---

## 💡 Tips

1. **Usa "Balanced" por defecto** - funciona en 90% de casos
2. **Monitorea xruns** - si ves > 5, considera perfil más conservador
3. **PipeWire es mejor** - menor latencia y CPU que PulseAudio
4. **RT kernel solo si lo necesitas** - para iglesias, kernel normal es suficiente

---

**¿Problemas?** Abre un issue en GitHub con los logs de inicio
