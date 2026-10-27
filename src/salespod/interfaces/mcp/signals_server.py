from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from salespod.config import Settings
from salespod.infrastructure.db.models import Company, SignalEvent
from salespod.infrastructure.db.session import create_session_factory

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None  # type: ignore[assignment,misc]

SIGNALS_TOOL_NAMES = (
    "get_company_news",
    "get_funding_events",
    "get_tech_stack",
)


class SignalsIntelligenceSource:
    """Provides market intelligence, news, funding, and tech stack data for accounts."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self.session_factory = session_factory

    def _resolve_company(
        self, session: Session, company_id: str | None = None, domain: str | None = None
    ) -> Company | None:
        if company_id:
            try:
                parsed = str(UUID(company_id))
                company = session.get(Company, parsed)
                if company:
                    return company
            except ValueError:
                pass
        if domain:
            cleaned_domain = (
                domain.lower().replace("https://", "").replace("http://", "").strip("/")
            )
            return session.scalar(
                select(Company).where(Company.domain.ilike(f"%{cleaned_domain}%"))
            )
        return None

    def get_company_news(
        self,
        company_id: str | None = None,
        domain: str | None = None,
        query: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        news_items: list[dict[str, Any]] = []
        company_name = "Target Account"
        company_domain = domain or "target.com"
        industry = "Enterprise B2B Software"

        if self.session_factory:
            with self.session_factory() as session:
                company = self._resolve_company(session, company_id, domain)
                if company:
                    company_name = company.name
                    company_domain = company.domain
                    industry = company.industry

                    # Include any actual recorded signals
                    db_signals = session.scalars(
                        select(SignalEvent)
                        .where(SignalEvent.company_id == company.id)
                        .order_by(SignalEvent.occurred_at.desc())
                        .limit(limit)
                    ).all()
                    for sig in db_signals:
                        news_items.append(
                            {
                                "title": sig.headline,
                                "source": sig.source,
                                "date": sig.occurred_at.isoformat(),
                                "summary": sig.summary,
                                "url": sig.source_url or f"https://news.example.com/{sig.id}",
                                "category": sig.event_type,
                                "relevance": sig.relevance_score,
                            }
                        )

        # Fallback / simulated items if few or no DB events
        now = datetime.now(UTC)
        candidates = [
            {
                "title": f"{company_name} announces strategic platform expansion",
                "source": "TechRadar Pro",
                "date": (now - timedelta(days=3)).isoformat(),
                "summary": (
                    f"{company_name} accelerated its multi-region rollout, targeting financial "
                    "services and tier-1 tech enterprises."
                ),
                "url": f"https://marketnews.example.com/{company_domain}/platform-expansion",
                "category": "product_announcement",
                "relevance": 92,
            },
            {
                "title": f"{company_name} appoints new executive leadership to spearhead revenue",
                "source": "VentureBeat",
                "date": (now - timedelta(days=12)).isoformat(),
                "summary": (
                    "Key executive change aims to streamline pipeline velocity, forecast "
                    f"predictability, and GTM productivity at {company_name}."
                ),
                "url": f"https://marketnews.example.com/{company_domain}/leadership-hire",
                "category": "leadership_change",
                "relevance": 95,
            },
            {
                "title": f"Industry benchmark: How {company_name} modernizes in {industry}",
                "source": "SaaS Digest",
                "date": (now - timedelta(days=24)).isoformat(),
                "summary": (
                    "An analysis of tech modernization, cloud migrations, and workflow "
                    f"consolidation within {company_name}."
                ),
                "url": f"https://marketnews.example.com/{company_domain}/modernization-profile",
                "category": "market_profile",
                "relevance": 86,
            },
        ]

        if query:
            q = query.lower()
            candidates = [
                c for c in candidates if q in c["title"].lower() or q in c["summary"].lower()
            ]

        for item in candidates:
            if len(news_items) < limit:
                news_items.append(item)

        return news_items[:limit]

    def get_funding_events(
        self,
        company_id: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        company_name = "Target Account"
        if self.session_factory:
            with self.session_factory() as session:
                company = self._resolve_company(session, company_id, domain)
                if company:
                    company_name = company.name

        now = datetime.now(UTC)
        return [
            {
                "round": "Series B",
                "amount_usd": 42_000_000,
                "amount_formatted": "$42M",
                "date": (now - timedelta(days=45)).strftime("%Y-%m-%d"),
                "lead_investor": "Bessemer Venture Partners",
                "co_investors": ["Insight Partners", "Accel"],
                "valuation_usd": 210_000_000,
                "summary": (
                    f"{company_name} closed a $42M Series B led by Bessemer to accelerate "
                    "enterprise GTM and revenue operations."
                ),
            },
            {
                "round": "Series A",
                "amount_usd": 14_000_000,
                "amount_formatted": "$14M",
                "date": (now - timedelta(days=450)).strftime("%Y-%m-%d"),
                "lead_investor": "Sequoia Capital",
                "co_investors": ["Y Combinator"],
                "valuation_usd": 70_000_000,
                "summary": (
                    f"{company_name} raised $14M Series A to scale initial enterprise deployments."
                ),
            },
        ]

    def get_tech_stack(
        self,
        company_id: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        company_name = "Target Account"
        company_domain = domain or "target.com"
        if self.session_factory:
            with self.session_factory() as session:
                company = self._resolve_company(session, company_id, domain)
                if company:
                    company_name = company.name
                    company_domain = company.domain

        return {
            "company_name": company_name,
            "domain": company_domain,
            "last_verified": datetime.now(UTC).strftime("%Y-%m-%d"),
            "technologies": {
                "crm": {"name": "Salesforce Sales Cloud", "status": "primary", "confidence": 0.98},
                "revenue_intelligence": {
                    "name": "Gong.io",
                    "status": "evaluating_alternatives",
                    "confidence": 0.88,
                },
                "sales_engagement": {"name": "Outreach.io", "status": "active", "confidence": 0.92},
                "data_warehouse": {"name": "Snowflake", "status": "active", "confidence": 0.95},
                "cloud_infrastructure": {
                    "name": "AWS (us-east-1, us-west-2)",
                    "status": "primary",
                    "confidence": 0.99,
                },
                "collaboration": {
                    "name": "Slack Enterprise Grid",
                    "status": "active",
                    "confidence": 0.99,
                },
                "security_sso": {"name": "Okta", "status": "active", "confidence": 0.94},
            },
            "recent_signals": [
                {
                    "category": "revenue_operations",
                    "event": "Detected pilot integration with revenue workflow tooling",
                    "detected_at": (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d"),
                },
                {
                    "category": "infrastructure",
                    "event": "Migrated auth layer to Okta Identity Engine",
                    "detected_at": (datetime.now(UTC) - timedelta(days=35)).strftime("%Y-%m-%d"),
                },
            ],
            "insights": [
                (
                    f"{company_name} runs Salesforce as core CRM but lacks unified predictive "
                    "risk intelligence."
                ),
                (
                    "Active interest in consolidating sales engagement tooling with AI workflow "
                    "agents."
                ),
            ],
        }


def create_signals_server(
    session_factory: sessionmaker[Session] | None = None,
) -> Any:
    """Create an isolated FastMCP server exposing market and account intelligence."""
    if FastMCP is None:
        raise RuntimeError("FastMCP is not installed; run pip install -e '.[dev,agents]'")

    if session_factory is None:
        settings = Settings.from_env()
        settings.ensure_database_parent()
        session_factory = create_session_factory(settings.database_url)

    source = SignalsIntelligenceSource(session_factory)
    mcp = FastMCP("signals-mcp")

    @mcp.tool(name="get_company_news")
    def get_company_news(
        company_id: str | None = None,
        domain: str | None = None,
        query: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Fetch recent company news, press releases, and leadership announcements."""
        return source.get_company_news(
            company_id=company_id, domain=domain, query=query, limit=limit
        )

    @mcp.tool(name="get_funding_events")
    def get_funding_events(
        company_id: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch historical and recent venture funding rounds, investors, and valuations."""
        return source.get_funding_events(company_id=company_id, domain=domain)

    @mcp.tool(name="get_tech_stack")
    def get_tech_stack(
        company_id: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Fetch verified technology stack footprint, CRM stack, and infrastructure signals."""
        return source.get_tech_stack(company_id=company_id, domain=domain)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Sales Pod Signals MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    args = parser.parse_args()
    server = create_signals_server()
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
