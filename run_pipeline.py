from pathlib import Path

from router.pipeline import run

ROOT = Path(__file__).parent
if __name__ == "__main__":
    for item in run(ROOT / "data/sample_leads.csv", ROOT / "data/gtm_router.db"):
        print(f"{item['company']}: {item['score']} → {item['route']}")
