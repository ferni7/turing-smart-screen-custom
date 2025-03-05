FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN python3 -m pip install -r requirements.txt --no-cache-dir

#RUN chmod -R +r *

RUN apt-get update && apt-get install nano -y

#RUN usermod -a -G dialout nobody

#USER nobody

ENTRYPOINT ["python3", "app.py"]