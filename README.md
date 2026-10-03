# canvas-calendar-agent

Explorador de solo lectura para conocer la información académica disponible en
Canvas UC antes de construir futuras integraciones.

Esta etapa permite elegir un curso y consultar tareas, módulos, páginas, archivos,
eventos de calendario, anuncios y syllabus. No descarga archivos ni integra Google
Calendar, OpenAI o agentes.

## Requisitos e instalación

- Python 3.10 o superior
- Un token de acceso personal de Canvas

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura `.env` con la raíz de la misma instancia donde generaste el token:

```dotenv
CANVAS_BASE_URL=https://cursos.canvas.uc.cl
CANVAS_TOKEN=tu_token_personal
```

`.env` está ignorado por Git. No compartas ni confirmes ese archivo.

## Explorar un curso

```powershell
python main.py
```

La CLI lista los cursos cuya **matrícula** figura como activa. Esto no significa
necesariamente que sean cursos del semestre actual. Cada fila muestra ID, nombre,
código, `enrollment_term_id`, estado y publicación cuando Canvas la informa.

Después de elegir un curso por número se consultan y resumen:

- assignments, con descripción, fechas, tipos de entrega y URL en los datos crudos;
- módulos y sus items (páginas, archivos, tareas, quizzes, enlaces y otros tipos);
- metadatos de páginas y archivos, sin descargar contenido;
- eventos de calendario;
- anuncios;
- detalles del curso y cuerpo HTML del syllabus, si existe.

La muestra impresa contiene como máximo tres títulos por categoría. Si Canvas no
autoriza una fuente, la CLI la marca como no disponible y continúa con las demás.

## Tests

Los tests usan respuestas simuladas y no necesitan credenciales ni red:

```powershell
python -m unittest discover -s tests
```

## Seguridad y alcance

- El token se lee exclusivamente desde `CANVAS_TOKEN`.
- Solo se realizan solicitudes HTTP `GET`.
- La paginación rechaza enlaces hacia otro origen para no filtrar el token.
- Los archivos se enumeran como metadatos; nunca se descargan.
- No hay integración con calendarios, IA, agentes ni extracción automática de fechas.
