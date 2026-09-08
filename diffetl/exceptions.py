from typing import Any, Dict, Mapping, Optional


class APIError(Exception):
    _message: Optional[str]
    http_status: Optional[int]
    headers: Optional[Mapping[str, str]]
    request_id: Optional[str]

    def __init__(
        self,
        message: Optional[str] = None,
        http_status: Optional[int] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        request_id: Optional[str] = None
    ) -> None:
        self._message = message
        self.http_status = http_status
        self.headers = headers
        self.json_body = json_body
        self.request_id = request_id

    def __str__(self):
        msg = self._message or "<empty message>"
        if self.request_id is not None:
            return "Request {0}: {1}".format(self.request_id, msg)
        else:
            return msg

    @property
    def user_message(self):
        return self._message

    def __repr__(self):
        return "%s(message=%r, http_status=%r, request_id=%r)" % (
            self.__class__.__name__,
            self._message,
            self.http_status,
            self.json_body,
            self.request_id,
        )
        
class APIConnectionError(APIError):
    should_retry: bool

    def __init__(
        self, 
        message, 
        http_status=None,
        json_body=None, 
        headers=None, 
        request_id= None,
        should_retry=False
    ) -> None:
        super().__init__(message, http_status, json_body, headers, request_id)
        self.should_retry = should_retry