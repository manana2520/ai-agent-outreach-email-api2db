#!/usr/bin/env python
import sys
import requests
import json
from datetime import datetime, timezone
from typing import Optional

from sales_personalized_email.crew import SalesPersonalizedEmailCrew, PersonalizedEmail
from crewai.crews.crew_output import CrewOutput

# This main file is intended to be a way for your to run your
# crew locally, so refrain from adding necessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def run(inputs_override: Optional[dict] = None):
    """
    Run the crew.
    If inputs_override is provided, it will be used instead of the hardcoded defaults.
    This allows the agentic runtime (or other callers) to pass in dynamic inputs.
    """
    if inputs_override:
        print(f"Using provided inputs: {inputs_override}")
        inputs = inputs_override
    else:
        print("No inputs_override provided, using default inputs for local run.")
        inputs = {
            "name": "Joe Eyles",
            "title": "Vice Principal",
            "company": "Park Lane International School",
            "industry": "Education",
            "linkedin_url": "https://www.linkedin.com/in/joe-eyles-93b66b265",
            "our_product": "AI and DAta Platform for Education",
            "email_address": "joe.eyles@example.com",
        }

    # Ensure email_address is present in inputs, defaulting if necessary for the store-emails API call
    # This is more of a safeguard if the default inputs somehow miss it or inputs_override doesn't include it
    # but the API call part of this script expects it.
    if "email_address" not in inputs:
        print("Warning: 'email_address' not found in inputs. Adding a placeholder for the store-emails API call.")
        inputs["email_address"] = "placeholder@example.com"

    crew_result = SalesPersonalizedEmailCrew().crew().kickoff(inputs=inputs)

    if crew_result:
        print(f"Crew execution result (type: {type(crew_result)}):\n{crew_result}")

        email_subject = "Default Subject"
        email_body = ""

        if isinstance(crew_result, PersonalizedEmail):
            print("Interpreting crew_result as PersonalizedEmail Pydantic model.")
            email_subject = crew_result.subject_line
            email_body = crew_result.email_body
        elif isinstance(crew_result, CrewOutput):
            print("Interpreting crew_result as CrewOutput object.")
            if hasattr(crew_result, 'subject_line') and hasattr(crew_result, 'email_body'):
                print("CrewOutput has subject_line and email_body attributes directly.")
                email_subject = crew_result.subject_line
                email_body = crew_result.email_body
            elif crew_result.tasks_output and isinstance(crew_result.tasks_output[-1].expected_output, PersonalizedEmail):
                print("Accessing PersonalizedEmail model from CrewOutput.tasks_output[-1].expected_output")
                exported_model = crew_result.tasks_output[-1].expected_output
                email_subject = exported_model.subject_line
                email_body = exported_model.email_body
            elif crew_result.tasks_output and isinstance(crew_result.tasks_output[-1].expected_output, dict):
                print("Accessing dict from CrewOutput.tasks_output[-1].expected_output")
                data_dict = crew_result.tasks_output[-1].expected_output
                email_subject = data_dict.get("subject_line", "Default Subject")
                email_body = data_dict.get("email_body", "")
            else:
                print("CrewOutput did not have direct attributes or expected tasks_output structure. Trying to_dict() or raw.")
                try_dict = None
                if hasattr(crew_result, "to_dict") and callable(crew_result.to_dict):
                    try_dict = crew_result.to_dict()
                elif hasattr(crew_result, "dict") and callable(crew_result.dict):
                    try_dict = crew_result.dict()
                elif hasattr(crew_result, "model_dump") and callable(crew_result.model_dump):
                    try_dict = crew_result.model_dump()
                elif hasattr(crew_result, "raw") and isinstance(crew_result.raw, str):
                    try:
                        try_dict = json.loads(crew_result.raw)
                    except json.JSONDecodeError:
                        print(f"Error: CrewOutput.raw string could not be parsed as JSON. String was: {crew_result.raw}")
                elif hasattr(crew_result, "json_output") and isinstance(crew_result.json_output, str):
                     try:
                        try_dict = json.loads(crew_result.json_output)
                     except json.JSONDecodeError:
                        print(f"Error: CrewOutput.json_output string could not be parsed as JSON. String was: {crew_result.json_output}")

                if isinstance(try_dict, dict):
                    email_subject = try_dict.get("subject_line", "Default Subject")
                    email_body = try_dict.get("email_body", "")
                else:
                    print(f"Could not extract subject/body from CrewOutput using common methods. Defaults will be used.")
        elif isinstance(crew_result, str):
            print("Interpreting crew_result as a string, attempting JSON parse.")
            try:
                data_dict = json.loads(crew_result)
                email_subject = data_dict.get("subject_line", "Default Subject")
                email_body = data_dict.get("email_body", "")
            except json.JSONDecodeError:
                print(f"Error: Crew result string could not be parsed as JSON.\nString was: {crew_result}")
        elif isinstance(crew_result, dict):
            print("Interpreting crew_result as a dictionary.")
            email_subject = crew_result.get("subject_line", "Default Subject")
            email_body = crew_result.get("email_body", "")
        else:
            print(f"Warning: Crew result is of an unexpected type ({type(crew_result)}). Attempting original getattr logic.")
            try:
                email_subject = getattr(crew_result, "subject_line", "Default Subject")
                email_body = getattr(crew_result, "email_body", "")
            except AttributeError:
                print(f"AttributeError when trying getattr on type {type(crew_result)}. Defaults will be used.")

        api_url = "https://mycomputer.maziak.eu/api/v1/import/store-emails"
        headers = {
            "CF-Access-Client-Id": "3894d1511738c7ab1d79f04866bce72e.access",
            "CF-Access-Client-Secret": "d9cc6e4001d53f87f7dcdf3777e330d2781a9b866ef55ff222241b829166c510",
            "Content-Type": "application/json",
            "X-API-Token": "33f311ec174ef02f7c7ae27cd4cc52e3",
        }
        payload = {
            "data": {
                "name": inputs.get("name"),
                "email": inputs.get("email_address"),
                "subject": email_subject,
                "message": email_body,
                "date": datetime.now(timezone.utc).isoformat(),
            }
        }

        print(f"Attempting to send the following payload to {api_url}:")
        print(json.dumps(payload, indent=2))

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Successfully sent email data to API. Status: {response.status_code}")
            print(f"Response from API: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending email data to API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"API Response content: {e.response.text}")
    else:
        print("Crew execution did not return a result. API call skipped.")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {"topic": "AI LLMs"}
    try:
        SalesPersonalizedEmailCrew().crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        SalesPersonalizedEmailCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {"topic": "AI LLMs"}
    try:
        SalesPersonalizedEmailCrew().crew().test(
            n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")
