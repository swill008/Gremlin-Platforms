# -*- coding: utf-8; -*-
from pathlib import Path

from gremlin import util


def test_user_data_lives_in_gremlin_platforms() -> None:
    # The test setup replaces userprofile_path with a temp folder; check the source.
    assert util.USER_DATA_FOLDER == "Gremlin Platforms"
    source = Path(util.__file__).read_text(encoding="utf-8")
    assert "/ USER_DATA_FOLDER).resolve()" in source


def test_startup_scaling_check_reads_the_same_folder() -> None:
    # joystick_gremlin.py reads configuration.json before Qt loads; it cannot use util.
    source = Path(__file__).resolve().parents[2].joinpath("joystick_gremlin.py")
    folder = util.USER_DATA_FOLDER
    expected = f'os.path.join(root, "{folder}", "configuration.json")'
    assert expected in source.read_text(encoding="utf-8")
