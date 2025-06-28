FROM python:3.13.5-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN mkdir /app && chown appuser:appuser /app

WORKDIR /app
USER appuser

# pip install <package> --kaikki-paskaks
RUN pip install --user pdm --break-system-packages
RUN pdm install --prod

EXPOSE 8000
COPY . .

CMD ["pdm", "run", "start"]