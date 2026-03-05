web: gunicorn -b 0.0.0.0:$PORT --log-level info --timeout 120 --worker-class uvicorn.workers.UvicornWorker --keep-alive 60 --workers 4 server:app
