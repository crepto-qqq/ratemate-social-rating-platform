from .models import AccountSecurity


def verified_force_login(client, user):
    AccountSecurity.objects.update_or_create(user=user, defaults={'email_verified': True})
    client.force_login(user)
    session = client.session
    session['auth_mfa_user'] = user.pk
    session.save()
