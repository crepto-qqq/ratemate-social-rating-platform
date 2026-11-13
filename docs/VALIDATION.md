# Public-export validation

Checked on **14 November 2026**, using source snapshot `00955938e1fefadccc0d3a51d14e97085188eed4` and filtered history `1d3c837264d6659cef8301244dae5531d3ceba23`.

| Check | Result |
| --- | --- |
| Current source preservation | All 150 school files retained; changes limited to documented privacy/configuration adjustments and portfolio additions |
| Imported history | All 62 source commits retained with names, timestamps and parent relationships; private email metadata anonymised |
| Frontend install | `npm ci --ignore-scripts` passed against the committed lockfile |
| Frontend build | `npm run build` passed; Vite 8.3.3, 59 modules |
| Python syntax | All 97 current Python files parsed and compiled in memory, without writing bytecode |
| Backend application subset | 79 tests discovered: **78 passed, 1 skipped**, no failures/errors |
| Dependency consistency | All six original pinned requirements installed; `pip check` passed |
| Updated checksum manifest | All 20 listed files verified by `deploy/verify_release.py` |
| Privacy review | Retained history checked for original Django secrets, private email values, original deployment-host defaults and common token/private-key formats; no remaining findings |
| Licence copies | Vite MIT and Manrope OFL matched their verified official-source hashes |

## Test environment and scope

Frontend validation used Node 24.19.0 and npm 11.17.0 in the isolated filtered checkout. Frontend sources and the lockfile are unchanged in the final public checkout. There is no frontend automated test script; a successful build is not an end-to-end browser test.

Backend validation used Python 3.12.10, Django 6.1.1 and the exact source requirements in a separate virtual environment. The application subset ran against the final public checkout with the upstream in-memory SQLite and in-memory email test settings:

```bash
cd backend
python -B manage.py test accounts config create_template moderation notifications rating --settings=config.test_settings --verbosity 2
```

The skipped test needs PostgreSQL concurrency/row-locking semantics. The recommendation test module is excluded from this passing subset.

For diagnostic comparison, the full upstream suite was also attempted on SQLite in the filtered checkout: 96 tests, **89 passed, 6 errors, 1 skipped**. All six errors were pgvector cosine-SQL operations unsupported by SQLite, with no assertion failures. This does not verify the recommendation suite on its intended database.

The Compose configuration specifies Python 3.13 and PostgreSQL 17/pgvector. Docker/PostgreSQL were unavailable for this verification, so the complete intended-environment suite, container startup and production deployment were **not** revalidated. No live email, paid AI API or original deployment server was contacted by these tests.

## Publication adjustments

The final checkout additionally accepts `DJANGO_SECRET_KEY` through the environment, passes it through Compose and leaves the optional AI API key empty in the example configuration. Development defaults remain development defaults. The security-update checksum manifest was regenerated for this sanitised checkout; it is file-integrity evidence, not production acceptance evidence.

Original engineering documents may contain tests/results recorded by the team at earlier dates. Those are preserved historical statements, not claims that every original experiment was rerun during this export.
