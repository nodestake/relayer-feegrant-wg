import os
import json
import sys
import requests

def get_issue_content(issue_number, token):
    """Fetch the content of the issue from GitHub."""
    url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/issues/{issue_number}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch issue content: {response.status_code}")

def parse_issue_content(issue_content):
    """Parse the issue content to extract necessary information."""
    body = issue_content['body']
    lines = body.split('\n')
    data = {}
    for line in lines:
        if line.startswith('- '):
            key, value = line[2:].split(':', 1)
            data[key.strip()] = value.strip()
    return data

def update_ibc_file(ibc_path, operator_data):
    file_path = f'./_IBC/{ibc_path}.json'
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    # Determine which chain is 'cosmoshub'
    cosmoshub_chain_key = 'chain_1' if data.get('chain_1', {}).get('chain_name', '') == 'cosmoshub' else \
                          'chain_2' if data.get('chain_2', {}).get('chain_name', '') == 'cosmoshub' else \
                          None

    if cosmoshub_chain_key:
        other_chain_key = 'chain_2' if cosmoshub_chain_key == 'chain_1' else 'chain_1'
        new_operator = {
            cosmoshub_chain_key: {
                "address": operator_data.get('Cosmoshub Account', '')
            },
            other_chain_key: {
                "address": operator_data.get('Counterparty Account', '')
            },
            'memo': operator_data.get('Memo', ''),
            'name': operator_data.get('Operator Name', ''),
            'discord': {'handle': operator_data.get('Discord Handle', '')},
            'telegram': {'handle': operator_data.get('Telegram Handle', '')}
        }
        data['operators'].append(new_operator)
    else:
        print(f"Cosmoshub chain not found in {ibc_path}.json")

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def validate_operator_data(operator_data):
    """Validate the operator data and return an error message if validation fails."""
    required_fields = ['Cosmoshub Account', 'Counterparty Account', 'Operator Name']
    missing_fields = [field for field in required_fields if not operator_data.get(field, '').strip()]
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}."

    if not (operator_data.get('Discord Handle', '').strip() or operator_data.get('Telegram Handle', '').strip()):
        return "At least one contact method (Discord Handle or Telegram Handle) is required."

    return ""

def post_comment(issue_number, message, token):
    """Post a comment on the GitHub issue."""
    url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/issues/{issue_number}/comments"
    headers = {"Authorization": f"token {token}"}
    response = requests.post(url, json={"body": message}, headers=headers)
    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to post comment: {response.status_code}, {response.text}")

def main():
    issue_number = sys.argv[1]
    token = os.environ['GITHUB_TOKEN']
    issue_content = get_issue_content(issue_number, token)
    operator_data = parse_issue_content(issue_content)

    validation_error = validate_operator_data(operator_data)
    if validation_error:
        print(validation_error)
        post_comment(issue_number, validation_error, token)
        sys.exit(1)

    ibc_path = operator_data.pop('IBC Path')
    update_ibc_file(ibc_path, operator_data)
    print(f"Updated {ibc_path}.json with new operator data.")

    branch_name = f"operator-onboarding-{issue_number}"
    success_message = (
        f"Input validation passed. Your changes have been committed to the branch `{branch_name}`.\n"
        "Please review the changes and open a pull request to merge them into the main branch."
    )
    post_comment(issue_number, success_message, token)

if __name__ == "__main__":
    main()