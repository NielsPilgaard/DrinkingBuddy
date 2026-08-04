we need OTEL metrics, spans and logs from our entire stack if possible, redis, postgres, fastapi, app. as much auto instrumentation as possible. remember to get the python config right, it can be tricky.

this is going to introduce some settings in the api, we should have a pydantic settings object reading from env