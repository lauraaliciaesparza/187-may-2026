from flask import Flask, flash, redirect, render_template, request, session, url_for
from gestor_tareas import GestorTareas

app = Flask(__name__) 
app.secret_key = "mimecita2.0" #La puse para proteger la sesion

gestor = GestorTareas()



@app.route("/")  #Abre la pagina principal
def index():
    return render_template("registro.html")

#Muestra el formulario de registro y procesa los datis enviados por el usuario.
@app.route("/registror", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"] 
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        
        if password !=confirm_password:
            return render_template("registro.html", error="Las contraseñas no coinciden!")
        gestor.crear_usuario(nombre, email, password)
        return redirect("login")
    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        usuario = gestor.usuarios.find_one({"email": email})

        if not usuario :  
            return render_template("login.html", error="Usuario no encontrado")
            
        if "password" not in usuario:
            return render_template("login.html", error="Usuario no tiene contraseña")
        if usuario["password"] == password:
            session["usuario_id"] = str(usuario["_id"])
            return redirect("/login")
        else:
            return render_template("login.html", error="Contraseña incorrecta")

    return render_template("login.html")



@app.route('/cerrarsesion')
def cerrarsesion():
    session.clear()
    flash('Haz cerrado sesion', 'success')
    return redirect(url_for('login'))



if __name__ == "__main__":
    app.run(debug=True)