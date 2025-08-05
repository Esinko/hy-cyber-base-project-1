FROM python:3.13.5-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN mkdir -p /home/appuser
RUN chown -R appuser:appuser /home/appuser

RUN mkdir /app
WORKDIR /app
RUN chown -R appuser:appuser /app

# pip install <package> --kaikki-paskaks
COPY . .
USER appuser
RUN pip install --user pdm --break-system-packages
RUN cd /app && /home/appuser/.local/bin/pdm install --prod

EXPOSE 5000
CMD ["/home/appuser/.local/bin/pdm", "run", "start-in-all-interfaces"]
