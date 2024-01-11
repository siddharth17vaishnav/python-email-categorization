from contants import EMAIL_CATEGORIES
from utils.extraction import extract_activation_link
import openai

openai.api_key = ''


def generate_category_prompt(email_body):
    prompt = f"Email Body: {email_body}\n\nCategorize the email:"
    return prompt


def gen(body, attachment, sender, subject, request_body):
    prompt = (""
              f"email: {body}"
              f"attachment:{attachment}"
              f"sender: {sender}"
              f"subject:{subject}"
              f"output_format: json_object"
              f"expected_output:{request_body}")
    return prompt


def parse_data(data_string):
    data_string = data_string.replace("{", "").replace("}", "").replace("'", "")
    key_value_pairs = [pair.strip() for pair in data_string.split(',')]
    email_data = {}
    for pair in key_value_pairs:
        if ':' in pair:
            key, *value_parts = pair.split(': ', 1)
            value = ': '.join(value_parts).strip() if value_parts else ''
            key = key.strip('\"')
            value = value.strip('\"')
            formatted_key = key.lower().replace(' ', '_')
            email_data[formatted_key] = value
    return email_data


def use_openai(prompt):
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role": "user", "content": prompt}],
        max_tokens=193,
        temperature=0,
    )
    if response.choices[0]["message"]["content"] == "Uncategorized":
        return "Miscellaneous"
    return response.choices[0]["message"]["content"]


def categorize_email(body, attachment, sender, subject, links=None):
    if links is None:
        links = []
    category_prompt = generate_category_prompt(body)
    category = use_openai(category_prompt)
    result = {}
    if category in EMAIL_CATEGORIES:
        request_data = EMAIL_CATEGORIES[category]["request_data"]
        prompt = gen(body, attachment, sender, subject, request_data)
        response = use_openai(prompt)
        result["data"] = parse_data(response)

        if category == "Account Verification":
            activation_links = extract_activation_link(links)
            result["data"]["activation_link"] = activation_links
    # elif len(category) > 15:
    #     category = "Miscellaneous"

    return {"result": result, "category": category}
