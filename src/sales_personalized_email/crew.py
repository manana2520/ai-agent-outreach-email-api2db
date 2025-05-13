from crewai_tools import ScrapeWebsiteTool, SerperDevTool
from pydantic import BaseModel
import requests
from datetime import datetime, timezone
import json

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
    print(f"send_email_to_api called with: email_data type {type(email_data)}, prospect_name: {prospect_name}, prospect_email: {prospect_email}")
    
    # Handle different input formats
    if isinstance(email_data, str):
        try:
            print(f"Attempting to parse email_data as JSON string: {email_data[:100]}...")
            email_data = json.loads(email_data)
            print(f"Successfully parsed JSON. Keys: {email_data.keys() if isinstance(email_data, dict) else 'Not a dict'}")
            
            # If it's now a dict but not a PersonalizedEmail, convert it
            if isinstance(email_data, dict) and not isinstance(email_data, PersonalizedEmail):
                try:
                    email_data = PersonalizedEmail(**email_data)
                    print(f"Converted dict to PersonalizedEmail object")
                except Exception as e:
                    print(f"Error converting dict to PersonalizedEmail: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Simple fallback for plain text
            email_data = PersonalizedEmail(
                subject_line="Email from Agent",
                email_body=email_data,
                follow_up_notes=""
            )
            print(f"Created simple PersonalizedEmail from text")
        except Exception as e:
            print(f"Unexpected error parsing email_data: {e}")
            email_data = PersonalizedEmail(
                subject_line="Email from Agent",
                email_body=str(email_data),
                follow_up_notes=""
            )
    elif isinstance(email_data, dict):
        try:
            email_data = PersonalizedEmail(**email_data)
            print(f"Converted dict directly to PersonalizedEmail object")
        except Exception as e:
            print(f"Error converting dict to PersonalizedEmail: {e}")
            # Try to extract useful fields from the dict
            email_data = PersonalizedEmail(
                subject_line=email_data.get("subject_line", "Email from Agent"),
                email_body=email_data.get("email_body", str(email_data)),
                follow_up_notes=email_data.get("follow_up_notes", "")
            )
    
    # Extract data from the email_data object
    try:
        # Check if it's a CrewOutput object from CrewAI
        if hasattr(email_data, 'items') and callable(getattr(email_data, 'items', None)):
            # CrewOutput behaves like a dictionary
            print(f"Processing as dictionary-like object with keys: {list(email_data.keys())}")
            subject = email_data.get('subject_line', "Default Subject")
            body = email_data.get('email_body', str(email_data))
        # Handle regular objects
        elif hasattr(email_data, "subject_line"):
            print(f"Processing as object with subject_line attribute")
            subject = email_data.subject_line
            body = email_data.email_body if hasattr(email_data, "email_body") else str(email_data)
        # Handle string that might be JSON
        elif isinstance(email_data, str):
            print(f"Processing as string, attempting JSON parse")
            try:
                data = json.loads(email_data)
                subject = data.get('subject_line', "Default Subject")
                body = data.get('email_body', email_data)
            except:
                subject = "Default Subject"
                body = email_data
        else:
            print(f"Processing as unknown object type: {type(email_data)}")
            # Try to get string representation and extract JSON-like data
            email_data_str = str(email_data)
            if "'subject_line':" in email_data_str and "'email_body':" in email_data_str:
                print("Found subject_line and email_body in string representation, extracting")
                # Extract the values using regex
                import re
                subject_match = re.search(r"'subject_line':\s*'([^']*)'", email_data_str)
                subject = subject_match.group(1) if subject_match else "Default Subject"
                # Get body until next single quote followed by comma (simplified)
                body_match = re.search(r"'email_body':\s*'([^']*)'", email_data_str)
                body = body_match.group(1) if body_match else email_data_str
            else:
                subject = "Default Subject"
                body = email_data_str
            
        print(f"Extracted subject: '{subject[:30]}...' and body (length: {len(str(body))})")
    except Exception as e:
        print(f"Error extracting fields from email_data: {e}")
        print(f"email_data type: {type(email_data)}")
        try:
            print(f"email_data stringified: {str(email_data)[:500]}...")
        except:
            print("Could not stringify email_data")
        subject = "Default Subject (extraction error)"
        body = str(email_data)
            
    api_url = "https://mycomputer.maziak.eu/api/v1/import/store-emails"
    headers = {
        "CF-Access-Client-Id": "3894d1511738c7ab1d79f04866bce72e.access",
        "CF-Access-Client-Secret": "d9cc6e4001d53f87f7dcdf3777e330d2781a9b866ef55ff222241b829166c510",
        "Content-Type": "application/json",
        "X-API-Token": "33f311ec174ef02f7c7ae27cd4cc52e3",
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
        # Since we can't reliably get the inputs in the callback,
        # we'll just return the output and handle the API sending in main.py
        return output
