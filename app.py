from flask import Flask, request, render_template, redirect, url_for
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
app = Flask(__name__, template_folder="templates")

# Variable global simple para guardar el token del usuario logueado (por simplicity)
TOKEN = None

# Lista corta de memes públicos (URLs directas) - usados para errores leves
MEMES = [
  "https://i.imgflip.com/30b1gx.jpg",
  "https://i.imgflip.com/1bij.jpg",
  "https://i.imgflip.com/3si4.jpg",
]

@app.route('/', methods=['GET'])
def index():
  return render_template('login.html', message=None)

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
    return render_template('login.html', message="Error de red al iniciar sesión. Intenta más tarde."), 502

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
    # login fallido: mostrar mensaje de error y no permitir entrar
    try:
      detail = resp.json().get('message') or resp.json().get('detail')
    except Exception:
      detail = resp.text or ''
    msg = f"Autenticación fallida ({resp.status_code}). {detail}"
    return render_template('login.html', message=msg), max(400, resp.status_code)

@app.route('/register', methods=['GET'])
def register():
  return render_template('register.html', message=None)

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
    return render_template('register.html', message=message), 502

  if resp.ok:
    try:
      body = resp.json()
      server_msg = body.get('message') or body.get('detail') or str(body)
    except Exception:
      server_msg = resp.text or 'Registro exitoso.'
    message = f"Registro satisfactorio. {server_msg}"
    # llevar al login con mensaje
    return render_template('login.html', message=message), 200
  else:
    try:
      body = resp.json()
      server_msg = body.get('message') or body.get('detail') or str(body)
    except Exception:
      server_msg = resp.text or 'Error en el registro.'
    message = f"Registro fallido ({resp.status_code}). {server_msg}"
    return render_template('register.html', message=message), max(400, resp.status_code)

@app.route('/productos_ui', methods=['GET'])
def productos_ui():
  global TOKEN
  token_present = "sí" if TOKEN else "no"
  return render_template('products_ui.html', token_present=token_present, message=None)

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
  return render_template('products_list.html', productos=productos)

@app.route('/productos/new', methods=['GET'])
def productos_new():
  global TOKEN
  if not TOKEN:
    return redirect(url_for('index'))
  return render_template('product_form.html', title="Crear producto", action=url_for('productos_create'), producto={})

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
      return render_template('products_ui.html', token_present="sí", message=f"Error creando producto: {resp.status_code} {resp.text}"), max(400, resp.status_code)
  except Exception:
    logger.exception('Error al crear producto')
    return render_template('products_ui.html', token_present="sí", message="Error de red al crear producto"), 502

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
  return render_template('product_view.html', producto=producto, producto_id=pid)

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
  return render_template('product_form.html', title=f"Editar producto {pid}", action=url_for('productos_update', pid=pid), producto=producto)

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
      return render_template('products_ui.html', token_present="sí", message=f"Error actualizando producto: {resp.status_code} {resp.text}"), max(400, resp.status_code)
  except Exception:
    logger.exception('Error al actualizar producto')
    return render_template('products_ui.html', token_present="sí", message="Error de red al actualizar producto"), 502

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
    return render_template('products_ui.html', token_present="sí", message="Error de red al eliminar producto"), 502

# Ruta auxiliar para mostrar formulario rápido de consultar por id
@app.route('/productos/view', methods=['GET'])
def productos_view_form():
  pid = request.args.get('id')
  if not pid:
    return redirect(url_for('productos_ui'))
  try:
    pid_int = int(pid)
  except ValueError:
    return render_template('products_ui.html', token_present=("sí" if TOKEN else "no"), message="ID inválido")
  return redirect(url_for('productos_view', pid=pid_int))

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)