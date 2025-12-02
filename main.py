import customtkinter
import database as db # Importamos nuestro nuevo módulo de base de datos
import analysis as an # Importamos nuestro nuevo módulo de análisis
import report_generator as rg # Importamos el generador de reportes
import os
import sys, json # Importamos sys para la detección del entorno
import shutil
import ast
from datetime import datetime, timedelta
from tkinter import ttk # Necesario para el widget Treeview (tabla)
from tkinter import messagebox, filedialog
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import LinearSegmentedColormap
import openpyxl # Importación explícita para que PyInstaller lo incluya

def get_app_path():
    """
    Determina la ruta base para la aplicación.
    Si está "congelada" (ejecutable), usa la ruta del .exe.
    Si no, usa la ruta del script .py.
    Esto asegura que los datos se guarden junto al ejecutable.
    """
    if getattr(sys, 'frozen', False):
        # Estamos corriendo en un bundle de PyInstaller (congelado)
        application_path = os.path.dirname(sys.executable)
    else:
        # Estamos corriendo en un entorno de desarrollo normal
        application_path = os.path.dirname(os.path.abspath(__file__))
    return application_path

# --- Configuración de la Apariencia ---
# Establece el tema de la aplicación (System, Dark, Light)
customtkinter.set_appearance_mode("System")  
# Establece el color por defecto de los widgets (blue, dark-blue, green)
customtkinter.set_default_color_theme("blue") 


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuración de la Ventana Principal ---
        self.title("Proteomics Analyzer")
        self.geometry("800x600") # Ancho x Alto

        # --- Configuración de la Cuadrícula (Grid) ---
        # Hacemos que la columna central (1) se expanda para ocupar el espacio disponible
        self.grid_columnconfigure(1, weight=1)
        # Hacemos que la fila principal (0) se expanda
        self.grid_rowconfigure(0, weight=1)

        # --- Frame Izquierdo para Botones ---
        self.left_frame = customtkinter.CTkFrame(self, width=180, corner_radius=0)
        self.left_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.left_frame.grid_rowconfigure(6, weight=1) # Espacio para empujar botones hacia arriba

        # --- Sección de Experimentos (antes Clientes) ---
        self.experiments_label = customtkinter.CTkLabel(self.left_frame, text="Experiments", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.experiments_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_experiment_button = customtkinter.CTkButton(self.left_frame, text="Add Experiment", command=self.add_experiment_event)
        self.add_experiment_button.grid(row=1, column=0, padx=20, pady=10)

        self.delete_experiment_button = customtkinter.CTkButton(self.left_frame, text="Delete Experiment", command=self.delete_experiment_event)
        self.delete_experiment_button.grid(row=2, column=0, padx=20, pady=10)

        # --- Nueva Sección de Máquina ---
        self.machine_label = customtkinter.CTkLabel(self.left_frame, text="Machine", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.machine_label.grid(row=3, column=0, padx=20, pady=(20, 10))
        self.import_machine_button = customtkinter.CTkButton(self.left_frame, text="Import Machine Folder", command=self.import_machine_data_event)
        self.import_machine_button.grid(row=4, column=0, padx=20, pady=10)

        # --- Frame Izquierdo para la Vista de Cliente (inicialmente oculto) ---
        self.client_view_left_frame = customtkinter.CTkFrame(self, width=180, corner_radius=0)
        self.client_view_left_frame.grid_rowconfigure(7, weight=1) # Espacio para empujar botones hacia abajo

        self.client_docs_label = customtkinter.CTkLabel(self.client_view_left_frame, text="Documents", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.client_docs_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_doc_button = customtkinter.CTkButton(self.client_view_left_frame, text="Add Document", command=self.add_document_event)
        self.add_doc_button.grid(row=1, column=0, padx=20, pady=10)

        # Frame para la lista de documentos
        self.document_list_frame = customtkinter.CTkScrollableFrame(self.client_view_left_frame, label_text="TSV Files")
        self.document_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        self.generate_heatmap_button = customtkinter.CTkButton(self.client_view_left_frame, text="Generate Heatmap", command=self.generate_heatmap_event)
        self.generate_heatmap_button.grid(row=3, column=0, padx=20, pady=(20, 5)) 

        self.generate_triangle_button = customtkinter.CTkButton(self.client_view_left_frame, text="Generate Tri-Report", command=self.generate_triangle_report_event)
        self.generate_triangle_button.grid(row=4, column=0, padx=20, pady=(5, 5))

        self.generate_pdf_button = customtkinter.CTkButton(self.client_view_left_frame, text="Generate PDF", command=self.generate_pdf_report_event)
        self.generate_pdf_button.grid(row=5, column=0, padx=20, pady=(5, 20))

        self.export_excel_button = customtkinter.CTkButton(self.client_view_left_frame, text="Export to Excel", command=self.export_to_excel_event)
        self.export_excel_button.grid(row=6, column=0, padx=20, pady=(5, 20))


        # --- Frame Derecho para la Lista de Clientes ---
        self.right_frame = customtkinter.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1) # La segunda fila (lista de máquinas) se expandirá
        self.right_frame.grid_columnconfigure(0, weight=1)

        # --- Lista de Experimentos (antes Clientes) ---
        self.experiment_list_frame = customtkinter.CTkScrollableFrame(self.right_frame, label_text="Experiments (Manual Groups)")
        self.experiment_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # --- Nueva Lista de Máquinas ---
        self.machine_list_frame = customtkinter.CTkScrollableFrame(self.right_frame, label_text="Machines (Automatic Groups)")
        self.machine_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.group_buttons = {} # Diccionario para guardar los botones de cada grupo (experimento o máquina)
        self.selected_group = None
        self.selected_group_type = None # 'experiment' o 'machine'
        self.current_df = None # Para guardar el DataFrame actual

        # --- Vista de Cliente Individual (inicialmente oculta) ---
        self.client_view_frame = customtkinter.CTkFrame(self.right_frame)
        # No usamos .grid() aquí para mantenerlo oculto hasta que se necesite

        self.back_button = customtkinter.CTkButton(self.client_view_frame, text="< Back to Lists", command=self.show_main_lists)
        self.back_button.pack(anchor="nw", padx=10, pady=10)

        self.main_list_frame = customtkinter.CTkFrame(self.right_frame, fg_color="transparent")
        self.main_list_frame.grid(row=0, column=1, sticky="nsew")

        # --- Frame de Controles (para el menú desplegable) ---
        self.controls_frame = customtkinter.CTkFrame(self.client_view_frame, fg_color="transparent")
        self.controls_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.metric_label = customtkinter.CTkLabel(self.controls_frame, text="Metric to display:")
        self.metric_label.pack(side="left", padx=(0, 10))

        metric_options = [
            "Total Intensity",
            "Count",
            "Associated Proteins",
            "Average Score",
            "Best Score",
            "Best q-value",
            "Average Angle",
            "Best Angle",
            "Charge States"
        ]
        self.metric_selector = customtkinter.CTkComboBox(self.controls_frame, values=metric_options, command=self.metric_changed)
        self.metric_selector.set("Total Intensity") # Valor por defecto
        self.metric_selector.pack(side="left")

        # --- Frame para la Tabla de Datos ---
        self.data_table_frame = customtkinter.CTkFrame(self.client_view_frame)
        self.data_table_frame.pack(expand=True, fill="both", padx=10, pady=10)
        self.tree = None # Placeholder para la tabla

        # --- Carga Inicial de Datos ---
        self.refresh_group_lists()
        # Mostramos la lista de clientes al iniciar
        self.show_main_lists()

    def refresh_group_lists(self):
        """Actualiza las listas de Experimentos y Máquinas."""
        # Limpiar listas actuales
        for widget in self.experiment_list_frame.winfo_children():
            widget.destroy()
        for widget in self.machine_list_frame.winfo_children():
            widget.destroy()
        self.group_buttons = {}

        # Cargar grupos (clientes/experimentos) desde la base de datos
        groups = db.get_clients() # db.get_clients() now returns all groups
        for group_name in groups:
            # We assume machine names won't contain " (Manual)"
            # --- FIX: Case-insensitive machine detection ---
            # Convert the group name to lowercase for robust matching.
            # This way, "Orbitrap Astral" will match "orbitrap".
            is_manual = not any(k in group_name.lower() for k in ["orbitrap", "exactive"])
            
            target_frame = self.experiment_list_frame if is_manual else self.machine_list_frame
            
            button = customtkinter.CTkButton(target_frame, text=group_name, command=lambda name=group_name: self.select_group(name))
            button.pack(fill="x", padx=5, pady=2)
            # Añadir evento de doble clic para abrir la vista del cliente
            button.bind("<Double-1>", lambda event, name=group_name: self.open_group_on_double_click(name))
            self.group_buttons[group_name] = button

    def select_group(self, name):
        # Deseleccionar el cliente anterior si lo hay
        if self.selected_group and self.selected_group in self.group_buttons:
            self.group_buttons[self.selected_group].configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])

        # Seleccionar el nuevo cliente
        self.selected_group = name
        self.group_buttons[name].configure(fg_color="green") # Resaltar el seleccionado

    def open_group_on_double_click(self, group_name):
        """Selecciona un cliente y abre su vista, llamado por el evento de doble clic."""
        self.select_group(group_name)
        self.open_group_view()

    def open_group_view(self):
        if not self.selected_group:
            # With double-clicking, this is less likely to happen, but it's a good safeguard.
            messagebox.showwarning("Warning", "No group selected.")
            return

        # Ocultar el frame derecho de la lista de clientes y mostrar el de la vista de cliente
        self.experiment_list_frame.grid_forget()
        self.machine_list_frame.grid_forget()
        self.main_list_frame.grid_forget()
        self.client_view_frame.grid(row=0, column=0, sticky="nsew")

        # Ocultar el menú principal izquierdo y mostrar el menú de documentos del cliente
        self.left_frame.grid_forget()
        self.client_view_left_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")

        # When opening the view, reset the selector and load the data
        self.refresh_document_list()
        self.metric_selector.set("Total Intensity") # La métrica principal por defecto
        self.load_group_data()

    def metric_changed(self, choice):
        """Se llama cuando el usuario cambia la métrica en el ComboBox."""
        self.load_group_data()

    def load_group_data(self):
        """Carga los datos del cliente seleccionado según la métrica elegida y puebla la tabla."""
        # Limpiar la tabla anterior si existe
        if self.tree:
            self.tree.destroy()
            self.tree = None # Asegurarse de que se limpia
        self.current_df = None # Limpiar el DataFrame guardado

        client_folder = os.path.join(db.DATA_DIR, self.selected_group)
        try:
            # Use the new database function to get the files
            tsv_files = db.get_client_documents(self.selected_group, full_path=True)

            if not tsv_files:
                label = customtkinter.CTkLabel(self.data_table_frame, text="No .tsv files found in this client's folder.")
                label.grid(row=0, column=0, padx=20, pady=20)
                return

            selected_metric = self.metric_selector.get()

            # --- FINAL FIX: Assign correct column names ---
            # 1. Create a list of short, descriptive column names from the filenames.
            #    e.g., '2024-10-28_..._R01.tsv' -> '2024-10-28_..._R01'
            column_names = [os.path.splitext(os.path.basename(f))[0] for f in tsv_files]

            # Procesar los archivos con nuestro módulo de análisis
            # 2. Pass both the file paths and the desired column names.
            self.current_df = an.process_tsv_files(
                tsv_files, column_names, default_peptide_column='Peptide', metric_column=selected_metric
            )

            if self.current_df.empty:
                label = customtkinter.CTkLabel(self.data_table_frame, text="Could not process TSV files or they contain no valid data.")
                label.grid(row=0, column=0, padx=20, pady=20)
                self.current_df = None # Asegurarse de que no se guarde un DF vacío
                return

            # Crear y poblar la tabla
            self.populate_data_table(self.current_df)

        except FileNotFoundError:
            messagebox.showerror("Error", f"Data folder for group {self.selected_group} not found.")
        except Exception as e:
            messagebox.showerror("Analysis Error", f"An error occurred while analyzing the files: {e}")

    def populate_data_table(self, dataframe):
        # Limpiar el frame por si había un mensaje de "no hay archivos"
        for widget in self.data_table_frame.winfo_children():
            widget.destroy()

        # Configurar columnas de la tabla
        columns = [dataframe.index.name] + dataframe.columns.tolist()
        self.tree = ttk.Treeview(self.data_table_frame, columns=columns, show='headings')

        # Definir encabezados
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100) # Ancho inicial

        # Insertar datos
        for index, row in dataframe.iterrows():
            self.tree.insert("", "end", values=[index] + list(row))

        # Añadir scrollbars
        vsb = ttk.Scrollbar(self.data_table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.data_table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        self.data_table_frame.grid_rowconfigure(0, weight=1)
        self.data_table_frame.grid_columnconfigure(0, weight=1)

    def add_experiment_event(self):
        dialog = customtkinter.CTkInputDialog(text="Enter the new experiment's name:", title="Add Experiment")
        experiment_name = dialog.get_input()
        if experiment_name:
            if db.add_client(experiment_name):
                self.refresh_group_lists()
            else:
                messagebox.showerror("Error", f"Experiment '{experiment_name}' already exists.")

    def delete_experiment_event(self):
        if self.selected_group:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the group '{self.selected_group}' and all its data?"):
                db.delete_client(self.selected_group)
                self.selected_group = None
                self.refresh_group_lists()
        else:
            messagebox.showwarning("Warning", "Please select a group to delete.")

    def show_main_lists(self):
        # Ocultar la vista de cliente (derecha) y mostrar la lista de clientes
        self.client_view_frame.grid_forget()
        
        # Mostrar los frames de las listas principales
        self.main_list_frame.grid(row=0, column=1, rowspan=2, padx=20, pady=20, sticky="nsew")
        self.experiment_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.machine_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Ocultar el menú de documentos y mostrar el menú principal
        self.client_view_left_frame.grid_forget()
        self.left_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")

    def refresh_document_list(self):
        """Actualiza la lista de documentos en el panel izquierdo de la vista de cliente."""
        # Limpiar la lista actual
        for widget in self.document_list_frame.winfo_children():
            widget.destroy()

        if not self.selected_group:
            return

        documents = db.get_client_documents(self.selected_group)
        for doc_name in documents:
            # Crear un frame para cada fila (documento + botón de borrar)
            doc_frame = customtkinter.CTkFrame(self.document_list_frame, fg_color="transparent")
            doc_frame.pack(fill="x", pady=2)
            doc_frame.columnconfigure(0, weight=1) # El label se expande

            label = customtkinter.CTkLabel(doc_frame, text=doc_name, anchor="w")
            label.grid(row=0, column=0, sticky="ew", padx=(5,0))

            delete_button = customtkinter.CTkButton(
                doc_frame, text="X", width=20, height=20,
                command=lambda name=doc_name: self.delete_document_event(name)
            )
            delete_button.grid(row=0, column=1, padx=5)

    def add_document_event(self):
        """Abre un diálogo para seleccionar y añadir un archivo .tsv al cliente actual."""
        if not self.selected_group:
            return

        filepaths = filedialog.askopenfilenames(
            title="Select TSV files",
            filetypes=[("TSV files", "*.tsv"), ("All files", "*.*")]
        )
        if filepaths:
            for path in filepaths:
                db.add_document_to_client(self.selected_group, path)
            self.refresh_document_list()
            self.load_group_data() # Recargar la tabla con los nuevos datos

    def delete_document_event(self, doc_name):
        """Elimina un documento del cliente actual."""
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the document '{doc_name}'?"):
            if db.delete_client_document(self.selected_group, doc_name):
                self.refresh_document_list()
                self.load_group_data() # Recargar la tabla

    def import_machine_data_event(self):
        """
        Abre un diálogo para seleccionar una carpeta, la escanea en busca de datos de experimentos
        y los importa automáticamente, organizándolos por máquina.
        """
        root_folder = filedialog.askdirectory(title="Select the main folder containing all experiments")
        if not root_folder:
            return

        imported_count = 0
        failed_count = 0
        
        for dirpath, dirnames, filenames in os.walk(root_folder):
            # --- MEJORA: Búsqueda dinámica de archivos ---
            # En lugar de buscar una carpeta con un nombre específico, buscamos directamente
            # la presencia de los dos archivos necesarios en cualquier carpeta.
            if 'lfq.tsv' in filenames and 'payload.json' in filenames:
                lfq_path = os.path.join(dirpath, 'lfq.tsv')
                payload_path = os.path.join(dirpath, 'payload.json')
                try:
                    with open(payload_path, 'r', encoding='utf-8') as f:
                        payload_data = json.load(f)

                    # Extraer el modelo de la máquina
                    instrument_info_str = payload_data.get('instrument_info', '{}')
                    # El campo es un string que parece un dict, usamos ast.literal_eval para convertirlo
                    instrument_info = ast.literal_eval(instrument_info_str)
                    machine_model = instrument_info.get('model', 'Unknown_Machine').strip()

                    date_prefix = "YYYY-MM-DD" # Prefijo por defecto si no se encuentra ninguna fecha
                    date_found = False

                    # Paso 1: Intentar extraer la fecha de 'thermo_creation_datetime'
                    creation_datetime_str = payload_data.get('thermo_creation_datetime')
                    if creation_datetime_str:
                        try:
                            # Intentar parsear formato '4/15/2025 10:22:04 PM'
                            dt_obj = datetime.strptime(creation_datetime_str, '%m/%d/%Y %I:%M:%S %p')
                            date_prefix = dt_obj.strftime('%Y-%m-%d')
                            date_found = True
                        except ValueError:
                            try:
                                # Intentar parsear formato '24/08/2019 10:39:28'
                                dt_obj = datetime.strptime(creation_datetime_str, '%d/%m/%Y %H:%M:%S')
                                date_prefix = dt_obj.strftime('%Y-%m-%d')
                                date_found = True
                            except ValueError:
                                # Falló el parseo, se intentará el Paso 2
                                pass

                    # Paso 2: Si no se encontró la fecha en el Paso 1, intentar de 'raw_file_name'
                    if not date_found:
                        raw_file_name_from_payload = payload_data.get('raw_file_name')
                        if raw_file_name_from_payload and len(raw_file_name_from_payload) >= 8:
                            # Se espera un formato YYYYMMDD_... al inicio del nombre del archivo
                            date_part = raw_file_name_from_payload[:8]
                            try:
                                dt_obj = datetime.strptime(date_part, '%Y%m%d')
                                date_prefix = dt_obj.strftime('%Y-%m-%d')
                            except ValueError:
                                # Si no tiene el formato YYYYMMDD, se mantiene el prefijo por defecto
                                pass

                    # Crear el grupo de máquina si no existe
                    db.add_client(machine_model) # Reutilizamos la función add_client

                    # Construir el nuevo nombre de archivo
                    # --- CORRECCIÓN: Usar el nombre de la carpeta padre para garantizar unicidad ---
                    # El 'Sample_Name' del JSON puede repetirse, pero el nombre de la carpeta
                    # que contiene la carpeta 'Results' suele ser único para cada ejecución.
                    sample_name = os.path.basename(os.path.dirname(dirpath))
                    new_filename = f"{date_prefix}_{sample_name}.tsv"
                    
                    # Copiar y renombrar el archivo lfq.tsv
                    destination_folder = os.path.join(db.DATA_DIR, machine_model)
                    destination_path = os.path.join(destination_folder, new_filename)
                    
                    shutil.copy(lfq_path, destination_path)
                    imported_count += 1

                except Exception as e:
                    print(f"Failed to process folder {dirpath}: {e}")
                    failed_count += 1

        self.refresh_group_lists()
        messagebox.showinfo("Import Complete", 
                            f"Successfully imported {imported_count} experiments.\n"
                            f"Failed to import {failed_count} experiments.")

    # --- REFACTORIZACIÓN: Mover la lógica de generación de reportes a una función interna ---
    def _generate_correlation_report(self, is_triangular: bool):
        """
        Función interna que genera una ventana con un mapa de calor (cuadrado o triangular)
        y añade filtros de fecha para actualizarlo dinámicamente.
        """
        try:
            # 1. Crear la ventana emergente para el reporte
            report_window = customtkinter.CTkToplevel(self)
            report_type = "Triangular" if is_triangular else "Square"
            report_window.title(f"{report_type} Correlation Report - {self.selected_group}")
            report_window.geometry("950x750") # Aumentamos el ancho para que quepan los botones
            report_window.grab_set()

            # 2. Crear el frame para los filtros de fecha
            filter_frame = customtkinter.CTkFrame(report_window)
            filter_frame.pack(fill="x", padx=10, pady=(10, 0))

            customtkinter.CTkLabel(filter_frame, text="Desde:").pack(side="left", padx=(10, 5))
            start_date_entry = customtkinter.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=120)
            start_date_entry.pack(side="left", padx=5)

            customtkinter.CTkLabel(filter_frame, text="Hasta:").pack(side="left", padx=(10, 5))
            end_date_entry = customtkinter.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=120)
            end_date_entry.pack(side="left", padx=5)

            # Frame para el lienzo del gráfico (inicialmente vacío)
            canvas_frame = customtkinter.CTkFrame(report_window)
            canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # --- MEJORA: Función para cambiar la fecha con la rueda del ratón/teclas ---
            def _change_date(event, delta):
                """
                Incrementa/decrementa el día, mes o año en el widget de entrada,
                dependiendo de la posición del cursor.
                """
                entry_widget = event.widget
                current_date_str = entry_widget.get()
                
                try:
                    current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()
                except ValueError:
                    current_date = datetime.now().date()

                cursor_pos = entry_widget.index("insert")
                year, month, day = current_date.year, current_date.month, current_date.day

                if 0 <= cursor_pos <= 4: # Modificar año (YYYY)
                    year += delta
                elif 5 <= cursor_pos <= 7: # Modificar mes (-MM)
                    month += delta
                    if month > 12:
                        month = 1
                        year += 1
                    elif month < 1:
                        month = 12
                        year -= 1
                else: # Modificar día (-DD)
                    new_date = current_date + timedelta(days=delta)
                    year, month, day = new_date.year, new_date.month, new_date.day
                
                # Prevenir fechas inválidas como el 31 de febrero
                try:
                    new_date = datetime(year, month, day).date()
                except ValueError:
                    # Si el día es inválido para el nuevo mes/año, ajústalo al último día válido
                    last_day_of_month = (datetime(year, month, 1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                    new_date = last_day_of_month.date()

                entry_widget.delete(0, "end")
                entry_widget.insert(0, new_date.strftime('%Y-%m-%d'))
                entry_widget.icursor(cursor_pos) # <-- ¡CORRECCIÓN! Mantiene el cursor en su sitio.

            # Vinculamos los eventos a los campos de fecha
            for entry in [start_date_entry, end_date_entry]:
                entry.bind("<MouseWheel>", lambda e: _change_date(e, 1 if e.delta > 0 else -1))
                entry.bind("<Up>", lambda e: _change_date(e, 1))
                entry.bind("<Down>", lambda e: _change_date(e, -1))

            # Variables to hold references to the canvas, figure, and data
            current_canvas = None
            current_fig = None
            current_corr_matrix = None # Para guardar la matriz de correlación

            def update_chart():
                nonlocal current_canvas, current_fig, current_corr_matrix

                # Clear the previous chart if it exists
                if current_canvas:
                    current_canvas.get_tk_widget().destroy()
                if current_fig:
                    plt.close(current_fig)
                current_corr_matrix = None

                # Obtener todas las rutas de los archivos TSV para el grupo
                all_tsv_files = db.get_client_documents(self.selected_group, full_path=True) # Get all TSV file paths for the group

                # Filter files by date
                start_date_str = start_date_entry.get()
                end_date_str = end_date_entry.get()
                
                filtered_files = []
                for file_path in all_tsv_files:
                    filename = os.path.basename(file_path)
                    try:
                        file_date_str = filename.split('_')[0]
                        file_date = datetime.strptime(file_date_str, '%Y-%m-%d').date()

                        start_ok = True
                        if start_date_str:
                            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                            if file_date < start_date:
                                start_ok = False
                        
                        end_ok = True
                        if end_date_str:
                            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                            if file_date > end_date:
                                end_ok = False

                        if start_ok and end_ok:
                            filtered_files.append(file_path)

                    except (ValueError, IndexError):
                        # If the filename doesn't have the date format, include it if no filters are set
                        if not start_date_str and not end_date_str:
                            filtered_files.append(file_path)

                if len(filtered_files) < 2:
                    messagebox.showwarning("Warning", "At least 2 documents in the selected date range are required to generate a correlation report.", parent=report_window)
                    return

                # Process data and generate the chart
                protein_df = an.get_protein_intensity_matrix(filtered_files)
                if protein_df.empty:
                    messagebox.showerror("Error", "Could not process data. Please ensure the TSV files contain a 'proteins' column and intensity data.", parent=report_window)
                    return

                corr_matrix = protein_df.corr(method='pearson')
                current_corr_matrix = corr_matrix # Save the matrix
                min_val = corr_matrix.where(corr_matrix < 1.0).min().min()
                max_val = 1.0

                corr_matrix.columns = [f"run {i+1}" for i in range(len(corr_matrix.columns))]
                corr_matrix.index = corr_matrix.columns

                num_items = len(corr_matrix.columns)
                base_size = max(8, min(num_items * 0.5, 25))
                fig_size = (base_size, base_size)

                current_fig, ax = plt.subplots(figsize=fig_size)

                if is_triangular:
                    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
                    custom_colors = ["#69e4ff", "#48f1a0"]
                    custom_cmap = LinearSegmentedColormap.from_list("custom_gradient", custom_colors)
                    sns.heatmap(corr_matrix, mask=mask, cmap=custom_cmap, annot=False, vmin=min_val, vmax=max_val, cbar_kws={'shrink': .8}, ax=ax)
                    
                    lower_triangle = corr_matrix.where(np.tril(np.ones(corr_matrix.shape).astype(bool), k=-1))
                    mean_corr = lower_triangle.stack().mean()
                    ax.text(0.98, 0.98, f">{mean_corr:.2f}\nMean Pearson\nCorrelation", transform=ax.transAxes,
                            horizontalalignment='right', verticalalignment='top', fontsize=12, color='black',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.5'))
                else: # Gráfico cuadrado
                    show_annotations = num_items <= 10
                    custom_colors = ["#b9edf9", "#48f1a0"]
                    custom_cmap = LinearSegmentedColormap.from_list("custom_gradient", custom_colors)
                    sns.heatmap(corr_matrix, annot=show_annotations, cmap=custom_cmap, ax=ax, fmt='.3f', vmin=min_val, vmax=max_val, linewidths=.5, linecolor='gray')

                if num_items > 2:
                    xticks = ax.get_xticklabels()
                    [label.set_visible(False) for i, label in enumerate(xticks) if i != 0 and i != len(xticks) - 1]
                    yticks = ax.get_yticklabels()
                    [label.set_visible(False) for i, label in enumerate(yticks) if i != 0 and i != len(yticks) - 1]

                ax.set_title("Pearson Correlation Matrix (Protein Intensities)")
                plt.subplots_adjust(left=0.15, bottom=0.15, right=0.9, top=0.9)

                # Incrustar la figura en la ventana
                current_canvas = FigureCanvasTkAgg(current_fig, master=canvas_frame)
                current_canvas.draw()
                current_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

            # Button to update the chart
            update_button = customtkinter.CTkButton(filter_frame, text="Update Chart", command=update_chart)
            update_button.pack(side="left", padx=(20, 10))
            

            # El lienzo del gráfico ahora se empaqueta después de los filtros (arriba)
            # y antes de los botones (abajo), por lo que ocupará todo el espacio restante.
            canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

            def export_chart_data():
                """Exports the correlation matrix to an Excel file."""
                if current_corr_matrix is None or current_corr_matrix.empty:
                    messagebox.showwarning("No Data", "There is no correlation data to export.", parent=report_window)
                    return

                filepath = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel Workbook", "*.xlsx"), ("All files", "*.*")],
                    title="Export Data to Excel",
                    parent=report_window
                )
                if not filepath:
                    return

                try:
                    current_corr_matrix.to_excel(filepath, index=True)
                    messagebox.showinfo("Success", f"Data successfully exported to:\n{filepath}", parent=report_window)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not export to Excel: {e}", parent=report_window)

            # Button to save the chart as an image
            save_chart_button = customtkinter.CTkButton(
                filter_frame, # Mover al frame de filtros superior
                text="Export Chart (Image)",
                command=lambda: self.save_figure(current_fig) if current_fig else None
            )
            save_chart_button.pack(side="right", padx=(5, 10), pady=5) # Empaquetar a la derecha

            # Mover el botón de exportar datos al frame de filtros superior
            save_data_button = customtkinter.CTkButton(
                filter_frame, # Mover al frame de filtros superior
                text="Export Data (Excel)",
                command=export_chart_data
            )
            save_data_button.pack(side="right", padx=5, pady=5) # Empaquetar a la derecha
            
            # Cerrar la figura de matplotlib al cerrar la ventana para liberar memoria
            def on_close():
                if current_fig:
                    plt.close(current_fig)
                report_window.destroy()

            report_window.protocol("WM_DELETE_WINDOW", on_close)

            # Load the initial chart without filters
            update_chart()

        except Exception as e:
            messagebox.showerror("Error", f"Could not generate the report: {e}")

    def generate_heatmap_event(self):
        """
        Genera un mapa de calor cuadrado con filtros de fecha.
        """
        self._generate_correlation_report(is_triangular=False)

    def generate_triangle_report_event(self):
        """
        Genera un mapa de calor triangular con filtros de fecha.
        """
        self._generate_correlation_report(is_triangular=True)

    def save_figure(self, fig):
        """Abre un diálogo para guardar una figura de matplotlib en un archivo."""
        if not fig:
            messagebox.showwarning("Warning", "No chart has been generated yet.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("SVG Vector Image", "*.svg"),
                ("JPEG Image", "*.jpg"),
                ("PDF Document", "*.pdf"),
                ("All files", "*.*")
            ],
            title="Save Chart As"
        )
        if not filepath:
            return # El usuario canceló

        try:
            # Guardamos la figura con buena resolución y sin bordes cortados
            fig.savefig(filepath, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Chart successfully saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save chart: {e}")

    def generate_pdf_report_event(self):
        """
        Genera un reporte en PDF de la tabla de datos que se está mostrando actualmente.
        """
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("No Data", "There is no data to generate a report from. Please load some documents first.")
            return

        # Abrir diálogo para guardar archivo
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf"), ("All files", "*.*")],
            title="Save PDF Report As"
        )

        if not filepath:
            return # El usuario canceló el diálogo

        try:
            # --- MEJORA: Preparar datos para el reporte en PDF ---

            # 1. Crear una copia del DataFrame para no modificar el original que se muestra en la GUI.
            report_df = self.current_df.copy()

            # 2. Crear nombres de columna más cortos y un mapa para la leyenda.
            #    Ej: 'C:\\path\\to\\file.tsv' -> 'file'
            original_columns = report_df.columns.tolist()
            short_columns = [os.path.splitext(os.path.basename(col))[0] for col in original_columns]
            
            # Crear un diccionario de mapeo para la leyenda del PDF
            column_mapping = {short: full for short, full in zip(short_columns, original_columns)}

            # 3. Renombrar las columnas en la copia del DataFrame.
            report_df.columns = short_columns

            # 4. Obtener el título del reporte.
            title = self.metric_selector.get()

            # 5. Llamar a la función de generación de PDF con los datos mejorados.
            #    Pasamos el DataFrame modificado, el mapa de columnas y pedimos orientación horizontal.
            rg.create_pdf_report(
                filepath=filepath,
                title=title,
                dataframe=report_df,
                column_mapping=column_mapping
            )

            messagebox.showinfo("Success", f"Report successfully saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF report: {e}")

    def export_to_excel_event(self):
        """
        Exporta el DataFrame actual a un archivo de Excel (.xlsx).
        """
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("No Data", "There is no data to export. Please load some documents first.")
            return

        # Abrir diálogo para guardar archivo
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("All files", "*.*")],
            title="Export Data to Excel"
        )

        if not filepath:
            return # El usuario canceló el diálogo

        try:
            # Usamos la función to_excel de pandas.
            # 'index=True' es el comportamiento por defecto y asegura que la columna de péptidos se incluya.
            # Necesitas tener 'openpyxl' instalado: pip install openpyxl
            self.current_df.to_excel(filepath, index=True)
            messagebox.showinfo("Success", f"Data successfully exported to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export to Excel: {e}\n\nMake sure you have 'openpyxl' installed (pip install openpyxl).")


if __name__ == "__main__":
    # 1. Determinar la ruta base de la aplicación (portable)
    APP_BASE_PATH = get_app_path()
    # 2. Inyectar la ruta en el módulo de la base de datos y luego inicializar
    db.set_data_dir(APP_BASE_PATH)
    db.initialize_database()
    app = App()
    app.mainloop()