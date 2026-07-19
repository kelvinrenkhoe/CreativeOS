"""Campaign models for CreativeOS."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class CampaignManifest:
    """Configuration written to a campaign workspace."""

    name: str
    artist: str
    status: str = "planning"
    release_date: str | None = None
    spotify: str | None = None
    smart_link: str | None = None
    hashtags: list[str] = field(default_factory=list)
    platforms: list[str] = field(
        default_factory=lambda: ["spotify", "instagram", "facebook", "tiktok", "x"]
    )
    goals: dict[str, int] = field(
        default_factory=lambda: {
            "spotify_streams": 100000,
            "playlist_adds": 250,
            "radio_stations": 100,
            "creators": 50,
        }
    )
