


### Requirements
Everything for minecraft of coarse. we're using [mc server container](https://github.com/itzg/docker-minecraft-server) and [docker-compose](https://docs.docker.com/compose/install/)
for the 





### test the rcon module
```python
from mcrcon import MCRcon
mcr = MCRcon("server.camp", "rootroot")
mcr.connect()
print(mcr.command("say hi"))
print(mcr.command("list uuids"))
```
