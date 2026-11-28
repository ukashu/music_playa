from conftest import make_player, make_tracks

from music_playa_gui.bridge import PlaybackBridge


def test_callbacks_become_signals() -> None:
    bridge = PlaybackBridge()
    tracks, progress = [], []
    bridge.track_changed.connect(tracks.append)
    bridge.progress_changed.connect(lambda position, duration: progress.append((position, duration)))
    track = make_tracks(1)[0]
    bridge.on_track(track)
    bridge.on_track(None)
    bridge.on_progress(1.5, 90.0)
    assert tracks == [track, None]
    assert progress == [(1.5, 90.0)]


def test_bridge_listens_to_the_player() -> None:
    tracks = make_tracks(2)
    player = make_player(tracks)
    bridge = PlaybackBridge()
    seen = []
    bridge.track_changed.connect(seen.append)
    player.add_listener(bridge)
    player.next()
    assert seen[-1] == tracks[1]
