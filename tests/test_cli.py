import os

from dnserver.cli import cli


def test_cli(mocker):
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

    os.environ['ZONE_FILE'] = 'zones.txt'
    mocker.patch('dnserver.cli.DNSServer', new=MockDNSServer)
    mock_signal = mocker.patch('dnserver.cli.signal.signal')
    cli()
    assert calls == [
        "init ('zones.txt',) {'port': 53, 'upstream': None}",
        'start',
        'is_running',
        'is_running',
        'stop',
    ]
    assert mock_signal.call_count == 2
