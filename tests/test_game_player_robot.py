"""Hardware-free checks for the manually referenced phone stylus controller."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / 'garage/phones/game-player/robot.py'
spec = importlib.util.spec_from_file_location('game_robot', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeDriver:
    def __init__(self):
        self.steps = []

    def step(self, axis, direction):
        self.steps.append((axis, direction))


def robot():
    controller = module.Robot(FakeDriver(), {})
    controller.configure(100, 100, 30, 10)
    return controller


def test_startup_requires_reference_even_with_saved_configuration():
    controller = robot()
    with pytest.raises(ValueError):
        controller.command(['start'])
    with pytest.raises(ValueError):
        controller.move('x', 10)
    assert controller.driver.steps == []


def test_bounded_jog_and_clearance_interlock():
    controller = robot()
    with pytest.raises(ValueError):
        controller.jog('x', 101)
    controller.command(['reference', 'confirm'])
    with pytest.raises(ValueError):
        controller.jog('x', -1)
    controller.move('z', 2)
    with pytest.raises(ValueError):
        controller.move('x', 10)
    assert controller.position == {'x': 0, 'y': 0, 'z': 2}


def test_invalid_tap_does_not_move_and_pause_blocks_taps():
    controller = robot()
    controller.command(['reference', 'confirm'])
    controller.command(['start'])
    with pytest.raises(ValueError):
        controller.command(['tap', '10', '101'])
    assert controller.driver.steps == []
    controller.command(['pause'])
    with pytest.raises(ValueError):
        controller.command(['tap', '10', '10'])


def test_tap_retracts_and_keeps_xy_clear_of_screen(monkeypatch):
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)
    controller = robot()
    controller.command(['reference', 'confirm'])
    controller.command(['start'])
    controller.command(['tap', '3', '4'])
    assert controller.position == {'x': 3, 'y': 4, 'z': 0}
    assert controller.driver.steps == [('x', 1)] * 3 + [('y', 1)] * 4 + [('z', 1)] * 10 + [('z', -1)] * 10


def test_changed_limits_and_interruption_invalidate_reference():
    controller = robot()
    controller.command(['reference', 'confirm'])
    controller.command(['limits', '100', '100', '20', '5'])
    assert not controller.referenced
    controller.command(['reference', 'confirm'])

    def interrupted(axis, direction):
        raise KeyboardInterrupt

    controller.driver.step = interrupted
    with pytest.raises(KeyboardInterrupt):
        controller.move('x', 1)
    assert not controller.referenced
    assert not controller.active


def test_bad_touch_depth_is_rejected():
    controller = robot()
    with pytest.raises(ValueError):
        controller.configure(100, 100, 10, 11)
