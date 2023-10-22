from dns.dnssec import DSDigest
import dns.rdataclass
import dns.rdatatype
import dns.message
import dns.name
import dns.query
import dns.rrset
from dns import dnssec

import struct


__all__ = ['load_dsdigest', 'TRUSTED_ANCHORS']


def load_dsdigest(digest: bytes | str, digest_type: DSDigest, key_id: int, algorithm: int):
    if isinstance(digest, str):
        digest = bytes.fromhex(digest)
    if isinstance(digest_type, str):
        digest_type = DSDigest[digest_type]
    else:
        digest_type = DSDigest(digest_type)

    dsrdata = struct.pack("!HBB", key_id, algorithm, digest_type) + digest
    return dns.rdata.from_wire(dns.rdataclass.IN, dns.rdatatype.DS, dsrdata, 0, len(dsrdata))


TRUSTED_ANCHORS = dns.rrset.RRset(dns.name.root, dns.rdataclass.IN, dns.rdatatype.RdataType.DS)
TRUSTED_ANCHORS.add(load_dsdigest('49AAC11D7B6F6446702E54A1607371607A1A41855200FD2CE1CDDE32F24E8FB5', 2, 19036, 8))
TRUSTED_ANCHORS.add(load_dsdigest('E06D44B80B8F1D39A95C0B0D7C65D08458E880409BBC683457104237C7F8EC8D', 2, 20326, 8))


#
# Missing Authenticated Denial of Existence in the DNS
# https://www.rfc-editor.org/rfc/rfc7129
# https://github.com/fabian-hk/dnssec_scanner/blob/master/dnssec_scanner/nsec/__init__.py
def verify(response: dns.message.Message, ns: str, verified: dict = None, anchors: dns.rrset.RRset = None):
    if isinstance(response, (bytes, memoryview, bytearray)):
        response = dns.message.from_wire(response)
    if isinstance(response, str):
        response = dns.message.from_text(response)
    if verified is None:
        verified = {}
    if anchors is None:
        anchors = TRUSTED_ANCHORS
    rrset, rrsig = response.answer
    signer: dns.name.Name = rrsig[0].signer
    # Maybe verify that signer is valid for response
    if signer not in verified:
        dnskey = dns.query.udp(dns.message.make_query(signer, dns.rdatatype.DNSKEY, want_dnssec=True), ns)
        dnskey_set, dnskey_sig = dnskey.answer
        dnssec.validate(dnskey_set, dnskey_sig, {signer: dnskey_set}, None)
        if signer == dns.name.root:
            ds_set = anchors
        else:
            ds = dns.query.udp(dns.message.make_query(signer, dns.rdatatype.DS, want_dnssec=True), ns)
            ds_set = ds.answer[0]
            if signer.fullcompare(ds.answer[1][0].signer)[0] != dns.name.NAMERELN_SUBDOMAIN:
                raise dnssec.ValidationFailure(signer)
            verify(ds, ns, verified)
        found = False
        for key in dnskey_set:
            _ds = dnssec.make_ds(ds_set.name, key, ds_set[0].digest_type)
            for _vds in ds_set:
                if _vds == _ds:
                    found = True
                    break
            if found:
                break
        if not found:
            raise dnssec.ValidationFailure(signer)
        verified[signer] = dnskey_set
    dnssec.validate(rrset, rrsig, verified, None)
