from __future__ import annotations

import ipaddress
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / ".certs"
CA_CERT = CERT_DIR / "grace-ca.crt"
CA_KEY = CERT_DIR / "grace-ca-key.pem"
SERVER_CERT = CERT_DIR / "grace-server.crt"
SERVER_KEY = CERT_DIR / "grace-server-key.pem"


def local_ip() -> ipaddress.IPv4Address:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        try:
            connection.connect(("10.255.255.255", 1))
            address = connection.getsockname()[0]
        except OSError:
            address = "127.0.0.1"
    return ipaddress.ip_address(address)


def write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    try:
        path.chmod(0o600)
    except OSError:
        pass


def create_or_load_ca(now: datetime) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    if CA_CERT.is_file() and CA_KEY.is_file():
        certificate = x509.load_pem_x509_certificate(CA_CERT.read_bytes())
        key = serialization.load_pem_private_key(CA_KEY.read_bytes(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise TypeError("The existing G.R.A.C.E. CA key is not an RSA private key.")
        return certificate, key

    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "G.R.A.C.E. Local CA")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True, encipher_only=None, decipher_only=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    write_private_key(CA_KEY, key)
    CA_CERT.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return certificate, key


def main() -> None:
    CERT_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    ca_certificate, ca_key = create_or_load_ca(now)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    hostname = socket.gethostname()
    address = local_ip()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "G.R.A.C.E. Local Server")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_certificate.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True, data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=None, decipher_only=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address), x509.IPAddress(ipaddress.ip_address("127.0.0.1")), x509.DNSName(hostname), x509.DNSName("localhost")]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    write_private_key(SERVER_KEY, server_key)
    SERVER_CERT.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    print(f"Created HTTPS certificate for {address}.")
    print(f"Phone setup: http://{address}:8000/certificate")
    print(f"Secure app: https://{address}:8443")


if __name__ == "__main__":
    main()
