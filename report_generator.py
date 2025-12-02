import os
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_pdf_report(filepath, title, dataframe, column_mapping=None):
    """
    Generates a multi-page PDF report from a pandas DataFrame, splitting wide tables
    across multiple pages by chunking columns to ensure readability.

    Args:
        filepath (str): The path where the PDF file will be saved.
        title (str): The main title of the report (the metric used).
        dataframe (pd.DataFrame): The DataFrame with the data to display.
        column_mapping (dict, optional): A dictionary mapping short column names to full paths.
    """
    # 1. Configuración de Página: Forzar siempre landscape para más ancho.
    doc = SimpleDocTemplate(filepath, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    header_style = styles['Normal'] # Estilo para los encabezados
    cell_style = styles['Normal']   # Estilo para las celdas de datos (para el word wrap)
    
    story = []

    # 1. Report Title
    story.append(Paragraph(title, styles['h1']))
    story.append(Spacer(1, 0.2*inch))

    # 2. Column Legend (if provided)
    if column_mapping:
        story.append(Paragraph("Column Legend (Short Name -> Full Path):", styles['h3']))
        legend_text = [f"<b>{short}</b>: {full}" for short, full in sorted(column_mapping.items())]
        story.append(Paragraph('<br/>'.join(legend_text), styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

    # 3. Preparación de Datos: Resetear el índice para que la columna de péptidos sea la columna 0.
    df_reset = dataframe.reset_index()
    peptide_col_name = df_reset.columns[0]
    data_cols = df_reset.columns[1:]

    # 4. Lógica de Chunking de Columnas
    MAX_DATA_COLS_PER_PAGE = 6 # Reducido a 6 para dar más espacio a la columna de péptidos
    num_chunks = -(-len(data_cols) // MAX_DATA_COLS_PER_PAGE) # Ceiling division

    for i in range(num_chunks):
        start_col_idx = i * MAX_DATA_COLS_PER_PAGE
        end_col_idx = start_col_idx + MAX_DATA_COLS_PER_PAGE
        
        # Seleccionar el bloque de columnas de datos
        current_cols_chunk = data_cols[start_col_idx:end_col_idx]
        
        # Crear el sub-dataframe: siempre incluye la columna de péptidos
        sub_df_cols = [peptide_col_name] + list(current_cols_chunk)
        sub_df = df_reset[sub_df_cols]

        # Añadir subtítulo para el bloque de columnas
        if num_chunks > 1:
            story.append(Paragraph(f"Columns {start_col_idx + 1} to {min(end_col_idx, len(data_cols))}", styles['h3']))
            story.append(Spacer(1, 0.1*inch))

        # 5. Generación de Tablas
        # Usar Paragraph en los encabezados para permitir el ajuste de texto (word wrap)
        header = [Paragraph(f'<b>{col}</b>', header_style) for col in sub_df.columns]
        
        # Convertir datos a lista, aplicando Paragraph a la columna de péptidos para el ajuste de texto
        data_rows = []
        for index, row in sub_df.iterrows():
            row_data = [Paragraph(str(row.iloc[0]), cell_style)] # Columna de péptido con word wrap
            row_data.extend(row.iloc[1:].astype(str).tolist())   # El resto de columnas como texto normal
            data_rows.append(row_data)
        data = [header] + data_rows

        pdf_table = Table(data, repeatRows=1) # repeatRows=1 repite el encabezado en cada página vertical

        # 6. Estilos
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),      # Header background color
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),             # Center align everything
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),            # Centrar verticalmente todo el contenido
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),             # Vertically align header text
            ('FONTSIZE', (0, 0), (-1, -1), 8),                 # Reduce font size
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),            # Padding in header
            ('GRID', (0, 0), (-1, -1), 1, colors.black)        # Grid for the whole table
        ])
        pdf_table.setStyle(style)

        # Alternar colores de fila para mejor legibilidad
        for row_idx, row in enumerate(data[1:], start=1):
            bg_color = colors.whitesmoke if row_idx % 2 == 0 else colors.beige
            style.add('BACKGROUND', (0, row_idx), (-1, row_idx), bg_color)

        story.append(pdf_table)
        
        # Añadir un salto de página después de cada tabla, excepto la última
        if i < num_chunks - 1:
            story.append(PageBreak())

    # Build the PDF
    doc.build(story)