import os
from azure.cognitiveservices.language.luis.runtime.models import LuisResult

from botbuilder.ai.luis import LuisApplication, LuisRecognizer, LuisPredictionOptions
from botbuilder.ai.qna import QnAMaker, QnAMakerEndpoint
from botbuilder.core import ActivityHandler, TurnContext, RecognizerResult
from botbuilder.schema import ChannelAccount

from config import DefaultConfig
import pandas as pd
from geopy.geocoders import AzureMaps
import geopy
# Set a sane HTTP request timeout for geopy
geopy.geocoders.options.default_timeout = 8

from . import helpers
def filter_by_cntry(df, cntry):
    out = (df.loc[df["Country/Region"] == cntry]
           .sort_values("Date", ascending=False)
           .head(1))
    if out.shape[0] == 0: out = None

    return  out
class HeroBot(ActivityHandler):
    def __init__(self, config: DefaultConfig):
        # downloading the latest dataset

        os.system("python $PYTHONPATH/bin/kaggle datasets download imdevskp/corona-virus-report -p ./data")

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

        self._covid_data = pd.read_csv("./data/corona-virus-report.zip")
        self._covid_data["Date"] = pd.to_datetime(self._covid_data["Date"])

        self._AzMap = AzureMaps(subscription_key=config.AZURE_MAPS_KEY)



    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    f"Welcome to Dispatch bot {member.name}. Type a greeting or a "
                    f"question about the weather to get started."
                )

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
        df  = self._covid_data

        outputs =  []
        if luis_result.entities:
            for ent in luis_result.entities:
                loc = self._AzMap.geocode(ent.entity)
                cntry = loc.raw["address"]["country"]
                out = filter_by_cntry(df, cntry)
                if out is None:
                    cntry_code = loc.raw["address"]["countryCode"]
                    out = filter_by_cntry(df, cntry_code)
                if out is not None:
                    confirmed = out["Confirmed"].tolist()[0]
                    dt  = helpers.to_human_readable(out["Date"].tolist()[0])
                    deaths = out["Deaths"].tolist()[0]
                    recovered = out["Recovered"].tolist()[0]

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
