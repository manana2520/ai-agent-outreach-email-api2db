#!/usr/bin/env python
import sys
import requests
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional
import os

from sales_personalized_email.crew import SalesPersonalizedEmailCrew, PersonalizedEmail, send_email_to_api
from crewai.crews.crew_output import CrewOutput

print("========== MAIN.PY MODULE LOADED ==========")
print(f"Python version: {sys.version}")
print(f"Current time: {datetime.now().isoformat()}")
print("===========================================")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sales_email_agent")

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
    print("=======================================")
    print("RUN FUNCTION CALLED")
    print(f"Received inputs_override: {inputs_override}")
    print("=======================================")
    
    logger.info("Starting run function")
    if inputs_override:
        logger.info(f"Using provided inputs: {inputs_override}")
        print(f"Using provided inputs: {inputs_override}")
        inputs = inputs_override
    else:
        logger.info("No inputs_override provided, using default inputs for local run.")
        print("No inputs_override provided, using default inputs for local run.")
        inputs = {
            "name": "Joe Eyles",
            "title": "Vice Principal",
            "company": "Park Lane International School",
            "industry": "Education",
            "linkedin_url": "https://www.linkedin.com/in/joe-eyles-93b66b265",
            "our_product": "AI and Data Platform for Education",
            "email_address": "joe.eyles@example.com",
        }

    # Ensure email_address is present in inputs
    if "email_address" not in inputs:
        logger.warning("'email_address' not found in inputs. Adding a placeholder for the API integration.")
        print("Warning: 'email_address' not found in inputs. Adding a placeholder for the API integration.")
        inputs["email_address"] = "placeholder@example.com"

    logger.info("Starting CrewAI workflow...")
    print("Starting CrewAI workflow")
    crew_result = SalesPersonalizedEmailCrew().crew().kickoff(inputs=inputs)

    # Log the result type for debugging
    logger.info(f"Crew execution result (type: {type(crew_result)})")
    print(f"Crew execution result (type: {type(crew_result)}):\n{crew_result}")
    
    # Now that we have the result, send it to the API
    api_result = send_email_to_api(
        email_data=crew_result,
        prospect_name=inputs.get("name", "Unknown Prospect"),
        prospect_email=inputs.get("email_address", "no-email@example.com")
    )
    
    print(f"API call result: {api_result}")
    
    # Now that we have the result, also send it to the API
    # This is a backup in case the callback in the crew isn't executed
    # (which can happen in some deployment environments)
    print("Executing API call from main.py (backup)")
    api_result = send_email_to_api(
        email_data=crew_result,
        prospect_name=inputs.get("name", "Unknown Prospect"),
        prospect_email=inputs.get("email_address", "no-email@example.com")
    )
    
    print(f"API call result: {api_result}")

    # Check if we need to send the result to the API
    # This only happens if we have an API token and URL and the flag indicating the callback executed is not set
    api_token = os.environ.get("EMAIL_API_TOKEN")
    api_url = os.environ.get("EMAIL_API_URL")
    
    # If environment variables are set, assume the callback has already executed and sent the email
    # Otherwise, send it from here as a fallback
    if not (api_token and api_url):
        print("Executing API call from main.py (primary - environment vars not found)")
        api_result = send_email_to_api(
            email_data=crew_result,
            prospect_name=inputs.get("name", "Unknown Prospect"),
            prospect_email=inputs.get("email_address", "no-email@example.com")
        )
        print(f"API call result: {api_result}")
    else:
        print("API environment variables found - assuming callback has already sent the email or will do so")
        
    print("=======================================")
    
    return crew_result


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


def test_api():
    """
    Diagnostic function to directly test API connectivity without running the CrewAI workflow.
    This function sends a test message to the API endpoint to verify that network connectivity 
    and authentication are working properly. It's especially useful for debugging Kubernetes 
    deployments or environment issues.
    """
    print("=======================================")
    print("RUNNING TEST_API FUNCTION")
    print("=======================================")

    api_url = "https://mycomputer.maziak.eu/api/v1/import/store-emails"
    headers = {
        "CF-Access-Client-Id": "3894d1511738c7ab1d79f04866bce72e.access",
        "CF-Access-Client-Secret": "d9cc6e4001d53f87f7dcdf3777e330d2781a9b866ef55ff222241b829166c510",
        "Content-Type": "application/json",
        "X-API-Token": "33f311ec174ef02f7c7ae27cd4cc52e3",
    }
    payload = {
        "data": {
            "name": "API Test Function",
            "email": "api.test@example.com",
            "subject": "Test Subject from API Test Function",
            "message": "This is a test message from the test_api function.",
            "date": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        }
    }
    
    print(f"Sending test request to {api_url}")
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        return True
    except Exception as e:
        print(f"Error during test API call: {e}")
        traceback.print_exc()
        return False

# Commented out automatic API test to prevent test messages in production
# To test API connectivity manually, call test_api() directly
# try:
#     print("Executing test_api function on module load to verify API connectivity")
#     test_api_result = test_api()
#     print(f"Test API connectivity result: {'Success' if test_api_result else 'Failed'}")
# except Exception as e:
#     print(f"Exception when calling test_api: {e}")
#     traceback.print_exc()

# Function available for manual testing but not automatically executed in production
# To test API connectivity manually, call test_api() directly
