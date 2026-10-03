# PhiAxis guide catalog

Canonical names, UI behavior, and implementation status for the overlay.

## Available since 0.5.0

| Canonical type | Settings flag | Construction | Modes |
| --- | --- | --- | --- |
| Rule of Thirds | `thirds` | 1/3 and 2/3 divisions | Full, horizontal only, vertical only |
| Phi Grid | `golden` | φ divisions at ~38.2% and ~61.8% | Symmetric |
| Golden Spiral | `golden_spiral` | Circular quarter-arcs inside a fitted golden rectangle | 4 rotations, mirror |
| Golden Rectangles | `golden_rectangles` | The spiral's golden rectangle and the cuts into nested squares | 4 rotations, mirror (matches the spiral) |
| Golden Triangle | `golden_triangle` | Main diagonal plus two true perpendiculars | 4 rotations, mirror |
| Dynamic Symmetry | `dynamic_symmetry` | Diagonals plus four reciprocals | Basic (frame), or a fitted root-2, -3, -4, -5 or root-φ rectangle with its reciprocal divisions |
| Diagonal Phi | `diagonal_phi` | Corner lines through φ-related edge divisions | 4 rotations, mirror |
| Radiating Grid | `radiating` | Configurable spokes from a movable focal point | Focal X/Y, 4–64 spokes |
| Tunnel | `tunnel` | Inner frame connected to outer-frame corners | Focal X/Y, inner scale |
| Center Lines | `center_cross` | Full-frame center axes | Both, horizontal only, vertical only |
| Pyramid | `pyramid` | Two sides and a base | Upright/inverted, adjustable apex X/inset |
| Vanishing Point | `vanishing_point` | Frame corners converging at a focal point | Lower corners or all corners |
| Leading Lines | `leading_lines` | Adjustable two-line wedge | Focal X/Y, lower-edge width |
| Circle | `circle` | Inscribed circle | Focal X/Y, scale |
| Center Crosshair | `crosshair` | Short center-axis marker | Symmetric |
| Frame Diagonals | `diagonals` | Both corner-to-corner diagonals | Symmetric |
| Single Diagonal | `single_diagonal` | One corner-to-corner line | 4 rotations, mirror pick the corner pair |
| Safe Area | `safe_area` | Inset rectangle | Independent X/Y margins |
| V Shape | `v_shape` | Two lines from the top edge meeting at an apex | Upright/inverted, apex X/depth, opening width |
| L Shape | `l_shape` | Vertical stroke meeting a horizontal base | 4 rotations, mirror, corner inset |
| S Curve | `s_curve` | One sine period across the frame | 4 rotations, mirror, curvature |
| C Curve | `c_curve` | Half-ellipse opening to one side | 4 rotations, mirror, curvature |
| Balance | `balance` | Two equal circles on a beam, fulcrum at the center | Spacing, size |
| Asymmetric Balance | `asymmetric_balance` | Two independent circles; fulcrum at their area-weighted center | Position and size of each region |

All types can be combined, fitted to the camera frame, and drawn in the active
viewport or all visible viewports. Every guide can use the shared style or its
own color, opacity, thickness and line style (solid, dashed, dotted).

Orientation and mirror are shared by the asymmetric guides: golden spiral,
golden rectangles, golden triangle, diagonal phi, single diagonal, L shape and
the S and C curves.

## Presets

Built in: Photography, Cinematography, Portrait and Landscape.
Users can save the current guide selection and parameters as named presets,
stored beside the saved defaults. A preset changes which guides show and their
parameters; it never changes colors, thickness, line styles or coverage.

## Possible future work

- Per-guide focal points (radiating, tunnel, vanishing point, leading lines and
  circle currently share one)
- Offsetting root rectangles within the frame instead of centering them
- Grid presets for specific aspect ratios, such as 2.39:1 anamorphic

The reference-image labels “golden spiral” and “Fibonacci spiral” map to one
Golden Spiral control. “Golden section,” “golden ratio grid,” and “phi grid” map
to Phi Grid. The loose “diagonal” example maps to Single Diagonal.

Reference behavior: Adobe exposes orientation cycling for Triangle and Golden
Spiral crop overlays, which informs the shared rotation/mirror controls:
https://helpx.adobe.com/archive/en/photoshop/cc/2015/photoshop_reference.pdf
