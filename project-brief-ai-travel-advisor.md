
# Mini-Project — AI Travel Advisor

<br>

## Goal

Build an AI-powered **Travel Advisor** that helps users plan personalized trips through a conversational interface.

The application should gather information about the user's trip, ask follow-up questions when needed, and generate a complete travel itinerary.

<img width="1672" height="941" alt="image" src="https://gist.github.com/user-attachments/assets/e1ab3474-94e7-4aaa-aaef-bc6bdb713291" />


<br><br>

# Core Requirements


The assistant should greet the user and collect the information needed to plan the trip. It should ask follow-up questions until it has gathered at least:

- Destination and trip duration
- Interests (e.g., food, museums, hiking, beaches, nightlife, shopping)
- Any relevant preferences or constraints (optional)


Once enough information has been collected, generate a personalized travel plan including:

- Trip title
- Trip summary
- Day-by-day itinerary
- Practical travel tips
- Estimated budget


Notes:
- The assistant should avoid asking unnecessary questions once it has enough information.
- If the user provides contradictory or ambiguous information, the assistant should ask for clarification before generating the itinerary.
- Feel free to be creative, while keeping the itinerary realistic and consistent with the user's preferences.


Maintaining Conversation Context:
- One of the main challenges here is that you'll need to keep track of the conversation between the user and the chatbot. LLMs don't automatically remember previous messages —they only see the information included in each request. If we only send the latest user message, the model won't know the earlier context, so you'll need to store the conversation history and include the relevant messages in every API call.

<br>

---
---

<br>

## Bonus Challenges

<br>

You can take this project as far as you'd like. Here are a few ideas for bonus features:

<br>


<details>
  <summary>Track token usage and estimate LLM costs</summary>
  <br />

  - For each conversation, calculate and display the total number of input/output tokens consumed and an estimated API cost (in $ or €).
  <br />
</details>

<details>
  <summary>Generate the itinerary in a structured format</summary>
  <br />

  - Return the itinerary in a well-defined format such as **Markdown**, **JSON**, or **HTML** (choose one and use it consistently).
  <br />
</details>

<details>
  <summary>Use tool calling and/or web search</summary>
  <br />
  
  - Enhance the itinerary by using tool calling and/or web search to retrieve relevant external information (e.g., weather forecasts, transportation options, or currency exchange rates).
  - You can allow the user to ask questions related to those topics and/or incorporate the retrieved information into the final itinerary where appropriate.
  <br />
</details>

<details>
  <summary>Compare different LLMs</summary>
  <br />
  
  - Experiment with different language models (e.g., other OpenAI models or models from other providers) and compare their performance in terms of quality, latency, and cost.
  - Evaluate whether using a more capable (and more expensive) model is justified for this use case.
  <br />
</details>

<details>
  <summary>Use multiple models for different tasks</summary>
  <br />
  
  - Implement a multi-model workflow to balance cost, latency, and quality. For example:
    - Use a smaller, lower-cost model to manage the conversation, ask follow-up questions, and collect the user's travel preferences.
    - Once all the required information has been gathered, have that model invoke a tool using **tool calling**.
    - Within that tool, call a more capable model to generate the final itinerary.
  
  - **Note 1:** This is a common production pattern that helps optimize both cost and response quality.
  
  - **Note 2:** For this particular use case, the most powerful model is unlikely to be necessary.
  <br />
</details>

<details>
  <summary>Automatically summarize long conversations</summary>
  <br />
  
  - When the conversation becomes too long to fit within the model's context window, automatically generate a summary of the relevant information and use it to continue the conversation.
  <br />
</details>

<details>
  <summary>Generate an image for each itinerary</summary>
  <br />
  
  - Generate an AI-created image that visually represents the destination and/or the proposed itinerary.
  <br />
</details>

<details>
  <summary>Perform a security analysis</summary>
  <br />

  - Analyze the application from a security perspective and identify potential risks, such as prompt injection attacks, misuse of tool calling, unintended chatbot behavior, or attempts to use the assistant for purposes outside its intended scope.
  - Propose appropriate mitigations and best practices to make the application more robust and secure.
  <br />
</details>