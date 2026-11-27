"""Draw the initial streamlines in Buckmaster, Coiculescu and Li, Hexagon 2611.00143v1, §3."""
from math import cos, exp, log, pi, sin, sqrt
from pathlib import Path

PERIOD = 6.0
HALF_WIDTH = 10.5
X_CENTER, Y_CENTER = 330, 143
SCALE = 30
MINT, AMBER = '#b9d6c8', '#ffc791'

def periodic_gaussian(q):
    """S(q) at eta = 0. Wrap to the central period before summing images."""
    q = (q + PERIOD / 2) % PERIOD - PERIOD / 2
    return sum(exp(-((q - n * PERIOD) ** 2) / 4) for n in range(-4, 5))

def transverse_height(q, level):
    return 2 * sqrt(max(0, log(periodic_gaussian(q) / level)))

def svg_point(q, eta):
    return f'{X_CENTER + q*SCALE:.2f},{Y_CENTER - eta*SCALE:.2f}'

def boundary_radius(level):
    left, right = 0, PERIOD/2
    for unused in range(50):
        middle = (left + right) / 2
        if periodic_gaussian(middle) > level:
            left = middle
        else:
            right = middle
    return (left + right) / 2

def contours(level):
    # Since -psi/2 = S(q) exp(-eta²/4), the transverse coordinate is explicit.
    if level < periodic_gaussian(PERIOD/2):
        for side in (-1, 1):
            points = []
            for j in range(125):
                q = -PERIOD/2 + PERIOD*j/124
                points.append(svg_point(q, side*transverse_height(q,level)))
            yield 'M' + ' '.join(points)
    else:
        radius = boundary_radius(level)
        points = []
        for j in range(120):
            theta = 2 * pi * j / 120
            x = radius * cos(theta)
            y = 0 if j in (0,60) else transverse_height(x,level)
            points.append(svg_point(x, y if sin(theta)>=0 else -y))
        yield 'M' + ' '.join(points) + 'Z'


def draw():
    svg = ['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 310" width="660" height="310" role="img" aria-labelledby="title desc"><title id="title">The initial periodic planar vortex train</title><desc id="desc">Contours of the Gaussian stream function in section 3 of the November 2026 Hexagon preprint by Tristan Buckmaster, Matei P. Coiculescu, and Chen Li. Closed streamlines circle three regularly spaced vortex centers. Weaker contours extend through adjacent periods. The plotted spacing is c = 6.</desc>
<metadata>Original level-set drawing after the initial stream function in Buckmaster, Coiculescu and Li, Non-Uniqueness of Leray–Hopf Solutions to the Unforced Three-Dimensional Navier–Stokes Equations (6 November 2026), section 3, p. 8. https://hexagonmath.org/2611.00143v1</metadata>
<defs>
  <clipPath id="crop"><rect x="15" y="6" width="630" height="267"/></clipPath>
  <linearGradient id="edge"><stop stop-color="white" stop-opacity=".12"/><stop offset=".08" stop-color="white" stop-opacity=".85"/><stop offset=".15" stop-color="white"/><stop offset=".85" stop-color="white"/><stop offset=".92" stop-color="white" stop-opacity=".85"/><stop offset="1" stop-color="white" stop-opacity=".12"/></linearGradient>
  <mask id="fade"><rect x="15" y="6" width="630" height="267" fill="url(#edge)"/></mask>
<g id="cell" fill="none" stroke-linejoin="round">''']
    levels = [.013,.020,.028,.040,.055,.073,.096,.123,.154,.182,.202,.220,.245,.28,.32,
              .365,.410,.455,.50,.55,.60,.65,.70,.75,.80,.85,.90,.94,.968,.987]
    for i,level in enumerate(levels):
        highlight = level in (.182,.455)
        tone = AMBER if highlight else MINT
        width = 1.75 if highlight else (.97 if i%4==0 else .72)
        opacity = .97 if highlight else (.76 if i%4==0 else .57)
        path = ''.join(contours(level))
        svg.append(f'<path d="{path}" stroke="{tone}" stroke-width="{width}" opacity="{opacity}"/>')
    svg.append('</g></defs><g clip-path="url(#crop)" mask="url(#fade)">')
    for cell in range(-2,3):
        svg.append(f'<use href="#cell" transform="translate({cell*PERIOD*SCALE:.1f} 0)"/>')
    svg.append('</g>')
    svg.append('<g fill="#c0d8c9" font-family="Georgia,serif" font-style="italic" font-size="18" text-anchor="middle">')
    for cell,label in [(-1,'−c'),(0,'0'),(1,'c')]:
        x = X_CENTER + cell*PERIOD*SCALE
        svg.append(f'<path d="M{x:.1f} 275v7" stroke="#8aa697" stroke-width=".9"/><text x="{x:.1f}" y="302">{label}</text>')
    svg.append('</g></svg>')
    return '\n'.join(svg)

if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "assets/figures/vortex-train.svg"
    output.write_text(draw() + "\n", encoding="utf-8")
