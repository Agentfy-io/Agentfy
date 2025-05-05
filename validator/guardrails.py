from pydantic import BaseModel
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
)
from openai.types.responses import ResponseTextDeltaEvent
import asyncio

class MathHomeworkOutput(BaseModel):
    is_math_homework: bool
    reasoning: str

math_guardrail_agent = Agent( 
    name="Guardrail check",
    instructions="Check if the user is asking you to do their math homework.",
    output_type=MathHomeworkOutput,
)


@input_guardrail
async def math_guardrail( 
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(math_guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output, 
        tripwire_triggered=result.final_output.is_math_homework,
    )

class PoliticsOutput(BaseModel):
    is_politics: bool
    reasoning: str

politics_guardrail_agent = Agent( 
    name="Guardrail check",
    instructions="""Check carefully if the user is asking you about politics.""",
    output_type=PoliticsOutput,
)


@input_guardrail
async def politics_guardrail( 
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(politics_guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output, 
        tripwire_triggered=result.final_output.is_politics,
    )


agent = Agent(  
    name="Customer support agent",
    instructions="You are a customer support agent. You help customers with their questions.",
    input_guardrails=[math_guardrail, politics_guardrail],
)

async def main():
    # This should trip the guardrail
    try:
        result = Runner.run_streamed(agent, "x^2 + 2x + 1 = 0, what's x?")
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)

        print("\nGuardrail didn't trip - this is unexpected")

    except InputGuardrailTripwireTriggered:
        print("\nguardrail tripped - as expected!")

if __name__ == "__main__":
    asyncio.run(main())