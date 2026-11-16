FROM python:3.13-alpine
WORKDIR /app
COPY airalarm ./airalarm
ENV PYTHONUNBUFFERED=1 STATE_FILE=/data/state.json
CMD ["python", "-m", "airalarm.main"]
