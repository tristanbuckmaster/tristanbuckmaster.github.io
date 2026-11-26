"""Draw two matched regularized vortex trains inspired by Hexagon 2611.00143v1.

    python3 bin/generate-vortex-movies.py /tmp/ring-lift --validate
    swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
    /tmp/encode-figure-frames /tmp/ring-lift/reference/frames /tmp/ring-lift/viscous-ring-lift.mp4 20
    /tmp/encode-figure-frames /tmp/ring-lift/perturbed/frames /tmp/ring-lift/viscous-ring-mode.mp4 20

Each isolated Gaussian core follows its exact radial viscous evolution. The
second run adds the solution of the angular-two equation linearized about
that same evolving core, with the growing isolated Euler eigenmode as seed.
We periodize the core streamfunctions with constant planar spacing and apply
Proposition 5.1's ring coordinates and radius-dependent ages. These illustrative
superpositions omit nonlinear interactions between cores and the 3D corrections.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.integrate import cumulative_trapezoid
from scipy.ndimage import label
from scipy.sparse import csr_matrix, diags, eye
from scipy.sparse.linalg import splu

from vortex_eigenmode import gaussian_mode


PERIOD, RADIUS = 8., 35.
VISCOSITY, MODE_AMPLITUDE, MODE_PHASE = .009, .09, math.pi/2
RING_RATIO = math.exp(PERIOD/RADIUS)
RADIAL_MIN, RADIAL_MAX = .37, 1.13
FIRST_TIME, FINAL_TIME = .05, 170.
FPS, FRAME_COUNT = 20, 241
LEVELS = np.array([.020,.031,.046,.062,.080,.102,.13,.16,.195,.235,.28,.33,.39,.46,.54,.63,.73,.84,.94])
GOLD_LEVELS = [.046,.235,.63]


def cubic_stencil(coordinates, spacing, size):
    """Indices and weights for periodic cardinal cubic interpolation."""
    position = np.asarray(coordinates) / spacing
    cell = np.floor(position).astype(int)
    t = position - cell
    weights = [t * (-.5 + t * (1 - .5*t)), 1 + t*t * (-2.5 + 1.5*t),
               t * (.5 + t * (2 - 1.5*t)), .5 * t*t * (t-1)]
    return [((cell + shift) % size, weight) for shift, weight in
            zip((-1, 0, 1, 2), weights)]


class RadialMode:
    """Viscous m=2 vorticity equation on a radial half-line, truncated at cutoff."""

    def __init__(self, dr, cutoff=48.):
        self.dr = dr
        self.r = dr*np.arange(1, int(cutoff/dr)+1)
        r = self.r
        # Δ₂ = ∂rr + ∂r/r − 4/r², with zero vorticity at both ends.
        lower, upper = 1/dr**2-1/(2*r*dr), 1/dr**2+1/(2*r*dr)
        self.laplacian = diags([lower[1:], -2/dr**2-4/r**2, upper[:-1]], [-1,0,1], format='csc')
        self.identity = eye(len(r), format='csc')
        self.heat_factors = {}
        seed = gaussian_mode()
        inside = r < seed.cutoff
        self.w = np.zeros_like(r, dtype=complex)
        self.w[inside] = seed.radial_factor(r[inside])*r[inside]**2*np.exp(1j*MODE_PHASE)
        self.time = 0.

    def stream(self, w):
        """Free-space Green inverse of Δ₂; choose its decaying exterior branch."""
        r = self.r
        integrand = w*r**3
        inner = cumulative_trapezoid(integrand, dx=self.dr, initial=0) + self.dr*integrand[0]/2
        outer = cumulative_trapezoid((w/r)[::-1], dx=self.dr, initial=0)[::-1]
        return -.25*(inner/r**2 + outer*r**2)

    def advection(self, t, w):
        a = 1+VISCOSITY*t
        x = self.r**2/(4*a)
        angular_speed = np.exp(-x)/a**2
        radial_gradient = angular_speed*(x-2)/a  # (∂r ω_reference)/r
        return 2j*(radial_gradient*self.stream(w) - angular_speed*w)

    def step(self, dt):
        # Second-order Strang split, Crank–Nicolson on the two half heat
        # steps and RK4 on the time-dependent inviscid linearization.
        if dt not in self.heat_factors:
            diffusion = VISCOSITY*dt/4*self.laplacian
            self.heat_factors[dt] = splu((self.identity-diffusion).astype(complex)), self.identity+diffusion
        implicit, explicit = self.heat_factors[dt]
        t = self.time
        w = implicit.solve(explicit@self.w)
        k1 = self.advection(t,w)
        k2 = self.advection(t+dt/2,w+dt*k1/2)
        k3 = self.advection(t+dt/2,w+dt*k2/2)
        k4 = self.advection(t+dt,w+dt*k3)
        w += dt/6*(k1+2*k2+2*k3+k4)
        self.w = implicit.solve(explicit@w)
        self.time += dt


class PeriodicCell:
    """Periodize the radial profiles onto one display cell, including the 1/r² tail."""

    def __init__(self, radial, nx, ny):
        self.shape = ny,nx
        height = 56.
        self.dx,self.dy = PERIOD/nx,height/ny
        self.q = np.fft.fftfreq(nx)*PERIOD
        self.eta = np.fft.fftfreq(ny)*height
        self.image_count = math.ceil(radial.r[-1]/PERIOD+.5)
        self.shifts = np.arange(-self.image_count,self.image_count+1)*PERIOD
        z = (self.q[None,:]+1j*self.eta[:,None]).ravel()
        self.tail = np.zeros_like(z)
        # Σ_n 1/(conj z+n c)², with the central pole subtracted analytically.
        k = np.pi/PERIOD
        at_origin = abs(z)<1.e-10
        self.tail[at_origin] = k**2/3
        others = z[~at_origin].conj()
        self.tail[~at_origin] = k**2/np.sin(k*others)**2-1/others**2
        rows,cols,weights = [],[],[]
        for shift in self.shifts:
            offset = z-shift
            distance = abs(offset)
            inside = distance < radial.r[-1]
            angle = np.angle(offset[inside])
            spin = np.exp(2j*angle)
            pos = distance[inside]/radial.dr
            left = np.floor(pos).astype(int)
            fraction = pos-left
            indices = np.flatnonzero(inside)
            rows.extend((indices,indices))
            cols.extend((left,left+1))
            weights.extend((spin*(1-fraction),spin*fraction))
            if shift != 0:
                self.tail -= 1/offset.conj()**2
            self.tail[~inside] += 1/offset[~inside].conj()**2
        self.interpolate = csr_matrix((np.concatenate(weights), (np.concatenate(rows),np.concatenate(cols))),
                                      shape=(len(z),len(radial.r)+1))

    def reference(self, t):
        a = 1+VISCOSITY*t
        row = np.exp(-(self.q[None,:]-self.shifts[:,None])**2/(4*a)).sum(axis=0)
        return np.exp(-self.eta[:,None]**2/(4*a))*row/a  # −ψ₀/2

    def mode(self, radial, stream):
        coefficient = stream[-1]*radial.r[-1]**2
        response = self.interpolate@np.r_[0j,stream] + coefficient*self.tail
        return -.5*response.real.reshape(self.shape)


class History:
    """Store one common age mesh and the two uniformly spaced periodic fields."""

    def __init__(self, dr=.035, dt0=.10, nx=64, ny=224):
        radial = RadialMode(dr)
        self.cell = PeriodicCell(radial,nx,ny)
        max_age = FINAL_TIME/RADIAL_MIN**2
        ages,reference,perturbed,amplitudes = [],[],[],[]
        mismatch = radial.advection(0.,radial.w)-gaussian_mode().eigenvalue*radial.w
        self.seed_residual = float(np.linalg.norm(mismatch)/np.linalg.norm(radial.w))
        while True:
            t = radial.time
            a = 1+VISCOSITY*t
            stream = radial.stream(radial.w)
            base = self.cell.reference(t)
            correction = MODE_AMPLITUDE*self.cell.mode(radial,stream)
            ages.append(t)
            reference.append(base.astype(np.float32))
            perturbed.append((base+correction).astype(np.float32))
            amplitudes.append(float(MODE_AMPLITUDE*a*np.max(abs(stream))/2))
            if t > max_age+1:
                break
            # The instantaneous angular speed decays like a^-2; coarse late
            # steps retain the same angular-phase resolution as at the inlet.
            dt = dt0*min(2**math.floor(math.log2(a*a)),128)
            for _ in range(4):
                radial.step(dt)
        self.ages = np.array(ages)
        self.fields = {'reference':np.array(reference), 'perturbed':np.array(perturbed)}
        self.max_isolated_ratio = max(amplitudes)


class MeridionalSampler:
    """Evaluate a common physical-time meridional slice at normalized r,z."""

    def __init__(self, history, branch, radius, z):
        self.history = history
        self.branch = branch
        self.radius = np.asarray(radius)
        q = RADIUS*np.log(self.radius)
        eta = RADIUS*np.asarray(z)[:,None]/self.radius[None,:]
        ny,nx = history.cell.shape
        self.x_stencil = cubic_stencil(q,history.cell.dx,nx)
        self.y_stencil = cubic_stencil(eta,history.cell.dy,ny)

    def sample(self, time):
        # First interpolate time and q at each radius, producing one vertical
        # grid column per image column; then interpolate its z-dependent eta.
        ages = self.history.ages
        local_age = time/self.radius**2
        i = np.clip(np.searchsorted(ages,local_age,side='right')-1,0,len(ages)-2)
        f = (local_age-ages[i])/(ages[i+1]-ages[i])
        fields = self.history.fields[self.branch]
        if np.any(f < 0) or np.any(f > 1):
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


def font(size):
    for path in ['/System/Library/Fonts/Supplemental/Georgia Italic.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf']:
        if Path(path).is_file():
            return ImageFont.truetype(path,size)
    return ImageFont.load_default(size=size)


class Plate:
    def __init__(self, history, branch):
        self.scale,self.width,self.plot_height = 2,630,230
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
        self.sampler = MeridionalSampler(history,branch,self.radius,z)
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
        rgb = self.bg + (color-self.bg)*coverage[:,:,None]*self.fade[None,:,None]
        s=self.scale
        chart=Image.new('RGB',(660*s,310*s),tuple(self.bg))
        chart.paste(Image.fromarray(rgb.round().astype('uint8')),(15*s,23*s))
        draw=ImageDraw.Draw(chart)
        for x in range(15,645,10):
            draw.line((x*s,138*s,(x+4)*s,138*s),fill=(86,111,101),width=s)
        for value,label in [(.4,'0.4'),(.6,'0.6'),(.8,'0.8'),(1,'1.0')]:
            x=(15+self.width*(value-RADIAL_MIN)/(RADIAL_MAX-RADIAL_MIN))*s
            draw.line((x,274*s,x,280*s),fill=(138,166,151),width=s)
            draw.text((x,298*s),label,font=self.label_font,anchor='ms',
                      fill=(194,216,201))
        draw.text((642*s,298*s),'r/R',font=self.label_font,anchor='rs',fill=(194,216,201))
        draw.text((642*s,18*s),f't = {time:.2f}',font=self.label_font,anchor='rs',
                  fill=(194,216,201),stroke_width=s,stroke_fill=tuple(self.bg))
        return chart.resize((660,310),Image.Resampling.LANCZOS)


def physical_time(index):
    # Log time allocates screen time to both the early mode and late overlap.
    fraction = index/(FRAME_COUNT-1)
    t0 = 9.
    return FIRST_TIME + t0*math.expm1(fraction*math.log1p((FINAL_TIME-FIRST_TIME)/t0))


def diagnostics(history):
    radius = np.linspace(RADIAL_MIN,RADIAL_MAX,511)
    z = np.linspace(-.14,.14,143)
    centers = [RING_RATIO**j for j in range(-12,4) if RADIAL_MIN < RING_RATIO**j < RADIAL_MAX]
    times = [FIRST_TIME,12.,35.,65.,FINAL_TIME]
    data = {}
    for branch in history.fields:
        sampler = MeridionalSampler(history,branch,radius,z)
        mirror,ncomponents,in_one_island = [],[],[]
        distinct_at_start = 0
        for t in times:
            field = sampler.sample(t)
            mirror.append(float(np.max(abs(field-field[::-1,:]))))
            regions,count = label(field > GOLD_LEVELS[0])
            ncomponents.append(count)
            labels = regions[len(z)//2,[np.abs(radius-c).argmin() for c in centers]]
            if t == FIRST_TIME:
                distinct_at_start = len(set(labels)-{0})
            in_one_island.append(bool(labels[0] and np.all(labels==labels[0])))
        if distinct_at_start != len(centers) or not in_one_island[-1]:
            raise ValueError(f"{branch} fixed amber contour must join all five initially separate cores")
        data[branch] = dict(mirror_errors=mirror, component_counts=ncomponents, connected_centers=in_one_island)
    if max(data['reference']['mirror_errors']) > 1.e-9 or max(data['perturbed']['mirror_errors']) < .012:
        raise ValueError(f'Reflection check failed: {data}')
    return dict(ring_centers=centers,physical_times=times,symmetry_and_overlap=data,
                isolated_stream_relative_perturbation_max=history.max_isolated_ratio,
                seed_euler_residual=history.seed_residual)


def validate(history):
    other = History(dr=.025,dt0=.05,nx=80,ny=320)
    radius,z = np.linspace(RADIAL_MIN,RADIAL_MAX,173),np.linspace(-.14,.14,59)
    result = {}
    for branch in history.fields:
        probe = MeridionalSampler(history,branch,radius,z)
        fine = MeridionalSampler(other,branch,radius,z)
        errors = [float(np.max(abs(probe.sample(t)-fine.sample(t)))) for t in (FIRST_TIME,8.,22.,50.,FINAL_TIME)]
        if max(errors) > .002:
            raise ValueError(f'{branch} refinement difference {errors}')
        result[branch] = errors
    if history.seed_residual > .001 or history.max_isolated_ratio > .35:
        raise ValueError('Check seed convergence and linear-amplitude range')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--preview',action='store_true',help='Render the first, middle and last frame')
    parser.add_argument('--no-render',action='store_true')
    args = parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    history = History()
    report = diagnostics(history)
    for name,slug in [('reference','lift'),('perturbed','mode')]:
        if args.no_render:
            continue
        plate = Plate(history,name)
        frames = args.directory/name/'frames'
        frames.mkdir(parents=True,exist_ok=True)
        indices = [0,FRAME_COUNT//2,FRAME_COUNT-1] if args.preview else range(FRAME_COUNT)
        for i in indices:
            frame = plate.frame(physical_time(i))
            frame.save(frames/f'{i:04}.png',compress_level=2)
            if i == 0:
                frame.save(args.directory/f'viscous-ring-{slug}-poster.webp',lossless=True,method=6)
        print(f'{name} frames written',flush=True)
    if args.validate:
        report['refinement_errors'] = validate(history)
    (args.directory/'run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
