import streamlit as st
from openai import OpenAI

# Show title and description.
st.title("💬 Chatbot - Kimi版")
st.write(
    "这是一个使用月之暗面Kimi模型的聊天机器人。 "
    "要使用此应用，您需要提供Kimi API密钥，您可以[在此获取](https://platform.moonshot.cn/console/api-keys)。 "
    "此应用基于Streamlit构建。"
)

# Ask user for their Kimi API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
kimi_api_key = st.text_input("Kimi API Key", type="password")
if not kimi_api_key:
    st.info("请添加您的Kimi API密钥以继续。", icon="🗝️")
else:

    # Create a Kimi client with custom base URL.
    client = OpenAI(
        api_key=kimi_api_key,
        base_url="https://api.moonshot.cn/v1"
    )

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("有什么可以帮您？"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate a response using the Kimi API.
        stream = client.chat.completions.create(
            model="moonshot-v1-8k",  # Kimi模型，也可以使用其他可用模型如 moonshot-v1-32k
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )

        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
