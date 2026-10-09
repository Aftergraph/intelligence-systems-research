# v2.1 Multi-Node Verified Fabric

v2.1 extends the v2.0 signed mTLS node transport with a paired multi-node verification path.

## New guarantees

- Two or more independent worker targets can verify the same exact candidate subject.
- Remote verifier execution is fenced by a durable lease and exact authority-grant binding.
- Remote callers still cannot choose the verifier command.
- Lease renewal occurs through the signed mTLS node transport.
- Worker progress can be polled through a bounded read-only journal stream.
- Journal pages are cursor-contiguous and reconstruct the same hash-chain head as the worker journal.
- Proof claims carry trust-domain metadata; quorum requires independent trust domains rather than duplicate votes from one domain.
- VSR, FCR, CPVO, TVO and frontier-intelligence-efficiency accounting are represented separately from runtime control.

## Truth boundary

The bundled `v21-demo` opens two real loopback TCP+mTLS node gateways and executes two real verifier subprocesses. It does **not** claim physical Jonas-Lenovo ↔ VDS execution. The included metric example is synthetic plumbing evidence, not a live TypeSafe/Dialagram benchmark.
