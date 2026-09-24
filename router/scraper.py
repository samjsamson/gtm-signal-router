import re
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from .models import Signals

KEYWORDS = {
    "b2b": ("enterprise", "business", "developer", "platform", "solution", "partner"),
    "ai": ("artificial intelligence", "generative ai", "machine learning", "ai"),
    "enterprise": ("enterprise", "organization", "organizations", "team", "teams"),
    "sales": ("sales", "revenue", "customer success", "support", "contact sales"),
}


DEMO_HOSTS = {'www.apple.com', 'apple.com', 'www.nvidia.com', 'nvidia.com',
              'www.tesla.com', 'tesla.com', 'about.meta.com', 'about.google', 'www.google.com'}


def extract_signals(url: str, hosted: bool = False) -> Signals:
    """Fetch only the supplied public homepage and derive transparent keyword signals."""
    try:
        for _ in range(5):
            parsed = urlparse(url)
            if hosted and (parsed.scheme != 'https' or parsed.hostname not in DEMO_HOSTS
                           or parsed.port not in (None, 443) or parsed.username or parsed.password):
                return Signals()
            with requests.get(url, timeout=12, headers={"User-Agent": "GTM-Signal-Router-Demo/1.0"},
                              allow_redirects=False, stream=True) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers['Location'])
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                for chunk in response.iter_content(8192):
                    size += len(chunk)
                    if size > 2_000_000:
                        break
                    chunks.append(chunk)
                html = b''.join(chunks)
                break
        else:
            return Signals()
        soup = BeautifulSoup(html, "html.parser")
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).lower()[:25000]
    except (requests.RequestException, ValueError):
        return Signals()

    found = [word for terms in KEYWORDS.values() for word in terms if word in text]
    b2b = any(word in text for word in KEYWORDS["b2b"])
    ai = any(word in text for word in KEYWORDS["ai"])
    enterprise = any(word in text for word in KEYWORDS["enterprise"])
    sales = any(word in text for word in KEYWORDS["sales"])
    motion = "enterprise" if b2b and enterprise else "self_serve" if "sign up" in text else "unknown"
    confidence = min(1.0, 0.35 + len(set(found)) * 0.08)
    return Signals(scraped=True, b2b=b2b, ai_related=ai, enterprise=enterprise,
                   sales_motion=motion, keywords=sorted(set(found)), excerpt=text[:500], confidence=confidence)
