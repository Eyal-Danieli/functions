import os
import mlrun
import pytest

# OpenAI tokens:
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
# os.environ["OPENAI_API_BASE"] = OPENAI_API_BASE


@pytest.mark.skipif("OPENAI_API_KEY" not in os.environ, reason="no token")
def test_json_data_generator():
    # Create mlrun project
    project = mlrun.get_or_create_project("json-data-generator-test")

    # Import the function from the yaml file, once it's in the hub we can import from there
    data_generation = project.set_function(func="json_data_generator.py", name="json_data_generator")

    # Run the imported function with desired file/s and params
    data_generation_run = data_generation.run(
        handler="generate_data",
        params={
            "amount": 3,
            "model_name": "gpt-4",
            "language": "en",
            "fields": [
                "first name",
                "last_name",
                "phone_number: at least 9 digits long",
                "email",
                "client_id: at least 8 digits long, only numbers"
            ],
        },
        returns=[
            "clients: file",
        ],
        local=True,
    )
    assert data_generation_run.outputs["clients"]