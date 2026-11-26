"""Angular-two Euler eigenmode of the Gaussian vortex, Hexagon 2611.00143v1, §4.1.

The base streamfunction is -2 exp(-r²/4), with u = (-ψ_y, ψ_x) and ω = Δψ.
An isolated-vortex eigenmode supplies a smooth initial perturbation to the
viscous periodic-train experiment. Its eigenvalue belongs to the stationary
isolated Euler vortex, not to the subsequent time-dependent viscous train.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline
from scipy.linalg import eigvals
from scipy.optimize import root


@dataclass(frozen=True)
class GaussianMode:
    eigenvalue: complex
    # h(r)/r², for the vorticity eigenfunction h(r) exp(2iθ).
    radial_factor: CubicSpline
    cutoff: float


def _coefficient(r, eigenvalue):
    x = r*r/4
    angular_speed = np.exp(-x)
    return 2j*(x-2)*angular_speed / (eigenvalue + 2j*angular_speed)


@lru_cache(maxsize=1)
def gaussian_mode():
    """Solve the regular/decaying radial eigenproblem and normalize max |h|=1."""
    cutoff = 14.0  # Gaussian exponent -49; the streamfunction still has its r^-2 tail.
    # Locate the growing root with the radial Green inverse (4.1). The
    # midpoint discretization only selects a branch. Shooting refines it.
    spacing = 0.06
    r = (np.arange(180) + .5)*spacing
    ratio = np.minimum.outer(r, r)/np.maximum.outer(r, r)
    green = -.25 * ratio**2 * r[None, :] * spacing
    x = r*r/4
    omega = np.exp(-x)
    operator = -2j*np.diag(omega) + 2j*((x-2)*omega)[:, None]*green
    candidates = eigvals(operator)
    guess = candidates[candidates.real.argmax()]

    # For streamfunction φ=r²g the angular-two equation is
    # g'' + (5/r)g' = [2ik/(λ+2iΩ)]g. Enforce regularity at zero and
    # φ proportional to r^-2 at the outer boundary (r g' + 4g = 0).
    start = 1.e-5

    def integrate(eigenvalue, dense=False):
        a = _coefficient(0., eigenvalue)/12

        def ode(r, state):
            g, derivative = state
            return derivative, _coefficient(r, eigenvalue)*g - 5*derivative/r

        solution = solve_ivp(ode, (start, cutoff), (1+a*start**2, 2*a*start),
                             method='DOP853', rtol=1.e-10, atol=2.e-12, dense_output=dense)
        if not solution.success:
            raise RuntimeError(solution.message)
        return solution

    def boundary(parts):
        g, derivative = integrate(complex(*parts)).y[:, -1]
        mismatch = cutoff*derivative + 4*g
        return [mismatch.real, mismatch.imag]

    result = root(boundary, [guess.real, guess.imag], tol=1.e-10)
    eigenvalue = complex(*result.x)
    if not result.success or eigenvalue.real <= 0 or not -2 < eigenvalue.imag < 0:
        raise RuntimeError(f'Growing Gaussian eigenmode not found: {result.message}')
    r = np.linspace(0., cutoff, 4097)
    solution = integrate(eigenvalue, dense=True)
    g = solution.sol(np.maximum(r, start))[0]
    g[0] = 1.
    factor = _coefficient(r, eigenvalue)*g
    # Fix the arbitrary complex phase by requiring h(1) to be real positive.
    phase = np.angle(_coefficient(1., eigenvalue)*solution.sol(1.)[0])
    factor *= np.exp(-1j*phase)/np.max(r*r*np.abs(factor))
    return GaussianMode(eigenvalue, CubicSpline(r, factor, extrapolate=False), cutoff)


def periodic_vorticity(nx, ny, period, height, phase=0.0):
    """Periodize Re[e^(i phase) h(r)e^(2iθ)] on PlanarTrain's Fourier grid.

    phase is a complex phase in radians. An amplitude of 1 here corresponds
    to unit maximum absolute vorticity for one isolated vortex. The sum of
    neighboring copies has its own peak. Remove its quadrature mean so the
    planar Poisson solve is compatible on the doubly periodic simulation box.
    """
    mode = gaussian_mode()
    x = ((np.arange(nx)/nx + .5) % 1 - .5)[None, :]*period
    y = ((np.arange(ny)/ny + .5) % 1 - .5)[:, None]*height
    seed = np.zeros((ny, nx))
    phase_factor = np.exp(1j*phase)
    x_copies = math.floor(mode.cutoff/period + .5)
    y_copies = math.floor(mode.cutoff/height + .5)
    for j in range(-y_copies, y_copies+1):
        for i in range(-x_copies, x_copies+1):
            position = (x - i*period) + 1j*(y - j*height)
            radius = np.abs(position)
            inside = radius < mode.cutoff
            seed[inside] += (phase_factor*mode.radial_factor(radius[inside]) *
                             position[inside]**2).real
    return seed - seed.mean()
