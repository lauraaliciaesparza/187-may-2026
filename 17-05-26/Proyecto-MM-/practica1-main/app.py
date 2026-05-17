from flask import Flask, flash, redirect, render_template, request, session, url_for

from gestor_tareas import GestorTareas, _UsuariosProxy

app = Flask(__name__)
app.secret_key = "mimecita2.0"  # La puse para proteger la sesión

gestor = GestorTareas()

# Asegura que exista gestor.usuarios.find_one aunque Mongo falle
if getattr(gestor, "usuarios", None) is None:
    gestor.usuarios = _UsuariosProxy(gestor)


@app.route("/")
def index():
    if session.get("usuario_id"):
        return redirect(url_for("dashboard"))
    return render_template("registro.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("usuario_id"):
        return redirect(url_for("login"))

    return (
        "<h1>Bienvenido</h1>"
        f"<p>Usuario ID: {session.get('usuario_id')}</p>"
        f"<a href='{url_for('cerrarsesion')}'>Cerrar sesión</a>"
    )


@app.route("/registrar", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template("registro.html", error="Las contraseñas no coinciden!")

        gestor.crear_usuario_con_password(nombre, email, password)
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        usuario = gestor.usuarios.find_one({"email": email})

        if not usuario:
            return render_template("login.html", error="Usuario no encontrado")

        if "password" not in usuario:
            return render_template("login.html", error="Usuario no tiene contraseña")

        if usuario["password"] == password:
            session["usuario_id"] = str(usuario["_id"])
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Contraseña incorrecta")

    return render_template("login.html")


@app.route("/cerrarsesion")
def cerrarsesion():
    session.clear()
    flash("Haz cerrado sesión", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)

