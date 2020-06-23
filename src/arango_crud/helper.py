"""This module helps with making requests using requests. This could use the
requests library HTTPAdapter, which uses the urllib3 retry tool, but it is
not adequately granular"""
import logging
import requests
import time
from http.client import responses

logger = logging.getLogger(__name__)


def http_get(config, url: str, **kwargs):
    return http_method('get', config, url, **kwargs)


def http_post(config, url: str, **kwargs):
    return http_method('post', config, url, **kwargs)


def http_patch(config, url: str, **kwargs):
    return http_method('patch', config, url, **kwargs)


def http_put(config, url: str, **kwargs):
    return http_method('put', config, url, **kwargs)


def http_delete(config, url: str, **kwargs):
    return http_method('delete', config, url, **kwargs)


def http_method(method, config, partial_url: str, **kwargs):
    """
    Performs the request using the given http verb (e.g., get, post, put). This
    will handle backing off according to the specified config. If backoffs are
    exceeded this raises a requests.exceptions.RequestException.
    """
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    if 'timeout' not in kwargs:
        kwargs['timeout'] = config.timeout_seconds
    if 'verify' not in kwargs and config.verify is not None:
        kwargs['verify'] = config.verify

    request_number = 1

    authorizing = kwargs.pop('add_authorization', True)
    reattempted_auth = False
    if authorizing:
        config.auth.authorize(kwargs['headers'], config)

    log_extra = kwargs.get('json', {}).get('_key')
    if log_extra is not None:
        log_extra = f' (key={log_extra})'
    else:
        log_extra = ''

    while True:
        url = config.cluster.select_next_url()
        if url.endswith('/'):
            url = url[:-1]
        if not partial_url.startswith('/'):
            url += '/'
        url += partial_url

        request_start_at = time.time()
        error = None
        response = None
        try:
            response = getattr(requests, method)(url, **kwargs)
        except requests.exceptions.RequestException as e:
            error = e
        request_time_ms = int((time.time() - request_start_at) * 1000)

        if response is not None:
            response_bytes = len(response.content)
            logger.info(
                '(%s ms) COMPLETE: %s %s%s ||| %s %s; %s bytes',
                request_time_ms, method.upper(), url, log_extra,
                response.status_code,
                responses.get(response.status_code, 'Unknown Status Code'),
                response_bytes
            )

            if response.status_code < 500:
                if (authorizing
                        and response.status_code == 401
                        and not reattempted_auth
                        and config.auth.try_recover_auth_failure()):
                    config.auth.authorize(kwargs['headers'], config)
                    reattempted_auth = True
                else:
                    return response

        if error is not None:
            logger.info(
                '(%s ms) ERROR: %s %s%s ||| %s',
                request_time_ms, method.upper(), url, log_extra, error
            )

        delay = config.back_off.get_back_off(request_number)
        if delay is None:
            raise requests.exceptions.RequestException(
                f'Max retries ({request_number - 1}) exceeded for endpoint {partial_url}'
            )
        request_number += 1
        time.sleep(delay)
