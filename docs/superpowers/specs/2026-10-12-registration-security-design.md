# Registration email and email OTP authentication

Registration requires a real email address. RateMate sends a six-digit activation code and keeps the new account inactive until the code is verified. A verified account still signs in with username and password, followed by a new email code for each login. Existing accounts without a verified email must bind and verify one after their password is checked.

Codes expire after five minutes, are hashed in the database, tied to the initiating session, and are single use. Resending invalidates the earlier code and is limited to once per minute; at most ten sends are allowed per account per hour. Five incorrect guesses in ten minutes temporarily block further attempts. Email delivery errors never complete registration or authentication. Logout clears the session; sessions created before this change cannot access authenticated features without the new MFA marker.

New passwords require at least eight characters, uppercase and lowercase letters, and a digit. Django's common-password and account-similarity checks run on registration and password changes. Existing passwords still work at the first login step. Profile password changes update Django's account password and preserve the verified current session.

The login and registration screen, errors, OTP flow, and logout control use English. Local Docker development delivers messages to Mailpit at localhost:8025. Real QQ SMTP requires an authorization code in the ignored root .env; no sender credential belongs in Git.

Validation uses PostgreSQL-backed Django tests, migration checks, the frontend production build, and HTTP checks through the Vite proxy.
