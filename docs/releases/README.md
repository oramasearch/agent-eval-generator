# Releases

One page per tagged release, newest first. A page states what the release includes, what it does
not include, known issues, verification output, and where the image runs. The first release also
lists every route, entry point, Lake capability and environment variable.

A release has one `vX.Y.Z` name shared by the Git tag, the GitHub release and the Docker Hub
image tag `oramasearch/agent-eval-generator:vX.Y.Z`. The image tag names the digest already built
from the tag and deployed; it is never produced by a second build.

| Release | Date | Summary |
|---|---|---|
| [v0.2.0](v0.2.0.md) | 2026-10-25 | Security fixes: the service token compared in constant time and required, and a turn's credential sent only to the service's own `LAKE_URL` |
| [v0.1.0](v0.1.0.md) | 2026-10-17 | The first release: the Lake library agent (bus worker, `/healthz`, `/v1/turn`), registry-aware eval profiles (prompt v3), the batch command line with its Hugging Face upload, and the image |

`pyproject.toml`'s `[project].version` is the one place the version is set; `GET /healthz` reports
it, and `tests/test_release.py` fails when that version has no page here.
