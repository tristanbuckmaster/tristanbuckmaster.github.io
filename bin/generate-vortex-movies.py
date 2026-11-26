"""Generate matched viscous ring-lift movies for Hexagon 2611.00143v1, §§3–5.

    python3 bin/generate-vortex-movies.py /tmp/ring-lift --validate
    swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
    /tmp/encode-figure-frames /tmp/ring-lift/reference/frames /tmp/viscous-ring-lift.mp4 20
    /tmp/encode-figure-frames /tmp/ring-lift/perturbed/frames /tmp/viscous-ring-mode.mp4 20

Both runs solve the two-dimensional viscous vorticity equation with a periodic
Gaussian row on a tall box. The second initial condition adds the periodized
angular-two eigenfunction of the isolated Euler vortex. Each trajectory is
sampled through the same meridional ring chart from Proposition 5.1, at the
local planar age s = R²t/r² and fixed physical streamfunction contours. These
raw ring lifts illustrate the instability with different smooth planar inlets;
the theorem also requires a three-dimensional correction and a Floquet mode.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vortex_eigenmode import gaussian_mode, periodic_vorticity


PERIOD = 12.0
RADIUS = 40.0
VISCOSITY = .001
MODE_AMPLITUDE = .04
RING_RATIO = math.exp(PERIOD / RADIUS)
RADIAL_MIN, RADIAL_MAX = .385, 1.13       # r/R, increasing to the right
FIRST_TIME, FINAL_TIME = .2, 32.0         # common physical times t
FPS, FRAME_COUNT = 20, 241
PROBE_AGES = [0., 9.92, 19.84, 40., 80., 120., 160., 200.]
# Fixed absolute levels, more densely spaced near the smaller inner rings.
LEVELS = np.array([.020,.029,.040,.055,.073,.094,.116,.138,.160,.182,.205,
                   .230,.257,.286,.318,.352,.388,.425,.464,.504,.545,.587,
                   .630,.674,.719,.765,.812,.860,.909,.955,.989])
GOLD_LEVELS = [.138,.352,.674]


def cubic_stencil(coordinates, spacing, size):
    """Indices and weights for periodic cardinal cubic interpolation."""
    position = np.asarray(coordinates) / spacing
    cell = np.floor(position).astype(int)
    t = position - cell
    weights = [t * (-.5 + t * (1 - .5*t)), 1 + t*t * (-2.5 + 1.5*t),
               t * (.5 + t * (2 - 1.5*t)), .5 * t*t * (t-1)]
    return [((cell + shift) % size, weight) for shift, weight in
            zip((-1, 0, 1, 2), weights)]


class PlanarTrain:
    """Dealiased Fourier vorticity evolution with integrating-factor RK4."""

    def __init__(self, nx, ny, height, dt, amplitude):
        self.shape = ny, nx
        self.dx, self.dy = PERIOD/nx, height/ny
        self.dt, self.height = dt, height
        self.kx = 2*np.pi*np.fft.rfftfreq(nx, self.dx)[None, :]
        self.ky = 2*np.pi*np.fft.fftfreq(ny, self.dy)[:, None]
        self.k2 = self.kx**2 + self.ky**2
        self.inverse_laplacian = np.zeros_like(self.k2)
        self.inverse_laplacian[self.k2 > 0] = -1/self.k2[self.k2 > 0]
        modes_x = np.arange(nx//2+1)
        modes_y = np.abs(np.rint(np.fft.fftfreq(ny)*ny))
        self.keep = (3*modes_x[None,:] < nx) & (3*modes_y[:,None] < ny)
        self.half_heat = np.exp(-VISCOSITY*dt*self.k2/2)
        self.full_heat = self.half_heat**2
        # Fourier coefficients of the periodized Laplacian of -2 exp(-|x|²/4).
        self.omega = (8*np.pi*nx*ny/(PERIOD*height)*self.k2*
                      np.exp(-self.k2)*self.keep).astype(complex)
        self.seed_peak_fraction = 0.
        if amplitude:
            seed = amplitude*np.fft.rfft2(periodic_vorticity(nx,ny,PERIOD,height))*self.keep
            seed[0,0] = 0
            self.seed_peak_fraction = float(np.max(np.abs(self.real(seed))) /
                                            np.max(np.abs(self.real(self.omega))))
            self.omega += seed
        self.real_mode_weight = np.full((1, nx//2+1), 2.0)
        self.real_mode_weight[:, 0] = self.real_mode_weight[:, -1] = 1
        self.max_cfl = 0

    def real(self, spectrum):
        return np.fft.irfft2(spectrum, s=self.shape, axes=(-2,-1))

    def rhs(self, omega):
        psi = self.inverse_laplacian*omega
        u,v,wx,wy = self.real(np.stack((-1j*self.ky*psi,1j*self.kx*psi,
                                         1j*self.kx*omega,1j*self.ky*omega)))
        self.max_cfl = max(self.max_cfl,float(self.dt*np.max(
            np.abs(u)/self.dx + np.abs(v)/self.dy)))
        tendency = -np.fft.rfft2(u*wx+v*wy)*self.keep
        tendency[0,0] = 0
        return tendency

    def step(self):
        w,h = self.omega,self.dt
        a = self.rhs(w)
        b = self.rhs(self.half_heat*(w+h*a/2))
        c = self.rhs(self.half_heat*w + h*b/2)
        d = self.rhs(self.full_heat*w + h*self.half_heat*c)
        self.omega = self.full_heat*w + h/6*(self.full_heat*a +
                                               2*self.half_heat*(b+c) + d)

    def invariants(self):
        ny,nx = self.shape
        norm = PERIOD*self.height/(nx*ny)**2
        power = np.abs(self.omega)**2*self.real_mode_weight
        return (-.5*norm*np.sum(power*self.inverse_laplacian),
                .5*norm*np.sum(power))

    def stream_field(self):
        # Section 5 uses psi itself; a constant changes r*psi and the lifted
        # velocity. Match the decaying-cylinder gauge at the far vertical seam.
        psi = self.real(self.inverse_laplacian*self.omega)
        return -.5*(psi - np.mean(psi[self.shape[0]//2,:]))


class History:
    """Numerical history of -psi/2 on the periodic planar coordinate grid."""

    def __init__(self, amplitude, nx=96, ny=288, height=36, dt=.08, stride=4):
        self.flow = PlanarTrain(nx,ny,height,dt,amplitude)
        self.delta_age = stride*dt
        # The validation samples the exact crop edges as well as pixel centers.
        count = math.ceil(FINAL_TIME/RADIAL_MIN**2/self.delta_age) + 2
        self.fields = np.empty((count,ny,nx),dtype=np.float32)
        energy0,enstrophy0 = self.flow.invariants()
        dissipation,previous_enstrophy = 0.0,enstrophy0
        self.max_energy_increase = 0.0
        previous_energy = energy0
        for age_index in range(count):
            self.fields[age_index] = self.flow.stream_field()
            if age_index+1 == count:
                break
            for _ in range(stride):
                self.flow.step()
                energy,enstrophy = self.flow.invariants()
                self.max_energy_increase = max(self.max_energy_increase,
                                               energy-previous_energy)
                dissipation += VISCOSITY*dt*(enstrophy+previous_enstrophy)
                previous_energy,previous_enstrophy = energy,enstrophy
        self.metrics = dict(nx=nx,ny=ny,height=height,dt=dt,delta_age=self.delta_age,
                            initial_peak_vorticity_fraction=self.flow.seed_peak_fraction,
                            maximum_computed_age=(count-1)*self.delta_age,
                            maximum_cfl=self.flow.max_cfl,
                            max_energy_increase=self.max_energy_increase,
                            relative_energy_balance=abs(previous_energy-energy0+
                                                        dissipation)/energy0)


class MeridionalSampler:
    """Evaluate a common physical-time meridional slice at normalized r,z."""

    def __init__(self, history, radius, z):
        self.history = history
        self.radius = np.asarray(radius)
        q = RADIUS*np.log(self.radius)
        eta = RADIUS*np.asarray(z)[:,None]/self.radius[None,:]
        ny,nx = history.flow.shape
        self.x_stencil = cubic_stencil(q,history.flow.dx,nx)
        self.y_stencil = cubic_stencil(eta,history.flow.dy,ny)

    def sample(self, time):
        # First interpolate time and q at each radius, producing one vertical
        # grid column per image column; then interpolate its z-dependent eta.
        idx = time/self.radius**2/self.history.delta_age
        i = np.floor(idx).astype(int)
        f = idx-i
        fields = self.history.fields
        if np.any(i < 0) or np.any(i+1 >= len(fields)):
            raise ValueError('Requested physical slice lies outside planar age history')
        columns = np.zeros((len(self.radius),fields.shape[1]))
        for ix,weight in self.x_stencil:
            columns += weight[:,None]*((1-f[:,None])*fields[i,:,ix] +
                                        f[:,None]*fields[i+1,:,ix])
        result = np.zeros(self.y_stencil[0][0].shape)
        x = np.arange(len(self.radius))
        for iy,weight in self.y_stencil:
            result += weight*columns[x,iy]
        return result*self.radius[None,:]


def analytic_inlet(radius, z):
    q = RADIUS*np.log(radius)
    q = (q + PERIOD/2) % PERIOD - PERIOD/2
    eta = RADIUS*np.asarray(z)[:,None]/radius
    images = sum(np.exp(-((q-n*PERIOD)**2)/4) for n in range(-5,6))
    return radius*images*np.exp(-eta**2/4)


def font(size):
    for path in ['/System/Library/Fonts/Supplemental/Georgia Italic.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf']:
        if Path(path).is_file():
            return ImageFont.truetype(path,size)
    return ImageFont.load_default(size=size)


class Plate:
    def __init__(self, history):
        self.scale,self.width,self.plot_height = 2,630,260
        scale=self.scale
        self.bg = np.array([17,46,42])
        self.ink = np.array([192,218,204])
        self.gold = np.array([255,199,145])
        self.accent = np.isin(LEVELS,GOLD_LEVELS)
        self.widths = np.where(self.accent,1.6,np.where(np.arange(len(LEVELS))%4==0,1,.74))
        self.alphas = np.where(self.accent,.96,np.where(np.arange(len(LEVELS))%4==0,.81,.61))
        pitch = (RADIAL_MAX-RADIAL_MIN)/self.width
        x = (np.arange(self.width*scale)+.5)/scale
        z = (self.plot_height/2-(np.arange(self.plot_height*scale)+.5)/scale)*pitch
        self.radius = RADIAL_MIN + x*pitch
        self.sampler = MeridionalSampler(history,self.radius,z)
        self.fade = np.interp(x/self.width,[0,.035,.08,.94,.985,1],
                              [.25,.85,1,1,.85,.28])
        self.label_font = font(15*scale)

    def frame(self, time):
        field = self.sampler.sample(time)
        gy,gx=np.gradient(field)
        gradient=np.maximum(np.hypot(gy,gx),1e-12)
        upper=np.searchsorted(LEVELS,field)
        coverage=np.zeros_like(field)
        colored=np.zeros_like(field,dtype=bool)
        for idx in [upper-1,upper]:
            k=np.clip(idx,0,len(LEVELS)-1)
            distance=np.abs(field-LEVELS[k])/gradient
            alpha=np.clip(.5+.5*self.scale*self.widths[k]-distance,0,1)
            alpha*=self.alphas[k]*(idx>=0)*(idx<len(LEVELS))
            colored=np.where(alpha>coverage,self.accent[k],colored)
            coverage=np.maximum(alpha,coverage)
        color=np.where(colored[:,:,None],self.gold,self.ink)
        rgb=self.bg + (color-self.bg)*coverage[:,:,None]*self.fade[None,:,None]
        s=self.scale
        chart=Image.new('RGB',(660*s,310*s),tuple(self.bg))
        chart.paste(Image.fromarray(rgb.round().astype('uint8')),(15*s,8*s))
        draw=ImageDraw.Draw(chart)
        for value,label in [(.4,'0.4'),(.6,'0.6'),(.8,'0.8'),(1,'1.0')]:
            x=(15+self.width*(value-RADIAL_MIN)/(RADIAL_MAX-RADIAL_MIN))*s
            draw.line((x,274*s,x,280*s),fill=(138,166,151),width=s)
            draw.text((x,298*s),label,font=self.label_font,anchor='ms',
                      fill=(194,216,201))
        draw.text((642*s,298*s),'r/R',font=self.label_font,anchor='rs',fill=(194,216,201))
        draw.text((642*s,27*s),f't = {time:.2f}',font=self.label_font,anchor='rs',
                  fill=(194,216,201),stroke_width=s,stroke_fill=tuple(self.bg))
        return chart.resize((660,310),Image.Resampling.LANCZOS)


def velocity_distances(flow, reference, perturbed):
    """Planar velocity difference in unnormalized L² on one periodic cell."""
    difference = -2*(perturbed.astype(float)-reference)
    modes = np.fft.rfft2(difference,axes=(-2,-1))
    squared = np.abs(modes)**2*flow.k2*flow.real_mode_weight
    norms = np.sqrt(PERIOD*flow.height*squared.sum(axis=(-2,-1)))/np.prod(flow.shape)
    return norms.tolist()


def probe_fields(history):
    indices = np.rint(np.array(PROBE_AGES)/history.delta_age).astype(int)
    if not np.allclose(indices*history.delta_age,PROBE_AGES):
        raise ValueError('Probe ages must coincide with saved timesteps')
    return history.fields[indices]


def validate(histories, separations):
    radius = np.linspace(RADIAL_MIN, RADIAL_MAX, 161)
    z = np.linspace(-.14, .14, 81)
    times = [0, FIRST_TIME, 8., 16., 24., FINAL_TIME]
    probes,scale_errors = {},{}
    for name,hist in histories.items():
        sampler = MeridionalSampler(hist, radius, z)
        probes[name] = np.array([sampler.sample(t) for t in times])
        scaled = MeridionalSampler(hist, RING_RATIO*radius, RING_RATIO*z)
        scale_errors[name] = float(max(np.max(np.abs(scaled.sample(RING_RATIO**2*t)-RING_RATIO*field))
                                       for t,field in zip(times,probes[name])))
        if (scale_errors[name] > 2.e-8 or hist.max_energy_increase > 1.e-10
                or hist.metrics['relative_energy_balance'] > 1.e-6 or hist.flow.max_cfl >= 1.5):
            raise ValueError(f'{name} ring scaling, energy or timestep check failed: {hist.metrics}')
    inlet_error = np.max(np.abs(analytic_inlet(radius,z)-probes['reference'][0]))
    # Bound sampling error below 1% of the smallest contour interval.
    if inlet_error > .01*np.min(np.diff(LEVELS)):
        raise ValueError(f'Gaussian inlet error {inlet_error}')
    comparison = {}
    for refinement,params in [('refined',dict(nx=128,ny=384,dt=.04,stride=4)),
                              ('taller',dict(ny=360,height=45))]:
        sample_fields,errors = {},{}
        for name,amplitude in [('reference',0.), ('perturbed',MODE_AMPLITUDE)]:
            fine = History(amplitude, **params)
            sample_fields[name] = probe_fields(fine)
            sampler = MeridionalSampler(fine,radius,z)
            errors[name] = [float(np.max(np.abs(sampler.sample(t)-field)))
                            for t,field in zip(times,probes[name])]
            flow = fine.flow
            del sampler, fine
        fine_separation = velocity_distances(flow,sample_fields['reference'],sample_fields['perturbed'])
        relative_error = float(np.max(np.abs(np.array(fine_separation)/separations-1)))
        comparison[refinement] = dict(maximum_slice_errors=errors,planar_velocity_l2=fine_separation,
                                      maximum_relative_separation_error=relative_error)
        print(refinement, json.dumps(comparison[refinement]), flush=True)
        if (max(map(max,errors.values())) > .0025 or relative_error > .05
                or fine_separation[-1] < 2*fine_separation[0]):
            raise ValueError(f'{refinement} mesh or domain check failed')
    return dict(physical_times=times, grid_checks=comparison, inlet_error=float(inlet_error),
                discrete_scaling_errors=scale_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--preview',action='store_true',help='Render first, middle and last frame')
    parser.add_argument('--no-render',action='store_true')
    args = parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    histories = {}
    for name,amplitude,slug in [('reference',0.,'lift'), ('perturbed',MODE_AMPLITUDE,'mode')]:
        hist = History(amplitude)
        histories[name] = hist
        print(f'{name} integrated to planar age {hist.metrics["maximum_computed_age"]:.2f}',flush=True)
        if args.no_render:
            continue
        plate = Plate(hist)
        frames = args.directory/name/'frames'
        frames.mkdir(parents=True,exist_ok=True)
        indices = [0,FRAME_COUNT//2,FRAME_COUNT-1] if args.preview else range(FRAME_COUNT)
        for i in indices:
            t = FIRST_TIME + (FINAL_TIME-FIRST_TIME)*i/(FRAME_COUNT-1)
            frame = plate.frame(t)
            frame.save(frames/f'{i:04}.png',compress_level=2)
            if i == 0:
                frame.save(args.directory/f'viscous-ring-{slug}-poster.webp',lossless=True,method=6)
    reference,perturbed = histories['reference'],histories['perturbed']
    separation = velocity_distances(reference.flow,probe_fields(reference),probe_fields(perturbed))
    eigenvalue = gaussian_mode().eigenvalue
    report = dict(physical_time=[FIRST_TIME,FINAL_TIME],viscosity=VISCOSITY,
                  period=PERIOD,radius=RADIUS,ring_ratio=RING_RATIO,amplitude=MODE_AMPLITUDE,
                  isolated_eigenvalue=[eigenvalue.real,eigenvalue.imag],
                  runs={name:hist.metrics for name,hist in histories.items()},
                  planar_ages=PROBE_AGES,planar_velocity_l2=separation)
    if args.validate:
        report.update(validate(histories,separation))
    (args.directory/'run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
