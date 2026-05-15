import csv

with open('columns_updated_new.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    print("Columns related to timeline and tracking:")
    for row in reader:
        if len(row) >= 3:
            col_name = row[0].lower()
            desc = row[2].lower()
            if any(word in col_name or word in desc for word in ['date', 'sap', 'progress', 'spud', 'rig_on', 'rig_off']):
                print(f"- {row[0]}: {row[2]}")
