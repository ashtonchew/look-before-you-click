"""Parse linearized accessibility trees and match click targets.

Input format: tab-separated lines with 7 columns:
  tag  name  text  class  description  position (top-left x&y)  size (w&h)

Position/size are formatted as tuples: (x, y) and (w, h).
Lines with fewer than 7 fields or an empty tag are skipped (handles
multi-line terminal text gracefully).
"""

import logging
import math
import re

from control.types import no_target_match

logger = logging.getLogger(__name__)

_TUPLE_RE = re.compile(r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)")

# Default radius for nearest-center fallback (pixels).
# Public: can be overridden at module level if needed.
NEAREST_RADIUS = 50.0


def parse_tree(a11y_tree_raw: str) -> list[dict]:
    """Parse a linearized a11y tree string into a list of node dicts.

    Skips the header line and any malformed lines.
    """
    if not a11y_tree_raw:
        return []

    lines = a11y_tree_raw.split("\n")
    nodes = []

    for i, line in enumerate(lines):
        # Skip header (first line)
        if i == 0:
            continue

        fields = line.split("\t")

        # Need exactly 7 fields with a non-empty tag
        if len(fields) != 7 or not fields[0].strip():
            continue

        tag = fields[0].strip()
        name = fields[1].strip()
        text = fields[2].strip()
        cls = fields[3].strip()
        desc = fields[4].strip()

        # Parse position and size tuples
        pos_match = _TUPLE_RE.search(fields[5])
        size_match = _TUPLE_RE.search(fields[6])

        if not pos_match or not size_match:
            logger.debug("a11y_parser: skipping node with bad position/size at line %d", i)
            continue

        nodes.append({
            "tag": tag,
            "name": name,
            "text": text,
            "class": cls,
            "description": desc,
            "x": float(pos_match.group(1)),
            "y": float(pos_match.group(2)),
            "w": float(size_match.group(1)),
            "h": float(size_match.group(2)),
        })

    return nodes


def match_target(nodes: list[dict], x: float, y: float) -> dict:
    """Match a click coordinate to the best a11y node.

    1. Find all nodes whose bounding box contains (x, y). Pick smallest area.
    2. If none contain the point, pick nearest node center within radius.
    3. If nothing is close, return no-match.
    """
    if not nodes:
        return no_target_match()

    # Pass 1: contains-point
    containing = []
    for node in nodes:
        nx, ny, nw, nh = node["x"], node["y"], node["w"], node["h"]
        if nx <= x <= nx + nw and ny <= y <= ny + nh:
            area = nw * nh
            containing.append((area, node))

    if containing:
        containing.sort(key=lambda t: t[0])
        best = containing[0][1]
        return _target_from_node(best, "contains_point")

    # Pass 2: nearest center within radius
    best_dist = float("inf")
    best_node = None
    for node in nodes:
        cx = node["x"] + node["w"] / 2
        cy = node["y"] + node["h"] / 2
        dist = math.hypot(x - cx, y - cy)
        if dist < best_dist:
            best_dist = dist
            best_node = node

    if best_node and best_dist <= NEAREST_RADIUS:
        return _target_from_node(best_node, "nearest_center")

    return no_target_match()


def _target_from_node(node: dict, method: str) -> dict:
    """Build target_* fields from a matched node."""
    return {
        "target_matched": True,
        "target_tag": node["tag"],
        "target_name": node["name"],
        "target_text": node["text"],
        "target_bounds": {
            "x": node["x"],
            "y": node["y"],
            "w": node["w"],
            "h": node["h"],
        },
        "target_match_method": method,
    }
