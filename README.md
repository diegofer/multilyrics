# Multilyrics — Instalación en Ubuntu

Este documento explica cómo preparar el entorno y ejecutar el proyecto en una máquina Ubuntu (20.04+). Está escrito en español.

## Requisitos del sistema

- Sistema: Ubuntu 20.04 o superior
- Python: 3.11 recomendado
- Paquetes del sistema necesarios:

Instala dependencias del sistema necesarias (FFmpeg, PortAudio, libsndfile, compiladores):

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg libsndfile1 libportaudio2 build-essential
```

Si usas alguna librería que compile extensiones (por ejemplo `sounddevice`, `soundfile`), puede ser necesario el paquete de desarrollo de PortAudio:

```bash
sudo apt install -y portaudio19-dev
```

## Uso del virtualenv incluido (opcional)

El repositorio puede venir con un entorno virtual dentro de la carpeta `env/`. Para usarlo:

```bash
# Desde la raíz del proyecto
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Crear un nuevo virtualenv (recomendado)

Si prefieres crear uno nuevo:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar la aplicación

Con el virtualenv activado, ejecuta:

```bash
python main.py
```

## Solución de problemas comunes

- Error relacionado con PortAudio o `sounddevice`: instala `portaudio19-dev` (ver arriba) y vuelve a instalar las dependencias del entorno.
- Error relacionado con `libsndfile`: confirma `libsndfile1` instalado.
- Si faltan paquetes en `requirements.txt`, instálalos con `pip install <paquete>` y considera actualizar `requirements.txt` con `pip freeze > requirements.txt` dentro del entorno.

## Notas

- Si quieres que pruebe los pasos de instalación y ejecute `python main.py` aquí, dime y lo hago (reportaré errores si aparecen).

---

Archivo creado automáticamente: instrucciones básicas para Ubuntu.
