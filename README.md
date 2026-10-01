# Dashboard IPK — Índice de Pasajeros por Kilómetro

## Qué contiene
Dashboard ejecutivo de una sola pantalla construido a partir de `ipk_zonal.xlsx`.

- **27.519 registros**
- **34 rutas**
- Cobertura: **2024-01-01 a 2026-09-20**
- Grano de operación: **fecha + ruta**
- IPK: **pasajeros / kilómetros**
- Filtros: rango de fechas y selección múltiple de rutas
- Evolución diaria y mensual
- Ranking de rutas, Top 5 y Bottom 5
- KPIs ejecutivos
- Detección automática de tendencias y outliers
- Panel de calidad de datos

## Tratamiento de calidad
Se encontraron:
- 401 registros con pasajeros nulos (1.46%).
- 0 kilómetros iguales a cero.
- 0 kilómetros negativos.
- 0 pasajeros negativos.
- 0 duplicados exactos.
- 0 duplicados en la llave fecha+ruta.
- 0 fechas inválidas.

Los registros con pasajeros nulos **no se usan para el cálculo del IPK**, porque no es posible conocer el numerador. Sus kilómetros se conservan para visibilizar el impacto de calidad.

## Cálculo
IPK agregado = `SUM(pasajeros válidos) / SUM(kilómetros asociados a pasajeros válidos)`.

No se utiliza `AVERAGE(IPK diario)` para los KPIs agregados, porque eso daría el mismo peso a operaciones de distinto volumen.

## Ejecutar localmente

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Luego abrir la URL local que muestre Streamlit.

## Publicar y obtener URL compartible

La opción recomendada es **Streamlit Community Cloud**:
1. Crear un repositorio GitHub.
2. Subir `app.py`, `requirements.txt` e `ipk_procesado.csv`.
3. En Streamlit Community Cloud, seleccionar el repositorio y `app.py`.
4. El servicio genera una URL `*.streamlit.app` compartible.

También puede desplegarse en un servidor institucional con Docker o en otra plataforma compatible con Streamlit.

## Limitación de este entregable
El código y los datos procesados quedan listos para despliegue, pero la generación de una URL pública requiere credenciales/acceso a una plataforma de hosting externa. No se inventa una URL que no haya sido desplegada.

## Archivos
- `app.py`: aplicación completa.
- `requirements.txt`: dependencias.
- `ipk_procesado.csv`: dataset con dimensiones temporales e IPK.
- `calidad_datos.json`: controles de calidad.
- `ipk_zonal.xlsx`: fuente original.
