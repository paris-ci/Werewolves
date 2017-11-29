# Werewolves
A werewolves game based on a RESTful API. Uses python3 & hug for the server, and no "exotic" dependencies for the client.

A sample python client is provided, but because of the API server side, you can and are encouraged to make a client in another language or using a different philosophy, as it will still be operating well with others.

## Server-side

You'll find more documentation about the server in the docstrings and in the `server/README.txt`

## Client-side

You'll find more documentation about the client in the docstrings and in the `client/README.txt`

## Official server

I currently host a server, located at `werewolves.api-d.com:8000`

## Installation and developpement

### Installation on a local machine

Clone the repository using git : `git clone https://github.com/paris-ci/Werewolves.git`

Change to the project directory : `cd Werewolves`

(Optional, but needed by some IDE) Create a simlink to make common avalable in the Server Directory : `cd server/ && ln -s ./common ../common`

Then, mark the `client/` and `server/` directory as source directories in your IDE if you use one.

Install hug `pip3 install hug`

Start the server using hug : `cd server/; hug -f ./launch.py`

### Installation on a server

Follow instructions for installing in a local machine, then install gunicorn for python3(.6) using your server package manager.

You can launch the server using `gunicorn3 launch:__hug_wsgi__ --bind 0.0.0.0:8000`


