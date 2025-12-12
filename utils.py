import os

from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def fetch_all_issues(jira, jql, max_issues=1000):
        
    all_issues = []
    jql = "project = SDIPR ORDER BY created DESC"
    next_token = None
    counter = 0
    b_max_results = 100
    while True:
        page = jira.enhanced_search_issues(
            jql_str=jql,
            maxResults=b_max_results,         # per API call
            nextPageToken=next_token,
            json_result=True,
        )

        all_issues.extend(page.get("issues", []))
        next_token = page.get("nextPageToken")

        if not next_token:  # no more pages
            break
        counter += b_max_results
        if counter >= max_issues:
            break

    print("Total issues fetched:", len(all_issues))
    return all_issues
    

# function to call OpenAI API to analyze the descriptions from list of descriptions for one category   
def run_prompt(openai, prompt):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def get_summary(descriptions: list[str]) -> str:
    # Construct prompt for GPT-4o-mini to analyze the descriptions from list of descriptions for one category   
    prompt = f"""Du bist ein Experte für die Analyse von Beschreibungen von Jira-Tickets.
            Ich gebe dir Beschreibunngen von Jira-Tickets aus dem Bereich Kundensupport (Service Desk) und du sollst aus den Texten
            wiederkehrende Themen und Probleme herausfinden. Die Tickets sind bereits nach einer Hauptkategorie gefiltert.
            Hier sind die Beschreibungen (durch Doppel- Pipes getrennt): {"\n||".join(descriptions)}
            Deine Antwort soll als Markdown-Text erfolgen.
            Ich möchte zuerst eine kurze Zusammenfassung der gesamten Hauptkategorie basierend auf den Beschreibungen erhalten.
            Dann sollst du fünf bis zehn wiederkehrende Themen und Probleme herausfinden, nach Häufigkeit sortiert.
            Gib auch eine Einschätzung zu ungefähren Häufigkeit der Themen und Probleme in der Form "Häufigkeit: X% (Y Tickets von N Tickets)".
            Nenne in der Zusammenfassung und in den Themen und Problemen keine Namen.
            Strukturiere deine Antwort als Markdown-Text.
            """
    return run_prompt(openai, prompt)