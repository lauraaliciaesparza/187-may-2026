from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from self import self

class GestorLabiales:
    def __init__(self, uri: str = 'mongodb+srv://karimeDB:cruzsilvaari091217@clusterkarimecruz.eb4k36a.mongodb.net/?appName=ClusterKarimeCruz'):
        try:
            self.cliente = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.cliente.admin.command('ping')
            self.db = self.cliente['gestor_laiales']
            self.tareas = self.db['labiales']
            self.usuarios = self.db['usuarios']
            
            # Crear índices necesarios
            self._crear_indices()
            print("✅ Conectado a MongoDB")
        except ConnectionFailure:
            print("❌ Error: No se pudo conectar a MongoDB")
            raise
    
    def _crear_indices(self):
        """Crear índices para mejorar rendimiento"""
        self.usuarios.create_index("email", unique=True)
        self.tareas.create_index("usuario_id")
        self.tareas.create_index("color")
        
    def agregar_labial(self, usuario_id: str, nombre: str, color: str, precio: float) -> Optional[str]:
        """Agregar un nuevo labial para un usuario"""
        if not self.obtener_usuario(usuario_id):
            print(f"❌ Error: Usuario {usuario_id} no existe")
            return None
        
        labial = {
            "usuario_id": ObjectId(usuario_id),
            "nombre": nombre,
            "color": color,
            "precio": precio,
            "stock": 10,
            "fecha_registro": datetime.now(),
            "vendido": False
                }
        resultado = self.labiales.insert_one(labial)
        return str(resultado.inserted_id)
    
    def obtener_labiales_usuario(self, usuario_id: str) -> list[Dict]:
        """Obtener labiales por ID"""
        labiales = self.labiales.find({"_id": ObjectId(usuario_id)})
        resultado = []
        for labiales in labiales:
            labiales['_id'] = str(labiales['_id'])
            labiales['usuario_id'] = str(labiales['usuario_id'])
            resultado.append(labiales)
            return resultado 
        except Exception as e:
        print(f"Error al obtener labiales: {e}")
        return None
        
    def vender_labial(self, labial_id: str, cantidad: int = 1) -> bool:
        resultado = self.labiales.update_one(
            {"_id": ObjectId(labial_id)},
            {"$inc": {"stock": -cantidad}, "$set": {"vendido": True, "fecha_venta": datetime.now()}}
        )
        return resultado.modified_count > 0
    
    def marcar_como_vendido(self, labial_id: str) -> bool:
            resultado = self.labiales.update_one(
                {"_id": ObjectId(labial_id)},
                {"$set": {"vendido": True, "fecha_venta": datetime.now()}}
            )
            return resultado.modified_count > 0
        
    def crear_usuario(self, nombre: str, email: str, password: str) -> Optional[str]:
        """Crear un nuevo usuario"""
        try:
            resultado = self.usuarios.insert_one({
                "nombre": nombre,
                "email": email,
                "password": password,
                "fecha_registro": datetime.now(),
                "activo": True
            })
            
            return str(resultado.inserted_id)
        except DuplicateKeyError:
            print(f"❌ Error: El email {email} ya está registrado")
            return None

    def crear_tarea(self, usuario_id: str, titulo: str, descripcion: str = "", 
                    fecha_limite: Optional[datetime] = None) -> Optional[str]:
        """Crear una nueva tarea para un usuario"""
        # Verificar que el usuario existe
        if not self.obtener_usuario(usuario_id):
            print(f"❌ Error: Usuario {usuario_id} no existe")
            return None
        tarea = {
            "usuario_id": ObjectId(usuario_id),
            "titulo": titulo,
            "descripcion": descripcion,
            "estado": "pendiente",
            "fecha_creacion": datetime.now(),
            "fecha_limite": fecha_limite or datetime.now() + timedelta(days=7),
            "completada": False,
            "etiquetas": []
        }
        
        resultado = self.tareas.insert_one(tarea)
        return str(resultado.inserted_id)
    
    def obtener_labiales_usuario(self, usuario_id: str, estado: Optional[str] = None) -> List[Dict]:
        """Obtener tareas de un usuario, opcionalmente filtradas por estado"""
        filtro = {"usuario_id": ObjectId(usuario_id)}
        if estado:
            filtro["estado"] = estado
        
        tareas = self.tareas.find(filtro).sort("fecha_creacion", -1)
        resultado = []
        for t in tareas:
            t['_id'] = str(t['_id'])
            t['usuario_id'] = str(t['usuario_id'])
            resultado.append(t)
        return resultado
    
    def actualizar_estado_tarea(self, tarea_id: str, nuevo_estado: str) -> bool:
        """Actualizar el estado de una tarea"""
        estados_validos = ["pendiente", "en_progreso", "completada", "cancelada"]
        if nuevo_estado not in estados_validos:
            print(f"❌ Error: Estado '{nuevo_estado}' no válido")
            return False
        
        resultado = self.tareas.update_one(
            {"_id": ObjectId(tarea_id)},
            {
                "$set": {
                    "estado": nuevo_estado,
                    "completada": nuevo_estado == "completada",
                    "fecha_actualizacion": datetime.now()
                }
            }
        )
        return resultado.modified_count > 0
    
    def agregar_etiqueta(self, tarea_id: str, etiqueta: str) -> bool:
        """Agregar etiqueta a una tarea"""
        resultado = self.tareas.update_one(
            {"_id": ObjectId(tarea_id)},
            {"$addToSet": {"etiquetas": etiqueta}}
        )
        return resultado.modified_count > 0
    
    def eliminar_tarea(self, tarea_id: str) -> bool:
        """Eliminar una tarea"""
        resultado = self.tareas.delete_one({"_id": ObjectId(tarea_id)})
        return resultado.deleted_count > 0
    
    def estadisticas_usuario(self, usuario_id: str) -> Dict:
        """Obtener estadísticas de tareas de un usuario"""
        pipeline = [
            {"$match": {"usuario_id": ObjectId(usuario_id)}},
            {"$group": {
                "_id": "$estado",
                "cantidad": {"$sum": 1},
                "fecha_ultima": {"$max": "$fecha_creacion"}
            }},
            {"$sort": {"_id": 1}}
        ]
        resultados = list(self.tareas.aggregate(pipeline))
        
        # Formatear resultados
        estadisticas = {
            "total": 0,
            "por_estado": {},
            "ultima_actividad": None
        }
        
        for r in resultados:
            estado = r['_id']
            cantidad = r['cantidad']
            estadisticas["por_estado"][estado] = cantidad
            estadisticas["total"] += cantidad
            
            if not estadisticas["ultima_actividad"] or r['fecha_ultima'] > estadisticas["ultima_actividad"]:
                estadisticas["ultima_actividad"] = r['fecha_ultima']
        
        return estadisticas
    
    def buscar_labiales(self, texto: str) -> List[Dict]:
        tareas = self.tareas.find({
            "$text": {"$search": texto}
        }).sort({"score": {"$meta": "textScore"}})
        
        resultado = []
        for t in tareas:
            t['_id'] = str(t['_id'])
            t['usuario_id'] = str(t['usuario_id'])
            resultado.append(t)
            return resultado
        tareas = self.tareas.find({
        "estado": {"$ne": "completada"},
        "fecha_limite": {"$gte": "ahora", "$lte": "limite"}}).sort("fecha_limite", 1)
        resultado = []
        for t in tareas:
            t['_id'] = str(t['_id'])
            t['usuario_id'] = str(t['usuario_id'])
            resultado.append(t)
        return resultado

def cerrar_conexion(self):
        """Cerrar conexión a MongoDB"""
        if self.cliente:
            self.cliente.close()
            print("🔌 Conexión cerrada")

# Ejemplo de uso
def ejemplo_uso():
    # Inicializar gestor
    gestor = GestorLabiales()
    
    # Crear usuario
    usuario_id = gestor.crear_usuario("Karime Cruz", "karimearisbelcruzsilva2@email.com", "1234")
    print(f"Usuario creado con ID: {usuario_id}")
    
    if usuario_id:
        laibal_id =gestor.agregar_labial(usuario_id, "Labial Rojo", "Rojo intenso", 15.99)
        print(f"Labial agregado con ID: {labial_id}")
        
        lista_Laviales = gestor.obteber_labiales_usuario(usuario_id)
        print(f"Labiales de {usuario_id}:")
        for l in lista_Laviales:
            print(f" - {l['nombre']} ({l['color']}) - ${l['precio']} stock: {l['stock']}" )
        
        # Tareas urgentes vender
        vendido = gestor.vender_labial(labial_id, cantidad=2)
        print(f"Venta realzada: {vendido}")
    
    # Cerrar conexión
    gestor.cerrar_conexion()


if __name__ == "__main__":
    ejemplo_uso()


if __name__ == "__main__":
    main()