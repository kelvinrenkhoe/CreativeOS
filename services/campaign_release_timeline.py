"""Generate deterministic release-date campaign timelines."""

from datetime import date, timedelta

from models.campaign_release_timeline import (
    CampaignReleaseTimeline,
    CampaignReleaseTimelineEvent,
)


class CampaignReleaseTimelineService:
    """Build a fixed music-release rollout around a release date."""

    _MUSIC_RELEASE_EVENTS = (
        (
            -21,
            "Pre-save campaign begins",
            "Social",
            "Launch the pre-save campaign and publish the primary call to action.",
        ),
        (
            -14,
            "First teaser video",
            "Teaser",
            "Publish the first short teaser introducing the release mood.",
        ),
        (
            -10,
            "Behind-the-scenes clip",
            "Video",
            "Share a behind-the-scenes clip that adds context to the song.",
        ),
        (
            -7,
            "Cover artwork reveal",
            "Artwork",
            "Reveal the official cover artwork across campaign channels.",
        ),
        (
            -5,
            "Countdown starts",
            "Social",
            "Begin the final countdown sequence with daily reminders.",
        ),
        (
            -3,
            "Press and influencer outreach",
            "Press",
            "Send the release pack to press, DJs, and selected creators.",
        ),
        (
            -1,
            "Final release reminder",
            "Social",
            "Publish the final reminder and confirm release-time links.",
        ),
        (
            0,
            "Release day",
            "Release",
            "Publish the release announcement and activate all launch assets.",
        ),
        (
            1,
            "Thank supporters",
            "Follow-up",
            "Thank early listeners and invite them to share the release.",
        ),
        (
            4,
            "Performance clip",
            "Live",
            "Publish a performance-led clip to sustain attention.",
        ),
        (
            7,
            "Playlist push",
            "Playlist",
            "Run the focused playlist and save campaign follow-up.",
        ),
    )

    def generate(
        self,
        release_date: date,
        campaign_type: str = "music-release",
    ) -> CampaignReleaseTimeline:
        """Return the deterministic timeline for a supported campaign type."""
        if not isinstance(release_date, date):
            raise ValueError("release_date must be a date")
        normalized_type = campaign_type.strip().lower()
        if normalized_type != "music-release":
            raise ValueError(f"unsupported campaign_type: {campaign_type}")

        events = tuple(
            sorted(
                CampaignReleaseTimelineEvent(
                    date=release_date + timedelta(days=day_offset),
                    day_offset=day_offset,
                    title=title,
                    category=category,
                    description=description,
                )
                for day_offset, title, category, description in self._MUSIC_RELEASE_EVENTS
            )
        )
        return CampaignReleaseTimeline(
            release_date=release_date,
            campaign_type=normalized_type,
            events=events,
        )
