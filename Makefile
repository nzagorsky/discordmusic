
build:
	docker build . -t discordmusic

build_no_cache:
	docker build . -t discordmusic --no-cache

run: build
	docker rm -f discordmusic; docker run -it --restart=always -e DISCORD_BOT_TOKEN=$$DISCORD_BOT_TOKEN --name=discordmusic discordmusic

