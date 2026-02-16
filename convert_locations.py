import pandas as pd
import json
import os

def convert_csv_to_json():
    # File check
    if not os.path.exists('world-cities.csv'):
        print("Error: 'world-cities.csv' file nahi mili. Please file ko same folder mein rakhen.")
        return

    print("Reading CSV file... (Thora time lag sakta hai)")
    try:
        df = pd.read_csv('world-cities.csv')
        
        locations = []
        
        # Data process karna
        for index, row in df.iterrows():
            city = str(row['name']).strip()
            country = str(row['country']).strip()
            subcountry = row['subcountry']
            
            # Format banana: "City, State, Country" (Serper ke liye best)
            if pd.notna(subcountry):
                full_location = f"{city}, {subcountry}, {country}"
            else:
                full_location = f"{city}, {country}"
                
            locations.append(full_location)
        
        # JSON save karna
        with open('locations.json', 'w', encoding='utf-8') as f:
            json.dump(locations, f, ensure_ascii=False)
            
        print(f"Success! {len(locations)} locations 'locations.json' mein save ho gayi hain.")
        
    except Exception as e:
        print(f"Koi masla hua: {e}")

if __name__ == "__main__":
    convert_csv_to_json()
