# ⚽ Prode Mundial 2026 — Simulador Dixon-Coles

Simulador avanzado de partidos para el Mundial 2026 utilizando el modelo probabilístico de **Poisson Bivariado con corrección de Dixon-Coles** y simulaciones de **Monte Carlo** (300,000 iteraciones por partido).

## Características principales

- 📈 **Modelo Dixon-Coles:** Modelado estadístico preciso que ajusta la correlación de bajas anotaciones (0-0, 1-0, 0-1, 1-1).
- 🟢 **Calibración Dinámica en Vivo:** Conexión directa a los endpoints CDN de **FotMob** para extraer estadísticas de goles esperados (xG) y goles esperados concedidos (xGA) en tiempo real conforme avanza el torneo.
- ⚙️ **Auto-calibración y Ajustes Manuales:** sliders dinámicos que se actualizan de forma automática según el estado del torneo y permiten al usuario personalizar los parámetros.
- ⚡ **Diseño Premium:** Interfaz oscura, moderna, responsiva, con visualización de matrices de calor para marcadores exactos y probabilidades 1X2.
- ☁️ **Listo para Vercel:** Estructura stateless lista para ser desplegada en Vercel Serverless con un solo clic.

## Estructura del Proyecto

- `app.py`: Servidor Flask principal y definición de APIs.
- `engine/`:
  - `simulation.py`: Motor de simulación Dixon-Coles y Monte Carlo.
  - `calibration.py`: Conector de FotMob, mapeo de equipos, sistema de caché y razonamiento de sugerencias.
- `data/`: Datos estáticos de equipos, calendario de partidos del Mundial y almacenamiento del caché.
- `templates/` y `static/`: Interfaz de usuario (HTML, CSS, JS).
- `vercel.json` y `api/index.py`: Configuraciones de despliegue en la nube.

## Instalación Local

1. Clonar el repositorio.
2. Crear un entorno virtual de Python:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecutar el servidor:
   ```bash
   python3 app.py
   ```
5. Abrir `http://127.0.0.1:5000` en tu navegador.

## Licencia

Desarrollado para propósitos educativos y predicción de prodes del Mundial 2026.
