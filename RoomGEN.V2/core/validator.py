from typing import List, Dict, Any
import math
from infrastructure.rules_schema import Rule, ValidationIssue

def measure_distance(item1: Dict[str, Any], item2: Dict[str, Any]) -> float:
    return math.sqrt((item1['x'] - item2['x'])**2 + (item1['y'] - item2['y'])**2)

def validate_rules(layout: Dict[str, Any], rules: List[Rule]) -> List[ValidationIssue]:
    report = []
    items = layout.get('items', [])
    # Convert list of items to dict for easier lookup by ID or type
    # For now, let's assume layout has named keys or we search by type
    # A simple mock approach: find first item of type 'target'
    
    def find_item_by_type(itype):
        for item in items:
            if item.get('type') == itype:
                return item
        return None

    for rule in rules:
        target_item = find_item_by_type(rule.target)
        if not target_item:
            continue # Target not present, maybe another rule handles "required" check
            
        if rule.constraint == "distance" and rule.reference:
            ref_item = find_item_by_type(rule.reference)
            if ref_item:
                dist = measure_distance(target_item, ref_item)
                if rule.max_value is not None and dist > rule.max_value:
                    report.append(ValidationIssue(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.message} (Naměřeno: {dist:.1f}, Max: {rule.max_value})",
                        affected_items=[rule.target, rule.reference]
                    ))
                    
    return report
