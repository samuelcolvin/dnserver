from dnserver.cli import cli_logic


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

    mocker.patch('dnserver.cli.DNSServer', new=MockDNSServer)
    mock_signal = mocker.patch('dnserver.cli.signal.signal')
    assert cli_logic(['--port', '1234', 'zones.txt']) == 0
    assert calls == [
        "init ('zones.txt',) {'port': '1234', 'upstream': None}",
        'start',
        'is_running',
        'is_running',
        'stop',
    ]
    assert mock_signal.call_count == 2


def test_cli_no_zones(mocker):
    mock_dnserver = mocker.patch('dnserver.cli.DNSServer')
    mock_signal = mocker.patch('dnserver.cli.signal.signal')
    assert cli_logic(['--port', '1234']) == 1
    assert mock_dnserver.call_count == 0
    assert mock_signal.call_count == 0
