.PHONY: run-server run-client help

# display help information
help:
	@echo "Available targets:"
	@echo "  help - display this help message"
	@echo "  run-server - start the server"
	@echo "  run-client - start the client"

# start the server
run-server:
	cd server && cargo run

# start the client
run-client:
	cd client && uv run src/main.py
