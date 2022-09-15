import pytest

from dnserver.load_records import Records, Zone, load_records
from dnserver.main import Record


def test_load_records():
    records = load_records('example_zones.toml')
    assert records == Records(
        zones=[
            Zone(host='example.com', type='A', answer='1.2.3.4'),
            Zone(host='example.com', type='A', answer='1.2.3.4'),
            Zone(host='example.com', type='CNAME', answer='whatever.com'),
            Zone(host='example.com', type='MX', answer=['whatever.com.', 5]),
            Zone(host='example.com', type='MX', answer=['mx2.whatever.com.', 10]),
            Zone(host='example.com', type='MX', answer=['mx3.whatever.com.', 20]),
            Zone(host='example.com', type='NS', answer='ns1.whatever.com.'),
            Zone(host='example.com', type='NS', answer='ns2.whatever.com.'),
            Zone(host='example.com', type='TXT', answer='hello this is some text'),
            Zone(host='example.com', type='SOA', answer=['ns1.example.com', 'dns.example.com']),
            Zone(
                host='testing.com',
                type='TXT',
                answer=(
                    'one long value: IICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgFWZUed1qcBziAsqZ/LzT2ASxJYuJ5sko1CzWFhFu'
                    'xiluNnwKjSknSjanyYnm0vro4dhAtyiQ7OPVROOaNy9Iyklvu91KuhbYi6l80Rrdnuq1yjM//xjaB6DGx8+m1ENML8PEdSFbK'
                    'Qbh9akm2bkNw5DC5a8Slp7j+eEVHkgV3k3oRhkPcrKyoPVvniDNH+Ln7DnSGC+Aw5Sp+fhu5aZmoODhhX5/1mANBgkqhkiG9w'
                    '0BAQEFAAOCAg8AMIICCgKCAgEA26JaFWZUed1qcBziAsqZ/LzTF2ASxJYuJ5sk'
                ),
            ),
        ],
    )


def test_create_server():
    records = load_records('example_zones.toml')
    [Record(zone) for zone in records.zones]


def test_no_zones(tmp_path):
    path = tmp_path / 'zones.toml'
    path.write_text('x = 4')
    with pytest.raises(ValueError, match=r'^No zones found in .+zones\.toml$'):
        load_records(path)


@pytest.mark.parametrize(
    'toml,error',
    [
        ('x = 4', r'^No zones found in .+zones\.toml$'),
        ('[zones]\ntype = 4', r'^Zones must be a list, not dict$'),
        ('zones = [4]', 'Zone 1 is not a valid dict, must have keys "host", "type" and "answer"'),
        ('[[zones]]\ntype = 4', 'Zone 1 is not a valid dict, must have keys "host", "type" and "answer"'),
        (
            'zones = [{host="a",type="A",answer="c"},4]',
            'Zone 2 is not a valid dict, must have keys "host", "type" and "answer"',
        ),
        ('zones = [{host=42,type="A",answer="c"}]', 'Zone 1 is invalid, "host" must be string'),
        ('zones = [{host="a",type="c",answer="c"}]', r'Zone 1 is invalid, "type" must be one of A, AAAA.+'),
    ],
)
def test_invalid_zones(tmp_path, toml, error):
    path = tmp_path / 'zones.toml'
    path.write_text(toml)
    with pytest.raises(ValueError, match=error):
        load_records(path)
