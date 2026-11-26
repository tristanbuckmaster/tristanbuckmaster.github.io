"""Render the planar train in §3 of https://hexagonmath.org/2611.00143v1.

    python3 bin/generate-vortex-movies.py /tmp/vortex-frames --validate

Requires NumPy and Pillow. The two numbered PNG sequences use the same clock,
contours and passive-particle seeds. Encode each at 20 fps, e.g. on macOS:
    swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
    /tmp/encode-figure-frames /tmp/vortex-frames/viscous vortex-train-evolution.mp4 20
    /tmp/encode-figure-frames /tmp/vortex-frames/inviscid vortex-train-inviscid.mp4 20

This evolves the two-dimensional vorticity equation using the initial planar
train of §3, p. 8. The viscous run uses nu=1/6 and spacing c=6. The comparison
is two-dimensional Euler (nu=0). The paper's vertical coordinate extends to
infinity; here the vertical period is 30 and only its central strip is shown.
Fourier projection gives a divergence-free velocity; product dealiasing uses
the 2/3 rule. The displayed streamfunction is referenced to its horizontal
mean at the distant vertical seam. Tracers move with the fluid; contour levels
remain fixed in time. s=0…9 is nondimensional simulation time.

The validation option checks the energy balance and compares both runs
against a finer spatial and temporal discretization and a taller vertical
box. These movies illustrate the 2D building block used by the authors.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PERIOD = 6.0
DURATION = 9
FPS = 20
LEVELS = np.array([.013, .020, .028, .040, .055, .073, .096, .123, .154, .182,
                   .202, .220, .245, .280, .320, .365, .410, .455, .500, .550,
                   .600, .650, .700, .750, .800, .850, .900, .940, .968, .987])
SEEDS = np.array([[-.90, .35], [1.10, 1.45], [2.42, -.72]])


def cubic_stencil(coordinates, spacing, size):
    """Periodic cardinal cubic interpolation, also used for the passive tracers."""
    position = np.asarray(coordinates) / spacing
    cell = np.floor(position).astype(int)
    t = position - cell
    weights = [t * (-.5 + t * (1 - .5*t)), 1 + t*t * (-2.5 + 1.5*t),
               t * (.5 + t * (2 - 1.5*t)), .5 * t*t * (t-1)]
    return [((cell + shift) % size, weight) for shift, weight in
            zip((-1, 0, 1, 2), weights)]


class Flow:
    def __init__(self, viscosity, nx=64, ny=320, height=30.0, steps_per_frame=2):
        self.nx, self.ny, self.height = nx, ny, height
        self.viscosity = viscosity
        self.dt = 1 / (FPS * steps_per_frame)
        self.shape = (ny, nx)
        self.dx, self.dy = PERIOD/nx, height/ny
        self.kx = 2*np.pi*np.fft.rfftfreq(nx, self.dx)[None, :]
        self.ky = 2*np.pi*np.fft.fftfreq(ny, self.dy)[:, None]
        self.k2 = self.kx**2 + self.ky**2
        self.inverse_laplacian = np.zeros_like(self.k2)
        self.inverse_laplacian[self.k2 > 0] = -1/self.k2[self.k2 > 0]
        # Strict 2/3 truncation on each axis for the quadratic advection product.
        modes_x = np.arange(nx//2 + 1)
        modes_y = np.abs(np.rint(np.fft.fftfreq(ny)*ny))
        self.keep = (3*modes_x[None,:] < nx) & (3*modes_y[:,None] < ny)
        self.heat_half = np.exp(-viscosity*self.dt*self.k2/2)
        self.heat = self.heat_half**2
        # Fourier transform of -2 exp(-|x|²/4), periodized in x and y.
        # The paper is periodic only in x. Its cylinder is approximated by a
        # tall periodic box in y; a second, taller box checks the visible strip.
        self.omega = (8*np.pi*nx*ny/(PERIOD*height)*self.k2*
                      np.exp(-self.k2)*self.keep).astype(complex)
        self.particles = SEEDS.copy()
        self.real_mode_weight = np.full((1, nx//2+1), 2.0)
        self.real_mode_weight[:, 0] = self.real_mode_weight[:, -1] = 1
        self.max_cfl = 0.0

    def field(self, spectrum):
        return np.fft.irfft2(spectrum, s=self.shape, axes=(-2,-1))

    def rhs(self, omega, positions):
        psi = self.inverse_laplacian * omega
        u, v, wx, wy = self.field(np.stack((-1j*self.ky*psi, 1j*self.kx*psi,
                                             1j*self.kx*omega, 1j*self.ky*omega)))
        tendency = -np.fft.rfft2(u*wx + v*wy) * self.keep
        tendency[0,0] = 0
        xst = cubic_stencil(positions[:,0], self.dx, self.nx)
        yst = cubic_stencil(positions[:,1], self.dy, self.ny)
        particle_velocity = np.zeros_like(positions)
        for ix, xweight in xst:
            for iy, yweight in yst:
                weight = xweight * yweight
                particle_velocity[:,0] += weight * u[iy,ix]
                particle_velocity[:,1] += weight * v[iy,ix]
        self.max_cfl = max(self.max_cfl, float(self.dt*np.max(
            np.abs(u)/self.dx + np.abs(v)/self.dy)))
        return tendency, particle_velocity

    def step(self):
        # Classical RK4 in the integrating factor for viscosity. Tracers use
        # the corresponding velocity field at each of the four RK stages.
        w, p, h = self.omega, self.particles, self.dt
        a, pa = self.rhs(w,p)
        b, pb = self.rhs(self.heat_half * (w + .5*h*a), p + .5*h*pa)
        c, pc = self.rhs(self.heat_half*w + .5*h*b, p + .5*h*pb)
        d, pd = self.rhs(self.heat*w + h*self.heat_half*c, p + h*pc)
        self.omega = self.heat*w + h/6*(self.heat*a + 2*self.heat_half*(b+c) + d)
        self.particles = p + h/6*(pa + 2*pb + 2*pc + pd)

    def display_field(self):
        # Restore the open-cylinder stream-function gauge at the remote seam.
        psi = self.field(self.inverse_laplacian * self.omega)
        return -.5 * (psi - np.mean(psi[self.ny//2,:]))

    def invariants(self):
        norm = PERIOD*self.height/(self.nx*self.ny)**2
        power = np.abs(self.omega)**2*self.real_mode_weight
        energy = -.5*norm*float(np.sum(power*self.inverse_laplacian))
        enstrophy = .5*norm*float(np.sum(power))
        return energy,enstrophy

    def sample(self, field, q, eta):
        cols = sum(field[:, ix]*weight[None,:] for ix,weight in
                   cubic_stencil(q, self.dx, self.nx))
        return sum(cols[iy,:]*weight[:,None] for iy,weight in
                   cubic_stencil(eta, self.dy, self.ny))


class Renderer:
    def __init__(self):
        self.scale = 2
        self.background = np.array([17,46,42])
        self.mint = np.array([185,214,200])
        self.gold = np.array([255,199,145])
        self.highlight = np.isin(LEVELS,[.182,.455])
        self.widths = np.where(self.highlight,1.75,
                               np.where(np.arange(len(LEVELS))%4==0,.97,.72))
        self.alphas = np.where(self.highlight,.97,
                               np.where(np.arange(len(LEVELS))%4==0,.76,.57))
        self.scale_space = 30
        self.xc, self.yc = 330,143
        self.q = ((np.arange(180*self.scale)+.5)/self.scale - 90)/self.scale_space
        self.eta = (self.yc - (6+(np.arange(267*self.scale)+.5)/self.scale))/self.scale_space
        x_screen = (np.arange(630*self.scale)+.5)/self.scale + 15
        self.tile_columns = np.floor(((x_screen-self.xc+90)*self.scale) %
                                     (180*self.scale)).astype(int)
        self.fade = np.interp((x_screen-15)/630,[0,.08,.15,.85,.92,1],
                              [.12,.85,1,1,.85,.12])
        font_candidates = [
            '/System/Library/Fonts/Supplemental/Georgia Italic.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf']
        self.font = ImageFont.load_default(size=16*self.scale)
        for filename in font_candidates:
            if Path(filename).exists():
                self.font = ImageFont.truetype(filename, 16*self.scale)
                break

    def draw(self, flow, time):
        # Render fixed isocontours by signed distance in screen pixels. Compute
        # a single horizontal period, then tile it exactly like the static SVG.
        field = flow.sample(flow.display_field(), self.q, self.eta)
        gy = np.gradient(field, axis=0)
        gx = (np.roll(field,-1,axis=1) - np.roll(field,1,axis=1))/2
        gradient = np.maximum(np.hypot(gy,gx),1e-12)
        hi = np.searchsorted(LEVELS,field)
        coverage = np.zeros_like(field)
        colored = np.zeros_like(field,dtype=bool)
        for idx in [hi-1,hi]:
            clipped = np.clip(idx,0,len(LEVELS)-1)
            distance = np.abs(field - LEVELS[clipped])/gradient
            alpha = np.clip(.5+.5*self.scale*self.widths[clipped]-distance,0,1)
            alpha *= self.alphas[clipped]*(idx>=0)*(idx<len(LEVELS))
            colored = np.where(alpha>coverage,self.highlight[clipped],colored)
            coverage = np.maximum(alpha,coverage)
        color = np.where(colored[:,:,None],self.gold,self.mint)
        rgb = self.background + (color-self.background)*coverage[:,:,None]
        display = (self.background + (rgb[:,self.tile_columns]-self.background)*
                   self.fade[None,:,None]).round().astype('uint8')
        s=self.scale
        chart=Image.new('RGB',(660*s,310*s),tuple(self.background))
        chart.paste(Image.fromarray(display),(15*s,6*s))
        draw=ImageDraw.Draw(chart)
        # Three passive material markers per period, identical in both runs.
        for x,y in flow.particles:
            for copy in range(-3,4):
                dx=self.xc + self.scale_space*(x+copy*PERIOD)
                dy=self.yc - self.scale_space*y
                if 20 < dx < 640 and 9 < dy < 269:
                    radius=2.5
                    draw.ellipse(((dx-radius)*s,(dy-radius)*s,(dx+radius)*s,(dy+radius)*s),
                                 fill=(246,237,205),outline=(55,72,58),width=s)
        for period,label in [(-1,'−c'),(0,'0'),(1,'c')]:
            x=(self.xc+period*180)*s
            draw.line((x,275*s,x,281*s),fill=(138,166,151),width=s)
            draw.text((x,297*s),label,font=self.font,anchor='ms',fill=(194,216,201))
        draw.text((643*s,297*s),f's = {time:.1f}',font=self.font,
                  anchor='rs',fill=(177,202,186))
        return chart.resize((660,310),Image.Resampling.LANCZOS)


def simulate(viscosity, frame_dir=None, nx=64, ny=320, height=30.0, steps_per_frame=2):
    flow = Flow(viscosity,nx,ny,height,steps_per_frame)
    initial_energy,initial_enstrophy=flow.invariants()
    old_enstrophy=initial_enstrophy
    dissipated=0
    snapshots={}
    max_divergence=0.0
    renderer=Renderer() if frame_dir else None
    if frame_dir:
        frame_dir.mkdir(parents=True,exist_ok=True)
    for frame in range(DURATION*FPS+1):
        if frame and frame%60==0:
            print(f'nu={viscosity:.5f}, {nx}×{ny}, s={frame/FPS:g}',flush=True)
        if frame_dir:
            image=renderer.draw(flow,frame/FPS)
            image.save(frame_dir/f'{frame:04}.png',compress_level=2)
            if frame==0 and viscosity>0:
                image.save(frame_dir.parent/'vortex-train-poster.webp',lossless=True,method=6)
        if frame % FPS == 0:
            psi=flow.inverse_laplacian*flow.omega
            uhat,vhat=-1j*flow.ky*psi,1j*flow.kx*psi
            divergence=flow.field(1j*flow.kx*uhat + 1j*flow.ky*vhat)
            max_divergence=max(max_divergence,float(np.max(np.abs(divergence))))
            sample=flow.sample(flow.display_field(),
                               np.linspace(-3,3,96,endpoint=False),
                               np.linspace(-5,5,141))
            snapshots[frame//FPS]=(sample,flow.particles.copy())
        if frame<DURATION*FPS:
            for _ in range(steps_per_frame):
                flow.step()
                _,enstrophy=flow.invariants()
                dissipated+=viscosity*flow.dt*(old_enstrophy+enstrophy)
                old_enstrophy=enstrophy
    energy,enstrophy=flow.invariants()
    metrics=dict(nx=nx,ny=ny,height=height,dt=flow.dt,viscosity=viscosity,
                 duration=DURATION,initial_energy=initial_energy,final_energy=energy,
                 initial_enstrophy=initial_enstrophy,final_enstrophy=enstrophy,
                 relative_energy_balance_residual=abs(energy-initial_energy+dissipated)/initial_energy,
                 relative_enstrophy_change=(enstrophy-initial_enstrophy)/initial_enstrophy,
                 maximum_cfl=flow.max_cfl,maximum_divergence=max_divergence)
    return snapshots,metrics


def max_discrepancy(a,b):
    return dict(maximum_stream_function_over_two_abs=float(max(
                    np.max(np.abs(x-b[t][0])) for t,(x,p) in a.items())),
                maximum_tracer_position_abs=float(max(
                    np.max(np.linalg.norm(p-b[t][1],axis=1)) for t,(x,p) in a.items())))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    report={}
    for mode,viscosity in [('viscous',1/6),('inviscid',0.0)]:
        print(f'Simulating {mode} train',flush=True)
        base,metrics=simulate(viscosity,None if args.no_render else args.directory/mode)
        if args.validate:
            fine,_=simulate(viscosity,nx=96,ny=480,steps_per_frame=4)
            padded,_=simulate(viscosity,nx=64,ny=448,height=42)
            metrics['higher_resolution']=max_discrepancy(base,fine)
            metrics['taller_domain']=max_discrepancy(base,padded)
            if metrics['maximum_divergence'] > 1e-12:
                raise ValueError(f'Velocity divergence check failed: {metrics}')
            if metrics['relative_energy_balance_residual'] > 2e-5:
                raise ValueError(f'Energy balance check failed: {metrics}')
            if viscosity==0 and abs(metrics['relative_enstrophy_change']) > 1e-5:
                raise ValueError(f'Enstrophy balance check failed: {metrics}')
            for key in ('higher_resolution','taller_domain'):
                if (metrics[key]['maximum_stream_function_over_two_abs'] > 2e-4 or
                    metrics[key]['maximum_tracer_position_abs'] > .01):
                    raise ValueError(f'{key} comparison failed: {metrics}')
        report[mode]=metrics
        print(json.dumps(metrics,indent=2),flush=True)
    report_name='validation.json' if args.validate else 'run.json'
    (args.directory/report_name).write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
