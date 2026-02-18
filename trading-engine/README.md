# Trading Engine Sidecar

Uses **Python 3.13.x** (e.g. 3.13.12). `pandas_ta>=0.3` works with this version.

The project has a **`.venv`** created with:
`C:\Users\cloudbase-admin\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv`

To **build the sidecar exe** using this venv:
```bash
cd trading-engine
.venv\Scripts\activate
pip install -r requirements.txt
python build.py
```

## If Python 3.13 is installed in a different path

Use that interpreter for install and build:

```bash
# Replace with your actual Python 3.13 path, e.g.:
# C:\Python313\python.exe
# or: py -3.13

<path-to-python-3.13>\python.exe -m pip install -r requirements.txt
<path-to-python-3.13>\python.exe build.py
```

Or set up a venv with 3.13 and use it:

```bash
<path-to-python-3.13>\python.exe -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python build.py
```
