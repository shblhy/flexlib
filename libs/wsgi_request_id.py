import uuid
import functools
import re

# note that this pattern supports either a full UUID, or a "squashed" UUID
# like the kind some certain PaaS routers send:
#
#     full:     01234567-89ab-cdef-0123-456789abcdef
#     squashed: 0123456789abcdef0123456789abcdef
#
PATTERN = re.compile(
    "^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$"
)
# ugh, RFC's are shitty. this doesn't work when both headers are sent
# through at the same time. *shrugs*
HEADERS = ['HTTP_REQUEST_ID', 'HTTP_X_REQUEST_ID']


class RequestID(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        ids = [self._generate_id()] + self._extract_request_ids(environ)

        environ['REQUEST_IDS'] = ids
        environ['REQUEST_ID'] = ids[0]

        def inject_headers(status, headers, exc_info=None):
            headers.append(('Request-Id', ids[0]))
            return start_response(status, headers, exc_info)

        return self.app(environ, inject_headers)

    def _generate_id(self):
        return uuid.uuid4().__str__()

    def _extract_request_ids(self, env):
        ids = self._raw_request_ids(env)
        # return only uuids
        return list(filter(PATTERN.match, ids))

    def _raw_request_ids(self, env):
        def _extract_from_headers(container, key):
            container += env.get(key, '').strip().replace(' ', '').split(',')
            return container

        return functools.reduce(_extract_from_headers, HEADERS, [])


def init_app(app):
    return RequestID(app)
