import logging
from datetime import datetime

import httpx

from backend.models import Game, GameClock, GameStatus, Sport, Team
from backend.scanner.sports import get_sport_config

logger = logging.getLogger(__name__)

ESPN_ENDPOINTS = {
    Sport.NBA: "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    Sport.NFL: "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    Sport.MLB: "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    Sport.NHL: "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    Sport.WNBA: "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
    Sport.CBB: "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
}


def _parse_clock(competition: dict, regular_periods: int) -> GameClock | None:
    status = competition.get("status", {})
    period = status.get("period", 0)
    display_clock = status.get("displayClock", "0:00")
    period_type = "overtime" if period > regular_periods else "regular"

    # Parse seconds remaining from display clock
    seconds = None
    try:
        parts = display_clock.split(":")
        if len(parts) == 2:
            seconds = int(parts[0]) * 60 + float(parts[1])
    except (ValueError, IndexError):
        pass

    return GameClock(
        period=period,
        period_type=period_type,
        display_clock=display_clock,
        seconds_remaining=seconds,
    )


def _parse_game_status(competition: dict) -> GameStatus:
    state = competition.get("status", {}).get("type", {}).get("state", "")
    if state == "in":
        return GameStatus.IN_PROGRESS
    elif state == "post":
        return GameStatus.FINAL
    return GameStatus.SCHEDULED


def _parse_competition(competition: dict, sport: Sport, regular_periods: int) -> Game | None:
    try:
        competitors = competition.get("competitors", [])
        if len(competitors) < 2:
            return None

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home_team = Team(
            id=home["team"]["id"],
            name=home["team"]["displayName"],
            abbreviation=home["team"]["abbreviation"],
            score=int(home.get("score", 0) or 0),
        )
        away_team = Team(
            id=away["team"]["id"],
            name=away["team"]["displayName"],
            abbreviation=away["team"]["abbreviation"],
            score=int(away.get("score", 0) or 0),
        )

        status = _parse_game_status(competition)
        clock = (
            _parse_clock(competition, regular_periods) if status == GameStatus.IN_PROGRESS else None
        )

        # Parse start time
        start_time = None
        date_str = competition.get("date")
        if date_str:
            try:
                start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        venue = None
        venue_data = competition.get("venue", {})
        if venue_data:
            venue = venue_data.get("fullName")

        return Game(
            id=competition["id"],
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            status=status,
            clock=clock,
            start_time=start_time,
            venue=venue,
        )
    except (KeyError, ValueError) as e:
        logger.warning(f"Failed to parse competition: {e}")
        return None


async def fetch_games(sport: Sport = Sport.NBA) -> list[Game]:
    url = ESPN_ENDPOINTS.get(sport)
    if not url:
        return []

    sport_config = await get_sport_config(sport)
    regular_periods = sport_config.regular_periods

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"ESPN API error for {sport}: {e}")
            return []

    games = []
    for event in data.get("events", []):
        for competition in event.get("competitions", []):
            game = _parse_competition(competition, sport, regular_periods)
            if game:
                games.append(game)

    return games
