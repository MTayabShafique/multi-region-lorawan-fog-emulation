# MQTT PKI

The project uses one private CA, separate server certificates for the
ChirpStack and fog EMQX clusters, and separate client identities for each
application role. EMQX requires a trusted client certificate and the existing
MQTT username/password, so certificate theft alone does not bypass broker ACLs.

Generate the certificates from the repository root:

```powershell
.\generate-mqtt-certificates.ps1
```

Generated files are written to `tls/generated/` and are ignored by Git. The
script preserves an existing CA and leaf certificates. Use `-RotateLeaves` to
renew all server and client certificates without replacing the CA:

```powershell
.\generate-mqtt-certificates.ps1 -RotateLeaves
```

Back up `tls/generated/ca/ca.key` securely and offline. It is needed only to
issue or renew certificates and is never mounted into a container. Replacing
the CA is an explicit trust migration and is intentionally not automated.

The server certificates include Docker DNS names used by HAProxy and the
applications. If deployment DNS names change, update the SAN lists in
`generate-mqtt-certificates.ps1`, rotate the leaf certificates, and redeploy
all brokers and clients together.
