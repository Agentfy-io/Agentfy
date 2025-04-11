from common.models.messages import UserInput
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.perception.module import PerceptionModule


user_input = "now find people who are interested in supporting donald trump on X"

user_input_list = ["now find people who are interested in supporting donald trump on X","now find people who are interested in supporting donald trump on X"]

for user_input in user_input_list:
    # 1. Initialize the modules
    memory_module = MemoryModule()
    reasoning_module = ReasoningModule()
    perception_module = PerceptionModule()

    # 2. Create a user input object
    user_input = UserInput(
        text=user_input,
        files=[],
        metadata={
            "user_id": "12345",
            "session_id": "67890",
            "timestamp": None,  # Will be set by the model
            "source": "api"
        }
    )

    # 3. Process the user input
    valid_result = await perception_module.validate_input(user_input)

    if not valid_result.is_valid:
        print(f"Validation failed: {valid_result.error_message}")

    # 4. If valid, proceed to memory and reasoning
    if valid_result.is_valid:
        # 5. get user chat history
        chat_history = await memory_module.get_user_chat_history(user_input.metadata["user_id"])

        # 6. get agents registry
        agents_registry = get_agent_registry()

        # 7. get workflow definition
        workflow_definition = await reasoning_module.build_workflow(user_input, agents_registry)

        print(f"Workflow definition: {workflow_definition}")