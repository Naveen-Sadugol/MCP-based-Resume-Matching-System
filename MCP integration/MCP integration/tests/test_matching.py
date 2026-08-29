import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from matching_agent import score_resume


def test_score_resume_finds_shared_keywords():
    job = "Python SQL Docker Linux backend"

    resume = """
    Python developer with SQL and Linux experience
    """

    score, keywords = score_resume(job, resume)

    assert score > 0
    assert {"python", "sql", "linux"}.issubset(set(keywords))