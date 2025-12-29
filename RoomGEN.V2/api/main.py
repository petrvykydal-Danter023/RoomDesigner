from typing import List, Dict, Any, Optional
import os
import sys

# Add V2 root to path to ensure imports work
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from fastapi import FastAPI, HTTPException, WebSocket
    from pydantic import BaseModel
except ImportError:
    # Mocking for environment without FastAPI installed
    class FastAPI:
        def post(self, path): return lambda x: x
        def websocket(self, path): return lambda x: x
    class BaseModel: pass
    print("⚠️  FastAPI not found. Running in mock mode.")

from core.room_parser import RoomParser
from solvers.wall_solver import WallSolver
from solvers.corner_solver import CornerSolver
from reporting.bom import BOMGenerator

app = FastAPI()

class SolveRequest(BaseModel):
    polygon: List[List[float]] # [[x,y], [x,y]...]
    required_items: List[str]

@app.post("/solve")
async def solve_layout(request: SolveRequest):
    """
    End-to-end solver endpoint.
    1. Parse Room
    2. Solve Corners
    3. Solve Walls
    4. Return Layout + BOM
    """
    try:
        # 1. Parse
        coords = [tuple(p) for p in request.polygon]
        walls, corners = RoomParser.parse_polygon(coords)
        
        all_items = []
        
        # 2. Solve Corners
        # Simple Logic: Solve all valid inner corners
        for corner in corners:
            if corner.type == 'inner':
                # Determine budget? Standard for now
                sol = CornerSolver.solve(corner, budget="standard")
                # Add corner item to list? 
                # It's an abstract reservation mostly, but let's visualize it
                all_items.append({
                    "type": sol['type'],
                    "wall_index": -1, # Corner
                    "meta": sol
                })
        
        # 3. Solve Walls
        # Distribute required items naive
        # Pass all requirements to first valid wall?
        # Or split?
        # For prototype: Try to put everything on Wall 1, then Wall 2...
        remaining_req = request.required_items[:]
        
        for wall in walls:
            if wall.available_length > 60:
                wall_items = WallSolver.solve(wall, required_items=remaining_req)
                for item in wall_items:
                    all_items.append(item)
                    if item['type'] in remaining_req:
                        remaining_req.remove(item['type'])
        
        # 4. BOM
        bom = BOMGenerator.generate_bom(all_items)
        
        return {
            "status": "success",
            "layout": all_items,
            "bom": bom,
            "remaining_unplaced": remaining_req
        }
        
    except Exception as e:
        # In real app, raise HTTPException
        return {"status": "error", "message": str(e)}

@app.websocket("/ws/configure")
async def websocket_endpoint(websocket: Any): # Type Any to avoid ImportErrors
    if hasattr(websocket, 'accept'):
        await websocket.accept()
        # Mock loop
        # while True:
        #    data = await websocket.receive_json()
        #    await websocket.send_json({"status": "validated"})
    pass
