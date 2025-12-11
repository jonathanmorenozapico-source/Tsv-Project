import pandas as pd
import os

# --- AGGREGATION STRATEGIES ---
# Here we define how each metric should be processed.
# Each key is the name of the metric displayed in the interface.
# The value is a dictionary containing:
#   - 'columns': a list of possible column names in the TSV file.
#   - 'agg_func': the aggregation function to use (e.g., 'sum', 'mean', or a lambda function).

def aggregate_unique_strings(series):
    """Aggregates unique values from a series, useful for 'charge'."""
    return ', '.join(map(str, sorted(series.dropna().unique())))

def aggregate_protein_strings(series):
    """Aggregates unique protein identifiers, handling semicolon-separated lists."""
    all_proteins = series.dropna().astype(str).str.split(';').explode()
    return ';'.join(sorted(all_proteins.unique()))

AGGREGATION_STRATEGIES = {
    'Count':               {'columns': [None], 'agg_func': 'size'}, # Special case, just counts rows
    'Total Intensity':     {'columns': [None], 'agg_func': 'sum'},  # Special case, uses the last column
    'Average Score':       {'columns': ['score'], 'agg_func': 'mean'},
    'Best Score':          {'columns': ['score'], 'agg_func': 'max'},
    'Best q-value':        {'columns': ['q_value', 'peptide_q-value'], 'agg_func': 'min'},
    'Average Angle':       {'columns': ['spectral_angle'], 'agg_func': 'mean'},
    'Best Angle':          {'columns': ['spectral_angle'], 'agg_func': 'max'},
    'Charge States':       {'columns': ['charge'], 'agg_func': aggregate_unique_strings},
    # 'Associated Proteins' REMOVED: Now handled permanently in the main table structure
}

def process_single_tsv(file_path, peptide_column, metric_column):
    """
    Processes a single TSV file to aggregate data according to the metric.
    """
    try:
        df = pd.read_csv(file_path, sep='\t')

        # --- MODIFICATION: Flexible and robust search for the peptide column ---
        # List of possible names for the peptide column.
        # The order matters: the first one found will be used.
        # We add 'peptide' (lowercase) which the user indicated appears.
        candidate_peptide_columns = [
            peptide_column, # The default name ('Peptide' from main.py)
            'peptide',      # El nombre que el usuario ha indicado que aparece
            'Sequence',
            'sequence',
            'Peptide_Sequence',
            'peptide_sequence',
            'Peptide Sequence',
            'Peptide ID',   # Un nombre común adicional
            'PeptideID',
            'Accession'     # Otro nombre común en algunos formatos
        ]
        
        actual_peptide_column = None
        for col_name in candidate_peptide_columns:
            if col_name in df.columns:
                actual_peptide_column = col_name
                break
        
        # If no known name was found, we try to use the first column
        if not actual_peptide_column and len(df.columns) > 0:
            actual_peptide_column = df.columns[0]
            # Optional: you could add a warning message here if you want to notify the user
            # that the first column was used by default.
        
        if not actual_peptide_column: # If still not found, or the file was empty
            raise ValueError(f"Could not find a valid peptide column (tried: {', '.join(candidate_peptide_columns)} and the first column) in {os.path.basename(file_path)}. Available columns: {', '.join(df.columns)}")
        # --- FIN MODIFICACIÓN ---

        if metric_column not in AGGREGATION_STRATEGIES:
            raise ValueError(f"Unknown metric: '{metric_column}'. Valid metrics are: {', '.join(AGGREGATION_STRATEGIES.keys())}")

        strategy = AGGREGATION_STRATEGIES[metric_column]
        agg_func = strategy['agg_func']

        # --- Aggregation Logic based on Strategies ---
        if metric_column == 'Count':
            agg_df = df.groupby(actual_peptide_column).size().reset_index(name=metric_column)
        elif metric_column == 'Total Intensity':
            metric_col_name = df.columns[-1] # La intensidad es siempre la última columna
            df[metric_col_name] = pd.to_numeric(df[metric_col_name], errors='coerce').fillna(0)
            agg_df = df.groupby(actual_peptide_column)[metric_col_name].agg(agg_func).reset_index()
            agg_df = agg_df.rename(columns={metric_col_name: metric_column})
        else:
            # Find the correct metric column in the file
            metric_col_name = None
            for col in strategy['columns']:
                if col in df.columns:
                    metric_col_name = col
                    break
            
            if not metric_col_name:
                raise ValueError(f"For metric '{metric_column}', none of the expected columns ({', '.join(strategy['columns'])}) were found in {os.path.basename(file_path)}.")

            # For non-text aggregation functions, convert to numeric
            if isinstance(agg_func, str) and agg_func in ['sum', 'mean', 'max', 'min']:
                df[metric_col_name] = pd.to_numeric(df[metric_col_name], errors='coerce').fillna(0)

            # Apply the aggregation function
            agg_df = df.groupby(actual_peptide_column)[metric_col_name].agg(agg_func).reset_index()
            
            # Rename the result column to match the selected metric
            if metric_col_name != metric_column:
                agg_df = agg_df.rename(columns={metric_col_name: metric_column})

        # Rename the results column with the file name (without extension)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        agg_df = agg_df.rename(columns={agg_df.columns[1]: file_name})
        
        return agg_df.set_index(actual_peptide_column)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        raise # Re-throw the exception so main.py can catch it and show a messagebox

def get_peptide_protein_map(file_path, peptide_column):
    """
    Extracts a dictionary mapping Peptides to Proteins from a TSV file.
    """
    try:
        df = pd.read_csv(file_path, sep='\t')
        
        # 1. Identify Peptide Column (Reuse logic or keep it simple if we assume process_single_tsv passed validation)
        # For simplicity, we'll repeat the robust search or assume standardization. 
        # But 'process_single_tsv' is called separately. 
        # Let's do a quick robust search again to be safe.
        candidate_peptide_columns = [
            peptide_column, 'peptide', 'Sequence', 'sequence', 
            'Peptide_Sequence', 'peptide_sequence', 'Peptide Sequence', 
            'Peptide ID', 'PeptideID', 'Accession'
        ]
        actual_peptide_column = None
        for col in candidate_peptide_columns:
            if col in df.columns:
                actual_peptide_column = col
                break
        if not actual_peptide_column and len(df.columns) > 0:
            actual_peptide_column = df.columns[0]
            
        if not actual_peptide_column:
            return {}

        # 2. Identify Protein Column
        candidate_protein_columns = [
            'Proteins', 'proteins', 'Protein', 'protein', 
            'Leading Proteins', 'Leading proteins', 'Leading razor protein', 'Protein Group'
        ]
        actual_protein_column = None
        for col in candidate_protein_columns:
            if col in df.columns:
                actual_protein_column = col
                break
        
        if not actual_protein_column:
            return {} # No protein info in this file

        # 3. Create Map (cleaning proteins)
        # We take the first protein if there are multiple (split by ;) or just the string
        # Drop duplicates to keep it fast
        subset = df[[actual_peptide_column, actual_protein_column]].dropna()
        subset[actual_protein_column] = subset[actual_protein_column].astype(str).apply(lambda x: x.split(';')[0])
        
        # Convert to dict. If a peptide appears multiple times, the last one wins (or we could aggregate).
        # Usually one peptide maps to one protein group context.
        return pd.Series(subset[actual_protein_column].values, index=subset[actual_peptide_column]).to_dict()

    except Exception:
        return {}

def process_tsv_files(tsv_files, column_names, default_peptide_column='Peptide', metric_column='Conteo'):
    """
    Procesa una lista de archivos TSV y los combina en un único DataFrame.
    Aditionally, it builds a master Peptide->Protein map and inserts it as the first column.
    """
    if not tsv_files:
        return pd.DataFrame()

    if len(tsv_files) != len(column_names):
        raise ValueError("The number of tsv_files must match the number of column_names.")

    all_dataframes = []
    master_protein_map = {}

    for i, file in enumerate(tsv_files):
        # 1. Process Numeric Data
        processed_df = process_single_tsv(file, default_peptide_column, metric_column)
        if processed_df is not None:
            # Rename the data column with the custom column name
            new_col_name = column_names[i]
            processed_df = processed_df.rename(columns={processed_df.columns[0]: new_col_name})
            all_dataframes.append(processed_df)

        # 2. Update Master Protein Map
        # We process the file again solely to extract protein info. 
        # This is slightly inefficient (double read) but cleaner for separation of concerns 
        # unless we refactor process_single_tsv to return both. 
        # Given standard file sizes, double read is acceptable for robustness.
        file_protein_map = get_peptide_protein_map(file, default_peptide_column)
        # Update master map. New files might overwrite old mappings or add new ones.
        master_protein_map.update(file_protein_map)

    if not all_dataframes:
        return pd.DataFrame()

    # Join all DataFrames into one, using the peptide index
    final_df = pd.concat(all_dataframes, axis=1, join='outer')

    # Fill NaN values (peptides not found in a file) with 0 for numeric columns.
    # Charge States is the only one left that returns strings, but we handle it generally.
    if AGGREGATION_STRATEGIES[metric_column]['agg_func'] != aggregate_unique_strings:
        final_df = final_df.fillna(0)

    # Ensure the index column (peptides) has a name.
    final_df.index.name = final_df.index.name or default_peptide_column

    # --- NEW: Insert Protein Column ---
    # Map the index (Peptides) to the Protein Name using the master map
    protein_series = final_df.index.map(master_protein_map).fillna('Unknown')
    
    # Insert at position 0
    final_df.insert(0, 'Protein', protein_series)

    return final_df

def get_protein_intensity_matrix(tsv_files):
    """
    Crea una matriz de intensidad de proteínas a partir de una lista de archivos TSV.
    Las filas son proteínas y las columnas son los archivos de muestra.
    """
    all_protein_dataframes = []

    for file_path in tsv_files:
        try:
            df = pd.read_csv(file_path, sep='\t')

            # 1. Find the intensity column (the last one) and ensure it's numeric
            intensity_col_name = df.columns[-1]
            df[intensity_col_name] = pd.to_numeric(df[intensity_col_name], errors='coerce').fillna(0)

            # 2. Find the protein column
            protein_col_name = None
            if 'proteins' in df.columns:
                protein_col_name = 'proteins'
            elif 'Proteins' in df.columns:
                protein_col_name = 'Proteins'
            
            if not protein_col_name:
                # If not found, skip the file, but an error could be thrown.
                print(f"Warning: Protein column ('proteins' or 'Proteins') not found in {os.path.basename(file_path)}. Skipping for correlation analysis.")
                continue

            # 3. Use only the first protein identifier for simplicity
            df['protein_group'] = df[protein_col_name].astype(str).str.split(';').str[0]

            # --- MODIFICATION: Clean data before grouping ---
            # Remove rows where the protein is not defined or the intensity is 0
            df = df[df['protein_group'].notna() & (df[intensity_col_name] > 0)]

            # 4. Group by protein and sum intensities
            protein_intensities = df.groupby('protein_group')[intensity_col_name].sum()

            # 5. Rename the series with the file name
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            protein_intensities.name = file_name
            
            all_protein_dataframes.append(protein_intensities)
        except Exception as e:
            raise ValueError(f"Failed to process file {os.path.basename(file_path)} for protein analysis: {e}")

    if not all_protein_dataframes:
        return pd.DataFrame()

    # 6. Combine all dataframes and fill NaNs
    final_df = pd.concat(all_protein_dataframes, axis=1, join='outer').fillna(0)
    return final_df