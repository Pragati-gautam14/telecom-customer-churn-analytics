"""Download the IBM Telco Customer Churn sample dataset into data/raw/."""
from pathlib import Path
import urllib.request
URL = "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "telco_customer_churn.csv"
if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists():
        urllib.request.urlretrieve(URL, OUT)
    print("data ready:", OUT)
