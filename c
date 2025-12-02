import pandas as pd
import os

def process_single_tsv(file_path, peptide_column, metric_column):
    """
    Procesa un único archivo TSV para agregar datos según la métrica.
    """
    try:
        df = pd.read_csv(file_path, sep='\t')

        # Validar que las columnas necesarias existan
        if peptide_column not in df.columns:
            raise ValueError(f"La columna de péptidos '{peptide_column}' no se encuentra en {os.path.basename(file_path)}")
        if metric_column != 'Conteo' and metric_column not in df.columns:
            raise ValueError(f"La columna de métrica '{metric_column}' no se encuentra en {os.path.basename(file_path)}")

        # Realizar la agregación
        if metric_column == 'Conteo':
            # Contar el número de ocurrencias de cada péptido
            agg_df = df.groupby(peptide_column).size().reset_index(name='Conteo')
        else:
            # Convertir la columna de métrica a numérico, forzando errores a NaN y luego rellenando con 0
            df[metric_column] = pd.to_numeric(df[metric_column], errors='coerce').fillna(0)
            # Sumar la métrica para cada péptido
            agg_df = df.groupby(peptide_column)[metric_column].sum().reset_index()

        # Renombrar la columna de resultados con el nombre del archivo (sin extensión)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        agg_df = agg_df.rename(columns={agg_df.columns[1]: file_name})
        
        return agg_df.set_index(peptide_column)

    except Exception as e:
        print(f"Error procesando el archivo {file_path}: {e}")
        return None

def process_tsv_files(tsv_files, default_peptide_column='Peptide', metric_column='Conteo'):
    """
    Procesa una lista de archivos TSV y los combina en un único DataFrame.
    """
    if not tsv_files:
        return pd.DataFrame()

    all_dataframes = []
    for file in tsv_files:
        processed_df = process_single_tsv(file, default_peptide_column, metric_column)
        if processed_df is not None:
            all_dataframes.append(processed_df)

    if not all_dataframes:
        return pd.DataFrame()

    # Unir todos los DataFrames en uno solo, usando el índice de péptidos
    # El 'outer' join asegura que se incluyan todos los péptidos de todos los archivos
    final_df = pd.concat(all_dataframes, axis=1, join='outer')
    
    # Rellenar los valores NaN (péptidos no encontrados en un archivo) con 0
    final_df = final_df.fillna(0).astype(int)
    final_df.index.name = default_peptide_column # Asegurarse de que la columna de índice tenga nombre
    
    return final_df