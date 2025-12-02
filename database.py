import os
import shutil

# Variable para el directorio de datos. Será establecida por main.py
# para asegurar que los datos se guarden junto al ejecutable.
DATA_DIR = None

def set_data_dir(base_path):
    """Establece la ruta del directorio de datos principal."""
    global DATA_DIR
    DATA_DIR = os.path.join(base_path, "client_data")

def initialize_database():
    """Asegura que el directorio de datos principal exista."""
    if DATA_DIR is None:
        raise RuntimeError("El directorio de datos no ha sido inicializado. Llama a set_data_dir() primero.")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_clients():
    """Devuelve una lista con los nombres de todos los clientes (carpetas)."""
    try:
        # Lista solo los directorios dentro de DATA_DIR
        clients = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
        return sorted(clients)
    except FileNotFoundError:
        return []

def add_client(client_name):
    """Añade un nuevo cliente creando su carpeta. Devuelve True si tiene éxito, False si ya existe."""
    client_path = os.path.join(DATA_DIR, client_name)
    if not os.path.exists(client_path):
        os.makedirs(client_path)
        print(f"Carpeta para el cliente '{client_name}' creada en: {client_path}")
        return True
    else:
        print(f"El cliente '{client_name}' ya existe.")
        return False

def delete_client(client_name):
    """Elimina un cliente y todos sus datos (su carpeta)."""
    client_path = os.path.join(DATA_DIR, client_name)
    if os.path.exists(client_path):
        try:
            shutil.rmtree(client_path)
            print(f"Cliente '{client_name}' y todos sus datos han sido eliminados.")
            return True
        except OSError as e:
            print(f"Error al eliminar la carpeta del cliente: {e}")
            return False
    return False

def get_client_documents(client_name, full_path=False):
    """
    Devuelve una lista de archivos .tsv para un cliente específico.
    Si full_path es True, devuelve las rutas completas, si no, solo los nombres de archivo.
    """
    client_path = os.path.join(DATA_DIR, client_name)
    try:
        files = [f for f in os.listdir(client_path) if f.endswith('.tsv')]
        if full_path:
            return [os.path.join(client_path, f) for f in files]
        return sorted(files)
    except FileNotFoundError:
        return []

def add_document_to_client(client_name, source_file_path):
    """Copies a document file to a client's folder."""
    client_path = os.path.join(DATA_DIR, client_name)
    if not os.path.exists(client_path):
        return False # Client does not exist
    
    file_name = os.path.basename(source_file_path)
    destination_path = os.path.join(client_path, file_name)
    shutil.copy(source_file_path, destination_path)
    return True

def delete_client_document(client_name, document_name):
    """Deletes a document file from a client's folder."""
    doc_path = os.path.join(DATA_DIR, client_name, document_name)
    if os.path.exists(doc_path):
        os.remove(doc_path)
        return True
    return False