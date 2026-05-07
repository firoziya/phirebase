import re
import time
import warnings
import threading
import six
import requests


end_of_field = re.compile(r'\r\n\r\n|\r\r|\n\n')

class SSEClient(object):
    def __init__(self, url, session, build_headers, last_id=None, retry=3000, **kwargs):
        self.url = url
        self.last_id = last_id
        self.retry = retry
        self.running = True
        self.session = session
        self.build_headers = build_headers
        self.start_time = None
        self.requests_kwargs = kwargs

        if 'headers' not in self.requests_kwargs:
            self.requests_kwargs['headers'] = {}
        self.requests_kwargs['headers']['Cache-Control'] = 'no-cache'
        self.requests_kwargs['headers']['Accept'] = 'text/event-stream'

        self.buf = u''
        self._connect()

    def _connect(self):
        if self.last_id:
            self.requests_kwargs['headers']['Last-Event-ID'] = self.last_id
        headers = self.build_headers()
        self.requests_kwargs['headers'].update(headers)
        self.requester = self.session or requests
        self.resp = self.requester.get(self.url, stream=True, **self.requests_kwargs)
        self.resp_iterator = self.resp.iter_content(decode_unicode=True)
        self.resp.raise_for_status()

    def _event_complete(self):
        return re.search(end_of_field, self.buf) is not None

    def __iter__(self):
        return self

    def __next__(self):
        while not self._event_complete():
            try:
                nextchar = next(self.resp_iterator)
                self.buf += nextchar
            except (StopIteration, requests.RequestException):
                time.sleep(self.retry / 1000.0)
                self._connect()

                head, sep, tail = self.buf.rpartition('\n')
                self.buf = head + sep
                continue

        split = re.split(end_of_field, self.buf)
        head = split[0]
        tail = "".join(split[1:])

        self.buf = tail
        msg = Event.parse(head)

        if msg.data == "credential is no longer valid":
            self._connect()
            return None

        if msg.data == 'null':
            return None

        if msg.retry:
            self.retry = msg.retry

        if msg.id:
            self.last_id = msg.id

        return msg

    if six.PY2:
        next = __next__


class Event(object):
    sse_line_pattern = re.compile('(?P<name>[^:]*):?( ?(?P<value>.*))?')

    def __init__(self, data='', event='message', id=None, retry=None):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def dump(self):
        lines = []
        if self.id:
            lines.append('id: %s' % self.id)

        if self.event != 'message':
            lines.append('event: %s' % self.event)

        if self.retry:
            lines.append('retry: %s' % self.retry)

        lines.extend('data: %s' % d for d in self.data.split('\n'))
        return '\n'.join(lines) + '\n\n'

    @classmethod
    def parse(cls, raw):
        msg = cls()
        for line in raw.split('\n'):
            m = cls.sse_line_pattern.match(line)
            if m is None:
                warnings.warn('Invalid SSE line: "%s"' % line, SyntaxWarning)
                continue

            name = m.groupdict()['name']
            value = m.groupdict()['value']
            if name == '':
                continue

            if name == 'data':
                if msg.data:
                    msg.data = '%s\n%s' % (msg.data, value)
                else:
                    msg.data = value
            elif name == 'event':
                msg.event = value
            elif name == 'id':
                msg.id = value
            elif name == 'retry':
                msg.retry = int(value)

        return msg

    def __str__(self):
        return self.data