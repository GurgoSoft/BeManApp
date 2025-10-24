# Be Man App - Plataforma de Salud Mental

Una aplicación web Django para la gestión de eventos, foros de apoyo y contenido de salud mental dirigida a hombres.

## 🚀 Características principales

### 📅 Sistema de Agenda y Eventos
- **Creación y gestión de eventos** con imagen, descripción, lugar, fecha y precio
- **Dashboard administrativo** para gestionar eventos y visualizar métricas
- **Sistema de inscripciones** de usuarios a eventos
- **Notificaciones automáticas** cuando se publican nuevos eventos
- **Validaciones inteligentes**: eventos del mismo día requieren 2 horas de anticipación mínima
- **Separación automática** entre "Próximos eventos" y "Eventos pasados"

### 💬 Foro de Historias
- **Publicación de historias** personales y experiencias
- **Sistema de comentarios** con respuestas anidadas
- **Likes y favoritos** para contenido relevante
- **Moderación automática** con filtro de palabras prohibidas y soporte para Azure Content Safety AI
- **Ocultación de contenido** inapropiado

### 👥 Gestión de Usuarios
- **Autenticación personalizada** con email como username
- **Perfiles de usuario** con foto, biografía y teléfono
- **Sistema de notificaciones** integrado
- **Roles administrativos** con acceso al dashboard

### 🎧 Módulo de Podcast
- Estructura preparada para contenido de audio y multimedia

### 💬 Soporte WhatsApp
- **Widget flotante** configurable para contacto directo
- **Integración automática** con números de soporte
- **Mensajes predefinidos** personalizables

## 🛠️ Tecnologías

- **Backend**: Django 5.2.7, Python 3.12
- **Base de datos**: SQLite (desarrollo)
- **Frontend**: Bootstrap 5.3.3, Remix Icons
- **Internacionalización**: Soporte multi-idioma (ES/EN/FR/DE/IT)
- **Moderación**: Sistema local + Azure Content Safety (opcional)

## 📋 Requisitos

```bash
# Instalar dependencias
pip install django==5.2.7
pip install pillow  # Para manejo de imágenes
```

## 🚀 Instalación y configuración

1. **Clonar y configurar el proyecto**:
```bash
cd "c:\Users\User\Desktop\Be Man App\BeManApp\saludmental\src"
```

2. **Aplicar migraciones**:
```bash
python manage.py migrate
```

3. **Crear superusuario admin (opcional)**:
```bash
python manage.py create_admin
```

4. **Ejecutar servidor de desarrollo**:
```bash
python manage.py runserver
```

5. **Acceder a la aplicación**:
   - Frontend: http://localhost:8000/
   - Admin Django: http://localhost:8000/admin/

## 🔐 Credenciales de acceso

### Usuario Administrador
- **Email**: `admin@example.com`
- **Contraseña**: `Admin123!@#`
- **Permisos**: Acceso completo al dashboard admin y gestión de eventos

### Acceso al Dashboard
- Una vez logueado como staff, verás el icono de admin en la navbar
- Ruta directa: `/es/agenda/admin/`

## ⚙️ Configuración

### Variables de entorno (opcional)

```bash
# WhatsApp Support
WHATSAPP_SUPPORT_NUMBER=573133169313
WHATSAPP_DEFAULT_MESSAGE="Hola, necesito ayuda con Be Man Be Woman."
WHATSAPP_HELP_ENABLED=True

# Moderación con Azure AI (opcional)
MODERATION_BACKEND=azure  # o "local"
AZURE_CONTENT_SAFETY_ENDPOINT=tu_endpoint
AZURE_CONTENT_SAFETY_KEY=tu_key
AZURE_CONTENT_SAFETY_THRESHOLD=2
```

### Archivos multimedia
- **Eventos**: Imágenes se guardan en `media/eventos/`
- **Perfiles**: Fotos en `media/perfil/`
- **Formatos soportados**: JPG, PNG, WEBP (máx. 3MB)

## 📱 Funcionalidades principales

### Para Administradores
1. **Dashboard de eventos**:
   - Métricas en tiempo real (usuarios, inscripciones, eventos)
   - Gestión CRUD completa de eventos
   - Visualización de inscritos por evento

2. **Publicación de eventos**:
   - Formulario con validaciones avanzadas
   - Previsualización de imagen en tiempo real
   - Generación automática de slug único
   - Contadores de caracteres
   - Publicación automática con notificaciones

3. **Moderación de contenido**:
   - Filtro automático de palabras prohibidas
   - Integración opcional con Azure Content Safety
   - Gestión de reportes de usuarios

### Para Usuarios
1. **Exploración de eventos**:
   - Listado visual con imágenes
   - Filtrado automático por fecha (próximos/pasados)
   - Sistema de inscripción con un clic
   - Páginas de detalle estilo e-commerce

2. **Participación en el foro**:
   - Publicación de historias personales
   - Comentarios y respuestas
   - Sistema de likes y favoritos
   - Notificaciones de actividad

3. **Gestión de perfil**:
   - Edición de información personal
   - Subida de foto de perfil
   - Configuración de notificaciones

## 🏗️ Estructura del proyecto

```
src/
├── apps/
│   ├── agenda/          # Gestión de eventos
│   ├── foro/            # Historias y comentarios
│   ├── podcast/         # Módulo multimedia
│   └── usuarios/        # Autenticación y perfiles
├── config/              # Configuración Django
├── templates/           # Plantillas HTML
├── static/             # CSS, JS, imágenes
├── media/              # Archivos subidos
└── manage.py
```

## 🔧 Comandos útiles

```bash
# Crear usuario admin
python manage.py create_admin

# Generar migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Recopilar archivos estáticos
python manage.py collectstatic

# Ejecutar tests
python manage.py test
```

## 🎨 Temas y diseño

- **Tema oscuro** por defecto con paleta azul/dorado
- **Diseño responsive** con Bootstrap 5
- **Iconografía** consistente con Remix Icons
- **Componentes reutilizables** para formularios y tarjetas

## 🛡️ Seguridad y validaciones

- **Validación de archivos**: Tipo, tamaño y contenido de imágenes
- **Filtro anti-spam**: Prevención de contenido inapropiado
- **Validaciones de negocio**: Fechas, precios, conflictos de horario
- **CSRF protection** en todos los formularios
- **Sanitización** de inputs de usuario

## 📞 Soporte

Para soporte técnico o preguntas sobre el proyecto:
- **WhatsApp**: +57 313 316 9313
- **Mensaje por defecto**: "Hola, necesito ayuda con Be Man Be Woman."

## 🚀 Próximas funcionalidades

- Export CSV de inscripciones
- Sistema de chat en tiempo real
- Integración con APIs de pago
- App móvil nativa
- Analytics avanzados

---

**Desarrollado para promover el bienestar mental masculino** 💙