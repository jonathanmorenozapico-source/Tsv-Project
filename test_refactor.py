import pandas as pd
import analysis as an
import os

# Create a dummy TSV file
dummy_data = """Peptide\tScore\tProteins\tIntensity
PEP1\t100\tPROT_A\t1000
PEP2\t200\tPROT_B;PROT_C\t2000
PEP3\t300\tPROT_A\t3000
"""
filename = "dummy_test.tsv"
with open(filename, "w") as f:
    f.write(dummy_data)

try:
    print("Testing process_tsv_files...")
    # Call the function
    df = an.process_tsv_files([filename], ["Run1"], default_peptide_column='Peptide', metric_column='Total Intensity')
    
    print("\nResulting DataFrame Columns:")
    print(df.columns)
    
    print("\nResulting DataFrame Head:")
    print(df.head())

    # Assertions
    # Column 0 should be 'Protein'
    assert df.columns[0] == 'Protein', f"First column should be 'Protein', but got '{df.columns[0]}'"
    
    # Check content
    # PEP2 -> PROT_B (first one)
    assert df.loc['PEP2', 'Protein'] == 'PROT_B', f"Expected PROT_B for PEP2, got {df.loc['PEP2', 'Protein']}"
    
    print("\nSUCCESS: The refactor is working correctly. 'Protein' is the first column.")

except Exception as e:
    print(f"\nFAILURE: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Cleanup
    if os.path.exists(filename):
        os.remove(filename)
