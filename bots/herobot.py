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
# Set a sane HTTP request timeout for geopy
geopy.geocoders.options.default_timeout = 8


from . import helpers


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

        #TODO: get the file from storage

        self._confirmed = pd.read_csv(
            "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Confirmed.csv",
            index_col=["Country/Region", "Province/State"]).iloc[:, -1]
        self._deaths = pd.read_csv(
            "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Deaths.csv",
            index_col=["Country/Region", "Province/State"]).iloc[:, -1]
        self._recovered = pd.read_csv(
            "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Recovered.csv",
            index_col=["Country/Region", "Province/State"]).iloc[:, -1]
        self._curr_date = pd.to_datetime(self._confirmed.name)

        self._AzMap = AzureMaps(subscription_key=config.AZURE_MAPS_KEY)

    def _filter_by_cntry(self, cntry):
        out = None
        try:
            out = (self._confirmed[cntry].sum(), self._deaths[cntry].sum(), self._recovered[cntry].sum())
        except Exception as e:
            out = None
            print(f"[WARNING] Encountered country matching problem, Country =  {e}")
        return out

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
                    confirmed, deaths, recovered = out
                    dt  = helpers.to_human_readable(self._curr_date)
                    outputs.append(f"As of {dt}, for Country: {cntry} there were {confirmed} confirmed cases, {deaths} deaths and {recovered} recoveries")
                else:
                    #TODO: propose the card with options
                    outputs.append(f"Country : {cntry}, Code: {cntry_code} not found in the dataset, please try different spelling")
            await turn_context.send_activity(
                 "\n".join(outputs)
             )



    async def _none(self, turn_context: TurnContext, luis_result: LuisResult):
        await self._get_status(turn_context, luis_result)
        return
