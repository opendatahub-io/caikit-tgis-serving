# OpenDataHub + KServe + Serverless + ServiceMesh + Authorino

This demo is designed to allow multiple installations, both individually and together.
(Note - Currently it works fine when installed separately, but not when installed together.)

- [KServe with Caikit + TGIS runtime](./Kserve.md)
  - This install `Serverless`, `Kserve` and `Caikit+TGIS serving runtime`
  - It demonstrates it can serve bloom-560m model with kserve using a new LLM runtime
- [TBD] [Opendatahub that OSSM enabled ](./OSSM-enabled.md)
  - This install a `new opendatahub operator(has ossm plugins)`, `Authorino`, `ServiceMesh`.
  - It demonstrates it can login dashboard through Authorino (without oauth-proxy)
- [TBD] [Update Kserve to use Authorino to secure ingress.](./KServe_Authorino.md)
