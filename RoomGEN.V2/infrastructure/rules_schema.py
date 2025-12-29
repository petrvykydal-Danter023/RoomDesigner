from typing import List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field
import yaml

class Rule(BaseModel):
    name: str
    target: str
    constraint: str
    reference: Optional[str] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    buffer_size: Optional[float] = None
    type: Optional[str] = None
    severity: Literal["critical", "warning", "info"]
    message: str

class ValidationIssue(BaseModel):
    rule_name: str
    severity: Literal["critical", "warning", "info"]
    message: str
    affected_items: List[str]

class DomainManifest(BaseModel):
    name: str
    version: str
    required_items: List[str]
    description: str

def load_rules_from_yaml(file_path: str) -> List[Rule]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    rules = []
    if data and 'rules' in data:
        for r in data['rules']:
            rules.append(Rule(**r))
    return rules
