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
    # 'Associated Proteins' removed as it is now a permanent column
}

def get_peptide_protein_map(df, peptide_column):
    """
    Extracts a dictionary mapping peptides to their associated proteins.
    Handles multiple protein columns candidates.
    """
    protein_candidates = [
        'Proteins', 'proteins', 
        'Protein', 'protein',
        'Leading Proteins', 'Leading proteins', 
        'Leading razor protein', 
        'Protein Group', 'Protein group'
    ]
    
    protein_col = None
    for col in protein_candidates:
        if col in df.columns:
            protein_col = col
            break
            
    if not protein_col:
        return {}
        
    # Extract unique pairs of (peptide, protein)
    # We drop NA values to avoid issues
    subset = df[[peptide_column, protein_col]].dropna()
    
    # We want to aggregate proteins for each peptide. 
    # A peptide might map to multiple proteins (or the same protein string repeated).
    # We use our existing logic to join them with ';'.
    
    # Group by peptide and apply the aggregation
    # We assume 'aggregate_protein_strings' logic is suitable here
    # (splitting by semicolon, finding uniques, joining back)
    
    # However, for efficiency in a single file, we can just take the value if it's consistent,
    # or aggregate if it differs.
    
    # Let's use the robust aggregation to be safe:
    return subset.groupby(peptide_column)[protein_col].apply(aggregate_protein_strings).to_dict()

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

def process_tsv_files(tsv_files, column_names, default_peptide_column='Peptide', metric_column='Conteo'):
    """
    Procesa una lista de archivos TSV y los combina en un único DataFrame.
    """
    if not tsv_files:
        return pd.DataFrame()

    if len(tsv_files) != len(column_names):
        raise ValueError("The number of tsv_files must match the number of column_names.")

    all_dataframes = []
    
    # --- New: Master map for Peptide -> Protein ---
    # We will accumulate mappings from all files.
    # If a peptide appears in multiple files with different proteins (unlikely but possible),
    # we will merge them.
    master_peptide_protein_map = {} 

    for i, file in enumerate(tsv_files):
        # We need to process the file to get the data AND the protein mapping
        # Unfortunately, process_single_tsv creates the aggregated DF but doesn't return the raw DF or mapping.
        # We could modify process_single_tsv, but to avoid breaking too much, 
        # let's peek at the file again or do it inside process_single_tsv?
        # A cleaner approach is to read the file once here if possible, but process_single_tsv has logic for column finding.
        
        # Let's trust process_single_tsv for the numeric data.
        processed_df = process_single_tsv(file, default_peptide_column, metric_column)
        
        if processed_df is not None:
             # Rename the data column with the custom column name
            new_col_name = column_names[i]
            processed_df = processed_df.rename(columns={processed_df.columns[0]: new_col_name})
            all_dataframes.append(processed_df)
            
            # --- Extract Protein Data for this file ---
            # We re-read the file to extract protein info. 
            # This adds some IO overhead but keeps logic separated and safe.
            # Efficiency is usually fine for these file sizes.
            try:
                temp_df = pd.read_csv(file, sep='\t')
                
                # Find the actual peptide column used (same logic as single_tsv basically)
                # We can reuse the logic or just try the candidates again.
                # To be consistent, let's copy the candidate list logic briefly or make a helper.
                # For now, let's assume one of the candidates works.
                candidate_peptide_columns = [
                    default_peptide_column, 'peptide', 'Sequence', 'sequence', 
                    'Peptide_Sequence', 'peptide_sequence', 'Peptide Sequence', 
                    'Peptide ID', 'PeptideID', 'Accession'
                ]
                actual_pep_col = None
                for col in candidate_peptide_columns:
                    if col in temp_df.columns:
                        actual_pep_col = col
                        break
                
                if not actual_pep_col and len(temp_df.columns) > 0:
                    actual_pep_col = temp_df.columns[0]
                    
                if actual_pep_col:
                    file_map = get_peptide_protein_map(temp_df, actual_pep_col)
                    
                    # Merge into master map
                    for pep, prot in file_map.items():
                        if pep in master_peptide_protein_map:
                            # If already exists, we might want to merge if they are different
                            # But usually they are the same protein accession.
                            # If we want to be super detailed:
                            existing_prots = set(master_peptide_protein_map[pep].split(';'))
                            new_prots = set(prot.split(';'))
                            combined = existing_prots.union(new_prots)
                            master_peptide_protein_map[pep] = ';'.join(sorted(combined))
                        else:
                            master_peptide_protein_map[pep] = prot
            except Exception as e:
                print(f"Warning: Could not extract protein mapping from {file}: {e}")

    if not all_dataframes:
        return pd.DataFrame()

    # Join all DataFrames into one, using the peptide index
    # The 'outer' join ensures that all peptides from all files are included
    final_df = pd.concat(all_dataframes, axis=1, join='outer')

    # Fill NaN values (peptides not found in a file) with 0, but only for numeric columns.
    # We always iterate AGGREGATION_STRATEGIES but now 'Associated Proteins' is gone, so most are numeric.
    # Text columns (like 'Charge States' if used) would need care.
    # 'Charge States' uses aggregate_unique_strings, so we shouldn't fill 0 there.
    
    # Check if the current metric is numeric-like (not string aggregation)
    is_numeric_metric = True
    current_strategy = AGGREGATION_STRATEGIES.get(metric_column)
    if current_strategy and current_strategy['agg_func'] in [aggregate_unique_strings, aggregate_protein_strings]:
        is_numeric_metric = False
        
    if is_numeric_metric:
        final_df = final_df.fillna(0)
    else:
        final_df = final_df.fillna("")

    # Ensure the index column (peptides) has a name.
    final_df.index.name = final_df.index.name or default_peptide_column
    
    # --- INSERT PROTEIN COLUMN ---
    # Create the protein series from the index
    protein_series = final_df.index.map(master_peptide_protein_map)
    
    # Fill missing proteins with specific placeholder or empty
    protein_series = protein_series.fillna("Unknown")
    
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