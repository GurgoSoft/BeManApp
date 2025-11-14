# 🚀 Guía de Deploy en PythonAnywhere

## Paso 1: Preparar el proyecto localmente

1. **Asegúrate de tener todos los archivos:**
   - `requirements.txt` ✅
   - `.env.example` ✅
   - `.gitignore` ✅

2. **Sube tu proyecto a GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Preparar para deploy"
   git remote add origin https://github.com/tu-usuario/tu-repo.git
   git push -u origin main
   ```

## Paso 2: Configurar PythonAnywhere

### 2.1 Crear cuenta
- Ve a [www.pythonanywhere.com](https://www.pythonanywhere.com)
- Crea una cuenta gratuita o de pago

### 2.2 Clonar el repositorio
1. Abre una **Bash console** en PythonAnywhere
2. Clona tu repo:
   ```bash
   git clone https://github.com/tu-usuario/tu-repo.git
   cd tu-repo/src
   ```

### 2.3 Crear entorno virtual
```bash
mkvirtualenv --python=/usr/bin/python3.10 saludmental
workon saludmental
pip install -r requirements.txt
```

### 2.4 Configurar variables de entorno
```bash
# Crear archivo .env
nano .env
```

Copiar y editar con tus datos:
```
SECRET_KEY=tu-secret-key-super-segura-generada
DEBUG=False
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com

EMAIL_HOST_USER=Iterum.comunidadhombres@gmail.com
EMAIL_HOST_PASSWORD=tfln svow zqlc axtv
```

**Generar SECRET_KEY nueva:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 2.5 Modificar settings.py para producción

Editar `config/settings.py`:

```python
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Email
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
```

### 2.6 Configurar base de datos y archivos estáticos
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## Paso 3: Configurar Web App en PythonAnywhere

### 3.1 Crear Web App
1. Ve a la pestaña **Web**
2. Click en **Add a new web app**
3. Selecciona **Manual configuration**
4. Elige **Python 3.10**

### 3.2 Configurar paths

**Source code:**
```
/home/tu-usuario/tu-repo/src
```

**Working directory:**
```
/home/tu-usuario/tu-repo/src
```

**Virtualenv:**
```
/home/tu-usuario/.virtualenvs/saludmental
```

### 3.3 Editar WSGI file

Click en el link del WSGI file y reemplaza TODO el contenido con:

```python
import os
import sys

# Agregar ruta del proyecto
path = '/home/tu-usuario/tu-repo/src'
if path not in sys.path:
    sys.path.insert(0, path)

# Cargar variables de entorno
from dotenv import load_dotenv
project_folder = os.path.expanduser(path)
load_dotenv(os.path.join(project_folder, '.env'))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 3.4 Configurar archivos estáticos

En la pestaña **Web**, en la sección **Static files**:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/tu-usuario/tu-repo/src/staticfiles` |
| `/media/` | `/home/tu-usuario/tu-repo/src/media` |

### 3.5 Instalar python-dotenv

```bash
workon saludmental
pip install python-dotenv
```

## Paso 4: ¡Lanzar!

1. Click en el botón verde **Reload** en la pestaña Web
2. Visita: `https://tu-usuario.pythonanywhere.com`

## 🔧 Comandos útiles después del deploy

### Actualizar código
```bash
cd ~/tu-repo/src
git pull
workon saludmental
python manage.py migrate
python manage.py collectstatic --noinput
# Luego hacer Reload en la Web tab
```

### Ver logs
```bash
# Error log
tail /var/log/tu-usuario.pythonanywhere.com.error.log

# Server log
tail /var/log/tu-usuario.pythonanywhere.com.server.log
```

### Ejecutar comandos Django
```bash
workon saludmental
cd ~/tu-repo/src
python manage.py shell
python manage.py createsuperuser
python manage.py migrate
```

## ⚠️ Problemas comunes

### Error 500
- Revisa los logs: `/var/log/*.log`
- Verifica que DEBUG=False
- Asegúrate de que ALLOWED_HOSTS incluya tu dominio

### Archivos estáticos no cargan
- Ejecuta `python manage.py collectstatic`
- Verifica las rutas en Static files
- Haz Reload de la web app

### Error con la base de datos
- Ejecuta `python manage.py migrate`
- Verifica permisos del archivo `db.sqlite3`

### Email no funciona
- Verifica las credenciales en `.env`
- Asegúrate de usar App Password de Gmail

## 📝 Notas importantes

- **Cuenta gratuita** tiene límites:
  - 1 web app
  - 512 MB de almacenamiento
  - Tráfico limitado
  
- **Actualizar después de cambios:**
  ```bash
  git pull
  python manage.py migrate
  python manage.py collectstatic --noinput
  # Reload en Web tab
  ```

- **Backup de la base de datos:**
  ```bash
  python manage.py dumpdata > backup.json
  ```

¡Listo! Tu aplicación debería estar funcionando en PythonAnywhere. 🎉
