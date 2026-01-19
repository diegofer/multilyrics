# MultiLyrics - Guía de Empaquetado para Linux

Esta guía cubre cómo empaquetar MultiLyrics para diferentes formatos de distribución en Linux, asegurando que `libxcb-cursor0` esté incluido como dependencia.

---

## 📦 Formatos Soportados

### 1. Debian Package (.deb)

#### Estructura de Directorios
```
multilyrics_1.0.0/
├── DEBIAN/
│   └── control
├── usr/
│   ├── bin/
│   │   └── multilyrics
│   ├── share/
│   │   ├── applications/
│   │   │   └── multilyrics.desktop
│   │   ├── icons/
│   │   │   └── hicolor/
│   │   │       └── 256x256/
│   │   │           └── apps/
│   │   │               └── multilyrics.png
│   │   └── multilyrics/
│   │       └── (archivos de la aplicación)
```

#### Archivo `DEBIAN/control`
```
Package: multilyrics
Version: 1.0.0
Section: sound
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.10), python3-pyside6.qtcore, python3-pyside6.qtgui, python3-pyside6.qtwidgets, libxcb-cursor0, ffmpeg, vlc
Maintainer: Diego Fernando <tu-email@example.com>
Description: Professional multitrack audio/video player for worship teams
 MultiLyrics is a free, lightweight, and cross-platform multitrack player
 designed for churches and worship teams.
```

**⚠️ Nota Crítica:** `libxcb-cursor0` debe estar en `Depends:` para que se instale automáticamente.

#### Construir el .deb
```bash
# 1. Preparar estructura
mkdir -p multilyrics_1.0.0/DEBIAN
mkdir -p multilyrics_1.0.0/usr/{bin,share/{applications,icons/hicolor/256x256/apps,multilyrics}}

# 2. Copiar archivos
cp -r core models ui utils video assets library config multilyrics_1.0.0/usr/share/multilyrics/
cp main.py multilyrics_1.0.0/usr/share/multilyrics/
cp requirements.txt multilyrics_1.0.0/usr/share/multilyrics/

# 3. Crear launcher script
cat > multilyrics_1.0.0/usr/bin/multilyrics << 'EOF'
#!/bin/bash
cd /usr/share/multilyrics
python3 main.py "$@"
EOF
chmod +x multilyrics_1.0.0/usr/bin/multilyrics

# 4. Crear DEBIAN/control (ver arriba)

# 5. Construir
dpkg-deb --build multilyrics_1.0.0

# 6. Instalar
sudo dpkg -i multilyrics_1.0.0.deb
sudo apt-get install -f  # Resuelve dependencias automáticamente
```

---

### 2. RPM Package (.rpm) - Fedora/RHEL

#### Archivo `multilyrics.spec`
```spec
Name:           multilyrics
Version:        1.0.0
Release:        1%{?dist}
Summary:        Professional multitrack audio/video player for worship teams

License:        GPLv3
URL:            https://github.com/tu-usuario/multilyrics
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3 >= 3.10
Requires:       python3-pyside6
Requires:       libxcb-cursor
Requires:       ffmpeg
Requires:       vlc

%description
MultiLyrics is a free, lightweight, and cross-platform multitrack player
designed for churches and worship teams.

%prep
%autosetup

%build
# No build step for Python app

%install
mkdir -p %{buildroot}%{_datadir}/multilyrics
cp -r core models ui utils video assets library config main.py requirements.txt %{buildroot}%{_datadir}/multilyrics/

mkdir -p %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/multilyrics << 'EOF'
#!/bin/bash
cd %{_datadir}/multilyrics
python3 main.py "$@"
EOF
chmod +x %{buildroot}%{_bindir}/multilyrics

mkdir -p %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/multilyrics.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=MultiLyrics
Comment=Multitrack player for worship teams
Exec=multilyrics
Icon=multilyrics
Categories=AudioVideo;Audio;
EOF

%files
%{_bindir}/multilyrics
%{_datadir}/multilyrics
%{_datadir}/applications/multilyrics.desktop

%changelog
* Sat Jan 18 2026 Diego Fernando <tu-email@example.com> - 1.0.0-1
- Initial release
```

**⚠️ Nota:** En Fedora, la librería se llama `libxcb-cursor` (sin el `0` final).

#### Construir el RPM
```bash
# 1. Preparar tarball
tar czf multilyrics-1.0.0.tar.gz multilyrics/

# 2. Copiar a rpmbuild
mkdir -p ~/rpmbuild/{SOURCES,SPECS}
cp multilyrics-1.0.0.tar.gz ~/rpmbuild/SOURCES/
cp multilyrics.spec ~/rpmbuild/SPECS/

# 3. Construir
rpmbuild -ba ~/rpmbuild/SPECS/multilyrics.spec

# 4. RPM resultante en:
# ~/rpmbuild/RPMS/noarch/multilyrics-1.0.0-1.noarch.rpm
```

---

### 3. AppImage (Universal)

AppImage bundlea todas las dependencias, incluyendo libxcb-cursor0.

#### Estructura
```
AppDir/
├── AppRun (script launcher)
├── multilyrics.desktop
├── multilyrics.png
├── usr/
│   ├── bin/
│   │   └── python3
│   ├── lib/
│   │   ├── python3.10/
│   │   └── x86_64-linux-gnu/
│   │       └── libxcb-cursor.so.0  ← Bundleado!
│   └── share/
│       └── multilyrics/
```

#### Script `AppRun`
```bash
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"

# Agregar librerías bundleadas al LD_LIBRARY_PATH
export LD_LIBRARY_PATH="${HERE}/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"

# Usar Python bundleado
export PYTHONHOME="${HERE}/usr"
export PYTHONPATH="${HERE}/usr/lib/python3.10"

# Ejecutar app
cd "${HERE}/usr/share/multilyrics"
"${HERE}/usr/bin/python3" main.py "$@"
```

#### Construir con linuxdeploy
```bash
# 1. Crear AppDir base
mkdir -p AppDir/usr/share/multilyrics
cp -r core models ui utils video assets library config main.py AppDir/usr/share/multilyrics/

# 2. Copiar Python y dependencias
# (Usar virtual environment o sistema)
cp -r /usr/lib/python3.10 AppDir/usr/lib/

# 3. Copiar libxcb-cursor0
mkdir -p AppDir/usr/lib/x86_64-linux-gnu
cp /usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0 AppDir/usr/lib/x86_64-linux-gnu/

# 4. Crear AppRun (ver arriba)
chmod +x AppDir/AppRun

# 5. Crear .desktop y icon
cp assets/img/icon.png AppDir/multilyrics.png
cat > AppDir/multilyrics.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=MultiLyrics
Exec=multilyrics
Icon=multilyrics
Categories=AudioVideo;Audio;
EOF

# 6. Construir AppImage
appimagetool AppDir MultiLyrics-1.0.0-x86_64.AppImage
```

**Ventaja:** El usuario no necesita instalar nada, todo está bundleado.

---

### 4. Flatpak

#### Archivo `org.multilyrics.MultiLyrics.json`
```json
{
  "app-id": "org.multilyrics.MultiLyrics",
  "runtime": "org.freedesktop.Platform",
  "runtime-version": "23.08",
  "sdk": "org.freedesktop.Sdk",
  "command": "multilyrics",
  "finish-args": [
    "--socket=wayland",
    "--socket=x11",
    "--socket=pulseaudio",
    "--device=dri",
    "--filesystem=home"
  ],
  "modules": [
    {
      "name": "libxcb-cursor",
      "buildsystem": "autotools",
      "sources": [
        {
          "type": "archive",
          "url": "https://xcb.freedesktop.org/dist/xcb-util-cursor-0.1.4.tar.gz",
          "sha256": "..."
        }
      ]
    },
    {
      "name": "python3-pyside6",
      "buildsystem": "simple",
      "build-commands": [
        "pip3 install --prefix=/app pyside6"
      ]
    },
    {
      "name": "multilyrics",
      "buildsystem": "simple",
      "build-commands": [
        "cp -r core models ui utils video assets library config main.py /app/share/multilyrics/",
        "install -D multilyrics.sh /app/bin/multilyrics"
      ],
      "sources": [
        {
          "type": "dir",
          "path": "."
        }
      ]
    }
  ]
}
```

**⚠️ Nota:** Flatpak bundlea automáticamente todas las dependencias del runtime.

#### Construir
```bash
flatpak-builder --repo=repo build-dir org.multilyrics.MultiLyrics.json
flatpak build-bundle repo multilyrics.flatpak org.multilyrics.MultiLyrics
```

---

## 📋 Checklist de Empaquetado

Antes de distribuir, verificar:

- [ ] `libxcb-cursor0` (o equivalente) está en dependencias
- [ ] `.desktop` file tiene categorías correctas (`AudioVideo;Audio;`)
- [ ] Icon está en formato PNG, 256x256px
- [ ] Launcher script configura `PYTHONPATH` correctamente
- [ ] Permisos de ejecución en scripts (`chmod +x`)
- [ ] Licencia GPL v3 incluida (`LICENSE` file)
- [ ] README con instrucciones de instalación

---

## 🧪 Testing de Paquetes

### Test en VM Limpia
```bash
# 1. Crear VM con distribución objetivo
# 2. Instalar paquete
sudo dpkg -i multilyrics_1.0.0.deb
sudo apt-get install -f

# 3. Verificar dependencias
dpkg -l | grep libxcb-cursor0

# 4. Ejecutar
multilyrics

# 5. Verificar logs
# Debe mostrar: "✅ Using XCB via XWayland (better modal support)"
```

### Test de Desinstalación
```bash
sudo apt remove multilyrics
# Verificar que no quedan archivos huérfanos
```

---

## 🌐 Distribución

### Ubuntu PPA (Personal Package Archive)
1. Crear cuenta en Launchpad
2. Subir `.deb` source
3. Launchpad construye para todas las versiones de Ubuntu

### Flathub (Flatpak official repo)
1. Fork de flathub/flathub
2. Agregar manifest `org.multilyrics.MultiLyrics.json`
3. Pull request para review

### AUR (Arch User Repository)
```bash
# PKGBUILD
pkgname=multilyrics
pkgver=1.0.0
pkgrel=1
pkgdesc="Multitrack player for worship teams"
arch=('any')
url="https://github.com/tu-usuario/multilyrics"
license=('GPL3')
depends=('python' 'python-pyside6' 'libxcb' 'ffmpeg' 'vlc')
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('...')

package() {
  cd "$srcdir/$pkgname-$pkgver"
  install -Dm755 main.py "$pkgdir/usr/share/$pkgname/main.py"
  # ... copiar resto de archivos
}
```

---

## 📚 Referencias

- [Debian Packaging Tutorial](https://www.debian.org/doc/manuals/maint-guide/)
- [RPM Packaging Guide](https://rpm-packaging-guide.github.io/)
- [AppImage Documentation](https://docs.appimage.org/)
- [Flatpak Builder Guide](https://docs.flatpak.org/en/latest/flatpak-builder.html)

---

**Última actualización:** 2026-01-18
