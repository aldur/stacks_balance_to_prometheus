#!/usr/bin/env python

import logging
import os
import time

import prometheus_client
import requests
import urllib3.exceptions

DEFAULT_HTTP_PORT = 8081
DEFAULT_SCRAPING_INTERVAL = 120  # seconds

STX_API_ENDPOINT = "https://api.hiro.so/extended/v1/address/{}/stx"
STX_ASSET = "uSTX"


def configure_logging():
    is_debug = bool(os.getenv("DEBUG", 0))
    log_level = logging.DEBUG if is_debug else logging.INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    logger = logging.getLogger("simple_stock_tracker")
    logger.setLevel(log_level)
    logger.addHandler(console_handler)

    return logger


logger = configure_logging()


balance = prometheus_client.Gauge("balance", "Balance", ["address", "asset"])
exceptions = prometheus_client.Counter("exceptions", "Exceptions")


session = requests.Session()
session.headers["User-agent"] = "stacks_balance_to_prometheus/1.0"


def expose_metrics(addresses) -> None:
    for address in addresses:
        try:
            r = requests.get(STX_API_ENDPOINT.format(address))
            r.raise_for_status()

            r_balance = int(r.json()["balance"])

            labels = {
                "asset": STX_ASSET,
                "address": address,
            }

            balance.labels(**labels).set(r_balance)
            logger.debug("%s: %s %s", address, r_balance, STX_ASSET)
        except (
            urllib3.exceptions.NewConnectionError,
            requests.exceptions.ConnectionError,
        ) as connection_exception:
            logger.error(
                "Error while connecting to Hiro API for address %s: %s",
                address,
                connection_exception,
            )
            exceptions.inc()
        except RuntimeError as runtime_exception:
            logger.error(
                "Error while retrieving data from Hiro API for address %s: %s",
                address,
                runtime_exception,
            )
            exceptions.inc()
        except Exception as exception:
            logger.error(
                "Error for address %s: %s",
                address,
                exception,
            )
            exceptions.inc()


if __name__ == "__main__":
    # Start up the server to expose the metrics.
    port = int(os.getenv("METRICS_PORT", default=DEFAULT_HTTP_PORT))
    prometheus_client.start_http_server(port)
    logger.info("Listening on port: %d.", port)

    addresses = os.getenv("ADDRESSES")
    if not addresses:
        logger.error("Please specify at least one address to track in ADDRESSES.")
        import sys

        sys.exit(1)

    addresses = addresses.split(",")

    while True:
        expose_metrics(addresses)

        time.sleep(
            int(os.getenv("SCRAPING_INTERVAL", default=DEFAULT_SCRAPING_INTERVAL))
        )  # seconds
