from intuitlib.client import AuthClient
from intuitlib.exceptions import AuthClientError

from django.conf import settings

def get_access_token():
    tokens = []
    filename = "quickBooks/apis/.token"
    f = open(filename, 'r')
    for line in f:
        tokens.append(line.rstrip())
    f.close()
    return tokens[0]

def refresh():
    tokens = []
    filename = "quickBooks/apis/.token"
    f = open(filename, 'r')
    for line in f:
        tokens.append(line.rstrip())
    f.close()

    auth_client = AuthClient(
        settings.CLIENT_ID,
        settings.CLIENT_SECRET,
        settings.REDIRECT_URI,
        settings.ENVIRONMENT,
        access_token=tokens[0],
        refresh_token=tokens[1],
    )
    try:
        auth_client.refresh()
    except AuthClientError as e:
        print(e.status_code)
        print(e.intuit_tid)

    print("----------")
    print([auth_client.access_token == tokens[0], auth_client.refresh_token == tokens[1]])
    print("----------")

    f = open(filename, 'w')
    f.write("{0}\n".format(auth_client.access_token))
    f.write("{0}\n".format(auth_client.refresh_token))
    f.close()
    return

