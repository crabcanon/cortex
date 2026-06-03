from __future__ import annotations

FINANCE_URLS: list[dict[str, object]] = [
    {
        "name": "Federal Reserve FOMC calendar",
        "url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "format_hint": "html",
        "expected_keywords": ["fomc", "federal reserve", "monetary policy"],
    },
    {
        "name": "Federal Reserve Financial Stability Report PDF",
        "url": "https://www.federalreserve.gov/publications/files/financial-stability-report-20241122.pdf",
        "format_hint": "pdf",
        "expected_keywords": ["financial stability", "vulnerabilities", "leverage"],
    },
    {
        "name": "IMF data API GDP growth",
        "url": "https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/USA",
        "format_hint": "json",
        "expected_keywords": ["NGDP_RPCH", "USA", "values"],
    },
    {
        "name": "World Bank Global Economic Prospects",
        "url": "https://openknowledge.worldbank.org/server/api/core/bitstreams/a9e24256-baf8-45bb-9075-75e437e1d6f7/content",
        "format_hint": "pdf",
        "expected_keywords": ["global economic prospects", "growth", "developing economies"],
    },
    {
        "name": "BIS Annual Economic Report PDF",
        "url": "https://www.bis.org/publ/arpdf/ar2024e.pdf",
        "format_hint": "pdf",
        "expected_keywords": ["annual economic report", "monetary policy", "resilience"],
    },
    {
        "name": "OECD Economic Outlook",
        "url": "https://www.oecd.org/en/publications/oecd-economic-outlook-volume-2025-issue-1_83363382-en.html",
        "format_hint": "html",
        "expected_keywords": ["economic outlook", "oecd", "growth"],
    },
    {
        "name": "US Treasury press releases",
        "url": "https://home.treasury.gov/news/press-releases",
        "format_hint": "html",
        "expected_keywords": ["treasury", "press release", "sanctions"],
    },
    {
        "name": "SEC 10-K form PDF",
        "url": "https://www.sec.gov/files/form10-k.pdf",
        "format_hint": "pdf",
        "expected_keywords": ["10-k", "annual report", "securities"],
    },
    {
        "name": "ECB monetary policy decisions",
        "url": "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/html/index.en.html",
        "format_hint": "html",
        "expected_keywords": ["ecb", "monetary policy", "inflation"],
    },
    {
        "name": "Bank of England Monetary Policy Report",
        "url": "https://www.bankofengland.co.uk/monetary-policy-report",
        "format_hint": "html",
        "expected_keywords": ["monetary policy report", "inflation", "bank rate"],
    },
    {
        "name": "BLS CPI PDF",
        "url": "https://www.bls.gov/news.release/pdf/cpi.pdf",
        "format_hint": "pdf",
        "expected_keywords": ["consumer price index", "inflation", "all items"],
    },
    {
        "name": "BLS CPI HTML",
        "url": "https://www.bls.gov/news.release/cpi.toc.htm",
        "format_hint": "html",
        "expected_keywords": ["consumer price index", "cpi", "prices"],
    },
    {
        "name": "FRED Fed Funds chart",
        "url": "https://fred.stlouisfed.org/series/FEDFUNDS",
        "format_hint": "html",
        "expected_keywords": ["federal funds", "interest rate", "fred"],
    },
    {
        "name": "FRED Fed Funds CSV",
        "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS",
        "format_hint": "csv",
        "expected_keywords": ["DATE", "FEDFUNDS"],
    },
    {
        "name": "CBO publications",
        "url": "https://www.cbo.gov/publication/61172",
        "format_hint": "html",
        "expected_keywords": ["budget", "economic outlook", "cbo"],
    },
    {
        "name": "FDIC bank data guide",
        "url": "https://www.fdic.gov/resources/bankers/call-reports/",
        "format_hint": "html",
        "expected_keywords": ["call reports", "fdic", "bank"],
    },
    {
        "name": "EDGAR company facts API",
        "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
        "format_hint": "json",
        "expected_keywords": ["dei", "facts", "us-gaap"],
    },
]
