# Third-party notices

## Vite / Vue starter material

The following source files were verified byte-for-byte against the official [Vite Vue starter](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-vue) when preparing this export:

- `frontend/src/components/HelloWorld.vue`
- `frontend/src/assets/hero.png`, `vite.svg`, `vue.svg`
- `frontend/public/icons.svg`
- `frontend/README.md`

They are starter material, not original student artwork or application features. The Vite MIT copyright and permission notice is included in [LICENSES/VITE-MIT.txt](LICENSES/VITE-MIT.txt), obtained from the [official licence file](https://github.com/vitejs/vite/blob/main/LICENSE). Vite, Vue and the other names/logos remain associated with their respective projects; no endorsement is implied.

## Fonts and favicon

The source favicon notes that its letter outlines come from Manrope. Its SIL Open Font License is retained at [LICENSES/MANROPE-OFL.txt](LICENSES/MANROPE-OFL.txt), sourced from [Google Fonts' Manrope distribution](https://github.com/google/fonts/blob/main/ofl/manrope/OFL.txt). The stylesheet also loads DM Sans and Manrope from Google Fonts; font binaries are not bundled here.

## Runtime dependencies and services

Django, Pillow, psycopg, python-dotenv, pgvector, FastEmbed, ONNX components, Vue, Vue Router, Vite and their transitive dependencies retain their respective licences. They are installed from the dependency manifests and lockfile, not presented as student-authored code. PostgreSQL/pgvector and Mailpit images are pulled separately by Docker.

The recommendation model is downloaded separately on first worker startup; its weights are not in this repository. OpenAI is an optional external API provider, not a model developed by this team. Use of downloaded models and external services remains subject to their own terms.

These notices do not apply an overall third-party licence to the team's application code.
