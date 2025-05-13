from crewai_tools import ScrapeWebsiteTool, SerperDevTool
from pydantic import BaseModel
import requests
from datetime import datetime, timezone
import json
import os
import re
import logging

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# It's better to get the logger configured in main.py or create a specific one for crew.py
# For simplicity, let's try to use a basic configured logger here if needed.
# However, ideally the main module logger should be passed or imported if possible.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.hasHandlers():
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # More explicit basic handler setup for this specific logger if needed:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False # Prevent duplicate messages if root logger is also configured by main.py

class PersonalizedEmail(BaseModel):
    subject_line: str
    email_body: str
    follow_up_notes: str


def send_email_to_api(email_data, prospect_name, prospect_email):
    """
    Utility function to send email data to the external API
    
    Args:
        email_data: The PersonalizedEmail object containing subject_line, email_body, and follow_up_notes
        prospect_name: The name of the prospect
        prospect_email: The email address of the prospect
        
    Returns:
        API response information
    """
    # Get API configuration from environment variables
    api_url = os.environ.get("EMAIL_API_URL", "https://mycomputer.maziak.eu/api/v1/import/store-emails")
    api_token = os.environ.get("EMAIL_API_TOKEN", "33f311ec174ef02f7c7ae27cd4cc52e3")
    cf_client_id = os.environ.get("CF_ACCESS_CLIENT_ID", "3894d1511738c7ab1d79f04866bce72e.access")
    cf_client_secret = os.environ.get("CF_ACCESS_CLIENT_SECRET", "d9cc6e4001d53f87f7dcdf3777e330d2781a9b866ef55ff222241b829166c510")
    
    # Parse string to dict if needed
    if isinstance(email_data, str):
        try:
            email_data = json.loads(email_data)
        except:
            # Not JSON, leave as is
            pass
    
    logger.info(f"send_email_to_api called with: email_data type {type(email_data)}, prospect_name: {prospect_name}, prospect_email: {prospect_email}")
    
    # Extract data from the email_data object
    try:
        actual_email_content = None
        if hasattr(email_data, 'raw_output') and email_data.raw_output:
            logger.info("Processing TaskOutput/CrewOutput via raw_output")
            # Try to parse raw_output if it's a JSON string
            try:
                actual_email_content = json.loads(email_data.raw_output)
            except json.JSONDecodeError:
                logger.warning(f"raw_output is not a valid JSON string: {email_data.raw_output[:100]}...")
                # Fallback if raw_output is not JSON but a plain string (should not happen with Pydantic model output)
                actual_email_content = {"subject_line": "Default Subject (raw_output non-json)", "email_body": str(email_data.raw_output)}
        elif isinstance(email_data, dict):
            logger.info("Processing TaskOutput/CrewOutput as dict")
            actual_email_content = email_data
        elif hasattr(email_data, 'subject_line') and hasattr(email_data, 'email_body'): # Direct Pydantic model
             logger.info("Processing TaskOutput/CrewOutput as Pydantic model attribute access")
             actual_email_content = {
                 "subject_line": email_data.subject_line,
                 "email_body": email_data.email_body
             }
        else:
            # Fallback for unexpected types or string representations
            logger.warning(f"Fallback: email_data is of type {type(email_data)}. Attempting string parsing.")
            email_str = str(email_data) 
            subject_match = re.search(r"['\"]subject_line['\"]:\s*['\"](.*?)['\"]", email_str)
            body_match = re.search(r"['\"]email_body['\"]:\s*['\"](.*?)['\"]", email_str, re.DOTALL)
            subject = subject_match.group(1) if subject_match else "Default Subject (str parse fallback)"
            body = body_match.group(1) if body_match else email_str
            actual_email_content = {"subject_line": subject, "email_body": body}

        subject = actual_email_content.get('subject_line', "Default Subject (content parse error)")
        body = actual_email_content.get('email_body', str(actual_email_content)) # Use str as last resort
            
        logger.info(f"Extracted subject: '{subject[:50]}...' and body (length: {len(body)})")
    except Exception as e:
        logger.error(f"Error extracting fields from email_data: {e}")
        import traceback
        traceback.print_exc()
        subject = "Default Subject (extraction exception)"
        body = str(email_data)
        
    # Prepare API call
    headers = {
        "CF-Access-Client-Id": cf_client_id,
        "CF-Access-Client-Secret": cf_client_secret,
        "Content-Type": "application/json",
        "X-API-Token": api_token,
    }
    
    payload = {
        "data": {
            "name": prospect_name,
            "email": prospect_email,
            "subject": subject,
            "message": body,
            "date": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        }
    }
    
    try:
        logger.info(f"Sending API request to {api_url}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        logger.info(f"API response status: {response.status_code}")
        
        try:
            response.raise_for_status()
            response_content = response.text
            logger.info(f"API response content: {response_content}")
            return {
                "status_code": response.status_code,
                "response_text": response_content,
                "success": True
            }
        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP error: {e}. Response body: {response.text}"
            logger.error(error_message)
            return {
                "status_code": response.status_code,
                "response_text": error_message,
                "success": False
            }
    except requests.exceptions.Timeout:
        error_message = f"Request to {api_url} timed out after 30 seconds"
        logger.error(error_message)
        return {
            "status_code": 408,
            "response_text": error_message,
            "success": False
        }
    except requests.exceptions.ConnectionError as e:
        error_message = f"Connection error to {api_url}: {e}"
        logger.error(error_message)
        return {
            "status_code": 503,
            "response_text": error_message,
            "success": False
        }
    except Exception as e:
        error_message = f"Unexpected error sending to API: {str(e)}"
        logger.error(error_message)
        import traceback
        traceback.print_exc()
        return {
            "status_code": 500,
            "response_text": error_message,
            "success": False
        }


@CrewBase
class SalesPersonalizedEmailCrew:
    """SalesPersonalizedEmail crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    _crew_instance_inputs: dict = None # To store inputs for the callback

    @agent
    def prospect_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["prospect_researcher"],
            tools=[SerperDevTool(), ScrapeWebsiteTool()],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def content_personalizer(self) -> Agent:
        return Agent(
            config=self.agents_config["content_personalizer"],
            tools=[],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def email_copywriter(self) -> Agent:
        return Agent(
            config=self.agents_config["email_copywriter"],
            tools=[],
            allow_delegation=False,
            verbose=True,
        )

    @task
    def research_prospect_task(self) -> Task:
        return Task(
            config=self.tasks_config["research_prospect_task"],
            agent=self.prospect_researcher(),
        )

    @task
    def personalize_content_task(self) -> Task:
        return Task(
            config=self.tasks_config["personalize_content_task"],
            agent=self.content_personalizer(),
        )

    @task
    def write_email_task(self) -> Task:
        """Define the email writing task"""
        return Task(
            config=self.tasks_config["write_email_task"],
            agent=self.email_copywriter(),
            output_json=PersonalizedEmail,
            callback=self.store_email_callback
        )

    @crew
    def crew(self) -> Crew:
        """Creates the SalesPersonalizedEmail crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )

    def store_email_callback(self, output):
        """Callback to send email to API after task completion"""
        logger.warning(f"CALLBACK_ENTRY: store_email_callback INVOKED. Output type: {type(output)}")
        logger.info(f"CALLBACK: Received output (type: {type(output)}): {str(output)[:200]}...")
        logger.debug(f"CALLBACK_DEBUG: Type of self._crew_instance_inputs: {type(self._crew_instance_inputs)}")
        logger.debug(f"CALLBACK_DEBUG: Value of self._crew_instance_inputs: {self._crew_instance_inputs}")

        prospect_name_default = "Unknown Prospect via Callback"
        prospect_email_default = "unknown_callback@example.com"
        
        prospect_name = prospect_name_default
        prospect_email = prospect_email_default
        
        if self._crew_instance_inputs and isinstance(self._crew_instance_inputs, dict):
            logger.debug(f"CALLBACK_DEBUG: self._crew_instance_inputs is a TRUTHY dictionary.")
            retrieved_name = self._crew_instance_inputs.get("name")
            retrieved_email = self._crew_instance_inputs.get("email_address")
            
            logger.debug(f"CALLBACK_DEBUG: Retrieved name from dict: {retrieved_name} (type: {type(retrieved_name)})")
            logger.debug(f"CALLBACK_DEBUG: Retrieved email from dict: {retrieved_email} (type: {type(retrieved_email)})")
            
            if retrieved_name:
                prospect_name = retrieved_name
            else:
                logger.warning(f"CALLBACK_DEBUG: 'name' key not found or None in _crew_instance_inputs. Using default: {prospect_name_default}")

            if retrieved_email:
                prospect_email = retrieved_email
            else:
                logger.warning(f"CALLBACK_DEBUG: 'email_address' key not found or None in _crew_instance_inputs. Using default: {prospect_email_default}")
            
            logger.info(f"CALLBACK: Using inputs from _crew_instance_inputs: Name='{prospect_name}', Email='{prospect_email}'")
        else:
            logger.warning(f"CALLBACK_DEBUG: self._crew_instance_inputs is FALSY or not a dict. Using defaults.")
            logger.warning(f"CALLBACK: Warning: _crew_instance_inputs not found, empty, or not a dict. Using default name='{prospect_name_default}', email='{prospect_email_default}'.")

        # Directly send the email to the API
        api_call_result = send_email_to_api(
            email_data=output,
            prospect_name=prospect_name,
            prospect_email=prospect_email
        )
        logger.info(f"CALLBACK: API call result: {api_call_result}")
        
        # Still return the output
        return output
