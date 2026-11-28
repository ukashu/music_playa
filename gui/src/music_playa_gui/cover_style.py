"""The ways the cover of the current track can be shown in the now-playing view."""

# The cover dimmed over the whole view (the original look).
COVER_FILL = "fill"
# The logo as a record, filled with the cover, spinning while a track plays.
COVER_DISC = "disc"
COVER_STYLES = (COVER_FILL, COVER_DISC)
DEFAULT_COVER_STYLE = COVER_FILL
COVER_STYLE_LABEL_KEYS = {COVER_FILL: "settings.cover_fill", COVER_DISC: "settings.cover_disc"}
