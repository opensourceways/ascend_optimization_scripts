FROM openeuler/openeuler:22.03-lts

ENV LANG=en_US.UTF-8

RUN yum install git python3-devel python3-pip openssl openssl-devel -y

WORKDIR /work/app

COPY . /work/app

RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN cp /usr/bin/python3 /usr/bin/python

WORKDIR /work/app/scripts

ENTRYPOINT ["python3", "/work/app/scripts/owners_collections.py"]
