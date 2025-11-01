# ...existing code...
from flask import Flask, request, render_template_string, redirect, url_for
import requests
import logging
import json

# configurar logging
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
logger = logging.getLogger(__name__)

"""
app.py - Pequeña app Flask que muestra login/registro y, tras login exitoso,
presenta una UI para gestionar productos usando la API remota.
Dependencias: flask, requests
Instalar: pip install flask requests
Ejecutar: python app.py
"""

API_BASE = "https://bug-free-journey-r45ww6g56p4725jj5-5000.app.github.dev"
# Endpoints de la nueva API
LOGIN_ENDPOINT = f"{API_BASE}/login"
REGISTER_ENDPOINT = f"{API_BASE}/registry"
PRODUCTS_ENDPOINT = f"{API_BASE}/productos"

# Inicializar app
app = Flask(__name__)

# Variable global simple para guardar el token del usuario logueado (por simplicity)
TOKEN = None

LOGIN_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Login</title>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
  <div class="bg-white shadow-md rounded-lg p-8 w-full max-w-md">
    <h1 class="text-2xl font-semibold text-center mb-6">Iniciar sesión</h1>
    <form method="post" action="{{ url_for('do_login') }}" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700">Usuario</label>
        <input name="username" required
               class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
               placeholder="tu.usuario"/>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">Contraseña</label>
        <input name="password" type="password" required
               class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
               placeholder="••••••••"/>
      </div>
      <div class="flex items-center justify-between">
        <button type="submit"
                class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition">
          Entrar
        </button>
        <a href="#" class="text-sm text-gray-500 hover:underline">¿Olvidaste la contraseña?</a>
      </div>
    </form>
    <p class="mt-4 text-center text-sm text-gray-600">
      ¿No tienes cuenta?
      <a href="{{ url_for('register') }}" class="text-indigo-600 hover:underline">Regístrate aquí</a>
    </p>
  </div>
</body>
</html>
"""

REGISTER_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Registro</title>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
  <div class="bg-white shadow-md rounded-lg p-8 w-full max-w-md">
    <h1 class="text-2xl font-semibold text-center mb-6">Registro de Usuario</h1>
    <form method="post" action="{{ url_for('do_register') }}" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700">Nombre completo</label>
        <input name="full_name" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" placeholder="Juan Pérez"/>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">Usuario</label>
        <input name="username" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" placeholder="juan.perez"/>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">Contraseña</label>
        <input name="password" type="password" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" placeholder="••••••••"/>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">Email</label>
        <input name="email" type="email" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" placeholder="juan@ejemplo.com"/>
      </div>
      <div class="flex items-center justify-between">
        <button type="submit" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition">Registrarse</button>
        <a href="{{ url_for('index') }}" class="text-sm text-gray-500 hover:underline">Ya tengo cuenta</a>
      </div>
    </form>
  </div>
</body>
</html>
"""

# Página principal después del login: botones para gestionar productos
PRODUCTS_UI_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Productos</title>
</head>
<body class="bg-gray-50 min-h-screen p-6">
  <div class="max-w-4xl mx-auto">
    <div class="bg-white shadow rounded-lg p-6 mb-6">
      <h1 class="text-2xl font-semibold mb-4">Gestión de Productos</h1>
      <p class="text-sm text-gray-600 mb-4">Token guardado en servidor: <code>{{ token_present }}</code></p>

      <div class="space-x-2">
        <a href="{{ url_for('productos_list') }}" class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">Mostrar productos</a>
        <a href="{{ url_for('productos_new') }}" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Crear producto</a>
        <form class="inline-block" method="get" action="{{ url_for('productos_view_form') }}">
          <input name="id" placeholder="ID para ver/editar/eliminar" class="px-2 py-1 border rounded" />
          <button type="submit" class="bg-gray-600 text-white px-3 py-1 rounded">Ir</button>
        </form>
        <a href="{{ url_for('index') }}" class="ml-4 text-sm text-gray-500 hover:underline">Cerrar sesión (volver)</a>
      </div>
    </div>

    {% if message %}
    <div class="bg-white shadow rounded-lg p-4 mb-4">
      <p class="text-sm text-gray-700">{{ message }}</p>
    </div>
    {% endif %}

  </div>
</body>
</html>
"""

PRODUCTS_LIST_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Lista de Productos</title>
</head>
<body class="bg-gray-50 min-h-screen p-6">
  <div class="max-w-6xl mx-auto">
    <div class="bg-white shadow rounded-lg p-6 mb-6">
      <h1 class="text-2xl font-semibold mb-4">Productos</h1>
      <a href="{{ url_for('productos_new') }}" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Crear producto</a>
      <a href="{{ url_for('productos_ui') }}" class="ml-2 text-sm text-gray-600 hover:underline">Volver</a>
    </div>

    <div class="bg-white shadow rounded-lg p-6">
      {% if productos %}
      <table class="min-w-full divide-y divide-gray-200">
        <thead><tr>
          <th class="px-4 py-2 text-left">ID</th><th class="px-4 py-2 text-left">Nombre</th><th class="px-4 py-2 text-left">Precio</th><th class="px-4 py-2 text-left">Stock</th><th class="px-4 py-2 text-left">Acciones</th>
        </tr></thead>
        <tbody>
          {% for p in productos %}
          <tr class="border-t">
            <td class="px-4 py-2">{{ p.get('id') or p.get('id_producto') or loop.index }}</td>
            <td class="px-4 py-2">{{ p.get('nombre_producto') or p.get('nombre') or '-' }}</td>
            <td class="px-4 py-2">{{ p.get('precio') or p.get('precio_unitario') or '-' }}</td>
            <td class="px-4 py-2">{{ p.get('stock') or '-' }}</td>
            <td class="px-4 py-2">
              <a href="{{ url_for('productos_view', pid=(p.get('id') or p.get('id_producto') )) }}" class="text-indigo-600 hover:underline">Ver / Editar</a>
              <form method="post" action="{{ url_for('productos_delete', pid=(p.get('id') or p.get('id_producto'))) }}" style="display:inline-block;margin-left:8px;">
                <button type="submit" class="text-red-600">Eliminar</button>
              </form>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <p class="text-sm text-gray-600">No hay productos o error al obtenerlos.</p>
      {% endif %}
    </div>
  </div>
</body>
</html>
"""

PRODUCT_FORM_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>{{ title }}</title>
</head>
<body class="bg-gray-50 min-h-screen p-6">
  <div class="max-w-2xl mx-auto">
    <div class="bg-white shadow rounded-lg p-6">
      <h1 class="text-xl font-semibold mb-4">{{ title }}</h1>
      <form method="post" action="{{ action }}">
        <div class="mb-2"><label class="block text-sm">Nombre</label><input name="nombre_producto" class="w-full border px-2 py-1" value="{{ producto.get('nombre_producto','') }}"></div>
        <div class="mb-2"><label class="block text-sm">Precio</label><input name="precio" class="w-full border px-2 py-1" value="{{ producto.get('precio','') }}"></div>
        <div class="mb-2"><label class="block text-sm">Stock</label><input name="stock" class="w-full border px-2 py-1" value="{{ producto.get('stock','') }}"></div>
        <div class="mb-2"><label class="block text-sm">id_categoria</label><input name="id_categoria" class="w-full border px-2 py-1" value="{{ producto.get('id_categoria','') }}"></div>
        <div class="mb-2"><label class="block text-sm">id_descuento</label><input name="id_descuento" class="w-full border px-2 py-1" value="{{ producto.get('id_descuento','') }}"></div>
        <div class="mb-2"><label class="block text-sm">id_iva</label><input name="id_iva" class="w-full border px-2 py-1" value="{{ producto.get('id_iva','') }}"></div>
        <div class="mb-2"><label class="block text-sm">id_proveedor</label><input name="id_proveedor" class="w-full border px-2 py-1" value="{{ producto.get('id_proveedor','') }}"></div>
        <div class="mt-4">
          <button type="submit" class="bg-indigo-600 text-white px-4 py-2 rounded">Enviar</button>
          <a href="{{ url_for('productos_ui') }}" class="ml-2 text-gray-600">Cancelar</a>
        </div>
      </form>
    </div>
  </div>
</body>
</html>
"""

PRODUCT_VIEW_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Producto {{ producto_id }}</title>
</head>
<body class="bg-gray-50 min-h-screen p-6">
  <div class="max-w-2xl mx-auto">
    <div class="bg-white shadow rounded-lg p-6">
      <h1 class="text-xl font-semibold mb-4">Producto {{ producto_id }}</h1>
      {% if producto %}
        <pre class="bg-gray-100 p-4 rounded">{{ producto | tojson(indent=2) }}</pre>
        <a href="{{ url_for('productos_edit', pid=producto_id) }}" class="bg-yellow-500 px-3 py-1 rounded text-white">Editar</a>
        <form method="post" action="{{ url_for('productos_delete', pid=producto_id) }}" style="display:inline-block;margin-left:8px;">
          <button type="submit" class="text-red-600">Eliminar</button>
        </form>
      {% else %}
        <p class="text-sm text-gray-600">Producto no encontrado.</p>
      {% endif %}
      <p class="mt-4"><a href="{{ url_for('productos_ui') }}" class="text-gray-600">Volver</a></p>
    </div>
  </div>
</body>
</html>
"""

# Lista corta de memes públicos (URLs directas) - usados para errores leves
MEMES = [
  "https://i.imgflip.com/30b1gx.jpg",
  "https://i.imgflip.com/1bij.jpg",
  "https://i.imgflip.com/3si4.jpg",
]

@app.route('/', methods=['GET'])
def index():
  return render_template_string(LOGIN_HTML)

@app.route('/do_login', methods=['POST'])
def do_login():
  global TOKEN
  username = request.form.get('username', '')
  password = request.form.get('password', '')
  payload = {"username": username, "password": password}
  logger.debug('Enviando login payload a %s: %s', LOGIN_ENDPOINT, payload)
  try:
    resp = requests.post(LOGIN_ENDPOINT, json=payload, timeout=8)
    logger.debug('Respuesta login status=%s body=%s', resp.status_code, resp.text)
  except requests.RequestException:
    logger.exception('Error de red al enviar login')
    return render_template_string(PRODUCTS_UI_HTML, token_present="no", message="Error de red al iniciar sesión"), 502

  token = None
  if resp.ok:
    try:
      body = resp.json()
      # claves comunes
      for key in ('access_token', 'token', 'access', 'jwt', 'id_token', 'authentication_token'):
        if isinstance(body, dict) and key in body:
          token = body[key]
          break
      # fallback: buscar string con 2 puntos (jwt)
      if not token:
        def find_jwt(obj):
          if isinstance(obj, str):
            return obj if obj.count('.') == 2 else None
          if isinstance(obj, dict):
            for v in obj.values():
              res = find_jwt(v)
              if res:
                return res
          if isinstance(obj, list):
            for item in obj:
              res = find_jwt(item)
              if res:
                return res
          return None
        token = find_jwt(body) or (body.get('detail') if isinstance(body, dict) else None)
    except Exception:
      token = resp.text or None

  if resp.ok and token:
    TOKEN = token
    logger.debug('Token guardado en servidor: %s', ('<oculto>' if TOKEN else 'None'))
    return redirect(url_for('productos_ui'))
  else:
    # login fallido
    msg = f"Autenticación fallida ({resp.status_code})."
    return render_template_string(PRODUCTS_UI_HTML, token_present="no", message=msg), max(400, resp.status_code)

@app.route('/register', methods=['GET'])
def register():
  return render_template_string(REGISTER_HTML)

@app.route('/register', methods=['POST'])
def do_register():
  data = {
    "full_name": request.form.get('full_name', ''),
    "username": request.form.get('username', ''),
    "password": request.form.get('password', ''),
    "email": request.form.get('email', ''),
  }
  logger.debug('Enviando register payload a %s: %s', REGISTER_ENDPOINT, data)
  try:
    resp = requests.post(REGISTER_ENDPOINT, json=data, timeout=8)
    logger.debug('Respuesta register status=%s body=%s', resp.status_code, resp.text)
  except requests.RequestException:
    logger.exception('Error de red al enviar registro')
    message = "Error de red al intentar registrarse. Intenta de nuevo más tarde."
    return render_template_string(PRODUCTS_UI_HTML, token_present="no", message=message), 502

  if resp.ok:
    try:
      body = resp.json()
      server_msg = body.get('message') or body.get('detail') or str(body)
    except Exception:
      server_msg = resp.text or 'Registro exitoso.'
    message = f"Registro satisfactorio. {server_msg}"
    return render_template_string(PRODUCTS_UI_HTML, token_present="no", message=message), 200
  else:
    try:
      body = resp.json()
      server_msg = body.get('message') or body.get('detail') or str(body)
    except Exception:
      server_msg = resp.text or 'Error en el registro.'
    message = f"Registro fallido ({resp.status_code}). {server_msg}"
    return render_template_string(PRODUCTS_UI_HTML, token_present="no", message=message), max(400, resp.status_code)

@app.route('/productos_ui', methods=['GET'])
def productos_ui():
  global TOKEN
  token_present = "sí" if TOKEN else "no"
  return render_template_string(PRODUCTS_UI_HTML, token_present=token_present, message=None)

# Mostrar lista de productos (proyecta desde la API remota)
@app.route('/productos', methods=['GET'])
def productos_list():
  global TOKEN
  if not TOKEN:
    return redirect(url_for('index'))
  headers = {"Authorization": f"Bearer {TOKEN}"}
  try:
    resp = requests.get(PRODUCTS_ENDPOINT, headers=headers, timeout=8)
    logger.debug('GET productos status=%s', resp.status_code)
    productos = resp.json() if resp.ok else []
  except Exception:
    logger.exception('Error al obtener productos')
    productos = []
  return render_template_string(PRODUCTS_LIST_HTML, productos=productos)

@app.route('/productos/new', methods=['GET'])
def productos_new():
  if not TOKEN:
    return redirect(url_for('index'))
  return render_template_string(PRODUCT_FORM_HTML, title="Crear producto", action=url_for('productos_create'), producto={})

@app.route('/productos/new', methods=['POST'])
def productos_create():
  global TOKEN
  if not TOKEN:
    return redirect(url_for('index'))
  data = {
    "nombre_producto": request.form.get('nombre_producto',''),
    "precio": float(request.form.get('precio') or 0),
    "stock": int(request.form.get('stock') or 0),
    "id_categoria": int(request.form.get('id_categoria') or 0),
    "id_descuento": int(request.form.get('id_descuento') or 0),
    "id_iva": int(request.form.get('id_iva') or 0),
    "id_proveedor": int(request.form.get('id_proveedor') or 0),
  }
  headers = {"Content-Type":"application/json", "Authorization": f"Bearer {TOKEN}"}
  try:
    resp = requests.post(PRODUCTS_ENDPOINT, json=data, headers=headers, timeout=8)
    logger.debug('POST productos status=%s body=%s', resp.status_code, resp.text)
    if resp.ok:
      return redirect(url_for('productos_list'))
    else:
      return render_template_string(PRODUCTS_UI_HTML, token_present="sí", message=f"Error creando producto: {resp.status_code} {resp.text}"), max(400, resp.status_code)
  except Exception:
    logger.exception('Error al crear producto')
    return render_template_string(PRODUCTS_UI_HTML, token_present="sí", message="Error de red al crear producto"), 502

@app.route('/productos/<int:pid>', methods=['GET'])
def productos_view(pid):
  global TOKEN
  if not TOKEN:
    return redirect(url_for('index'))
  headers = {"Authorization": f"Bearer {TOKEN}"}
  try:
    resp = requests.get(f"{PRODUCTS_ENDPOINT}/{pid}", headers=headers, timeout=8)
    producto = resp.json() if resp.ok else None
  except Exception:
    logger.exception('Error al obtener producto')
    producto = None
  return render_template_string(PRODUCT_VIEW_HTML, producto=producto, producto_id=pid)

# Form de edición
@app.route('/productos/<int:pid>/edit', methods=['GET'])
def productos_edit(pid):
  global TOKEN
  if not TOKEN:
    return redirect(url_for('index'))
  headers = {"Authorization": f"Bearer {TOKEN}"}
  try:
    resp = requests.get(f"{PRODUCTS_ENDPOINT}/{pid}", headers=headers, timeout=8)
    producto = resp.json() if resp.ok else {}
  except Exception:
    logger.exception('Error al obtener producto para editar')
    producto = {}
  return render_template_string(PRODUCT_FORM_HTML, title=f"Editar producto {pid}", action=url_for('productos_update', pid=pid), producto=producto)

@app.route('/productos/<int:pid>/edit', methods=['POST'])
def productos_update(pid):
  global TOKEN
  if not TOKEN:
    return redirect(url_for('index'))
  data = {
    "nombre_producto": request.form.get('nombre_producto',''),
    "precio": float(request.form.get('precio') or 0),
    "stock": int(request.form.get('stock') or 0),
    "id_categoria": int(request.form.get('id_categoria') or 0),
    "id_descuento": int(request.form.get('id_descuento') or 0),
    "id_iva": int(request.form.get('id_iva') or 0),
    "id_proveedor": int(request.form.get('id_proveedor') or 0),
  }
  headers = {"Content-Type":"application/json", "Authorization": f"Bearer {TOKEN}"}
  try:
    resp = requests.put(f"{PRODUCTS_ENDPOINT}/{pid}", json=data, headers=headers, timeout=8)
    logger.debug('PUT productos/%s status=%s body=%s', pid, resp.status_code, resp.text)
    if resp.ok:
      return redirect(url_for('productos_view', pid=pid))
    else:
      return render_template_string(PRODUCTS_UI_HTML, token_present="sí", message=f"Error actualizando producto: {resp.status_code} {resp.text}"), max(400, resp.status_code)
  except Exception:
    logger.exception('Error al actualizar producto')
    return render_template_string(PRODUCTS_UI_HTML, token_present="sí", message="Error de red al actualizar producto"), 502

@app.route('/productos/<int:pid>/delete', methods=['POST'])
def productos_delete(pid):
  global TOKEN
  if not TOKEN:
    return redirect(url_for('index'))
  headers = {"Authorization": f"Bearer {TOKEN}"}
  try:
    resp = requests.delete(f"{PRODUCTS_ENDPOINT}/{pid}", headers=headers, timeout=8)
    logger.debug('DELETE productos/%s status=%s', pid, resp.status_code)
    return redirect(url_for('productos_list'))
  except Exception:
    logger.exception('Error al eliminar producto')
    return render_template_string(PRODUCTS_UI_HTML, token_present="sí", message="Error de red al eliminar producto"), 502

# Ruta auxiliar para mostrar formulario rápido de consultar por id
@app.route('/productos/view', methods=['GET'])
def productos_view_form():
  pid = request.args.get('id')
  if not pid:
    return redirect(url_for('productos_ui'))
  try:
    pid_int = int(pid)
  except ValueError:
    return render_template_string(PRODUCTS_UI_HTML, token_present=("sí" if TOKEN else "no"), message="ID inválido")
  return redirect(url_for('productos_view', pid=pid_int))

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
# ...existing code...