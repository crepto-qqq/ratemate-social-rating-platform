# Contribution evidence

The application is a team project. Its 62 retained upstream commits include work by multiple contributors. Author names and merge structure are retained, while private email metadata is anonymised.

The following commits are identifiable as Tian Liao's work in the committed source:

| Contribution | Original school commit | Public-history commit |
| --- | --- | --- |
| Bilingual requirements and project-context documents | `4bded4c` | [`8b5adb6`](https://github.com/crepto-qqq/ratemate-social-rating-platform/commit/8b5adb638a44d4c7c38c49545b3ea5bb0cc81190) |
| Admin moderation and notifications, spanning UI, backend, visibility handling and tests | `53e81a5` | [`4fbf019`](https://github.com/crepto-qqq/ratemate-social-rating-platform/commit/4fbf0194a320151421deed2fd21f7992b81bd2a9) |
| Integration of the moderation/notification branch through PR 20 | `b7c4462` | [`df6640a`](https://github.com/crepto-qqq/ratemate-social-rating-platform/commit/df6640aa462dfac7833e1eed50006a994441e6c7) |

The moderation/notification commit changed 42 files. Its scope includes the administrator page, backend role/permission checks, moderation reasons and audit records, user notifications and read status, hidden-content owner views, visibility propagation into other flows, and automated tests.

Requirements documents were subsequently removed from the latest school tree; they remain visible in their historical commit. A merge is integration evidence, not an additional independent implementation. Git author counts do not establish the complete division of team work or measure project management effort.

Recommendation retrieval, AI rating, authentication, deployment changes and other features have separate team authorship in the history. They should be described as capabilities of the team system unless specific personal contribution evidence is available. Starter assets are attributed separately in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
