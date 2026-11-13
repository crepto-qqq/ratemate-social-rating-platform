# Source origin and refresh record

| Field | Value |
| --- | --- |
| Original repository | https://github.sydney.edu.au/2026S2-INTERNET-SOFTWARE-PLATFORM/Fri-16-19-18 |
| Source branch | `main` |
| Source commit | `00955938e1fefadccc0d3a51d14e97085188eed4` |
| Source commit date | 4 November 2026 |
| Public snapshot date | 14 November 2026 |
| Filtered source tip | `1d3c837264d6659cef8301244dae5531d3ceba23` |
| Original / retained commits | 62 / 62 |
| Current imported source files | 150 / 150 |

The export was built from the fetched, committed school `origin/main` in an isolated directory. The school working tree was not edited, reset, pulled over or committed. Uncommitted files are never implicitly included in this workflow.

## Preserved material

All current tracked source files, tests, migrations, frontend assets, lockfiles, deployment tools and technical documents are present. Historical requirements documents and the initial Python prototype remain in the development history. Author names, timestamps, commit messages, merges and parent relationships are retained where possible; no author has been relabelled as Tian Liao.

## Publication transformations

- Removed two historical Python bytecode cache files. No current source file was dropped.
- Replaced the hardcoded Django development secret throughout imported history.
- Consistently anonymised personal email addresses and replaced author/committer email metadata with non-private placeholders. Synthetic test identities are preserved.
- Replaced the live deployment host defaults in verification tools with a local address. The tools were not run against the original deployment.
- Added portfolio documentation and verified third-party licence notices. Current Django settings accept `DJANGO_SECRET_KEY`; local fallback is explicitly a public development placeholder. Compose passes the setting to both backend and embedding worker.
- Regenerated the current security-update checksum manifest for the sanitised checkout. Its `source_base_commit` remains an upstream reference; `export_base_commit` identifies this public lineage. Earlier manifests in Git history remain historical records and can contain hashes from before sanitisation.

These changes necessarily alter Git commit hashes. This is a traceable source copy, not a byte-identical mirror or a GitHub fork-network relationship. The original school URL remains the authoritative upstream reference.

## Future updates

Updates are manual. Fetch the school repository, audit the intended committed branch, reproduce the privacy filter, verify the export and merge the reviewed update into this public history. Preserve existing public commits and never force-push a raw school mirror. Do not upload the source `.git` directory, private branches, database dumps, environment files or uncommitted local material.

See [docs/VALIDATION.md](docs/VALIDATION.md) for the checks completed for this snapshot.
