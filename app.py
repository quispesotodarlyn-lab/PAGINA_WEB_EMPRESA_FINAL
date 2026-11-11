"""Creaciones GMD - Python (Flask) + MySQL de XAMPP. Un HTML por sección en /templates."""
import csv, io, os, random, time, unicodedata, uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
import pymysql
from flask import Flask, jsonify, request, render_template, Response, abort
from flask.json.provider import DefaultJSONProvider
import config

MES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre']


class Prov(DefaultJSONProvider):
    @staticmethod
    def default(o):
        if isinstance(o, (date, datetime)): return o.isoformat()
        if isinstance(o, Decimal): return float(o)
        return DefaultJSONProvider.default(o)


app = Flask(__name__, static_folder="static", static_url_path="")
app.json = Prov(app)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024          # máximo 10 MB por imagen
CARPETA_IMG = os.path.join(app.static_folder, "uploads")      # aquí se guardan las imágenes de las publicaciones
os.makedirs(CARPETA_IMG, exist_ok=True)
EXT_OK = {"jpg", "jpeg", "png", "webp", "gif"}


# ---------- base de datos ----------
def conectar(con_bd=True):
    return pymysql.connect(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER, password=config.DB_PASSWORD,
                           database=config.DB_NAME if con_bd else None, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)


def rows(sql, a=()):
    con = conectar()
    try:
        with con.cursor() as c:
            c.execute(sql, a)
            return list(c.fetchall())
    finally:
        con.close()


def run(sql, a=()):
    con = conectar()
    try:
        with con.cursor() as c:
            c.execute(sql, a)
            i = c.lastrowid
        con.commit()
        return i
    finally:
        con.close()


def iniciar_bd():
    """Crea la base de datos y las tablas VACÍAS. Si encuentra la estructura vieja (de pruebas), la reemplaza."""
    ultimo = None
    for puerto in dict.fromkeys([config.DB_PORT, 3306, 3307, 3308]):   # prueba los puertos más comunes de XAMPP
        try:
            config.DB_PORT = puerto
            con = conectar(False)
            break
        except pymysql.err.OperationalError as e:
            ultimo = e
    else:
        raise ultimo
    with con.cursor() as c:
        c.execute("SELECT COUNT(*) n FROM information_schema.columns WHERE table_schema=%s AND table_name='clientes' AND column_name IN ('creado','correo')", (config.DB_NAME,))
        if c.fetchone()["n"]:
            print("Actualizando la base de datos a la versión nueva (se reemplaza la estructura anterior de pruebas)...")
            c.execute(f"DROP DATABASE `{config.DB_NAME}`")
        for s in [x.strip() for x in open("schema.sql", encoding="utf-8").read().split(";") if x.strip()]:
            c.execute(s)
        c.execute("SELECT COUNT(*) n FROM information_schema.columns WHERE table_schema=%s AND table_name='publicaciones' AND column_name='imagen'", (config.DB_NAME,))
        if not c.fetchone()["n"]:   # versión anterior: publicaciones sin imagen
            c.execute(f"ALTER TABLE `{config.DB_NAME}`.publicaciones ADD COLUMN imagen VARCHAR(255) NOT NULL DEFAULT '' AFTER id, DROP COLUMN titulo, MODIFY descripcion VARCHAR(300)")
    con.commit()
    con.close()


def log(icono, color, texto, detalle=""):
    run("INSERT INTO actividades (icono,color,texto,detalle,ts) VALUES (%s,%s,%s,%s,%s)", (icono, color, texto, detalle, int(time.time() * 1000)))


def norm(s):
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()


def num(v):
    try: return float(str(v).replace(",", "."))
    except ValueError: return 0.0


@app.errorhandler(Exception)
def error(e):
    if request.path.startswith("/api"):
        code = getattr(e, "code", 500)
        return jsonify(error=str(getattr(e, "description", e))), (code if isinstance(code, int) else 500)
    raise e


# ---------- páginas (un HTML por sección) ----------
for ruta, plantilla in [("/", "inicio"), ("/publicaciones", "publicaciones"), ("/clientes", "clientes"), ("/pedidos", "pedidos"),
                        ("/materiales", "materiales"), ("/reportes", "reportes"), ("/configuracion", "configuracion"),
                        ("/buscar", "buscar"), ("/consulta", "consulta")]:
    app.add_url_rule(ruta, "pagina_" + plantilla, (lambda p: lambda: render_template(p + ".html", activa=p))(plantilla))

PED = """SELECT p.id,p.cliente_id,c.nombre cliente,c.telefono,p.material,p.ancho,p.alto,p.precio,p.fecha,p.estado
         FROM pedidos p JOIN clientes c ON c.id=p.cliente_id"""
ORD = " ORDER BY p.fecha DESC, p.id DESC"


# ---------- clientes ----------
@app.get("/api/clientes")
def clientes_lista():
    return jsonify(rows("""SELECT c.id, c.nombre, c.telefono, COUNT(p.id) pedidos, COALESCE(SUM(p.precio),0) total, MAX(p.fecha) ultima
                           FROM clientes c LEFT JOIN pedidos p ON p.cliente_id=c.id GROUP BY c.id ORDER BY total DESC"""))


@app.get("/api/clientes/<int:i>")
def cliente_uno(i):
    c = rows("SELECT * FROM clientes WHERE id=%s", (i,))
    if not c: return jsonify(error="No existe"), 404
    return jsonify(cliente=c[0], pedidos=rows(PED + " WHERE p.cliente_id=%s" + ORD, (i,)))


@app.put("/api/clientes/<int:i>")
def cliente_editar(i):
    d = request.get_json(force=True)
    run("UPDATE clientes SET nombre=%s, telefono=%s WHERE id=%s", (d["nombre"].strip(), d.get("telefono", ""), i))
    return jsonify(ok=True)


@app.delete("/api/clientes/<int:i>")
def cliente_borrar(i):
    if rows("SELECT COUNT(*) n FROM pedidos WHERE cliente_id=%s", (i,))[0]["n"]:
        return jsonify(error="El cliente tiene pedidos: no se puede eliminar"), 409
    run("DELETE FROM clientes WHERE id=%s", (i,))
    return jsonify(ok=True)


# ---------- pedidos: la compra se guarda con el ID del cliente y la fecha de hoy ----------
def cliente_id(nombre, telefono):
    """Devuelve el ID del cliente; si no existe lo crea. Si ya existe y se escribió teléfono, lo actualiza."""
    c = rows("SELECT id FROM clientes WHERE nombre=%s", (nombre,))
    if c:
        if telefono: run("UPDATE clientes SET telefono=%s WHERE id=%s", (telefono, c[0]["id"]))
        return c[0]["id"]
    log("👥", "#1a7dff", "Se registró un nuevo cliente", nombre)
    return run("INSERT INTO clientes (nombre,telefono) VALUES (%s,%s)", (nombre, telefono))


def datos_pedido(d):
    nombre = d.get("cliente", "").strip()
    if not nombre: raise ValueError("Falta el nombre del cliente")
    mat = d.get("material", "").strip()
    if mat: run("INSERT IGNORE INTO materiales (nombre) VALUES (%s)", (mat,))
    return cliente_id(nombre, d.get("telefono", "").strip()), mat, num(d.get("ancho")), num(d.get("alto")), num(d.get("precio")), nombre


@app.get("/api/pedidos")
def pedidos_lista():
    w, a = [], []
    for campo, sql in [("desde", "p.fecha>=%s"), ("hasta", "p.fecha<=%s"), ("estado", "p.estado=%s"), ("material", "p.material=%s")]:
        if request.args.get(campo):
            w.append(sql); a.append(request.args[campo])
    return jsonify(rows(PED + (" WHERE " + " AND ".join(w) if w else "") + ORD, a))


@app.get("/api/pedidos/<int:i>")
def pedido_uno(i):
    r = rows(PED + " WHERE p.id=%s", (i,))
    return jsonify(r[0]) if r else (jsonify(error="No existe"), 404)


@app.post("/api/pedidos")
def pedido_nuevo():
    cid, mat, an, al, pr, nombre = datos_pedido(request.get_json(force=True))
    i = run("INSERT INTO pedidos (cliente_id,material,ancho,alto,precio,fecha) VALUES (%s,%s,%s,%s,%s,CURDATE())", (cid, mat, an, al, pr))
    log("🛒", "#ff8a1a", f"Nuevo pedido #{i:04d}", nombre)
    return jsonify(id=i)


@app.put("/api/pedidos/<int:i>")
def pedido_editar(i):
    cid, mat, an, al, pr, nombre = datos_pedido(request.get_json(force=True))
    run("UPDATE pedidos SET cliente_id=%s,material=%s,ancho=%s,alto=%s,precio=%s WHERE id=%s", (cid, mat, an, al, pr, i))
    log("✏️", "#1a7dff", f"Se editó el pedido #{i:04d}", nombre)
    return jsonify(ok=True)


@app.post("/api/pedidos/<int:i>/estado")
def pedido_estado(i):
    run("UPDATE pedidos SET estado=IF(estado='C','P','C') WHERE id=%s", (i,))
    p = rows(PED + " WHERE p.id=%s", (i,))[0]
    log("✔" if p["estado"] == "C" else "🔄", "#18c866", f"Pedido #{i:04d} " + ("completada" if p["estado"] == "C" else "en proceso"), p["cliente"])
    return jsonify(ok=True)


@app.delete("/api/pedidos/<int:i>")
def pedido_borrar(i):
    run("DELETE FROM pedidos WHERE id=%s", (i,))
    return jsonify(ok=True)


# ---------- materiales y publicaciones ----------
@app.get("/api/materiales")
def materiales_lista():
    return jsonify(rows("SELECT m.*, (SELECT COUNT(*) FROM pedidos o WHERE o.material=m.nombre) pedidos FROM materiales m ORDER BY nombre"))


@app.post("/api/materiales")
def material_nuevo():
    n = request.get_json(force=True)["nombre"].strip()
    if not n: return jsonify(error="Falta el nombre"), 400
    run("INSERT IGNORE INTO materiales (nombre) VALUES (%s)", (n,))
    log("🏷", "#18c866", "Se agregó un material", n)
    return jsonify(ok=True)


@app.delete("/api/materiales/<int:i>")
def material_borrar(i):
    run("DELETE FROM materiales WHERE id=%s", (i,))
    return jsonify(ok=True)


def guardar_imagen(f):
    if not f or not f.filename: return None
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in EXT_OK: abort(400, "La imagen debe ser JPG, PNG, WEBP o GIF")
    nombre = uuid.uuid4().hex + "." + ext
    f.save(os.path.join(CARPETA_IMG, nombre))
    return nombre


def borrar_imagen(nombre):
    try: os.remove(os.path.join(CARPETA_IMG, nombre))
    except OSError: pass


@app.get("/api/publicaciones")
def pubs_lista():
    return jsonify(rows("SELECT * FROM publicaciones ORDER BY fecha DESC, id DESC"))


@app.post("/api/publicaciones")
def pub_nueva():
    img = guardar_imagen(request.files.get("imagen"))
    if not img: abort(400, "Elige una imagen")
    d = request.form.get("descripcion", "").strip()[:300]
    run("INSERT INTO publicaciones (imagen,descripcion,fecha,estado) VALUES (%s,%s,CURDATE(),%s)", (img, d, request.form.get("estado", "Publicada")))
    log("📣", "#ff2fa8", "Se creó una nueva publicación", d[:40])
    return jsonify(ok=True)


@app.put("/api/publicaciones/<int:i>")
def pub_editar(i):
    img = guardar_imagen(request.files.get("imagen"))
    d = request.form.get("descripcion", "").strip()[:300]
    if img:
        viejo = rows("SELECT imagen FROM publicaciones WHERE id=%s", (i,))
        run("UPDATE publicaciones SET imagen=%s WHERE id=%s", (img, i))
        if viejo: borrar_imagen(viejo[0]["imagen"])
    run("UPDATE publicaciones SET descripcion=%s, estado=%s WHERE id=%s", (d, request.form.get("estado", "Publicada"), i))
    return jsonify(ok=True)


@app.delete("/api/publicaciones/<int:i>")
def pub_borrar(i):
    viejo = rows("SELECT imagen FROM publicaciones WHERE id=%s", (i,))
    run("DELETE FROM publicaciones WHERE id=%s", (i,))
    if viejo: borrar_imagen(viejo[0]["imagen"])
    return jsonify(ok=True)


@app.get("/api/actividades")
def actividades():
    return jsonify(rows("SELECT icono i,color col,texto t,detalle s,ts FROM actividades ORDER BY id DESC LIMIT %s", (int(request.args.get("limite", 20)),)))


# ---------- inicio ----------
@app.get("/api/dashboard")
def dashboard():
    N = 30 if request.args.get("dias") == "30" else 7
    hoy = date.today()
    ym = hoy.strftime("%Y-%m")
    ped = rows("SELECT material,precio,fecha,estado FROM pedidos")
    por_mat, total, previo = {}, 0, 0
    for o in ped:
        a = (hoy - o["fecha"]).days
        if a < 0: continue
        if a < N:
            total += float(o["precio"])
            s = por_mat.setdefault(o["material"] or "Sin material", [0] * 7)
            s[6 - (a * 7 // N)] += float(o["precio"])
        elif a < 2 * N:
            previo += float(o["precio"])
    top = sorted(por_mat.items(), key=lambda x: -sum(x[1]))[:5]
    mes = [o for o in ped if o["fecha"].strftime("%Y-%m") == ym]
    return jsonify(
        publicaciones=rows("SELECT COUNT(*) n FROM publicaciones")[0]["n"], clientes=rows("SELECT COUNT(*) n FROM clientes")[0]["n"],
        proceso=sum(o["estado"] == "P" for o in ped), completados=sum(o["estado"] == "C" for o in ped),
        mes_pub=rows("SELECT COUNT(*) n FROM publicaciones WHERE DATE_FORMAT(fecha,'%%Y-%%m')=%s", (ym,))[0]["n"],
        mes_cli=rows("SELECT COUNT(*) n FROM (SELECT MIN(fecha) f FROM pedidos GROUP BY cliente_id) t WHERE DATE_FORMAT(f,'%%Y-%%m')=%s", (ym,))[0]["n"],
        mes_proceso=sum(o["estado"] == "P" for o in mes), mes_completados=sum(o["estado"] == "C" for o in mes),
        total=total, previo=previo, series=[{"n": k, "v": v} for k, v in top],
        etiquetas=[(hoy - timedelta(days=(6 - i) * N // 7)).strftime("%d/%m") for i in range(7)],
        recientes=rows(PED + ORD + " LIMIT 8"),
        destacados=rows("SELECT c.id,c.nombre,COUNT(p.id) pedidos FROM clientes c JOIN pedidos p ON p.cliente_id=c.id GROUP BY c.id ORDER BY pedidos DESC LIMIT 5"),
        actividades=rows("SELECT icono i,color col,texto t,detalle s,ts FROM actividades ORDER BY id DESC LIMIT 4"))


# ---------- búsqueda general y consulta de cliente ----------
def buscar(q):
    toks = norm(q).split()
    ped, cli = [], []
    for o in rows(PED + ORD):
        f = o["fecha"]
        hay = norm(" ".join([o["cliente"], o["telefono"] or "", o["material"] or "", f.strftime("%d/%m/%Y"), str(f), MES[f.month - 1], str(f.year),
                             f"{float(o['ancho']):g}x{float(o['alto']):g}", f"{float(o['ancho']):g} x {float(o['alto']):g}", f"#{o['id']:04d}",
                             "completado" if o["estado"] == "C" else "en proceso"]))
        if all(t in hay for t in toks): ped.append(o)
    for c in rows("SELECT * FROM clientes"):
        if all(t in norm(c["nombre"] + " " + (c["telefono"] or "")) for t in toks): cli.append(c)
    return ped, cli


@app.get("/api/buscar")
def api_buscar():
    ped, cli = buscar(request.args.get("q", ""))
    return jsonify(pedidos=ped, clientes=cli)


def consultar():
    nombre, desde, hasta = request.args.get("nombre", "").strip(), request.args.get("desde", ""), request.args.get("hasta", "")
    w, a = [], []
    if nombre: w.append("c.nombre LIKE %s"); a.append(f"%{nombre}%")
    if desde and not hasta: w.append("p.fecha=%s"); a.append(desde)          # solo una fecha = ese día
    if desde and hasta: w.append("p.fecha BETWEEN %s AND %s"); a.extend([desde, hasta])
    if hasta and not desde: w.append("p.fecha<=%s"); a.append(hasta)
    return rows(PED + (" WHERE " + " AND ".join(w) if w else "") + ORD, a)


@app.get("/api/consulta")
def api_consulta():
    return jsonify(consultar())


# ---------- reportes ----------
@app.get("/api/reportes")
def reportes():
    anio = int(request.args.get("anio", date.today().year))
    m = {r["m"]: r for r in rows("""SELECT MONTH(fecha) m, COUNT(*) n, SUM(precio) v, SUM(CASE WHEN estado='C' THEN precio ELSE 0 END) c
                                    FROM pedidos WHERE YEAR(fecha)=%s GROUP BY MONTH(fecha)""", (anio,))}
    mensual = [{"mes": MES[i], "pedidos": int(m[i + 1]["n"]) if i + 1 in m else 0, "ventas": float(m[i + 1]["v"]) if i + 1 in m else 0,
                "cobrado": float(m[i + 1]["c"]) if i + 1 in m else 0} for i in range(12)]
    anual = rows("SELECT YEAR(fecha) anio, COUNT(*) pedidos, SUM(precio) ventas FROM pedidos GROUP BY YEAR(fecha) ORDER BY anio")
    anios = sorted({a["anio"] for a in anual} | {date.today().year}, reverse=True)
    mats = rows("SELECT COALESCE(NULLIF(material,''),'Sin material') material, COUNT(*) pedidos, SUM(precio) ventas FROM pedidos WHERE YEAR(fecha)=%s GROUP BY 1", (anio,))
    return jsonify(anio=anio, anios=anios, mensual=mensual, anual=anual, materiales=mats)


# ---------- CSV ----------
def csv_resp(filas, nombre):
    s = io.StringIO()
    csv.writer(s).writerows(filas)
    return Response("\ufeff" + s.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename={nombre}"})


def filas_pedidos(L):
    r = [["N° pedido", "Fecha de compra", "Año", "Mes", "Cliente", "Teléfono", "Tipo de material", "Ancho (m)", "Alto (m)", "Área (m²)", "Precio (S/)", "Estado"]]
    for o in L:
        r.append([f"{o['id']:04d}", o["fecha"].strftime("%d/%m/%Y"), o["fecha"].year, MES[o["fecha"].month - 1], o["cliente"], o["telefono"], o["material"],
                  o["ancho"], o["alto"], round(float(o["ancho"] * o["alto"]), 2), o["precio"], "Completado" if o["estado"] == "C" else "En proceso"])
    return r


@app.get("/api/csv/<tipo>")
def csv_descarga(tipo):
    if tipo == "pedidos": return csv_resp(filas_pedidos(rows(PED + ORD)), "pedidos-gmd.csv")
    if tipo == "buscar": return csv_resp(filas_pedidos(buscar(request.args.get("q", ""))[0]), "busqueda-gmd.csv")
    if tipo == "consulta": return csv_resp(filas_pedidos(consultar()), "consulta-cliente-gmd.csv")
    if tipo == "cliente": return csv_resp(filas_pedidos(rows(PED + " WHERE p.cliente_id=%s" + ORD, (request.args.get("id"),))), "cliente-gmd.csv")
    if tipo == "clientes":
        r = [["ID", "Cliente", "Teléfono", "Pedidos", "Total comprado (S/)", "Última compra"]]
        for c in rows("SELECT c.id,c.nombre,c.telefono,COUNT(p.id) n,COALESCE(SUM(p.precio),0) t,MAX(p.fecha) u FROM clientes c LEFT JOIN pedidos p ON p.cliente_id=c.id GROUP BY c.id"):
            r.append([c["id"], c["nombre"], c["telefono"], c["n"], c["t"], c["u"].strftime("%d/%m/%Y") if c["u"] else ""])
        return csv_resp(r, "clientes-gmd.csv")
    if tipo == "mensual":
        r = [["Año", "Mes", "Pedidos", "Ventas (S/)", "Cobrado completados (S/)"]]
        for x in rows("""SELECT YEAR(fecha) a, MONTH(fecha) m, COUNT(*) n, SUM(precio) v, SUM(CASE WHEN estado='C' THEN precio ELSE 0 END) c
                         FROM pedidos GROUP BY YEAR(fecha), MONTH(fecha) ORDER BY a, m"""):
            r.append([x["a"], MES[x["m"] - 1], x["n"], x["v"], x["c"]])
        return csv_resp(r, "ganancias-por-mes-gmd.csv")
    if tipo == "anual":
        r = [["Año", "Pedidos", "Ventas (S/)"]] + [[x["a"], x["n"], x["v"]] for x in rows("SELECT YEAR(fecha) a, COUNT(*) n, SUM(precio) v FROM pedidos GROUP BY YEAR(fecha) ORDER BY a")]
        return csv_resp(r, "ganancias-por-anio-gmd.csv")
    return jsonify(error="Tipo desconocido"), 404


# ---------- datos de ejemplo / borrar ----------
@app.post("/api/borrar")
def borrar():
    for p in rows("SELECT imagen FROM publicaciones"): borrar_imagen(p["imagen"])
    for t in ["pedidos", "clientes", "publicaciones", "actividades"]: run(f"DELETE FROM {t}")
    return jsonify(ok=True)


@app.post("/api/demo")
def demo():
    borrar()
    r = random.Random(42)
    hoy = date.today()
    nombres = ["Empresa ABC", "Juan Pérez", "Maribel Torres", "Taller Sol", "Luis García", "Patricia Rojas", "Carlos Mendoza", "DecoPrint", "Ana Quispe",
               "Bodega Don Pepe", "Farmacia Salud", "Colegio Los Andes", "Pollería El Sabor", "Gym Titan", "Inmobiliaria Lima", "Café Aroma", "Ferretería Central", "Boutique Luna"]
    ids = [run("INSERT INTO clientes (nombre,telefono) VALUES (%s,%s)", (n, "9" + str(r.randint(10000000, 99999999)))) for n in nombres]
    mats = {"Banner 13oz": 25, "Lona frontlight": 18, "Vinil adhesivo": 22, "Sticker troquelado": 30, "Canvas": 35, "Sintra": 40}
    for m in mats: run("INSERT IGNORE INTO materiales (nombre) VALUES (%s)", (m,))
    for k in range(80):
        m = r.choice(list(mats)); z = r.choice([(1, 1), (2, 1), (3, 1), (2, 2), (3, 2), (4, 2), (6, 3), (1.5, 1)])
        age = r.randint(0, 25 if k < 12 else 660)
        run("INSERT INTO pedidos (cliente_id,material,ancho,alto,precio,fecha,estado) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (r.choice(ids), m, z[0], z[1], round(z[0] * z[1] * mats[m], 2), hoy - timedelta(days=age), "P" if age < 18 and r.random() < .6 else "C"))
    log("🏷", "#18c866", "Se cargaron datos de ejemplo")
    return jsonify(ok=True)


if __name__ == "__main__":
    try:
        iniciar_bd()
    except pymysql.err.OperationalError as e:
        raise SystemExit(f"\nNO SE PUDO CONECTAR A MYSQL.\nDetalle técnico: {e}\n\n1) En XAMPP, MySQL debe estar en verde (Start).\n2) Revisa usuario/clave/puerto en config.py (root, sin clave, 3306).\n3) Si MySQL se apaga solo, otro programa usa el puerto 3306.\n")
    print(f"Sistema listo: http://localhost:{config.APP_PORT}")
    app.run(host=config.APP_HOST, port=config.APP_PORT)
