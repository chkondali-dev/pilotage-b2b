import pandas as pd

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"
fname = "Code%20MAGASIN%20Business%20Central.xlsx"

import requests
from io import BytesIO
r = requests.get(GITHUB_RAW + fname, timeout=30)
df = pd.read_excel(BytesIO(r.content))
print("COLUMNS:", df.columns.tolist())
print("SHAPE:", df.shape)
print(df.head(10))