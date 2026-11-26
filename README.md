# Tristan Buckmaster’s academic website

The site uses Jekyll and Jekyll-Scholar. It builds static HTML for the homepage, Publications, Media, Talks, and CV. Every page uses the same navigation, footer, and type styles.

## Preview and build

Use the repository’s Ruby environment and run the commands from its root.

```sh
bundle install
bundle exec jekyll serve --baseurl ""
```

Open the local URL printed by Jekyll. A standard build uses the configured Courant path, `/~tristanb`.

```sh
bundle exec jekyll build
```

The Courant web directory also holds public documents outside this repository, including `statement.pdf`. The legacy `deploy.sh` calls `server.sh`, which clears that directory before it uploads the build. A future Courant deployment should preserve those files and their existing URLs.

## Add or update content

| Content | Source | How to update it |
| --- | --- | --- |
| Publications | `_bibliography/papers.bib` | Add a BibTeX record with a unique key, title, authors, and year. The bibliography groups years automatically. Optional fields include abstract, DOI, arXiv, URL, PDF, and code. |
| Slop mark | `_data/slop_papers.yml` | Add or remove a paper’s BibTeX key. For a research highlight or news entry featuring that paper, set its `paper_key` to the same key. The ink mark links to the symbol key on Publications. |
| Talks | `_data/talks.json` | Add a dated record with a title, venue, and recording URL. A YouTube ID enables playback on the page. An event URL, local poster, and description are optional. |
| Media | `_data/media.json` | Add the publication date, headline, author, outlet, type, and article URL. Use the outlet name “Quanta Magazine” for Quanta entries. Use “News brief” for a dispatch. Optional companion links can point to audio or related coverage. |
| CV | `assets/pdf/CV.pdf`, `_data/cv_overview.json` | Replace the PDF at its stable URL. Update the displayed revision date and the appointments, education, and honors in the HTML overview. |
| Research highlights | `_data/highlights.yml`, `assets/figures/` | Add a record with a unique ID, tab label, summary, paper link, figure, dimensions, alt text, caption, and source link. For one movie, set `movie` to the MP4 and `figure` to its poster. For matched movies, add a `clips` list with a label, MP4 path (`movie`), poster, description, and caption for each. Give the clips a common timeline so the player can switch at the same instant. |
| What’s new | `_data/updates.yml` | Add a date, type, title, URL, and optional credit line. The homepage sorts entries by date. An archive item can be featured here when an announcement is appropriate. |
| Profile and funding | `_data/profile.yml`, `_pages/about.md` | Update contact information, affiliation, portrait, or award links in the data file. The opening and acknowledgment are arranged in the homepage template. |
| Navigation | `_data/navigation.yml` | Add or reorder a page title and site-relative path. The layout applies the site’s base URL. |

Page templates live in `_pages/`. The shared layout is `_layouts/plates.html`, and the shared header, footer, and research feature are in `_includes/plates/`. Page-specific styles and scripts are loaded through the `page_css` and `page_js` front matter fields. Publications and all research topics remain readable with JavaScript disabled.

## Research figures

- **Singularity formation.** Figure 1 on page 4 of Levent Alpöge and Tristan Buckmaster’s *Finite-time blow-up for the Navier–Stokes equations*. The image is the original two-panel figure, encoded losslessly as WebP. It shows the computed approximate profile at two vorticity magnitudes. [Pinned manuscript](https://github.com/tristanbuckmaster/navier-stokes/blob/b86ec358087c6d32c4bff73f4ef440f7491b426f/paper/finite-time-blow-up-navier-stokes.pdf)
- **Non-uniqueness.** Two movies show the viscous evolution of a periodic row of Gaussian vortices in the paper’s ring geometry. The second run adds the real part of the isolated Gaussian’s unstable angular-two vorticity eigenfunction at initialization. Both runs evolve by nonlinear planar Navier–Stokes. The figure draws a meridional slice of the raw ring lift at a common physical time `t`. Ring radii follow `rₙ = R exp(nc/R)`, and the local planar age is `s = R²t/r²`. The inner rings are smaller and evolve faster. The paper obtains solutions sharing a singular initial trace using a growing Floquet mode of the corrected three-dimensional flow. [Gaussian instability, §4](https://hexagonmath.org/pdf/2611.00143v1#page=12) · [Ring lift, §5](https://hexagonmath.org/pdf/2611.00143v1#page=19) · [Solution branches, §19](https://hexagonmath.org/pdf/2611.00143v1#page=74)
- **Wave turbulence.** The two Feynman trees in `assets/figures/wave-interaction-diagrams.svg` represent the cubic term in equation (3.2b) and the third-order term in Figure 1. Each vertex has the momentum rule `k = k₁ − k₂ + k₃`. Dashed branches denote conjugated factors. [Figure 1 and equation (4.2)](https://arxiv.org/pdf/1907.03667#page=12)

### Reproduce the two viscous ring simulations

Both movies use `R = 40`, period `c = 12`, and viscosity `ν = 0.001`. The horizontal axis spans `0.385 ≤ r/R ≤ 1.13`. Each step toward the axis scales the ring radius by `exp(−12/40) ≈ 0.74`. The 241 frames cover physical times `t = 0.2` through `32` with identical contour levels of the physical streamfunction `r ψ(q,η,s)`. This clock starts after the two smooth planar initializations at local age zero.

`bin/vortex_eigenmode.py` solves the radial eigenproblem in §4.1 for the isolated Gaussian. It selects the growing angular-two mode and refines the eigenvalue by radial shooting, giving `λ ≈ 0.0222674 − 0.2696523i`. The second run adds `0.04 Re[h(ρ) exp(2iθ)]`, periodized on the planar grid, with `max |h| = 1`. Its initial peak vorticity perturbation is about 2% of the base core’s peak. The generator evolves each field independently using dealiased Fourier advection and integrating-factor RK4, then interpolates the streamfunction in space and local age. The reported separation is the planar velocity difference in the `L²` norm over one computational cell.

On the movie grid the planar velocity separation increases from `0.116` at age `s = 0` to `0.325` at `s = 200`. A finer grid with half the time step gives `0.115` and `0.324`. These ages refer to the local planar clock. Near the last movie frame (`t = 32`), the ring at `r/R ≈ 0.4` has reached age 200.

The generator requires NumPy, SciPy, and Pillow 10.1 or newer. The macOS encoder uses AVFoundation.

```sh
python3 bin/generate-vortex-movies.py /tmp/ring-lift --validate
swiftc bin/encode-figure-frames.swift -o /tmp/encode-figure-frames
/tmp/encode-figure-frames /tmp/ring-lift/reference/frames /tmp/ring-lift/viscous-ring-lift.mp4 20
/tmp/encode-figure-frames /tmp/ring-lift/perturbed/frames /tmp/ring-lift/viscous-ring-mode.mp4 20
```

Copy the two MP4s and their `viscous-ring-*-poster.webp` files from `/tmp/ring-lift/` into `assets/figures/`. The checked-in videos play offline.
