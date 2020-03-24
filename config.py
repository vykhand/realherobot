#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import logging

# Load secrets from .env file
from dotenv import load_dotenv
# Don't override existing system env vars,
# because we could be running on Azure App Service
# and our env vars are sourced from Application Settings
load_dotenv(verbose=True, override=False)

class DefaultConfig:
    """ Bot Configuration """
    LOCAL_MODE = os.path.exists(".env")
    ROOT_LOGGER = "realherobot"
    PORT = os.environ.get("PORT")

    LUIS_APP_ID = os.environ.get("LUIS_APP_ID")
    LUIS_API_KEY = os.environ.get("LUIS_API_KEY")
    
    LUIS_API_HOST_NAME = os.environ.get("LUIS_API_HOST_NAME")
    AZURE_MAPS_KEY = os.environ.get("AZURE_MAPS_KEY")

    # Azure Bot Service only -
    APP_ID = os.environ.get("MICROSOFT_APP_ID", "")
    APP_PASSWORD = os.environ.get("MICROSOFT_APP_SECRET", "")

    INSTRUMENTATION_KEY = os.environ.get("INSTRUMENTATION_KEY")