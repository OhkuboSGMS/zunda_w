import os

from langchain_openai import ChatOpenAI
from loguru import logger

_openai_api_key = "OPENAI_API_KEY"


def check_enviroment_variable():
    api_key = os.getenv(_openai_api_key)
    if not api_key:
        logger.warning("OPENAI_API_KEY not found. need key for OPENAI api use")


def gpt_4_correct():
    return ChatOpenAI(temperature=0, model_name="gpt-4")


def gpt_4_turbo_correct():
    return ChatOpenAI(temperature=0, model_name="gpt-4-turbo-preview")


def gpt_3_5_turbo_correct():
    return ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-0125")


def gpt_3_5_turbo_creative():
    return ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo-0125")


def gpt_4_turbo_creative():
    return ChatOpenAI(temperature=0.7, model_name="gpt-4-turbo-preview")


def gpt_4_creative():
    return ChatOpenAI(temperature=0.7, model_name="gpt-4")
