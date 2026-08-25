from dataclasses import dataclass

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User
from django.db import transaction

from ..graphql.jwt import (
    generate_access_token,
    generate_refresh_token,
    get_user_from_refresh_token,
    invalidate_user_tokens,
    revoke_refresh_token,
)


@dataclass(frozen=True)
class AuthenticationResult:
    user: User
    access_token: str
    refresh_token: str


def _tokens_for(user):
    return AuthenticationResult(
        user=user,
        access_token=generate_access_token(user),
        refresh_token=generate_refresh_token(user),
    )


@transaction.atomic
def signup(username, email, password):
    if User.objects.filter(username=username).exists():
        raise Exception("Username already exists")
    if User.objects.filter(email=email).exists():
        raise Exception("Email already exists")

    user = User.objects.create_user(username=username, email=email, password=password)
    try:
        customer_group = Group.objects.get(name="Customer")
    except Group.DoesNotExist:
        raise Exception("Customer group does not exist")
    user.groups.add(customer_group)
    return _tokens_for(user)


def login(username, password):
    user = authenticate(username=username, password=password)
    if user is None:
        raise Exception("Invalid username or password")
    return _tokens_for(user)


@transaction.atomic
def refresh(refresh_token):
    user = get_user_from_refresh_token(refresh_token)
    if user is None:
        raise Exception("Invalid or expired refresh token")
    if not revoke_refresh_token(refresh_token):
        raise Exception("Invalid or expired refresh token")
    return _tokens_for(user)


@transaction.atomic
def logout(refresh_token):
    user = get_user_from_refresh_token(refresh_token)
    if user is None or not revoke_refresh_token(refresh_token):
        raise Exception("Invalid or expired refresh token")
    invalidate_user_tokens(user)
    return True
