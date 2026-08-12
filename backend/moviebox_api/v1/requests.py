"""
Provide ways to interact with Moviebox using `httpx`
"""

import json

import httpx
from httpx import Response
from httpx._config import DEFAULT_TIMEOUT_CONFIG
from httpx._types import CookieTypes, HeaderTypes, ProxyTypes, TimeoutTypes

from moviebox_api.v1.constants import DOWNLOAD_REQUEST_HEADERS
from moviebox_api.v1.exceptions import EmptyResponseError, MissingAuthError
from moviebox_api.v1.helpers import (
    get_absolute_url,
    process_api_response,
)
from moviebox_api.v1.models import MovieboxAppInfo, UserInfo

request_cookies = {}

__all__ = ["Session"]


class Session:
    """Performs actual get & post http requests asynchronously
    with or without cookies on demand
    """

    _moviebox_app_info_url = get_absolute_url(
        r"/wefeed-h5-bff/app/get-latest-app-pkgs?app_name=moviebox"
    )

    _user_info_endpoint = (
        "https://h5-api.aoneroom.com/wefeed-h5api-bff/subject/search-suggest"
    )
    """Search suggestion responses are attached with auth bearer value as both 
    cookie and custom headers"""

    def __init__(
        self,
        headers: HeaderTypes | None = DOWNLOAD_REQUEST_HEADERS,
        cookies: CookieTypes | None = request_cookies,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        proxy: ProxyTypes | None = None,
        **httpx_kwargs,
    ):
        """Constructor for `Session`

        Args:
            headers (HeaderTypes  | None, optional): Http request headers. Defaults to DOWNLOAD_REQUEST_HEADERS.
            cookies (CookieTypes | None , optional): Http request cookies. Defaults to request_cookies.
            timeout (TimeoutTypes, optional): Http request timeout in seconds. Defaults to DEFAULT_TIMEOUT_CONFIG.
            proxy (ProxyTypes | None, optional): Http requests proxy. Defaults to None.

        httpx_kwargs : Other keyword arguments for `httpx.AsyncClient`
        """  # noqa: E501
        self._headers = headers
        self._cookies = cookies
        self._timeout = timeout
        self._proxy = proxy

        self._client = httpx.AsyncClient(
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            **httpx_kwargs,
        )

        self.moviebox_app_info: MovieboxAppInfo | None = None
        self.user_info: UserInfo | None = None
        self.__moviebox_app_info_fetched: bool = False
        """Used to track cookies assignment status"""

    def _validate_response(self, response: Response) -> Response:
        """Ensures response is not empty"""
        if response is None or not bool(response.content):
            raise EmptyResponseError(
                response, "Server returned an empty body response."
            )
        return response

    def __repr__(self):
        return rf"<Session(MovieBoxAPI) timeout={self._timeout}>"

    async def _request_with_fallback(self, method: str, url: str, **kwargs) -> Response:
        """
        Executes HTTP requests. Optimistically tries direct first, and
        falls back to rotated public proxies if blocked (403, 401, 406 or exception).
        """
        use_client = kwargs.pop('use_client', self._client)
        
        # Helper to execute request on client
        async def do_request(c):
            # Clean headers to let httpx handle Host and Accept-Encoding dynamically
            for headers_dict in [c.headers, kwargs.get('headers', {})]:
                for key in ['Host', 'host', 'Accept-Encoding', 'accept-encoding']:
                    if key in headers_dict:
                        try: del headers_dict[key]
                        except: pass
            if method.lower() == 'get':
                return await c.get(url, **kwargs)
            else:
                return await c.post(url, **kwargs)

        import api
        
        # 1. Try utilizing the cached working proxy first
        if api.active_proxy:
            try:
                p_client = httpx.AsyncClient(
                    headers=use_client.headers,
                    cookies=use_client.cookies,
                    proxy=api.active_proxy,
                    timeout=self._timeout,
                    verify=False
                )
                resp = await do_request(p_client)
                if resp.status_code == 200:
                    use_client.cookies.update(p_client.cookies)
                    return resp
            except Exception:
                if api.active_proxy:
                    failed_ip = api.active_proxy.replace("http://", "")
                    api.proxies_list = [p for p in api.proxies_list if p != failed_ip]
                    api.active_proxy = None

        # 2. Direct Optimistic Request attempt
        try:
            resp = await do_request(use_client)
            if resp.status_code == 200:
                return resp
            if resp.status_code in [403, 401, 406]:
                raise httpx.HTTPStatusError("Blocked by MovieBox", request=resp.request, response=resp)
        except (httpx.HTTPError, httpx.HTTPStatusError):
            pass

        # 3. Fallback retry loop via rotated public proxies
        for _ in range(5):
            p_url = await api.get_proxy_url()
            if p_url:
                try:
                    p_client = httpx.AsyncClient(
                        headers=use_client.headers,
                        cookies=use_client.cookies,
                        proxy=p_url,
                        timeout=self._timeout,
                        verify=False
                    )
                    resp = await do_request(p_client)
                    if resp.status_code == 200:
                        api.active_proxy = p_url  # Cache successful proxy
                        use_client.cookies.update(p_client.cookies)
                        return resp
                except Exception:
                    failed_ip = p_url.replace("http://", "")
                    api.proxies_list = [p for p in api.proxies_list if p != failed_ip]
                    api.active_proxy = None

        # Last resort: try direct one more time to raise exception
        return await do_request(use_client)

    async def get(self, url: str, params: dict = {}, **kwargs) -> Response:
        """Makes a http get request without server cookies from previous requests.
        """
        client = httpx.AsyncClient(
            headers=self._headers,
            cookies=self._cookies,
            proxy=self._proxy,
            timeout=self._timeout,
            **kwargs,
        )
        response = await self._request_with_fallback('get', url, params=params, use_client=client)
        response.raise_for_status()
        return self._validate_response(response)

    async def get_from_api(self, *args, **kwargs) -> dict:
        """Fetch data from api and extract the `data` field from the response
        """
        response = await self.get(*args, **kwargs)
        return process_api_response(response)

    async def get_with_cookies(
        self, url: str, params: dict = {}, **kwargs
    ) -> Response:
        """Makes a http get request with server-assigned cookies from previous
          requests.
        """
        await self.ensure_cookies_are_assigned()
        response = await self._request_with_fallback('get', url, params=params, use_client=self._client, **kwargs)
        response.raise_for_status()
        return self._validate_response(response)

    async def get_with_cookies_from_api(self, *args, **kwargs) -> dict:
        """Makes a http get request with server-assigned cookies from previous
        requests and extract the `data` field from the response.
        """
        response = await self.get_with_cookies(*args, **kwargs)
        return process_api_response(response)

    async def post(self, url: str, json: dict, **kwargs) -> Response:
        """Makes a http post request with both self assigned and server-
        assigned cookies
        """
        await self.ensure_cookies_are_assigned()
        response = await self._request_with_fallback('post', url, json=json, use_client=self._client, **kwargs)
        response.raise_for_status()
        return self._validate_response(response)

    async def post_to_api(self, *args, **kwargs) -> dict:
        """Sends data to api and extract the `data` field from the response
        """
        response = await self.post(*args, **kwargs)
        return process_api_response(response)

    async def ensure_cookies_are_assigned(self) -> bool:
        """Checks if the essential cookies are available if not update it.
        """
        if not self.__moviebox_app_info_fetched:
            # First run probably
            await self._fetch_user_info()
            await self._fetch_app_info()
            self.__moviebox_app_info_fetched = True

        return (
            self._client.cookies.get("account") is not None
            and self._client.cookies.get("token") is not None
        )

    async def _fetch_app_info(self) -> MovieboxAppInfo:
        """Fetches the moviebox app info but the main goal is to get the essential
          cookies required for requests such as download to go through.
        """
        response = await self._request_with_fallback('get', url=self._moviebox_app_info_url, use_client=self._client)
        response.raise_for_status()

        moviebox_app_info = process_api_response(response)

        if isinstance(moviebox_app_info, list):
            moviebox_app_info = moviebox_app_info[0]

        self.moviebox_app_info = MovieboxAppInfo(**moviebox_app_info)

        return self.moviebox_app_info

    async def _fetch_user_info(self) -> UserInfo:
        """Fetches the user info but the main goal is to get the essential
          cookies required for requests such as search & download to go through.
        """
        response = await self._request_with_fallback(
            'post', url=self._user_info_endpoint, json={"keyword": "avatar", "perPage": 0}, use_client=self._client
        )
        response.raise_for_status()

        user_info = response.headers.get("x-user")

        if not user_info:
            raise MissingAuthError(
                "App-info response misses x-user key in headers"
            )

        self.user_info = UserInfo(**json.loads(user_info))

        new_auth = {"Authorization": f"Bearer {self.user_info.token}"}

        self._client.headers.update(new_auth)

        return self.user_info

    update_session_cookies = _fetch_app_info
