# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import logging

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bots import HeroBot
from config import DefaultConfig
from opencensus.ext.azure.log_exporter import AzureLogHandler

CONFIG = DefaultConfig()

# Application Insights bootstrap via OpenCensus
logger = logging.getLogger(CONFIG.ROOT_LOGGER + ".app")

# setting up the logging
root_log = logging.getLogger(CONFIG.ROOT_LOGGER)
formatter = logging.Formatter('[%(asctime)s][%(name)s] {%(module)s.%(funcName)s:%(lineno)d %(levelname)s} - %(message)s')
console_handl = logging.StreamHandler(stream=sys.stdout)
console_handl.setFormatter(formatter)
root_log.addHandler(console_handl)
root_log.setLevel(logging.DEBUG)

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)


# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity, which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)


ADAPTER.on_turn_error = on_error

# Create the Bot
BOT = HeroBot(CONFIG)

# Listen on / for GET requests
# Only used by App Service AlwaysOn pings for now
async def handle_get(req: Request) -> Response:

    return Response(status=200, text="Hello.")    

# Listen on /api/refresh-dataset
async def refresh_dataset(req: Request) -> Response:
    # Handle dataset update
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=415, text="Invalid Content-Type, expecting application/json.")

    BOT.fetch_dataset(force=True)

    return Response(status=200, text="Alright, refresh_dataset handler works.")

# Listen for incoming requests on /api/messages
async def messages(req: Request) -> Response:
    # Main bot message handler.
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=415, text="Invalid Content-Type, expecting application/json.")

    activity = Activity().deserialize(body)
    if activity.text:
        logger.debug(f'activity.text = {activity.text}')

    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=201)


APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)
APP.router.add_post("/api/refresh-dataset", refresh_dataset)
APP.router.add_get("/", handle_get)

if __name__ == "__main__":

    if not CONFIG.LOCAL_MODE:
        #Azure mode
        root_log.setLevel(logging.INFO)
        logger.info("Running in Azure Mode")
        formatter = logging.Formatter('{%(name)s} - %(message)s')
        az_handl = AzureLogHandler(connection_string=f"InstrumentationKey={CONFIG.INSTRUMENTATION_KEY}")
        az_handl.setFormatter(formatter)
        root_log.addHandler(az_handl)
    else:
        root_log.setLevel(logging.DEBUG)
        logger.info("Running in LOCAL Mode")

    #setting up the periodic refresh
    scheduler = BackgroundScheduler()
    scheduler.add_job(BOT.fetch_dataset, 'interval', minutes=10)
    scheduler.start()

    try:
        web.run_app(APP, host="0.0.0.0", port=CONFIG.PORT)
    except Exception as error:
        raise error
