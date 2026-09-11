# macOS launcher recovery review

Two independent, single-file fixes based on
[Vandomas/RecoilEngine-AppleSilicon at 562fe461](https://github.com/Vandomas/RecoilEngine-AppleSilicon/tree/562fe461f8b045f863089815edac7f2d6559e178):

- [Download error classification](download-error/README.md): report a known
  failure to install local content metadata accurately, with its diagnostic.
- [Rapid backup and restoration](rapid-restore/README.md): recover only from
  complete backups and stop safely when restoration fails.

Each directory contains the exact original and candidate script, a standalone
test, recorded original/fixed results, repeat instructions and a manifest of
source and public-copy hashes. Real launcher helper windows were also checked
with controlled offline input; their results and scope are documented inside.
Application binaries and the private GUI harness are not included.

Private paths in selected textual evidence were replaced as documented in
each manifest. Screenshots included here are unchanged. The restoration error
screenshot contains a private path and is omitted; its sourced textual
observations are included instead. This checks error handling, not the physical
cause of the historical access refusal or a complete Finder/network install.

OpenAI Codex prepared the patches, tests and evidence. Independent Codex review
is documented in the individual packages; human maintainer review is pending.

Evidence bytes, including original line endings and trailing whitespace, are
preserved by the scoped `.gitattributes` file.
