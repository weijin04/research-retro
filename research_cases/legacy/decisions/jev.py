"""Small stdlib TypeSafe adapter. Only explicit synthetic/public inputs may leave.

Credentials come from TYPESAFE_API_KEY. Aliases never use persisted cache; exact
three-part model versions may reuse a successful result whose actual model matches.
A returned record is advisory, including when the network or contract fails.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import uuid
from urllib import request, error
from urllib.parse import urlsplit


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credentials or content to another endpoint.


class JevAdapter:
    def __init__(self, record_dir: Path, *, endpoint=None, api_key=None, timeout=25, max_attempts=2, transport=None):
        self.record_dir = Path(record_dir)
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self.endpoint = endpoint or 'https://api.typesafe.ai/v1/systemone'
        parts = urlsplit(self.endpoint)
        if parts.scheme != 'https' or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError('endpoint must be HTTPS without credentials, query or fragment')
        self.api_key = api_key if api_key is not None else os.getenv('TYPESAFE_API_KEY')
        self.timeout = min(max(float(timeout), 0.1), 60)
        self.max_attempts = min(max(int(max_attempts), 1), 3)
        self.transport = transport or self._http

    def _http(self, body):
        req = request.Request(self.endpoint, data=canonical(body).encode(), headers={
            'Authorization': 'Bearer ' + self.api_key, 'Content-Type': 'application/json'})
        with request.build_opener(NoRedirect).open(req, timeout=self.timeout) as response:
            return json.loads(response.read(2_000_000))

    @staticmethod
    def _validate(response, questions):
        if not isinstance(response, dict) or not isinstance(response.get('model'), str):
            raise ValueError('missing model')
        usage = response.get('usage')
        if not isinstance(usage, dict) or any(not isinstance(usage.get(k), int) or usage[k] < 0 for k in ('input_tokens', 'output_tokens')):
            raise ValueError('invalid usage')
        answers = response.get('answers', {})
        if set(answers) != set(questions):
            raise ValueError('answer ids mismatch')
        def probability(value):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1
        for key, q in questions.items():
            a = answers[key]
            if not isinstance(a, dict) or a.get('type') != q['type']:
                raise ValueError('answer type mismatch')
            if q['type'] == 'noul':
                if not probability(a.get('noul')): raise ValueError('invalid noul')
            else:
                p = a.get('probabilities', {})
                expected = set(q['criteria']) if q['type'] == 'choice' else {str(i) for i in range(len(q['criteria']))}
                if set(p) != expected or not all(probability(v) for v in p.values()) or abs(sum(p.values())-1) > .02:
                    raise ValueError('invalid distribution')
                if not probability(a.get('confidence')): raise ValueError('invalid confidence')
                if q['type'] == 'choice' and a.get('choice') not in expected: raise ValueError('invalid choice')
                if q['type'] == 'score':
                    score = a.get('score')
                    if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= len(expected)-1:
                        raise ValueError('invalid score')
                    if set(a.get('legend', {})) != expected: raise ValueError('invalid legend')

    def _save(self, record):
        record['record_id'] = uuid.uuid4().hex
        path = self.record_dir / (record['record_id'] + '.json')
        record['record_path'] = str(path)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(path)
        return record

    def evaluate(self, task_family, state, questions, questions_version, policy_version,
                 requested_model='jev-latest', egress_scope='denied', *, content_version='1',
                 candidate_version='1', source_refs=None, attempt_budget=None, use_cache=True):
        body = {'state': state, 'model': requested_model, 'questions': questions}
        metadata = dict(task_family=task_family, questions_version=questions_version,
                        policy_version=policy_version, content_version=content_version,
                        candidate_version=candidate_version, egress_scope=egress_scope,
                        source_refs=source_refs or [], endpoint=self.endpoint)
        key = digest({'body': body, **metadata, 'cache_policy': 'exact-three-part-model-only-v1'})
        record = dict(**metadata, request_hash=digest(body), cache_key=key, requested_model=requested_model,
                      actual_model=None, action='advisory', subsequent_verification=None,
                      timestamp=time.time(), cache_hit=False, retries=0, attempts=[], answers=None,
                      confidence=None, usage=None, latency_ms=0, status='error', error_category=None)
        if egress_scope not in ('synthetic', 'public'):
            record['error_category'] = 'privacy_denied'
            return self._save(record)  # Do not even persist denied plaintext.
        record['request'] = body
        pinned = bool(re.fullmatch(r'jev-\d+\.\d+\.\d+', requested_model))
        if use_cache and pinned:
            for path in sorted(self.record_dir.glob('*.json')):
                try: previous = json.loads(path.read_text())
                except (ValueError, OSError): continue
                if previous.get('cache_key') == key and previous.get('status') == 'ok' and previous.get('actual_model') == requested_model:
                    for field in ('answers', 'confidence', 'actual_model'):
                        record[field] = previous[field]
                    record.update(status='ok', cache_hit=True, cache_source=previous['record_id'],
                                  usage={'input_tokens': 0, 'output_tokens': 0}, original_usage=previous.get('usage'))
                    return self._save(record)
        if not self.api_key and self.transport == self._http:
            record['error_category'] = 'missing_credentials'
            return self._save(record)
        limit = self.max_attempts if attempt_budget is None else min(self.max_attempts, max(0, int(attempt_budget)))
        started = time.monotonic()
        for attempt in range(limit):
            retryable = False
            try:
                response = self.transport(body)
                record['raw_response'] = response
                self._validate(response, questions)
                record.update(status='ok', actual_model=response['model'], answers=response['answers'],
                              usage=response['usage'], confidence={k:v.get('confidence') for k,v in response['answers'].items()}, error_category=None)
                record['attempts'].append({'attempt': attempt + 1, 'status': 'ok'})
                break
            except error.HTTPError as exc:
                category = {401:'authentication', 403:'authentication', 422:'request_contract', 429:'rate_limit', 529:'overloaded'}.get(exc.code, 'http_error')
                retryable = exc.code in (429, 529, 502, 503, 504)
                exc.close()
                record['attempts'].append({'attempt':attempt+1, 'error_category': category, 'http_status':exc.code})
            except (TimeoutError, error.URLError):
                category, retryable = 'transport_timeout_or_network', True
                record['attempts'].append({'attempt':attempt+1, 'error_category': category})
            except (ValueError, TypeError, KeyError, AttributeError):
                category = 'response_contract'
                record['attempts'].append({'attempt':attempt+1, 'error_category': category})
            record['error_category'] = category
            if not retryable or attempt + 1 == limit: break
            time.sleep(min(2 ** attempt * .25, 1))
        if limit == 0: record['error_category'] = 'attempt_budget_exhausted'
        record['retries'] = max(0, len(record['attempts'])-1)
        record['latency_ms'] = round((time.monotonic()-started)*1000, 3)
        return self._save(record)
