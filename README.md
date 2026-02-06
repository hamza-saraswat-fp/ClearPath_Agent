# ClearPath Agent

Automated workflow configuration generator for FieldPulse ClearPath. Converts natural language workflow descriptions into importable Excel templates.

## Overview

ClearPath Agent is a multi-agent pipeline that transforms customer workflow descriptions into FieldPulse-compatible Excel import files.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Customer     │     │    Agent 1:     │     │    Agent 2:     │     │  Excel Pipeline │
│  Natural Lang   │ ──▶ │  Conversational │ ──▶ │   Relational    │ ──▶ │  (This Repo)    │
│  Description    │     │     Agent       │     │     Agent       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                StructuredIntent
                                                     (JSON)
```

### Agent Pipeline

| Agent | Role | Output |
|-------|------|--------|
| **Agent 1: Conversational** | Interviews customer about their workflow needs | Natural language requirements |
| **Agent 2: Relational** | Converts requirements to structured schema using ClearPath knowledge graph | `StructuredIntent` JSON |
| **Excel Pipeline** | Transforms schema to FieldPulse import format | `.xlsx` file |

## This Repository: Excel Pipeline

This repo contains the **Excel Pipeline** - the final stage that converts `StructuredIntent` JSON into a FieldPulse-compatible Excel import template.

### Pipeline Flow

```
StructuredIntent (JSON)
        │
        ▼
┌───────────────────────┐
│   IntentTransformer   │  Add missing fields (category, color, icon, etc.)
│                       │  Pass through all actions/widgets - no filtering
└───────────────────────┘
        │
        ▼
   StatusActionFlow (Internal Model)
        │
        ▼
┌───────────────────────┐
│ ConfigToExcelConverter│  Flatten to Excel row schemas
│                       │  Format booleans as T/F
└───────────────────────┘
        │
        ▼
   ExcelImportTemplate
        │
        ▼
┌───────────────────────┐
│    ExcelGenerator     │  Generate .xlsx with 3 tabs
│                       │  Match FieldPulse format exactly
└───────────────────────┘
        │
        ▼
   ClearPath_Import.xlsx
```

### Output Format

The generated Excel file has 3 tabs matching FieldPulse's import template:

**Tab 1: Job Custom Status** (Horizontal layout)
```
| Custom Job Status Workflow Name | Status Name 1 | Status Type 1 | Status Color 1 | Status Icon 1 | ...
```

**Tab 2: Action Buttons**
```
| Custom Job Status Workflow Name | Status Action Flow Name | Job Status Name | User Role | Button Action | Action Option | Action Button Name |
```

**Tab 3: Focus View + Status Instruction**
```
| Custom Job Status Workflow Name | Status Action Flow Name | Job Status Name | User Role | Status Instructions | Display Action Menu | ... | Focus View Layout | Restrict... |
```

## Installation

```bash
# Clone the repository
git clone https://github.com/hamza-saraswat-fp/ClearPath_Agent.git
cd ClearPath_Agent

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
import json
from pathlib import Path
from clearpath_agent.services import IntentTransformer, ConfigToExcelConverter, ExcelGenerator
from clearpath_agent.models.intent_schemas import StructuredIntent

# Load StructuredIntent from Relational Agent
intent_data = json.loads(Path('intent.json').read_text())
intent = StructuredIntent(**intent_data)

# Transform to internal model
transformer = IntentTransformer()
flow = transformer.transform(intent)

# Convert to Excel template
converter = ConfigToExcelConverter()
template = converter.convert(flow)

# Generate Excel file
generator = ExcelGenerator()
output_path = generator.generate(template, Path('output/workflow.xlsx'), overwrite=True)

print(f"Generated: {output_path}")
```

### One-liner Convenience Method

```python
from clearpath_agent.services import ConfigToExcelConverter

converter = ConfigToExcelConverter()
output_path = converter.convert_and_generate(flow, Path('output/workflow.xlsx'))
```

## Input Schema: StructuredIntent

The pipeline expects a `StructuredIntent` JSON from the Relational Agent:

```json
{
  "workflow_name": "Residential Service Call Workflow",
  "workflow_description": "End-to-end workflow for residential service calls...",
  "job_types": ["Service Call", "Repair"],
  "steps": [
    {
      "step_name": "Job Created",
      "sequence": 1,
      "role_mentioned": "Dispatcher",
      "action_phrases": [
        {
          "phrase": "sends a confirmation text to the customer",
          "suggested_type": "action:send_customer_communication",
          "confidence": 0.95
        }
      ],
      "information_needs": [
        {
          "phrase": "customer contact",
          "suggested_type": "widget:job_customer_contact",
          "confidence": 0.95
        }
      ]
    }
  ]
}
```

## Project Structure

```
src/clearpath_agent/
├── models/
│   ├── entities.py          # Internal data models (StatusActionFlow, Status, etc.)
│   ├── excel_schemas.py     # Excel row schemas (FieldPulse format)
│   ├── intent_schemas.py    # StructuredIntent input schema
│   └── enums.py             # StatusCategory, UserRole enums
├── services/
│   ├── intent_transformer.py    # StructuredIntent → StatusActionFlow
│   ├── config_to_excel.py       # StatusActionFlow → ExcelImportTemplate
│   └── excel_generator.py       # ExcelImportTemplate → .xlsx file
└── __init__.py
```

## Design Principles

1. **Pass-through Architecture**: The pipeline passes through all actions and widgets from the Relational Agent without validation or filtering. The Relational Agent is trained on the ClearPath knowledge graph and is trusted.

2. **Add Only What's Missing**: IntentTransformer only adds fields that the Relational Agent doesn't provide (category, color, icon, focus view settings, etc.).

3. **Match FieldPulse Exactly**: The Excel output matches FieldPulse's import template format exactly - column names, boolean format (T/F), horizontal status layout.

## License

Proprietary - FieldPulse Internal Use Only
