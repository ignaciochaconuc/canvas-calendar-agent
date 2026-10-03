# canvas-calendar-agent

Primera etapa de un proyecto para consultar de forma segura la API REST de Canvas UC.
Por ahora, la aplicación solo obtiene los cursos activos del usuario autenticado y
muestra sus nombres e IDs. No integra Google Calendar, IA ni extracción de fechas.

## Requisitos

- Python 3.10 o superior
- Un token de acceso personal de Canvas

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y completa las variables:

```dotenv
CANVAS_BASE_URL=https://canvas.uc.cl
CANVAS_TOKEN=tu_token_personal
```

El archivo `.env` está ignorado por Git. No compartas ni confirmes ese archivo.

## Primera prueba contra Canvas

Con el entorno virtual activo y `.env` configurado:

```powershell
python main.py
```

La salida tendrá este formato:

```text
Cursos activos:
- 12345: Nombre del curso
```

La URL puede variar según la instancia institucional. Debe ser la raíz de Canvas,
sin `/api/v1` al final.

## Tests

Los tests no requieren token ni acceso a Canvas:

```powershell
python -m unittest discover -s tests
```

## Seguridad

Las credenciales se leen exclusivamente desde `CANVAS_TOKEN` y
`CANVAS_BASE_URL`. No se registran ni se incluyen en mensajes de error. Mantén los
secretos solo en `.env` o en variables de entorno del sistema.
