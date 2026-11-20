import pandas as pd
from estat_multivariada.pipeline import profile, slugify

def test_slugify():
    assert slugify("Euroemp.csv") == "euroemp_csv"

def test_profile():
    result=profile(pd.DataFrame({"x":[1,1,None],"group":["a","a","b"]}))
    assert result["rows"]==3 and result["duplicate_rows"]==1 and result["missing_cells"]==1
