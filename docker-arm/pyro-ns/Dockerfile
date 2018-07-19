FROM python:3.6.4-jessie

RUN pip install Pyro4 dill

ENV PYRO_SERIALIZERS_ACCEPTED=serpent,json,marshal,pickle,dill
ENV PYTHONUNBUFFERED=0

ENTRYPOINT ["pyro4-ns"]

EXPOSE 9090