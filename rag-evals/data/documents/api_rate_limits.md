# API Rate Limits

The Monthly plan allows 60 API requests per minute.

The Pro plan allows 600 API requests per minute.

The Enterprise plan allows 6000 API requests per minute.

Exceeding the limit returns HTTP 429. Clients should retry with exponential
backoff.
