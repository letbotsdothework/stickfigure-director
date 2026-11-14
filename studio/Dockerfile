FROM python:3.13-slim
WORKDIR /app
COPY app.py cleanup.py ./
COPY static/ ./static/
RUN pip install --no-cache-dir flask
ENV PROJECTS_ROOT=/data \
    PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "app.py"]
