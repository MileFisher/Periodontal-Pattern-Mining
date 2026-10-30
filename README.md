# Periodontal Pattern Mining

Mining site-level periodontal destruction patterns in NHANES 2009–2014 and testing whether they predict diabetes better than the CDC/AAP case definition.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name perio --display-name "Python (perio)"
```

Conda users: `conda env create -f environment.yml`.

## Run

```bash
python -m src.load   # downloads the 21 NHANES files, writes data/interim/
```

Then open the notebooks in `notebooks/` with the "Python (perio)" kernel.
