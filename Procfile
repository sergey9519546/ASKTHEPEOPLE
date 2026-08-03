web: cd backend && exec gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 1 --threads 4 --timeout 300 --graceful-timeout 240 --access-logfile - --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s' wsgi:app
worker: cd backend && exec celery -A app.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=100 --time-limit=3600 --soft-time-limit=3000
