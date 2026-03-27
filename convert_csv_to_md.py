import pandas as pd
import os

files_to_convert = [
    r"C:\Users\sagar\Downloads\Bashira-Intelligence (2)\Results (1).csv",
    r"C:\Users\sagar\Downloads\Bashira-Intelligence (2)\Bashira-Intelligence\columns_clean.csv",
    r"C:\Users\sagar\Downloads\Bashira-Intelligence (2)\Bashira-Intelligence\columns_updated.csv"
]

for file_path in files_to_convert:
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            md_path = file_path.replace('.csv', '.md')
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(df.to_markdown(index=False))
            print(f"Successfully converted {file_path} to {md_path}")
        except Exception as e:
            print(f"Failed to convert {file_path}: {e}")
    else:
        print(f"File not found: {file_path}")
