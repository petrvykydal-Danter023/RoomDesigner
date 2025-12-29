import csv
from collections import defaultdict
from typing import List, Dict, Any, Tuple

class BOMGenerator:
    @staticmethod
    def generate_bom(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregates items and adds hidden hardware (legs, hinges).
        Returns a list of rows for the BOM.
        """
        summary = defaultdict(int)
        
        # 1. Count Visible Items
        for item in items:
            # Create a unique key based on type and width (e.g. "base_cabinet 60cm")
            width = item.get('width', 0)
            key = f"{item['type']} ({width}cm)"
            summary[key] += 1
            
            # 2. Add Hidden Items (Heuristics)
            if 'base_cabinet' in item['type'] or 'sink' in item['type'] or 'stove' in item['type']:
                # Assume base items need legs
                summary["Legs (Pack of 4)"] += 1
                
                # Plinth
                summary[f"Plinth {width}cm"] += 1
            
            if 'cabinet' in item['type']:
                # Assume 2 hinges per cabinet door
                summary["Hinge pair"] += 1
                summary["Handle"] += 1
                
        # 3. Format Output
        bom_rows = []
        for key, count in summary.items():
            bom_rows.append({
                "item_name": key,
                "quantity": count,
                "notes": "Generated from layout"
            })
            
        # Sort by name
        bom_rows.sort(key=lambda x: x['item_name'])
        return bom_rows

    @staticmethod
    def export_csv(bom_rows: List[Dict[str, Any]], filepath: str):
        """
        Writes BOM to a CSV file.
        """
        headers = ["item_name", "quantity", "notes"]
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(bom_rows)
            return True
        except Exception as e:
            print(f"Error writing CSV: {e}")
            return False
