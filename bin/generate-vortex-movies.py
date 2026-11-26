"""Generate matched viscous ring-lift movies for Hexagon 2611.00143v1, §§3–5.

    python3 bin/generate-vortex-movies.py /tmp/ring-lift --validate
    swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
    /tmp/encode-figure-frames /tmp/ring-lift/reference/frames /tmp/viscous-ring-lift.mp4 20
    /tmp/encode-figure-frames /tmp/ring-lift/perturbed/frames /tmp/viscous-ring-mode.mp4 20

Both movies solve the two-dimensional viscous vorticity equation on a periodic
row of Gaussian cores, grouped into pairs to illustrate merger. The second run
perturbs each inlet core with the angular-two mode of §4. We sample positive
planar vorticity in the meridional ring coordinates of Proposition 5.1, using
the local age s = R²t/r². The color scale and contours are fixed in both runs.
This closer pair geometry illustrates vortex interaction under regularization.
The paper uses a dilute evenly spaced train and a further 3D Floquet correction.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import label, maximum_filter

from vortex_eigenmode import gaussian_mode, periodic_vorticity


PERIOD = 18.0                       # repeat distance between pair centers
PAIR_SPACING = 4.3                  # distance between cores within each pair
RADIUS = 41.0
VISCOSITY = .062
MODE_AMPLITUDE = .075
RING_RATIO = math.exp(PERIOD / RADIUS)
RADIAL_MIN, RADIAL_MAX = .49, 1.30  # r/R
FIRST_TIME, FINAL_TIME = .05, 29.0
FPS, FRAME_COUNT = 20, 241
PROBE_AGES = [0., 2.4, 8., 16., 24., 32., 64., 96., 112.]
# Fixed levels of planar vorticity divided by the isolated inlet peak of 2.
LEVELS = np.array([.014,.023,.036,.055,.080,.115,.160,.215,.28,.36,.46,.58,.72,.87])
GOLD_LEVELS = [.036,.160,.58]


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
        # Translate a copy to either side of each periodic pair center. The
        # same two translation operators act on the reference and perturbation.
        pair = 2*np.cos(self.kx*PAIR_SPACING/2)
        self.omega *= pair
        self.seed_peak_fraction = 0.
        if amplitude:
            seed = amplitude*np.fft.rfft2(periodic_vorticity(nx,ny,PERIOD,height))*self.keep
            seed *= pair
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

class History:
    """Local vorticity history in units of an isolated Gaussian's inlet peak."""

    def __init__(self, amplitude, nx=96, ny=224, height=42, dt=.08, stride=2):
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
            self.fields[age_index] = .5*self.flow.real(self.flow.omega)
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
        return result


def analytic_inlet(radius, z):
    q = RADIUS*np.log(radius)
    q = (q + PERIOD/2) % PERIOD - PERIOD/2
    eta = RADIUS*np.asarray(z)[:,None]/radius
    vorticity = np.zeros_like(eta)
    for image in range(-2,3):
        for offset in (-PAIR_SPACING/2, PAIR_SPACING/2):
            distance = ((q-image*PERIOD-offset)**2 + eta**2)/4
            vorticity += (1-distance)*np.exp(-distance)
    return vorticity


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
        self.fill = np.array([115,143,112])
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
        # A fixed, saturating color scale keeps diffusing cores legible. The
        # highlighted contours retain their exact numerical level in all frames.
        positive = np.maximum(field,0.)
        tint = .78*positive/(positive+.12)
        ground = self.bg + (self.fill-self.bg)*tint[:,:,None]
        rgb = ground + (color-ground)*coverage[:,:,None]
        rgb = self.bg + (rgb-self.bg)*self.fade[None,:,None]
        s=self.scale
        chart=Image.new('RGB',(660*s,310*s),tuple(self.bg))
        chart.paste(Image.fromarray(rgb.round().astype('uint8')),(15*s,8*s))
        draw=ImageDraw.Draw(chart)
        for value,label in [(.6,'0.6'),(.8,'0.8'),(1,'1.0'),(1.2,'1.2')]:
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
    difference = 2*(perturbed.astype(float)-reference)
    modes = np.fft.rfft2(difference,axes=(-2,-1))
    squared = np.abs(modes)**2*(-flow.inverse_laplacian)*flow.real_mode_weight
    norms = np.sqrt(PERIOD*flow.height*squared.sum(axis=(-2,-1)))/np.prod(flow.shape)
    return norms.tolist()


def probe_fields(history):
    indices = np.rint(np.array(PROBE_AGES)/history.delta_age).astype(int)
    if not np.allclose(indices*history.delta_age,PROBE_AGES):
        raise ValueError('Probe ages must coincide with saved timesteps')
    return history.fields[indices]


def topology(history):
    """Count visible regularized-core peaks and islands on the plotted slice."""
    radius = np.linspace(RADIAL_MIN,RADIAL_MAX,631)
    z_max = .5*260*(RADIAL_MAX-RADIAL_MIN)/630
    plane = MeridionalSampler(history,radius,np.linspace(-z_max,z_max,261))
    result = {}
    for time in (FIRST_TIME,12.,FINAL_TIME):
        field = plane.sample(time)
        inside = field > LEVELS[0]
        peaks = inside & (field == maximum_filter(field,size=5))
        result[time] = dict(peaks=label(peaks)[1],islands=label(inside)[1])
    if [r['peaks'] for r in result.values()] != [4,3,2]:
        raise ValueError(f'Expected two pairs to merge from four visible peaks to two: {result}')
    if result[FIRST_TIME]['islands'] != 4 or result[FINAL_TIME]['islands'] != 2:
        raise ValueError(f'Fixed vorticity contour does not show pair merger: {result}')
    return result


def validate(histories, separations):
    radius = np.linspace(RADIAL_MIN, RADIAL_MAX, 161)
    z = np.linspace(-.14, .14, 81)
    times = [0, FIRST_TIME, 3., 9., 16., 24., FINAL_TIME]
    probes,scale_errors = {},{}
    for name,hist in histories.items():
        sampler = MeridionalSampler(hist, radius, z)
        probes[name] = np.array([sampler.sample(t) for t in times])
        scaled = MeridionalSampler(hist, RING_RATIO*radius, RING_RATIO*z)
        scale_errors[name] = float(max(np.max(np.abs(scaled.sample(RING_RATIO**2*t)-field))
                                       for t,field in zip(times,probes[name])))
        if (scale_errors[name] > 2.e-8 or hist.max_energy_increase > 1.e-10
                or hist.metrics['relative_energy_balance'] > 2.e-4 or hist.flow.max_cfl >= 1.5):
            raise ValueError(f'{name} ring scaling, energy or timestep check failed: {hist.metrics}')
    inlet_error = np.max(np.abs(analytic_inlet(radius,z)-probes['reference'][0]))
    # Cubic spatial interpolation should resolve the small visible intervals.
    if inlet_error > .04*np.min(np.diff(LEVELS)):
        raise ValueError(f'Gaussian inlet error {inlet_error}')
    comparison = {}
    for refinement,params in [('refined',dict(nx=144,ny=336,dt=.04,stride=2)),
                              ('taller',dict(ny=288,height=54))]:
        sample_fields,errors = {},{}
        for name,amplitude in [('reference',0.), ('perturbed',MODE_AMPLITUDE)]:
            fine = History(amplitude, **params)
            sample_fields[name] = probe_fields(fine)
            sampler = MeridionalSampler(fine,radius,z)
            errors[name] = [float(np.max(np.abs(sampler.sample(t)-field)))
                            for t,field in zip(times,probes[name])]
            topology(fine)
            flow = fine.flow
            del sampler, fine
        fine_separation = velocity_distances(flow,sample_fields['reference'],sample_fields['perturbed'])
        relative_error = float(np.max(np.abs(np.array(fine_separation)/separations-1)))
        comparison[refinement] = dict(maximum_slice_errors=errors,planar_velocity_l2=fine_separation,
                                      maximum_relative_separation_error=relative_error)
        print(refinement, json.dumps(comparison[refinement]), flush=True)
        # Inlet mode quadrature is compared to 1% of the isolated peak.
        # Once viscosity smooths it, require 0.1% throughout the merger.
        limit = np.where(np.array(times) < 3, .01, .001)
        if any(np.any(np.array(err) > limit) for err in errors.values()) or relative_error > .05:
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
            fraction = i/(FRAME_COUNT-1)
            t = FIRST_TIME + (FINAL_TIME-FIRST_TIME)*fraction**2*(3-2*fraction)
            frame = plate.frame(t)
            frame.save(frames/f'{i:04}.png',compress_level=2)
            if i == 0:
                frame.save(args.directory/f'viscous-ring-{slug}-poster.webp',lossless=True,method=6)
    reference,perturbed = histories['reference'],histories['perturbed']
    separation = velocity_distances(reference.flow,probe_fields(reference),probe_fields(perturbed))
    eigenvalue = gaussian_mode().eigenvalue
    report = dict(physical_time=[FIRST_TIME,FINAL_TIME],viscosity=VISCOSITY,
                  period=PERIOD,pair_spacing=PAIR_SPACING,radius=RADIUS,ring_ratio=RING_RATIO,
                  amplitude=MODE_AMPLITUDE,topology={n:topology(h) for n,h in histories.items()},
                  isolated_eigenvalue=[eigenvalue.real,eigenvalue.imag],
                  runs={name:hist.metrics for name,hist in histories.items()},
                  planar_ages=PROBE_AGES,planar_velocity_l2=separation)
    if args.validate:
        report.update(validate(histories,separation))
    (args.directory/'run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
