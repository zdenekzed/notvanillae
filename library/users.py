from google.appengine.api import users
import oauth2client.appengine

import settings
import routes
from library import utils


def get_current_user():
    return users.get_current_user()


def is_signed_in():
    user = users.get_current_user()
    if user:
        return True
    else:
        return False


def create_google_signout_url():
    return users.create_logout_url('/')


def create_google_signin_url(redirect=None):
    return users.create_login_url(redirect or routes.configs.get_default_redirect_after_signin().url)


class OAuth2DecoratorLocalRedirect(oauth2client.appengine.OAuth2Decorator):
    """Utility for making OAuth 2.0 easier.
    """

    def __init__(self, client_id, client_secret, scope, **kwargs):

        super(OAuth2DecoratorLocalRedirect, self).__init__(client_id, client_secret, scope, **kwargs)

    def oauth_required(self, method):
        """Decorator that starts the OAuth 2.0 dance.

        Starts the OAuth dance if a user isn't logged in
        or if they haven't already granted access for this application.

        Args:
          method: callable, to be decorated method of a webapp.RequestHandler instance.
        """

        def check_oauth(request_handler, *args, **kwargs):

            if self._in_error:
                self._display_error_message(request_handler)
                return

            origin_url = request_handler.request.get('origin') or request_handler.request.path
            local_authorize_url = utils.add_url_params(settings.urls.canonical_secure + routes.configs.get('authorize').url, {'origin': origin_url})

            # Ensure user is logged in and redirect if not
            user = users.get_current_user()
            # Don't use @login_decorator as this could be used in a POST request.
            if not user:
                signin_url = utils.add_url_params(routes.configs.get('signin').url, {'origin': origin_url})
                return request_handler.redirect(signin_url)

            self._create_flow(request_handler)

            # Store the request URI in 'state' so we can use it later
            self.flow.params['state'] = oauth2client.appengine._build_state_value(request_handler, user)
            self.credentials = oauth2client.appengine.StorageByKeyName(
                oauth2client.appengine.CredentialsModel, user.user_id(), 'credentials').get()

            if not self.has_credentials():
                return request_handler.redirect(local_authorize_url)

            try:
                return method(request_handler, *args, **kwargs)
            except oauth2client.appengine.AccessTokenRefreshError:
                return request_handler.redirect(self.authorize_url())

        return check_oauth


# Set up an OAuth2Decorator object to be used for authentication
oauth_decorator = OAuth2DecoratorLocalRedirect(
    client_id=settings.oauth.client_id,
    client_secret=settings.oauth.client_secret,
    scope=settings.oauth.scope)

@oauth_decorator.oauth_required
def verify_oauth(request_handler):
    pass