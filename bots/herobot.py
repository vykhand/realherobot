import os
from azure.cognitiveservices.language.luis.runtime.models import LuisResult

from botbuilder.ai.luis import LuisApplication, LuisRecognizer, LuisPredictionOptions
from botbuilder.ai.qna import QnAMaker, QnAMakerEndpoint
from botbuilder.core import ActivityHandler, TurnContext, RecognizerResult, CardFactory, MessageFactory
from botbuilder.schema import ChannelAccount, HeroCard, ActionTypes, CardAction, CardImage, Attachment

from config import DefaultConfig
import pandas as pd
from geopy.geocoders import AzureMaps
import geopy
import requests
import logging

from . import helpers
from . import constants as C


# Set a sane HTTP request timeout for geopy
geopy.geocoders.options.default_timeout = 8
log = logging.getLogger(C.LOGGER_NAME)



class HeroBot(ActivityHandler):
    def __init__(self, config: DefaultConfig):

        luis_application = LuisApplication(
            config.LUIS_APP_ID,
            config.LUIS_API_KEY,
            "https://" + config.LUIS_API_HOST_NAME,
        )
        luis_options = LuisPredictionOptions(
            include_all_intents=True, include_instance_data=True
        )
        self.recognizer = LuisRecognizer(luis_application, luis_options, True)
        self._last_file_name = None
        self._last_date = None
        self._last_file_update = None

        self.fetch_dataset()

        self._AzMap = AzureMaps(subscription_key=config.AZURE_MAPS_KEY)


    def fetch_dataset(self, force = False):

        last_file_name, last_date = self._get_last_file_name()
        last_file_update = self._get_last_update(last_file_name)

        if (self._last_file_name is None) or (last_date > self._last_date) \
                or (last_file_update > self._last_file_update) or force:
            self._data = pd.read_csv(C.FILE_URL_BASE + last_file_name)
            self._last_file_name = last_file_name
            self._last_date = last_date
            self._last_file_update = last_file_update

            log.info(f"Updated dataset, new last_date = {self._last_date}, last committed = {self._last_file_update}")
        else:
            log.debug(f"Based on timestamp check, last_date = {last_date}, prev last_update = {self._last_date}, " +
                f"timestamps: old {self._last_file_update}, new: {last_file_update} , no refresh required")

    def _get_last_file_name(self):
        ret = (None, None)
        try:
            req = requests.get(C.FILE_DIR_URL)
            dts = pd.DataFrame(pd.Series([n["name"] for n in req.json()], name="name"))
            dts["dt"] = pd.to_datetime(dts["name"].str.rstrip(".csv"), errors = "coerce")
            last_file = dts.sort_values("dt", ascending=False)["name"].tolist()[0]
            last_date = dts.sort_values("dt", ascending=False)["dt"].tolist()[0]
            ret = (last_file, last_date)
        except Exception as e:
            log.error(f"Error getting last filename and date, message: {e}")
        return ret

    def _get_last_update(self, filename):
        ret = None
        if filename is not None:
            try:
                req = requests.get(C.LAST_UPDATE_URL_TEMPLATE.format(filename))

                last_update = req.json()[0]["commit"]["committer"]["date"]
                ret =  pd.to_datetime(last_update)
            except Exception as e:
                log.error(f"Getting the last update timestamp failed with message: {e}, timestamp is set to: {self._last_file_update}")
        return ret


    def _filter_by_cntry(self, cntry):
        df = (self._data
              .query("Country_Region == @cntry")
              .groupby("Country_Region")[['Confirmed', 'Deaths', 'Recovered', 'Active']]
              .sum())
        if df.shape[0] == 0:
            log.warning(f"Encountered country matching problem, Country = {cntry}")
        else:
            confirmed, dead, recovered, active = df.values[0]
            return (confirmed, dead, recovered, active )

    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                card = HeroCard(
                    title="Welcome to the COVID-19 Information bot",
                    images=[
                        CardImage(
                            url="https://i.imgur.com/zm095AG.png"
                        )
                    ],
                    buttons=[
                        CardAction(
                            type=ActionTypes.open_url,
                            title="Repository link",
                            value="https://github.com/vykhand/realherobot",
                        )
                    ],
                )
                repl = MessageFactory.list([])
                repl.attachments.append(CardFactory.hero_card(card))
                await turn_context.send_activity(repl)

    async def on_message_activity(self, turn_context: TurnContext):
        # First, we use the dispatch model to determine which cognitive service (LUIS or QnA) to use.
        recognizer_result = await self.recognizer.recognize(turn_context)

        # Top intent tell us which cognitive service to use.
        intent = LuisRecognizer.top_intent(recognizer_result)

        # Next, we call the dispatcher with the top intent.
        await self._dispatch_to_top_intent(turn_context, intent, recognizer_result)

    async def _dispatch_to_top_intent(
        self, turn_context: TurnContext, intent, recognizer_result: RecognizerResult
    ):
        if intent == "get-status":
            await self._get_status(
                turn_context, recognizer_result.properties["luisResult"]
            )
        elif intent == "None":
            await self._none(
                turn_context, recognizer_result.properties["luisResult"]
            )
        else:
            await turn_context.send_activity(f"Dispatch unrecognized intent: {intent}.")
    async def _get_status(self, turn_context: TurnContext, luis_result: LuisResult):
        # await turn_context.send_activity(
        #     f"Matched intent {luis_result.top_scoring_intent}."
        # )
        #
        # intents_list = "\n\n".join(
        #     [intent_obj.intent for intent_obj in luis_result.intents]
        # )
        # await turn_context.send_activity(
        #     f"Other intents detected: {intents_list}."
        # )
        #

        outputs =  []
        if luis_result.entities:
            for ent in luis_result.entities:
                loc = self._AzMap.geocode(ent.entity, language='en-US')
                cntry = loc.raw["address"]["country"]

                out = self._filter_by_cntry(cntry)
                if out is None:
                    cntry_code = loc.raw["address"]["countryCode"]
                    out = self._filter_by_cntry( cntry_code)
                if out is not None:
                    confirmed, deaths, recovered, active = out
                    dt  = helpers.to_human_readable(self._last_date)
                    outputs.append(f"As of {dt}, for Country: {cntry} there were {confirmed} confirmed cases, " +
                                   f"{deaths} deaths, {recovered} recoveries and {active} active cases")
                else:
                    #TODO: propose the card with options
                    outputs.append(f"Country : {cntry}, Code: {cntry_code} not found in the dataset, please try different spelling")
            await turn_context.send_activity(
                 "\n".join(outputs)
             )



    async def _none(self, turn_context: TurnContext, luis_result: LuisResult):
        await self._get_status(turn_context, luis_result)
        return
