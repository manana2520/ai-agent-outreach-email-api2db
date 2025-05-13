from crewai_tools import ScrapeWebsiteTool, SerperDevTool
from pydantic import BaseModel
import requests
from datetime import datetime, timezone
import json
import os
import re

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


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
    
    print(f"send_email_to_api called with: email_data type {type(email_data)}, prospect_name: {prospect_name}, prospect_email: {prospect_email}")
    
    # Extract data from the email_data object
    try:
        # Check if it's a CrewOutput object from CrewAI
        if hasattr(email_data, 'items') and callable(getattr(email_data, 'items', None)):
            # CrewOutput behaves like a dictionary
            subject = email_data.get('subject_line', "Default Subject")
            body = email_data.get('email_body', str(email_data))
        # Handle regular objects
        elif hasattr(email_data, "subject_line"):
            subject = email_data.subject_line
            body = email_data.email_body if hasattr(email_data, "email_body") else str(email_data)
        else:
            print("Processing as unknown object type:", type(email_data))
            # Try to see if there's subject_line and email_body in string representation
            email_str = str(email_data)
            if "subject_line" in email_str and "email_body" in email_str:
                print("Found subject_line and email_body in string representation, extracting")
                # Extract subject
                subject_match = re.search(r"'subject_line':\s*'([^']*)'", email_str)
                if subject_match:
                    subject = subject_match.group(1)
                else:
                    subject = "Default Subject"
                
                # Extract email body (more complex as it can contain quotes and newlines)
                body_start = email_str.find("'email_body': ")
                if body_start != -1:
                    # Move past the 'email_body': part
                    body_start += len("'email_body': ")
                    
                    # Handle email body properly
                    if email_str[body_start:].startswith('"'):
                        # Double-quoted string
                        body_end = email_str.find('",', body_start)
                        if body_end == -1:
                            body_end = email_str.find('"}', body_start)
                        body = email_str[body_start+1:body_end] if body_end != -1 else email_str[body_start+1:]
                    else:
                        # Assume it's a single-quoted string
                        body_end = email_str.find("',", body_start)
                        if body_end == -1:
                            body_end = email_str.find("'}", body_start)
                        body = email_str[body_start+1:body_end] if body_end != -1 else email_str[body_start+1:]
                else:
                    body = email_str  # Just use the whole string if parsing fails
            else:
                subject = "Default Subject"
                body = email_str
            
        print(f"Extracted subject: '{subject[:30]}...' and body (length: {len(body)})")
    except Exception as e:
        print(f"Error extracting fields from email_data: {e}")
        subject = "Default Subject (extraction error)"
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
        print(f"Sending API request to {api_url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        print(f"API response status: {response.status_code}")
        
        try:
            response.raise_for_status()
            response_content = response.text
            print(f"API response content: {response_content}")
            return {
                "status_code": response.status_code,
                "response_text": response_content,
                "success": True
            }
        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP error: {e}. Response body: {response.text}"
            print(error_message)
            return {
                "status_code": response.status_code,
                "response_text": error_message,
                "success": False
            }
    except requests.exceptions.Timeout:
        error_message = f"Request to {api_url} timed out after 30 seconds"
        print(error_message)
        return {
            "status_code": 408,
            "response_text": error_message,
            "success": False
        }
    except requests.exceptions.ConnectionError as e:
        error_message = f"Connection error to {api_url}: {e}"
        print(error_message)
        return {
            "status_code": 503,
            "response_text": error_message,
            "success": False
        }
    except Exception as e:
        error_message = f"Unexpected error sending to API: {str(e)}"
        print(error_message)
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

    # Store the current inputs for use in the callback
    _current_inputs = {}

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
        print(f"Executing store_email_callback")
        print(f"Received output: {output}")
        
        # Directly send the email to the API and don't rely on processing in main.py
        # Get email inputs from the inputs hash or use defaults
        send_email_to_api(
            email_data=output,
            prospect_name="Joe Eyles Script Test",
            prospect_email="joe.eyles.script.api2db@example.com"
        )
        
        # Still return the output so main.py can use it if needed
        return output
