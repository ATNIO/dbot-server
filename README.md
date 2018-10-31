# ATN DBot Server

DBot Server provide a set of tools for API providers in order to easily deploy their API to ATN ecosystem. API provider can decide to monetize their API with a "pay-per-use" design or make it free. They can also decide to deploy their own token which will be needed in order to use their services. It's a complete open-source project build on a fully decentralized infrastructure.

## Introduction

In order to join ATN ecosystem and deploy your API, you will have to follow this work flow:

1. Deploy this DBot server technology on your Linux/Unix server. The DBot server is a framework, It provides the core functionalities needed for your services. ( DBot server support the deployment of many DBot services (API))

One the DBot server is up and running you need to start a DBot service.

2. Start a DBot service:
 * Prepare the required data including, DBot metadata (name, description, keywords, domain name), API specification file (swagger 2.0) and Middleware(optional).
 * Deploy a DBot contract on chain and start a DBot service on your Dbot server. This can be done by just one command we provide.

3. After your API is up an running, you can either publish it on our official ATN API market or decide to deploy your own API market and publish it in your market.


## Quick Start

For example, we want to share an API which use AI to generate chinese-poetry based on one sentence.

```bash
curl -X POST "http://airpc.atnio.net:8003/poetry/reg" -F "theme=中秋月更圆"
```
Let's start step by step:

#### 1. Prerequisite

1. A Linux/Unix Server which can access from internet and an ATN chain node with RPC enable. You can start your own ATN node or use our offical one: `https://rpc-test.atnio.net`

2. An ATN account which has enough ATN . You can get ATN from the [faucet](https://faucet-test.atnio.net/) service.

#### 2. Start DBot server

DBot server can start with docker. We just need provide keystore and password file of your account on ATN chain, and two folders(`logs` and `data`) is required for storage.

```bash
# run container
docker run -p 4548:80 \
    --mount type=bind,source=<Logs Folder>,target=/dbot-server/logs \
    --mount type=bind,source=<Data Folder>,target=/dbot-server/data \
    --mount type=bind,source=<Keystore File>,target=/dbot-server/keystore/keyfile \
    --mount type=bind,source=<Password File>,target=/dbot-server/password/passwd \
    -e "WEB3_PROVIDER=<Web3 Provider>" \
    atnio/dbot-server

# check DBot server is ok
curl http://0.0.0.0:4548/api/v1

# make sure your DBot server is up and running
curl http://<IP or Domain of DBot Server>/api/v1
```

#### 3. Develop a simple DBot

A DBot profile and an API specification file(only [swagger2.0](https://swagger.io/specification/v2/) is supported now) are required to deploy an API DBot. We also support a middleware(python) for a DBot, it is optional. This three files should be in the same folder.

You can find example of these files in the dbot-demos folder

Just use the `dbot-service` command  provided by the python package`dbot-manager`, to manage DBot on your DBot server.

```bash
# install dbot-manager, it provides the dbot-service command
sudo pip install dbot-manager
# config dbot-service command first, the account used here should be the same with the one which used to start DBot server
dbot-service config --dbot-server http://<IP or Domain of DBot Server> --pk-file <keystore file> --pw-file <password file> --http-provider https://rpc-test.atnio.net
# Add the DBot service, you will receive the contract address of the new API DBot as an output.
git clone https://github.com/ATNIO/dbot-server.git
cd dbot-server
dbot-service add --profile dbot-demos/ai_poetry_en/profile.json
# Check the DBot service, if the status is ok, the DBot service is work, congratulation.
dbot-service status --address <DBot address>
```

#### Test the DBot

We use payment channel technology which give use a "pay-per-call" design (every time you query the API you need to pay). So API consumers can use the [ATN client](https://github.com/ATNIO/atn-node-js/tree/alpha#atn-node-js) to call the API in DBot. You also can use the ATN client to test your own DBot.

We also provide [Python ATN client](https://github.com/ATNIO/pyatn-client) which just for develop now.
```bash
# install Python ATN client
pip install pyatn-client
```

Here is an example about how to use the python ATN Client. ATN client is used by API consumers, so we use other account here.

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pyatn_client import Atn

requests_data = {
    # calling endpoint
    "endpoint": {
        "uri": "/reg",
        "method": "POST"
    },
    # kwargs for `requests` to send HTTP request, since we use `requests` underlying layer.
    "kwargs": {
        "data": {
            "theme": "中秋月更圆"
        }
    }
}

DBOT_ADDRESS = '0xfd4F504F373f0af5Ff36D9fbe1050E6300699230' # address of the DBot you want to test, use 'AI poetry' as example
atn = Atn(http_provider=<HTTP_PROVIDER>, pk_file=<Keystore File>, pw_file=<Password File>)

# call dbot api, it will auto create channel with the DBot if no exist channel.
response = atn.call_dbot_api(dbot_address=DBOT_ADDRESS,
                             uri=requests_data['endpoint']['uri'],
                             method=requests_data['endpoint']['method'],
                             **requests_data['kwargs']
                             )
```

#### Test the DBot on AI Market

Putting your DBot on the AI Market is a good way to promote your API, since everyone can try your API on website.

TODO: How to Deploy private AI Market


## Develop Guide

###  1. Start DBot Server

#### start from source

```bash
git clone https://github.com/ATNIO/dbot-server.git
cd dbot-server
# setup python virtual env, we depend on python3.6+, make sure you have installed it.
python -m venv env
# activate venv
source env/bin/activate
# install dependencies
pip install -r dbot-server/requirements.txt
# start DBot server, default port is 4548
python dbot-server/manager.py run_server --pk-file <Keystore File> --pw-file <Password File> --http-provider <Web3 Provider> [--port <PORT>]
```

The default server port is 4548, use follwing command to check if the DBot server is ok
```bash
curl http://0.0.0.0:4548/api/v1
```

#### start with docker

In production envrionment, it will be better to run DBot server with docker.
The `atnio/dbot-server` docker image contain uWSGI and Nginx for our DBot server application(develop by flask).

When start Dbot server with docker, we need specify folders to mount for `data` and `logs`. Keystore file and Password file is also required.

```bash
# prepare foler for volume
mkdir -p data logs

# run container
docker run -p 4548:80 \
    --mount type=bind,source=<Logs Folder>,target=/dbot-server/logs \
    --mount type=bind,source=<Data Folder>,target=/dbot-server/data \
    --mount type=bind,source=<Keystore File>,target=/dbot-server/keystore/keyfile \
    --mount type=bind,source=<Password File>,target=/dbot-server/password/passwd \
    -e "WEB3_PROVIDER=<Web3 Provider>" \
    atnio/dbot-server

# check dbot server is ok
curl http://0.0.0.0:4548/api/v1
```


###  2. Develop a DBot service

#### Prepare Data for a DBot Service

A profile file and specification file(only [swagger2.0](https://swagger.io/specification/v2/) is supported now) is required to create a new dbot. And we support add a middleware(python) for a DBot, it is optional.
This three files should be in the same folder.

##### Specification

Swagger (now known as the OpenAPI Initiative, under the structure of the Linux Foundation) is a framework for describing your API by using a common language that is easy read and understand by developers and testers, even they have weak source code knowledge.

The current version of the OpenAPI specification is [OpenAPI Specification 3.0.1](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md), but we support [OpenAPI Specification 2.0](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md) now.
The OpenAPI Specification 2.0 was renamed from [Swagger 2.0 specification](https://swagger.io/specification/v2/). You can find the difference between Swagger and OpenAPI from [here](https://swagger.io/blog/api-strategy/difference-between-swagger-and-openapi/).

Following tools and documents can help you know how to define the swagger specification file for your API
* [Swagger Editor](https://editor.swagger.io)
* [Swagger 2.0 Specification](https://swagger.io/specification/v2/)
* [Examples](https://github.com/OAI/OpenAPI-Specification/tree/master/examples/v2.0/json)

TODO: add detail doc and examples

##### Middleware

When share your APIs through ATN blockchain, the API accessment and authorization can be handed over to the blockchain.
Token or API key will be no longer neccesary for you API consumers. It will be more easier to use the API.
If the API can only access by API key now, we support you add a middleware which add the API key in the request for API consumers so that they can use the API easier.

Following documents can help you know how to define a middleware.
* [Application Dispatching](http://flask.pocoo.org/docs/1.0/patterns/appdispatch/#app-dispatch)
* [How to create a middleware in Flask](https://medium.com/@devsudhi/how-to-create-a-middleware-in-flask-4e757041a6aa)

Here is an example middleware for Dbot of xiaoi(http://cloud.xiaoi.com/) smart chart API.
It add `X-Auth` in request header which generated from APP key and APP secret.

TODO: add detail doc and examples

##### Profile

Every Dbot need a profile to define the info and configration. The `name`, `domain` and `price` of every endpoints will record on blockchain.
So that all the changement can be traced.

Following info should be defined in the profile:
1. The information of a DBot, include name, domain, description, logo, category, tags.
2. The file name and type of the specification file
3. Endpoints list of the API. The `path` of a endpoint corresponds to the `path` of API in specification(swagger) file. And every endpont has a price.
4. If there is a middleware, the module and class name is required in profile so that the middleware can be load.

The three file (specification file, middleware file and profile file) should be in the same folder.

TODO: add detail doc and examples


#### add/update/remove a DBot Service

It is easy to add a DBot service on the DBot server, if the profile and other data for the DBot service is ready.
We provide a simple command line script `dbot-service.py` for Dbot developer to add/update/remove a DBot service on the DBot server.

If you are running this `dbot-service.py` script at the same host with the DBot server, just run as following

```bash
# install dbot-manager
sudo pip install dbot-manager
# config dbot-service command first
dbot-service config --dbot-server <DBot Server URL> --pk-file <keystore file> --pw-file <password file> --http-provider https://rpc-test.atnio.net
# add DBot service
cd <dbot-server source root folder>
dbot-service add --profile dbot-demos/ai_poetry_en/profile.json [--publish]
# you will get the address of the DBot from last command's output, check if the status of the DBot
# If the status is ok, every one can use our ATN client to call the API through blockchain.
dbot-service status --address <DBot address>
# show all DBot service running on the DBot server
dbot-service list
# update the dbot service if something changed
dbot-service update --profile <DBot Profile full path Name> --address <DBot address>
# remove the dbot service (you can add it back use add command with --address option)
dbot-service remove --address <DBot address>
```

TODO: detail command help
