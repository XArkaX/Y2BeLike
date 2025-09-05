# YouTube Downloader con Interfaz Gráfica

Una aplicación moderna para descargar videos y audio de YouTube con interfaz gráfica usando Kivy.

## 🚀 Características

- ✅ **Interfaz moderna**: GUI atractiva con Kivy
- ✅ **Múltiples formatos**: Video MP4 y Audio MP3
- ✅ **Control de calidad**: Opciones específicas para video y audio
- ✅ **Descargas concurrentes**: Automáticas basadas en cantidad de URLs
- ✅ **Modo oscuro/claro**: Alternancia visual completa
- ✅ **Sin terminal**: Ejecución limpia sin consola
- ✅ **Soporte completo**: Videos, playlists y canales
- ✅ **Logs en tiempo real**: Seguimiento completo del progreso

## 📦 Instalación

### 1. Clona o descarga el proyecto
```bash
git clone <repository-url>
cd Download-Simply-Videos-From-YouTube-main
```

### 2. Instala las dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecuta la aplicación
**Opción A: Con launcher (recomendado)**
```bash
python launcher.py
```

**Opción B: Archivo batch (Windows)**
```bash
run_downloader.bat
```

**Opción C: Directo**
```bash
python download.py
```

## 📋 Dependencias

- **yt-dlp**: Motor de descarga de YouTube
- **kivy**: Framework de interfaz gráfica moderna
- **ffmpeg-python**: Procesamiento de audio/video

## 🎯 Uso

1. **URLs**: Pega las URLs de YouTube (una por línea o separadas por comas)
2. **Formato**: Selecciona Video (MP4) o Audio (MP3)
3. **Calidad**: Elige la calidad deseada (cambia automáticamente según formato)
4. **Directorio**: Selecciona dónde guardar los archivos
5. **Tema**: Alterna entre modo oscuro 🌙 y claro ☀️
6. **Descargar**: Haz clic en "Iniciar Descarga"

## 🎨 Interfaz

### Modo Video (MP4)
- Calidades: 1080p, 720p, 480p, 360p, 240p
- Descarga videos con audio incluido

### Modo Audio (MP3)
- Calidades: 320kbps, 256kbps, 192kbps, 128kbps, 64kbps
- Descarga solo audio en formato MP3

### Características Avanzadas
- **Workers automáticos**: Se ajustan según cantidad de URLs
- **Logs detallados**: Seguimiento completo en tiempo real
- **Progreso visual**: Barra de progreso integrada
- **Tema dinámico**: Cambio visual completo

## 🛠️ Archivos del Proyecto

- `download.py`: Aplicación principal
- `launcher.py`: Ejecuta sin mostrar terminal
- `run_downloader.bat`: Launcher para Windows
- `requirements.txt`: Dependencias del proyecto
- `README.md`: Esta documentación

## 📝 Notas

- La aplicación maneja automáticamente la concurrencia
- Los mensajes de progreso aparecen en el área de logs
- No se muestra ventana de terminal durante la ejecución
- Compatible con Windows, macOS y Linux

## 🔧 Solución de Problemas

### Error de Kivy
```bash
pip install kivy[full]
```

### FFmpeg no encontrado
La aplicación usa FFmpeg integrado de yt-dlp, pero para mejor compatibilidad:
```bash
# Windows
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

¡Disfruta descargando contenido de YouTube con esta interfaz moderna y profesional! 🎬✨