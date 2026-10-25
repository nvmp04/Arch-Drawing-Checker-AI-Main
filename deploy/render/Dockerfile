# MAIN ở chế độ chấm cho đối tác trên Render (D-24). Dựng từ thư mục giải nén của review-bundle.tar.gz.
# Biến môi trường đặt trên Render: MAIN_REVIEW_PASSWORD, MAIN_REVIEWS_DATABASE_URL (Neon).
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY samples ./samples
COPY data/inspect ./data/inspect

ENV MAIN_REVIEW_ONLY=true \
    MAIN_INSPECT_ENABLED=true \
    MAIN_INSPECT_DIR=data/inspect \
    MAIN_AI_PROVIDER=off

# Render đặt cổng qua biến PORT.
CMD ["sh", "-c", "uvicorn drawing_checker.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
