# RoomDesigner - Kitchen Layout Generator

Elastic Kitchen Engine - an intelligent kitchen layout generation system using constraint programming.

## Features

- **Elastic Zones**: Accordion-style zone allocation that stretches to fill available space
- **Smart Skinning**: IKEA Metod module fitting with intelligent type selection
- **Ghost Chef Simulation**: Ergonomic scoring based on simulated cooking workflows
- **Style Critic**: Visual harmony scoring (rhythm, alignment)
- **12+ Cabinet Types**: Detailed 3D models with realistic internal geometry

## Usage

```bash
python -m kitchen_core.main input.json
```

## Output

Generated files are saved to `outputs/run_TIMESTAMP/`:
- `layout.obj` - 3D model
- `layout.json` - Item placement data
- `input_snapshot.json` - Input copy for reproducibility

## Architecture

- `geometry.py` - Room and slope calculations
- `solver.py` - CP-SAT constraint solver with elastic zones
- `generator.py` - Procedural 3D geometry generation
- `ghost_chef.py` - Ergonomic simulation
- `style_grammar.py` - Visual scoring
- `skins/ikea_metod.py` - IKEA module fitting
