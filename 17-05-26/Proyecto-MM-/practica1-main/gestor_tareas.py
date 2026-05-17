import os
from datetime import datetime
from typing import Optional, List, Dict

try:
    from pymongo import MongoClient
    from pymongo.errors import DuplicateKeyError, ConnectionFailure
    from bson.objectid import ObjectId
except Exception:  # pragma: no cover
    MongoClient = None
    DuplicateKeyError = Exception
    ConnectionFailure = Exception
    ObjectId = None


class GestorTareas:
    def __init__(
        self,
        uri: Optional[str] = None,
    ):
        """Inicializar conexión a MongoDB.

        Para que el proyecto "corra" aunque Mongo falle (por ejemplo por red/SSL),
        usamos un modo fallback en memoria.
        """

        self._mem_usuarios: List[Dict] = []

        uri = uri or os.getenv(
            "MONGODB_URI",
            'mongodb+srv://karimeDB:cruzsilvaari091217@clusterkarimecruz.eb4k36a.mongodb.net/?appName=ClusterKarimeCruz',
        )

        self.cliente = None
        self.db = None
        self.tareas = None
        self.usuarios = None

        if MongoClient is None:
            print("⚠️ pymongo no está disponible. Usando modo memoria.")
            return

        try:
            self.cliente = MongoClient(uri, serverSelectionTimeoutMS=5000, tls=True)
            self.cliente.admin.command('ping')
            self.db = self.cliente['gestor_tareas']
            self.tareas = self.db['tareas']
            self.usuarios = self.db['usuarios']
            self._crear_indices()
            print('✅ Conectado a MongoDB')
        except Exception as e:
            print(f"⚠️ No se pudo conectar a MongoDB ({e}). Usando modo memoria.")

    def _crear_indices(self):
        if self.usuarios is None:
            return
        self.usuarios.create_index("email", unique=True)
        self.tareas.create_index([("usuario_id", 1), ("fecha_creacion", -1)])
        self.tareas.create_index("estado")

    def crear_usuario(self, nombre: str, email: str) -> Optional[str]:
        """Crear un nuevo usuario (sin password)."""
        return self.crear_usuario_con_password(nombre, email, password="")

    def crear_usuario_con_password(self, nombre: str, email: str, password: str) -> Optional[str]:
        if self.usuarios is None:
            # modo memoria
            for u in self._mem_usuarios:
                if u.get("email") == email:
                    return None
            self._mem_usuarios.append(
                {"_id": str(len(self._mem_usuarios) + 1), "nombre": nombre, "email": email, "password": password}
            )
            return str(len(self._mem_usuarios))

        try:
            res = self.usuarios.insert_one(
                {
                    "nombre": nombre,
                    "email": email,
                    "password": password,
                    "fecha_registro": datetime.now(),
                    "activo": True,
                }
            )
            return str(res.inserted_id)
        except DuplicateKeyError:
            print(f'❌ Error: El email {email} ya está registrado')
            return None

    def obtener_usuario(self, usuario_id: str) -> Optional[Dict]:
        if self.usuarios is None:
            for u in self._mem_usuarios:
                if str(u.get("_id")) == str(usuario_id):
                    return dict(u)
            return None

        try:
            usuario = self.usuarios.find_one({"_id": ObjectId(usuario_id)})
            if usuario:
                usuario['_id'] = str(usuario['_id'])
            return usuario
        except Exception:
            return None

    def cerrar_conexion(self):
        if getattr(self, 'cliente', None):
            self.cliente.close()
            print('🔌 Conexión cerrada')

    # --- Helpers para que app.py funcione igual en modo memoria ---
    def _find_one_mem(self, query: Dict):
        # soporta solo {"email": ...}
        if "email" in query:
            email = query["email"]
            for u in self._mem_usuarios:
                if u.get("email") == email:
                    return dict(u)
        return None

    # Exponer interfaz compatible
    @property
    def usuarios_proxy(self):
        return self.usuarios


# Monkey-patch simple para que app.py siga usando gestor.usuarios.find_one
# aunque estemos en modo memoria.
class _UsuariosProxy:
    def __init__(self, gestor: GestorTareas):
        self.gestor = gestor

    def find_one(self, query: Dict):
        if self.gestor.usuarios is not None:
            return self.gestor.usuarios.find_one(query)
        return self.gestor._find_one_mem(query)

