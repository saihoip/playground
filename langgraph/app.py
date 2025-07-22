import chainlit as cl
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage

from workflow import app


@cl.on_message
async def on_message(msg: cl.Message):
    config = {"configurable": {"thread_id": cl.context.session.id}}
    cb = cl.LangchainCallbackHandler()
    final_answer = cl.Message(content="")

    for msg, metadata in app.stream(
        {
            "task": msg.content,
            "messages": [HumanMessage(content=msg.content)],
        },
        stream_mode="messages",
        # config=RunnableConfig(callbacks=[cb], **config),
    ):
        if (
            msg.content
            and not isinstance(msg, HumanMessage)
            # and metadata["langgraph_node"] == "final"x
        ):
            await final_answer.stream_token(msg.content)

    await final_answer.send()
