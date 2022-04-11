FROM openeuler-21.09
LABEL maintainer="ethanzhang55@outlook.com"

ENV websockify_listen 21580
WORKDIR /data/vnc_tokens

RUN dnf install -y python3-websockify

CMD websockify --token-plugin TokenFile --token-source . $websockify_listen
