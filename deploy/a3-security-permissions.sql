BEGIN;
REVOKE ALL ON TABLE public.accounts_loginthrottle FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.accounts_loginthrottle TO ratemate_app;
COMMIT;
