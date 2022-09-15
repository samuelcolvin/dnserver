import os
from pathlib import Path

import pytest

from dnserver.cli import cli


@pytest.fixture
def tmp_working_dir(tmp_path: Path):
    dft_working_dir = os.getcwd()
    os.chdir(tmp_path)

    yield tmp_path

    os.chdir(dft_working_dir)


def test_cli(mocker, tmp_working_dir: Path):
    calls = []

    class MockDNSServer:
        """Using this rather than MagicMock as I couldn't get is_running to evaluate to falsey"""

        def __init__(self, *args, **kwargs):
            self.run_check = 0
            calls.append(f'init {args} {kwargs}')

        def start(self):
            calls.append('start')

        @property
        def is_running(self):
            calls.append('is_running')
            self.run_check += 1
            return self.run_check < 2

        def stop(self):
            calls.append('stop')

    (tmp_working_dir / 'zones.txt').write_text('test zones_text')
    os.environ['ZONE_FILE'] = 'zones.txt'
    mocker.patch('dnserver.cli.DNSServer', new=MockDNSServer)
    mock_signal = mocker.patch('dnserver.cli.signal.signal')
    cli()
    assert calls == [
        "init ('test zones_text',) {'port': 53, 'upstream': None}",
        'start',
        'is_running',
        'is_running',
        'stop',
    ]
    assert mock_signal.call_count == 2
