from crewai_tools import ScrapeWebsiteTool, SerperDevTool
from pydantic import BaseModel
import requests
from datetime import datetime, timezone
import json
import os
import re
import logging
import traceback

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
        
        # Add detailed debugging for the subject
        logger.info(f"SUBJECT DEBUG - Full subject: '{subject}'")
        logger.info(f"SUBJECT DEBUG - Subject length: {len(subject)}")
        logger.info(f"SUBJECT DEBUG - First 20 chars: '{subject[:20]}'")
        
        # Add detailed debugging for the email body
        logger.info(f"BODY DEBUG - First 50 chars: '{body[:50]}'")
        logger.info(f"BODY DEBUG - Last 50 chars: '{body[-50:] if len(body) > 50 else body}'")
        logger.info(f"BODY DEBUG - Body total length: {len(body)}")
        logger.info(f"BODY DEBUG - Body contains newlines: {'\\n' in body}")
        logger.info(f"BODY DEBUG - Body content type: {type(body)}")
    except Exception as e:
        logger.error(f"Error extracting fields from email_data: {e}")
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
        
        # Debug the actual payload subject that will be sent
        logger.info(f"PAYLOAD DEBUG - Subject in payload: '{payload['data']['subject']}'")
        logger.info(f"PAYLOAD DEBUG - Subject length in payload: {len(payload['data']['subject'])}")
        logger.info(f"PAYLOAD DEBUG - Message length in payload: {len(payload['data']['message'])}")
        
        # Add detailed debugging for the full message in payload
        message_sample = payload['data']['message']
        logger.info(f"PAYLOAD BODY DEBUG - First 100 chars: '{message_sample[:100]}'")
        logger.info(f"PAYLOAD BODY DEBUG - Last 100 chars: '{message_sample[-100:] if len(message_sample) > 100 else message_sample}'")
        
        # Create a separate debug log with the serialized JSON
        payload_json = json.dumps(payload)
        logger.info(f"PAYLOAD JSON DEBUG - JSON length: {len(payload_json)}")
        logger.info(f"PAYLOAD JSON DEBUG - Preview: '{payload_json[:200]}...'")
        
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

    def kickoff(self, inputs: dict | None = None):
        """
        Kicks off the crew execution with the provided inputs.
        Stores the inputs for use in callbacks.
        """
        effective_inputs = inputs if inputs is not None else {}
        logger.info(f"SalesPersonalizedEmailCrew.kickoff called. Storing inputs (type: {type(effective_inputs)}): {effective_inputs}")
        self._crew_instance_inputs = effective_inputs

        # Now, get the actual CrewAI crew and kick it off
        crew_ai_crew_instance = self.crew() # This calls the @crew decorated method
        return crew_ai_crew_instance.kickoff(inputs=effective_inputs)

    def store_email_callback(self, output):
        """Callback to send email to API after task completion"""
        logger.warning(f"CALLBACK_ENTRY: store_email_callback INVOKED. Output type: {type(output)}")
        logger.info(f"CALLBACK: Received output (type: {type(output)}): {str(output)[:200]}...")
        
        # Default fallback values
        prospect_name_default = "Unknown Prospect via Callback"
        prospect_email_default = "unknown_callback@example.com"
        
        prospect_name = prospect_name_default
        prospect_email = prospect_email_default
        
        # FIRST APPROACH: Try to get data from task context or request payload
        try:
            # Check if there's a 'task' attribute with run context
            if hasattr(output, 'task') and hasattr(output.task, 'inputs'):
                task_inputs = output.task.inputs
                logger.info(f"CALLBACK: Found task.inputs: {task_inputs}")
                if isinstance(task_inputs, dict):
                    if 'name' in task_inputs and task_inputs['name']:
                        prospect_name = task_inputs['name']
                        logger.info(f"CALLBACK: Found name in task inputs: '{prospect_name}'")
                    if 'email_address' in task_inputs and task_inputs['email_address']:
                        prospect_email = task_inputs['email_address']
                        logger.info(f"CALLBACK: Found email_address in task inputs: '{prospect_email}'")
                    elif 'email' in task_inputs and task_inputs['email']:
                        prospect_email = task_inputs['email']
                        logger.info(f"CALLBACK: Found email in task inputs: '{prospect_email}'")
            
            # Try to access the run inputs through any available mechanism
            import inspect
            current_frame = inspect.currentframe()
            for frame_info in inspect.getouterframes(current_frame):
                frame = frame_info.frame
                if 'inputs' in frame.f_locals and isinstance(frame.f_locals['inputs'], dict):
                    run_inputs = frame.f_locals['inputs']
                    logger.info(f"CALLBACK: Found run inputs in stack frame: {run_inputs}")
                    if 'name' in run_inputs and run_inputs['name'] and prospect_name == prospect_name_default:
                        prospect_name = run_inputs['name']
                        logger.info(f"CALLBACK: Found name in run inputs: '{prospect_name}'")
                    if 'email_address' in run_inputs and run_inputs['email_address'] and prospect_email == prospect_email_default:
                        prospect_email = run_inputs['email_address']
                        logger.info(f"CALLBACK: Found email_address in run inputs: '{prospect_email}'")
                    elif 'email' in run_inputs and run_inputs['email'] and prospect_email == prospect_email_default:
                        prospect_email = run_inputs['email']
                        logger.info(f"CALLBACK: Found email in run inputs: '{prospect_email}'")
                elif 'run_inputs' in frame.f_locals and isinstance(frame.f_locals['run_inputs'], dict):
                    run_inputs = frame.f_locals['run_inputs']
                    logger.info(f"CALLBACK: Found run_inputs in stack frame: {run_inputs}")
                    if 'name' in run_inputs and run_inputs['name'] and prospect_name == prospect_name_default:
                        prospect_name = run_inputs['name']
                        logger.info(f"CALLBACK: Found name in run_inputs: '{prospect_name}'")
                    if 'email_address' in run_inputs and run_inputs['email_address'] and prospect_email == prospect_email_default:
                        prospect_email = run_inputs['email_address']
                        logger.info(f"CALLBACK: Found email_address in run_inputs: '{prospect_email}'")
                    elif 'email' in run_inputs and run_inputs['email'] and prospect_email == prospect_email_default:
                        prospect_email = run_inputs['email']
                        logger.info(f"CALLBACK: Found email in run_inputs: '{prospect_email}'")
                
                # Also look for run_id to possibly fetch inputs
                if 'run_id' in frame.f_locals and prospect_email == prospect_email_default:
                    run_id = frame.f_locals['run_id']
                    logger.info(f"CALLBACK: Found run_id in stack frame: {run_id}")
                    try:
                        import os
                        import requests
                        api_url = f"http://localhost:8000/runs/{run_id}"
                        headers = {"Authorization": f"Bearer {os.environ.get('AGENT_API_TOKEN', '')}"}
                        response = requests.get(api_url, headers=headers, timeout=5)
                        if response.status_code == 200:
                            run_data = response.json()
                            if 'inputs' in run_data and isinstance(run_data['inputs'], dict):
                                api_inputs = run_data['inputs']
                                logger.info(f"CALLBACK: Retrieved run inputs from API: {api_inputs}")
                                
                                # Extract email and name if available
                                if 'name' in api_inputs and api_inputs['name'] and prospect_name == prospect_name_default:
                                    prospect_name = api_inputs['name']
                                    logger.info(f"CALLBACK: Found name from API: '{prospect_name}'")
                                if 'email_address' in api_inputs and api_inputs['email_address'] and prospect_email == prospect_email_default:
                                    prospect_email = api_inputs['email_address']
                                    logger.info(f"CALLBACK: Found email_address from API: '{prospect_email}'")
                                elif 'email' in api_inputs and api_inputs['email'] and prospect_email == prospect_email_default:
                                    prospect_email = api_inputs['email']
                                    logger.info(f"CALLBACK: Found email from API: '{prospect_email}'")
                    except Exception as e:
                        logger.error(f"CALLBACK: Error fetching inputs from API: {e}")
        except Exception as e:
            logger.error(f"CALLBACK: Error accessing task/run context: {e}")
            logger.error(traceback.format_exc())
        
        # SECOND APPROACH: Try environment variables
        if (prospect_name == prospect_name_default or prospect_email == prospect_email_default):
            try:
                import os
                import json
                
                # Try the direct JSON input variable
                agent_inputs_json = os.environ.get('AGENT_RUN_INPUTS_JSON', '')
                if agent_inputs_json:
                    logger.info(f"CALLBACK: Found AGENT_RUN_INPUTS_JSON environment variable")
                    try:
                        input_data = json.loads(agent_inputs_json)
                        # For direct input format
                        if isinstance(input_data, dict) and 'inputs' in input_data and isinstance(input_data['inputs'], dict):
                            inputs = input_data['inputs']
                            logger.info(f"CALLBACK: Successfully parsed direct inputs: {json.dumps(inputs)[:200]}...")
                        # For top-level format
                        else:
                            inputs = input_data
                            logger.info(f"CALLBACK: Using top-level inputs: {json.dumps(inputs)[:200]}...")
                        
                        # Extract name
                        if prospect_name == prospect_name_default and 'name' in inputs and inputs['name']:
                            prospect_name = inputs['name']
                            logger.info(f"CALLBACK: Found name in environment JSON: '{prospect_name}'")
                        
                        # Extract email
                        if prospect_email == prospect_email_default:
                            if 'email_address' in inputs and inputs['email_address']:
                                prospect_email = inputs['email_address']
                                logger.info(f"CALLBACK: Found email_address in environment JSON: '{prospect_email}'")
                            elif 'email' in inputs and inputs['email']:
                                prospect_email = inputs['email']
                                logger.info(f"CALLBACK: Found email in environment JSON: '{prospect_email}'")
                    except json.JSONDecodeError as e:
                        logger.error(f"CALLBACK: Error parsing AGENT_RUN_INPUTS_JSON: {e}")
            except Exception as e:
                logger.error(f"CALLBACK: Error accessing environment variables: {e}")
                logger.error(traceback.format_exc())
        
        # THIRD APPROACH: Try CrewAI instance inputs
        if (prospect_name == prospect_name_default or prospect_email == prospect_email_default) and self._crew_instance_inputs and isinstance(self._crew_instance_inputs, dict):
            logger.debug(f"CALLBACK_DEBUG: self._crew_instance_inputs is a TRUTHY dictionary.")
            # Get name from the inputs
            if prospect_name == prospect_name_default and "name" in self._crew_instance_inputs and self._crew_instance_inputs["name"]:
                prospect_name = self._crew_instance_inputs["name"]
                logger.info(f"CALLBACK: Found name in inputs: '{prospect_name}'")
            
            # Get email from inputs
            if prospect_email == prospect_email_default:
                if "email_address" in self._crew_instance_inputs and self._crew_instance_inputs["email_address"]:
                    prospect_email = self._crew_instance_inputs["email_address"]
                    logger.info(f"CALLBACK: Found email_address in inputs: '{prospect_email}'")
                elif "email" in self._crew_instance_inputs and self._crew_instance_inputs["email"]:
                    prospect_email = self._crew_instance_inputs["email"]
                    logger.info(f"CALLBACK: Found email in inputs: '{prospect_email}'")
        
        # FOURTH APPROACH: Extract from email output
        if prospect_name == prospect_name_default or prospect_email == prospect_email_default:
            logger.info("CALLBACK: Attempting to extract information from email body")
            try:
                # Get the actual content from output
                email_body = None
                if hasattr(output, 'email_body'):
                    email_body = output.email_body
                elif isinstance(output, dict) and 'email_body' in output:
                    email_body = output['email_body']
                else:
                    # Try to parse from the string representation
                    email_str = str(output)
                    body_match = re.search(r"['\"]email_body['\"]:\s*['\"](.*?)['\"]", email_str, re.DOTALL)
                    if body_match:
                        email_body = body_match.group(1)
                
                if email_body:
                    # Extract name from greeting
                    if prospect_name == prospect_name_default:
                        # Find patterns like "Dear [Name]," or "Hi [Name]," or "Hello [Name],"
                        name_match = re.search(r"(?:Dear|Hi|Hello)\s+([^,\n]+)", email_body)
                        if name_match and name_match.group(1):
                            extracted_name = name_match.group(1).strip()
                            # If extracted name looks reasonable (not too long, not containing weird chars)
                            if 2 <= len(extracted_name) <= 50 and re.match(r"^[A-Za-z\s\.\-']+$", extracted_name):
                                prospect_name = extracted_name
                                logger.info(f"CALLBACK: Extracted prospect name from email greeting: '{prospect_name}'")
                    
                    # Look for job title and company pairing if name still not found
                    if prospect_name == prospect_name_default:
                        title_company_match = re.search(r"(?:as|at|with|for)\s+(?:the|a|an)?\s+([A-Za-z\s\.\-']+)\s+(?:at|of|with|for)\s+([A-Za-z\s\.\-'&]+)", email_body)
                        if title_company_match:
                            title = title_company_match.group(1).strip()
                            company = title_company_match.group(2).strip()
                            if title and company:
                                prospect_name = f"{title} at {company}"
                                logger.info(f"CALLBACK: Created name from title/company: '{prospect_name}'")
                    
                    # Try to extract email if still using default
                    if prospect_email == prospect_email_default:
                        # Look for common email references in the body
                        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email_body)
                        if email_match:
                            extracted_email = email_match.group(0)
                            if '@' in extracted_email and '.' in extracted_email and len(extracted_email) > 5:
                                prospect_email = extracted_email
                                logger.info(f"CALLBACK: Extracted email from body: '{prospect_email}'")
            except Exception as e:
                logger.error(f"CALLBACK: Error attempting to extract name/email from output: {e}")
                traceback.print_exc()
        
        # FINAL APPROACH: Set default email based on name if we have a name but no email
        if prospect_name != prospect_name_default and prospect_email == prospect_email_default:
            # Create a simple email based on the name
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', prospect_name.lower().replace(' ', '.'))
            if clean_name:
                prospect_email = f"{clean_name}@example.com"
                logger.info(f"CALLBACK: Created email from name: '{prospect_email}'")
        
        logger.info(f"CALLBACK: Using final values: Name='{prospect_name}', Email='{prospect_email}'")

        # Directly send the email to the API
        api_call_result = send_email_to_api(
            email_data=output,
            prospect_name=prospect_name,
            prospect_email=prospect_email
        )
        logger.info(f"CALLBACK: API call result: {api_call_result}")
        
        # Still return the output
        return output
