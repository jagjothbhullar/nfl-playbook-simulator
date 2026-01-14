"""
NFL Playbook Simulator - Flask Web Application

Helps users understand defensive coverages and find offensive answers.
"""

from flask import Flask, render_template, jsonify, request
import json
import os

app = Flask(__name__)

# Load data files
def load_json(filename):
    data_path = os.path.join(os.path.dirname(__file__), "data", filename)
    with open(data_path, "r") as f:
        return json.load(f)

DEFENSES = load_json("defenses.json")
OFFENSE = load_json("offensive_concepts.json")


# =============================================================================
# SVG PLAY DIAGRAM GENERATOR
# =============================================================================

def generate_field_svg():
    """Generate base football field SVG"""
    return '''
    <rect x="0" y="0" width="400" height="250" fill="#2d5a27" />
    <line x1="0" y1="50" x2="400" y2="50" stroke="white" stroke-width="2" />
    <line x1="0" y1="100" x2="400" y2="100" stroke="white" stroke-width="2" />
    <line x1="0" y1="150" x2="400" y2="150" stroke="white" stroke-width="2" />
    <line x1="0" y1="200" x2="400" y2="200" stroke="white" stroke-width="2" />
    <line x1="200" y1="0" x2="200" y2="250" stroke="white" stroke-width="1" stroke-dasharray="5,5" />
    '''

def generate_offensive_formation_svg(formation="pro"):
    """Generate offensive player positions"""
    # Standard pro formation positions
    positions = {
        "C": (200, 150),
        "LG": (170, 150),
        "RG": (230, 150),
        "LT": (140, 150),
        "RT": (260, 150),
        "QB": (200, 175),
        "RB": (200, 200),
        "WR1": (50, 150),
        "WR2": (350, 150),
        "TE": (290, 150),
        "SLOT": (100, 150)
    }

    svg = ""
    for pos, (x, y) in positions.items():
        if pos in ["WR1", "WR2", "SLOT"]:
            # Receivers - circles
            svg += f'<circle cx="{x}" cy="{y}" r="10" fill="#1e90ff" stroke="white" stroke-width="2" />'
        elif pos == "QB":
            svg += f'<circle cx="{x}" cy="{y}" r="10" fill="#ffd700" stroke="white" stroke-width="2" />'
        elif pos == "RB":
            svg += f'<circle cx="{x}" cy="{y}" r="10" fill="#32cd32" stroke="white" stroke-width="2" />'
        elif pos == "TE":
            svg += f'<circle cx="{x}" cy="{y}" r="10" fill="#1e90ff" stroke="white" stroke-width="2" />'
        else:
            # O-line - squares
            svg += f'<rect x="{x-8}" y="{y-8}" width="16" height="16" fill="#4169e1" stroke="white" stroke-width="2" />'

    return svg

def generate_defensive_formation_svg(formation, coverage):
    """Generate defensive player positions based on formation and coverage"""

    # Base positions for different formations
    base_positions = {
        "4-3": {
            "DL": [(155, 135), (185, 135), (215, 135), (245, 135)],
            "LB": [(140, 110), (200, 105), (260, 110)],
            "CB": [(50, 100), (350, 100)],
            "S": [(150, 60), (250, 60)]
        },
        "3-4": {
            "DL": [(170, 135), (200, 135), (230, 135)],
            "LB": [(120, 115), (165, 110), (235, 110), (280, 115)],
            "CB": [(50, 100), (350, 100)],
            "S": [(150, 60), (250, 60)]
        },
        "nickel": {
            "DL": [(155, 135), (185, 135), (215, 135), (245, 135)],
            "LB": [(170, 110), (230, 110)],
            "CB": [(50, 100), (350, 100)],
            "SLOT_CB": [(100, 105)],
            "S": [(150, 50), (250, 50)]
        },
        "dime": {
            "DL": [(155, 135), (185, 135), (215, 135), (245, 135)],
            "LB": [(200, 105)],
            "CB": [(50, 100), (350, 100)],
            "SLOT_CB": [(100, 105), (300, 105)],
            "S": [(150, 45), (250, 45)]
        }
    }

    # Default to 4-3 if formation not found
    positions = base_positions.get(formation, base_positions["4-3"])

    # Adjust safety positions based on coverage
    if coverage in ["cover_2", "cover_2_man", "tampa_2", "cover_4", "cover_6"]:
        positions["S"] = [(120, 40), (280, 40)]  # Two deep
    elif coverage in ["cover_3", "cover_3_sky", "cover_3_cloud", "cover_1", "cover_1_robber"]:
        positions["S"] = [(200, 35), (250, 80)]  # Single high + SS in box
    elif coverage == "cover_0":
        positions["S"] = [(180, 95), (220, 95)]  # Both safeties in box

    svg = ""

    # Draw DL (triangles)
    for x, y in positions.get("DL", []):
        svg += f'<polygon points="{x},{y-10} {x-10},{y+8} {x+10},{y+8}" fill="#dc143c" stroke="white" stroke-width="2" />'

    # Draw LBs (triangles)
    for x, y in positions.get("LB", []):
        svg += f'<polygon points="{x},{y-10} {x-10},{y+8} {x+10},{y+8}" fill="#ff6347" stroke="white" stroke-width="2" />'

    # Draw CBs (triangles)
    for x, y in positions.get("CB", []):
        svg += f'<polygon points="{x},{y-10} {x-10},{y+8} {x+10},{y+8}" fill="#ff4500" stroke="white" stroke-width="2" />'

    # Draw Slot CB if present
    for x, y in positions.get("SLOT_CB", []):
        svg += f'<polygon points="{x},{y-10} {x-10},{y+8} {x+10},{y+8}" fill="#ff4500" stroke="white" stroke-width="2" />'

    # Draw Safeties (triangles)
    for x, y in positions.get("S", []):
        svg += f'<polygon points="{x},{y-10} {x-10},{y+8} {x+10},{y+8}" fill="#ff8c00" stroke="white" stroke-width="2" />'

    return svg

def generate_coverage_zones_svg(coverage):
    """Generate shaded zones showing coverage responsibilities"""

    zones = {
        "cover_0": [],  # No zones - pure man
        "cover_1": [
            {"type": "deep", "x": 50, "y": 0, "w": 300, "h": 60, "color": "rgba(255,165,0,0.3)"}
        ],
        "cover_2": [
            {"type": "deep", "x": 50, "y": 0, "w": 150, "h": 50, "color": "rgba(255,165,0,0.3)"},
            {"type": "deep", "x": 200, "y": 0, "w": 150, "h": 50, "color": "rgba(255,165,0,0.3)"},
            {"type": "flat", "x": 0, "y": 50, "w": 80, "h": 60, "color": "rgba(255,69,0,0.3)"},
            {"type": "flat", "x": 320, "y": 50, "w": 80, "h": 60, "color": "rgba(255,69,0,0.3)"}
        ],
        "tampa_2": [
            {"type": "deep", "x": 50, "y": 0, "w": 120, "h": 50, "color": "rgba(255,165,0,0.3)"},
            {"type": "deep", "x": 170, "y": 0, "w": 60, "h": 70, "color": "rgba(255,140,0,0.3)"},
            {"type": "deep", "x": 230, "y": 0, "w": 120, "h": 50, "color": "rgba(255,165,0,0.3)"}
        ],
        "cover_3": [
            {"type": "deep", "x": 0, "y": 0, "w": 133, "h": 60, "color": "rgba(255,69,0,0.3)"},
            {"type": "deep", "x": 133, "y": 0, "w": 134, "h": 60, "color": "rgba(255,165,0,0.3)"},
            {"type": "deep", "x": 267, "y": 0, "w": 133, "h": 60, "color": "rgba(255,69,0,0.3)"}
        ],
        "cover_4": [
            {"type": "deep", "x": 0, "y": 0, "w": 100, "h": 60, "color": "rgba(255,69,0,0.3)"},
            {"type": "deep", "x": 100, "y": 0, "w": 100, "h": 60, "color": "rgba(255,165,0,0.3)"},
            {"type": "deep", "x": 200, "y": 0, "w": 100, "h": 60, "color": "rgba(255,165,0,0.3)"},
            {"type": "deep", "x": 300, "y": 0, "w": 100, "h": 60, "color": "rgba(255,69,0,0.3)"}
        ]
    }

    svg = ""
    for zone in zones.get(coverage, []):
        svg += f'<rect x="{zone["x"]}" y="{zone["y"]}" width="{zone["w"]}" height="{zone["h"]}" fill="{zone["color"]}" />'

    return svg

def generate_soft_spots_svg(coverage):
    """Generate highlighted soft spots in the coverage"""

    spots = {
        "cover_0": [
            {"x": 200, "y": 30, "label": "Deep - no help!"}
        ],
        "cover_1": [
            {"x": 100, "y": 80, "label": "Crossers"},
            {"x": 300, "y": 80, "label": "Crossers"}
        ],
        "cover_2": [
            {"x": 200, "y": 25, "label": "Hole Shot"},
            {"x": 70, "y": 15, "label": "Corner"},
            {"x": 330, "y": 15, "label": "Corner"}
        ],
        "tampa_2": [
            {"x": 120, "y": 40, "label": "Seam"},
            {"x": 280, "y": 40, "label": "Seam"}
        ],
        "cover_3": [
            {"x": 100, "y": 50, "label": "Seam"},
            {"x": 300, "y": 50, "label": "Seam"},
            {"x": 50, "y": 90, "label": "Flat"},
            {"x": 350, "y": 90, "label": "Flat"}
        ],
        "cover_4": [
            {"x": 50, "y": 90, "label": "Flat"},
            {"x": 350, "y": 90, "label": "Flat"},
            {"x": 150, "y": 85, "label": "Curl"},
            {"x": 250, "y": 85, "label": "Curl"}
        ],
        "cover_2_man": [
            {"x": 200, "y": 75, "label": "Crossers"}
        ]
    }

    svg = ""
    for spot in spots.get(coverage, []):
        # Draw pulsing circle
        svg += f'''
        <circle cx="{spot["x"]}" cy="{spot["y"]}" r="15" fill="rgba(0,255,0,0.4)" stroke="#00ff00" stroke-width="2">
            <animate attributeName="r" values="12;18;12" dur="1.5s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.6;0.3;0.6" dur="1.5s" repeatCount="indefinite"/>
        </circle>
        <text x="{spot["x"]}" y="{spot["y"]+30}" text-anchor="middle" fill="#00ff00" font-size="10" font-weight="bold">{spot["label"]}</text>
        '''

    return svg

def generate_route_svg(concept):
    """Generate route lines for an offensive concept"""

    routes = {
        "four_verticals": [
            {"from": (50, 150), "to": (50, 20), "type": "go"},
            {"from": (100, 150), "to": (130, 20), "type": "seam"},
            {"from": (290, 150), "to": (270, 20), "type": "seam"},
            {"from": (350, 150), "to": (350, 20), "type": "go"}
        ],
        "curl_flat": [
            {"from": (50, 150), "to": (70, 80), "type": "curl"},
            {"from": (100, 150), "to": (50, 110), "type": "flat"}
        ],
        "smash": [
            {"from": (50, 150), "to": (60, 110), "type": "hitch"},
            {"from": (100, 150), "to": (40, 40), "type": "corner"}
        ],
        "mesh": [
            {"from": (50, 150), "to": (250, 110), "type": "cross"},
            {"from": (350, 150), "to": (150, 110), "type": "cross"}
        ],
        "levels": [
            {"from": (50, 150), "to": (200, 115), "type": "shallow"},
            {"from": (350, 150), "to": (200, 80), "type": "dig"}
        ],
        "flood": [
            {"from": (50, 150), "to": (30, 20), "type": "clear"},
            {"from": (100, 150), "to": (60, 50), "type": "corner"},
            {"from": (200, 200), "to": (40, 120), "type": "flat"}
        ],
        "slant_flat": [
            {"from": (50, 150), "to": (120, 100), "type": "slant"},
            {"from": (100, 150), "to": (50, 120), "type": "flat"}
        ]
    }

    svg = ""
    for route in routes.get(concept, []):
        x1, y1 = route["from"]
        x2, y2 = route["to"]

        # Draw route line with arrow
        svg += f'''
        <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#00bfff" stroke-width="3" marker-end="url(#arrowhead)" />
        '''

    return svg

def generate_play_diagram(formation, coverage, concept=None):
    """Generate complete play diagram SVG"""

    svg = f'''
    <svg viewBox="0 0 400 250" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#00bfff" />
            </marker>
        </defs>
        {generate_field_svg()}
        {generate_coverage_zones_svg(coverage)}
        {generate_soft_spots_svg(coverage)}
        {generate_offensive_formation_svg()}
        {generate_defensive_formation_svg(formation, coverage)}
    '''

    if concept:
        svg += generate_route_svg(concept)

    svg += '</svg>'
    return svg


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def index():
    """Main page"""
    return render_template("index.html")


@app.route("/api/formations")
def get_formations():
    """Get all defensive formations"""
    return jsonify({
        "formations": DEFENSES["formations"]
    })


@app.route("/api/coverages")
def get_coverages():
    """Get all coverage types"""
    return jsonify({
        "coverages": DEFENSES["coverages"]
    })


@app.route("/api/blitzes")
def get_blitzes():
    """Get all blitz packages"""
    return jsonify({
        "blitzes": DEFENSES["blitz_packages"]
    })


@app.route("/api/analyze", methods=["POST"])
def analyze_defense():
    """
    Analyze a defensive look and return offensive answers.

    POST /api/analyze
    {
        "formation": "4-3",
        "coverage": "cover_3",
        "blitz": "base"
    }
    """
    data = request.json
    formation = data.get("formation", "4-3")
    coverage = data.get("coverage", "cover_3")
    blitz = data.get("blitz", "base")

    # Get coverage details
    coverage_info = DEFENSES["coverages"].get(coverage, {})
    formation_info = DEFENSES["formations"].get(formation, {})
    blitz_info = DEFENSES["blitz_packages"].get(blitz, {})

    # Get offensive answers
    beaters = OFFENSE["coverage_beaters"].get(coverage, {})

    # If it's a blitz, also get blitz beaters
    if blitz != "base":
        blitz_beaters = OFFENSE["coverage_beaters"].get(blitz, {})
        # Merge blitz beaters with coverage beaters
        beaters = {
            "best_pass": list(set(beaters.get("best_pass", []) + blitz_beaters.get("best_pass", [])))[:5],
            "best_run": list(set(beaters.get("best_run", []) + blitz_beaters.get("best_run", [])))[:4],
            "priority": blitz_beaters.get("priority", beaters.get("priority", "")),
            "key_advice": blitz_beaters.get("key_advice", beaters.get("key_advice", ""))
        }

    # Build detailed pass concept info
    pass_concepts = []
    for concept_key in beaters.get("best_pass", []):
        concept = OFFENSE["pass_concepts"].get(concept_key, {})
        if concept:
            pass_concepts.append({
                "key": concept_key,
                "name": concept.get("name", concept_key),
                "routes": concept.get("routes", []),
                "description": concept.get("description", ""),
                "why_it_works": concept.get("why_it_works", {}).get(coverage, "Exploits coverage weakness"),
                "key_read": concept.get("key_read", ""),
                "hot_adjustment": concept.get("hot_adjustment", "")
            })

    # Build detailed run concept info
    run_concepts = []
    for concept_key in beaters.get("best_run", []):
        concept = OFFENSE["run_concepts"].get(concept_key, {})
        if concept:
            run_concepts.append({
                "key": concept_key,
                "name": concept.get("name", concept_key),
                "blocking": concept.get("blocking", ""),
                "description": concept.get("description", ""),
                "why_it_works": concept.get("why_it_works", {}).get(coverage,
                    concept.get("why_it_works", {}).get(formation, "Attacks defensive weakness")),
                "key_read": concept.get("key_read", "")
            })

    # Generate play diagram
    diagram = generate_play_diagram(formation, coverage)

    return jsonify({
        "status": "ok",
        "defense": {
            "formation": formation,
            "formation_info": formation_info,
            "coverage": coverage,
            "coverage_info": coverage_info,
            "blitz": blitz,
            "blitz_info": blitz_info
        },
        "offense": {
            "pass_concepts": pass_concepts,
            "run_concepts": run_concepts,
            "priority": beaters.get("priority", ""),
            "key_advice": beaters.get("key_advice", "")
        },
        "diagram_svg": diagram
    })


@app.route("/api/concept/<concept_type>/<concept_key>")
def get_concept_diagram(concept_type, concept_key):
    """Get a specific concept with diagram"""

    if concept_type == "pass":
        concept = OFFENSE["pass_concepts"].get(concept_key, {})
    else:
        concept = OFFENSE["run_concepts"].get(concept_key, {})

    if not concept:
        return jsonify({"status": "error", "message": "Concept not found"}), 404

    # Generate diagram with routes
    diagram = generate_play_diagram("4-3", "cover_3", concept_key)

    return jsonify({
        "status": "ok",
        "concept": concept,
        "diagram_svg": diagram
    })


@app.route("/api/all-plays")
def get_all_plays():
    """Get all defensive plays (formations + coverages + blitzes)"""

    plays = []

    for form_key, formation in DEFENSES["formations"].items():
        for cov_key, coverage in DEFENSES["coverages"].items():
            for blitz_key, blitz in DEFENSES["blitz_packages"].items():
                plays.append({
                    "id": f"{form_key}_{cov_key}_{blitz_key}",
                    "formation": form_key,
                    "formation_name": formation["name"],
                    "coverage": cov_key,
                    "coverage_name": coverage["name"],
                    "blitz": blitz_key,
                    "blitz_name": blitz["name"]
                })

    return jsonify({
        "plays": plays,
        "count": len(plays)
    })


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("Starting NFL Playbook Simulator...")
    print(f"Loaded {len(DEFENSES['formations'])} formations")
    print(f"Loaded {len(DEFENSES['coverages'])} coverages")
    print(f"Loaded {len(DEFENSES['blitz_packages'])} blitz packages")
    print(f"Total defensive combinations: {len(DEFENSES['formations']) * len(DEFENSES['coverages']) * len(DEFENSES['blitz_packages'])}")
    app.run(debug=True, port=5002)
