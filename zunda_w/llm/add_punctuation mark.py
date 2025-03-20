from openai import OpenAI

client = OpenAI()
def _request(text: str,client:OpenAI) -> str:
    response = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {
          "role": "system",
          "content": [
            {
              "text": "与えるテキストに適切な位置に句読点を入れてください",
              "type": "text"
            }
          ]
        },
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "<input>"
            }
          ]
        }
      ],
      temperature=0.3,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )