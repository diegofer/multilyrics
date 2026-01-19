#!/bin/bash
# filepath: scripts/setup_pipewire_ubuntu.sh
# MultiLyrics - PipeWire Setup for Ubuntu 22.04+
# Part of the MultiLyrics audio optimization suite

set -e  # Exit on error

echo "🚀 MultiLyrics - Configuración de PipeWire"
echo "=========================================="

# Verificar versión de Ubuntu
if ! grep -q "22.04\|23.04\|23.10\|24.04" /etc/os-release; then
    echo "⚠️  Advertencia: Este script está diseñado para Ubuntu 22.04+"
    echo "Tu versión puede no soportar PipeWire correctamente."
    read -p "¿Continuar de todos modos? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "Cancelado."
        exit 1
    fi
fi

# 1. Instalar paquetes necesarios
echo ""
echo "📦 Instalando dependencias de PipeWire..."
sudo apt update
sudo apt install -y \
    pipewire-audio-client-libraries \
    libspa-0.2-bluetooth \
    libspa-0.2-jack \
    wireplumber \
    pipewire-pulse

# 2. Deshabilitar PulseAudio
echo ""
echo "🛑 Deshabilitando PulseAudio..."
systemctl --user --now disable pulseaudio.service pulseaudio.socket 2>/dev/null || true
systemctl --user mask pulseaudio 2>/dev/null || true

# 3. Habilitar PipeWire
echo ""
echo "⚡ Activando PipeWire y WirePlumber..."
systemctl --user --now enable pipewire pipewire-pulse wireplumber

# 4. Reiniciar servicios
echo ""
echo "🔄 Reiniciando servicios de audio..."
systemctl --user restart pipewire pipewire-pulse wireplumber

echo ""
echo "=================================================="
echo "✅ ¡Configuración completada!"
echo ""
echo "⚠️  IMPORTANTE: Reinicia tu equipo para aplicar cambios."
echo ""
echo "🔍 Después de reiniciar, verifica con:"
echo "   pactl info | grep 'Server Name'"
echo "   (Debe mostrar: PulseAudio built on PipeWire)"
echo ""
echo "📖 Documentación: docs/development.md"
echo "=================================================="
