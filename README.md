Simple web service to provide circulating supply for BOB token
====

This web service is requests totalSupply() through configured RPCs and returns the sum of requested values as a response on GET to `/`.

## Build a docker image

The docker image is built autimatically by GitHub actions and available by

```
docker pull ghcr.io/zkbob/bob-circulating-supply:latest
```

Another option is to build the docker image from scratch:

```
docker build -t ghcr.io/zkbob/bob-circulating-supply .
```

## Run the docker image

By using `.env.example` prepare `.env` file. Tune `UPDATE_INTERVAL` in the file to achieve desired behavior.

The docker container can be run in this case as

```
docker run -ti --rm -p 8000:8000 -e PORT=8000 ghcr.io/zkbob/bob-circulating-supply
```

Another option is to use docker composer to run the service:

```
docker compose up -d
docker compose logs -f
```

## Publishing the docker image on Heroku

Assuming that the app `my-heroku-app` is created on Heroku platform and Heroku CLI is installed on the local machine, the next steps can be executed to release the app:

```
heroku login
docker login --username=_ --password=$(heroku auth:token) registry.heroku.com
docker tag ghcr.io/zkbob/bob-circulating-supply:main registry.heroku.com/my-heroku-app/web:latest
docker push registry.heroku.com/my-heroku-app/web:latest
heroku container:release -a my-heroku-app web
```

More info about the docker container deployment to Heroku can be found [here](https://devcenter.heroku.com/articles/container-registry-and-runtime#logging-in-to-the-registry).

An extra step can be done if you have a [papertrail](https://papertrailapp.com/) account configured and would like to forward logs from the Heroku app to the remote logs storage:

```
heroku login
heroku drains:add syslog+tls://logsXXX.papertrailapp.com:YYYY -a my-heroku-app
```

Is it possible to see configured drains for the app by:

```
heroku drains --app my-heroku-app
```

For more info refer to [the Papertrail documentation](https://www.papertrail.com/help/heroku/).
