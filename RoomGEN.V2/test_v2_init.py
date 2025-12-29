import sys
import os
import json

# Add V2 to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from infrastructure.rules_schema import load_rules_from_yaml, DomainManifest
from core.validator import validate_rules
from pydantic import ValidationError

def run_test():
    print("----------------------------------------------------------------")
    print("🏗️  RoomGEN V2 Initialization Test")
    print("----------------------------------------------------------------")

    # 1. Load Domain Manifest
    manifest_path = os.path.join(os.path.dirname(__file__), 'domains', 'kitchen', 'manifest.json')
    print(f"Loading Manifest: {manifest_path}")
    try:
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        manifest = DomainManifest(**manifest_data)
        print(f"✅ Manifest Loaded: {manifest.name} v{manifest.version}")
        print(f"   Required Items: {manifest.required_items}")
    except Exception as e:
        print(f"❌ Failed to load manifest: {e}")
        return

    # 2. Load Rules
    rules_path = os.path.join(os.path.dirname(__file__), 'domains', 'kitchen', 'rules.yaml')
    print(f"\nLoading Rules: {rules_path}")
    try:
        rules = load_rules_from_yaml(rules_path)
        print(f"✅ Rules Loaded: {len(rules)} rules found")
        for r in rules:
            print(f"   - {r.name}: {r.constraint} (Target: {r.target})")
    except Exception as e:
        print(f"❌ Failed to load rules: {e}")
        return

    # 3. Simulate Layout Validation
    print("\nRunning Validator Simulation...")
    
    # Case A: Good Layout
    good_layout = {
        "items": [
            {"type": "sink", "x": 100, "y": 0},
            {"type": "water_outlet", "x": 150, "y": 0} # Dist = 50 < 100
        ]
    }
    issues = validate_rules(good_layout, rules)
    if len(issues) == 0:
        print("✅ Case A (Good Layout): Passed (0 issues)")
    else:
        print(f"❌ Case A Failed: Expected 0 issues, got {len(issues)}")

    # Case B: Bad Layout (Sink too far)
    bad_layout = {
        "items": [
            {"type": "sink", "x": 100, "y": 0},
            {"type": "water_outlet", "x": 300, "y": 0} # Dist = 200 > 100
        ]
    }
    issues = validate_rules(bad_layout, rules)
    if len(issues) > 0:
        print(f"✅ Case B (Bad Layout): Caught issues as expected:")
        for issue in issues:
            print(f"   ⚠️  [{issue.severity.upper()}] {issue.message}")
    else:
        print("❌ Case B Failed: Expected issues but got none")

if __name__ == "__main__":
    run_test()
