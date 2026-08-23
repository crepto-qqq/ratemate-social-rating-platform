# Rate Anything - Software Requirements Specification

**Document status:** Draft v0.1  
**Product name:** Working title only; final name is not yet selected  
**Language:** English submission draft; product UI language is not yet selected  
**Scope:** Product baseline for Assignments 1-3  
**Last updated:** 23 August 2026

## 1. Purpose

This Software Requirements Specification (SRS) defines the initial product requirements for an entertainment-focused community rating website. It records confirmed product decisions, separates them from course-driven proposals, and provides a traceable baseline for functional requirements, the data model, wireframes, implementation, testing, deployment, and security.

This is an early draft. Requirements marked **Provisional** remain subject to team confirmation. Items marked **TBD** must be resolved before the Assignment 1 report is treated as final.

## 2. Product Vision

Rate Anything enables people who are casually curious about other people's opinions to create and discover playful ratings for virtually anything. A subject may be a tangible product such as a refrigerator or an abstract concept such as staying up late. A member can create the subject, define the dimensions by which it should be judged, submit scores, and publish the result. Other members can find the subject, see its community content, discuss individual submissions, and reuse an existing set of dimensions to submit their own scores.

The website is designed for entertainment. A Result Score represents the opinions expressed by community members and is not intended to be objective, authoritative, or factually verified.

### 2.1 Value proposition

The product provides:

- a low-friction way to express an opinion about any tangible or abstract Thing;
- a structured alternative to an unqualified star rating by allowing members to define Criteria;
- a way to compare how different people judge the same Thing using the same Rating Scheme;
- a searchable collection of ratings, written reactions, images, and discussions;
- a playful experience in which subjective or humorous results are acceptable.

### 2.2 Target users

The primary user is a person who is casually curious about how other people feel about a Thing and wants a lightweight entertainment experience while browsing in their free time.

The current draft recognises three roles:

| Role | Description | Intended access |
|---|---|---|
| Visitor | A person who has not signed in | **Provisional:** search and read public content only |
| Member | A registered and authenticated community participant | Create Things and Rating Schemes, submit ratings, upload images, comment, and manage their own content |
| Moderator | A privileged Member responsible for reactive content moderation | All Member access plus review and removal of prohibited content through a custom moderation panel |

## 3. Scope

### 3.1 Confirmed in scope

- Creating a rateable Thing whose subject may be tangible or abstract.
- Searching for an existing Thing by its name.
- Creating a Rating Scheme for a Thing by defining user-selected Criteria.
- Submitting a score for every Criterion in a Rating Scheme.
- Calculating and storing a Result Score under the associated Thing.
- Allowing multiple members to create independent Rating Schemes for the same Thing.
- Allowing another member to reuse an existing Rating Scheme and submit their own scores.
- Displaying all relevant Rating Submissions, written reactions, images, and discussion when a user opens a Thing.
- Commenting on another member's Rating Submission.
- Allowing any community Member to add a new Thing without prior moderator approval.
- Allowing Moderators to remove unlawful, violent, sexual, or otherwise prohibited content, with particular attention to user-uploaded images.
- Retaining the existing Score-O-Matic prototype's visual identity and useful interaction ideas where practical, without requiring exact implementation parity.

### 3.2 Provisional MVP boundary

The recommended MVP is a community website centred on individual Thing pages. The existing prototype's personal weighted-ranking workflow is not itself an MVP requirement. Its colour palette, cards, step-based rating flow, and results presentation may be reused.

The following are proposed as the five authenticated-only core capabilities required by the course:

1. Create and publish a Thing.
2. Create a Rating Scheme and publish an initial Rating Submission.
3. Reuse an existing Rating Scheme to publish or update a Rating Submission.
4. Comment on and discuss another member's Rating Submission.
5. Report potentially prohibited content for Moderator review.

The fifth capability is **Provisional** because community reporting has not yet been explicitly confirmed by the team, although it provides the necessary workflow for reactive moderation.

### 3.3 Out of scope for the MVP

- Claims that a score is objectively true or professionally authoritative.
- E-commerce, payment, ordering, or product inventory functions.
- Native mobile applications.
- Private messaging or real-time chat.
- A full social follower network.
- AI-generated official scores.
- Automated recommendations driven by machine learning.
- WebSocket functionality unless later selected as the Assignment 2 Modern Web option.
- A complete recreation of the current standalone Score-O-Matic tool.

## 4. Domain Model

### 4.1 Canonical concepts

| Concept | Definition |
|---|---|
| Thing | Any tangible object, product, experience, idea, or abstract concept selected as a subject for rating. |
| Rating Scheme | A reusable scoring structure created for exactly one Thing. |
| Criterion | A named scoring dimension within a Rating Scheme. This is not a discovery tag. |
| Rating Submission | One Member's completed Criterion scores using one Rating Scheme, optionally accompanied by text and images. |
| Result Score | The calculated outcome of one Rating Submission. |
| Comment | A discussion response attached to a Rating Submission. |
| Media Asset | An image contributed with a Rating Submission. |
| Content Report | A request for a Moderator to review potentially prohibited content. |

### 4.2 Domain rules

1. A Thing may have many Rating Schemes.
2. A Rating Scheme shall belong to exactly one Thing and have exactly one creator.
3. A Rating Scheme shall contain at least one Criterion.
4. A Criterion shall belong to exactly one Rating Scheme.
5. A Rating Submission shall use exactly one Rating Scheme.
6. A completed Rating Submission shall contain one Criterion Score for every active Criterion in its Rating Scheme.
7. The creator of a Rating Scheme may publish the first Rating Submission using that scheme.
8. Other Members may reuse the Rating Scheme without changing its Criteria.
9. A Member may create a different Rating Scheme for a Thing when they want to judge it using different Criteria.
10. A Comment shall belong to exactly one Rating Submission.
11. A Media Asset shall be attributable to the Member who uploaded it and to the community content in which it appears.
12. A Moderator may remove prohibited content without deleting unrelated content under the same Thing.
13. Result Scores shall be presented as subjective community entertainment, not verified fact.

### 4.3 Example scenario

1. Member A searches for `Refrigerator` and finds no matching Thing.
2. Member A creates the Thing `Refrigerator`.
3. Member A creates a Rating Scheme named `How great is a refrigerator?` with Criteria such as `Usefulness`, `Noise`, and `Joy`.
4. Member A scores each Criterion, adds a written reaction and an image, and publishes the Rating Submission.
5. Member B searches for `Refrigerator` and sees the Thing page, Member A's Result Score, Criteria, written reaction, image, and discussion.
6. Member B reuses Member A's Rating Scheme, submits their own Criterion scores, and receives a separate Result Score.
7. Member B comments on Member A's Rating Submission.
8. If an uploaded image violates the content policy, a Moderator removes that image while preserving the lawful rating and discussion where appropriate.

## 5. Functional Requirements

All stable functional requirements use `shall` statements. Priorities are `Must`, `Should`, or `Could`. Acceptance evidence describes the minimum observable behaviour needed to verify the requirement.

### 5.1 Authentication and access

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-AUTH-01 | The system shall allow a new user to register a Member account using a unique identifier and password. | Must | A valid registration creates one account; duplicate identifiers and invalid passwords are rejected with user-facing feedback. |
| FR-AUTH-02 | The system shall allow a registered Member to sign in securely and establish an authenticated session. | Must | Valid credentials create a session; invalid credentials do not reveal whether a particular account exists. |
| FR-AUTH-03 | The system shall allow an authenticated Member to sign out and shall invalidate the active session. | Must | A signed-out session cannot access an authenticated-only endpoint. |
| FR-AUTH-04 | **Provisional:** The system shall allow Visitors to search and read public Things, Rating Submissions, images, and Comments without signing in. | Should | A signed-out visitor can open public read-only pages but cannot perform a write action. |
| FR-AUTH-05 | **Provisional:** The system shall require authentication before a user creates, edits, rates, comments on, uploads to, reports, or deletes community content. | Must | Every protected user interface and backend endpoint rejects an unauthenticated write request. |

### 5.2 Thing discovery and creation

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-THG-01 | The system shall allow an authenticated Member to create a Thing with a non-empty name and a subject type indicating whether it is tangible or abstract. | Must | A valid Thing is stored and becomes searchable; an empty name is rejected. |
| FR-THG-02 | The system shall allow any authenticated Member to publish a new Thing without prior Moderator approval. | Must | A newly created valid Thing becomes publicly visible immediately unless automatically blocked by a technical validation rule. |
| FR-THG-03 | The system shall allow a user to search for Things by name. | Must | A query returns matching Things and clearly displays a no-results state when no match exists. |
| FR-THG-04 | The system shall display a Thing detail page containing all active Rating Schemes and Rating Submissions associated with that Thing. | Must | Opening a Thing displays every active associated contribution without exposing content removed by moderation. |
| FR-THG-05 | The system shall display the written reactions, active Media Assets, Result Scores, and Comments associated with the Rating Submissions shown on a Thing page. | Must | The Thing page exposes the complete active community content hierarchy and correctly attributes each contribution. |
| FR-THG-06 | **Provisional:** The system shall warn a Member when the proposed Thing name is similar to an existing Thing name before creating a possible duplicate. | Should | A duplicate-like name produces a choice to use the existing Thing or continue creating a distinct Thing. |

### 5.3 Rating Scheme creation

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-SCH-01 | The system shall allow an authenticated Member to create a Rating Scheme for an existing Thing. | Must | A valid scheme is stored under exactly one Thing and attributed to its creator. |
| FR-SCH-02 | The system shall require the creator to add at least one non-empty Criterion before a Rating Scheme can be published. | Must | Publication remains disabled while no valid Criterion exists. |
| FR-SCH-03 | The system shall allow the creator to add, rename, reorder, and remove Criteria before publishing the Rating Scheme. | Must | The saved scheme reflects the final ordered Criterion list. |
| FR-SCH-04 | The system shall prevent a Member who reuses a published Rating Scheme from changing that scheme's Criteria. | Must | A non-owner rating flow reads the published Criteria but exposes no Criterion mutation operation. |
| FR-SCH-05 | **Provisional:** The system shall preserve the Criterion definitions used by an existing Rating Submission when its creator later edits a Rating Scheme. | Should | Previously published results remain reproducible after an allowed scheme revision. |

### 5.4 Rating and scoring

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-RAT-01 | The system shall allow an authenticated Member to assign one valid score to every Criterion in a selected Rating Scheme. | Must | The submission is accepted only when all required Criterion scores fall within the configured scale. |
| FR-RAT-02 | The system shall calculate a Result Score from the submitted Criterion scores using the published scoring rule. | Must | Given the same scheme version and Criterion scores, the backend returns the same Result Score. |
| FR-RAT-03 | The system shall calculate and validate the Result Score on the backend rather than trusting a client-supplied result. | Must | Altering a result in the browser request cannot change the stored backend calculation. |
| FR-RAT-04 | The system shall store each Rating Submission under the Thing associated with its Rating Scheme and attribute it to the submitting Member. | Must | The stored submission is reachable from the correct Thing and displays its author and timestamps. |
| FR-RAT-05 | The system shall allow an authenticated Member to reuse another Member's published Rating Scheme to create a separate Rating Submission. | Must | Two Members can submit different scores against the same immutable Criterion set. |
| FR-RAT-06 | **Provisional:** The system shall allow a Member to update their own Rating Submission and shall recalculate its Result Score. | Should | An authorised update changes the scores and produces a backend-recalculated result; another ordinary Member cannot perform the update. |
| FR-RAT-07 | The system shall display individual Result Scores in a way that does not claim they are objectively true or authoritative. | Must | Rating pages label scores as community opinions or entertainment results. |

### 5.5 Written reactions and comments

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-COM-01 | The system shall allow the author of a Rating Submission to include an optional written reaction with that submission. | Must | A reaction can be saved with the submission and is displayed under the correct Thing. |
| FR-COM-02 | The system shall allow an authenticated Member to post a Comment on another active Rating Submission. | Must | A valid Comment appears under the selected submission and is attributed to its author. |
| FR-COM-03 | The system shall reject an empty Comment. | Must | Whitespace-only content is not stored and produces a clear validation message. |
| FR-COM-04 | **Provisional:** The system shall allow a Member to edit or delete their own Comment but not another ordinary Member's Comment. | Should | Ownership checks are enforced by the backend for both user interface and direct HTTP requests. |
| FR-COM-05 | **Provisional:** The system shall use a single-level Comment list for the MVP and shall not support nested reply threads. | Should | Comments display directly under a Rating Submission without child-comment relationships. |

### 5.6 Images

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-MED-01 | The system shall allow an authenticated Member to attach an image to their Rating Submission. | Must | A valid image is stored, attributed, and displayed under the correct Thing and submission. |
| FR-MED-02 | The system shall validate every uploaded file by allowed media type and configured size limit before storage. | Must | A disallowed or oversized file is rejected without being served as public content. |
| FR-MED-03 | The system shall prevent one ordinary Member from modifying or deleting another Member's image. | Must | Backend authorisation rejects an unauthorised image mutation. |
| FR-MED-04 | The system shall stop displaying a Media Asset after a Moderator removes it. | Must | The removed image is inaccessible through ordinary public pages and media URLs. |
| FR-MED-05 | **Provisional:** The system shall show a neutral placeholder when an image has been removed while retaining lawful surrounding content. | Should | A removed image does not break the Rating Submission layout or delete its unrelated text and scores. |

### 5.7 Reporting and moderation

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-MOD-01 | **Provisional:** The system shall allow an authenticated Member to report a Thing, Rating Submission, Comment, or Media Asset for Moderator review. | Must | A report records its reporter, target, reason, status, and creation time. |
| FR-MOD-02 | The system shall provide a custom moderation panel for privileged Moderators and shall not use Django's built-in admin site as the user-facing moderation solution. | Must | An authorised Moderator can access a purpose-built panel; an ordinary Member cannot. |
| FR-MOD-03 | The system shall allow a Moderator to locate and remove unlawful, violent, sexual, or otherwise prohibited community content. | Must | Removal from the custom panel prevents public access to the selected content. |
| FR-MOD-04 | The system shall limit Moderator access to community-content management and shall not expose developer-level system configuration. | Must | The custom panel contains only defined moderation actions and data. |
| FR-MOD-05 | **Provisional:** The system shall record the Moderator, target, reason, and timestamp for each moderation removal. | Should | A moderation audit entry is available to authorised Moderators. |
| FR-MOD-06 | The system shall preserve unrelated lawful content when a Moderator removes a specific prohibited image or Comment. | Must | Removing a child contribution does not cascade-delete the entire Thing or unrelated submissions. |

### 5.8 Ownership and content lifecycle

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-OWN-01 | The system shall enforce content ownership and moderation permissions on the backend for every create, update, and delete operation. | Must | Direct requests cannot bypass the permissions presented by the user interface. |
| FR-OWN-02 | **Provisional:** The system shall allow the creator of a Thing or Rating Scheme to edit its descriptive text while it has no dependent community submissions. | Could | The edit succeeds only while no other Member's dependent content would be reinterpreted. |
| FR-OWN-03 | **Provisional:** The system shall prevent destructive edits to published Rating Scheme Criteria after another Member has used the scheme. | Should | Used Criteria are immutable or versioned, preserving historical Result Scores. |
| FR-OWN-04 | **Provisional:** The system shall use a visible removed-content state instead of silently reassigning deleted community content to another author. | Should | Attribution remains honest and deleted content is not represented as authored by another Member. |

### 5.9 AJAX and interaction feedback

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-AJX-01 | The system shall use AJAX for appropriate dynamic interactions, including rating entry, Comment submission, status changes, and moderation actions, without requiring a full page reload. | Must | Successful actions update the relevant visible state in place. |
| FR-AJX-02 | The system shall display explicit success, validation, and failure feedback for each AJAX operation. | Must | Network, validation, authorisation, and server failures do not fail silently or corrupt the displayed state. |
| FR-AJX-03 | The backend shall apply the same validation and authorisation to AJAX requests as to any equivalent non-AJAX request. | Must | Directly constructed requests cannot bypass business rules. |

### 5.10 RESTful API

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---:|---|
| FR-API-01 | The system shall expose at least four documented RESTful JSON endpoints that allow external clients to interact with selected community resources. | Must | API documentation lists the endpoints, verbs, authentication, examples, errors, and limitations. |
| FR-API-02 | The REST API shall support create, read, update, and delete operations across its documented resource set using appropriate HTTP verbs. | Must | Automated API tests verify the supported CRUD matrix. |
| FR-API-03 | The REST API shall validate input, return consistent JSON error responses, and enforce authentication and ownership where required. | Must | Invalid and unauthorised requests receive appropriate non-2xx status codes and do not mutate data. |

Proposed resource endpoints are:

- `/api/things/` and `/api/things/{id}/`;
- `/api/things/{id}/schemes/` and `/api/schemes/{id}/`;
- `/api/schemes/{id}/submissions/` and `/api/submissions/{id}/`;
- `/api/submissions/{id}/comments/` and `/api/comments/{id}/`;
- `/api/reports/` and `/api/reports/{id}/`.

The final CRUD matrix remains TBD.

## 6. Data Requirements

### 6.1 Preliminary entity catalogue

The following model contains more than the six meaningful business tables required by the course. Django-generated authentication and session tables are not counted.

| Entity | Purpose | Preliminary fields |
|---|---|---|
| UserProfile | Stores community-specific Member information in a one-to-one relationship with the authentication user | id, user_id, display_name, bio, avatar_path, created_at, updated_at |
| Thing | Represents a tangible or abstract subject | id, created_by_id, name, normalised_name, subject_type, description, status, created_at, updated_at |
| RatingScheme | Defines one reusable way to judge one Thing | id, thing_id, creator_id, title, description, scale_min, scale_max, formula_version, status, created_at, updated_at |
| Criterion | Defines one scored dimension and its order within a Rating Scheme | id, rating_scheme_id, name, description, weight, display_order, status |
| RatingSubmission | Stores one Member's completed use of one Rating Scheme | id, rating_scheme_id, author_id, result_score, reaction_text, status, created_at, updated_at |
| CriterionScore | Stores one score within one Rating Submission | id, rating_submission_id, criterion_id, score |
| Comment | Stores discussion under a Rating Submission | id, rating_submission_id, author_id, body, status, created_at, updated_at |
| MediaAsset | Stores image metadata and moderation state | id, rating_submission_id, uploader_id, storage_path, mime_type, byte_size, status, created_at |
| ContentReport | Tracks a request for Moderator review | id, reporter_id, target_type, target_id, reason, details, status, resolved_by_id, created_at, resolved_at |
| ModerationAction | **Provisional:** Records a moderation audit event | id, moderator_id, target_type, target_id, action, reason, created_at |

### 6.2 Required relationship coverage

- **One-to-one:** authentication user to UserProfile.
- **One-to-many:** Thing to RatingScheme; RatingScheme to Criterion; RatingScheme to RatingSubmission; RatingSubmission to Comment; RatingSubmission to MediaAsset.
- **Many-to-many:** Members to Things through RatingSubmissions. Many Members may rate many Things, and the associative business records preserve the selected Rating Scheme and submitted scores.

### 6.3 Integrity rules

- A Thing name shall be non-empty after trimming.
- A Rating Scheme shall reference an active Thing.
- A Criterion name shall be non-empty and unique within its Rating Scheme unless a later decision explicitly permits duplicates.
- A Criterion Score shall be unique for the pair `(rating_submission, criterion)`.
- A Criterion Score shall fall inside the Rating Scheme's configured scale.
- A Rating Submission shall not include a Criterion from another Rating Scheme.
- Derived Result Scores shall be calculated by the backend and shall not be accepted directly from clients.
- Moderation and soft-deletion states shall be represented explicitly so prohibited content is not accidentally returned by public queries.
- Image metadata shall be preserved even when a public image is removed, if required for moderation audit evidence.

### 6.4 Retention and deletion

The exact retention policy is TBD. The recommended policy is to soft-delete community records that are needed for moderation evidence and permanently remove prohibited image bytes from public storage. Account deletion, anonymisation, and retention periods require a later decision.

## 7. Preliminary User Journeys

### UJ-01: Discover community opinions

1. The user enters a Thing name in search.
2. The system returns matching Things or a no-results state.
3. The user opens a Thing.
4. The system displays its Rating Schemes, individual Rating Submissions, Result Scores, reactions, images, and Comments.

### UJ-02: Create and rate a new Thing

1. An authenticated Member searches for a Thing.
2. If no suitable match exists, the Member creates it.
3. The Member creates a Rating Scheme and defines its Criteria.
4. The Member scores every Criterion.
5. The Member optionally adds a written reaction and image.
6. The system validates the input, calculates the Result Score, and publishes the Rating Submission under the Thing.

### UJ-03: Reuse another Member's Rating Scheme

1. An authenticated Member opens a Thing.
2. The Member selects an existing Rating Scheme.
3. The system displays the scheme's immutable Criteria.
4. The Member submits scores for all Criteria.
5. The system calculates and publishes a separate Result Score attributed to that Member.

### UJ-04: Discuss a rating

1. An authenticated Member opens a Rating Submission.
2. The Member submits a non-empty Comment.
3. The system validates and displays it without a full page reload.

### UJ-05: Moderate prohibited content

1. A Moderator opens the custom moderation panel.
2. The Moderator locates content directly or through a Content Report.
3. The Moderator reviews the contribution and its context.
4. The Moderator removes the prohibited target and records a reason.
5. The public page stops serving the removed target but retains unrelated lawful content.

## 8. Wireframe Inventory

Assignment 1 wireframes should cover the following generic views and map every functional requirement to at least one state:

1. Landing page and global search.
2. Search results, including no-results and similar-name states.
3. Thing detail with multiple Rating Schemes and Rating Submissions.
4. Create Thing form.
5. Create Rating Scheme and Criterion editor.
6. Rating flow using a newly created scheme.
7. Rating flow reusing another Member's scheme.
8. Rating Submission detail with reaction, images, and Comments.
9. Member profile and own-content management.
10. Registration, sign-in, sign-out, and authentication feedback.
11. Content reporting dialog or page.
12. Custom Moderator dashboard, report queue, content review, and removal confirmation.
13. Removed-content placeholder.
14. Loading, validation-error, network-error, empty, permission-denied, and success states for relevant views.
15. Responsive mobile and desktop variants for layout-sensitive views.

## 9. Non-Functional Requirements

### 9.1 Usability and accessibility

- NFR-USE-01: The system shall provide a consistent, modern, responsive interface on the agreed desktop and mobile viewport range.
- NFR-USE-02: The system shall provide visible labels, keyboard-accessible controls, meaningful focus states, and text alternatives for informative images.
- NFR-USE-03: The system shall distinguish loading, empty, success, validation-error, permission-error, and server-error states.
- NFR-USE-04: The system shall retain the existing prototype's playful visual identity where it does not reduce legibility, accessibility, or implementation feasibility.

### 9.2 Performance and reliability

- NFR-PERF-01: The production system shall support at least five concurrent users without an identifiable application error.
- NFR-PERF-02: The system shall degrade gracefully when its external API is slow or unavailable; core creation, rating, browsing, and moderation functions shall continue to operate.
- NFR-PERF-03: Reusable external data shall be cached or stored locally to prevent unnecessary repeated API calls.
- NFR-REL-01: Production services shall recover automatically after an EC2 server restart without manual process startup.
- NFR-REL-02: Application errors shall not expose stack traces or internal implementation details to users.

### 9.3 Security and privacy

- NFR-SEC-01: Authentication, authorisation, validation, scoring, and moderation checks shall be enforced by the backend.
- NFR-SEC-02: The system shall use Django protections and secure implementation practices to defend against XSS, SQL injection, and CSRF.
- NFR-SEC-03: The production system shall use HTTPS and shall set `DEBUG=False`.
- NFR-SEC-04: The system shall not expose source code, secret keys, environment files, private keys, command-history secrets, or sensitive server files through HTTP.
- NFR-SEC-05: Production database access shall use least privilege appropriate to application runtime operations.
- NFR-SEC-06: SSH access shall use private-key authentication and shall disable password-based login.
- NFR-SEC-07: Uploaded images shall be treated as untrusted data, validated before storage, and served without executable privileges.
- NFR-SEC-08: The final security design shall implement two course-approved simple security measures and one course-approved advanced security measure. The selected measures are TBD.

### 9.4 Maintainability and testing

- NFR-MNT-01: The Django backend shall follow MVT with clear separation of models, views, templates, services, validation, and permissions.
- NFR-MNT-02: URL routing, static files, media files, settings, and error handling shall be modular and documented.
- NFR-TST-01: Backend tests shall cover models, views, API endpoints, permissions, scoring, validation, ownership, moderation, and failure cases.
- NFR-TST-02: The project shall target approximately 85% meaningful coverage of critical backend files, with agreed exclusions documented.

## 10. Technical and Course Constraints

- The backend shall use Django.
- The database shall contain at least six meaningful business tables and demonstrate one-to-one, one-to-many, and many-to-many relationships.
- The system shall provide at least four RESTful JSON endpoints and support CRUD across the documented resource set.
- The system shall provide a custom, non-developer moderation panel rather than using Django's built-in admin as the submitted administrative interface.
- The frontend shall include custom CSS and meaningful custom JavaScript and shall use AJAX broadly where immediate feedback is appropriate.
- The system shall integrate at least one value-adding external API through the Django backend, with caching and a failure fallback. The API is TBD.
- The team shall choose either a Modern Frontend Design or meaningful WebSocket integration for Assignment 2. The choice is TBD.
- At least five core capabilities shall require authentication.
- The project shall use Django's built-in testing framework and meaningful backend tests.
- Production shall be deployed to an AWS Learner Lab EC2 Linux instance.
- Nginx shall act as reverse proxy and shall serve static and media files.
- uWSGI shall run the Django application.
- Ports 22, 80, and 443 shall be configured as required by the assignment, with HTTP expected to redirect to HTTPS subject to tutor confirmation.
- The deployed system shall satisfy all twelve Assignment 3 security checks.

## 11. Preliminary Architecture Direction

The current course repository contains a Django 5.2.17 starter project. A separate public prototype uses React and Vite as a local Score-O-Matic tool.

The recommended low-risk implementation is:

- Django models, authentication, permissions, views, REST API, scoring, moderation, and media handling;
- Django templates for the primary pages;
- custom CSS adapted from the prototype's visual language;
- targeted JavaScript and Fetch-based AJAX for rating, comments, search feedback, and moderation;
- SQLite for local development, with the production database decision deferred;
- no LLM dependency in the core scoring path.

This direction is **Provisional**. Reusing the React frontend remains possible but would increase integration and deployment work for a two-person beginner team.

## 12. Course Traceability Summary

| Assignment expectation | Planned product evidence |
|---|---|
| At least five authenticated-only core functions | Create Thing; create scheme and initial submission; reuse scheme; comment; report content |
| At least six business tables | UserProfile, Thing, RatingScheme, Criterion, RatingSubmission, CriterionScore, Comment, MediaAsset, ContentReport |
| One-to-one | Authentication user to UserProfile |
| One-to-many | Thing to RatingScheme and other listed parent-child relationships |
| Many-to-many | Members to Things through RatingSubmissions |
| Custom admin panel | Purpose-built Moderator dashboard and content-removal workflow |
| At least four REST endpoints and CRUD | Things, schemes, submissions, comments, and reports APIs |
| Broad AJAX | Rating entry, Comments, state changes, reporting, and moderation |
| External API | TBD; backend-only, cached, and non-critical |
| Modern Web option | TBD between frontend architecture and WebSocket; modern frontend is currently lower risk |
| Security | Backend permissions, upload safety, HTTPS, secure sessions, two simple and one advanced measure TBD |
| AWS production deployment | EC2 Linux, Nginx, uWSGI, HTTPS, automatic restart, five concurrent users |

## 13. Risks

| Risk | Impact | Initial response |
|---|---|---|
| Arbitrary user-created subjects cause duplicates or ambiguous identity | Fragmented search and community content | Normalise names, show similar matches, and define merge rules before implementation |
| Different Rating Schemes produce incomparable Result Scores | Misleading Thing-level aggregate | Display scheme-specific submissions until an aggregation rule is confirmed |
| User-uploaded unlawful, violent, or sexual images | Safety, assessment, and legal risk | Strict upload validation, reporting, custom moderation, removal, and audit trail |
| Two beginner developers must learn the full stack | Schedule and quality risk | Keep the MVP narrow, favour Django templates, test continuously, and defer AI/WebSockets |
| External API or LLM is unavailable | Broken core workflow | Keep all core rating functions local and use cached external data only as enhancement |
| Published Criteria are edited after other Members reuse them | Historical scores become irreproducible | Make used schemes immutable or version them |
| Assignment 3 uses binary/stepwise checks | Large mark loss from one missing deployment or security item | Treat every A3 checklist item as a Must requirement from the start |

## 14. Open Questions

The following decisions must be resolved before this SRS becomes a submission baseline:

1. Does a Thing page show only individual Result Scores, or also one overall community score?
2. If an overall score is shown, how are submissions using different Rating Schemes combined without becoming misleading?
3. What score input is used: 1-5 stars, 0-10, 0-100, letter grades, or another scale?
4. Do Criteria have numeric weights, as in the prototype, or are they equally weighted in the MVP?
5. What is the precise Result Score formula and rounding rule?
6. Does `anyone can add content` mean any authenticated Member, or are anonymous writes permitted?
7. Can a Member submit more than one Rating Submission for the same Rating Scheme?
8. Can the creator edit a published Rating Scheme before or after another Member has used it?
9. Is a written reaction part of a Rating Submission, distinct from later Comments?
10. Are Comments single-level or may they have nested replies?
11. Can a Rating Submission contain one image or multiple images, and what are the file size, type, and dimension limits?
12. Are images attached to the Thing itself, to a Rating Scheme, or to an individual Rating Submission?
13. What exact content policy defines unlawful, violent, sexual, or otherwise prohibited content?
14. Should Members be able to report content, or must Moderators find all violations themselves?
15. Can authors edit or delete their own Things, schemes, submissions, images, and Comments?
16. How are duplicate Things detected, distinguished, merged, or redirected?
17. Does the MVP use free-form subject names only, or also categories and discovery tags?
18. What information is required when creating a Thing beyond its name and tangible/abstract type?
19. Which pages are public, and which require authentication?
20. Which two simple and one advanced security measures will the team implement?
21. Which external API will add value without becoming a core dependency?
22. Will the implementation use Django templates or retain the React frontend?
23. Which database will be used in production?
24. What are the supported browsers, viewport sizes, and accessibility target?
25. What is the final product name and UI language?

## 15. Approval State

This draft captures the confirmed concept and a proposed course-aligned MVP. It is not yet approved as the shared requirements baseline. The team should resolve the Open Questions in decision-tree order, update requirements and acceptance criteria, and then explicitly approve the resulting version before implementation is treated as committed scope.
