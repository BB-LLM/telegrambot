FROM ncr.nie.netease.com/mirror_docker.io/library/python:3.10.6

# CMAKE
WORKDIR /tmp
RUN wget https://github.com/Kitware/CMake/releases/download/v3.24.2/cmake-3.24.2.tar.gz
RUN tar -zxvf cmake-3.24.2.tar.gz
RUN cd cmake-3.24.2
WORKDIR /tmp/cmake-3.24.2
RUN ./bootstrap
RUN make
RUN make install


WORKDIR /workspace
COPY ./requirements.txt /workspace


RUN pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/
RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/


# Expose ports
# http port
EXPOSE 8080

COPY . /workspace

CMD ["gunicorn",  \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8080", \
     "--max-requests", "50000",  \
     "--max-requests-jitter", "5000", \
     "--timeout", "120", \
     "server.server:app"]
